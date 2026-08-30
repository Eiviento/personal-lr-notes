# MCP（Model Context Protocol）：工具和数据的"USB-C 标准插头"

> 2026-08-30 实操跑通。覆盖：一句话理解 / 为什么需要 / 架构三件套 / 三个原语 / 与 Function Calling 对比 / 实操走查（零 LLM 成本）/ 最新动态 / 踩坑。

## 一、一句话理解

**MCP = 你已经会做的"模型点菜、代码上菜"（4.2 / 聊天助手）的标准化版本。**

- 4.2 的 `@tool` + `bind_tools`：工具定义在**你自己的代码**里，只有你的程序能用——**私有插头**
- MCP：把同一套工具做成**标准插头（USB-C）**——任何支持 MCP 的客户端（Claude Desktop、Claude Code、LangChain、任何 LLM 应用）都能插上用——**一次写好，到处能插**

关键认知：**MCP 与"大模型"没有必然关系**。它是客户端和服务器之间的"通话协议"（JSON-RPC 2.0），客户端可以是模型（点菜），也可以是纯代码（本项目 `demo_mcp_client.py` 就是——全程零 LLM 调用，照样调工具）。

## 二、为什么需要：N×M 问题

| | 没有 MCP | 有 MCP |
|---|---------|--------|
| 5 个客户端 × 6 个服务（数据库/文件/GitHub/搜索/公司 API…） | 要写 5×6=30 份对接代码 | 每个服务写 1 个 MCP 服务器，每个客户端写 1 个 MCP 客户端：5+6=11 |
| 新客户端接入 | 重新对接全部服务 | 自带 MCP 支持，直接插 |

对公司的意义：内部系统（协议库、测试设备、Wiki）各做一个 MCP 服务器，任何人的任何 AI 工具都能用——这正是"公司内部 agent 助手"生态的底座。

## 三、架构三件套

```
┌───────────── Host（宿主应用：Claude Desktop / Claude Code / 你的 app）
│  ┌─────── Client（内嵌的 MCP 客户端，负责"翻译"）
│  │          │ JSON-RPC 2.0（文本消息，一问一答）
│  │          ▼
│  └─────── Server（MCP 服务器：暴露工具/资源/提示词）
└─────────────
  传输方式：stdio（本地子进程管道，本项目用的）
           / streamable HTTP（远程服务，可部署到服务器上给全公司用）
```

- Host = 用户面对的应用；Client = 协议翻译层（Host 内置）；Server = 你写的插头
- 一个 Server 可同时服务多个 Host；一个 Host 可同时插多个 Server

## 四、三个原语

| 原语 | 是什么 | 本项目对应 |
|------|--------|-----------|
| **Tools 工具** | 能调的函数（参数进、结果出） | `validate_field_type` / `get_fixed_size`（照抄 4.2 的死规则表） |
| **Resources 资源** | 能读的数据（URI 寻址，如 `protocol-tools://fixed-size/table`） | 同一张表以数据形式暴露——工具=动词，资源=名词 |
| **Prompts 提示词** | 可复用的提示词模板（带参数） | （本项目没用，概念同 2.1 的模板） |

## 五、与 Function Calling 对比（你学过的）

| | Function Calling（4.2） | MCP |
|---|------------------------|-----|
| 工具定义在哪 | 每个应用自己的代码里 | 独立的 MCP 服务器 |
| 谁能用 | 只有那个应用 | 任何 MCP 客户端 |
| 类比 | 设备内置功能 | 外接标准接口设备 |
| 关系 | 两者不冲突：LangChain 的模型照样能"点"MCP 服务器上的菜（langchain-mcp-adapters 桥接） | |

## 六、实操走查（scripts/demo_mcp_server.py + demo_mcp_client.py）

服务器 30 行 = 插头本体：

```python
mcp = FastMCP("protocol-tools")                       # 建服务器（插头品牌名）

@mcp.tool()                                           # 原语一：工具
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    """校验协议字段的类型与字节数是否匹配。…"""
    # 复用 phase4_2_tool_calling 的 FIXED_SIZE（from phase4_2_tool_calling import FIXED_SIZE）
    …

@mcp.resource("protocol-tools://fixed-size/table")    # 原语二：资源
def get_fixed_size_table() -> str: …

if __name__ == "__main__":
    mcp.run(transport="stdio")                        # 等客户端来插
```

