"""模型驱动 MCP —— 演示完整的 Agent「工具调用循环」。

这是 MCP 之所以有用的核心场景：模型自己决定「要不要调工具、调哪个、传什么参数」，
宿主负责真正执行并把结果喂回模型，直到模型给出最终答案。

链路：
    user 提问
      → 把 MCP tools 转成模型的 function schema
      → 模型返回 tool_calls
      → 宿主调用 client.call_tool() 真正执行
      → 结果作为 tool 消息喂回模型
      → 再让模型决策 ... 循环直到没有 tool_call

运行：
    .venv/Scripts/python.exe llm_agent.py            # 离线 MockLLM，无需 API key，直接跑通
    .venv/Scripts/python.exe llm_agent.py --real     # 真实模型（需配置环境变量，见下）

真实模型对接任意 OpenAI 兼容接口，配置 3 个环境变量即可：
    set LLM_BASE_URL=https://api.deepseek.com/v1
    set LLM_API_KEY=sk-xxxx
    set LLM_MODEL=deepseek-chat
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

SERVER = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).with_name("server.py"))],
)


def mcp_tools_to_openai(tools: list) -> list[dict]:
    """把 MCP 的 Tool 定义转成 OpenAI function-calling 的 tools 格式。

    妙处在于 MCP 的 inputSchema 本来就是 JSON Schema —— 和 OpenAI 的 parameters 完全同构，
    所以这一步几乎是零成本的「格式搬运」。
    """
    out: list[dict] = []
    for t in tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.input_schema,
                },
            }
        )
    return out


# ---------------------------------------------------------------------------
# 两种「模型」后端，接口统一：chat(messages, tools) -> assistant message(dict)
# ---------------------------------------------------------------------------
class MockLLM:
    """离线假模型：第 1 轮决定调用 add(3,4)，拿到结果后第 2 轮收尾。

    它把「模型决策」简化成固定规则，好处是无需 API key 就能跑通并看清整条链路。
    """

    def __init__(self) -> None:
        self.step = 0

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        self.step += 1
        if self.step == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "add",
                            "arguments": json.dumps({"a": 3, "b": 4}),
                        },
                    }
                ],
            }
        return {"role": "assistant", "content": "3 加 4 等于 7。"}


class OpenAICompatLLM:
    """真实模型：任何 OpenAI 兼容接口（DeepSeek / 通义 / Kimi / 本地 vLLM 等）。"""

    def __init__(self) -> None:
        self.base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        body = json.dumps(
            {"model": self.model, "messages": messages, "tools": tools}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]


async def run_agent(llm, user_input: str) -> str | None:
    """通用 Agent 循环：与具体模型后端无关。"""
    async with Client(SERVER) as client:
        tools = await client.list_tools()
        openai_tools = mcp_tools_to_openai(tools.tools)
        print(f"[工具清单] {[t['function']['name'] for t in openai_tools]}")

        messages: list[dict] = [{"role": "user", "content": user_input}]
        while True:
            msg = llm.chat(messages, openai_tools)
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return msg.get("content")

            messages.append(msg)
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                print(f"[模型决定调用] {name}({args})")
                result = await client.call_tool(name, args)
                text = result.content[0].text
                print(f"[MCP 执行结果] {text}")
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": text}
                )


async def main() -> None:
    llm = OpenAICompatLLM() if "--real" in sys.argv else MockLLM()
    answer = await run_agent(llm, "帮我算一下 3 加 4 等于几？")
    print("最终回答:", answer)


if __name__ == "__main__":
    anyio.run(main)
