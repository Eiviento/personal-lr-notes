# Phase 7 · 客服工作台：把 6 个机制拼成一个可交互系统

> 2026-09-08。回答"学完 6 个隔离的控制台实验后，怎么让 agent 真正服务人"。配套代码：业务后端 `scripts\agent7_webapp.py` + UI 薄壳 `app.py` + 冒烟 `scripts\agent7_app_test.py`。本 Phase 是**综合**——不引入全新机制，而是让 P1-P6 的机制第一次在同一个图上协同，并跨过"web 无状态 ↔ agent 长时运行"这道控制台脚本教不会的工程桥。

## 一、为什么要这一步（从"机制"到"系统"）

前 6 个 Phase 每个都是一个**隔离的控制台实验**：P1 拆白盒、P2 上下限护栏、P3 记忆、P4 审批、P5 评估、P6 V2+子图。机制全会了，但没有一个把它们协同起来服务用户。真实 agent 恰恰是**记忆 + 工具 + 审批 + 版本演进同时在线**。

Phase 7 的目标：一个能跑的 **SmartHome 客服工作台**——左侧新建会话、聊天框对话、申请退款时暂停等客服经理审批。产出可展示、可续进化。

## 二、核心论断：web 无状态 ≠ agent 无记忆，桥 = thread_id

这是全 Phase 最重要的一句话。

- **Streamlit 的模型是"无状态重跑"**：每次用户交互（发消息、点按钮）都从第一行重跑整个 `app.py`。它不记得上一秒发生了什么——`st.session_state` 只是本次浏览器会话的临时抽屉，刷新/换标签就没了。
- **agent 的模型是"长时运行"**：LangGraph 图可能跑一半停在 `interrupt` 等人审批，状态存在 checkpointer 里，随时可以从断点恢复。
- 两个模型对不上。**桥就是 `thread_id`**：UI 只持有并搬运一个 `thread_id`（会话钥匙），历史和"停在哪"全部由 checkpointer 持有。

```
UI（无状态，每次重跑）                  agent（有状态，长时运行）
  st.session_state["thread_id"] ──────► checkpointer[thread_id] = 全部消息 + 暂停点
  只记一把钥匙                            记忆/断点真相都在这里
```

**关键设计决策：状态真相源 = checkpointer，不是 `st.session_state`。** 对比姊妹项目 `LangChain-RAG-Agent\app.py`：那里每轮把整个 messages 列表全量重发给无状态 agent（消息历史存在前端 session_state）。Phase 7 反过来——历史存在后端的 checkpointer，前端刷新后调 `get_history` 从 checkpointer 拉回来渲染。这就是"重启/刷新不丢"的真相所在。

## 三、把 6 个机制拼起来的三处接线

### 接线 1：工具内 interrupt（P4 的升级）

Phase 4 的审批是**独立小图**（`RefundState`：collect → approval → finalize），interrupt 调在图的**节点函数**里。但真实客服 agent 是个 ReAct 图（`create_agent`），没有"审批节点"这个位置——审批必须发生在**工具执行时**。

Phase 7 把 interrupt 放进工具函数体内：

```python
@tool
def request_refund(order_id: str, reason: str) -> str:
    """申请订单退款（写操作，需人工审批）。"""
    order = _lookup(order_id)              # 1. 事实核对（只信数据）
    if order is None: return "订单不存在…"
    if not order["refund_eligible"]: return "不符合退款条件…"
    decision = interrupt({                  # 2. 写操作 → 停在这里等人批（★ 核心）
        "type": "refund_approval", "order_id": order_id, "price": order["price"], ...
    })
    if decision == "approved":              # 3. resume 后恢复执行
        _REFUNDED[order_id] = "approved"
        return f"退款已执行：{order_id} {order['price']} 元已原路退回。"
    return f"退款未通过审批：{order_id}。"
```

