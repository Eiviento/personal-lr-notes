"""
LangGraph 实操：把 LCEL 直线管道和手写工具循环，改写成"图"
==============================================================
LangChain 的 LCEL 是直线管道，三个做不到：循环 / 条件分支 / 暂停等人工。
LangGraph 用"图"描述流程：State（全局状态）+ Node（节点）+ Edge（边）。

本脚本两个演示：
  Graph A：3.2 的四步链 → 声明成图（直线图，看图和管道的对应关系）
  Graph B：4.2 的手写 while 工具循环 → 声明成 agent 图（条件边 + 循环，
           手写 20 行 while 变成 3 个函数 + 3 条边）

用法：
  python extra_langgraph_intro.py <需求文档>
"""

import json
import sys
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import analyze_chain, fields_chain, rules_chain, merge_final
from phase4_2_tool_calling import FUNC_MAP, llm_with_tools

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# ═══════════════════════════════════════════════════════
# Graph A：四步链 → 直线图
# ═══════════════════════════════════════════════════════
class PipelineState(TypedDict):
    """贯穿全图的状态：节点各自读需要的键、写产出的键"""
    requirement: str
    key_points: str
    fields: dict
    checks: dict
    final: dict


def node_analyze(state: PipelineState) -> dict:
    """节点 = 一个函数，返回部分状态更新（新键或改键）"""
    return {"key_points": analyze_chain.invoke({"requirement": state["requirement"]})}


def node_fields(state: PipelineState) -> dict:
    return {"fields": fields_chain.invoke({"key_points": state["key_points"]})}


def node_rules(state: PipelineState) -> dict:
    return {"checks": rules_chain.invoke(
        {"fields": state["fields"], "key_points": state["key_points"]})}


def node_merge(state: PipelineState) -> dict:
    result = merge_final({"fields": state["fields"], "checks": state["checks"]})
    return {"final": result}


def build_pipeline_graph():
    g = StateGraph(PipelineState)
    g.add_node("analyze", node_analyze)
    g.add_node("fields", node_fields)
    g.add_node("rules", node_rules)
    g.add_node("merge", node_merge)
    # 直线图的边：等价于 LCEL 的 |，但这里每步的"路由"是显式声明的
    g.add_edge(START, "analyze")
    g.add_edge("analyze", "fields")
    g.add_edge("fields", "rules")
    g.add_edge("rules", "merge")
    g.add_edge("merge", END)
    return g.compile()


# ═══════════════════════════════════════════════════════
# Graph B：工具校验循环 → agent 图（条件边 + 循环）
# ═══════════════════════════════════════════════════════
class AgentState(TypedDict):
    """messages 用 Annotated+add：节点返回的新消息是追加，不是替换"""
    messages: Annotated[list, add]


def node_model(state: AgentState) -> dict:
    """模型节点：发消息给带工具的模型"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def node_tools(state: AgentState) -> dict:
    """工具节点：执行模型请求的函数，结果作为 ToolMessage 追加"""
    last = state["messages"][-1]
    tool_msgs = []
    for tc in last.tool_calls:
        result = str(FUNC_MAP[tc["name"]].invoke(tc["args"]))
        tool_msgs.append(ToolMessage(content=result, tool_call_id=tc["id"]))
    return {"messages": tool_msgs}


def should_continue(state: AgentState):
    """条件边：模型还在请求工具 → 回 tools 节点（循环）；
    不再请求 → 结束。这就是 4.2 手写 while 的声明式版本。"""
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END


def build_agent_graph():
    g = StateGraph(AgentState)
    g.add_node("model", node_model)
    g.add_node("tools", node_tools)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "model")  # 工具执行完回到模型 → 循环
    return g.compile()


def main():
    if len(sys.argv) < 2:
        print("用法：python extra_langgraph_intro.py <需求文档>")
        sys.exit(1)

    doc = read_doc(sys.argv[1])

    # ─── Graph A：直线图跑四步链 ──────────────────────
    print("=" * 60)
    print("【Graph A】四步链的图版本（直线图 = LCEL 管道的超集表达）")
    pipeline = build_pipeline_graph()
    result = pipeline.invoke({"requirement": doc})
    final = result["final"]
    print(f"  → {final.get('protocol_name')}（{len(final.get('fields', []))} 字段）")
    print(f"  图的节点流：analyze → fields → rules → merge（每条边显式声明）")

    # ─── Graph B：agent 循环图跑工具校验 ───────────────
    print("\n" + "=" * 60)
    print("【Graph B】工具校验 agent 图（4.2 手写 while 的声明式版本）")
    agent = build_agent_graph()
    msgs = [
        SystemMessage(
            "你是协议评审工程师。逐个字段调用 validate_field_type 校验，"
            "全部校验完输出汇总：哪些字段有问题、修正建议；都合法输出'全部通过'。"),
        HumanMessage(json.dumps(final.get("fields", []), ensure_ascii=False)),
    ]
    agent_result = agent.invoke({"messages": msgs})
    print(agent_result["messages"][-1].content)
    print("\n  图的节点流：model → tools → model → ...（循环直到模型不再调用工具）→ END")

    with open(OUTPUT_DIR / "langgraph_demo_result.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print("\n✅ 协议结果已保存 outputs/langgraph_demo_result.json")


if __name__ == "__main__":
    main()
