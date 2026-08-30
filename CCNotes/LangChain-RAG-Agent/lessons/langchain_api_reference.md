# LangChain API 参考手册（本项目用到版）

> **查词条来这里**：Ctrl+F 搜类名/方法名直达。每词条七段：一句话 / 签名 / 参数表 / 最小示例（真实输出）/ 项目出处 / 原理要点 / 踩坑。
> **概念原理**看 [00_beginner_guide.md](00_beginner_guide.md) 与 [extra_*](extra_lcel_explained.md) 专题；**逐行精读**看 code_walkthrough 系列；**按脚本查**看 [scripts_overview.md](scripts_overview.md)。
> 最小示例的输出来源：`scripts/demo_api_reference.py` 实跑日志 `outputs/demo_api_reference_run.log`（2026-08-30 跑）。
> 引用约定：输出块已裁掉日志开头的 `RequestsDependencyWarning` 横幅和 `====` 分隔线；内容行逐字保留。

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
- `scripts/phase3_2_prompt_chain.py:32,46,59,81`（3.2 四步链的三个 Prompt 全用它，第④步是 Python 合并，不用 Prompt）
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

**3. 参数表**（本项目用到的常用参数，取值见 2.1 实跑验证）：

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

---

# 第 5 章 解析

### StrOutputParser

**1. 一句话**：把模型回复（AIMessage 对象）里的文本取出来，变成纯字符串——`prompt | llm | StrOutputParser()` 链尾最常见的一节，4.1~4.3 的 chain 就是它收尾。

**2. 签名**：

```python
from langchain_core.output_parsers import StrOutputParser
```

`inspect.signature(StrOutputParser.__init__)` 原文：

```text
(self, *args: Any, **kwargs: Any) -> None
```

关键参数：无参构造 `StrOutputParser()`；把 LLM 的 AIMessage 输出转成纯字符串。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 无参构造：`StrOutputParser()` 直接用，不需要配置 |

**4. 最小示例**：

```python
fake = AIMessage(content='{"name": "测试", "count": 3}')
print("【5.1 StrOutputParser：AIMessage → 纯文本】")
s = StrOutputParser().invoke(fake)
print(f"  结果：{s!r}")
print(f"  类型：{type(s).__name__}，isinstance(s, str) = {isinstance(s, str)}")
print("  坑：langchain_core 1.x 返回 TextAccessor（str 子类）——判断用 isinstance，别用 type() == str")
```

输出（实跑原文）：

```
【5.1 StrOutputParser：AIMessage → 纯文本】
  结果：'{"name": "测试", "count": 3}'
  类型：TextAccessor，isinstance(s, str) = True
  坑：langchain_core 1.x 返回 TextAccessor（str 子类）——判断用 isinstance，别用 type() == str
```

**5. 本项目在哪用到**：

- `scripts/demo_parallel_merge.py:24,69,70`
- `scripts/phase2_3_output_parsers.py:2,7,8,14,15,22,92,93,96`（Parser 三路对比的核心）
- `scripts/phase3_2_prompt_chain.py:12,31,107`
- `scripts/phase5_2_robust.py:30,57`

**6. 原理要点**：模型返回的是 AIMessage **对象**，不是纯文本——StrOutputParser 把里面的文本内容抽出来当字符串用，这就是链尾总挂着它的原因：`prompt | llm | StrOutputParser()` 的链，invoke 结果才是能直接打印、拼接、写文档的字符串（4.1~4.3 全是这么用）。**选型口诀**：下游要文本用 Str，要结构化用 Json（口诀详解见下词条）。

**7. 踩坑**：**langchain_core 1.x 返回 TextAccessor（str 子类），判断用 isinstance 别用 type() == str**（坑 #15）——5.1 输出实证：`类型：TextAccessor，isinstance(s, str) = True`。TextAccessor 是 str 的子类：拼接、比较、格式化全正常，但 `type(s) == str` 是 False——判断"是不是字符串"一律用 isinstance；对返回类型有精确要求的代码（类型检查、序列化）别假设 `type(s) is str`。这是版本差异，报错照实修（坑 #15）。深挖见 [code_walkthrough_phase2.md](code_walkthrough_phase2.md)（精读 4：Parser 三路对比）。

### JsonOutputParser

**1. 一句话**：把模型回复解析成 dict（JSON 对象）：模型输出"看起来像 JSON 的文字"时，它负责变成真 dict，还内置容错——剥围栏、截废话，5.3 演示给你看。

**2. 签名**：

```python
from langchain_core.output_parsers import JsonOutputParser
```

`inspect.signature(JsonOutputParser.__init__)` 原文：

```text
(self, *args: Any, **kwargs: Any) -> None
```

关键参数：无参构造 `JsonOutputParser()`；把 LLM 输出解析成 dict，内置容错（部分解析）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 无参构造：`JsonOutputParser()` 直接用；容错内置，不需要配置 |

**4. 最小示例**：

```python
fake = AIMessage(content='{"name": "测试", "count": 3}')
print("\n【5.2 JsonOutputParser：AIMessage → dict】")
d = JsonOutputParser().invoke(fake)
print(f"  结果：{d}")
print(f"  类型：{type(d).__name__}，d['count'] + 1 = {d['count'] + 1}")

print("\n【5.3 JsonOutputParser 的容错：剥代码围栏 + 截取花括号（= phase1_4 手写四道保险的原理）】")
messy = AIMessage(content='好的，结果如下：\n```json\n{"ok": true}\n```\n以上。')
print(f"  输入含围栏与废话 → 输出：{JsonOutputParser().invoke(messy)}")
```

输出（实跑原文）：

```
【5.2 JsonOutputParser：AIMessage → dict】
  结果：{'name': '测试', 'count': 3}
  类型：dict，d['count'] + 1 = 4

【5.3 JsonOutputParser 的容错：剥代码围栏 + 截取花括号（= phase1_4 手写四道保险的原理）】
  输入含围栏与废话 → 输出：{'ok': True}
```

**5. 本项目在哪用到**：

- `scripts/demo_parallel_merge.py:24,72`
- `scripts/phase2_1_langchain_basics.py:8,18,98,103,105`
- `scripts/phase2_2_lcel_pipeline.py:35,80`
- `scripts/phase2_3_output_parsers.py:2,8,15,22,101,102,105`
- `scripts/phase3_1_doc_input.py:20,144`
- `scripts/phase3_2_prompt_chain.py:14,16,31,108,109`（3.2 四步链的字段表解析）
- `scripts/phase4_1_rag.py:39,205`
- `scripts/phase4_3_human_review.py:32,55`
- `scripts/phase5_2_robust.py:30,58,59`

