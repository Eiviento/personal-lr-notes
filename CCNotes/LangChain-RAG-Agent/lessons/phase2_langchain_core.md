# Phase 2：LangChain 核心概念

> 对应脚本：`scripts/phase2_1_langchain_basics.py`、`phase2_2_lcel_pipeline.py`、`phase2_3_output_parsers.py`
> 一句话总纲：**LangChain 的核心思想是把所有环节统一成 Runnable，用 `|` 串成管道。**

---

## 2.1 三大核心：PromptTemplate / Model / Parser

| 原生 SDK（Phase 1.4） | LangChain | 变化 |
|----------------------|-----------|------|
| 手拼字符串 messages | `ChatPromptTemplate` | 模板与代码分离，`{占位符}` 填充；模板里要输出花括号字面量用 `{{ }}` 转义 |
| `OpenAI(base_url=...)` | `ChatOpenAI(base_url=...)` | 统一 `.invoke()` 接口，换模型只改参数 |
| 手写 `_parse_response()` 容错 | `JsonOutputParser()` | 自动剥 markdown 围栏 + 容错，链式调用 |

LCEL 管道：`prompt | llm | parser` —— 数据流：输入 → 填模板 → 发模型 → 解析 → dict。

**原理**：`|` 是把左侧结果作为输入传给右侧，最后组装成 `RunnableSequence`。所有 LangChain 组件都是 Runnable，所以可以任意组合——这是后面所有高级玩法的基础。

## 2.2 LCEL 进阶：在管道里插自定义逻辑

| 组件 | 作用 | 使用场景 |
|------|------|---------|
| `RunnableLambda(func)` | 把普通 Python 函数包装进管道 | 校验、计算、任何后处理 |
| `RunnableParallel(a=..., b=...)` | 多个分支并行执行后合并 | 多个独立校验同时跑（2.2 实操：字段/频率/字节数三路并行） |
| `RunnablePassthrough()` | 原样透传输入 | 保留中间产物给下游 |
| `.assign(key=子链)` | 在当前数据流上挂一个新键 | 逐步丰富数据流（3.2 的链式拼装） |

**数据流思想**：管道里流动的是一个 dict，每一步取出自己需要的键、产出一个新键挂上去。谁缺键谁报错——这是防漏配的免费保护。

## 2.3 Output Parser：模型输出 → 程序可用的类型

模型返回的是 `AIMessage` 对象，Parser 负责转换：

| 方案 | 输出类型 | 用途 |
|------|---------|------|
| 不用 Parser | `AIMessage` | 基本不直接用 |
| `StrOutputParser` | `str`（LangChain 1.x 实际返回 `TextAccessor`，是 str 子类，可直接用） | 生成概述、文档 |
| `JsonOutputParser` | `dict` | 程序拿字段做计算 |

选型原则：**下游要文本用 Str，下游要结构化数据用 Json。**

## 2.4 原生 vs LCEL 结论

| 维度 | 原生 SDK | LCEL |
|------|---------|------|
| Prompt 管理 | 字符串拼在代码里 | 模板独立、可复用 |
| 换模型 | 改 SDK 调用 | 改一个参数 |
| 解析容错 | 手写 30 行 | 一行 `JsonOutputParser()` |
| 加后处理 | 改函数调用链 | 管道里 `\|` 一个新 Runnable |

---

*对应 progress.md 的 Phase 2 记录。*
