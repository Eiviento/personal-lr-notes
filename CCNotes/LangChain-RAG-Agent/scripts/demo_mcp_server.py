"""
MCP 实操演示：把项目里的"死规则表"变成标准插头（MCP 服务器）
==============================================================
一句话理解 MCP：4.2 的 @tool（模型点菜代码上菜）是"自己项目里的私有插头"，
MCP 是把同一套工具做成**标准插头（USB-C）**——任何支持 MCP 的客户端
（Claude Desktop / Claude Code / LangChain / 任何 LLM 应用）都能插上用。

本服务器暴露两个工具 + 一个资源：
  - 工具 validate_field_type：复用 phase4_2 的 FIXED_SIZE 死规则表（照抄不改）
  - 工具 get_fixed_size：返回整张死规则表
  - 资源 fixed_size://table：同一张表，以"资源"（数据）形式暴露——展示 MCP
    的第二个原语：工具=能调的函数，资源=能读的数据

测试（零 LLM 成本）：scripts/demo_mcp_client.py 直接连本服务器调工具，
证明"MCP 是插头，模型不是必需品"。

用法（本文件一般不由人直接跑，由客户端拉起）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_mcp_server.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 复用兄弟模块的死规则表

from mcp.server.fastmcp import FastMCP

from phase4_2_tool_calling import FIXED_SIZE

# ─── 建服务器（一个名字，就是插头的"品牌"） ──────────────
mcp = FastMCP("protocol-tools")


# ─── 原语一：工具（能调的函数） ─────────────────────────
@mcp.tool()
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    """校验协议字段的类型与字节数是否匹配。
    参数：field_name 字段名；field_type 数据类型（uint8/int16/float32/string 等）；length 声明的字节数。"""
    if field_type == "string":
        return f"{field_name}: string 是变长类型，声明 {length} 字节 → 合法（约定为最大长度）"
    expected = FIXED_SIZE.get(field_type)
    if expected is None:
        return f"{field_name}: 未知类型 {field_type} → 不合法"
    if expected == length:
        return f"{field_name}: {field_type} 标准 {expected} 字节，声明 {length} → 合法"
    return f"{field_name}: {field_type} 应为 {expected} 字节，实际声明 {length} → 不合法"


@mcp.tool()
def get_fixed_size() -> str:
    """返回 FIXED_SIZE 死规则表（类型 → 标准字节数）的 JSON。"""
    return json.dumps(FIXED_SIZE, ensure_ascii=False)


# ─── 原语二：资源（能读的数据） ─────────────────────────
@mcp.resource("protocol-tools://fixed-size/table")  # 资源 URI 必须是合法 URL：空 host 会炸、scheme 不能含下划线（RFC 3986）
def get_fixed_size_table() -> str:
    """同一张死规则表，以资源形式暴露——资源是数据不是函数。"""
    return json.dumps(FIXED_SIZE, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")  # stdio：本地子进程管道（另一主流是 streamable HTTP：远程服务）