**6. 原理要点**：

- **容错三件套 = 剥围栏 + 截取花括号 + 带证据报错**：模型爱给 JSON 裹代码围栏（`` ```json `` 开头、`` ``` `` 结尾）、爱在前后加废话——5.3 输入 ``好的，结果如下：\n```json\n{"ok": true}\n```\n以上。`` 照样解析出 `{'ok': True}`。三步：① 剥掉开头结尾的围栏；② 截取第一个 `{` 到最后一个 `}` 之间的部分（废话全丢）；③ 两步都不行时**带原始输出一起报错**——报错里能看到模型原话，方便定位是格式问题还是内容问题
- **原理就是 phase1_4 手写的四道保险（剥围栏 → 截取花括号 → 带证据报错）**：`scripts/phase1_4_req_to_protocol.py:128-149` 的 `_parse_response` 就是这三件事的手写版（精读见 [code_walkthrough_phase1.md](code_walkthrough_phase1.md) 第 4 块）——后来被 JsonOutputParser 替代，原理一字不差
- **选型口诀：下游要文本用 Str，要结构化用 Json**——4.1~4.3 只要"把话说出来"（打印、拼接），用 StrOutputParser；2.2 三个校验分支、3.2 四步链要拿字段表继续加工（5.2 的 `d['count'] + 1 = 4` 就是拿解析结果当数据用），用 JsonOutputParser

**7. 踩坑**：容错只救"包裹"问题，救不了 **JSON 本身畸形**（缺引号、多逗号）——那是 `json.loads` 层面的错误，三件套兜不住。根治手段在提示词：让模型"只输出 JSON、不要解释"能大幅减少容错需求（5.3 演示的就是最常见的不合法形态）。带证据报错是这套容错的第三步：phase1_4 手写版是 `ValueError(f"无法解析 LLM 输出为 JSON，原始输出：\n{raw}")`——解析失败必须把模型原文带出来，否则无从排查。深挖见 [code_walkthrough_phase2.md](code_walkthrough_phase2.md)（精读 4：Parser 三路对比）。

---

# 第 6 章 消息

### SystemMessage

**1. 一句话**：系统消息：给模型定人设、定规则的"开场白"——对话历史里通常第一条就是它（"你是协议评审工程师……"，4.2 的评审开场）。

**2. 签名**：

```python
from langchain_core.messages import SystemMessage
```

`inspect.signature(SystemMessage.__init__)` 原文：

```text
SystemMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
```

关键参数：`content`（文本内容）、`content_blocks`（结构化内容块）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| content | str / list / None | None | 消息正文；SystemMessage 传人设与规则（"你是协议评审工程师……"，phase4_2_tool_calling.py:100） |
| content_blocks | list[内容块] | None | 结构化内容块（文本/图片/工具调用等）；普通文本消息不用管 |

**4. 最小示例**：

```python
sys_msg = SystemMessage("你是助手")
human_msg = HumanMessage("你好")
tool_msg = ToolMessage(content="校验结果：合法", tool_call_id="call_001")
print("【6.1 三种消息对象与字段】")
for m in [sys_msg, human_msg, tool_msg]:
    extra = f"，tool_call_id={m.tool_call_id}" if isinstance(m, ToolMessage) else ""
    print(f"  {type(m).__name__}: content={m.content!r}, type字段={m.type!r}{extra}")
print("  ToolMessage 的 tool_call_id = 回执编号，模型靠它把结果和请求配对")
```

输出（实跑原文）：

```
【6.1 三种消息对象与字段】
  SystemMessage: content='你是助手', type字段='system'
  HumanMessage: content='你好', type字段='human'
  ToolMessage: content='校验结果：合法', type字段='tool'，tool_call_id=call_001
  ToolMessage 的 tool_call_id = 回执编号，模型靠它把结果和请求配对
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:22,93,98,140,143`（140 = 真调版的系统人设）
- `scripts/phase4_2_tool_calling.py:10,26,76,100,105`（100 = 4.2 的评审人设开场）

**6. 原理要点**：**messages 列表 = 对话历史**——模型没有记忆，每次调用你把整个列表发回去，它才"记得"前面说了什么；SystemMessage 是这条历史的"人设/规则"部分，通常第一条。6.1 输出 `type字段='system'`——消息对象自己知道自己的角色；第 1 章 ChatPromptTemplate 的角色元组（"system"/"user"）最终也编译成这些消息对象（1.1 输出里的 SystemMessagePromptTemplate 就是它的模板版）。

**7. 踩坑**：人设与规则写 SystemMessage，别混进 HumanMessage——模型对两类消息的处理权重不同，规则放 human 位容易被当成对话内容稀释。对话历史只增不改：改历史里旧消息 = 篡改历史，模型无从知晓；要改人设就换新 SystemMessage 追加（拼法见 HumanMessage 词条）。

### HumanMessage

**1. 一句话**：用户消息：对话历史里"用户说的话"——4.2 的字段表输入、demo 7.2 的"帮我算 123 + 456"都是它。

**2. 签名**：

```python
from langchain_core.messages import HumanMessage
```

`inspect.signature(HumanMessage.__init__)` 原文：

```text
HumanMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
```

关键参数：`content`（文本内容）、`content_blocks`（结构化内容块）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| content | str / list / None | None | 消息正文；HumanMessage 传用户提问/输入（4.2 把字段表 JSON 当用户输入：phase4_2_tool_calling.py:105） |
| content_blocks | list[内容块] | None | 结构化内容块；普通文本不用管 |

**4. 最小示例**：

```python
print("\n【6.2 消息相加 = 拼对话历史（列表进，模型吃列表）】")
msgs = [sys_msg, human_msg]
print(f"  messages = {msgs!r}")
print("  → 工具循环里就是 messages = messages + [response] + tool_msgs 这样拼")
```

（`sys_msg` / `human_msg` 的定义见 SystemMessage 词条的 6.1 代码。）

输出（实跑原文）：

```
【6.2 消息相加 = 拼对话历史（列表进，模型吃列表）】
  messages = [SystemMessage(content='你是助手', additional_kwargs={}, response_metadata={}), HumanMessage(content='你好', additional_kwargs={}, response_metadata={})]
  → 工具循环里就是 messages = messages + [response] + tool_msgs 这样拼
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:22,93,98,140,143`（143 = 真调版的用户输入）
- `scripts/phase4_2_tool_calling.py:10,26,76,100,105`（105 = 4.2 的字段表输入）

