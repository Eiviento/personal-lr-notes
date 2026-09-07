"""
Phase 6 · 规模化与版本演进 —— V2 迁移 + subgraph 子图
======================================================
两个主题：
  Part A · 版本演进：create_react_agent 被弃用（V1.0 标记，V2.0 移除），官方迁往
           `langchain.agents.create_agent`。同一模型同一工具，V1 与 V2 对照跑——
           看"迁移 = 换 import + prompt 参数改名 system_prompt"，V2 不再打弃用警告。
  Part B · 规模化：subgraph（子图）——把一小段流程编译成独立小图，当节点嵌进大图。
           客服主图 = 分类节点(路由) → 调用订单子图 / 知识子图 → 汇总。
           子图是独立编译的 StateGraph，可单独测试、可复用、可嵌任意父图。

运行：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent6_scale.py
  （Part A 需 .env key 真实 API 两次小对话；Part B 零 API）
"""

import sys
import warnings
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from typing import TypedDict

from agent1_whitebox import _build_llm, get_order_status, search_knowledge

SEP = "─" * 66
TOOLS = [search_knowledge, get_order_status]
PROMPT = """你是 SmartHome 技术支持客服助手。有工具：search_knowledge(知识库)、get_order_status(查单)。
政策/故障先检索知识库；给订单号就查单。中文简洁。"""


# ═══════════ Part A · V1 vs V2 版本迁移对照（真实 API 两次小对话）═══════════
def build_v1():
    """旧版：langgraph.prebuilt.create_react_agent + prompt= 参数。"""
    from langgraph.prebuilt import create_react_agent

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = create_react_agent(model=_build_llm(), tools=TOOLS, prompt=PROMPT)
        dep = [str(w.message).split("\n")[0][:70] for w in caught if "Deprecat" in str(w.message)]
    return agent, dep


def build_v2():
    """新版：langchain.agents.create_agent + system_prompt= 参数（迁移目标）。"""
    from langchain.agents import create_agent

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = create_agent(model=_build_llm(), tools=TOOLS, system_prompt=PROMPT)
        dep = [str(w.message).split("\n")[0][:70] for w in caught if "Deprecat" in str(w.message)]
    return agent, dep


def run_and_show(agent, question):
    out = agent.invoke({"messages": [HumanMessage(question)]})
    for m in reversed(out["messages"]):
        if hasattr(m, "content") and m.content and not getattr(m, "tool_calls", None):
            return str(m.content)[:70]
    return "(无文本回答)"


def part_a_migration():
    print(SEP)
    print("Part A · 版本演进：create_react_agent(V1) → create_agent(V2) 迁移对照")
    print(SEP)
    q = "帮我查一下订单 SO-1003 到哪了？"
    a1, dep1 = build_v1()
    print(f"V1 构建弃用警告: {len(dep1)} 条" + (f" 例: {dep1[0]}" if dep1 else ""))
    print(f"V1 回答: {run_and_show(a1, q)}")
    a2, dep2 = build_v2()
    print(f"V2 构建弃用警告: {len(dep2)} 条" + (f" 例: {dep2[0]}" if dep2 else ""))
    print(f"V2 回答: {run_and_show(a2, q)}")
    print("→ 同模型同工具同人设，V1/V2 都能跑；差异只在：导入路径 + prompt→system_prompt 参数名")
    print("  源码对照：from langgraph.prebuilt import create_react_agent → from langchain.agents import create_agent")


# ═══════════ Part B · subgraph：子图嵌进父图（零 API）══════════════════
class OrderState(TypedDict):
    order_id: str
    result: str


def build_order_subgraph():
    """订单子图：吃 order_id，吐订单状态文本（独立可测的小图）。"""

    def lookup(state: OrderState):
        return {"result": get_order_status.invoke({"order_id": state["order_id"]}).splitlines()[0]}

    g = StateGraph(OrderState)
    g.add_node("lookup", lookup)
    g.add_edge(START, "lookup")
    g.add_edge("lookup", END)
    return g.compile()


class KnowledgeState(TypedDict):
    query: str
    result: str


def build_knowledge_subgraph():
    """知识子图：吃 query，吐知识库命中第一条标题（独立可测的小图）。"""

    def retrieve(state: KnowledgeState):
        return {"result": search_knowledge.invoke({"query": state["query"]}).split("\n")[0]}

    g = StateGraph(KnowledgeState)
    g.add_node("retrieve", retrieve)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", END)
    return g.compile()


class ParentState(TypedDict):
    """客服主图状态：输入 user_input，路由后各子图写回自己的结果。"""
    user_input: str
    kind: str
    order_result: str
    knowledge_result: str


def part_b_subgraph():
    print()
    print(SEP)
    print("Part B · subgraph：客服主图 = 分类节点 → 路由到 订单子图/知识子图")
    print(SEP)
    order_sub = build_order_subgraph()
    knowledge_sub = build_knowledge_subgraph()

    def classify(state: ParentState):
        # 纯函数路由：含"订单/SO-"→ order；含"怎么/政策/退"→ knowledge
        kind = "order" if ("SO-" in state["user_input"] or "订单" in state["user_input"]) else "knowledge"
        print(f"  [classify] 输入「{state['user_input'][:18]}」→ 判定走 {kind} 子图")
        return {"kind": kind}

    def to_order(state: ParentState):
        # 子图当节点：把父状态字段喂给子图.invoke，取回结果
        out = order_sub.invoke({"order_id": "SO-1003"})
        return {"order_result": out["result"]}

    def to_knowledge(state: ParentState):
        out = knowledge_sub.invoke({"query": "七天无理由退货"})
        return {"knowledge_result": out["result"]}

    def route(state: ParentState):
        return "order" if state["kind"] == "order" else "knowledge"

    p = StateGraph(ParentState)
    p.add_node("classify", classify)
    p.add_node("order", to_order)
    p.add_node("knowledge", to_knowledge)
    p.add_edge(START, "classify")
    p.add_conditional_edges("classify", route)
    p.add_edge("order", END)
    p.add_edge("knowledge", END)
    parent = p.compile()

    for q in ["我的订单 SO-1003 在哪？", "七天无理由退货怎么算？"]:
        out = parent.invoke({"user_input": q, "kind": "", "order_result": "", "knowledge_result": ""})
        hit = out["order_result"] or out["knowledge_result"]
        print(f"  [主图] 用户问「{q[:14]}…」→ 子图结果: {hit}")
    print("→ 主图节点 order/knowledge 内部各是一个独立编译的 StateGraph（子图）")
    print("  子图可单独测试/复用；父图只把子图当『黑盒节点』调用——规模化拆分的标准手法")


def main():
    print("Phase 6 · 规模化与版本演进（Part A 真实 API 两次小对话；Part B 零 API）")
    part_a_migration()
    part_b_subgraph()


if __name__ == "__main__":
    main()
