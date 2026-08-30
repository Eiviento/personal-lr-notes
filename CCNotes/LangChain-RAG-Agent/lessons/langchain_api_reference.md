# LangChain API 参考手册（本项目用到版）

> **查词条来这里**：Ctrl+F 搜类名/方法名直达。每词条七段：一句话 / 签名 / 参数表 / 最小示例（真实输出）/ 项目出处 / 原理要点 / 踩坑。
> **概念原理**看 [00_beginner_guide.md](00_beginner_guide.md) 与 [extra_*](extra_lcel_explained.md) 专题；**逐行精读**看 code_walkthrough 系列；**按脚本查**看 [scripts_overview.md](scripts_overview.md)。
> 最小示例的输出来源：`scripts/demo_api_reference.py` 实跑日志 `outputs/demo_api_reference_run.log`（2026-08-30 跑）。

## 版本基线

| 包 | 版本 |
|----|------|
| langchain_core | 1.4.9 |
| langchain_openai | 1.3.5 |
| langgraph | 1.2.9 |
| chromadb | 1.5.9 |
| onnxruntime | 1.23.2 |

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

# 第 1 章 提示词

### ChatPromptTemplate

**1. 一句话**：把"角色 + 内容"的对话模板声明成对象；填入变量后变成一条条真实消息，交给模型。

**2. 签名**：

```python
from langchain_core.prompts import ChatPromptTemplate
```

`inspect.signature(ChatPromptTemplate.from_messages)` 原文（`__init__` 与类方法各一条）：

```text
(self, messages: 'Sequence[MessageLikeRepresentation]', *, template_format: 'PromptTemplateFormat' = 'f-string', **kwargs: 'Any') -> 'None'
(messages: 'Sequence[MessageLikeRepresentation]', template_format: 'PromptTemplateFormat' = 'f-string') -> 'ChatPromptTemplate'
```

关键参数：`messages` 是消息元组序列（如 `("system", "...")` / `("human", "...")`）；构造用 `ChatPromptTemplate.from_messages([...])`，`template_format` 默认 `f-string`。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| `from_messages` 的入参 | list[tuple[str, str]] | 必填 | 每个元组 =（角色, 模板文本）；角色常用 "system" / "user" / "ai" |

**4. 最小示例**：

```python
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
```

输出（实跑原文）：

```
【1.1 模板定义（from_messages 用角色元组列表）】
  ChatPromptTemplate(input_variables=['limit', 'role', 'topic'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=['limit', 'role'], input_types={}, partial_variables={}, template='你是{role}，回答必须控制在{limit}字以内。'), additional_kwargs={}), HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['topic'], input_types={}, partial_variables={}, template='用一句话解释：{topic}'), additional_kwargs={})])

【1.2 填入变量：invoke 只做格式化，不调模型】
  [system] 你是小学老师，回答必须控制在50字以内。
  [human] 用一句话解释：电压

【1.3 缺变量 = 直接报错点名（防漏配的保护机制）】
  KeyError: "Input to ChatPromptTemplate is missing variables {'topic', 'limit'}.  Expected: ['limit', 'role', 'topic'] Received: ['role']\nNote: if you intended {topic} to be part of the string and not a variable, please escape it with double curly braces like: '{{topic}}'.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langchain/errors/INVALID_PROMPT_INPUT "
```

**5. 本项目在哪用到**：

- `scripts/demo_parallel_merge.py:25,32,39,46`
- `scripts/phase2_1_langchain_basics.py:8,17,30,38`
- `scripts/phase2_2_lcel_pipeline.py:36,49`
- `scripts/phase2_3_output_parsers.py:23,36,49`
- `scripts/phase3_1_doc_input.py:21,47`
- `scripts/phase3_2_prompt_chain.py:32,46,59,81`（3.2 四步链的四个 Prompt 全用它）
- `scripts/phase4_1_rag.py:40`

**6. 原理要点**：模板 = 半成品，invoke 只是字符串格式化（不调模型、零成本）；`{变量}` 是占位符，`{{ }}` 是转义（模板里要输出字面花括号——JSON 示例里到处是）；缺变量直接 KeyError 点名，是防漏配的保护机制（3.2 真踩过：assign 挂的键名与占位符不一致 → missing variables）。

**7. 踩坑**：变量名拼错不报"拼错"，报 missing variables {'xxx'}——报错里点名的就是缺的键（3.2 真踩过：assign 挂的键名与占位符不一致，见 [progress.md](../docs/progress.md) Error Log 2026-08-29 第二条）。版本差异属正常，报错照实修（坑 #15）。深挖见 [code_walkthrough_phase3.md](code_walkthrough_phase3.md)。

---

# 第 2 章 模型

### ChatOpenAI

**1. 一句话**：把"调模型"封装成一个对象：给定模型名、密钥、接口地址，一句 `invoke` 就能拿到模型回复；换厂家（OpenAI → DeepSeek）只改参数，代码不动。

**2. 签名**：

```python
from langchain_openai import ChatOpenAI
```

`inspect.signature(ChatOpenAI.__init__)` 原文：

```text
(self, *args: Any, **kwargs: Any) -> None
```

