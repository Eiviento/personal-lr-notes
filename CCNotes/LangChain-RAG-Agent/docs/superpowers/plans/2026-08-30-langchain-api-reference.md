# LangChain API 参考手册 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出 `lessons/langchain_api_reference.md`——按模块分 9 章 26 个词条的 LangChain API 手册，每条带真实运行输出，并配套 `scripts/demo_api_reference.py` 演示脚本。

**Architecture:** 先收集素材（版本基线、签名、行号引用）到 `docs/api_ref_notes.md`；再写演示脚本并实跑捕获真实输出到 `outputs/demo_api_reference_run.log`；然后分 4 个任务把手册 9 章写出来（输出全部抄自实跑日志）；最后更新索引、全量验证、同步规划文件并提交。

**Tech Stack:** Python + LangChain 1.x（langchain_core / langchain_openai / langgraph）+ chromadb，DeepSeek API（OpenAI 兼容）。

## Global Constraints

- 手册正文与代码注释一律中文；术语表沿用 lessons/ 现有文档（如"点菜/上菜"）
- 跑脚本一律：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe`（坑 #5 控制台 GBK 吃不下 emoji；坑 #6 必须用 agent_env）
- 脚本输出路径一律以 `Path(__file__).resolve().parent.parent / "outputs"` 为基准（坑 #12）
- API Key 从环境变量 `DEEPSEEK_API_KEY` 读取，绝不硬编码进文件
- 手册第 4 段"最小示例"的输出必须**逐字抄自实跑日志**，不得手编
- git 直接提交 main（用户约定：不分特性分支）；commit message 末尾带 `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- 每完成一个任务，同步更新 `docs/progress.md`（坑 #7：教完立刻记录）

---

### Task 1: 素材收集——版本基线 + 签名 + 行号引用

**Files:**
- Create: `docs/api_ref_notes.md`

**Interfaces:**
- Produces: `docs/api_ref_notes.md`，含以下固定小节名（后续任务按名取用）：
  - `## 版本基线`（表格：包 / 版本 / 获取命令）
  - `## 词条签名`（每词条一节：`### ChatPromptTemplate`、`### ChatOpenAI`、`### with_retry`、`### bind_tools`、`### 管道运算符|`、`### RunnableLambda`、`### RunnablePassthrough`、`### RunnableParallel`、`### assign`、`### invoke/batch/stream`、`### StrOutputParser`、`### JsonOutputParser`、`### SystemMessage/HumanMessage/ToolMessage`、`### @tool`、`### StateGraph/START/END`、`### chromadb EmbeddingFunction/Embeddings/Documents`，每节贴 `inspect.signature` 输出原文 + 关键参数一句话）
  - `## 行号引用`（每词条一行：词条名 + `scripts/xxx.py:行号` 多处引用，供手册第 5 段直接抄）

- [ ] **Step 1: 查版本基线**