**6. 原理要点**：**messages 列表 = 对话历史，模型吃的是列表**（6.2："列表进，模型吃列表"）——`llm.invoke(messages)` 收的是消息列表，不是单个字符串；列表里每条消息一个角色，模型按顺序读。**工具循环里就是 `messages = messages + [response] + tool_msgs` 这样拼**：旧历史 + 模型这轮的回复（AIMessage）+ 工具回执（ToolMessage 们），拼成新历史再发回去——模型就是这样"看见"上菜结果的（demo_api_reference.py:239；4.2 的 run_tool_loop 同款，phase4_2_tool_calling.py:77；extra_langgraph 的工具节点也是这个套路）。

**7. 踩坑**：拼历史**必须包含上一轮的 response**——只拼 tool_msgs 不拼 response，模型没看到自己发过的点菜请求，会以为结果是凭空出现的；demo 的写法 `messages = messages + [response] + tool_msgs` 三样一个不少（顺序：旧历史、模型回复、工具回执）。对话历史是只增不改的列表，追加要"带上下文"拼（`messages = messages + [...]`），别只保留新消息。

### ToolMessage

**1. 一句话**：工具回执消息：代码执行完工具后，把结果以消息形式回传给模型——它带着 `tool_call_id` 回执编号，模型靠它把"上菜结果"和"点菜请求"配对。

**2. 签名**：

```python
from langchain_core.messages import ToolMessage
```

`inspect.signature(ToolMessage.__init__)` 原文：

```text
ToolMessage: (self, content: str | list[str | dict[typing.Any, typing.Any]] | None = None, content_blocks: list[langchain_core.messages.content.TextContentBlock | langchain_core.messages.content.InvalidToolCall | langchain_core.messages.content.ReasoningContentBlock | langchain_core.messages.content.NonStandardContentBlock | langchain_core.messages.content.ImageContentBlock | langchain_core.messages.content.VideoContentBlock | langchain_core.messages.content.AudioContentBlock | langchain_core.messages.content.PlainTextContentBlock | langchain_core.messages.content.FileContentBlock | langchain_core.messages.content.ToolCall | langchain_core.messages.content.ToolCallChunk | langchain_core.messages.content.ServerToolCall | langchain_core.messages.content.ServerToolCallChunk | langchain_core.messages.content.ServerToolResult] | None = None, **kwargs: Any) -> None
```

关键参数：`content`（文本内容）、`content_blocks`（结构化内容块）；ToolMessage 还常用 `tool_call_id=`（经 `**kwargs`）关联到模型发出的工具调用。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| content | str / list / None | None | 工具执行结果的文本（demo：`"校验结果：合法"`、`"579"`） |
| content_blocks | list[内容块] | None | 结构化内容块；普通文本不用管 |
| tool_call_id | str | 回传时必填 | **回执编号**：填模型点菜请求里的 `tc["id"]`，模型靠它把结果和请求配对 |

**4. 最小示例**：

```python
tool_msg = ToolMessage(content="校验结果：合法", tool_call_id="call_001")
print("【6.1 三种消息对象与字段】")
for m in [sys_msg, human_msg, tool_msg]:
    extra = f"，tool_call_id={m.tool_call_id}" if isinstance(m, ToolMessage) else ""
    print(f"  {type(m).__name__}: content={m.content!r}, type字段={m.type!r}{extra}")
print("  ToolMessage 的 tool_call_id = 回执编号，模型靠它把结果和请求配对")
```

（完整 6.1 代码见 SystemMessage 词条，此处只摘 ToolMessage 相关行；`sys_msg` / `human_msg` 定义在上词条。）

输出（实跑原文）：

```
【6.1 三种消息对象与字段】
  SystemMessage: content='你是助手', type字段='system'
  HumanMessage: content='你好', type字段='human'
  ToolMessage: content='校验结果：合法', type字段='tool'，tool_call_id=call_001
  ToolMessage 的 tool_call_id = 回执编号，模型靠它把结果和请求配对
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:22,93,98,140,143`（93 = 工具节点说明、98 = 真调版回传 ToolMessage）
- `scripts/phase4_2_tool_calling.py:10,26,76,100,105`（76 = 4.2 回传 `ToolMessage(content=..., tool_call_id=tc["id"])`）

**6. 原理要点**：**`tool_call_id` = 回执编号，模型靠它把上菜结果和点菜请求配对**——模型发出的每条点菜请求（`response.tool_calls` 里的每一项）都带一个 id（`tc["id"]`）；代码执行完回传时，把同一个 id 写进 ToolMessage（demo 7.2：`ToolMessage(content=result, tool_call_id=tc["id"])`），模型一看编号就知道"579 是 123+456 那次请求的结果"。6.1 输出 `tool_call_id=call_001` 是演示编号，真实流程里编号来自模型请求。**一个点菜请求配一条 ToolMessage**——多个工具并行点菜时，每个请求各自一条回执、编号一一对应（demo 7.2 的循环里就是逐条 append）。

**7. 踩坑**：**忘传 tool_call_id = 模型配对不上**——要么报错、要么模型把结果安到错误的请求上；id 必须原样抄模型请求里的 `tc["id"]`，不能自己编（demo 和 4.2 都是 `tool_call_id=tc["id"]` 直取）。另外 content 要**字符串**：工具返回的是函数原值（demo 的 add 返回 int），塞 ToolMessage 前要 `str()` 包一层（坑 #15 的同类问题，第 7 章工具循环词条展开）。

---

# 第 7 章 工具

### @tool

**1. 一句话**：装饰器：把普通 Python 函数变成"工具"——自动生成参数 JSON Schema（模型填参的硬约束）和使用时机描述（模型点不点菜的依据），绑定后模型就能在回复里请求调用它。

**2. 签名**：

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """两个整数相加。当用户需要算加法时调用。"""
    return a + b
