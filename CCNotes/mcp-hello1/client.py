"""MCP Client 示例 —— 用代码连接一个 MCP Server 并调用它的三种原语。

这份代码等价于「AI 宿主（Claude Desktop / Cursor / 自研 Agent）」内部替模型做的事：
先 list（问服务器有什么能力），再按需 call（真正执行）。

运行：
    .venv/Scripts/python.exe client.py

它会把 server.py 作为子进程拉起，通过 stdio(标准输入输出) 通信。
把下面的 StdioServerParameters 换成一个 URL 字符串，就变成连远程 HTTP 服务：
    async with Client("http://localhost:8000/mcp") as client:
"""
from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

# 决定「怎么连上 server」——这里选 stdio：把 server.py 当子进程启动
SERVER = StdioServerParameters(
    command=sys.executable,                       # 当前虚拟环境的 python
    args=[str(Path(__file__).with_name("server.py"))],
)


async def main() -> None:
    # async with 内部完成：进程启动 → 握手(initialize) → 能力协商
    async with Client(SERVER) as client:
        # 1) list_tools：问服务器「你有哪些工具」。宿主会把这份清单转给模型。
        tools = await client.list_tools()
        print("== 可用工具 ==")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description}")
            print(f"      inputSchema: {t.input_schema}")

        # 2) call_tool：真正调用工具。这就是模型决定「调用 add(3, 4)」后发生的事。
        result = await client.call_tool("add", {"a": 3, "b": 4})
        print("\n== 调用 add(a=3, b=4) ==")
        print("  structured_content:", result.structured_content)  # {'result': 7}
        print("  content:", result.content[0].text)                # '7'

        # 3) read_resource：读一个只读资源（URI 寻址）
        res = await client.read_resource("greeting://Alice")
        print("\n== 读取资源 greeting://Alice ==")
        print("  ", res.contents[0].text)

        # 4) list_prompts + get_prompt：拿到预置提示词模板
        prompts = await client.list_prompts()
        print("\n== 可用提示词模板 ==")
        for p in prompts.prompts:
            print(f"  - {p.name}: {p.description}")
        rendered = await client.get_prompt("code_review", {"code": "print(1/0)"})
        print("\n== 渲染 code_review 模板 ==")
        print("  ", rendered.messages[0].content.text)


if __name__ == "__main__":
    anyio.run(main)
