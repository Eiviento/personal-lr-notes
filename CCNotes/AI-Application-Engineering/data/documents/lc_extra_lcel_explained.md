# LCEL 详解：LangChain 的管道写法

> 零基础可读。这是本项目所有代码的"写法本身"，值得单独讲透。
> 深挖组装方法再看 `phase3_3_chain_assembly.md`（三原理 + 5 步法）。

---

## 一、LCEL 是什么：不是一门语言，是一个组装约定

**L**ang**C**hain **E**xpression **L**anguage——名字唬人，但它**不是编程语言**：没有编译器、没有新语法、不需要安装任何额外东西。它就是 Python 里的一个约定：

> **`a | b` 的意思是："把 a 的输出，作为 b 的输入。"**

就这么简单。Python 里 `|` 本来是集合的"或"运算，LangChain 重定义了它（叫"运算符重载"），让数据从左往右流。

**为什么这么干成立**：LangChain 所有积木都是同一个接口——**任何积木都有 `.invoke(输入) → 输出`**（这个统一接口叫 Runnable）。既然全部是"输入→输出"的小黑盒，首尾相接就是最自然的事，不需要任何适配器。

## 二、最小演示：管道 = 嵌套调用，没有魔法

```python
from langchain_core.runnables import RunnableLambda

add_one = RunnableLambda(lambda x: x + 1)   # 小黑盒1：加一
double  = RunnableLambda(lambda x: x * 2)   # 小黑盒2：翻倍

chain = add_one | double                    # LCEL：首尾相接
chain.invoke(3)          # → 8，即 (3+1)*2

# 管道符展开后就是普通嵌套调用：
double.invoke(add_one.invoke(3))   # → 8，一模一样
```

## 三、真实数据流全程追踪（本项目四步链的第①步）

用真实代码看一次数据长什么样（填模板不调 API，可以自己跑）：

```python
ANALYZE_PROMPT.invoke({"requirement": "设备每 10 分钟上报心跳"})
```

| 步骤 | 输入 | 输出 |
|------|------|------|
| `ANALYZE_PROMPT` | `{"requirement": "设备每 10 分钟上报心跳"}`（dict） | `ChatPromptValue`——填好模板的完整消息（SystemMessage 说明书 + HumanMessage 需求文本） |
| `llm` | 上面这串消息 | `AIMessage`——模型生成的文字 |
| `StrOutputParser` | AIMessage | `str`——纯字符串（关键需求点列表） |

整条链 `ANALYZE_PROMPT | llm | StrOutputParser()` 就是把这三步串起来：**dict 进 → 消息 → 模型文字 → 字符串出**。四种不同类型的东西能首尾相接，全靠 Runnable 统一接口。

## 四、LCEL 能表达的三种组合（代码结构 = 数据流结构）

| 组合 | 写法 | 数据流形状 |
|------|------|-----------|
| 串联 | `a \| b \| c` | 直线：A→B→C |
| 并行分支 | `RunnableParallel(a=..., b=...)` | 分叉再合并：同时跑两个分支 |
| 插自定义逻辑 | `RunnableLambda(普通函数)` | 任意位置插一段 Python |

本项目 3.2 的四步链就是这三样的组合：`assign(分析链) | assign(字段链) | assign(规则链) | Lambda(合并)`。

## 五、为什么 LCEL 值得用（四个好处）

1. **代码即流程图**：一行管道就是一张数据流图，读代码等于读流程——不用在函数调用间跳来跳去找逻辑
2. **换模型只改参数**：`ChatOpenAI` 一个积木统一了所有模型接口，DeepSeek/OpenAI/国产模型切换不改管道
3. **三种调用方式通用**：同一条链，`invoke`（单个）/`batch`（批量，自动并发）/`stream`（流式打字机）——不用为每种用法重写代码
4. **易测试**：管道里每个小黑盒都能单独 `.invoke` 验证（就像第三部分拆开看每一步）

## 六、边界：LCEL 的直线天花板

LCEL 是直线传送带，做不到**循环、条件分支、暂停等人工**。需要这些时用 LangGraph（图是管道的超集）——详见 `extra_langchain_langgraph.md`。

---

*这一课是用户提问的额外内容。对应实操：`scripts/phase2_1~2_3`、`phase3_2`、`phase3_3` 全部是 LCEL 写法。*
