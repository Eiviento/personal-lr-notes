"""MCP 示例的端到端 smoke 测试。

两套验证：
1. in-memory：把 server 的 MCPServer 实例直接交给 Client（不走进程），快速验证三原语。
2. stdio：像真实宿主那样把 server.py 作为子进程拉起，验证完整链路。

运行：
    .venv/Scripts/python.exe -m pytest tests/ -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

# 让 tests/ 能 import 项目根的 server.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402


def test_list_tools_exposes_add_and_now() -> None:
    async def _inner():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            return {t.name for t in tools.tools}

    assert {"add", "now"} <= anyio.run(_inner)


def test_call_add_returns_structured_result() -> None:
    async def _inner():
        async with Client(server.mcp) as client:
            return await client.call_tool("add", {"a": 2, "b": 3})

    result = anyio.run(_inner)
    assert result.structured_content == {"result": 5}


def test_read_greeting_resource() -> None:
    async def _inner():
        async with Client(server.mcp) as client:
            res = await client.read_resource("greeting://Bob")
            return res.contents[0].text

    assert "Bob" in anyio.run(_inner)


def test_get_code_review_prompt() -> None:
    async def _inner():
        async with Client(server.mcp) as client:
            rendered = await client.get_prompt("code_review", {"code": "print(1/0)"})
            return rendered.messages[0].content.text

    assert "print(1/0)" in anyio.run(_inner)


def test_end_to_end_over_stdio_subprocess() -> None:
    """真实子进程链路：等价于 client.py 的连接方式。"""
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(server.__file__))],
    )

    async def _inner():
        async with Client(params) as client:
            result = await client.call_tool("add", {"a": 10, "b": 20})
            return result.structured_content

    assert anyio.run(_inner) == {"result": 30}
