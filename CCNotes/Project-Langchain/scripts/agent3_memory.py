"""
Phase 3 · 记忆与状态 —— 让 agent 记住对话
=============================================
核心论断先行：LLM 自己【没有记忆】（无状态，每轮全量重喂——你已从慢镜头
看到消息数 2→4→7→10 的增长）。"记住对话"是【框架层】能力 = checkpointer
（检查点）把每一步的 state 落盘，下次同一 thread 的 invoke 从检查点恢复接着跑。

三类演示（全部 FakeLLM = 零 API。记忆机制与模型无关，测的是框架层）：
  A. 失忆对照：不挂 checkpointer → 两次 invoke 完全独立，第二次看不到第一次
  B. 进程内记忆：挂 MemorySaver + thread_id → 同 thread 累积、不同 thread 隔离
  C. 落盘持久化：挂 SqliteSaver(文件) → 分两个进程跑 store/ask，
     新进程从磁盘恢复上一进程的对话（"进程重启不丢"）

运行：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent3_memory.py          # A + B
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent3_memory.py store    # C 进程1：写对话
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent3_memory.py ask      # C 进程2(=重启)：恢复
"""

import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "outputs" / "memory_demo.db"

SEP = "─" * 66


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


class FakeLLM:
    """假模型：每轮打印『我这次收到了 N 条消息』——让『有没有历史』肉眼可见。"""

    def __init__(self, name="FakeLLM"):
        self.name = name
        self.calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls += 1
        n_history = len(messages)  # 收到几条 = 能看到几轮上下文
        last_text = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_text = m.content
                break
        print(f"    🧠 [{self.name} 第{self.calls}次调用] 看到 {n_history} 条消息，最新用户说：{last_text[:30]}")
        return AIMessage(content=f"（{self.name}）已收到你的第 {self.calls} 条消息，本条是：{last_text[:20]}")


def build_agent(llm, checkpointer=None):
    """最小对话图：START→agent→END。checkpointer 决定『记忆存不存、存哪』。"""

    def call_model(state: AgentState):
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(AgentState)
    g.add_node("agent", call_model)
    g.add_edge(START, "agent")
    g.add_edge("agent", END)
    return g.compile(checkpointer=checkpointer)  # None=无记忆；MemorySaver/SqliteSaver=有记忆


def run_turn(graph, thread_id: str, text: str):
    """发一条消息；thread_id 是『会话钥匙』。"""
    print(f"  [turn] thread={thread_id!r} 用户：{text}")
    result = graph.invoke(
        {"messages": [HumanMessage(content=text)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    msgs = result["messages"]
    print(f"  → 这轮结束后 state 里共 {len(msgs)} 条消息")


def part_a_no_memory(llm):
    print(SEP)
    print("A · 不挂 checkpointer：两次 invoke 完全独立（失忆）")
    print(SEP)
    g = build_agent(llm, checkpointer=None)
    run_turn(g, "t1", "记住：我的订单号是 SO-1003")
    print("  （换新一轮……用户又问：我订单号是多少？）")
    run_turn(g, "t1", "我刚才说的订单号是多少？")
    print("  → 看到没：第二次 FakeLLM 只看到 1 条消息——上一轮的话根本没进来。模型失忆。")


def part_b_memory_saver(llm):
    print()
    print(SEP)
    print("B · 挂 MemorySaver + thread_id：同 thread 累积、不同 thread 隔离")
    print(SEP)
    from langgraph.checkpoint.memory import MemorySaver

    g = build_agent(llm, checkpointer=MemorySaver())
    run_turn(g, "alice", "记住：我的订单号是 SO-1003")
    run_turn(g, "alice", "我刚才说的订单号是多少？")  # 同 thread → 应看到 3 条
    run_turn(g, "bob", "我也有个订单号，是 SO-2001")   # 新 thread → 从零开始
    run_turn(g, "bob", "alice 的订单号是多少？")        # 隔离 → bob 看不到 alice
    print("  → alice 两轮消息累积；bob 是独立会话，看不到 alice 的 SO-1003。")


def part_c_sqlite_store(llm):
    from langgraph.checkpoint.sqlite import SqliteSaver

    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        g = build_agent(llm, checkpointer=saver)
        print(SEP)
        print(f"C · 进程1(store)：对话写进 SqliteSaver → {DB_PATH}")
        print(SEP)
        run_turn(g, "carol", "我的订单 SO-3001 卡在运输中，帮我记下")
        run_turn(g, "carol", "我的订单号是什么来着？")
        print("  进程1 结束，连接关闭。对话已落盘。现在跑 ask（=新进程/重启）看能否恢复。")


def part_c_sqlite_ask(llm):
    from langgraph.checkpoint.sqlite import SqliteSaver

    with SqliteSaver.from_conn_string(str(DB_PATH)) as saver:
        g = build_agent(llm, checkpointer=saver)
        print(SEP)
        print("C · 进程2(ask=重启)：重开同一 db 文件，同一 thread 继续问")
        print(SEP)
        run_turn(g, "carol", "所以我的订单号到底是？")
        print("  → FakeLLM 看到了历史消息（>1 条）→ 跨进程记忆恢复成功：'重启不丢' 达成")


def main():
    llm = FakeLLM()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "store":
        part_c_sqlite_store(llm)
    elif mode == "ask":
        part_c_sqlite_ask(llm)
    else:
        part_a_no_memory(llm)
        part_b_memory_saver(llm)


if __name__ == "__main__":
    main()
