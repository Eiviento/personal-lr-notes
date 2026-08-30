# 对话式协议助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 app.py 升级为聊天窗口式协议助手：create_react_agent + 两个工具（generate_protocol 包 rag_chain / validate_field_type 复用 4.2）+ Streamlit 聊天组件 + token 级打字机，配零成本冒烟测试与真实对话实录。

**Architecture:** 大脑（scripts/chat_agent.py：工具 + system prompt + build_chat_agent + stream_turn）与薄壳（app.py：渲染/状态搬运）分离；工具读模块级 `_current_doc`（app.py 上传时注入）而非 st.session_state——headless 脚本也能用同一套大脑。教学落盘 lessons/extra_chat_assistant_build.md（含真调对话原文）。

**Tech Stack:** Python + LangChain 1.x（langgraph.prebuilt.create_react_agent）+ Streamlit + DeepSeek API。

## Global Constraints

- 中文注释与文档；零基础可读；讲解带实跑输出
- 跑脚本：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe`（坑 #5/#6）
- 输出/路径一律 `Path(__file__).resolve()` 基准（坑 #12）；API Key 从环境变量 `DEEPSEEK_API_KEY` 读取，不硬编码
- UI 薄壳原则：业务逻辑全部在 scripts/，app.py 零业务新增
- git 直接提交 main（用户约定）；commit 末尾带 `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- 每完成一个任务同步 `docs/progress.md`（坑 #7）

---

### Task 1: 环境确认——create_react_agent 可用性 + 版本基线

**Files:**
- 无新文件（验证结论记入实现报告）

**Interfaces:**
- Produces: 版本基线（agent_env 的 langgraph / langchain_core / streamlit 版本号）+ 三个确认结论，后续任务直接依赖：
  1. `from langgraph.prebuilt import create_react_agent` 在 agent_env 可用
  2. `create_react_agent(llm, tools, prompt=str)` 编译成功
  3. `agent.stream({"messages": [...]}, stream_mode="messages")` 产出 `(chunk, metadata)`，chunk 为 AIMessageChunk/ToolMessage

- [ ] **Step 1: 查版本**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import langgraph, langchain_core, streamlit; print('langgraph', langgraph.__version__); print('langchain_core', langchain_core.__version__); print('streamlit', streamlit.__version__)"
```
Expected: 三行版本号（langgraph 应为 1.x）。

- [ ] **Step 2: 最小可用性验证（真调一次，几分钱）**

写临时脚本 `/tmp/check_agent.py` 并运行：
```python
import os, sys
sys.path.insert(0, r"D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent\scripts")
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessageChunk, HumanMessage

llm = ChatOpenAI(model="deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key-here"),
                 base_url="https://api.deepseek.com", temperature=0.3, max_tokens=1024)
agent = create_react_agent(llm, [], prompt="你是协议助手，中文回答。")
for chunk, meta in agent.stream({"messages": [HumanMessage("说一个字：好")]}, stream_mode="messages"):
    print(type(chunk).__name__, "|", repr(getattr(chunk, "content", None))[:80], "|", repr(getattr(chunk, "tool_calls", None))[:60])
```
运行：
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe /tmp/check_agent.py
```
Expected: 输出若干行 `AIMessageChunk | '好'...`（可能拆成多个 chunk）；无异常。若 chunk 类型/字段名与本计划假设不符（如 content 是 list），把实测形状记入报告并在报告里给出修正建议——后续任务的 stream_turn 过滤规则以实测为准（本计划代码已按 str content 编写）。

- [ ] **Step 3: 清理并记录**

删除 /tmp/check_agent.py（不提交）。把版本号与三个确认结论写入任务报告。

---

### Task 2: 编写 scripts/chat_agent.py（大脑）

**Files:**
- Create: `scripts/chat_agent.py`