关键参数：`__init__` 参数全部经 `**kwargs` 由 pydantic 配置（`model`、`temperature`、`api_key`、`base_url` 等），直接 `ChatOpenAI(model=..., temperature=...)` 调用。

**3. 参数表**（常用构造参数，全表见 2.1 实跑验证）：

| 参数 | 类型 | 本项目传的值 | 干什么用 |
|------|------|-------------|---------|
| model | str | "deepseek-chat" | 模型名；必须与厂家匹配（本项目 = DeepSeek 的对话模型） |
| api_key | str | 环境变量 DEEPSEEK_API_KEY | 调用凭证；敏感，日志里故意不打印 |
| base_url | str | "https://api.deepseek.com" | OpenAI 兼容 API 地址；换厂家只改这里（接口协议不变） |
| temperature | float | 0.3 | 采样随机性：0 = 稳定，越大越"有创意"；协议生成要确定性，所以压低 |
| max_tokens | int | 4096 | 单次回答的最大长度（token 数），防模型无限写 |
| request_timeout | float | None（未传） | 单次请求超时秒数；None = 不超时（2.2 演示里传 2 秒看重试） |

**4. 最小示例**：

```python
llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,          # "deepseek-chat"
    api_key=DEEPSEEK_API_KEY,      # 从环境变量读（demo 脚本顶部常量）
    base_url=DEEPSEEK_BASE_URL,    # "https://api.deepseek.com"
    temperature=0.3,
    max_tokens=4096,
)
for name in ["model", "base_url", "temperature", "max_tokens", "request_timeout"]:
    print(f"  {name} = {getattr(llm, name, '<无此属性>')}")
print("  （api_key 故意不打印）")
```

输出（实跑原文）：

```
【2.1 构造参数（常用几个）】
  model = deepseek-chat
  base_url = <无此属性>
  temperature = 0.3
  max_tokens = 4096
  request_timeout = None
  （api_key 故意不打印）
```

**5. 本项目在哪用到**：

- `scripts/phase2_1_langchain_basics.py:89`
- `scripts/phase2_2_lcel_pipeline.py:72`
- `scripts/phase2_3_output_parsers.py:73`
- `scripts/phase3_1_doc_input.py:137`
- `scripts/phase3_2_prompt_chain.py:98`（3.2 之后全项目复用的 llm 实例）
- `scripts/phase5_2_robust.py:91`

**6. 原理要点**：

- 为什么"换厂家只改参数"：各家模型（OpenAI / DeepSeek / 通义…）都实现了 OpenAI 兼容的 HTTP 接口，ChatOpenAI 就是把"发请求 + 拿回复"包成对象；`base_url` + `api_key` + `model` 三件套一起换 = 换厂家，业务代码不动
- 构造参数由 pydantic 校验：类型不对、必填缺失在**构造时**就报错，不会拖到调用才炸
- api_key 为什么不写死在代码里：密钥进代码 = 进 git 历史 = 泄露；从环境变量读，换人换机都不用改代码
- temperature 是"随机性旋钮"：协议生成要可复现的字段表，调低；写文案才调高

**7. 踩坑**：

- `base_url` 传参有效，但对象上**读不到同名属性**——2.1 输出里 `base_url = <无此属性>`（内部属性名不同）。别用 `getattr(llm, "base_url")` 去校验配置
- `request_timeout` 不设 = 不超时：网络黑洞时调用会一直挂着，生产建议设值（2.2 演示设 2 秒 + 重试，25.6 秒才收场）
- api_key 别写死：demo 从 `os.getenv("DEEPSEEK_API_KEY")` 读，密钥不进仓库

### .with_retry

**1. 一句话**：给 llm 包一层自动重试：失败后按"指数退避 + 抖动"再试，默认最多 3 次；重试穷尽才把异常抛出来。

**2. 签名**：

```python
llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
```

`inspect.signature` 原文（定义在 `Runnable` 基类上）：

```text
(self, *, retry_if_exception_type: 'tuple[type[BaseException], ...]' = (<class 'Exception'>,), wait_exponential_jitter: 'bool' = True, exponential_jitter_params: 'ExponentialJitterParams | None' = None, stop_after_attempt: 'int' = 3) -> 'Runnable[Input, Output]'
```

关键参数：`stop_after_attempt`（最大尝试次数，默认 3）、`wait_exponential_jitter`（指数退避+抖动，默认 True）、`retry_if_exception_type`（重试哪些异常，默认 `Exception`）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| stop_after_attempt | int | 3 | 最大尝试次数（含第一次）：3 = 失败 2 次、共试 3 次 |
| wait_exponential_jitter | bool | True | 指数退避 + 随机抖动：等 1s → 2s → 4s…再试；抖动让同时失败的客户端错开重试时刻（防惊群） |
| exponential_jitter_params | ExponentialJitterParams | None | 退避细节微调（最小/最大等待等），默认不用管 |
| retry_if_exception_type | tuple[异常类] | (Exception,) | 只对这些异常重试；默认几乎全重试 |

**4. 最小示例**：

```python
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
```

输出（实跑原文）：

