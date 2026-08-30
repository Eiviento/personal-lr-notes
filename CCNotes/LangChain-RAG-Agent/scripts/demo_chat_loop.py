"""
对话循环最小内核：零成本演示（假模型，不调 API）
================================================
对话助手 = 会话历史 + 循环 + UI。这里把 UI 和真模型都去掉，
只留"每轮把全部历史发出去 + 历史累积"这一个内核。

把 fake_llm 换成 llm_with_tools（4.2 的带工具模型），
这个循环就"会思考"了（模型点菜 → 代码上菜 → 回传）。

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_chat_loop.py
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def fake_llm(messages):
    """假模型：统计历史里用户说过几轮，模仿"看到了历史"的回答"""
    rounds = sum(1 for m in messages if isinstance(m, HumanMessage))
    return AIMessage(content=f"我看到了 {rounds} 轮历史，这是第 {rounds} 次回答")


def main():
    history = [SystemMessage("你是内部协议助手")]
    for question in ["什么是协议字段表？", "字段要多少字节？"]:
        history.append(HumanMessage(question))
        answer = fake_llm(history)  # 关键：每轮把【全部历史】发出去
        history.append(answer)
        print(f"用户: {question}\n助手: {answer.content}\n")
    print(f"messages 列表长度 = {len(history)}（历史在累积，这就是对话的本质）")


if __name__ == "__main__":
    main()
