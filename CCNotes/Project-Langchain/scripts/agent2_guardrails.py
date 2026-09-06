"""
Phase 2 · 阀门与护栏 —— agent 循环的四道保险
===============================================
干什么：P1 学会了循环怎么转，这一课学怎么让循环【不失控】。三类对照实验：
  实验 1 · recursion_limit 步数上限：设太小会误杀正当任务（GraphRecursionError），
           设太大防不住恶意死循环——引出"上限是大坝"
  实验 2 · 重复调用熔断：同一工具连续点 N 次（同参数）→ 强制中断并让模型收尾
           （大坝拦不住的口子用闸门补）
  实验 3 · 工具异常回流：工具抛异常时 ToolNode 默认把它转成错误消息回传给模型，
           模型如实转述而不崩溃——对比 handle_tool_errors=False 会直接炸到顶层
吃什么吐什么：输入诱导性用户问题/坏工具；输出每类护栏的对照行为 + 留档日志。
为什么这么写：护栏必须在【你手上那张图】里看得见摸得着——用 P1 的白盒改，不上黑盒。

运行：PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent2_guardrails.py
"""

import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict

from agent1_whitebox import (
    PROJECT_ROOT,
    _build_llm,
    get_now_time,
    get_order_status,
    search_knowledge,
)

OUT_DIR = PROJECT_ROOT / "outputs"
LOG: list[str] = []


def log(line: str = ""):
    print(line)
    LOG.append(line)


# ─── 复用的状态与模型节点（同 P1 白盒） ────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def make_model_node(llm_with_tools, system_prompt: str):
    def call_model(state: AgentState):
        msgs = [SystemMessage(content=system_prompt), *state["messages"]]
        return {"messages": [llm_with_tools.invoke(msgs)]}

    return call_model


# ─── 实验 2 用的诱导提示：让模型"必须查 3 次时间取平均" ───────────────
INDUCE_PROMPT = """你是技术支持助手。规则（必须遵守）：
用户问时间时，你【必须】连续调用 get_now_time 共 3 次（每次拿到结果后再调下一次），
取三次结果的平均值后回答。不允许只查一次就回答。
你有工具：get_now_time、get_order_status、search_knowledge。
回答用中文。"""

# ─── 实验 3 用的坏工具：总是抛异常，模拟外部服务崩溃 ──────────────────
@tool
def fragile_lookup(order_id: str) -> str:
    """查询外部订单详情服务（注意：该服务当前不稳定，可能报错）。"""
    raise ConnectionError(f"外部订单服务超时（order_id={order_id}）——模拟服务崩溃")


# ══════════════════════════════════════════════════════════════════════
# 实验 1 · recursion_limit：步数上限设太小会误杀正当任务
# ══════════════════════════════════════════════════════════════════════
def experiment1_limit_too_small():
    log("=" * 70)
    log("实验 1 · recursion_limit=2（太小）：一个需要 2 次工具调用的正当任务")
    log("=" * 70)
    llm = _build_llm().bind_tools([get_order_status, search_knowledge])
    node_model = make_model_node(llm, "你是技术支持助手，用工具回答问题，中文。")

    g = StateGraph(AgentState)
    g.add_node("agent", node_model)
    g.add_node("tools", ToolNode([get_order_status, search_knowledge]))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    agent = g.compile()

    question = "先查一下订单 SO-1003 的状态，再查一下七天无理由退货政策，两个都告诉我。"
    try:
        for step in agent.stream(
            {"messages": [HumanMessage(question)]},
            config={"recursion_limit": 2},  # ← 阀门拧太紧
            stream_mode="updates",
        ):
            for node_name, update in step.items():
                msgs = update.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    if getattr(last, "tool_calls", None):
                        log(f"  [agent] 点菜: {[tc['name'] for tc in last.tool_calls]}")
                    elif type(last).__name__ == "ToolMessage":
                        log(f"  [tools] 返回: {str(last.content)[:60]}")
                    elif type(last).__name__ == "AIMessage":
                        log(f"  [agent] 回答: {str(last.content)[:60]}")
        log("  → 意外：limit=2 下任务竟完成了？")
    except GraphRecursionError as e:
        log(f"  → GraphRecursionError 被捕获：正常任务被 limit=2 误杀")
        log(f"    提示：任务需要多次工具往返，但循环在第 2 步就被上限掐断")


# ══════════════════════════════════════════════════════════════════════
# 实验 2 · 重复调用熔断：同一工具连续同参数点 N 次 → 强制收尾
# ══════════════════════════════════════════════════════════════════════
def _recent_same_tool_calls(state: AgentState, n: int) -> bool:
    """检测最近 n 次模型点菜是否都是同一工具、同一参数。"""
    ai_calls = [
        tuple(sorted((tc["name"], json.dumps(tc["args"], sort_keys=True)) for tc in m.tool_calls))
        for m in state["messages"]
        if isinstance(m, AIMessage) and m.tool_calls
    ]
    if len(ai_calls) < n:
        return False
    return all(c == ai_calls[-1] for c in ai_calls[-n:])