```
【2.2 with_retry：坏地址看自动重试（重试穷尽后放弃）】
  观察：SDK 层与 LangChain 层各重试 → 双层重试现象
  3 次重试后放弃：APITimeoutError（耗时 25.6s）
  教训：429/5xx 重试有效；4xx（认证/参数）重试永远失败
```

**5. 本项目在哪用到**：`scripts/phase5_2_robust.py:11,55,96`（11 = 用法说明，55 = 正常路径的重试 llm，96 = 模拟失败的重试 llm）

**6. 原理要点**：

- 挂在 llm 上，不挂整条链：链上唯一可能失败的是"真模型调用"（网络）；本地步骤（格式化、解析）失败重试也没用。所以是 `ChatOpenAI(...).with_retry(...)`，不是 `chain.with_retry(...)`
- 指数退避 + 抖动 = 防惊群：一批请求同时失败时，若所有人 1 秒后同时重试，服务端会被再撞一次；加随机抖动让重试时刻错开
- 什么错值得重试：429（限流）和 5xx（服务器抖动）是"过一会儿可能就好"，重试有效；4xx（认证/参数错）重试一万次结果一样——重试是浪费，所以生产里可用 `retry_if_exception_type` 收窄范围

**7. 踩坑**：**双层重试**——ChatOpenAI 的 SDK 层自带重试（内置 max_retries）+ LangChain 层 with_retry 再重试，两层叠加：2.2 输出里"观察：SDK 层与 LangChain 层各重试 → 双层重试现象"，phase5_2 实跑日志里 Retrying 出现 6 行而不是 3 行（见 [code_walkthrough_phase5.md](code_walkthrough_phase5.md) 的 D 节）。本演示只设 stop_after_attempt=3 却耗时 25.6s 才放弃，远超"3 × 2 秒"的直觉。调参要两层都知道：想精确控制，先调低/关掉 SDK 层 max_retries，再定 LangChain 层的次数。

### .bind_tools

**1. 一句话**：把工具（函数）的签名发给模型，模型就能在回复里"点菜"式请求调用工具。本章只认签名，完整演示在第 7 章。

**2. 签名**：

```python
llm.bind_tools([add])
```

`inspect.signature` 原文（经 `ChatOpenAI` 取到；langchain_core 1.4.9 的 `Runnable` 基类上没有这个方法）：

```text
(self, tools: 'Sequence[dict[str, Any] | type | Callable | BaseTool]', *, tool_choice: 'dict | str | bool | None' = None, strict: 'bool | None' = None, parallel_tool_calls: 'bool | None' = None, response_format: '_DictOrPydanticClass | None' = None, **kwargs: 'Any') -> 'Runnable[LanguageModelInput, AIMessage]'
```

关键参数：`tools`（函数/模型/BaseTool 列表，把签名发给模型）、`tool_choice`（强制选择工具）、`strict`（严格模式）、`parallel_tool_calls`（并行工具调用）。

**3. 参数表**（只列核心参数，完整演示见第 7 章）：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| tools | list[函数/BaseTool] | 必填 | 要暴露给模型的工具；`@tool` 装饰的函数直接传入 |
| tool_choice | dict/str/bool | None | 强制模型调用指定工具；None = 模型自己决定 |

**4. 最小示例**：见第 7 章（demo 节 7 实跑输出：模型点菜 → 代码上菜 → 最终答复）。

**5. 本项目在哪用到**：`scripts/phase4_2_tool_calling.py:60,61`（`llm.bind_tools([validate_field_type])`——把字段校验工具交给模型；完整工具循环在第 7 章）

**6. 原理要点**：bind_tools 只做一件事：把函数的"签名说明书"（参数 Schema + 使用时机描述）发给模型。模型不执行，只在回复里带 `tool_calls` 请求调用——执行权永远在代码手里（安全边界，第 7 章展开）。

**7. 踩坑**：版本差异——`bind_tools` 不在 `Runnable` 基类上（langchain_core 1.4.9 实测报错 `AttributeError: type object 'Runnable' has no attribute 'bind_tools'`），直接 `ChatOpenAI(...).bind_tools(...)` 调用。更深的坑见第 7 章。

---

# 第 3 章 管道

### \|

**1. 一句话**：把零件（Prompt / 模型 / 解析器 / 函数）串成一条流水线：`a | b | c` 顺序串联，前一个零件的输出自动变成后一个零件的输入。

**2. 签名**：

```python
chain = prompt | llm | StrOutputParser()
```

`inspect.signature(Runnable.__or__)` 原文（命令来自补取）：

```text
(self, other: 'Runnable[Output, Other] | Callable[[Iterator[Output]], Iterator[Other]] | Callable[[AsyncIterator[Output]], AsyncIterator[Other]] | Callable[[Output], Other] | Mapping[str, Runnable[Output, Any] | Callable[[Output], Any] | Any]') -> 'RunnableSerializable[Input, Any]'
```

关键参数：`self` 是左侧 Runnable，`other` 是右侧 Runnable/函数/Mapping；`a | b | c` 顺序串联成一条 LCEL 管道（`Runnable.__or__`，命令来自补取）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| `self`（左侧） | Runnable | 必填 | 上游零件：它的输出就是右侧零件的输入 |
| `other`（右侧） | Runnable / 函数 / Mapping | 必填 | 下游零件：Runnable 直接接；普通函数或 dict 由 LangChain 自动包装后接入 |

