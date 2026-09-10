"""
Phase 7 · 客服工作台 —— 把 6 个机制拼成可交互系统（业务后端，headless 可测）
=============================================================================
核心论断先行：
  (1) web 无状态 ≠ agent 无记忆。Streamlit 每次交互都重跑脚本（无状态请求），
      LangGraph agent 却可能跑一半停在 interrupt 等人审批（长时运行）。
      桥 = thread_id：UI 只搬运 thread_id 与每轮增量，历史/暂停全由
      checkpointer 持有——"checkpointer 即真相源"，不是 st.session_state。
  (2) 6 个 Phase 的机制第一次在同一个图上协同：记忆(checkpointer) +
      工具(agent1 复用) + 审批(工具内 interrupt) + V2 create_agent(agent6)。

本文件 = 业务层：不含任何 UI 代码，headless 可测（self-test main 零 API）。
  app.py（Streamlit 薄壳）只 import 这里的函数做渲染与状态搬运。

关键 API（V2 时代，agent_env 实测，见 docs/findings F8）：
  - langchain.agents.create_agent(model, tools, system_prompt=, checkpointer=)
  - 工具函数内直接 interrupt({...}) → 图暂停，invoke 返回 __interrupt__
  - Command(resume=...) 同 thread 再 invoke → 从断点恢复，interrupt() 返回 resume 值

运行：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent7_webapp.py    # self-test（零 API）
"""

import json
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langchain.agents import create_agent

