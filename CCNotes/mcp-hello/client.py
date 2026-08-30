"""
MCP 最小示例客户端：零 LLM 成本，直接调工具看输入输出
======================================================
拉起 server.py 子进程，通过 stdio 说 JSON-RPC：
  list_tools → 看有哪些工具
  call_tool ×4 → 每个工具的输入与输出
  read_resource → 读资源

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe client.py
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "server.py"


async def main():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("【服务器里有哪些工具】")
            for t in tools.tools:
                print(f"  🔌 {t.name}")
            print()

            print("【逐个调用：输入 → 输出】")
            calls = [
                ("add", {"a": 3, "b": 5}),
                ("add", {"a": 1.5, "b": 2.5}),
                ("celsius_to_fahrenheit", {"c": 25}),
                ("celsius_to_fahrenheit", {"c": 0}),
            ]
            for name, args in calls:
                r = await session.call_tool(name, args)
                out = " / ".join(c.text for c in r.content)
                print(f"  {name}{args}  →  {out}")
            print()

            res = await session.read_resource("notes://weekly-plan")
            print("【读资源 notes://weekly-plan】")
            print(res.contents[0].text)


if __name__ == "__main__":
    asyncio.run(main())