**4. 最小示例**：

```python
print("【3.1 | 运算符：把零件串成链（本质 = RunnableSequence）】")
prompt = ChatPromptTemplate.from_messages([("user", "{x}")])
chain = prompt | RunnableLambda(lambda m: m.to_messages()[0].content) | RunnableLambda(lambda s: s.upper())
print(f"  chain.invoke({{'x': 'hello lcel'}}) → {chain.invoke({'x': 'hello lcel'})!r}")
print(f"  链的类型：{type(chain).__name__}，内部步骤：{[type(s).__name__ for s in chain.steps]}")
```

输出（实跑原文）：

```
【3.1 | 运算符：把零件串成链（本质 = RunnableSequence）】
  chain.invoke({'x': 'hello lcel'}) → 'HELLO LCEL'
  链的类型：RunnableSequence，内部步骤：['ChatPromptTemplate', 'RunnableLambda', 'RunnableLambda']
```

**5. 本项目在哪用到**：

- `scripts/demo_parallel_merge.py:69,70,72`
- `scripts/generate_protocol.py:35,36,37`
- `scripts/phase2_1_langchain_basics.py:114`
- `scripts/phase2_2_lcel_pipeline.py:81`
- `scripts/phase2_3_output_parsers.py:93,102`
- `scripts/phase3_1_doc_input.py:144`
- `scripts/phase3_2_prompt_chain.py:107,108,109,140,141,142,143`（3.2 四步链）
- `scripts/phase3_3_batch_stream.py:37,38,39`
- `scripts/phase4_1_rag.py:205,210,211,212,213`
- `scripts/phase4_3_human_review.py:55`
- `scripts/phase5_2_robust.py:57,58,59,60`

**6. 原理要点**：`a | b` 不是魔法运算符，它就是 `Runnable` 基类上的 `__or__` 方法（签名里 `self` = 左链、`other` = 右链），产物是一个 `RunnableSequence` 对象——3.1 输出"链的类型：RunnableSequence"是真类型名，不是比喻。无魔法的证据是 `.steps`：内部步骤就是一张表，3.1 直接打印出 `['ChatPromptTemplate', 'RunnableLambda', 'RunnableLambda']`——几个零件、各是什么类型一目了然；3.3 的 show_structure() 也是靠它拆开链逐段打印（phase3_3_batch_stream.py:46）。

**7. 踩坑**：`|` 右边可以直接接普通函数或 dict（签名里 `other` 接受 `Callable` 与 `Mapping`），LangChain 会自动包装成 Runnable 再进链——所以 `.steps` 里看到的是包装后的类型名（如 RunnableLambda），不是你写的函数名。深挖见 [extra_lcel_explained.md](extra_lcel_explained.md)（管道展开 = 普通嵌套调用，没有魔法）。

### RunnableLambda

**1. 一句话**：把普通 Python 函数包装成管道零件：业务逻辑照常写普通函数，组装链时才包一层 `RunnableLambda(函数)`，函数就能被 `|` 串进链里。

**2. 签名**：

```python
from langchain_core.runnables import RunnableLambda
```

`inspect.signature(RunnableLambda.__init__)` 原文：

```text
(self, func: 'Callable[[Input], Iterator[Output]] | Callable[[Input], Runnable[Input, Output]] | Callable[[Input], Output] | Callable[[Input, RunnableConfig], Output] | Callable[[Input, CallbackManagerForChainRun], Output] | Callable[[Input, CallbackManagerForChainRun, RunnableConfig], Output] | Callable[[Input], Awaitable[Output]] | Callable[[Input], AsyncIterator[Output]] | Callable[[Input, RunnableConfig], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun, RunnableConfig], Awaitable[Output]]', afunc: 'Callable[[Input], Awaitable[Output]] | Callable[[Input], AsyncIterator[Output]] | Callable[[Input, RunnableConfig], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun], Awaitable[Output]] | Callable[[Input, AsyncCallbackManagerForChainRun, RunnableConfig], Awaitable[Output]] | None' = None, name: 'str | None' = None) -> 'None'
```

关键参数：`func`（同步 Python 函数，可接收 `Input` 或 `Input, RunnableConfig`）、`afunc`（可选异步版）、`name`（可选命名）。普通函数经它包装成管道可用 Runnable。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| func | 同步函数 | 必填 | 要包的业务函数：收前一步的输出，返回给下一步 |
| afunc | 异步函数 | None | 异步版包装（async def 函数），同步项目用不到 |
| name | str | None | 给这一步起名，日志/调试里好认出它 |

**4. 最小示例**：

```python
print("\n【3.2 RunnableLambda：普通函数包一层，就能进管道】")
def add_exclaim(s: str) -> str:
    return s + "!!"
chain2 = chain | RunnableLambda(add_exclaim)
print(f"  chain2.invoke({{'x': 'hello'}}) → {chain2.invoke({'x': 'hello'})!r}")
```

输出（实跑原文）：

```
【3.2 RunnableLambda：普通函数包一层，就能进管道】
  chain2.invoke({'x': 'hello'}) → 'HELLO!!'
```