from agent1_whitebox import (
    _build_llm,
    get_now_time,
    get_order_status,
    search_knowledge,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")

# ─── 已批准退款登记（模拟写操作落库；不真改 data\orders.json，避免污染共享数据）───
_REFUNDED: dict[str, str] = {}  # order_id -> "approved"/"denied"


# ─── 新增工具 4：申请退款（写操作 → 工具内 interrupt 等人批）────────────
@tool
def request_refund(order_id: str, reason: str) -> str:
    """申请订单退款（写操作，需人工审批）。用户要求退款/退货/不想要了时调用，
    传订单号(order_id 形如 SO-1003)与理由(reason)。注意：工具会暂停等待客服经理
    审批，不要自行宣称退款成功。"""
    # 1. 订单存在性 + 可退资格核对（事实只信数据，不信模型的嘴——P4 纵深）
    data = json.loads((DATA_DIR / "orders.json").read_text(encoding="utf-8"))
    order = None
    for o in data["orders"]:
        if o["order_id"].upper() == order_id.strip().upper():
            order = o
            break
    if order is None:
        return f"退款申请失败：订单 {order_id} 不存在，请先核对订单号。"
    if not order.get("refund_eligible"):
        return f"退款申请失败：订单 {order_id}（{order['product']}）当前不符合退款条件（已发货/已送达且超期等），请如实告知用户。"

    # 2. 写操作 → 停在这里等人批（★ 本 Phase 核心：工具内 interrupt）
    decision = interrupt({
        "type": "refund_approval",
        "order_id": order_id,
        "product": order["product"],
        "price": order["price"],
        "reason": reason,
    })

    # 3. 外部 resume 后恢复执行
    if decision == "approved":
        _REFUNDED[order_id] = "approved"
        return f"退款已执行：订单 {order_id}（{order['product']}）{order['price']} 元已原路退回。"
    _REFUNDED[order_id] = "denied"
    return f"退款未通过审批：订单 {order_id}。请如实告知用户审批未通过及原因。"


DEFAULT_TOOLS = [search_knowledge, get_order_status, get_now_time, request_refund]

# ─── 系统提示词（继承 agent1 四要素 + 新增退款工具规则）─────────────────
SYSTEM_PROMPT = """你是 SmartHome 智能家居产品的技术支持客服助手。

你的能力：
1. 用 search_knowledge 检索产品知识库（退换货/保修/连接/固件等政策与排查）
2. 用 get_order_status 查询订单状态（用户给订单号时）
3. 用 get_now_time 告知当前时间
4. 用 request_refund 帮用户申请退款（写操作，会暂停等待客服经理人工审批）

规则：
- 用户问政策/故障类问题先调 search_knowledge，用检索结果回答，不要凭印象编
- 用户查订单先要订单号（形如 SO-1001），拿到就调 get_order_status
- 用户明确要退款/退货时：先取订单号与理由 → 调 request_refund；工具会暂停等人批，
  审批结果出来后如实转述（"已批准"或"未通过"），不要替审批者做决定
- 工具返回"未找到/不存在/未通过"时，如实转述并请用户核对，不要编造订单、政策或退款结果
- 回答用中文，简洁，需要时列要点
"""


# ─── 组装：V2 create_agent + checkpointer（记忆与审批的前提）──────────
def build_agent(llm=None, checkpointer=None):
    """V2 主图。checkpointer 一石二鸟：同 thread 记住对话（P3）+ interrupt 暂停点依赖它（P4）。
    llm 传 None 用真实 DeepSeek；FakeLLM 传入则零 API。"""
    return create_agent(
        model=llm if llm is not None else _build_llm(),
        tools=DEFAULT_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer if checkpointer is not None else MemorySaver(),
    )


# ─── 一轮对话封装：invoke + __interrupt__ 检测 ────────────────────────
def _cfg(thread_id: str):
    return {"configurable": {"thread_id": thread_id}}


def _final_text(out: dict) -> str:
    """从 invoke 返回的 state 里取最后一个 AI 文本答复。"""
    for m in reversed(out.get("messages", [])):
        if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
            return str(m.content)
    return ""


def _pending_approval(out: dict) -> dict | None:
    """取暂停点快照：有 __interrupt__ 且是退款审批 → 返回待审信息 dict。"""
    for it in out.get("__interrupt__", []):
        val = getattr(it, "value", None)
        if isinstance(val, dict) and val.get("type") == "refund_approval":
            return val
    return None


def run_turn(agent, thread_id: str, text: str) -> dict:
    """用户发一条消息 → 跑一轮。返回：
      {text: 最终答复, pending: 待审快照或 None, history: 当前全部消息}
    若 pending 非 None：图已暂停，等外部批准/拒绝后调 resume_turn。"""
    out = agent.invoke({"messages": [HumanMessage(content=text)]}, config=_cfg(thread_id))
    return {
        "text": _final_text(out),
        "pending": _pending_approval(out),
        "history": out.get("messages", []),
    }


def resume_turn(agent, thread_id: str, decision: str) -> dict:
    """外部(人)对暂停点做决定 → Command(resume) 同 thread 恢复。decision: approved/denied"""
    out = agent.invoke(Command(resume=decision), config=_cfg(thread_id))
    return {
        "text": _final_text(out),
        "pending": _pending_approval(out),
        "history": out.get("messages", []),
    }


def get_history(agent, thread_id: str) -> list:
    """从 checkpointer 拉该 thread 当前全部消息（UI 重跑后恢复渲染用——真相在 checkpointer）。"""
    try:
        state = agent.get_state(_cfg(thread_id))
        return state.values.get("messages", [])
    except Exception:  # 无该 thread 的检查点
        return []


# ─── FakeAgent：AppTest 冒烟替身（不真调 API，模拟 .invoke/.get_state 形状）───
class FakeAgent:
    """零 API 假 agent：规则式应答 + 一次可触发的暂停路径。
    冒烟目标：UI 机制不崩（渲染/历史累积/审批卡片出现），非 agent 行为本身。"""

    def __init__(self):
        self.mem: dict[str, list] = {}  # thread_id -> [HumanMessage, AIMessage, ...]

    def invoke(self, inputs, config=None):
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
        msgs = self.mem.setdefault(thread_id, [])
        if isinstance(inputs, Command):
            # resume 分支：上一次的 pending 审批
            decision = inputs.resume
            verdict = "已批准" if decision == "approved" else "未通过审批"
            msgs.append(AIMessage(content=f"（假agent）退款申请{verdict}：订单 SO-1003 已按您的决定处理。"))
            return {"messages": list(msgs), "__interrupt__": []}
        text = inputs["messages"][-1].content
        msgs.append(HumanMessage(content=text))
        if "退款" in text or "退" in text and "SO-" in text:
            # 触发一次可审批的暂停（模拟真 agent 调 request_refund 后 interrupt）
            pending = {"type": "refund_approval", "order_id": "SO-1003",
                       "product": "温湿度传感器", "price": 89, "reason": "质量问题"}
            return {"messages": list(msgs), "__interrupt__": [type("I", (), {"value": pending})()]}
        msgs.append(AIMessage(content=f"（假agent）已收到：{text[:30]}"))
        return {"messages": list(msgs), "__interrupt__": []}

    def get_state(self, config=None):
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
        return type("S", (), {"values": {"messages": self.mem.get(thread_id, [])}})()


# ─── FakeLLM：self-test 用规则模型（零 API，驱动真图验证机制）───────────
class FakeLLM:
    """在真实 V2 图上跑零 API 自测。规则：
      - 消息历史里有 request_refund 的 ToolMessage 且含"已执行/未通过" → 收敛给最终答复
      - 用户话含"SO-"且含"退" → 点菜 request_refund（走 interrupt 全链路）
      - 用户话含"SO-" → 点菜 get_order_status
      - 用户话含"时间/几点" → 点菜 get_now_time
      - 其余直接答复
    """

    def __init__(self, name="FakeLLM"):
        self.name = name

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages, **kwargs):
        from langchain_core.messages import ToolMessage
        # 收敛检查：最近一条是工具结果（任一工具跑完）→ 基于结果总结给用户，不再点菜
        last = messages[-1] if messages else None
        if isinstance(last, ToolMessage):
            name = getattr(last, "name", "?")
            content = str(last.content)[:60]
            if name == "request_refund":
                return AIMessage(content=f"您的退款申请处理结果：{content}（已如实转述工具结果）")
            return AIMessage(content=f"查询结果：{content}")
        last_text = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_text = str(m.content)
                break
        if "SO-" in last_text and ("退" in last_text or "款" in last_text):
            return AIMessage(content="", tool_calls=[{"name": "request_refund",
                                                       "args": {"order_id": "SO-1003", "reason": "商品质量问题"},
                                                       "id": "tc-refund", "type": "tool_call"}])
        if "SO-" in last_text:
            return AIMessage(content="", tool_calls=[{"name": "get_order_status",
                                                       "args": {"order_id": "SO-1003"},
                                                       "id": "tc-order", "type": "tool_call"}])
        return AIMessage(content=f"（{self.name}）已收到：{last_text[:40]}")


