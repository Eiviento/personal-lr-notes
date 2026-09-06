"""
Phase 1 · 拆开黑盒 —— 第 1 步：黑盒 create_react_agent 跑通技术支持助手
=======================================================================
干什么：用官方封装 create_react_agent 组装一个"技术支持客服 agent"
        （3 个工具），跑真实对话，并借 graph.stream 把 agent 内部的
        循环轨迹一格格打出来——黑盒不黑，你能看到模型"点菜"、
        工具"上菜"、循环"收敛"的每一步。
吃什么吐什么：输入示例用户问题（写死在 main 里）；输出逐节点执行轨迹
        + 最终回答，存 outputs/agent1_blackbox_run.log。
为什么这么写：P1 的教学目标是"先看见循环，再拆开循环"。这版只用官方
        封装（黑盒）+ 流式查看器；第 2 步（同文件下半段/lesson）再手写
        等价 StateGraph 对照。对比基准先立住：官方封装到底替我们做了啥。

运行（需 .env 配好 DEEPSEEK_API_KEY）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent1_whitebox.py

教学三问（读代码时问自己）：
  1. 这一段在干什么？
  2. 它吃什么（输入）吐什么（输出）？
  3. 为什么这么写，不这么写会怎样？
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows 控制台 GBK 坑：强制 stdout 走 UTF-8（配合 PYTHONIOENCODING 前缀双保险）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition
from typing import Annotated, TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUT_DIR = PROJECT_ROOT / "outputs"

load_dotenv(PROJECT_ROOT / ".env")

# ─── 工具 1：检索知识库（读 data/knowledge.txt，轻量关键词匹配） ──────
@tool
def search_knowledge(query: str) -> str:
    """在产品知识库中检索与问题相关的条目。支持退换货/保修/连接/离线/退款到账
    等主题。回答产品政策、故障排查类问题时调用；把用户原问题作为 query 传入。"""
    text = (DATA_DIR / "knowledge.txt").read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split("## ") if b.strip()]
    q = query.strip().replace(" ", "").replace("？", "").replace("?", "")
    # 生成 query 的连续 n-gram（n=4..8），任一出现在块文本即命中——
    # 容忍模型改写措辞（实测：模型把"怎么算"改写为"政策"导致整串子串漏检）
    grams = {q[i : i + n] for n in range(4, 9) for i in range(max(len(q) - n + 1, 0))} if len(q) >= 4 else {q}
    hits = []
    for block in blocks:
        body = block.replace("\n", "").replace(" ", "")
        if q in body or any(g in body for g in grams):
            hits.append(block)
    if not hits:
        return "知识库中未找到与「" + q + "」直接相关的条目。请如实告诉用户：这个问题知识库没有覆盖，建议转人工或换一种问法。"
    return "\n\n".join(hits[:3])


# ─── 工具 2：查订单（读 data/orders.json） ────────────────────────────
@tool
def get_order_status(order_id: str) -> str:
    """查询订单的当前状态。参数 order_id 形如 SO-1001。查到返回产品/价格/状态/日期；
    查不到必须如实说明系统里没有这个订单，不要编造。"""
    data = json.loads((DATA_DIR / "orders.json").read_text(encoding="utf-8"))
    for order in data["orders"]:
        if order["order_id"].upper() == order_id.strip().upper():
            lines = [
                f"订单 {order['order_id']}：{order['product']}",
                f"状态：{order['status']}",
                f"下单日期：{order['order_date']}",
            ]
            if order.get("delivered_date"):
                lines.append(f"送达日期：{order['delivered_date']}")
            if order.get("tracking"):
                lines.append(f"物流单号：{order['tracking']}")
            lines.append(f"价格：{order['price']} 元")
            return "\n".join(lines)
    return f"订单 {order_id} 未找到：系统中不存在该订单号。请让用户核对订单号是否正确（形如 SO-1001）。"


# ─── 工具 3：当前时间（P1/P2 教学用最小无副作用工具） ──────────────────
@tool
def get_now_time() -> str:
    """返回服务器当前时间（含时区）。用户问时间/几点时调用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── LLM：DeepSeek（OpenAI 兼容） ────────────────────────────────────
def _build_llm():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        print("[错误] 未找到 DEEPSEEK_API_KEY：请确认 .env 已配置（复制 .env.example 并填入真实 key）。", file=sys.stderr)
        sys.exit(1)
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=key,
        base_url="https://api.deepseek.com",
        temperature=0.3,
        max_tokens=2048,
    )