**5. 本项目在哪用到**：

- `scripts/demo_invoke_batch_stream.py:15,24,46`
- `scripts/demo_parallel_merge.py:26,63`
- `scripts/demo_stream_feel.py:13,23`
- `scripts/generate_protocol.py:27,37`
- `scripts/phase2_2_lcel_pipeline.py:5,37,84,85,123,125,126,127`（2.2 核心演示）
- `scripts/phase3_2_prompt_chain.py:33,122,143`（3.2 的 tap 与 merge_final）
- `scripts/phase3_3_batch_stream.py:27,39`
- `scripts/phase4_1_rag.py:41,213`
- `scripts/phase5_2_robust.py:31,60`

**6. 原理要点**：核心模式是**业务逻辑写普通函数，组装时才包一层**（2.2 的重要模式）——2.2 里 `validate_fields` / `validate_timing` / `calculate_total_bytes` 都是普通 Python 函数（能单测、能复用、不懂 LangChain 也能写），组装链时才有 `RunnableParallel(field_check=RunnableLambda(validate_fields), ...)` 这一层包装（phase2_2_lcel_pipeline.py:123,125,126,127）。包一层的意义 = 补上"输入 → 输出"的统一接口，让函数能和 Prompt、模型、Parser 一起被 `|` 串起来。函数返回值任意类型；返回生成器（yield）的函数还支持流式（demo_stream_feel.py:23）。

**7. 踩坑**：想给函数带参数，别直接写 `RunnableLambda(my_func(arg))`——参数在组装时就被求值了；要用闭包或偏函数造一个"只收一个输入参数"的函数（3.4 的 `slow(tag)` 返回 `f(_)` 就是这个套路）。另外 RunnableLambda 是**流式边界**：它必须收齐完整输入才执行、输出也一次性给出，链里夹着它，stream 的打字机效果就断在那里（详见 4.3 词条）。

### RunnablePassthrough

**1. 一句话**：原样透传：输入什么，输出就是什么，一个零件都不加工；它最常见的用法不是单独用，而是 `RunnablePassthrough.assign(键=子链)`——保留输入的同时挂上新键。

**2. 签名**：

```python
from langchain_core.runnables import RunnablePassthrough
```

`inspect.signature(RunnablePassthrough.__init__)` 原文：

```text
(self, func: 'Callable[[Other], None] | Callable[[Other, RunnableConfig], None] | Callable[[Other], Awaitable[None]] | Callable[[Other, RunnableConfig], Awaitable[None]] | None' = None, afunc: 'Callable[[Other], Awaitable[None]] | Callable[[Other, RunnableConfig], Awaitable[None]] | None' = None, *, input_type: 'type[Other] | None' = None, **kwargs: 'Any') -> 'None'
```

关键参数：无参 `RunnablePassthrough()` 原样透传 dict；`assign()` 返回新的 `RunnableAssign` 追加字段；`func`/`afunc` 是旁路副作用钩子。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| func | 函数 | None | 旁路副作用钩子：收到输入时顺带调用它（如打印、记日志），结果丢弃，透传原样继续 |
| afunc | 异步函数 | None | 同上，异步版 |
| input_type | type | None | 输入类型标注（可空） |

**4. 最小示例**：

```python
print("\n【3.3 RunnablePassthrough：原样透传，一个零件都不加工】")
print(f"  RunnablePassthrough().invoke('任意输入') → {RunnablePassthrough().invoke('任意输入')!r}")
```

输出（实跑原文）：

```
【3.3 RunnablePassthrough：原样透传，一个零件都不加工】
  RunnablePassthrough().invoke('任意输入') → '任意输入'
```

**5. 本项目在哪用到**：

- `scripts/generate_protocol.py:27,34,35,36`
- `scripts/phase2_2_lcel_pipeline.py:8,37,121,129`
- `scripts/phase3_2_prompt_chain.py:21,33,140,141,142`（3.2 四步链的 assign）
- `scripts/phase3_3_batch_stream.py:27,36,37,38`
- `scripts/phase4_1_rag.py:41,209,210,211,212`
- `scripts/phase5_2_robust.py:31,57,58,59`

**6. 原理要点**：单独用 = 什么都不做（3.3 输出 `'任意输入' → '任意输入'`）。真正常见的用法是**"保留输入 + 挂新键"**：`RunnablePassthrough.assign(键=子链)` 把输入 dict 原样保留，再往上面追加子链算出的新键——3.2 四步链就是一路挂过来的：`RunnablePassthrough.assign(key_points=analyze_chain) | RunnablePassthrough.assign(fields=fields_chain) | RunnablePassthrough.assign(checks=rules_chain) | RunnableLambda(merge_final)`，`{"requirement": 文档}` 进链，每步挂一个新键、旧键一个不动（phase3_2_prompt_chain.py:140,141,142）。签名里的 `func` 是旁路副作用钩子：透传的同时干打印/记日志的事（3.2 的 tap 用 RunnableLambda 包打印后原样返回，同一思路）。

