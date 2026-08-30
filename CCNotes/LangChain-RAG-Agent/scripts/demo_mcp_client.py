"""
MCP 实操演示：客户端（零 LLM 成本——不经过任何大模型）
======================================================
拉起 demo_mcp_server.py 子进程，通过 stdio 管道和它说 JSON-RPC 话：
  1. list_tools()          —— 问服务器：你有哪些工具？
  2. call_tool(...)        —— 调 validate_field_type（故意注入错误，看死规则表发威）
  3. call_tool(get_fixed_size) —— 取整张表
  4. read_resource(...)    —— 读资源（MCP 第二原语）

关键认知：整个过程没有调用任何大模型——MCP 是"插头协议"，
客户端可以是模型（点菜），也可以是纯代码（本文件就是）。

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_mcp_client.py
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "demo_mcp_server.py"


async def main():
    # 环境：把中文 Windows 的坑挡在子进程外面（坑 #5）
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # v1 协议：先握手（2026 新规范已改为无会话，见 lessons/extra_mcp.md）

            print("=" * 60)
            print("【1】问服务器有哪些工具（list_tools）")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"  🔌 {t.name}: {t.description[:50]}...")

            print("\n【2】调工具 validate_field_type（故意注入错误：status uint8 声明 2 字节）")
            r = await session.call_tool(
                "validate_field_type",
                {"field_name": "status", "field_type": "uint8", "length": 2},
            )
            for c in r.content:
                print(f"  → {c.text}")

            print("\n【3】调工具 get_fixed_size（取整张死规则表）")
            r = await session.call_tool("get_fixed_size", {})
            for c in r.content:
                print(f"  → {c.text}")

            print("\n【4】读资源 protocol-tools://fixed-size/table（MCP 第二原语：资源 = 数据）")
            res = await session.read_resource("protocol-tools://fixed-size/table")
            for item in res.contents:
                print("  → " + item.text.replace("\n", "\n    "))


if __name__ == "__main__":
    asyncio.run(main())
