# Phase 4.2：Function Calling / Tool Use —— 让模型调用你的函数

> 对应脚本：`scripts/phase4_2_tool_calling.py`
> 1.3 埋的伏笔在此兑现：结构化输出三法中最可靠的 Tool Calling。

---

## 原理一句话：模型不执行代码，它只"点菜"

模型输出的是**结构化的调用请求**（函数名 + 参数 JSON），真正执行的是你的 Python 代码，执行结果再回传给模型继续推理：

```
你的消息 + 函数签名(JSON Schema) ──► 模型
                                     │ 输出 tool_calls:
         {"name": "validate_field_type",
          "args": {"field_name": "msg_type", "field_type": "uint8", "length": 2}}
                                     ▼
                          代码执行（你的函数，~20 行循环）
                                     │ ToolMessage 回传
            "msg_type: uint8 应为 1 字节，实际声明 2 → 不合法"
                                     ▼
                        模型继续 → 汇总报告（或再调用工具）
```

**安全边界**：模型只能"请求"调用，执行权永远在代码手里——这是 Function Calling 与"让 AI 跑代码"的本质区别。

## 什么时候用工具

| 任务性质 | 交给谁 | 例子 |
|---------|--------|------|
| 需要精确性（死规则、查表、计算） | **代码**（工具） | uint8 占几字节、CRC 计算、查数据库 |
| 需要判断（要不要校验、结果怎么解读、怎么写报告） | **模型** | 评审策略、汇总、修正建议 |

实测分工：模型决定"逐字段校验"，代码精确执行 7 次校验（含揪出人为注入的错误），模型最后把 7 条结果汇总成带修正建议的报告。**两边都干了各自最擅长的事。**

## 代码三要素

```python
# 1. 定义工具：类型注解 → JSON Schema（模型的"参数说明书"），docstring → 使用时机
@tool
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    """校验协议字段的类型与字节数是否匹配。参数：..."""

# 2. 绑定：把函数签名发给模型
llm_with_tools = llm.bind_tools([validate_field_type])

# 3. 工具循环（手写版，生产环境用 LangGraph 替代）：
#    while response.tool_calls: 执行 → ToolMessage 回传 → 再 invoke
```

**为什么说 Tool Calling 是"最可靠的结构化输出"**（1.3 的结论）：工具参数由 JSON Schema 硬约束，模型生成的 args 必然是合法 dict——Prompt 约束靠自觉，Tool Calling 靠契约。

## 与 3.2 评审步骤的关系

| | 3.2 ③ 约束规则（纯 LLM 评审） | 4.2 工具校验（LLM + 代码） |
|---|---|---|
| 检查方式 | 模型"凭知识"说 | 代码"按规则"算 |
| 可靠性 | 可能漏、可能背错 | 死规则永不出错 |
| 洞察力 | 能发现"预留位不够"这类开放问题 | 只能回答工具覆盖的问题 |

**两者互补，不是替代**：4.3 的人工审核环节把两者都用上（LLM 评审 + 工具校验 + 人确认）。

## 注意

- 手写 `while` 循环是为了看清原理；生产环境用 **LangGraph** 管理这个"模型↔工具"循环（LangChain 的 Agent 运行时）
- 循环要设次数上限，防止模型反复调用工具死循环
- langchain_core 版本差异：`tool.invoke(args)` 在部分版本返回 `str` 而非 `ToolOutput`，用 `str(...)` 包一层最稳

---

*对应 progress.md 的 Phase 4 记录。*