Run（在项目根目录）:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import langchain_core, langchain_openai, chromadb, langgraph, onnxruntime; print('langchain_core', langchain_core.__version__); print('langchain_openai', langchain_openai.__version__); print('chromadb', chromadb.__version__); print('langgraph', langgraph.__version__); print('onnxruntime', onnxruntime.__version__)"
```
Expected: 五行 `包名 版本号`，无异常。

- [ ] **Step 2: 查每个词条的签名**

Run（每条一个命令，输出贴进 notes 对应小节）:
```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_core.prompts import ChatPromptTemplate; print(inspect.signature(ChatPromptTemplate.__init__)); print(inspect.signature(ChatPromptTemplate.from_messages))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_openai import ChatOpenAI; print(inspect.signature(ChatOpenAI.__init__))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_core.runnables.base import Runnable; print('invoke:', inspect.signature(Runnable.invoke)); print('batch:', inspect.signature(Runnable.batch)); print('stream:', inspect.signature(Runnable.stream)); print('with_retry:', inspect.signature(Runnable.with_retry)); print('bind_tools:', inspect.signature(Runnable.bind_tools)); print('assign:', inspect.signature(RunnablePassthrough.assign))" 2>&1 | head -20
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_core.output_parsers import StrOutputParser, JsonOutputParser; from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough; print('StrOutputParser:', inspect.signature(StrOutputParser.__init__)); print('JsonOutputParser:', inspect.signature(JsonOutputParser.__init__)); print('RunnableLambda:', inspect.signature(RunnableLambda.__init__)); print('RunnableParallel:', inspect.signature(RunnableParallel.__init__)); print('RunnablePassthrough:', inspect.signature(RunnablePassthrough.__init__))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage; print('SystemMessage:', inspect.signature(SystemMessage.__init__)); print('HumanMessage:', inspect.signature(HumanMessage.__init__)); print('ToolMessage:', inspect.signature(ToolMessage.__init__)); print('AIMessage:', inspect.signature(AIMessage.__init__))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langchain_core.tools import tool; print('tool:', inspect.signature(tool))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect; from langgraph.graph import StateGraph; print('StateGraph:', inspect.signature(StateGraph.__init__)); print('add_node:', inspect.signature(StateGraph.add_node)); print('add_edge:', inspect.signature(StateGraph.add_edge)); print('add_conditional_edges:', inspect.signature(StateGraph.add_conditional_edges))"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -c "import inspect, chromadb; from chromadb import EmbeddingFunction, Embeddings, Documents; print('PersistentClient:', inspect.signature(chromadb.PersistentClient.__init__)); print('get_or_create_collection:', inspect.signature(chromadb.Client.get_or_create_collection)); print('query:', inspect.signature(chromadb.Client.get_or_create_collection))" 2>&1 | head -5
```
Expected: 每条命令输出该类的构造签名。若某条报错，把报错原文也记入 notes（版本差异证据）。

- [ ] **Step 3: 收集行号引用**

Run（在项目根目录，输出贴进 notes 的 `## 行号引用`）:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -n "ChatPromptTemplate" scripts/*.py | head -20
grep -n "ChatOpenAI(" scripts/*.py
grep -n "with_retry" scripts/*.py
grep -n "bind_tools" scripts/*.py
grep -n "RunnableLambda\|RunnablePassthrough\|RunnableParallel" scripts/*.py
grep -n "\.assign(" scripts/*.py
grep -n "\.invoke(\|\.batch(\|\.stream(" scripts/*.py | grep -v "tool\.invoke\|FUNC_MAP" | head -30
grep -n "StrOutputParser\|JsonOutputParser" scripts/*.py
grep -n "SystemMessage\|HumanMessage\|ToolMessage" scripts/*.py
grep -n "@tool" scripts/*.py
grep -n "StateGraph\|add_conditional_edges\|add_edge\|START\|END" scripts/*.py
grep -n "EmbeddingFunction\|Embeddings\|Documents\|PersistentClient\|get_or_create_collection\|\.query(\|\.upsert(" scripts/*.py
```
Expected: 每条 grep 有命中（行号 + 文件），全部原文记入 notes。

- [ ] **Step 4: 组装 notes 文件并验证**

写入 `docs/api_ref_notes.md`（开头注明"临时素材笔记，手册完成后删除"），按 Produces 里的小节名组织。验证:
```bash
grep -c "^### " docs/api_ref_notes.md
```
Expected: ≥ 16（16 个词条小节），且 `## 版本基线`、`## 词条签名`、`## 行号引用` 三个主节齐全。

- [ ] **Step 5: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add docs/api_ref_notes.md
git commit -m "docs: collect API reference source material (versions/signatures/line refs)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: 编写 demo_api_reference.py（9 节完整代码）

**Files:**
- Create: `scripts/demo_api_reference.py`

**Interfaces:**
- Consumes: 无（自带全部 import；节 9 函数内导入 `phase4_1_rag`）
- Produces: 脚本分节函数 `section1_prompts` ~ `section9_chroma`；`--only 1,3` 可选参数；节 4/7 在无 API Key 时打印提示并跳过。打印节头格式固定为 `节 N：第X章 标题`（Task 3 按此解析日志）。

- [ ] **Step 1: 写入完整脚本**

写入 `scripts/demo_api_reference.py`（以下为完整内容，直接照抄）:

```python
"""
API 手册配套演示：lessons/langchain_api_reference.md 的"最小示例"输出来源
======================================================================
分 9 节，一节对应手册一章。成本原则：能零成本就零成本（假消息/假函数），
必须真模型的节（4 调用 / 7 工具）才走 DeepSeek 真调。

用法：
  python demo_api_reference.py              # 跑全部 9 节
  python demo_api_reference.py --only 1,3   # 只跑指定节（逗号分隔）
跑手册示例时用完整环境（在项目根目录执行；节 9 导入同目录的 phase4_1_rag，
Python 会自动把脚本所在目录放进 sys.path，所以从哪跑都能导入）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_api_reference.py
"""

import json
import os
import sys
import time
from operator import add as list_add
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
BASE_DIR = Path(__file__).resolve().parent.parent


def ensure_api_key() -> bool:
    """节 4/7 需要真模型；没有 Key 就提示跳过（零成本节不受影响）"""
    if DEEPSEEK_API_KEY == "your-api-key-here":
        print("  ⚠ 未设置环境变量 DEEPSEEK_API_KEY，跳过本节（真模型调用）")
        return False
    return True


# ═══ 节 1：第1章 提示词 ═══════════════════════════════════════
def section1_prompts():
    """ChatPromptTemplate：角色元组 → 模板 → 填入变量（不调模型，零成本）"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是{role}，回答必须控制在{limit}字以内。"),
            ("user", "用一句话解释：{topic}"),
        ]
    )
    print("【1.1 模板定义（from_messages 用角色元组列表）】")
    print("  " + repr(prompt))
    print("\n【1.2 填入变量：invoke 只做格式化，不调模型】")
    msgs = prompt.invoke({"role": "小学老师", "limit": "50", "topic": "电压"})
    for m in msgs.to_messages():
        print(f"  [{m.type}] {m.content}")
    print("\n【1.3 缺变量 = 直接报错点名（防漏配的保护机制）】")
    try:
        prompt.invoke({"role": "小学老师"})
    except KeyError as e:
        print(f"  KeyError: {e}")


# ═══ 节 2：第2章 模型 ═══════════════════════════════════════
def section2_models():
    """ChatOpenAI：构造参数 + with_retry 坏地址演示（坏地址连不上，零成本）"""
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=4096,
    )
    print("【2.1 构造参数（常用几个）】")
    for name in ["model", "base_url", "temperature", "max_tokens", "request_timeout"]:
        print(f"  {name} = {getattr(llm, name, '<无此属性>')}")
    print("  （api_key 故意不打印）")

    print("\n【2.2 with_retry：坏地址看自动重试（重试穷尽后放弃）】")
    print("  观察：SDK 层与 LangChain 层各重试 → 双层重试现象")
    bad_llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key="fake-key",
        base_url="http://127.0.0.1:9",  # 打不开的端口
        request_timeout=2,
    ).with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
    t0 = time.time()
    try:
        bad_llm.invoke("测试")
    except Exception as e:
        print(f"  3 次重试后放弃：{type(e).__name__}（耗时 {time.time() - t0:.1f}s）")
        print("  教训：429/5xx 重试有效；4xx（认证/参数）重试永远失败")


# ═══ 节 3：第3章 管道 ═══════════════════════════════════════
def section3_runnables():
    """| 运算符 / Lambda / Passthrough / Parallel / assign（全部零成本）"""
    print("【3.1 | 运算符：把零件串成链（本质 = RunnableSequence）】")
    prompt = ChatPromptTemplate.from_messages([("user", "{x}")])
    chain = prompt | RunnableLambda(lambda m: m.to_messages()[0].content) | RunnableLambda(lambda s: s.upper())
    print(f"  chain.invoke({{'x': 'hello lcel'}}) → {chain.invoke({'x': 'hello lcel'})!r}")
    print(f"  链的类型：{type(chain).__name__}，内部步骤：{[type(s).__name__ for s in chain.steps]}")

    print("\n【3.2 RunnableLambda：普通函数包一层，就能进管道】")
    def add_exclaim(s: str) -> str:
        return s + "!!"
    chain2 = chain | RunnableLambda(add_exclaim)
    print(f"  chain2.invoke({{'x': 'hello'}}) → {chain2.invoke({'x': 'hello'})!r}")

    print("\n【3.3 RunnablePassthrough：原样透传，一个零件都不加工】")
    print(f"  RunnablePassthrough().invoke('任意输入') → {RunnablePassthrough().invoke('任意输入')!r}")

    print("\n【3.4 RunnableParallel：并行分支，分支名 = 输出键名】")
    def slow(tag):
        def f(_):
            time.sleep(1)
            return f"{tag}:睡了1秒"
        return f
    parallel = RunnableParallel(a=RunnableLambda(slow("分支A")), b=RunnableLambda(slow("分支B")))
    t0 = time.time()
    out = parallel.invoke({})
    print(f"  两个 1 秒分支同时跑，总耗时 {time.time() - t0:.1f}s → 真并行")
    print(f"  输出：{out}")
    print(f"  分支表挂在 .steps__（双下划线）：{parallel.steps__}")

    print("\n【3.5 assign：往 dict 挂新键，旧键不动】")
    assembled = RunnablePassthrough.assign(upper=chain, length=RunnableLambda(lambda s: len(s["x"])))
    print(f"  assembled.invoke({{'x': 'hello lcel'}}) → {assembled.invoke({'x': 'hello lcel'})}")


# ═══ 节 4：第4章 调用（真调 DeepSeek）═══════════════════════
def section4_calls():
    """invoke / batch / stream 三种调用方式（真模型，费用约几分钱）"""
    if not ensure_api_key():
        return
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=256,
    )
    prompt = ChatPromptTemplate.from_messages([("user", "用一个词回答：{word}的反义词")])
    chain = prompt | llm | StrOutputParser()

    print("【4.1 invoke：单输入单输出（点一份外卖）】")
    t0 = time.time()
    r = chain.invoke({"word": "快"})
    print(f"  结果：{r}（耗时 {time.time() - t0:.1f}s）")

    print("\n【4.2 batch：多输入多输出，内部并发（同时点三份）】")
    t0 = time.time()
    rs = chain.batch([{"word": "快"}, {"word": "冷"}, {"word": "大"}])
    print(f"  3 个词的结果：{rs}（耗时 {time.time() - t0:.1f}s）")

    print("\n【4.3 stream：逐块吐字（炒一道上一道）】")
    print("  ", end="", flush=True)
    for chunk in chain.stream({"word": "复杂"}):
        print(chunk, end="", flush=True)
    print()


# ═══ 节 5：第5章 解析（零成本，假 AIMessage）════════════════
def section5_parsers():
    """Str / Json 两个 Parser：模型输出永远是文字，Parser 决定它变成什么类型"""
    fake = AIMessage(content='{"name": "测试", "count": 3}')
    print("【5.1 StrOutputParser：AIMessage → 纯文本】")
    s = StrOutputParser().invoke(fake)
    print(f"  结果：{s!r}")
    print(f"  类型：{type(s).__name__}，isinstance(s, str) = {isinstance(s, str)}")
    print("  坑：langchain_core 1.x 返回 TextAccessor（str 子类）——判断用 isinstance，别用 type() == str")

    print("\n【5.2 JsonOutputParser：AIMessage → dict】")
    d = JsonOutputParser().invoke(fake)
    print(f"  结果：{d}")
    print(f"  类型：{type(d).__name__}，d['count'] + 1 = {d['count'] + 1}")

    print("\n【5.3 JsonOutputParser 的容错：剥代码围栏 + 截取花括号（= phase1_4 手写四道保险的原理）】")
    messy = AIMessage(content='好的，结果如下：\n```json\n{"ok": true}\n```\n以上。')
    print(f"  输入含围栏与废话 → 输出：{JsonOutputParser().invoke(messy)}")


# ═══ 节 6：第6章 消息（零成本）══════════════════════════════
def section6_messages():
    """三种消息对象：对话历史的最小单位"""
    sys_msg = SystemMessage("你是助手")
    human_msg = HumanMessage("你好")
    tool_msg = ToolMessage(content="校验结果：合法", tool_call_id="call_001")
    print("【6.1 三种消息对象与字段】")
    for m in [sys_msg, human_msg, tool_msg]:
        extra = f"，tool_call_id={m.tool_call_id}" if isinstance(m, ToolMessage) else ""
        print(f"  {type(m).__name__}: content={m.content!r}, type字段={m.type!r}{extra}")
    print("  ToolMessage 的 tool_call_id = 回执编号，模型靠它把结果和请求配对")

    print("\n【6.2 消息相加 = 拼对话历史（列表进，模型吃列表）】")
    msgs = [sys_msg, human_msg]
    print(f"  messages = {msgs!r}")
    print("  → 工具循环里就是 messages = messages + [response] + tool_msgs 这样拼")


# ═══ 节 7：第7章 工具（真调 1 次）═══════════════════════════
@tool
def add(a: int, b: int) -> int:
    """两个整数相加。当用户需要算加法时调用。"""
    return a + b


def section7_tools():
    """@tool / bind_tools / 工具循环：模型点菜，代码上菜"""
    print("【7.1 @tool：类型注解 → JSON Schema，docstring → 使用时机】")
    print(f"  工具名：{add.name}")
    print(f"  给模型的描述：{add.description}")
    print(f"  JSON Schema：{json.dumps(add.args_schema.model_json_schema(), ensure_ascii=False)}")
    print(f"  代码直接调用：add.invoke({{'a': 1, 'b': 2}}) → {add.invoke({'a': 1, 'b': 2})}")

    if not ensure_api_key():
        return
    print("\n【7.2 bind_tools + 工具循环（模型点菜 → 代码上菜 → 回传 → 汇总）】")
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )
    llm_tools = llm.bind_tools([add])
    messages = [HumanMessage("帮我算 123 + 456")]
    response = llm_tools.invoke(messages)
    rounds = 0
    while response.tool_calls and rounds < 5:  # 上限防死循环
        print(f"  模型点菜：{[(tc['name'], tc['args']) for tc in response.tool_calls]}")
        tool_msgs = []
        for tc in response.tool_calls:
            result = str(add.invoke(tc["args"]))  # ← 真正执行的是你的代码
            tool_msgs.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            print(f"  代码上菜：{tc['name']}({tc['args']}) → {result}")
        messages = messages + [response] + tool_msgs
        response = llm_tools.invoke(messages)
        rounds += 1
    print(f"  模型最终答复：{response.content}")


# ═══ 节 8：第8章 编排（零成本，纯 Python 节点）══════════════
def section8_langgraph():
    """StateGraph：图 = 状态 + 节点 + 边（直线图与条件边循环，均零成本）"""
    print("【8.1 直线图：LCEL 管道的超集表达】")
    class State(TypedDict):
        text: str
        log: Annotated[list, list_add]

    def node_A(state: State) -> dict:
        return {"text": state["text"].upper(), "log": ["A"]}

    def node_B(state: State) -> dict:
        return {"text": state["text"] + "!", "log": ["B"]}

    g = StateGraph(State)
    g.add_node("A", node_A)
    g.add_node("B", node_B)
    g.add_edge(START, "A")
    g.add_edge("A", "B")
    g.add_edge("B", END)
    app = g.compile()
    out = app.invoke({"text": "hello", "log": []})
    print(f"  输入 hello → 输出：{out}")
    print(f"  Annotated[list, add]：log 是追加不是覆盖 → {out['log']}")

    print("\n【8.2 条件边：循环直到满足条件（手写 while 的声明式版）】")
    class LoopState(TypedDict):
        n: int
        path: Annotated[list, list_add]

    def inc(state: LoopState) -> dict:
        return {"n": state["n"] + 1, "path": ["inc"]}

    def check(state: LoopState):
        return "inc" if state["n"] < 3 else END

    g2 = StateGraph(LoopState)
    g2.add_node("inc", inc)
    g2.add_edge(START, "inc")
    g2.add_conditional_edges("inc", check, {"inc": "inc", END: END})
    app2 = g2.compile()
    out2 = app2.invoke({"n": 0, "path": []})
    print(f"  n=0 跑完 → n={out2['n']}，path={out2['path']}（inc 跑了 3 次直到 n≥3）")


# ═══ 节 9：第9章 向量（本地 BGE，零成本）═══════════════════
def section9_chroma():
    """chromadb 三件套：用项目已有的 BGE 模型 + rag_db 真实检索"""
    from chromadb import PersistentClient
    from phase4_1_rag import LocalBertEmbedding

    print("【9.1 EmbeddingFunction 接口：Documents 进，Embeddings 出】")
    print("  实现示例：scripts/phase4_1_rag.py 的 LocalBertEmbedding（WordPiece 分词 → ONNX 推理 → CLS 池化 → 归一化）")
    print("  接口签名：def __call__(self, input: Documents) -> Embeddings")
    client = PersistentClient(path=str(BASE_DIR / "rag_db"))
    ef = LocalBertEmbedding(str(BASE_DIR / "models/bge-small-zh"), pooling="cls")
    col = client.get_collection("protocol_templates", embedding_function=ef)

    print("\n【9.2 query：真实 BGE 中文语义检索】")
    hits = col.query(query_texts=["智能水表 阀门 开关控制"], n_results=2)
    for ids, metas, dists in zip(hits["ids"][0], hits["metadatas"][0], hits["distances"][0]):
        print(f"  命中 {ids}（{metas['title']}）距离 {dists:.3f}（越小越相似）")
    print("  → '水表'语义命中水表模板（关键词搜索做不到）")


SECTIONS = {
    "1": ("第1章 提示词", section1_prompts),
    "2": ("第2章 模型", section2_models),
    "3": ("第3章 管道", section3_runnables),
    "4": ("第4章 调用", section4_calls),
    "5": ("第5章 解析", section5_parsers),
    "6": ("第6章 消息", section6_messages),
    "7": ("第7章 工具", section7_tools),
    "8": ("第8章 编排", section8_langgraph),
    "9": ("第9章 向量", section9_chroma),
}


def main():
    only = None
    if len(sys.argv) == 3 and sys.argv[1] == "--only":
        only = set(sys.argv[2].split(","))
    for key, (title, fn) in SECTIONS.items():
        if only and key not in only:
            continue
        print("=" * 70)
        print(f"节 {key}：{title}")
        print("=" * 70)
        fn()
        print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 零成本节先验（快速失败检查）**

Run（节 1/3/5/6/8 不联网不花钱）:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_api_reference.py --only 1,3,5,6,8
```
Expected: exit 0；出现 5 个节头（`节 1：第1章 提示词` 等）；节 3.4 显示"总耗时 1.x s"（并行）；无 Traceback。

- [ ] **Step 3: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add scripts/demo_api_reference.py
git commit -m "feat: add API reference demo script (9 sections, zero-cost first)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: 实跑 demo 捕获真实输出

**Files:**
- Create: `outputs/demo_api_reference_run.log`
- Modify: `docs/progress.md`（追加本任务记录）

**Interfaces:**
- Consumes: `scripts/demo_api_reference.py`（Task 2）；`models/bge-small-zh/` 与 `rag_db/`（Phase 4.1 产物）
- Produces: `outputs/demo_api_reference_run.log`——手册第 4 段输出的唯一来源，节头行格式 `节 N：第X章 标题`

- [ ] **Step 1: 前置条件检查**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
ls models/bge-small-zh/vocab.txt models/bge-small-zh/model.onnx rag_db
```
Expected: 三处都存在。若 rag_db 缺失：先跑 `PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/phase4_1_rag.py build` 重建，再继续。若 models 缺失：按 README 从 hf-mirror 下载 Xenova/bge-small-zh-v1.5。

- [ ] **Step 2: 确认 API Key 存在**

Run:
```bash
echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:+已设置}"
```
Expected: `已设置`。未设置则节 4/7 会跳过，此时把跳过提示记入日志并在手册对应词条说明"本机未设 Key，示例输出为跳过提示"——不要手编模型输出。

- [ ] **Step 3: 全量实跑，输出重定向到日志**

Run（项目根目录）:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_api_reference.py > outputs/demo_api_reference_run.log 2>&1
echo "exit=$?"
```
Expected: `exit=0`（节 2 的坏地址重试最终被 try/except 接住，不算失败）。耗时约 30~60 秒。

- [ ] **Step 4: 验证日志完整性**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -c "^节 [1-9]：" outputs/demo_api_reference_run.log
grep -n "双层重试\|Retrying" outputs/demo_api_reference_run.log | head -5
grep -n "模型点菜\|模型最终答复" outputs/demo_api_reference_run.log
grep -n "命中 " outputs/demo_api_reference_run.log
```
Expected: 节头计数 = 9；节 2 出现重试日志行；节 7 出现"模型点菜"与"模型最终答复"；节 9 出现"命中"。

- [ ] **Step 5: 同步 progress.md 并 Commit**

在 `docs/progress.md` 末尾追加：
```markdown
### 专题：LangChain API 参考手册
- **Status:** in_progress
- **Started:** 2026-08-30
- Actions taken:
  - 收集素材：版本基线 / 26 词条签名 / 行号引用 → docs/api_ref_notes.md
  - 编写 scripts/demo_api_reference.py（9 节，零成本优先）并全量实跑
  - 真实输出捕获至 outputs/demo_api_reference_run.log（手册示例的唯一来源）
```
然后:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add outputs/demo_api_reference_run.log docs/progress.md
git commit -m "feat: capture real outputs from API reference demo run

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: 手册骨架 + 第 1~2 章（提示词 / 模型）

**Files:**
- Create: `lessons/langchain_api_reference.md`

**Interfaces:**
- Consumes: `docs/api_ref_notes.md`（版本基线、ChatPromptTemplate/ChatOpenAI/with_retry/bind_tools 签名与行号引用）、`outputs/demo_api_reference_run.log`（节 1、节 2 输出）
- Produces: 手册文件，含开头块 + 目录 + 第 1、2 章；**后续任务（5/6/7）在该文件末尾追加第 3~9 章**。七段式节标题格式固定：`### <词条名>`；七段小标题固定为 `**1. 一句话**`、`**2. 签名**`、`**3. 参数表**`、`**4. 最小示例**`、`**5. 本项目在哪用到**`、`**6. 原理要点**`、`**7. 踩坑**`（Task 8 按此格式全量校验）

- [ ] **Step 1: 写开头块 + 目录 + 第 1 章**

写入 `lessons/langchain_api_reference.md`。开头块内容如下（版本表数字从 `docs/api_ref_notes.md` 的 `## 版本基线` 抄）:

```markdown
# LangChain API 参考手册（本项目用到版）

> **查词条来这里**：Ctrl+F 搜类名/方法名直达。每词条七段：一句话 / 签名 / 参数表 / 最小示例（真实输出）/ 项目出处 / 原理要点 / 踩坑。
> **概念原理**看 [00_beginner_guide.md](00_beginner_guide.md) 与 [extra_*](extra_lcel_explained.md) 专题；**逐行精读**看 code_walkthrough 系列；**按脚本查**看 [scripts_overview.md](scripts_overview.md)。
> 最小示例的输出来源：`scripts/demo_api_reference.py` 实跑日志 `outputs/demo_api_reference_run.log`（2026-08-30 跑）。

## 版本基线

| 包 | 版本 |
|----|------|
| langchain_core | （抄 notes） |
| langchain_openai | （抄 notes） |
| langgraph | （抄 notes） |
| chromadb | （抄 notes） |
| onnxruntime | （抄 notes） |

> 版本差异属正常：不同版本细节（如 StrOutputParser 返回类型）可能不同，以本表基线与实跑输出为准。

## 目录

| 章 | 词条 |
|----|------|
| [第 1 章 提示词](#第-1-章-提示词) | ChatPromptTemplate |
| [第 2 章 模型](#第-2-章-模型) | ChatOpenAI / .with_retry / .bind_tools |
| [第 3 章 管道](#第-3-章-管道) | \| / RunnableLambda / RunnablePassthrough / RunnableParallel / assign |
| [第 4 章 调用](#第-4-章-调用) | .invoke / .batch / .stream |
| [第 5 章 解析](#第-5-章-解析) | StrOutputParser / JsonOutputParser |
| [第 6 章 消息](#第-6-章-消息) | SystemMessage / HumanMessage / ToolMessage |
| [第 7 章 工具](#第-7-章-工具) | @tool / .bind_tools / 工具循环 |
| [第 8 章 编排](#第-8-章-编排) | StateGraph / START / END |
| [第 9 章 向量](#第-9-章-向量) | EmbeddingFunction / Embeddings / Documents |

---
```

第 1 章内容（词条 `ChatPromptTemplate`，七段齐全；签名从 notes 抄；示例代码块 = demo 节 1 的 1.1~1.3 代码 + 输出逐字抄自日志 `节 1` 区间；行号引用从 notes 的 `## 行号引用` 抄；原理段必须讲清"角色元组 + `{变量}` 占位 + `{{ }}` 转义"；踩坑段引用 坑 #15 与 3.2 的 missing variables 错误——见 docs/progress.md Error Log 2026-08-29 第二条）:

```markdown
# 第 1 章 提示词

### ChatPromptTemplate

**1. 一句话**：把"角色 + 内容"的对话模板声明成对象；填入变量后变成一条条真实消息，交给模型。

**2. 签名**：
（抄 notes 的 `### ChatPromptTemplate` 小节：`from langchain_core.prompts import ChatPromptTemplate` + `inspect.signature(ChatPromptTemplate.from_messages)` 原文）

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| `from_messages` 的入参 | list[tuple[str, str]] | 必填 | 每个元组 =（角色, 模板文本）；角色常用 "system" / "user" / "ai" |

**4. 最小示例**：

```python
（demo 节 1 的 1.1~1.3 代码原文）
```

输出（实跑原文）：

```
（逐字抄日志"节 1：第1章 提示词"区间）
```

**5. 本项目在哪用到**：（抄 notes 行号引用）

**6. 原理要点**：模板 = 半成品，invoke 只是字符串格式化（不调模型、零成本）；`{变量}` 是占位符，`{{ }}` 是转义（模板里要输出字面花括号——JSON 示例里到处是）；缺变量直接 KeyError 点名，是防漏配的保护机制（3.2 真踩过：assign 挂的键名与占位符不一致 → missing variables）。

**7. 踩坑**：变量名拼错不报"拼错"，报 missing variables {'xxx'}——报错里点名的就是缺的键。深挖见 [code_walkthrough_phase3.md](code_walkthrough_phase3.md)。
```

- [ ] **Step 2: 写第 2 章**

在第 1 章后追加第 2 章：三个词条 `ChatOpenAI`（含构造参数全表：model/api_key/base_url/temperature/max_tokens/request_timeout，签名与属性值抄 notes + 日志节 2 的【2.1】）、`.with_retry`（示例 = demo 2.2 代码 + 坏地址重试输出原文；原理段讲"挂在 llm 上不挂链 + 指数退避抖动防惊群 + 429/5xx 重试有效 4xx 无效"；踩坑段引用"双层重试"——SDK 层也重试，日志里 6 行 Retrying，见 phase5_2 精读）、`.bind_tools`（本章只给签名 + "详解放第 7 章"，两句话带过）。每词条同样七段。

- [ ] **Step 3: 验证第 1~2 章**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -c "^### " lessons/langchain_api_reference.md
grep -n "版本基线\|目录\|第 1 章\|第 2 章" lessons/langchain_api_reference.md | head -10
```
Expected: 词条标题计数 = 4（第 1 章 1 个 + 第 2 章 3 个）；开头的"（抄 notes）"字样必须已替换为真实内容——`grep -c "（抄"` 必须为 0。

- [ ] **Step 4: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/langchain_api_reference.md
git commit -m "docs: add API reference manual skeleton + chapters 1-2

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: 第 3~4 章（管道 / 调用）

**Files:**
- Modify: `lessons/langchain_api_reference.md`（末尾追加）

**Interfaces:**
- Consumes: `docs/api_ref_notes.md`（管道/调用类词条签名与行号引用）、`outputs/demo_api_reference_run.log`（节 3、节 4 输出）
- Produces: 手册第 3、4 章（8 个词条：`\|`、RunnableLambda、RunnablePassthrough、RunnableParallel、assign、invoke、batch、stream）

- [ ] **Step 1: 追加第 3 章**

在文件末尾追加 `# 第 3 章 管道`，5 个词条各七段（格式同 Task 4 Step 1 模板；示例代码 = demo 节 3 的 3.1~3.5 对应块；输出逐字抄日志 `节 3` 区间；行号引用抄 notes）。原理要点必须包含：
- `\|`：本质是 RunnableSequence，`.steps` 可透视内部步骤（无魔法）
- RunnableLambda：业务逻辑写普通函数，组装时才包一层（2.2 的重要模式）
- RunnablePassthrough：透传原样，常用于"保留输入 + 挂新键"
- RunnableParallel：分支并行、分支名=输出键名、分支表在 `.steps__`（**双下划线**，坑 #13）
- assign：给 dict 挂新键旧键不动；**挂的键名必须与下游 Prompt 占位符同名**（3.2 踩过的 missing variables）

- [ ] **Step 2: 追加第 4 章**

追加 `# 第 4 章 调用`，3 个词条（invoke/batch/stream）各七段（示例 = demo 节 4 的 4.1~4.3；输出抄日志 `节 4` 区间；含真实耗时数字）。开头先放三合一对比表：

| 调用方式 | 输入 | 输出 | 何时用 |
|---------|------|------|--------|
| `.invoke` | 单个 | 单个 | 单份处理 |
| `.batch` | 列表 | 列表（内部并发） | 批量处理同事文档 |
| `.stream` | 单个 | 逐块 yield | UI 打字机 |

原理要点：组装一次三种用法全有；stream 不省总时间，省的是**首字延迟**（坑 #14，用户追问过"没感觉"）；RunnableLambda 是流式边界（3.3 用 analyze_chain 而非 full_chain 的原因）。

- [ ] **Step 3: 验证**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -c "^### " lessons/langchain_api_reference.md
grep -n "第 3 章\|第 4 章\|steps__\|首字延迟" lessons/langchain_api_reference.md | head -10
```
Expected: 词条计数较 Task 4 增加 8；`steps__` 与 `首字延迟` 均出现。

- [ ] **Step 4: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/langchain_api_reference.md
git commit -m "docs: add API reference chapters 3-4 (runnables/calls)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: 第 5~7 章（解析 / 消息 / 工具）

**Files:**
- Modify: `lessons/langchain_api_reference.md`（末尾追加）

**Interfaces:**
- Consumes: `docs/api_ref_notes.md`（解析/消息/工具词条签名与行号引用）、`outputs/demo_api_reference_run.log`（节 5、6、7 输出）
- Produces: 手册第 5、6、7 章（8 个词条：StrOutputParser、JsonOutputParser、SystemMessage、HumanMessage、ToolMessage、@tool、.bind_tools、工具循环）

- [ ] **Step 1: 追加第 5 章**

`# 第 5 章 解析`，2 个词条（示例 = demo 节 5；输出抄日志 `节 5` 区间）。StrOutputParser 踩坑段必写：**langchain_core 1.x 返回 TextAccessor（str 子类），判断用 isinstance 别用 type() == str**（坑 #15，demo 5.1 输出有实证）。JsonOutputParser 原理段必写：容错三件套 = 剥围栏 + 截取花括号 + 带证据报错，原理就是 phase1_4 手写的四道保险。选型口诀：下游要文本用 Str，要结构化用 Json。

- [ ] **Step 2: 追加第 6 章**

`# 第 6 章 消息`，3 个词条各七段（示例 = demo 节 6；输出抄日志 `节 6` 区间）。ToolMessage 必写 `tool_call_id` 回执编号——模型靠它把上菜结果和点菜请求配对。原理段：messages 列表 = 对话历史，工具循环里 `messages = messages + [response] + tool_msgs` 这样拼（4.2/extra_langgraph 同款）。

- [ ] **Step 3: 追加第 7 章**

`# 第 7 章 工具`，3 个词条（示例 = demo 节 7；输出抄日志 `节 7` 区间；含"模型点菜/代码上菜/最终答复"真实原文）。@tool 原理段：类型注解 → JSON Schema（最可靠的结构化输出），docstring → 使用时机说明书。工具循环原理段：**模型只能请求调用，执行权永远在代码手里**（安全边界）；上限 5 轮防死循环。踩坑段：`tool.invoke()` 返回 str 要 `str()` 包一层（坑 #15）。深挖链接 [phase4_tool_calling.md](phase4_tool_calling.md)。

- [ ] **Step 4: 验证**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -c "^### " lessons/langchain_api_reference.md
grep -n "第 5 章\|第 6 章\|第 7 章\|TextAccessor\|tool_call_id" lessons/langchain_api_reference.md | head -10
```
Expected: 词条计数较 Task 5 增加 8；`TextAccessor` 与 `tool_call_id` 均出现。

- [ ] **Step 5: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/langchain_api_reference.md
git commit -m "docs: add API reference chapters 5-7 (parsers/messages/tools)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: 第 8~9 章（编排 / 向量）

**Files:**
- Modify: `lessons/langchain_api_reference.md`（末尾追加）

**Interfaces:**
- Consumes: `docs/api_ref_notes.md`（LangGraph/chroma 词条签名与行号引用）、`outputs/demo_api_reference_run.log`（节 8、9 输出）
- Produces: 手册第 8、9 章（6 个词条：StateGraph、START、END、EmbeddingFunction、Embeddings、Documents）

- [ ] **Step 1: 追加第 8 章**

`# 第 8 章 编排`，3 个词条（**必须各占一节**，保证全手册词条计数 = 26）：StateGraph（示例 = demo 节 8 的 8.1；原理段：图 = State + Node + Edge，图是管道的超集——能表达直线，还能表达循环/分支/暂停；`Annotated[list, add]` = 追加不覆盖）、START（一句话词条：图的入口哨兵，`add_edge(START, "首节点")`）、END（一句话词条：图的出口哨兵，也是条件边返回值的终点）。真调版引用 extra_langgraph_intro.py。深挖链接 [extra_langchain_langgraph.md](extra_langchain_langgraph.md)。踩坑段：条件边返回 END 或节点名，映射表 `{"inc": "inc", END: END}` 的写法照抄 demo。

- [ ] **Step 2: 追加第 9 章**

`# 第 9 章 向量`，3 个词条：EmbeddingFunction（示例 = demo 节 9 的 9.1；原理段：实现 `__call__(input: Documents) -> Embeddings` 即接入 chroma，内部三步分词/推理/池化见 phase4_1 精读）、Embeddings / Documents（类型别名词条：`Documents = list[str]` 文档文本，`Embeddings = list[list[float]]` 向量，两者只是类型注释，不是新对象）。示例输出抄日志 `节 9` 区间（真实 BGE 中文检索命中 + 距离）。踩坑段三连：S3 下载超时（URL 写死）→ 本地模型；MiniLM 中文失效 → 换 BGE；**换 embedding 模型必须删 rag_db 重建**（坑 #10/#11）。深挖链接 [phase4_rag.md](phase4_rag.md)。

- [ ] **Step 3: 验证（9 章齐全）**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -c "^### " lessons/langchain_api_reference.md
grep -c "^# 第 [1-9] 章" lessons/langchain_api_reference.md
```
Expected: 词条计数 = 26；章标题计数 = 9。

- [ ] **Step 4: Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/langchain_api_reference.md
git commit -m "docs: add API reference chapters 8-9 (langgraph/chroma)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: 索引更新 + 全量验证 + 清理 + 同步 + 提交

**Files:**
- Modify: `lessons/README.md`（索引表新增一行）
- Delete: `docs/api_ref_notes.md`（素材已被手册吸收）
- Modify: `docs/task_plan.md`、`docs/progress.md`、`docs/HANDOFF.md`
- Test: 无新增代码（验证即测试）

- [ ] **Step 1: 更新 lessons/README.md 索引**

在索引表最后新增一行：
```markdown
| [langchain_api_reference.md](langchain_api_reference.md) | **API 手册（查词条来这里）**：9 章 26 词条七段式（签名/参数表/真实输出示例/项目出处/原理/踩坑）+ 配套 demo 脚本 | `scripts/demo_api_reference.py` |
```

- [ ] **Step 2: 全量验证（对照规格 6 条验证标准）**

Run:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
echo "--- 标准1：demo 实跑通过、日志在 ---"
test -s outputs/demo_api_reference_run.log && echo OK
echo "--- 标准2：26 词条、9 章、每词条七段 ---"
grep -c "^### " lessons/langchain_api_reference.md
grep -c "^# 第 [1-9] 章" lessons/langchain_api_reference.md
grep -c "\*\*7\. 踩坑\*\*" lessons/langchain_api_reference.md
echo "--- 标准3：版本基线表无占位符 ---"
grep -c "（抄" lessons/langchain_api_reference.md
echo "--- 标准4：索引已更新 ---"
grep -c "langchain_api_reference.md" lessons/README.md
echo "--- 标准5：相对链接目标存在 ---"
for f in 00_beginner_guide.md extra_lcel_explained.md scripts_overview.md code_walkthrough_phase3.md phase4_tool_calling.md extra_langchain_langgraph.md phase4_rag.md; do test -f "lessons/$f" && echo "OK $f"; done
```
Expected：标准1 OK；标准2 输出 `26`、`9`、`26`（七段计数=词条数）；标准3 输出 `0`；标准4 ≥1；标准5 七个 OK。

- [ ] **Step 3: 行号引用抽查**

从手册任选 3 处 `scripts/xxx.py:行号` 引用，打开对应文件核对该行确实出现对应 API（grep 复核即可）:
```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
grep -n "ChatPromptTemplate" scripts/phase2_1_langchain_basics.py | head -3
grep -n "with_retry" scripts/phase5_2_robust.py
grep -n "StateGraph" scripts/extra_langgraph_intro.py | head -3
```
Expected: 手册引用与 grep 结果一致。不一致的立即修正手册后重跑本步。

- [ ] **Step 4: 删除素材笔记**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git rm docs/api_ref_notes.md
```

- [ ] **Step 5: 同步规划文件**

`docs/task_plan.md` 在 `## Phases` 之后新增：
```markdown
## 专题任务
- [x] 专题：LangChain API 参考手册（9 章 26 词条 + demo_api_reference.py + 真实输出，全量验证通过）
- [ ] 5.3 整体验收：用户真实需求文档全流程（仍待用户素材）
```

`docs/progress.md` 专题小节 Status 改 `complete`，Actions taken 追加：手册 9 章完成（输出全部抄自实跑日志）、索引更新、全量验证通过、素材笔记删除。

`docs/HANDOFF.md`：
- 二、教学层面落盘产物列表加一行：`lessons/langchain_api_reference.md`：API 手册（9 章 26 词条七段式，查词条入口）
- 四、下一步计划第 1 条不变；教学纪律不变
- 六、关键文件索引 lessons/ 行补充 API 手册

- [ ] **Step 6: 最终 Commit**

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
git add lessons/README.md docs/task_plan.md docs/progress.md docs/HANDOFF.md
git commit -m "docs: update indexes and planning files for API reference manual

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```
