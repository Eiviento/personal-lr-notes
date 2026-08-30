"""
对话式协议助手：无 UI 版（真实 agent，真调 DeepSeek）
======================================================
app.py 的同一套大脑（chat_agent），去掉 Streamlit，在控制台里聊。
教学价值：历史累积、模型点菜（🔧 标记）、最终答复逐字输出，全程可见。

用法：
  python demo_chat_cli.py                              # 交互式
  python demo_chat_cli.py <需求文档> "帮我生成协议" "第一个字段的类型对吗"   # 非交互（实录用）
"""

import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from chat_agent import build_chat_agent, set_current_doc, stream_turn


def run_scripted(questions: list) -> None:
    agent = build_chat_agent()
    messages = []
    for q in questions:
        print(f"👤 用户：{q}")
        messages.append(HumanMessage(q))
        print("🤖 助手：", end="", flush=True)
        full = ""
        for piece in stream_turn(agent, messages):
            print(piece, end="", flush=True)
            full += piece
        messages.append(AIMessage(full))
        print("\n" + "=" * 60)


def run_interactive() -> None:
    agent = build_chat_agent()
    messages = []
    print("（输入 exit 退出）")
    while True:
        q = input("\n你：").strip()
        if q in ("exit", "quit", "退出"):
            break
        if not q:
            continue
        messages.append(HumanMessage(q))
        print("助手：", end="", flush=True)
        full = ""
        for piece in stream_turn(agent, messages):
            print(piece, end="", flush=True)
            full += piece
        messages.append(AIMessage(full))
        print()


def main():
    args = sys.argv[1:]
    doc_path, questions = None, []
    for a in args:
        if not doc_path and Path(a).exists():
            doc_path = a
        else:
            questions.append(a)

    if doc_path:
        set_current_doc(Path(doc_path).read_text(encoding="utf-8", errors="ignore"))
        print(f"📄 已加载文档：{doc_path}")

    if questions:
        run_scripted(questions)   # 非交互：实录
    else:
        run_interactive()


if __name__ == "__main__":
    main()
