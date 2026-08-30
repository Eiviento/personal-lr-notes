"""
Phase 5.1 升级版：对话式协议助手（聊天窗口）
============================================
从"上传→按钮→出结果"升级为聊天窗口。三零件（详见 lessons/extra_chat_agent.md）：
  - 会话历史：st.session_state["messages"]（重跑不丢）
  - agent 循环：scripts/chat_agent.py 的 build_chat_agent()（create_react_agent）
  - 聊天 UI：st.chat_message 渲染历史 + st.chat_input 输入 + st.write_stream 打字机

薄壳原则不变：业务逻辑全在 scripts/，这里只有渲染与状态搬运。

运行：
  streamlit run app.py
AppTest 冒烟（假 agent，不真调 API）：
  测试脚本里设环境变量 CHAT_FAKE_AGENT=1（见 scripts/demo_app_test.py）
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from langchain_core.messages import AIMessage, HumanMessage

from chat_agent import (
    FakeAgent,
    build_chat_agent,
    get_last_protocol,
    set_current_doc,
    stream_turn,
)
from generate_protocol import render_markdown


def decode_doc(raw: bytes) -> str:
    """上传文件的编码自适应（同 3.1：utf-8-sig → utf-8 → gb18030）"""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文件编码")


st.set_page_config(page_title="协议助手", page_icon="🤖", layout="wide")
st.title("🤖 协议助手")
st.caption("对话式协议规范助手：可聊天问答；上传需求文档后，说一声就帮你生成协议")


@st.cache_resource(show_spinner="加载模型组件中...")
def get_agent():
    """agent 是昂贵资源，缓存后重跑不重建；AppTest 冒烟走假 agent"""
    if os.getenv("CHAT_FAKE_AGENT") == "1":
        return FakeAgent()
    return build_chat_agent()


agent = get_agent()

# ─── 历史初始化（重跑不丢） ──────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ─── 上传：文档注入 chat_agent 模块，工具自己读 ────────
uploaded = st.file_uploader("上传需求文档（.md / .txt，可随时换、随时传）", type=["md", "txt"])
if uploaded is not None and uploaded.getvalue():
    set_current_doc(decode_doc(uploaded.getvalue()))
    st.info(f"已加载文档：{uploaded.name}。现在可以说\"帮我生成协议\"，或直接问问题。")

# ─── 历史气泡渲染 ────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg.type):
        st.markdown(msg.content)

# ─── 输入：追加历史 → 流式回答 → 追加回答 ──────────────
if question := st.chat_input("问我协议问题，或说\"帮我生成协议\""):
    st.session_state["messages"].append(HumanMessage(question))
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        full = ""
        try:
            full = st.write_stream(stream_turn(agent, st.session_state["messages"]))
        except Exception as e:
            st.error(f"调用失败：{e}")
        if full:
            st.session_state["messages"].append(AIMessage(full))

# ─── 侧栏：生成过协议后出现下载按钮 ────────────────────
with st.sidebar:
    st.header("📦 产物")
    last = get_last_protocol()
    if last is None:
        st.write("生成协议后，这里出现下载按钮")
    else:
        st.write(f"协议《{last.get('protocol_name', '未命名')}》")
        st.download_button("⬇ 下载 JSON（草稿）", json.dumps(last, ensure_ascii=False, indent=2),
                           file_name="protocol_draft.json", mime="application/json")
        st.download_button("⬇ 下载 Markdown（草稿）", render_markdown(last),
                           file_name="protocol_draft.md", mime="text/markdown")
