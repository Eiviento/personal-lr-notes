"""
MCP 最小示例：个人工具箱服务器（独立于任何项目的 hello-world）
============================================================
两个工具 + 一个资源，与协议项目毫无关系——证明 MCP 是通用插头。

用法（本文件一般由客户端拉起，不直接跑）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-toolbox")  # 插头的品牌名


@mcp.tool()
def add(a: float, b: float) -> float:
    """两个数相加。当用户要算加法时调用。"""
    return a + b


@mcp.tool()
def celsius_to_fahrenheit(c: float) -> float:
    """摄氏度转华氏度。当用户要换算温度时调用。"""
    return c * 9 / 5 + 32


@mcp.resource("notes://weekly-plan")  # URI 必须合法：host 不能空、scheme 不能含下划线
def weekly_plan() -> str:
    """一周计划（演示"资源"原语：数据不是函数）"""
    return "周一：写协议文档\n周二：评审\n周三：联调\n周四：测试\n周五：发布"


if __name__ == "__main__":
    mcp.run(transport="stdio")  # stdio：本地子进程管道
