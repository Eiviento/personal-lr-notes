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