**为什么能工作**：`interrupt` 抛出的控制流被 LangGraph 运行时接住，图暂停，`invoke` 返回 `__interrupt__` 快照；外部用 `Command(resume="approved")` 同 thread 再 invoke，工具从 `interrupt(...)` 那行**返回 resume 值**继续跑。这一切的前提仍是 **checkpointer**（P4 已证：无 checkpointer 时 resume 报错）。

**与 P4 的差别一句话**：P4 教"interrupt 是什么"，P7 教"interrupt 怎么长在 ReAct agent 的工具里"——因为真实系统里审批点不在图结构上，而在某个具体动作（退款、发信、删数据）里。

### 接线 2：checkpointer 一石二鸟

P3 用 checkpointer 记对话，P4 用 checkpointer 存档断点。Phase 7 是**同一个 checkpointer 同时担这两件事**——记忆和审批在同一个 `create_agent(..., checkpointer=...)` 上协同。这是前 6 个 Phase 从没有过的组合。

### 接线 3：UI 只渲染"面向用户"的消息

真实 agent 的一条用户消息，内部会produce 一串消息：模型带 `tool_calls` 的中间消息、工具原始返回（`ToolMessage`）、最后无 `tool_calls` 的答复。**UI 只该渲染用户输入和最终答复**，中间过程是噪音。

这个坑是真实跑出来的（见第六节）：初版 UI 把 `ToolMessage` 和中间 `AIMessage` 都渲染成助手气泡，结果界面上出现了英文 preamble "I'll help you with the refund request" 和订单原始 JSON 文本。修复：

```python
for msg in history:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
        st.chat_message("assistant").markdown(msg.content)   # 只渲染最终答复
    # ToolMessage / 带 tool_calls 的中间 AIMessage → 跳过
```

## 四、完整交互闭环（退款审批）

```
[用户] 我要退款，订单 SO-1003，商品有质量问题
  │
  ├─ run_turn(thread_id, 文本)  →  agent.invoke(messages, config={thread_id})
  │     LLM 点菜 get_order_status → 查单 → LLM 点菜 request_refund
  │       → 工具内 interrupt({退款待审})  →  图暂停
  │     invoke 返回 __interrupt__ = [Interrupt(value={order_id, price, reason})]
  │
  ├─ UI 检测到 pending → 渲染审批卡片（订单/金额/理由 + ✅批准/❌拒绝）
  │
[用户] 点「✅ 批准」
  │
  └─ resume_turn(thread_id, "approved")  →  agent.invoke(Command(resume="approved"), 同 thread)
        工具从 interrupt() 返回 "approved" → 登记退款 → LLM 生成最终答复
        → UI 从 checkpointer 拉历史，渲染"退款已执行…"
```

## 五、复现与证据

**零成本冒烟（不调 API，假模型/假 agent）**：

```bash
# 后端机制链自测：记忆累积 / 审批批准+拒绝 / 会话隔离
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent7_webapp.py

# UI 冒烟：AppTest 走假 agent，验渲染/卡片/恢复
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent7_app_test.py

# 真实跑 UI（真实 DeepSeek）
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe -m streamlit run app.py
```

**本轮实跑证据（单次实跑、未挑选）**：

- `outputs\agent7_selftest.log`（exit 0）：同 thread 两轮 history 2→6 条（记忆累积）；退款 interrupt 暂停 → `resume(approved)` 退款登记 approved；`resume(denied)` 不执行退款；新 thread 历史为空（会话隔离）。
- `outputs\agent7_apptest.log`（exit 0）：页面渲染无异常 / 假 agent 应答 / 审批卡片+批准·拒绝按钮出现 / 点批准后卡片消失+恢复结果渲染。
- `outputs\agent7_live.log`（exit 0，真实 API）：① 查知识（真实检索七天无理由退货政策）② 查订单 SO-1003（状态 delivered）③ 退款申请触发 interrupt（待审快照 order_id=SO-1003, price=89）④ 批准恢复（退款登记 approved，回复含"89 元已原路退回"）。
- 真实浏览器端到端（browser_debug + 系统 Chrome CDP）：真实 LLM 正确"查订单→提交退款→interrupt 暂停"，审批卡片渲染，点批准后卡片消失、最终答复渲染，控制台 0 错误（旧页面残留除外）。

