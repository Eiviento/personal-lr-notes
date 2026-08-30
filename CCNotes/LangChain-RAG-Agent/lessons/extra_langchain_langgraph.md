# LangChain 与 LangGraph 详解

> 对应脚本：`scripts/extra_langgraph_intro.py`
> 这一课回答：它们分别是什么、什么关系、什么时候用哪个。零基础可读。

---

## 一、回到起点：没有框架时怎么写 LLM 应用

假设不装任何库，直接调 DeepSeek（本项目 Phase 1.4 的 `scripts/phase1_4_req_to_protocol.py` 就是证据）：

```python
response = client.chat.completions.create(model="deepseek-chat", messages=[...])  # 手拼消息
raw = response.choices[0].message.content.strip()          # 拿字符串
result = _parse_response(raw)                              # 手写四道保险 JSON 容错
```

痛点：手拼消息串、手写解析容错、手写重试、换模型要改一大片代码、逻辑全揉在一个函数里没法复用。**LangChain 就是来解决这些痛点的积木箱。**

## 二、LangChain 是什么：大模型应用的积木箱

定义：**LangChain 是一个 Python 库，把"调用大模型"这件事包装成标准积木，并提供胶水把它们组装起来。**

核心积木及本项目实际用法：

| 积木 | 作用 | 本项目哪里用了 |
|------|------|--------------|
| `ChatPromptTemplate` | 提示词模板，`{占位符}` 填充 | 每一步的"任务说明书"（四要素） |
| `ChatOpenAI` 等模型类 | 模型统一接口——换 DeepSeek/OpenAI 只改参数 | 全部脚本 |
| `OutputParser` | AI 输出 → 程序可用类型（str/dict） | Str/JsonOutputParser |
| `Runnable` + `\|`（LCEL） | 把积木串成管道 | 3.2 四步链 |
| `bind_tools` | 把函数签名告诉模型（4.2 工具调用） | 字段校验工具 |
| 向量库/检索器封装 | RAG 检索 | 4.1 的 Chroma |

**它不是的东西**：不是模型本身（模型在 DeepSeek 服务器上）、不是应用服务器（不提供网页）、不是 AI 运行时。它只是**你 Python 代码里的胶水**。

**版本注意**：现在是 LangChain 1.x。网上大量旧教程里的 `LLMChain`/`SequentialChain` 已废弃——遇到旧教程直接跳过那部分（3.3 讲过）。

## 三、LCEL 的天花板：直线管道做不到的三件事

`prompt | llm | parser` 是直线传送带。现实流程经常超出直线：

| 做不到的事 | 现实场景 | 本项目当时的妥协 |
|-----------|---------|----------------|
| **循环**（回到上一步） | AI 生成 → 调用工具 → 看结果 → 再生成 → 再调用…… | 4.2 只能手写 `while` 循环 |
| **条件分支**（按结果决定下一步） | 校验发现问题 → 打回重新生成；没问题 → 结束 | 无，只能全跑 |
| **暂停等人工/断点恢复** | 4.3 人工审核：生成到一半停下来等人确认 | 只能把流程切成两个脚本 |

## 四、LangGraph 是什么：用"图"描述程序流程

定义：**LangChain 官方出的编排框架。程序流程 = 图：节点（Node）干活的积木，边（Edge）数据的流向，State（状态）贯穿全局的数据。** 它是 LangChain 生态的一部分，节点通常就是 LangChain 的 Runnable。

三个核心概念（对应脚本 `extra_langgraph_intro.py`）：

```python
class State(TypedDict):          # ① State：贯穿全图的数据（节点读它、写它）
    requirement: str
    key_points: str
    ...

def node_analyze(state):         # ② Node：一个函数，返回部分状态更新
    return {"key_points": ...}

g = StateGraph(State)            # ③ Edge：声明谁流向谁
g.add_edge("analyze", "fields")  #    直线：等价 LCEL 的 |
g.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
```

四种关键能力：

1. **条件边**（conditional edges）：按当前状态决定下一步去哪
2. **循环**：`tools → model` 回边就是 agent 循环——实测 Graph B 里模型自动循环 9 次校验
3. **checkpointer（检查点）**：每一步状态落盘——程序挂了从断点续跑；还能"时间旅行"回放任意一步
4. **interrupt（中断）**：停在某节点等人确认——**4.3 人工审核的生产级实现**（我们的脚本只能"跑完再问"，LangGraph 可以"跑到一半停住"）

**图是管道的超集**：直线管道能表达成图（Graph A 实测：四步链 = 4 节点 + 5 条直线边），但循环/分支/暂停只有图能表达。

类比：LCEL 是工厂的**直线传送带**；LangGraph 是**整个车间**——有岔路、有回流、能停工等审批。

## 五、二者的关系（一句话版）

**LangChain 提供积木，LangGraph 提供编排。** LangGraph 的节点里用的就是 LangChain 的组件。不是二选一，是分工：LangGraph 内部一直用 LangChain。

## 六、什么时候用哪个（决策表）

| 流程形态 | 用什么 | 本项目对应 |
|---------|--------|-----------|
| 固定直线流程 | LCEL 就够 | 3.2 四步链 |
| 模型↔工具循环（agent） | LangGraph | 4.2 的手写 while → Graph B |
| 中途人工确认 | LangGraph interrupt | 4.3 的升级方向 |
| 多分支/多 agent 协作 | LangGraph | 将来 |
| 简单校验/合并等纯 Python | 都不用，直接写代码 | ④ 合并步骤 |

**原则：能直线就直线（简单），有环有岔才上图（不提前过度设计）。**

## 七、进阶学习路线（按需取用）

1. LangGraph 官方教程（`langchain-ai.github.io/langgraph/`，有中文）
2. checkpoint 持久化到 SQLite + interrupt 人工确认——把 4.3 重写成"真·跑到一半等人"
3. subgraph（子图）：大流程里嵌小图
4. LangSmith：LangChain 官方的调试/观测平台（可视化每次调用的中间状态，排错神器）
5. LangServe：把链/图一键部署成 HTTP API

---

*这一课是用户提问的额外内容，不在原 5 阶段计划里。实操脚本 `scripts/extra_langgraph_intro.py` 用两个图复现了 3.2 与 4.2 的功能。*