```

`inspect.signature(tool)` 原文：

```text
(name_or_callable: str | collections.abc.Callable[..., typing.Any] | None = None, runnable: Optional[langchain_core.runnables.base.Runnable[Any, Any]] = None, *args: Any, description: str | None = None, return_direct: bool = False, args_schema: type[pydantic.main.BaseModel] | type[pydantic.v1.main.BaseModel] | dict[str, typing.Any] | None = None, infer_schema: bool = True, response_format: Literal['content', 'content_and_artifact'] = 'content', parse_docstring: bool = False, error_on_invalid_docstring: bool = True, extras: dict[str, typing.Any] | None = None) -> langchain_core.tools.base.BaseTool | collections.abc.Callable[[typing.Union[collections.abc.Callable[..., typing.Any], langchain_core.runnables.base.Runnable[typing.Any, typing.Any]]], langchain_core.tools.base.BaseTool]
```

关键参数：直接 `@tool`（无括号）或 `@tool(description=..., args_schema=...)`；`infer_schema` 默认从类型注解推断参数 schema；`parse_docstring` 从 docstring 解析描述；`response_format` 可选 `'content'` 或 `'content_and_artifact'`。

**3. 参数表**（常用参数；其余默认不用管）：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| name_or_callable | str / 函数 | None | 直接 `@tool` 时 = 被装饰的函数本身；`@tool("改名")` 时 = 给工具起别的名字 |
| description | str | None | 手动指定给模型的描述；不传默认用 docstring（7.1 输出"给模型的描述" = docstring 原文） |
| args_schema | pydantic 模型 / dict | None | 手动指定参数 Schema；不传则从类型注解推断（配合 infer_schema） |
| infer_schema | bool | True | 从函数类型注解自动生成参数 JSON Schema（7.1 的 JSON Schema 就是这么来的） |
| return_direct | bool | False | True = 工具结果直接当最终答复返回（不回传模型）；False（默认）= 回传模型继续推理 |
| parse_docstring | bool | False | 从 docstring 解析参数级描述；默认 False = docstring 整体当描述 |

**4. 最小示例**：

```python
@tool
def add(a: int, b: int) -> int:
    """两个整数相加。当用户需要算加法时调用。"""
    return a + b

print("【7.1 @tool：类型注解 → JSON Schema，docstring → 使用时机】")
print(f"  工具名：{add.name}")
print(f"  给模型的描述：{add.description}")
print(f"  JSON Schema：{json.dumps(add.args_schema.model_json_schema(), ensure_ascii=False)}")
print(f"  代码直接调用：add.invoke({{'a': 1, 'b': 2}}) → {add.invoke({'a': 1, 'b': 2})}")
```

输出（实跑原文）：

```
【7.1 @tool：类型注解 → JSON Schema，docstring → 使用时机】
  工具名：add
  给模型的描述：两个整数相加。当用户需要算加法时调用。
  JSON Schema：{"description": "两个整数相加。当用户需要算加法时调用。", "properties": {"a": {"title": "A", "type": "integer"}, "b": {"title": "B", "type": "integer"}}, "required": ["a", "b"], "title": "add", "type": "object"}
  代码直接调用：add.invoke({'a': 1, 'b': 2}) → 3
```

**5. 本项目在哪用到**：`scripts/phase4_2_tool_calling.py:41`（validate_field_type——字段校验工具：类型注解 + docstring 与 demo 的 add 同款套路）

**6. 原理要点**：

- **类型注解 → JSON Schema（最可靠的结构化输出）**：7.1 输出里 `"properties": {"a": {"title": "A", "type": "integer"}, "b": {"title": "B", "type": "integer"}}, "required": ["a", "b"]` 就是从 `def add(a: int, b: int) -> int` 自动生成的——参数约束由**代码声明**，不靠模型猜。这就是"最可靠的结构化输出"：模型按 Schema 填参，类型、必填都由 Schema 硬约束，模型填错是它的错，不是代码的错
- **docstring → 使用时机说明书**：7.1 输出"给模型的描述：两个整数相加。当用户需要算加法时调用。"——docstring 告诉模型**什么时候该用这个工具**，这是模型决定"点不点菜"的依据（4.2 里 validate_field_type 的 docstring 连参数含义都写清了）
- **装饰后仍是普通对象**：`add.invoke({'a': 1, 'b': 2}) → 3`——代码里想直接调用就调用，不用等模型

**7. 踩坑**：**docstring 不写使用时机 = 模型不知道该不该用它**——描述空着或写实现细节，模型要么不点菜、要么乱点菜；docstring 面向"使用场景"写（何时用、参数是什么含义），不写实现。**类型注解别省**：不写注解也能装饰，但 infer_schema 推断不出参数类型，生成的 Schema 少了类型约束，参数质量全凭模型自觉。深挖见 [phase4_tool_calling.md](phase4_tool_calling.md)。

### .bind_tools

**1. 一句话**：把工具的"签名说明书"（JSON Schema + 描述）发给模型，模型从此能在这段对话里"点菜"式请求调用工具——一次绑定、多次调用；它只发请求，执行还是代码的事（第 2 章只认签名，这里是完整演示）。

**2. 签名**：`inspect.signature` 原文与第 2 章词条相同（经 `ChatOpenAI` 取到；langchain_core 1.4.9 的 `Runnable` 基类上没有这个方法）：

```python
llm_tools = llm.bind_tools([add])
```

```text
(self, tools: 'Sequence[dict[str, Any] | type | Callable | BaseTool]', *, tool_choice: 'dict | str | bool | None' = None, strict: 'bool | None' = None, parallel_tool_calls: 'bool | None' = None, response_format: '_DictOrPydanticClass | None' = None, **kwargs: 'Any') -> 'Runnable[LanguageModelInput, AIMessage]'
```

关键参数：`tools`（@tool 函数/模型/BaseTool 列表）、`tool_choice`（强制指定工具）；返回 `Runnable[LanguageModelInput, AIMessage]`——绑定后 invoke 返回 AIMessage，点菜单在 `.tool_calls` 里。

**3. 参数表**（只列核心参数）：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| tools | list[函数/BaseTool] | 必填 | 要暴露给模型的工具；`@tool` 装饰的函数直接传入 |
| tool_choice | dict / str / bool | None | 强制模型调用指定工具；None = 模型自己决定 |
| strict | bool | None | 严格模式（参数严格按 Schema 校验），默认不设 |
| parallel_tool_calls | bool | None | 是否允许模型一次点多个菜（并行工具调用），默认不设 |

**4. 最小示例**：

```python
# 绑定 + 首次调用（demo 节 7 的 7.2 前半段；while 循环见"工具循环"词条）
llm_tools = llm.bind_tools([add])
messages = [HumanMessage("帮我算 123 + 456")]
response = llm_tools.invoke(messages)
# → 模型不执行，只回一个"点菜单"：response.tool_calls（打印在循环里）
```

输出（实跑原文，7.2 日志首两行）：

```
【7.2 bind_tools + 工具循环（模型点菜 → 代码上菜 → 回传 → 汇总）】
  模型点菜：[('add', {'a': 123, 'b': 456})]