客户端 40 行 = 插上插头说 JSON-RPC（**没有一个大模型参与**）：

```python
params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)
async with stdio_client(params) as (read, write):          # 拉起服务器子进程
    async with ClientSession(read, write) as session:      # 会话（v1 先握手）
        await session.initialize()
        tools = await session.list_tools()                 # 问：你有哪些工具？
        r = await session.call_tool("validate_field_type", # 调：点菜（不经过模型）
            {"field_name": "status", "field_type": "uint8", "length": 2})
        res = await session.read_resource("protocol-tools://fixed-size/table")
```

实跑输出（2026-08-30，完整原文可重跑复现）：

```
【1】问服务器有哪些工具（list_tools）
  🔌 validate_field_type: 校验协议字段的类型与字节数是否匹配。…
  🔌 get_fixed_size: 返回 FIXED_SIZE 死规则表（类型 → 标准字节数）的 JSON。...
【2】调工具 validate_field_type（故意注入错误：status uint8 声明 2 字节）
  → status: uint8 应为 1 字节，实际声明 2 → 不合法
【3】调工具 get_fixed_size（取整张死规则表）
  → {"uint8": 1, "int8": 1, "bool": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "float32": 4, "float64": 8}
【4】读资源 protocol-tools://fixed-size/table（MCP 第二原语：资源 = 数据）
  → { "uint8": 1, … "float64": 8 }（带缩进的原样表）
```

跑法：
```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_mcp_client.py
```

## 七、最新动态（2026-08）

- **2025-12-09**：Anthropic 把 MCP 捐给 Linux 基金会（Agentic AI Foundation），成为行业标准协议（OpenAI、Google 等都已支持）
- **2026-07-28 规范**：无状态化重写——取消握手/会话（`server/discover` 一次发现）、取消服务器主动推送（改多轮请求 `InputRequiredResult`）；对应 Python SDK **v2 稳定版**（`FastMCP` 更名 `MCPServer`）
- 本项目实操用 v1 SDK（`mcp>=1.28,<2`，生态 84% 还在用、最稳）；v2 迁移是将来方向
- 官方文档（含中文）：https://modelcontextprotocol.io

## 八、踩坑（全部实测踩中）

| # | 现象 | 原因与解法 |
|---|------|-----------|
| 1 | `@mcp.resource("fixed_size://table")` 报 "Input should be a valid URL" | 资源 URI 必须是**合法 URL**：`fixed_size://table` 的 host 是空的 → 补上：`//rules/table` |
| 2 | 改成 `fixed_size://rules/table` 仍报同样错 | URL **scheme 不能含下划线**（RFC 3986）→ 换成连字符：`protocol-tools://fixed-size/table` |
| 3 | 装 mcp 时提示 `veadk-python requires mcp==1.23.0` | 环境里已有包锁定旧版本；mcp 1.29.1 与项目演示不冲突，先记下不动它 |

## 九、独立于项目的 hello-world 示例

想脱离协议项目看最纯的 MCP：`CCNotes/mcp-hello/`（项目外独立目录）——"个人工具箱"服务器（`add` / `celsius_to_fahrenheit` 两个工具 + `notes://weekly-plan` 一个资源）+ 零 LLM 客户端，实跑输出：

```
【逐个调用：输入 → 输出】
  add{'a': 3, 'b': 5}                    →  8.0
  add{'a': 1.5, 'b': 2.5}                →  4.0
  celsius_to_fahrenheit{'c': 25}         →  77.0
  celsius_to_fahrenheit{'c': 0}          →  32.0
【读资源 notes://weekly-plan】
周一：写协议文档 …周五：发布
```

跑法：`cd CCNotes/mcp-hello && PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe client.py`

## 十、下一步可选

- **把本服务器插进 Claude Code / Claude Desktop**（配置文件 `mcpServers` 一项即可）——届时你在对话里就能直接"点"到项目的死规则表
- 给公司内部系统（协议库/Wiki/测试设备）各做一个 MCP 服务器，接入任何 AI 工具
- 深挖：https://modelcontextprotocol.io（官方）、https://github.com/modelcontextprotocol/python-sdk（SDK）、服务器目录 mcp.so / mcpreg.com
