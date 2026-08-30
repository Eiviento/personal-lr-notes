"""
对话式协议助手：agent 循环 + 工具（混合式助手的"大脑"）
======================================================
三个零件全在项目里（详见 lessons/extra_chat_agent.md）：
  - 会话历史：Human/AIMessage 列表，每轮全量重发（第 6 章）
  - agent 循环：create_react_agent（= 4.2 手写 while + Graph B 的官方成品版）
  - UI：app.py 薄壳渲染；本模块不含任何 UI 逻辑，headless 也能用

工具设计（模型点菜，代码上菜）：
  generate_protocol   → 跑 4.1 的 rag_chain，回传紧凑摘要（完整结果存模块级变量供下载）
  validate_field_type → 直接复用 4.2 的 @tool，不改一行

文档注入：set_current_doc() 存模块级变量（而非 st.session_state），
这样 app.py 和命令行 demo 共用同一套大脑。
"""

import json
import os

from langchain_core.messages import AIMessageChunk
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from phase4_1_rag import rag_chain
from phase4_2_tool_calling import validate_field_type

# ─── 配置 ─────────────────────────────────────────────
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key-here"),
    base_url="https://api.deepseek.com",
    temperature=0.3,
    max_tokens=4096,
)

# ─── 模块级"当前文档"与"最近协议"：UI 与 CLI 共用的状态 ───
_current_doc: str | None = None
_last_result: dict | None = None


def set_current_doc(text: str | None) -> None:
    """上传文档时注入；generate_protocol 无参调用时读它"""
    global _current_doc
    _current_doc = text


def get_last_protocol() -> dict | None:
    """最近一次 generate_protocol 的完整结果（app.py 侧栏下载用）"""
    return _last_result


# ─── 工具 1：生成协议（把整条 rag_chain 包成工具） ─────
@tool
def generate_protocol(requirement: str = "") -> str:
    """当用户要求生成、起草、整理协议规范时调用。参数可选：
    用户直接贴出了需求文本就传进来；否则留空，用当前已上传的需求文档。"""
    text = requirement.strip() or _current_doc
    if not text:
        return "错误：手头没有需求文档。请告诉用户：先上传需求文档（或直接把需求内容发给我），我再生成协议。"
    result = rag_chain.invoke({"requirement": text})  # 4.1 的链：检索历史模板 + 四步链
    global _last_result
    _last_result = result
    fields = result.get("fields", [])
    summary = (
        f"协议《{result.get('protocol_name', '未命名')}》已生成：\n"
        f"- 共 {len(fields)} 个字段：" + "、".join(f"{f.get('name')}:{f.get('type')}" for f in fields) + "\n"
        f"- {len(result.get('constraints', []))} 条约束规则，{len(result.get('issues', []))} 条评审提示\n"
        f"- 完整规范已保存，请提醒用户到侧栏下载"
    )
    return summary


# ─── 系统提示词：四要素（角色/指令/上下文/输出格式） ────
SYSTEM_PROMPT = """\
你是公司内部的协议规范助手，服务于通信协议工程师。

你的能力：
1. 直接回答协议相关的任何问题（字段类型、字节数、校验、上报频率等），中文、简洁、表格优先
2. 用 generate_protocol 工具把需求文档变成协议规范（用户上传文档或直接贴需求后说"生成协议"）
3. 用 validate_field_type 工具校验字段的类型与字节数是否匹配（用户问"这个字段对吗"时主动调用）

规则：
- 用户要求生成协议时，先确认手头有没有需求内容：有已上传文档就直接调 generate_protocol（不传参数）；没有就请用户上传或贴出来
- 工具返回错误信息时，如实转述给用户并给出建议，不要编造结果
- 生成协议后主动提醒用户：完整规范在侧栏可下载
"""


# ─── 组装：官方封装 = 4.2 手写 while + Graph B 的成品版 ─
def build_chat_agent():
    """create_react_agent 内部：model 节点 → 条件边（有 tool_calls? → tools → 回 model）→ END"""
    return create_react_agent(llm, [generate_protocol, validate_field_type], prompt=SYSTEM_PROMPT)


# ─── 流式输出：token 级打字机 + 工具调用标记 ───────────
def stream_turn(agent, messages):
    """跑一轮并逐段产出。过滤规则：
    - AIMessageChunk 的 tool_calls → "🔧 调用工具 X（参数）" 标记（按 tool_call id 去重）
    - AIMessageChunk 的 str content → 逐 token 产出（最终答复）
    - ToolMessage 的 content → 不上屏（执行细节不打扰用户）"""
    seen = set()
    for chunk, _ in agent.stream({"messages": messages}, stream_mode="messages"):
        if isinstance(chunk, AIMessageChunk):
            for tc in chunk.tool_calls or []:
                cid = tc.get("id")
                if cid and cid not in seen:
                    seen.add(cid)
                    yield "\n\n🔧 调用工具 " + tc.get("name", "?") + "（" + json.dumps(tc.get("args", {}), ensure_ascii=False) + "）\n"
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content


# ─── AppTest 冒烟用假 agent：不真调 API ────────────────
class FakeAgent:
    """.stream 接口模仿真 agent（stream_mode='messages' 输出形状），内容固定"""

    def stream(self, inputs, stream_mode="messages"):
        def gen():
            yield AIMessageChunk(content="（假agent）你好，我是协议助手，冒烟测试通过"), {}
        return gen()
