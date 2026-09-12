"""连接「现成的」第三方 MCP Server —— 以官方 Python 版 time server 为例。

你几乎不用自己写所有工具：社区和官方已有大量现成 MCP Server（时间、抓网页、
Git、GitHub、数据库、Slack……）。这里演示用同一套 Client 代码连接别人写好的 server。

启动命令用 `uvx`（uv 自带的工具运行器）：它会为 mcp-server-time 单独建隔离环境，
不污染本项目的 .venv。这正体现 MCP 的「进程边界」——client 与 server 可以是
不同语言、不同依赖版本，只要能通过 stdio 说 MCP 协议即可。

运行：
    .venv/Scripts/python.exe connect_external.py

对照：把 StdioServerParameters 换成别的命令，就换成连别的 server；
Client 代码一行都不用改。
"""
from __future__ import annotations

import shutil

import anyio
from mcp import Client, StdioServerParameters

# uvx 优先级：PATH 里的 uvx；Windows 上可能是 uvx.exe
UVX = shutil.which("uvx") or shutil.which("uvx.exe") or "uvx"

# 只改这里，就从一个 server 换到另一个
TIME_SERVER = StdioServerParameters(
    command=UVX,
    args=["mcp-server-time"],
)


async def main() -> None:
    async with Client(TIME_SERVER) as client:
        tools = await client.list_tools()
        print("== mcp-server-time 提供的工具 ==")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description}")
            print(f"      inputSchema: {t.input_schema}")

        print("\n== 调用 get_current_time(timezone='Asia/Shanghai') ==")
        result = await client.call_tool(
            "get_current_time", {"timezone": "Asia/Shanghai"}
        )
        if result.structured_content is not None:
            print("  structured:", result.structured_content)
        print("  text:", result.content[0].text)


if __name__ == "__main__":
    anyio.run(main)