## 六、踩坑记录（都是本轮真实遇到的）

1. **探针报"架构假设不成立"，实为探针自身 bug**（重要教训：失败先归因，别把探针 bug 当环境 RED）。首跑 H2 报 `create_agent` 工具内 interrupt ❌——细看是两个探针缺陷：① 假模型 `bind_tools()` 签名不接受 `create_agent` 传入的 `tool_choice` 关键字；② 假模型发的 tool_call `args={}` 缺工具要求的 `question` 参数，导致 pydantic 校验失败（**在 interrupt 之前就报错了**，压根没走到 interrupt）。修好探针后三假设全 ✅。**教训**：验证"机制是否支持"时，先确认失败发生在被测机制那一层，而不是被测试脚手架自己的错误掩盖。
2. **FakeLLM 死循环**：自测的规则假模型只对 `request_refund` 的工具结果收敛，链路 1 调 `get_order_status` 后它不会收敛，反复点菜同一工具直到超时。修复：任何 `ToolMessage` 回来即总结。**教训**：假模型的收敛规则要覆盖它可能点名的所有工具。
3. **UI 渲染噪音**（见第三节接线 3）：`ToolMessage`/中间 `AIMessage` 不该上屏。
4. **streamlit rerun 时序**：审批按钮的回调里若手动渲染恢复结果、又 `st.rerun()`，rerun 后从 checkpointer 拉的历史会**再渲染一遍**，导致重复。修复：回调里只 `resume` + 清 pending + `rerun`，让 rerun 后的历史渲染自然带出结果。**这本身就印证了"checkpointer 即真相源"——结果不需要手动搬，它已在真相源里。**
5. **端口占用**：`kill` dev server 后端口未立即释放，换端口重起即可。

## 七、延伸方向（本 Phase 未做，供后续选）

- **流式打字机**：姊妹项目 `chat_agent.py:stream_turn` 的 `st.write_stream` 模式，可接在最终答复上（审批暂停语境下要处理中间态）。
- **防幻觉验证节点入图**（P4 实验 2）：把"工具核对模型事实主张"做成图节点，接进客服主图。
- **SqliteSaver 落盘**：本版默认 `MemorySaver`（进程内记忆）——P7 核心是 web 桥而非落盘。改成 `SqliteSaver.from_conn_string(outputs\agent7_chat.db)` 即"服务重启也不丢"，一行之差（注意 3.1.1 的生成器工厂用法，见 findings F7）。
- **多会话管理面板**：侧栏列出历史 thread（需读 checkpointer 的 thread 列表）。
- **多 agent**：把"客服经理"审批从人换成审核 agent（subgraph/supervisor，P6 已铺垫）。

## 八、三问法精读指引

1. **`app.py` 里为什么把 `thread_id` 存 `st.session_state`，而把消息历史存 checkpointer？**（答：session_state 是本次浏览器会话的临时抽屉，刷新即丢；thread_id 只是"钥匙"，真正的对话历史与断点必须在后端 checkpointer 里，才能"刷新/重跑不丢"——这正是 web 无状态与 agent 有状态的桥。）
2. **`request_refund` 里的 `interrupt()` 为什么必须配 checkpointer？**（答：resume 要靠 checkpointer 按 thread 找回"停在工具哪一行"的状态；无 checkpointer 时 `Command(resume=...)` 直接报错，P4 已证。）
3. **UI 为什么只渲染 `HumanMessage` 和无 `tool_calls` 的 `AIMessage`？**（答：其余是 agent 内部过程——工具原始返回、模型的中间思考文本；渲染出来就是噪音，用户只该看到自己的话和最终答复。）