# ─── 系统提示词（四要素：角色/能力/规则/格式） ─────────────────────────
SYSTEM_PROMPT = """你是 SmartHome 智能家居产品的技术支持客服助手。

你的能力：
1. 用 search_knowledge 检索产品知识库（退换货/保修/连接/固件等政策与排查）
2. 用 get_order_status 查询订单状态（用户给订单号时）
3. 用 get_now_time 告知当前时间

规则：
- 用户问政策/故障类问题先调 search_knowledge，用检索结果回答，不要凭印象编
- 用户查订单先要订单号（形如 SO-1001），拿到就调 get_order_status
- 工具返回"未找到/没有"时，如实转述并请用户核对，不要编造订单或政策
- 回答用中文，简洁，需要时列要点
"""


# ─── 组装黑盒 agent + 逐节点轨迹查看 ──────────────────────────────────
def build_agent():
    llm = _build_llm()
    tools = [search_knowledge, get_order_status, get_now_time]
    return create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)


def run_question(agent, question: str, log_lines: list[str]):
    """跑一个问题，用 stream(stream_mode='updates') 逐节点打印循环轨迹。"""
    header = f"\n{'='*70}\n用户：{question}\n{'='*70}"
    print(header)
    log_lines.append(header)
    try:
        for step in agent.stream(
            {"messages": [HumanMessage(question)]},
            stream_mode="updates",
        ):
            for node_name, update in step.items():
                msgs = update.get("messages", [])
                if not msgs:
                    continue
                last = msgs[-1]
                kind = type(last).__name__
                if kind == "AIMessage" and getattr(last, "tool_calls", None):
                    for tc in last.tool_calls:
                        line = f"[模型点菜] {node_name} → 调用工具 {tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"
                        print("  " + line)
                        log_lines.append("  " + line)
                elif kind == "ToolMessage":
                    snippet = (last.content or "")[:200]
                    line = f"[工具上菜] {node_name} → {last.name} 返回：{snippet}"
                    print("  " + line)
                    log_lines.append("  " + line)
                else:
                    content = getattr(last, "content", "")
                    line = f"[{node_name}] {kind}: {content}"
                    print("  " + line)
                    log_lines.append("  " + line)
    except Exception as e:  # noqa: BLE001 —— 教学脚本：异常如实打印并留档
        line = f"[异常] {type(e).__name__}: {e}"
        print("  " + line)
        log_lines.append("  " + line)


# ─── 白盒对照：手写等价 StateGraph（抄黑盒内部的 4 节点 4 边） ──────────
class AgentState(TypedDict):
    """图贯穿的共享状态：消息列表。Annotated[list, add_messages] 表示
    各节点返回的新消息会被【追加】进列表而不是覆盖——这是多轮对话能累积的原因。"""
    messages: Annotated[list, add_messages]


def build_whitebox_agent():
    """手写 create_react_agent 的内部结构：agent 节点 + tools 节点 + 条件边。"""
    llm = _build_llm()
    tools = [search_knowledge, get_order_status, get_now_time]
    # 关键 1：bind_tools —— 把工具 schema 告诉模型，模型才"知道能点哪些菜"
    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: AgentState):
        # 关键 2：模型节点 = 一次 LLM 调用。系统提示 + 全部历史拼给它。
        #   （黑盒里 create_react_agent 也做同样的事：prompt 参数 + 累积消息）
        msgs = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        return {"messages": [llm_with_tools.invoke(msgs)]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)               # 节点 1：模型决策
    graph.add_node("tools", ToolNode(tools))          # 节点 2：执行工具
    graph.add_edge(START, "agent")
    # 关键 3：条件边 —— 模型输出里有 tool_calls 就走 tools，没有就 END。
    #   tools_condition 是 prebuilt 提供的现成判定函数（等价于手写
    #   "if last.tool_calls: return 'tools' else return END"）
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")                  # 工具结果回传 → 循环
    return graph.compile()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    print("组装黑盒 create_react_agent ...（首次运行会初始化连接）")
    black = build_agent()

    # 教学示例：两个问题覆盖 工具1(知识检索) 与 工具2(查订单) 两条循环路径
    black_log: list[str] = []
    run_question(black, "我买了 SmartHome Hub，请问七天无理由退货怎么算？", black_log)
    run_question(black, "帮我查一下订单 SO-1003 现在到哪了？", black_log)
    (OUT_DIR / "agent1_blackbox_run.log").write_text("\n".join(black_log) + "\n", encoding="utf-8")
    print(f"[留档] 黑盒运行记录 → outputs/agent1_blackbox_run.log")

    # ─── 白盒对照：同一问题，手写 StateGraph 再跑一遍 ───
    print("\n" + "=" * 70)
    print("白盒对照：手写 StateGraph 跑同一问题（验证封装无魔法）")
    print("=" * 70)
    white = build_whitebox_agent()
    white_log: list[str] = []
    run_question(white, "帮我查一下订单 SO-1003 现在到哪了？", white_log)
    (OUT_DIR / "agent1_whitebox_run.log").write_text("\n".join(white_log) + "\n", encoding="utf-8")
    print(f"[留档] 白盒运行记录 → outputs/agent1_whitebox_run.log")


if __name__ == "__main__":
    main()