**Interfaces:**
- Consumes: Task 1 的确认结论（create_react_agent 用法）
- Produces（后续任务按名使用）:
  - `set_current_doc(text: str | None) -> None`：注入当前需求文档（工具读它）
  - `get_last_protocol() -> dict | None`：最近一次生成的完整协议（下载用）
  - `build_chat_agent()`：编译好的 create_react_agent（工具 = generate_protocol + validate_field_type）
  - `stream_turn(agent, messages)`：生成器，逐段产出（tool 调用标记 / token 文本）
  - `FakeAgent`：AppTest 冒烟用假 agent（.stream 接口模仿真 agent）
  - `SYSTEM_PROMPT`、模块级 `llm`

- [ ] **Step 1: 写入完整脚本（照抄，不改）**

```python
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
```

- [ ] **Step 2: 零成本自检（stream_turn 过滤规则 + FakeAgent）**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent\scripts"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "
from chat_agent import FakeAgent, stream_turn
from langchain_core.messages import HumanMessage
pieces = list(stream_turn(FakeAgent(), [HumanMessage('你好')]))
print(pieces)
assert pieces == ['（假agent）你好，我是协议助手，冒烟测试通过']
print('stream_turn OK')
"
```
Expected: 打印列表与 `stream_turn OK`，无异常。（本步同时验证 import 链：chat_agent → phase4_1_rag → phase4_2_tool_calling 全部可导入。）

- [ ] **Step 3: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add scripts/chat_agent.py
git commit -m "feat: add chat agent brain (create_react_agent + 2 tools + stream_turn)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: 重写 app.py 为聊天窗口（薄壳）

**Files:**
- Modify: `app.py`（整体替换）

**Interfaces:**
- Consumes: Task 2 的 chat_agent 接口（build_chat_agent / set_current_doc / get_last_protocol / stream_turn / FakeAgent）
- Produces: 聊天窗口 UI；`CHAT_FAKE_AGENT=1` 环境变量开关切假 agent（Task 4 冒烟用）

- [ ] **Step 1: 整体替换 app.py（照抄，不改）**

```python
"""
Phase 5.1 升级版：对话式协议助手（聊天窗口）
============================================
从"上传→按钮→出结果"升级为聊天窗口。三零件（详见 lessons/extra_chat_agent.md）：
  - 会话历史：st.session_state["messages"]（重跑不丢）
  - agent 循环：scripts/chat_agent.py 的 build_chat_agent()（create_react_agent）
  - 聊天 UI：st.chat_message 渲染历史 + st.chat_input 输入 + st.write_stream 打字机

薄壳原则不变：业务逻辑全在 scripts/，这里只有渲染与状态搬运。

运行：
  streamlit run app.py
AppTest 冒烟（假 agent，不真调 API）：
  测试脚本里设环境变量 CHAT_FAKE_AGENT=1（见 scripts/demo_app_test.py）
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from langchain_core.messages import AIMessage, HumanMessage

from chat_agent import (
    FakeAgent,
    build_chat_agent,
    get_last_protocol,
    set_current_doc,
    stream_turn,
)
from generate_protocol import render_markdown


def decode_doc(raw: bytes) -> str:
    """上传文件的编码自适应（同 3.1：utf-8-sig → utf-8 → gb18030）"""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文件编码")


st.set_page_config(page_title="协议助手", page_icon="🤖", layout="wide")
st.title("🤖 协议助手")
st.caption("对话式协议规范助手：可聊天问答；上传需求文档后，说一声就帮你生成协议")


@st.cache_resource(show_spinner="加载模型组件中...")
def get_agent():
    """agent 是昂贵资源，缓存后重跑不重建；AppTest 冒烟走假 agent"""
    if os.getenv("CHAT_FAKE_AGENT") == "1":
        return FakeAgent()
    return build_chat_agent()


agent = get_agent()

# ─── 历史初始化（重跑不丢） ──────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ─── 上传：文档注入 chat_agent 模块，工具自己读 ────────
uploaded = st.file_uploader("上传需求文档（.md / .txt，可随时换、随时传）", type=["md", "txt"])
if uploaded is not None and uploaded.getvalue():
    set_current_doc(decode_doc(uploaded.getvalue()))
    st.info(f"已加载文档：{uploaded.name}。现在可以说\"帮我生成协议\"，或直接问问题。")

# ─── 历史气泡渲染 ────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg.type):
        st.markdown(msg.content)

# ─── 输入：追加历史 → 流式回答 → 追加回答 ──────────────
if question := st.chat_input("问我协议问题，或说\"帮我生成协议\""):
    st.session_state["messages"].append(HumanMessage(question))
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        full = ""
        try:
            full = st.write_stream(stream_turn(agent, st.session_state["messages"]))
        except Exception as e:
            st.error(f"调用失败：{e}")
        if full:
            st.session_state["messages"].append(AIMessage(full))

# ─── 侧栏：生成过协议后出现下载按钮 ────────────────────
with st.sidebar:
    st.header("📦 产物")
    last = get_last_protocol()
    if last is None:
        st.write("生成协议后，这里出现下载按钮")
    else:
        st.write(f"协议《{last.get('protocol_name', '未命名')}》")
        st.download_button("⬇ 下载 JSON（草稿）", json.dumps(last, ensure_ascii=False, indent=2),
                           file_name="protocol_draft.json", mime="application/json")
        st.download_button("⬇ 下载 Markdown（草稿）", render_markdown(last),
                           file_name="protocol_draft.md", mime="text/markdown")
```

- [ ] **Step 2: 语法检查**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -m py_compile app.py
```
Expected: 无输出、exit 0。

- [ ] **Step 3: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add app.py
git commit -m "feat: rewrite app.py as chat-window protocol assistant

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: AppTest 冒烟（假 agent，零成本）

**Files:**
- Create: `scripts/demo_app_test.py`（冒烟测试脚本，保留作回归）

**Interfaces:**
- Consumes: app.py + chat_agent.py（FakeAgent 分支）
- Produces: 可重复运行的 UI 冒烟；验证上传注入、假聊天一轮、历史累积、侧栏占位

- [ ] **Step 1: 写入测试脚本（照抄）**

```python
"""
app.py 冒烟测试（AppTest + 假 agent，零成本）
=============================================
验证聊天窗口的 UI 机制不崩：
  1. 页面渲染、无异常
  2. 上传文档 → chat_agent 模块收到文档
  3. 发消息 → 假 agent 回答 → 历史累积 2 条
  4. 侧栏显示"生成协议后"占位文案