```

（完整 7.2 输出——代码上菜、最终答复——见"工具循环"词条。）

**5. 本项目在哪用到**：

- `scripts/phase4_2_tool_calling.py:60,61`（`llm.bind_tools([validate_field_type])`——把字段校验工具交给模型）
- `scripts/demo_api_reference.py:228`（demo 节 7 的 `llm.bind_tools([add])`）

**6. 原理要点**：bind_tools 只做一件事：**把函数的"签名说明书"发给模型**——参数 Schema（怎么填）+ 描述（什么时候用）。之后模型每次回复都可能带 `.tool_calls`（点菜单）：`[('add', {'a': 123, 'b': 456})]`——这是**请求**不是执行：模型只负责"决定要不要算、算哪两个数"，真正执行在代码（见"工具循环"词条）。demo 里温度设 0（`temperature=0`）：工具调用要确定性，别让模型随机发挥。

**7. 踩坑**：`bind_tools` 不在 `Runnable` 基类上（langchain_core 1.4.9 实测 `AttributeError: type object 'Runnable' has no attribute 'bind_tools'`，见第 2 章词条）——直接 `ChatOpenAI(...).bind_tools(...)` 调用。绑定的工具名要对得上执行时的映射表：点菜单里工具名找不到对应函数，执行就 KeyError——4.2 的做法是一张 `FUNC_MAP = {"validate_field_type": validate_field_type}` 名字→函数的表（phase4_2_tool_calling.py:55）。

### 工具循环

**1. 一句话**：手写 while 循环把"模型点菜 → 代码执行 → 结果回传 → 再问模型"转起来，直到模型不再点菜——这是 Function Calling 的标准用法（生产环境用 LangGraph 替代手写循环，但原理就是这段循环）。

**2. 签名**：无函数签名——这是**模式**（手写 while 循环），不是 API 方法：

```python
while response.tool_calls and rounds < 5:  # 上限防死循环
    ...
```

关键参数：循环条件 `response.tool_calls`（模型有点菜请求才进循环）+ `rounds < 5`（5 轮上限防死循环）。

**3. 参数表**：无参数——循环体三个关键动作：

| 动作 | 代码 | 干什么用 |
|------|------|---------|
| 执行 | `result = str(add.invoke(tc["args"]))` | **真正执行工具的是你的代码**（模型只发了参数 JSON） |
| 回传 | `ToolMessage(content=result, tool_call_id=tc["id"])` | 把执行结果写给模型，带上回执编号配对（第 6 章 ToolMessage） |
| 拼历史 | `messages = messages + [response] + tool_msgs` | 旧历史 + 模型回复 + 工具回执，拼成新历史再发回去（第 6 章 HumanMessage） |

**4. 最小示例**：

```python
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
```

输出（实跑原文）：

```
【7.2 bind_tools + 工具循环（模型点菜 → 代码上菜 → 回传 → 汇总）】
  模型点菜：[('add', {'a': 123, 'b': 456})]
  代码上菜：add({'a': 123, 'b': 456}) → 579
  模型最终答复：123 + 456 = **579**。
```

**5. 本项目在哪用到**：

- `scripts/phase4_2_tool_calling.py:64,68,77`（run_tool_loop：64 函数定义、68 循环条件带 5 轮上限、77 拼历史）
- `scripts/demo_api_reference.py:232,239`（demo 节 7 的同款循环：232 循环条件、239 拼历史）

**6. 原理要点**：

- **模型只能请求调用，执行权永远在代码手里（安全边界）**：循环里"执行"就一行 `add.invoke(tc["args"])`——模型发来的只是参数 JSON（`{'a': 123, 'b': 456}`），算 123+456 的是你的代码。这意味着工具能干什么、不能干什么由你定义：模型再怎么"想调用"也碰不到你的文件/网络，除非你专门写一个会碰它们的工具（4.2 的 validate_field_type 只查常量表，零风险）。这是 Function Calling 与"让 AI 直接跑代码"的本质区别，也是它能安全接入业务系统的原因
- **上限 5 轮防死循环**：循环条件 `rounds < 5`——模型万一反复点菜（陷入"再校验一次"的死循环），5 轮封顶后直接把当前回复当最终答复；没有上限，一次失控对话能无限烧 token
- **配对靠 tool_call_id**：每条点菜请求带 `tc["id"]`，回传的 ToolMessage 写同一个 id（第 6 章 ToolMessage 词条）——模型据此把上菜结果和点菜请求对上
- 7.2 的真实流程：`模型点菜：[('add', {'a': 123, 'b': 456})]` → `代码上菜：add({'a': 123, 'b': 456}) → 579` → `模型最终答复：123 + 456 = **579**。`——模型只负责"决定算什么"，结果全部来自代码

**7. 踩坑**：

- **`tool.invoke()` 返回类型不可控，要 `str()` 包一层**（坑 #15）：工具返回什么类型，invoke 就返回什么——demo 的 add 返回 int，而 ToolMessage 的 content 要字符串，所以 `result = str(add.invoke(tc["args"]))` 必须包（demo_api_reference.py:236，注释"← 真正执行的是你的代码"）；4.2 里 validate_field_type 返回 str 也照样包，保证类型干净。这和 StrOutputParser 的 TextAccessor 是同一家族（坑 #15：langchain_core 1.x 返回类型与直觉不符，版本差异照实修）
- **漏拼历史 = 模型失忆**：每次 invoke 都要把上一轮的 response 和 tool_msgs 追加进 messages 再发（`messages = messages + [response] + tool_msgs`）；漏了哪一样，模型就看不到自己的点菜或你的上菜（第 6 章 HumanMessage 词条）
- 深挖见 [phase4_tool_calling.md](phase4_tool_calling.md)

---

# 第 8 章 编排

LCEL 管道是直线（第 3 章）；本章的图是它的超集——State（状态）+ Node（节点）+ Edge（边）还能表达循环、分支、暂停。8.1~8.2 全程零成本（纯 Python 节点，不调模型）。

### StateGraph

**1. 一句话**：把流程声明成"图"：State（全局状态）+ Node（节点函数）+ Edge（边），节点只写"这一站干什么"、边决定"下一步去哪"——比 LCEL 管道多出循环、分支、暂停的能力，是管道的超集。

**2. 签名**：

```python
from langgraph.graph import END, START, StateGraph
```

`inspect.signature` 原文（StateGraph 构造与三个方法各一条）：

```text
StateGraph: (self, state_schema: 'type[StateT]', context_schema: 'type[ContextT] | None' = None, *, input_schema: 'type[InputT] | None' = None, output_schema: 'type[OutputT] | None' = None, **kwargs: 'Unpack[DeprecatedKwargs]') -> 'None'
add_node: (self, node: 'str | StateNode[NodeInputT, ContextT]', action: 'StateNode[NodeInputT, ContextT] | None' = None, *, defer: 'bool' = False, metadata: 'dict[str, Any] | None' = None, input_schema: 'type[NodeInputT] | None' = None, retry_policy: 'RetryPolicy | Sequence[RetryPolicy] | None' = None, cache_policy: 'CachePolicy | None' = None, error_handler: 'StateNode[Any, ContextT] | None' = None, destinations: 'dict[str, str] | tuple[str, ...] | None' = None, timeout: 'float | timedelta | TimeoutPolicy | None' = None, **kwargs: 'Unpack[DeprecatedKwargs]') -> 'Self'
add_edge: (self, start_key: 'str | list[str]', end_key: 'str') -> 'Self'
add_conditional_edges: (self, source: 'str', path: 'Callable[..., Hashable | Sequence[Hashable]] | Callable[..., Awaitable[Hashable | Sequence[Hashable]]] | Runnable[Any, Hashable | Sequence[Hashable]]', path_map: 'dict[Hashable, str] | list[str] | None' = None) -> 'Self'
```

关键参数：`state_schema`（状态 schema，必填）；`add_node(node, action)`（`action` 可为字符串函数名或函数）；`add_edge(start_key, end_key)`；`add_conditional_edges(source, path, path_map)`（`path` 返回分支键，`path_map` 映射到节点名）。`START`/`END` 是图内置哨兵常量，`g.add_edge(START, "analyze")`、`g.add_edge("merge", END)`。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| state_schema（构造入参） | type（TypedDict 等） | 必填 | 状态的"全局变量表"：所有节点共享的 dict 形状；节点只读自己需要的键、写自己产出的键 |
| add_node 的 node / action | str + 函数 | 必填 | 注册一个节点：给节点起名 + 接节点函数（函数收 state、返回部分状态更新 dict） |
| add_edge 的 start_key / end_key | str | 必填 | 声明一条边：前一个节点 → 后一个节点；从 `START` 出发、到 `END` 收口 |
| add_conditional_edges 的 source / path / path_map | str + 函数 + dict | path_map 可空 | 条件边：`path` 函数按 state 返回分支键，`path_map` 把分支键映射成节点名（或 `END`） |

**4. 最小示例**：

```python
print("【8.1 直线图：LCEL 管道的超集表达】")
# demo 顶部：from operator import add as list_add（Annotated 的第二个参数 = 合并函数）
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
```

输出（实跑原文）：

```
【8.1 直线图：LCEL 管道的超集表达】
  输入 hello → 输出：{'text': 'HELLO!', 'log': ['A', 'B']}
  Annotated[list, add]：log 是追加不是覆盖 → ['A', 'B']