**7. 踩坑**：`assign` 返回的是**新的** `RunnableAssign`，不是原地改 dict——必须把 `RunnablePassthrough.assign(...)` 接在 `|` 后面当链零件用，返回值丢了等于没挂键。调试时可以在链里插一个 `RunnablePassthrough()` 看上游输出长什么样（它不改数据，只让你能观察）。

### RunnableParallel

**1. 一句话**：把几个互不依赖的分支零件并排装好、同时开跑，各自的结果按分支名合成一个 dict 输出；分支名 = 输出键名。

**2. 签名**：

```python
from langchain_core.runnables import RunnableParallel
```

`inspect.signature(RunnableParallel.__init__)` 原文：

```text
(self, steps__: 'Mapping[str, Runnable[Input, Any] | Callable[[Input], Any] | Mapping[str, Runnable[Input, Any] | Callable[[Input], Any]]] | None' = None, **kwargs: 'Runnable[Input, Any] | Callable[[Input], Any] | Mapping[str, Runnable[Input, Any] | Callable[[Input], Any]]') -> 'None'
```

关键参数：每个关键字参数即一个分支（`a=chain1, b=chain2`），并行执行后合并成 dict；`steps__` 位置参数等价形式。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| 关键字参数 | Runnable / 函数 / dict | 必填 | 一个关键字 = 一个分支；分支结果挂到同名键上 |
| steps__ | Mapping | None | 分支表的位置参数写法（等价形式；注意是**双下划线**） |

**4. 最小示例**：

```python
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
```

输出（实跑原文）：

```
【3.4 RunnableParallel：并行分支，分支名 = 输出键名】
  两个 1 秒分支同时跑，总耗时 1.0s → 真并行
  输出：{'a': '分支A:睡了1秒', 'b': '分支B:睡了1秒'}
  分支表挂在 .steps__（双下划线）：{'a': RunnableLambda(f), 'b': RunnableLambda(f)}
```

**5. 本项目在哪用到**：

- `scripts/demo_parallel_merge.py:26,68`
- `scripts/phase2_2_lcel_pipeline.py:6,22,37,118,123`（2.2 三个校验分支并行）

**6. 原理要点**：

- **分支并行**：互不依赖的分支同时开跑——3.4 两个各睡 1 秒的分支，顺序跑要 2 秒，并行只花 1.0s（输出"总耗时 1.0s → 真并行"）；2.2 的 validation_chain 把字段校验、频率校验、字节数计算三个分支并排跑（phase2_2_lcel_pipeline.py:123）
- **分支名 = 输出键名**：`a=...` 的分支，结果进输出 dict 的 `a` 键——3.4 输出 `{'a': '分支A:睡了1秒', 'b': '分支B:睡了1秒'}`，分支怎么命名，输出就怎么出键
- **分支表在 `.steps__`（双下划线，坑 #13）**：签名里位置参数就叫 `steps__`，对象的属性也是它——3.4 打印 `parallel.steps__` 得到 `{'a': RunnableLambda(f), 'b': RunnableLambda(f)}`，想透视/改分支就找这个属性

**7. 踩坑**：`.steps__` 是**双下划线**（坑 #13）——和 `|` 链的 `.steps`（单下划线）不是一回事，写错就找不到属性。另外并行分支**各吃同一份输入、互相不能依赖**：分支 A 的结果想喂给分支 B，得拆成两段（先并行、再用 `|` 串下一段）；2.2 三个校验函数都只吃 LLM 输出、互不依赖，才适合并行。

### assign

**1. 一句话**：给数据流里的 dict 追加新键，旧键一个不动；新键的值由挂上的子链/函数现算——常连用 `RunnablePassthrough.assign(键=子链)`。

**2. 签名**：

```python
RunnablePassthrough.assign(键=子链)
```

`inspect.signature(RunnablePassthrough.assign)` 原文（另行补取）：

```text
(**kwargs: 'Runnable[dict[str, Any], Any] | Callable[[dict[str, Any]], Any] | Mapping[str, Runnable[dict[str, Any], Any] | Callable[[dict[str, Any]], Any]]') -> 'RunnableAssign'
```

关键参数：每个关键字=一个子链/函数，往输入 dict 追加对应键，返回 `RunnableAssign`；常连用 `| RunnablePassthrough.assign(键=子链)`。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| 关键字参数 | Runnable / 函数 / dict | 必填 | 一个关键字 = 一个新键；值由子链/函数现算，算完挂到输入 dict 上（旧键不动） |

**4. 最小示例**：

```python
print("\n【3.5 assign：往 dict 挂新键，旧键不动】")
assembled = RunnablePassthrough.assign(upper=chain, length=RunnableLambda(lambda s: len(s["x"])))
print(f"  assembled.invoke({{'x': 'hello lcel'}}) → {assembled.invoke({'x': 'hello lcel'})}")
```

输出（实跑原文）：

```
【3.5 assign：往 dict 挂新键，旧键不动】
  assembled.invoke({'x': 'hello lcel'}) → {'x': 'hello lcel', 'upper': 'HELLO LCEL', 'length': 10}
```

**5. 本项目在哪用到**：

