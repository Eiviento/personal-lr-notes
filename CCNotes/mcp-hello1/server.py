"""最小可运行的 MCP Server —— 演示 MCP 的三种核心「原语」。

一个 MCP Server 就是把「工具 / 资源 / 提示词」暴露给 AI 应用的那一头。

运行方式：
  * 默认 stdio（宿主/客户端把你当子进程拉起，走标准输入输出通信）：
        .venv/Scripts/python.exe server.py
  * Streamable HTTP（适合部署成常驻服务、被远程连接）：
        .venv/Scripts/python.exe server.py --http     # 默认监听 8000/mcp

改用 MCP Inspector 可视化调试：
        .venv/Scripts/mcp.exe dev server.py
"""
from __future__ import annotations

import sys
from datetime import datetime

from mcp.server import MCPServer

# 一个 server 实例，名字会随握手返回给客户端
mcp = MCPServer("demo-server")


# ---------------------------------------------------------------------------
# 原语 1：Tool（工具）—— 模型可以「主动调用」的函数，会改变世界或做计算
# 关键点：类型注解 (a: int) 就是给模型看的 JSON Schema，docstring 就是给模型看的说明。
# 你不需要手写任何 schema、参数解析、校验代码。
# ---------------------------------------------------------------------------
@mcp.tool()
def add(a: int, b: int) -> int:
    """把两个整数相加并返回结果。"""
    return a + b


@mcp.tool()
def now() -> str:
    """返回当前本地时间（ISO 8601 格式）。"""
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 原语 2：Resource（资源）—— 只读数据，像 GET 请求，用 URI 标识，由宿主/用户决定是否注入
# URI 里的 {name} 是模板参数，客户端读 greeting://Alice 即可拿到内容。
# ---------------------------------------------------------------------------
@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """按名字打招呼（演示资源：只读、可寻址的数据）。"""
    return f"Hello, {name}! 欢迎来到 MCP 世界。"


# ---------------------------------------------------------------------------
# 原语 3：Prompt（提示词模板）—— 预置的可复用交互模板，通常由用户显式触发
# ---------------------------------------------------------------------------
@mcp.prompt()
def code_review(code: str) -> str:
    """生成一段代码审查的提示词模板。"""
    return (
        "请审查下面这段代码，指出潜在 bug 并给出改进建议：\n\n"
        f"{code}"
    )


if __name__ == "__main__":
    if "--http" in sys.argv:
        # 常驻 HTTP 服务，供远程客户端连接
        mcp.run(transport="streamable-http")
    else:
        # 默认：stdio，一行一行 JSON 走标准输入输出（本地子进程模式）
        mcp.run()
