# Phase 2 · 阀门与护栏：怎么让 agent 循环不失控

> 2026-09-06。P1 学会了循环怎么转（agent↔tools），这一课学怎么防它转疯。三类对照实验全部实跑（`outputs/agent2_guardrails_run.log`，单次实跑未挑选），配套脚本 `scripts/agent2_guardrails.py`。

## 一、护栏矩阵：循环有四道阀门

| 护栏 | 防什么 | 在哪加 | 实验 |
|------|--------|--------|------|
| recursion_limit 步数上限 | 无限循环烧 token | invoke/stream 的 config | 实验 1 |
| 重复调用熔断 | 模型反复点同一工具（同参数） | tools 节点后的条件边 | 实验 2 |
| 工具异常回流 | 工具崩溃把整个 agent 炸掉 | ToolNode 的 handle_tool_errors | 实验 3 |
| 超时（时间维度） | 单步卡死 | 模型层 timeout 参数 | 本轮未单列（见文末） |

核心心智模型：**recursion_limit 是"大坝"（兜底总数），熔断是"堤内闸门"（提前识别病态模式）**。大坝设太大防不住恶意死循环、设太小误杀正当任务；闸门负责在病态发生早期掐断。

## 二、实验 1：recursion_limit——大坝设太小的代价

代码：`agent.stream(..., config={"recursion_limit": 2})`。真实输出：

```
[agent] 点菜: ['get_order_status', 'search_knowledge']   ← 模型一次并行点了两个工具
[tools] 返回: 退换货政策…                                  ← 工具正常执行
→ GraphRecursionError 被捕获：正常任务被 limit=2 误杀
```

- **recursion_limit 语义**：图的"步数"上限（每执行一个节点算一步），超了抛 `GraphRecursionError`。它是防无限循环的总闸。
- **实测教训**：一个正常任务（查订单 + 查政策，需要 2+ 次工具往返）在 limit=2 下就被掐断——**上限设太小会误杀正当任务**。模型一次还能并行点多个工具，一个"简单"任务实际步数比你直觉多。
- **工程取法**：默认值很大（LangChain-RAG-Agent 记录 1.2.9 实测默认 10007，防的是真死循环）；生产上按"正当任务最大步数 × 安全系数"设，如 20~50。

## 三、实验 2：重复调用熔断——堤内的闸门

用诱导提示（"必须连续调用 get_now_time 3 次取平均"）制造重复点菜，自定义条件边在 tools 后检测。真实输出：

```
[agent] 点菜: ['get_now_time']        ← 第 1 次
[tools] 返回: 2026-09-06 16:31:41
[agent] 点菜: ['get_now_time']        ← 第 2 次（同参数）
[breaker] 熔断触发: 【熔断提示】检测到你已连续多次调用同一工具且参数相同…
[agent] 点菜: ['get_now_time']        ← 模型想查第 3 次
[breaker] 熔断触发
[agent] 最终回答: 三次调用结果分别为…（收尾）
```

实现要点（对照脚本）：
- **`route_after_tools` 自定义条件边**：tools 执行完不是无条件回 agent，先问一句"最近 2 次点菜是否同一工具同一参数？"——是 → 走 `breaker` 节点；否 → 正常回 agent。
- **`breaker` 节点**：往消息历史注入一条 SystemMessage（"检测到重复调用，立即停止并直接回答"），再回 agent 让它收尾。熔断不是硬切断，是**给模型一个台阶下**——真正生产里可换成"强制结束 + 告警"。
- 检测函数 `_recent_same_tool_calls`：只比对最近 N 次 AI 消息的 `(tool name, args)` 是否相同。注意 args 相同才熔断——查订单 SO-1001→SO-1002 是合理连续查询，不能误杀。

**为什么需要它**：recursion_limit 只能等模型烧到上限才停；熔断在"同参数重复"这种病态模式出现第 2~3 次就介入，省 token、省时间、输出质量也高（模型被迫收尾）。

## 四、实验 3：工具异常回流——默认护栏不万能（实测发现的坑）

工具 `fragile_lookup` 故意抛 `ConnectionError`。开发中第一版用默认 `ToolNode([...])` **直接崩溃**（exit 1），读 langgraph 1.2.9 源码（`tool_node.py:_default_handle_tool_errors`）真相：

```python
def _default_handle_tool_errors(e):
    if isinstance(e, ToolInvocationError):   # 只兜"工具调用层"错误
        return e.message
    raise e                                   # 工具自己抛的业务异常：直接炸！
```

**默认护栏只兜 `ToolInvocationError`（如参数校验失败），工具内部抛的业务异常默认 raise 到顶层把 agent 炸掉。** 要兜全部异常必须显式：

```python
ToolNode(tools, handle_tool_errors=True)   # True → 全部异常转 "Error: ..." 消息
```

显式 True 后的真实输出（护栏生效）：

```
[tools] 返回: Error: ConnectionError('外部订单服务超时（order_id=SO-1005）——模拟服务崩溃')
[agent] 最终回答: 该外部订单服务当前不稳定，返回了连接超时错误…我无法获取详情。
```

**护栏的价值双层**：① 工具崩溃不炸掉整个 agent（健壮性）；② 错误以消息形式回流给模型，模型**如实转述并给用户下一步建议，不编造**（可靠性）——这与你 P1 学到的防幻觉纪律是同一根：错误也是事实，要忠实传递。

## 五、超时护栏（时间维度）说明

recursion_limit 管"步数"不管"时间"。单步可能卡死（模型 API 无响应）——时间维度的护栏在**模型调用层**：`ChatOpenAI(..., timeout=60)` 之类。LangGraph 层面没有"整个循环 N 秒超时"的内置开关，需要自己包（如把 invoke 包在 asyncio.wait_for / 外层超时装饰器）。本课不单列实验（属工程加固而非机制），P5 评估阶段若涉及再展开。

## 六、设计原则小结

1. **分层设防**：大坝（recursion_limit）兜总步数 + 闸门（熔断）提前识别病态 + 异常回流防崩溃——单靠一层不够。
2. **护栏别误杀正常**：limit 太紧误杀并行多工具（实验 1）；熔断只比对"同工具同参数"（实验 2 设计取舍）。
3. **显式优于默认**：`handle_tool_errors` 默认值的行为要读源码确认（实验 3 实测推翻"默认会兜"的想当然）。
4. **调优纪律预告**：改护栏参数是一次只改一个变量的实验（P5 会教你量化评估——现在先记住"改完要拿同一批问题回归"）。

## 七、复现与证据

复现：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent2_guardrails.py`（需 .env 配好 key）
证据：`outputs/agent2_guardrails_run.log`（三类实验完整轨迹）
源码依据：`E:\software\OfficeWorkLife\Anaconda\envs\agent_env\lib\site-packages\langgraph\prebuilt\tool_node.py` 的 `_default_handle_tool_errors` / `_handle_tool_error`（1.2.9 实测）