- `scripts/generate_protocol.py:34,35,36`
- `scripts/phase2_2_lcel_pipeline.py:7`
- `scripts/phase3_2_prompt_chain.py:21,140,141,142`（3.2 四步链逐步挂键）
- `scripts/phase3_3_batch_stream.py:36,37,38`
- `scripts/phase4_1_rag.py:209,210,211,212`
- `scripts/phase5_2_robust.py:57,58,59`

**6. 原理要点**：

- **挂新键、旧键不动**：3.5 输出 `{'x': 'hello lcel', 'upper': 'HELLO LCEL', 'length': 10}`——输入 dict 的 `x` 原样保留，新增 `upper`、`length` 两个键。这正是"保留输入 + 挂新键"，是流水线逐步加料的基石
- **挂的键名必须与下游 Prompt 占位符同名**：assign 挂的键是给下游用的，下游 Prompt 写 `{key_points}` 就等着 `key_points` 这个键——3.2 真踩过：挂的键名 `protocol` 与 ③ Prompt 占位符 `{fields}` 不一致，invoke 直接报 missing variables {'fields'}。报错点名缺的键，就是防漏配的保护机制（详见 [progress.md](../docs/progress.md) Error Log 2026-08-29 第二条与第 1 章 ChatPromptTemplate 词条）
- 每个键的子链/函数独立算、只吃输入 dict：3.2 四步链三次 assign 逐步挂 key_points / fields / checks，最后 merge_final 一把取齐（phase3_2_prompt_chain.py:140,141,142,143）

**7. 踩坑**：键名与占位符不一致 → missing variables（见本词条 6 与第 1 章）；`assign` 返回新的 `RunnableAssign`，必须接在 `|` 上当零件用，返回值丢了等于没挂键。

---

# 第 4 章 调用

同一条链装好后，三种调用方式全有（4.1~4.3 用的是同一条 `chain`，换的只是调用方法）：

| 调用方式 | 输入 | 输出 | 何时用 |
|---------|------|------|--------|
| `.invoke` | 单个 | 单个 | 单份处理 |
| `.batch` | 列表 | 列表（内部并发） | 批量处理同事文档 |
| `.stream` | 单个 | 逐块 yield | UI 打字机 |

### .invoke

**1. 一句话**：单输入、单输出：给链一个输入，等它全部跑完，拿回完整结果——像点一份外卖，下单后等着，做好了一次性端上来。

**2. 签名**：

```python
r = chain.invoke({"word": "快"})
```

`inspect.signature(Runnable.invoke)` 原文（定义在 `Runnable` 基类上）：

```text
invoke: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any') -> 'Output'
```

关键参数：`invoke` 单输入返回完整输出。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| input | Input | 必填 | 单个输入；长什么样由链的第一段决定（demo 里是 dict `{"word": ...}`） |
| config | RunnableConfig | None | 运行配置（回调、超时等），默认不用传 |

**4. 最小示例**：

```python
# 4.1~4.3 共用的一条链（demo 节 4 开头组装）
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
```

输出（实跑原文）：

```
【4.1 invoke：单输入单输出（点一份外卖）】
  结果：慢（耗时 0.6s）
```

**5. 本项目在哪用到**：

- `scripts/demo_2_2_checks.py:39,58`
- `scripts/demo_invoke_batch_stream.py:28`
- `scripts/demo_parallel_merge.py:79`
- `scripts/demo_stream_feel.py:27`
- `scripts/extra_langgraph_intro.py:46,50,54,88,130,145`
- `scripts/generate_protocol.py:100`
- `scripts/phase2_1_langchain_basics.py:87,159`
- `scripts/phase2_2_lcel_pipeline.py:190`
- `scripts/phase2_3_output_parsers.py:85,94,103`
- `scripts/phase3_1_doc_input.py:147`
- `scripts/phase3_2_prompt_chain.py:196`（3.2 四步链入口）
- `scripts/phase4_1_rag.py:221,226`
- `scripts/phase4_2_tool_calling.py:66,78`
- `scripts/phase4_3_human_review.py:127`

**6. 原理要点**：**组装一次，三种用法全有**——链是装配出来的对象，invoke / batch / stream 只是它的三种调用接口（4.1~4.3 用的全是同一条 `chain`，换的只是调用方法）。invoke 内部 = 把输入依次喂给每个零件，收齐最终输出再返回；batch 是多份 invoke 的内部并发，stream 是逐块产出 invoke 的结果。

**7. 踩坑**：invoke 要等**全部**生成完才返回，期间没有任何输出——模型回复越长等得越久。demo_stream_feel.py 的场景对比：生成协议 10~30 秒的任务，invoke 让用户盯着空白转圈、以为卡死了；想"先看到字"就换 stream（4.3）。

### .batch

**1. 一句话**：多输入、多输出：给一串输入，等全部跑完，拿回与输入一一对应的结果列表；内部并发，多条同时处理——像同时点三份外卖。

**2. 签名**：

```python
rs = chain.batch([{"word": "快"}, {"word": "冷"}, {"word": "大"}])
```

`inspect.signature(Runnable.batch)` 原文（定义在 `Runnable` 基类上）：

```text
batch: (self, inputs: 'list[Input]', config: 'RunnableConfig | list[RunnableConfig] | None' = None, *, return_exceptions: 'bool' = False, **kwargs: 'Any | None') -> 'list[Output]'
```