【8.2 条件边：循环直到满足条件（手写 while 的声明式版）】
  n=0 跑完 → n=3，path=['inc', 'inc', 'inc']（inc 跑了 3 次直到 n≥3）
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:23,64,70,71,72,73,74,106,110,113,114,115,147`（真调版：23 = 导入；64~74 = Graph A 四步链直线图；106/110/113/114/115 = Graph B agent 循环图；147 = 真调输出）
- `scripts/demo_api_reference.py:259,262,263,264,281,282,283,284`（demo 节 8：259/281 = 两个 StateGraph 构造；262~264 = 直线图三条边；283/284 = 循环图的入口边与条件边）

**6. 原理要点**：

- **图 = State + Node + Edge 三件套**：State 是贯穿全图的"全局变量表"（TypedDict 声明形状），Node 是节点函数（收 state、返回部分更新，如 `{"text": ...}`），Edge 是节点之间的路（`add_edge` 直线 / `add_conditional_edges` 条件）。8.1 里 A、B 两个节点各干各的，拼起来就是一条"直线管道"
- **图是管道的超集**：LCEL 的 `|` 只能表达直线——前一个零件固定接后一个；图把"下一步去哪"从"组装时写死"变成"运行时可决定"：能循环（8.2 的 inc 跑了 3 次）、能分支（条件边按 state 选路）、能暂停等人工（生产里挂断点等人确认）——管道能表达的图都能表达，反过来不行
- **`Annotated[list, add]` = 追加不覆盖**：状态合并默认是"覆盖"（节点返回的键替换旧值）；`Annotated[list, add]` 表示这个键的合并规则是"用 `add`（`operator.add`，list 加法 = 拼接）合并"——8.1 输出 `log: ['A', 'B']`：A、B 各返回 `["A"]`/`["B"]`，拼起来而不是后者覆盖前者
- **编译后就是 Runnable**：`g.compile()` 返回的 `app` 和链一样 `.invoke`/`.stream`（4.1 词条里 extra_langgraph_intro.py:130,145 就是图真调）；真调版见 extra_langgraph_intro.py——Graph A 把 3.2 四步链声明成直线图（每步一个节点、边显式声明），Graph B 把 4.2 手写 while 工具循环声明成 agent 图（条件边 model → tools → model 循环）

**7. 踩坑**：条件边函数返回的必须是**节点名或 END**（8.2 的 `check` 返回 `"inc"` 或 `END`），且 path_map 里要有对应的映射——`g2.add_conditional_edges("inc", check, {"inc": "inc", END: END})` 的写法照抄 demo：左边是 check 可能返回的分支键（`"inc"` / `END`），右边是映射到的目标（节点名 / `END`）；分支键漏映射，运行时找不到下一步去哪就报错。深挖见 [extra_langchain_langgraph.md](extra_langchain_langgraph.md)。

### START

**1. 一句话**：图的入口哨兵：一个内置常量，代表"图的起点"——`add_edge(START, "首节点")` 声明第一条边从入口出发，图编译后从这里开跑。

**2. 签名**：

```python
from langgraph.graph import END, START, StateGraph
```

`START` 是图内置哨兵常量，没有函数签名——直接当值用：`g.add_edge(START, "analyze")`、`g.add_edge(START, "inc")`（笔记原文：`START`/`END` 是图内置哨兵常量）。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 常量不是函数，没有参数：`add_edge(START, "首节点")` 里它就是 start_key |

**4. 最小示例**（demo 节 8 摘录）：

```python
g.add_edge(START, "A")     # 8.1 直线图：入口 → 首节点 A
g2.add_edge(START, "inc")  # 8.2 循环图：入口 → 首节点 inc
```

输出（实跑原文）：

```
【8.1 直线图：LCEL 管道的超集表达】
  输入 hello → 输出：{'text': 'HELLO!', 'log': ['A', 'B']}
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:23,70,113`（23 = 导入哨兵；70 = Graph A 入口边；113 = Graph B 入口边）
- `scripts/demo_api_reference.py:29,262,283`

**6. 原理要点**：为什么需要"入口哨兵"而不是直接用首节点名：图里任何节点都可能被条件边指到，入口必须是一个"不是节点"的特殊位置——它只负责"从哪开跑"，编译时以它为起点的边决定第一站。START 不产出数据、不占状态：它是位置标记，不是一站。

**7. 踩坑**：入口边只连一次，`add_edge(START, 节点名)` 的第二个参数是首节点名——想换起点就换这条边的 end_key；每个图有且只有一个 START。`START`/`END` 是保留哨兵名，别拿它们当自定义节点名注册。

### END

**1. 一句话**：图的出口哨兵：内置常量，代表"流程到此结束"——`add_edge("末节点", END)` 收口；条件边里 `return END` 就是"这条路走到头"。

**2. 签名**：

```python
from langgraph.graph import END, START, StateGraph
```

`END` 是图内置哨兵常量，没有函数签名——直接当值用：`g.add_edge("merge", END)`。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 常量不是函数：`add_edge(..., END)` 里它是 end_key；条件边里它是 path_map 的目标 |

**4. 最小示例**（demo 节 8 摘录）：

```python
g.add_edge("B", END)                       # 8.1 直线图收口：B 跑完 → 结束
def check(state: LoopState):
    return "inc" if state["n"] < 3 else END  # 8.2 条件边：n≥3 就返回 END（结束）