不真调 API（CHAT_FAKE_AGENT=1）。

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_app_test.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 导入 chat_agent

os.environ["CHAT_FAKE_AGENT"] = "1"

from streamlit.testing.v1 import AppTest


class FileMock:
    """模仿上传文件对象（AppTest 的 file_uploader 输入）"""
    def __init__(self, name, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def main():
    sample = Path(__file__).resolve().parent.parent / "inputs/sample_requirement.md"

    at = AppTest.from_file(Path(__file__).resolve().parent.parent / "app.py").run()
    assert not at.exception, f"初始渲染异常：{at.exception}"

    # 1. 上传文档 → 注入成功
    at.file_uploader[0].set_value(FileMock(sample.name, sample.read_bytes())).run()
    assert not at.exception, f"上传后异常：{at.exception}"

    # 2. 发一条消息 → 假 agent 回答 → 历史 2 条
    at.chat_input[0].set_value("你好").run()
    assert not at.exception, f"聊天后异常：{at.exception}"
    msgs = at.session_state["messages"]
    assert len(msgs) == 2, f"历史应 2 条，实际 {len(msgs)}"
    assert msgs[0].type == "human" and msgs[1].type == "ai"

    print("✅ AppTest 冒烟通过：上传注入 / 假聊天一轮 / 历史累积 2 条 / 无异常")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行（若 file_uploader 的 set_value 在已装 streamlit 版本不支持，按报错调整 FileMock——报错原文记入报告）**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_app_test.py
```
Expected: `✅ AppTest 冒烟通过：...`。失败则修（调整测试或 app，不动 chat_agent 接口），把失败与修复记入报告。

- [ ] **Step 3: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add scripts/demo_app_test.py
git commit -m "feat: add AppTest smoke for chat assistant (fake agent, zero cost)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: CLI 对话实录（真调 DeepSeek）

**Files:**
- Create: `scripts/demo_chat_cli.py`
- Create: `outputs/chat_demo_transcript.log`（实录，教学文档引用）

**Interfaces:**
- Consumes: Task 2 的 chat_agent（build_chat_agent / set_current_doc / stream_turn）
- Produces: 教学用真实对话原文（"思考→执行→回答"全节奏可见）

- [ ] **Step 1: 写入 CLI 脚本（照抄）**

```python
"""
对话式协议助手：无 UI 版（真实 agent，真调 DeepSeek）
======================================================
app.py 的同一套大脑（chat_agent），去掉 Streamlit，在控制台里聊。
教学价值：历史累积、模型点菜（🔧 标记）、最终答复逐字输出，全程可见。

用法：
  python demo_chat_cli.py                              # 交互式
  python demo_chat_cli.py <需求文档> "帮我生成协议" "第一个字段的类型对吗"   # 非交互（实录用）
"""

import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from chat_agent import build_chat_agent, set_current_doc, stream_turn


def run_scripted(questions: list) -> None:
    agent = build_chat_agent()
    messages = []
    for q in questions:
        print(f"👤 用户：{q}")
        messages.append(HumanMessage(q))
        print("🤖 助手：", end="", flush=True)
        full = ""
        for piece in stream_turn(agent, messages):
            print(piece, end="", flush=True)
            full += piece
        messages.append(AIMessage(full))
        print("\n" + "=" * 60)


def run_interactive() -> None:
    agent = build_chat_agent()
    messages = []
    print("（输入 exit 退出）")
    while True:
        q = input("\n你：").strip()
        if q in ("exit", "quit", "退出"):
            break
        if not q:
            continue
        messages.append(HumanMessage(q))
        print("助手：", end="", flush=True)
        full = ""
        for piece in stream_turn(agent, messages):
            print(piece, end="", flush=True)
            full += piece
        messages.append(AIMessage(full))
        print()


def main():
    args = sys.argv[1:]
    doc_path, questions = None, []
    for a in args:
        if not doc_path and Path(a).exists():
            doc_path = a
        else:
            questions.append(a)

    if doc_path:
        set_current_doc(Path(doc_path).read_text(encoding="utf-8", errors="ignore"))
        print(f"📄 已加载文档：{doc_path}")

    if questions:
        run_scripted(questions)   # 非交互：实录
    else:
        run_interactive()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 真调实录（约 5 次 LLM 调用，几分钱）**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent\scripts"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe demo_chat_cli.py ../inputs/sample_requirement.md "你好，简单介绍下你自己" "帮我生成协议" "第一个字段的类型和字节数对吗" > ../outputs/chat_demo_transcript.log 2>&1
echo "exit=$?"
```
Expected: exit=0；实录含三段问答；第二轮出现 `🔧 调用工具 generate_protocol` 标记 + 协议摘要；第三轮出现 `🔧 调用工具 validate_field_type` + 校验结论。若模型没有按预期点菜（正常现象，模型有自主权），如实保留实录——教学文档如实描述模型行为，不重跑粉饰。

- [ ] **Step 3: Commit（progress.md 由 Task 6 统一同步，本任务不碰）**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add outputs/chat_demo_transcript.log scripts/demo_chat_cli.py
git commit -m "feat: add headless chat CLI + real conversation transcript

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: 教学文档 + 索引 + 规划文件同步

**Files:**
- Create: `lessons/extra_chat_assistant_build.md`
- Modify: `lessons/README.md`、`docs/progress.md`、`docs/HANDOFF.md`

**Interfaces:**
- Consumes: chat_agent.py / app.py / demo_chat_cli.py / outputs/chat_demo_transcript.log（实录原文）、docs/superpowers/specs/2026-08-30-chat-assistant-design.md

- [ ] **Step 1: 写 lessons/extra_chat_assistant_build.md**

结构（零基础可读，做什么/为什么/不做会怎样）：
1. **一张图看懂**：三零件拼装（引用 extra_chat_agent.md 的零件表，给出本实现的拼法）
2. **大脑 chat_agent.py 逐块导读**：模块级状态为什么不用 st.session_state（headless 复用）；generate_protocol 为什么返回摘要不返回全文（省 token）；SYSTEM_PROMPT 四要素落位
3. **create_react_agent vs 手写循环对照表**：一行 create_react_agent = extra_langgraph_intro.py 的 Graph B（model 节点/条件边/tools 节点/END 逐项对应）；recursion limit 内置说明
4. **打字机三规则**：tool_calls → 🔧 标记（按 id 去重）；AIMessageChunk content → 逐字；ToolMessage → 不上屏。附 stream_mode="messages" 的 (chunk, metadata) 形状说明
5. **UI 薄壳导读**：st.chat_message/st.chat_input/st.write_stream 各干什么；session_state 历史；侧栏下载
6. **实跑对话原文**：从 outputs/chat_demo_transcript.log 逐字贴（裁 requests 警告行并注明）；对每段标注"模型在这一步做了什么"（点菜/思考/执行/答复）
7. **AppTest 冒烟**：CHAT_FAKE_AGENT 开关的设计（测试不花钱）；怎么跑
8. **踩坑**：Task 4/5 实际遇到的（若有）

- [ ] **Step 2: 同步索引与规划文件**

`lessons/README.md` 加一行：
```markdown
| [extra_chat_assistant_build.md](extra_chat_assistant_build.md) | 聊天助手构建全解：三零件拼装 / create_react_agent 对照手写循环 / 打字机三规则 / 实跑对话原文 | `scripts/chat_agent.py` + `app.py` + `demo_chat_cli.py` |
```

`docs/progress.md`：追加会话小节（Actions：升级 app.py 聊天窗口、chat_agent 大脑、AppTest 冒烟、真调实录、教学文档；Files 列表）。

`docs/HANDOFF.md`：
- 二、功能层面 Phase 5 表：5.1 内容改为"Streamlit 聊天窗口协议助手（create_react_agent + 两工具 + 打字机）"
- 三、卡在哪：待办 #2（app.py stream 升级）标记完成——注明"已随聊天助手升级一并兑现"
- 六、关键文件索引：app.py 行注释改为"聊天窗口协议助手（streamlit run app.py）"；scripts/ 行补 chat_agent.py / demo_chat_cli.py / demo_app_test.py；lessons/ 行补 API 手册之外的聊天构建文档

- [ ] **Step 3: 全量验证**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
echo "--- AppTest 冒烟 ---"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_app_test.py
echo "--- 实录存在且含工具标记 ---"
grep -c "🔧 调用工具" outputs/chat_demo_transcript.log
grep -c "用户\|👤" outputs/chat_demo_transcript.log
echo "--- 文档引用存在 ---"
grep -c "extra_chat_assistant_build" lessons/README.md
test -f lessons/extra_chat_assistant_build.md && echo "lesson OK"
```
Expected: 冒烟 `✅`；`🔧 调用工具` ≥ 1；用户轮 ≥ 2；README 引用 ≥ 1；lesson 存在。

- [ ] **Step 4: 最终 Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/extra_chat_assistant_build.md lessons/README.md docs/progress.md docs/HANDOFF.md
git commit -m "docs: add chat assistant build lesson + sync planning files

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```