关键参数：`batch` 输入列表、`return_exceptions` 为 True 时单条失败不中断。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| inputs | list[Input] | 必填 | 输入列表，每个元素就是一条 invoke 的输入；结果与输入一一对应 |
| config | RunnableConfig / 列表 | None | 运行配置；传列表可给每条分别配 |
| return_exceptions | bool | False | True 时某条失败不中断整批，失败位置放异常对象 |

**4. 最小示例**：

```python
# chain 同 4.1（prompt | llm | StrOutputParser）
print("\n【4.2 batch：多输入多输出，内部并发（同时点三份）】")
t0 = time.time()
rs = chain.batch([{"word": "快"}, {"word": "冷"}, {"word": "大"}])
print(f"  3 个词的结果：{rs}（耗时 {time.time() - t0:.1f}s）")
```

输出（实跑原文）：

```
【4.2 batch：多输入多输出，内部并发（同时点三份）】
  3 个词的结果：['慢', '热', '小']（耗时 0.7s）
```

**5. 本项目在哪用到**：

- `scripts/demo_invoke_batch_stream.py:33`
- `scripts/generate_protocol.py:100`
- `scripts/phase3_3_batch_stream.py:58`（批量处理同事文档）

**6. 原理要点**：**内部并发**——同一条链收到多份输入同时处理，不用自己写多线程：4.1 单个词 0.6s，4.2 三个词也只 0.7s，总时间没变成三倍。**返回顺序与输入顺序一一对应**：4.2 输入 `快/冷/大`，输出 `['慢', '热', '小']`，谁先谁后不乱。最适合"批量处理同事文档"：3.3 的 `clean_chain.batch([{"requirement": d} for d in docs])` 一次处理多份需求文档，每份内部还有 3 次 LLM 调用（phase3_3_batch_stream.py:58）。

**7. 踩坑**：batch 同样"全部跑完才返回"，结果列表一次性到手，不能边跑边看进度；要逐条进度就换 stream，或分批小批量调用。默认某条失败整批抛错中断——想"单条失败不拖累整批"用 `return_exceptions=True`，失败的位置放异常对象。

### .stream

**1. 一句话**：单输入、逐块输出：不等到全部生成完，生成一块就吐一块（返回迭代器），for 循环边收边打——打字机效果，UI 展示用。

**2. 签名**：

```python
for chunk in chain.stream({"word": "复杂"}):
    print(chunk, end="", flush=True)
```

`inspect.signature(Runnable.stream)` 原文（定义在 `Runnable` 基类上）：

```text
stream: (self, input: 'Input', config: 'RunnableConfig | None' = None, **kwargs: 'Any | None') -> 'Iterator[Output]'
```

关键参数：`stream` 按块产出迭代器。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| input | Input | 必填 | 单个输入（同 invoke） |
| config | RunnableConfig | None | 运行配置 |

**4. 最小示例**：

```python
# chain 同 4.1（prompt | llm | StrOutputParser）
print("\n【4.3 stream：逐块吐字（炒一道上一道）】")
print("  ", end="", flush=True)
for chunk in chain.stream({"word": "复杂"}):
    print(chunk, end="", flush=True)
print()
```

输出（实跑原文）：

```
【4.3 stream：逐块吐字（炒一道上一道）】
  简单
```

**5. 本项目在哪用到**：

- `scripts/demo_invoke_batch_stream.py:46`
- `scripts/demo_stream_feel.py:33`
- `scripts/phase3_3_batch_stream.py:75`（打字机效果）

**6. 原理要点**：

- **逐块 yield**：`chain.stream` 返回迭代器，模型生成一块吐一块，for 循环边收边打（4.3 代码里 `end=""` 逐块连打才有打字机效果）。demo_stream_feel.py 用 yield 的函数模拟"每 0.5 秒一个字"，把 invoke 和 stream 的差别钉死
- **不省总时间，省的是首字延迟（坑 #14）**：stream 的总耗时和 invoke 一样（模型该生成多少还是多少），差别只在"多久看到第一个字"。短输出看不出区别——4.3 的"简单"两个字，首字和全文几乎同时到，这就是用户追问过的"stream 怎么没感觉"；生成协议这种 10~30 秒的长输出才明显：invoke 前 20 秒一片空白，stream 1 秒内出第一个字
- **RunnableLambda 是流式边界**：链上夹着普通函数（RunnableLambda）的地方，流式被挡住——Lambda 必须收齐完整输入才执行，输出也一次性给出，没法逐块吐。所以 3.3 演示打字机效果时，stream 的是没有 Lambda 的 analyze_chain（prompt | llm | StrOutputParser 全程可流式），而不是带 `RunnableLambda(merge_final)` 的 full_chain（phase3_3_batch_stream.py:75）

**7. 踩坑**：分块是"生成到哪吐到哪"，别假设一次循环就收到完整回答——4.3 的 print 用 `end=""` 逐块连打，要拿完整文本得自己收块拼起来（`''.join(chunks)`）。想只流式某一段：把链拆成"可流式段（prompt | llm | parser）"和"一次性段（Lambda 处理）"，只对前者 stream——3.3 就是这么做的。
