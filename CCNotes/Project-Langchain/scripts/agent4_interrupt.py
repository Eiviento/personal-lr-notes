"""
Phase 4 · 可靠性与人在回路 —— interrupt 人工审批 + 防幻觉验证节点
===================================================================
核心论断先行：
  (1) 人在回路：写操作（退款）不能让 agent 自己拍板，要在【真正执行前】停下
      等外部（人）批准。LangGraph 用 interrupt 原语实现——图跑到审批点暂停，
      返回待审快照；外部决定后用 Command(resume=...) 从断点恢复继续。
  (2) 防幻觉纵深：模型会编造"听起来对"的内容（坑 #18 已证）。纵深防御 =
      加【验证节点】：模型输出里的关键事实(订单号/金额)交给工具核对，
      对不上就拦截修正——事实只信工具，不信模型的嘴。

两个实验全部零 API（确定性演示机制本身）：
  实验 1 · 退款审批：request_refund → 审批点 interrupt（暂停）→
           外部批准/拒绝 → resume 恢复 → 执行退款 or 告知拒绝
  实验 2 · 防幻觉：FakeLLM 编造订单号 → 验证节点用 get_order_status 核对
           → 编造的"已退款"被拦截修正（对照：无验证节点时编造直接通过）

运行：PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent4_interrupt.py
"""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing import TypedDict

from agent1_whitebox import get_order_status

SEP = "─" * 66


class RefundState(TypedDict):
    """退款审批图的共享状态。"""
    order_id: str
    reason: str
    history: list          # 记录流程每一步（用于展示）
    decision: str          # 外部审批结果（approved / denied）


def log(state, entry):
    return {"history": state["history"] + [entry]}


def make_refund_graph():
    """退款审批图：collect → approval(interrupt) → finalize。"""

    def collect(state: RefundState):
        print(f"  ① 收集退款请求: 订单 {state['order_id']}，理由「{state['reason']}」")
        return log(state, f"请求退款 {state['order_id']}")

    def approval(state: RefundState):
        # ★ interrupt：图停在这里，把待审信息抛给外部，等 resume 值
        decision = interrupt({
            "type": "refund_approval",
            "order_id": state["order_id"],
            "reason": state["reason"],
        })
        # 恢复后：interrupt() 返回外部给的 resume 值
        return {"decision": decision}

    def finalize(state: RefundState):
        if state.get("decision") == "approved":
            print(f"  ③ 批准 → 真正执行退款: {state['order_id']} 已退款（模拟写操作）")
            return log(state, "退款已执行")
        print(f"  ③ 拒绝 → 不执行退款: 告知用户审批未通过")
        return log(state, "退款被拒绝")

    g = StateGraph(RefundState)
    g.add_node("collect", collect)
    g.add_node("approval", approval)
    g.add_node("finalize", finalize)
    g.add_edge(START, "collect")
    g.add_edge("collect", "approval")
    g.add_edge("approval", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=MemorySaver())


def submit_and_decide(thread_id, order_id, reason, decision):
    """第一次 invoke 触发审批（会暂停）→ 打印待审快照 → 外部决定 → resume。"""
    app = make_refund_graph()
    cfg = {"configurable": {"thread_id": thread_id}}
    print(f"\n[用户] 申请退款：{order_id}（理由：{reason}）")
    out = app.invoke({"order_id": order_id, "reason": reason, "history": []}, config=cfg)
    # 暂停点：state 里的 __interrupt__ 就是要给外部(人)审批的内容
    pending = out.get("__interrupt__", [])
    payload = pending[0].value if pending else None
    print(f"  ② ⏸ 图暂停在审批点，待审快照: {payload}")
    print(f"  [外部审批者 客服经理] 决定：{decision}")
    out2 = app.invoke(Command(resume=decision), config=cfg)
    print(f"  流程历史: {out2['history']}")


# ─── 实验 2：防幻觉验证节点 ────────────────────────────────────────────
def experiment2_anti_hallucination():
    print()
    print(SEP)
    print("实验 2 · 防幻觉验证节点：模型编造「已退款」，验证节点用工具核对拦截")
    print(SEP)

    class AnswerState(TypedDict):
        model_text: str     # 模型(FakeLLM)生成的回答
        verified: str       # 验证后的最终回答
        order_id: str

    def fake_llm_generate(state: AnswerState):
        # FakeLLM 生成一段"编造"的回答：声称订单已退款——但库里根本没这笔退款记录
        text = f"订单 {state['order_id']} 已经为您办理退款了，金额 399 元，请放心。"
        print(f"  [模型生成] {text}")
        return {"model_text": text}

    def verify_node(state: AnswerState):
        # ★ 验证节点：把模型回答里的"事实主张"拿去工具核对
        # 主张1: 该订单存在且状态允许退；主张2: 声称已退款 → 用工具查真实状态
        real = get_order_status.invoke({"order_id": state["order_id"]})
        if "未找到" in real:
            verdict = f"【验证拦截】订单 {state['order_id']} 根本不存在——模型编造了订单号。已改为如实答复。"
        elif "refunded" in real or "已退款" in real:
            verdict = f"【验证通过】订单确实已退款。{state['model_text']}"
        else:
            verdict = (f"【验证拦截】工具显示订单 {state['order_id']} 状态未退款（真实状态见下）"
                       f"——模型声称已退款是编造。已改为如实转述工具结果。\n  工具返回: {real.splitlines()[1] if len(real.splitlines())>1 else real}")
        print(f"  {verdict}")
        return {"verified": verdict}

    # 场景 A：模型对"不存在订单"声称已退款（编造订单号）
    print("\n场景 A · 编造订单号：模型对 SO-0000 声称已退款")
    g = StateGraph(AnswerState)
    g.add_node("generate", fake_llm_generate)
    g.add_node("verify", verify_node)
    g.add_edge(START, "generate")
    g.add_edge("generate", "verify")
    g.add_edge("verify", END)
    app = g.compile()
    out = app.invoke({"model_text": "", "verified": "", "order_id": "SO-0000"})
    print(f"  最终答复给用户: {out['verified'][:60]}…")

    # 场景 B：真实存在的已送达订单，模型仍声称"已退款"（编造动作）
    print("\n场景 B · 存在但未退款：模型对 SO-1003 声称已退款")
    out = app.invoke({"model_text": "", "verified": "", "order_id": "SO-1003"})
    print(f"  最终答复给用户: {out['verified'][:80]}…")


def main():
    print("Phase 4 · 可靠性与人在回路（零 API 演示，单次实跑）")
    print(SEP)
    print("实验 1 · interrupt 退款审批：批准 vs 拒绝 两分支")
    print(SEP)
    submit_and_decide("refund-a", "SO-1003", "商品质量问题", "approved")
    submit_and_decide("refund-b", "SO-1001", "我不想要了", "denied")
    experiment2_anti_hallucination()


if __name__ == "__main__":
    main()
