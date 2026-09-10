"""
Phase 7 · 客服工作台（Streamlit 薄壳 UI）
===========================================
薄壳原则：业务逻辑全在 scripts\agent7_webapp.py，本文件只做渲染与状态搬运——
  UI 三零件：
    1. 会话：thread_id 存 st.session_state（新会话 = 换新 thread_id）
    2. 历史渲染：从 agent.get_state 拉（checkpointer 即真相源，重跑不丢）
    3. 聊天/审批：st.chat_input 发消息 → run_turn；返回 __interrupt__ 暂停 →
       渲染审批卡片（订单/理由 + 批准/拒绝按钮）→ resume_turn 恢复

核心论断（教学点，详见 lessons\lesson_agent7_webapp.md）：
  web 无状态 ≠ agent 无记忆。Streamlit 每次交互都重跑本脚本（无状态请求），
  agent 却可能跑一半停在 interrupt 等人审批（长时运行）。桥 = thread_id：
  UI 只搬运 thread_id 与每轮增量，历史/暂停全由 checkpointer 持有。

运行：
  streamlit run app.py
AppTest 冒烟（零 API）：
  scripts\agent7_app_test.py（CHAT_FAKE_AGENT=1 走 FakeAgent）
"""

import os
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from langchain_core.messages import AIMessage, HumanMessage

from agent7_webapp import (
    FakeAgent,
    build_agent,
    get_history,
    resume_turn,
    run_turn,
)

st.set_page_config(page_title="SmartHome 客服工作台", page_icon="🎧", layout="wide")
st.title("🎧 SmartHome 客服工作台")
st.caption("Phase 7 教学 Demo：LangGraph 记忆 + 人工审批 拼进可交互 UI。左侧新建会话，输入框聊天；申请退款会暂停等审批。")


@st.cache_resource(show_spinner="加载客服 Agent 中...")
def get_agent():
    """agent 是昂贵资源，缓存后重跑不重建；AppTest 冒烟走假 agent"""
    if os.getenv("CHAT_FAKE_AGENT") == "1":
        return FakeAgent()
    return build_agent()  # 真实 DeepSeek + V2 create_agent + checkpointer


agent = get_agent()

# ─── 会话管理：thread_id = web 会话的钥匙 ─────────────────
# uuid 必须在模块顶部 import：streamlit 每次交互都重新执行整个脚本，而若 import
# 写在下面的 if 块内，rerun 时 thread_id 已存在 → 该分支不进入 → uuid 未定义，
# 点「新建会话」就会 NameError（实测坑，见 findings F10）。
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = f"web-{uuid.uuid4().hex[:8]}"

# 上一轮遗留的待审卡片（rerun 后仍要显示，直到用户点批准/拒绝）
if "pending_card" not in st.session_state:
    st.session_state["pending_card"] = None

with st.sidebar:
    st.header("💬 会话")
    st.write(f"当前 thread：`{st.session_state['thread_id']}`")
    if st.button("🆕 新建会话", use_container_width=True, key="new_chat"):
        st.session_state["thread_id"] = f"web-{uuid.uuid4().hex[:8]}"
        st.session_state["pending_card"] = None
        st.rerun()
    st.divider()
    st.caption("新会话 = 换新 thread_id → checkpointer 里是全新对话（会话隔离）。")


# ─── 历史渲染：从 checkpointer 拉当前 thread 全部消息 ─────
# 只渲染"面向用户"的消息：用户输入 + 最终答复(无 tool_calls 的 AI 文本)。
# 跳过 ToolMessage（工具原始返回）与带 tool_calls 的中间 AI 消息——这些是 agent
# 内部过程，渲染出来是噪音（真实 LLM 的英文 preamble / 原始数据都会漏出来）。
history = get_history(agent, st.session_state["thread_id"])
for msg in history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(str(msg.content))
    elif isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
        with st.chat_message("assistant"):
            st.markdown(str(msg.content))

# 显示待审卡片（若有暂停中的审批）
if st.session_state["pending_card"] is not None:
    card = st.session_state["pending_card"]
    with st.chat_message("assistant"):
        st.warning("⏸ 退款申请待审批（客服经理）——agent 已暂停等待您的决定")
        st.markdown(
            f"**订单**：{card.get('order_id')}（{card.get('product')}）  "
            f"**金额**：{card.get('price')} 元\n\n"
            f"**理由**：{card.get('reason')}"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 批准", key="approve", use_container_width=True):
                resume_turn(agent, st.session_state["thread_id"], "approved")
                st.session_state["pending_card"] = None
                st.rerun()  # rerun 后历史从 checkpointer 拉取，自动带出恢复结果
        with col2:
            if st.button("❌ 拒绝", key="deny", use_container_width=True):
                resume_turn(agent, st.session_state["thread_id"], "denied")
                st.session_state["pending_card"] = None
                st.rerun()


# ─── 聊天输入：发消息 → run_turn → 可能暂停 ───────────────
if question := st.chat_input("问产品/查订单/申请退款…（例：我要退 SO-1003，质量问题）"):
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            result = run_turn(agent, st.session_state["thread_id"], question)
            if result["pending"] is not None:
                # 图暂停：存卡片，rerun 后上方渲染审批按钮
                st.session_state["pending_card"] = result["pending"]
                st.info("⏸ 已触发退款审批，等待客服经理决定…")
                st.rerun()
            elif result["text"]:
                st.markdown(result["text"])
        except Exception as e:
            st.error(f"调用失败：{type(e).__name__}: {e}")