# ─── self-test main（零 API，驱动真 V2 图验证两条机制链）────────────────
def self_test():
    SEP = "─" * 66
    print("Phase 7 self-test · 零 API（FakeLLM 驱动真实 V2 图，验证机制链）")
    print(SEP)
    print("链路 1 · 记忆：同 thread 两轮，checkpointer 累积消息")
    print(SEP)
    agent = build_agent(llm=FakeLLM())
    t = "st-thread-1"
    r1 = run_turn(agent, t, "你好")
    print(f"  第 1 轮后 history {len(r1['history'])} 条: {r1['text'][:30]}")
    r2 = run_turn(agent, t, "我的订单 SO-1003 到哪了？")
    print(f"  第 2 轮后 history {len(r2['history'])} 条（应 > 第 1 轮 → 记忆累积）")
    assert len(r2["history"]) > len(r1["history"]), "记忆累积失败"
    got_status = any(getattr(m, "type", "") == "tool" and getattr(m, "name", "") == "get_order_status"
                     for m in r2["history"])
    assert got_status, "第 2 轮应调用 get_order_status"
    print("  ✓ 同 thread 消息累积 + 工具调用成功")

    print(SEP)
    print("链路 2 · 审批：request_refund → interrupt 暂停 → resume 批准恢复")
    print(SEP)
    t2 = "st-thread-2"
    rr = run_turn(agent, t2, "我要退掉 SO-1003，质量问题")
    print(f"  首轮 text={rr['text'][:30]!r}  pending={rr['pending'] is not None}")
    assert rr["pending"] is not None, "应触发审批暂停"
    assert rr["pending"]["order_id"] == "SO-1003"
    print(f"  待审快照: order={rr['pending']['order_id']} reason={rr['pending']['reason']}")
    # 批准分支
    ok = resume_turn(agent, t2, "approved")
    print(f"  resume(approved) → {ok['text'][:60]}")
    assert "已执行" in ok["text"] or "退款" in ok["text"], "批准后应执行退款"
    assert _REFUNDED.get("SO-1003") == "approved", "退款登记应为 approved"
    print("  ✓ interrupt 暂停 → 批准恢复 → 退款登记 approved")

    print(SEP)
    print("链路 3 · 审批拒绝分支 + 新 thread 隔离")
    print(SEP)
    t3 = "st-thread-3"
    r3 = run_turn(agent, t3, "我要退掉 SO-1003，不想要了")
    assert r3["pending"] is not None, "应再次触发审批暂停"
    denied = resume_turn(agent, t3, "denied")
    print(f"  resume(denied) → {denied['text'][:60]}")
    assert "未通过" in denied["text"], "拒绝后应告知未通过"
    assert _REFUNDED.get("SO-1003") == "denied", "登记应被覆盖为 denied"
    print("  ✓ 拒绝分支：不执行退款，如实告知")

    # 新 thread 看不到旧 thread 消息（会话隔离）
    t4 = "st-thread-4"
    h4 = get_history(agent, t4)
    assert len(h4) == 0, "新 thread 历史应为空"
    print("  ✓ 新 thread 历史为空（会话隔离成立）")

    print(SEP)
    print(f"self-test 全过：记忆累积 / 审批批准+拒绝 / 会话隔离（exit 0）")
    return 0


def main():
    try:
        sys.exit(self_test())
    except AssertionError as e:
        print(f"[self-test 失败] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