```

输出（实跑原文）：

```
【8.2 条件边：循环直到满足条件（手写 while 的声明式版）】
  n=0 跑完 → n=3，path=['inc', 'inc', 'inc']（inc 跑了 3 次直到 n≥3）
```

**5. 本项目在哪用到**：

- `scripts/extra_langgraph_intro.py:23,74,106,114`（74 = Graph A 收口；106 = should_continue 返回 END；114 = 条件边 path_map 的 END 键）
- `scripts/demo_api_reference.py:29,264,279,284`

**6. 原理要点**：END 是"终点站"：边指到它，图就停，invoke 返回最终状态。条件边里 END 有双重身份：`return END` 里的 END 是分支键，`{"inc": "inc", END: END}` 里的左 END 是"check 可能返回的分支键"、右 END 是"该分支映射到的目标（出口）"。没有 END，"不满足就继续"的循环就没有尽头——8.2 里 `state["n"] < 3` 是终止条件：n 到 3 时 check 返回 END，循环才停（输出 n=3、path 里三个 inc）。

**7. 踩坑**：条件边函数在"结束"分支必须返回 END（或映射到 END）——8.2 的 `{"inc": "inc", END: END}` 把"继续"和"结束"两个分支都写全了，照抄这个写法；终止条件写错（`n < 3` 写反）才是真死循环。END 和 START 一样是内置哨兵，不用 add_node 注册。

---

# 第 9 章 向量

chromadb 三件套：EmbeddingFunction（文本 → 向量）+ 本地 BGE 模型 + rag_db 向量库。9.1~9.2 用项目真实库做中文语义检索（本地 ONNX 推理，零成本）。

### EmbeddingFunction

**1. 一句话**：chroma 的"文本 → 向量"接口（协议类）：实现 `__call__(input: Documents) -> Embeddings` 就接入了 chroma——入库（upsert）和检索（query）时 chroma 自动调用它，把文本变成能算距离的向量。

**2. 签名**：

```python
from chromadb import EmbeddingFunction, Documents, Embeddings
```

`inspect.signature` 原文（命令 8 输出；`-D` 是 chromadb 1.5.9 对 `Documents` 别名（`List[str]`）的渲染显示，照录原文）：

```text
EmbeddingFunction.__call__: (self, input: -D) -> List[numpy.ndarray[tuple[int, ...], numpy.dtype[Union[numpy.int32, numpy.float32]]]]
EmbeddingFunction: <class 'chromadb.api.types.EmbeddingFunction'>
Embeddings: typing.List[numpy.ndarray[tuple[int, ...], numpy.dtype[typing.Union[numpy.int32, numpy.float32]]]]
Documents: typing.List[str]
```

关键参数：`EmbeddingFunction` 是协议类，实现 `__call__(input: Documents) -> Embeddings` 即接入 chroma；`Embeddings = List[numpy.ndarray]`、`Documents = List[str]`；`PersistentClient(path=...)`；`get_or_create_collection(name, embedding_function=...)` 返回 `Collection`；`Collection.query(query_texts=[...], n_results=k)`；`Collection.upsert(ids=..., documents=..., embeddings=...)`。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| input（`__call__` 唯一入参） | Documents（=`List[str]`） | 必填 | 要转向量的文档文本列表；返回的 Embeddings 与它一一对应、等长 |

**4. 最小示例**（demo 节 9；`BASE_DIR` = 项目根目录，demo 顶部常量）：

```python
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
```

输出（实跑原文）：

```
【9.1 EmbeddingFunction 接口：Documents 进，Embeddings 出】
  实现示例：scripts/phase4_1_rag.py 的 LocalBertEmbedding（WordPiece 分词 → ONNX 推理 → CLS 池化 → 归一化）
  接口签名：def __call__(self, input: Documents) -> Embeddings

【9.2 query：真实 BGE 中文语义检索】
  命中 水表计量协议模板（水表计量协议模板）距离 0.408（越小越相似）
  命中 环境监测协议模板（环境监测协议模板）距离 0.561（越小越相似）
  → '水表'语义命中水表模板（关键词搜索做不到）
