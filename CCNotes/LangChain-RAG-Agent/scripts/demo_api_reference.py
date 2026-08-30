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