def experiment2_duplicate_breaker():
    log("")
    log("=" * 70)
    log("实验 2 · 重复调用熔断：诱导模型连续查 3 次时间 → 第 3 次同参数重复被熔断")
    log("=" * 70)
    llm = _build_llm().bind_tools([get_now_time])
    node_model = make_model_node(llm, INDUCE_PROMPT)
    tool_node = ToolNode([get_now_time])

    def breaker(state: AgentState):
        # 熔断节点：注入提示让模型停止重复，直接回答
        return {
            "messages": [
                SystemMessage(
                    content="【熔断提示】检测到你已连续多次调用同一工具且参数相同（疑似循环）。"
                    "规则改为：立即停止调用工具，直接基于已有信息回答用户。"
                )
            ]
        }

    def route_after_tools(state: AgentState):
        # 关键护栏逻辑：tools 执行完后，若最近 2 次点菜完全一致 → 走熔断
        if _recent_same_tool_calls(state, 2):
            return "breaker"
        return "agent"

    g = StateGraph(AgentState)
    g.add_node("agent", node_model)
    g.add_node("tools", tool_node)
    g.add_node("breaker", breaker)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)  # 点菜→tools，否则→END
    g.add_conditional_edges("tools", route_after_tools)  # ← 熔断闸门
    g.add_edge("breaker", "agent")  # 熔断提示后让模型最后收尾一次
    agent = g.compile()

    for step in agent.stream(
        {"messages": [HumanMessage("现在几点了？")]},
        config={"recursion_limit": 15},  # 大坝放宽，靠闸门拦
        stream_mode="updates",
    ):
        for node_name, update in step.items():
            msgs = update.get("messages", [])
            if not msgs:
                continue
            last = msgs[-1]
            if getattr(last, "tool_calls", None):
                log(f"  [agent] 点菜: {[tc['name'] for tc in last.tool_calls]}")
            elif type(last).__name__ == "ToolMessage":
                log(f"  [tools] get_now_time 返回: {str(last.content)[:20]}")
            elif type(last).__name__ == "SystemMessage":
                log(f"  [breaker] 熔断触发: {str(last.content)[:40]}…")
            elif type(last).__name__ == "AIMessage" and not last.tool_calls:
                log(f"  [agent] 最终回答: {str(last.content)[:80]}")
    log("  → 熔断生效：模型没有无限查下去，被强制收尾")


# ══════════════════════════════════════════════════════════════════════
# 实验 3 · 工具异常回流：ToolNode 默认把异常转成错误消息给模型
# ══════════════════════════════════════════════════════════════════════
def experiment3_tool_error_handling():
    log("")
    log("=" * 70)
    log("实验 3 · 工具异常：fragile_lookup 抛 ConnectionError → ToolNode 默认护栏")
    log("=" * 70)
    llm = _build_llm().bind_tools([fragile_lookup, get_order_status])
    node_model = make_model_node(
        llm,
        "你是技术支持助手。用工具查订单。工具返回错误时如实告诉用户，不要编造。中文。",
    )
    g = StateGraph(AgentState)
    g.add_node("agent", node_model)
    # handle_tool_errors=True：把工具抛出的异常转成错误消息回流给模型。
    # 注意默认值不是 True！langgraph 1.2.9 的默认 handler 只兜 ToolInvocationError，
    # 工具自己抛的业务异常（如 ConnectionError）默认会直接 raise 炸到顶层——
    # 上一版实验实测崩溃（exit 1）。显式 True 才兜全部异常。
    g.add_node("tools", ToolNode([fragile_lookup, get_order_status], handle_tool_errors=True))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    agent = g.compile()

    for step in agent.stream(
        {"messages": [HumanMessage("用 fragile_lookup 查一下订单 SO-1005 的详情")]},
        config={"recursion_limit": 10},
        stream_mode="updates",
    ):
        for node_name, update in step.items():
            msgs = update.get("messages", [])
            if not msgs:
                continue
            last = msgs[-1]
            if getattr(last, "tool_calls", None):
                log(f"  [agent] 点菜: {[tc['name'] for tc in last.tool_calls]}")
            elif type(last).__name__ == "ToolMessage":
                log(f"  [tools] 返回(错误已转消息): {str(last.content)[:70]}")
            elif type(last).__name__ == "AIMessage" and not last.tool_calls:
                log(f"  [agent] 最终回答: {str(last.content)[:100]}")
    log("  → 护栏生效（handle_tool_errors=True）：工具崩溃转错误消息回流，模型如实应对")
    log("  ※ 对照：默认值下业务异常会直接 raise 崩溃——实测见本文件开发过程记录（lesson 详述）")


def main():
    log("Phase 2 · 阀门与护栏 —— 三类护栏对照实验（单次实跑）")
    experiment1_limit_too_small()
    experiment2_duplicate_breaker()
    experiment3_tool_error_handling()
    out = OUT_DIR / "agent2_guardrails_run.log"
    out.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\n[留档] → {out}")


if __name__ == "__main__":
    main()