```

**5. 本项目在哪用到**：

- `scripts/phase4_1_rag.py:18,38,104,105,116,142,144,163,175`（104 = LocalBertEmbedding 实现类；105 = 接口说明；116 = `__call__` 实现；142/144 = PersistentClient + get_or_create_collection；163/175 = upsert / query）
- `scripts/demo_api_reference.py:294,299,300,301,304`

**6. 原理要点**：

- **实现 `__call__(input: Documents) -> Embeddings` 即接入 chroma**：chroma 只认这个接口——入库时拿它把文档文本算成向量存库（9.1 的 `get_collection(..., embedding_function=ef)`），检索时拿它把查询文本算成向量再比距离（9.2 的 `col.query(query_texts=[...])`）；接口收文本列表、还向量列表，一一对应。`-D` 是 chromadb 1.5.9 打印签名时对 `Documents` 的渲染，实际就是 `List[str]`
- **内部三步，没有魔法**（phase4_1 精读见 [code_walkthrough_phase4.md](code_walkthrough_phase4.md)）：① WordPiece 分词——中文逐字成 token，英文子词最长匹配；② ONNX 推理——token ids 过神经网络，每个 token 一个向量；③ 池化 + 归一化——BGE 取 `[CLS]` 向量（`pooling="cls"`），归一化后余弦相似度 = 点积，所以 9.2 输出"距离越小越相似"
- **9.2 是语义检索，不是关键词检索**：查询"智能水表 阀门 开关控制"没有出现"计量""协议"字样，却命中"水表计量协议模板"（距离 0.408）——向量空间里语义相近的词离得近，关键词搜索做不到（"设备位置上报"和"GPS 经纬度"没有共同关键词但语义相关）

**7. 踩坑**（chroma 环境坑三连，坑 #10/#11）：

- **S3 下载超时（URL 写死）→ 本地模型**：chromadb 内置 ONNX embedding 模型从 S3 下载，国内网络不通 + 下载路径在库内写死 → 从 hf-mirror 下载 `Xenova/bge-small-zh-v1.5` 的 `onnx/model.onnx` + `vocab.txt` 到 `models/bge-small-zh/`，自定义 EmbeddingFunction 本地推理，完全离线
- **MiniLM 中文失效 → 换 BGE**：all-MiniLM-L6-v2 是英文模型，中文检索排序错乱（查"水表阀门"命中"环境监测"）→ 换 BGE-small-zh-v1.5（CLS 池化）+ 显式 `hnsw:space=cosine`，检索立刻正确
- **换 embedding 模型必须删 rag_db 重建**：向量库里已存的向量是旧模型算的，新旧向量不在同一语义空间、算出的距离没意义——换模型后必须删掉 `rag_db/`（或重建集合）再 `phase4_1_rag.py build` 重灌，否则"检索正确"是假象（hnsw 空间参数也只在首次创建生效）
- 深挖见 [phase4_rag.md](phase4_rag.md)（环境坑三连全记录 + 实测对比）

### Embeddings

**1. 一句话**：向量列表的类型别名：`Embeddings = List[numpy.ndarray]`（直观理解 `list[list[float]]`）——只是类型注释，不是运行时存在的对象。

**2. 签名**：

```python
from chromadb import Embeddings
```

照录原文（命令 8 输出）：

```text
Embeddings: typing.List[numpy.ndarray[tuple[int, ...], numpy.dtype[typing.Union[numpy.int32, numpy.float32]]]]
```

关键参数：`Embeddings = List[numpy.ndarray]`（向量列表）——`__call__` 的返回值类型就是它：每个文本一个向量，几个文本进、几个向量出。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 类型别名不是类：没有构造参数、没有方法，只用于签名里的类型注释 |

**4. 最小示例**：见 EmbeddingFunction 词条的 9.1/9.2——9.2 输出的"距离"就是 Embeddings 的产物：`命中 水表计量协议模板（水表计量协议模板）距离 0.408（越小越相似）`（实跑原文）——文本进、向量出、按距离排序，全程没出现"Embeddings 对象"：别名只是注释。

**5. 本项目在哪用到**：

- `scripts/phase4_1_rag.py:18,38,104,105,116,142,144,163,175`（38 = 导入别名；116 = `__call__` 返回 `-> Embeddings`；175 = query 的 distances 就是向量算出来的）

**6. 原理要点**：**类型别名 = 给类型起小名，不是新对象**——`Embeddings` 就是 `list[numpy.ndarray]`（一行一个向量），运行时不存在"Embeddings 类"，`isinstance(x, Embeddings)` 都无处可调。别名的价值是让接口签名可读：`-> Embeddings` 比 `-> list[list[float]]` 更懂业务——chroma 的接口签名（EmbeddingFunction / query / upsert）里到处是它，认得出它 = 读得懂签名。

**7. 踩坑**：别在运行时拿类型别名做事（构造、判断类型都别指望它）——它只是注释，真正干活的是值本身（numpy 数组列表）。9.2 的 `hits` 是 dict（QueryResult：ids / metadatas / distances），不是"Embeddings 对象"；原始向量在返回结果的 `embeddings` 键里，要拿就从那取。

### Documents

**1. 一句话**：文档文本列表的类型别名：`Documents = List[str]`——只是类型注释，不是运行时存在的对象。

**2. 签名**：

```python
from chromadb import Documents
```

照录原文（命令 8 输出）：

```text
Documents: typing.List[str]
```

关键参数：`Documents = List[str]`（文本列表）——`__call__` 的唯一入参类型就是它：要转向量的文本，一条条排在列表里。

**3. 参数表**：

| 参数 | 类型 | 默认值 | 干什么用 |
|------|------|--------|---------|
| （无） | — | — | 类型别名不是类：没有构造参数、没有方法，只用于签名里的类型注释 |

**4. 最小示例**：见 EmbeddingFunction 词条的 9.1/9.2——`col.query(query_texts=["智能水表 阀门 开关控制"], n_results=2)` 里 `query_texts` 收的就是 Documents：`["智能水表 阀门 开关控制"]` 是一个文本的列表，进 `__call__` 返回一个向量（实跑原文见 9.2 输出）。

**5. 本项目在哪用到**：

- `scripts/phase4_1_rag.py:18,38,104,105,116,142,144,163,175`（38 = 导入别名；116 = `__call__` 的 `input: Documents` 参数标注）

**6. 原理要点**：**类型别名 = 给类型起小名，不是新对象**——`Documents` 就是 `list[str]`，运行时不存在"Documents 类"。别名的价值是让接口签名可读：`input: Documents` 比 `input: list[str]` 更懂业务——收的是"文档文本"不是任意字符串列表（EmbeddingFunction 词条签名里的 `-D` 就是 chromadb 1.5.9 对它的渲染显示）。

**7. 踩坑**：别在运行时拿类型别名做事——它只是注释，真正传进来的就是普通 `list[str]`；写自定义 EmbeddingFunction 时签名照抄 `def __call__(self, input: Documents) -> Embeddings`，接口收列表、还列表，别造新类型。
