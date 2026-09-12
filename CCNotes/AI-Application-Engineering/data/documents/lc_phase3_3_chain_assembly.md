# Phase 3.3：程序组装 —— 怎么组装、为什么这么写、原理

> 对应脚本：`scripts/phase3_3_batch_stream.py`（复用 3.2 的零件，重新组装）
> 这一讲回答三个问题：**怎么组装程序 / 代码为什么长这样 / 底层原理是什么**。

---

## 原理 1：一切皆 Runnable（为什么能任意组合）

LangChain 的所有组件——Prompt、模型、Parser、甚至你的普通 Python 函数——都实现同一个接口：

```
Runnable:  输入 ──► 输出
```

统一的"输入→输出"契约带来一个后果：**任何组件可以和任何组件组合**，`|` 左边是什么类型不重要，只要有 `.invoke()`：

```python
ANALYZE_PROMPT | llm | StrOutputParser()   # 三种完全不同的东西，串成一条链
```

没有统一接口，每两种组件之间都要写适配器，组合数爆炸。这是 LangChain 相对"手写管道"的根本优势。

## 原理 2：代码结构 = 数据流结构

写程序之前先画数据流图，**图上每种拓扑都有对应写法**：

| 数据流拓扑 | 写法 | 用途 |
|-----------|------|------|
| 顺序流 A→B→C | `a \| b \| c`（本质是 RunnableSequence） | 固定步骤依次执行 |
| 并行分支 | `RunnableParallel(a=..., b=...)` | 互不依赖的计算同时跑 |
| 顺序 + 保留中间结果 | `.assign(key=子链)`（本质是 RunnableAssign） | 下游要用上游产出 |
| 插入任意逻辑 | `RunnableLambda(普通函数)` | 校验、计算、合并 |

3.2 的四步链就是四种拓扑的组合——**代码长什么样，取决于数据流长什么样，不是风格问题**。实测 `clean_chain.steps` 打印出来的结构：

```
0: RunnableAssign     ← assign(key_points=...)
1: RunnableAssign     ← assign(fields=...)
2: RunnableAssign     ← assign(checks=...)
3: RunnableLambda     ← merge_final（Python 合并）
```

## 原理 3：没有魔法，invoke 就是普通 dict 流转

拆开 `full_chain.invoke({"requirement": doc})` 的每一步：

```
{"requirement": 文档}
  → ① ChatPromptTemplate 从 dict 里取 "requirement" 填模板 → messages
  → ② llm 收 messages 出 AIMessage
  → ③ Parser 把 AIMessage 转 str / dict
  → ④ assign 把结果作为新键挂回 dict：{"requirement":..., "key_points":...}
  → ...重复，直到 merge_final 输出最终 dict
```

关键认知：**键的匹配不是链干的，是 PromptTemplate 干的**（按占位符名从输入 dict 取键）；链只负责把 dict 往下传。所以"挂键名 = 占位符名 = 下游取用名"必须三处一致——不一致会在需要时当场报错（3.2 实撞过一次）。

## 组装方法论（可操作 5 步）

1. **画数据流图**：输入是什么、最终产出什么、中间经过哪些变换
2. **每个变换写成一个 Runnable**：LLM 步骤用 `prompt | llm | parser`，纯计算用 `RunnableLambda`
3. **按拓扑组装**：顺序 `|`、挂键 `assign`、并行 `RunnableParallel`
4. **调试期挂 tap** 打印中间产物 → 稳定后换成干净版（3.2 vs 3.3 就是同一批零件、两种装法）
5. **换调用方式不改链**：`invoke` / `batch` / `stream` 三种方式套在同一条链上

## 三种调用方式

| 方式 | 输入 → 输出 | 特点 | 场景 |
|------|-----------|------|------|
| `invoke(x)` | 单个 → 单个 | 同步返回完整结果 | 交互式单次处理 |
| `batch([x1, x2, ...])` | 多个 → 多个 | 内部自动并发 | **批量处理同事文档**（3.3 实测 2 份文档跑通） |
| `stream(x)` | 单个 → 逐块 | 打字机效果 | UI 展示、实时反馈 |

**坑**：`RunnableLambda` 是流式边界——中间插了它，token 级流式就断了（会缓冲完整输入才继续）。所以 3.3 的流式演示用的是 `analyze_chain`（纯 prompt|llm|parser），而不是带 Lambda 的 `full_chain`。要流式到 UI，流式路径上别放 Lambda。

## 旧版 SequentialChain（一眼带过，别学）

旧 API：`LLMChain` + `SequentialChain`，靠**字符串键**显式声明每一步的输入输出变量名，只能串 LLMChain，串不了 Parser 和普通函数。官方已废弃（deprecated），新代码一律 LCEL。Runnable 统一接口出现后，这套字符串键簿记完全是多余的。

---

*对应的实操输出：`outputs/batch_sample_requirement_protocol.json`、`outputs/batch_sample_requirement2_protocol.json`。*
