# Phase 1 · 拆开黑盒：create_react_agent 里面到底是什么

> 2026-09-06。回答"官方封装到底替我们做了什么"——先把黑盒跑通看见循环，再运行时拆开图，最后手写一份等价白盒对照。配套脚本 `scripts/agent1_whitebox.py`。

## 一、先立住的事实：agent 是循环，不是一次调用

拿实跑轨迹（`outputs/agent1_blackbox_run.log`，单次实跑未挑选）看查订单 SO-1003 这一轮：

```
[模型点菜] agent → 调用工具 get_order_status({"order_id": "SO-1003"})
[工具上菜] tools → get_order_status 返回：订单 SO-1003：SmartHome 温湿度传感器…delivered
[agent] AIMessage: 我帮您查到了订单 SO-1003 的信息：…
```

- `agent` 节点出现 **2 次 = DeepSeek 被调用 2 次**。第 1 次看到问题后输出"点菜单"（tool_calls），第 2 次拿到工具结果后不再点菜、输出最终回答。
- 规律：**LLM 调用次数 = 工具执行次数 + 1**。若模型查完还要再查（如又问政策），会第 3 次点菜 → 第 3 次调用。
- 对比普通聊天助手（固定 1 次调用即回答）：agent 多出"请求执行工具"这一档决策，这是分水岭。

**为什么这是关键认知**：如果以为"agent = 一次调用"，后面所有调优（护栏、记忆、防幻觉）都没有下手点。知道它是循环，才知道每个环节该在哪加阀门。

## 二、黑盒内部：运行时图揭示（4 节点 4 边）

构建图对象后 `agent.get_graph()` 直接看（不 invoke 不调 API）：

```
节点：__start__ → agent → tools → __end__
边：  __start__→agent    agent→__end__    agent→tools    tools→agent
```

| 成分 | 是什么 | 对应轨迹里的哪一行 |
|------|--------|------------------|
| `agent` 节点 | 一次 LLM 调用（模型决策） | `[模型点菜]` 与最终 `AIMessage` 都出自它 |
| `tools` 节点 | 真实执行 Python 工具，结果回填 | `[工具上菜]` |
| `agent→tools` | **条件边**：模型输出含 tool_calls 才走 | 点菜后的流转 |
| `agent→__end__` | 同一条件边的另一分支：不再点菜就结束 | 最终回答后的停止 |
| `tools→agent` | 工具结果回传，形成循环 | 上菜后再回模型 |

**create_react_agent 的全部封装 = 两个干活节点（模型、工具）+ 一条条件分流边 + 状态累积。** 没有魔法。

## 三、手写等价白盒（验证封装无魔法）

用 `StateGraph` 抄同样的 4 节点（见脚本 `build_whitebox_agent`），三个关键机制：

1. **`llm.bind_tools(tools)`**——把工具的名字+参数 schema 发给模型，模型才"知道能点哪些菜"。没 bind 的模型只会说话，不会点菜。
2. **条件边 `tools_condition`**——prebuilt 提供的现成判定：最后一条消息有 tool_calls → `"tools"`，否则 → `END`。等价于手写 `if last.tool_calls: return "tools"; return END`。
3. **状态累积 `Annotated[list, add_messages]`**——节点返回的新消息被**追加**进共享状态而不是覆盖，多轮对话才能累积。黑盒内部也用它（`create_react_agent` 的 state_schema 默认含 messages）。

实跑对照（`outputs/agent1_whitebox_run.log`，单次实跑未挑选）：黑盒与白盒跑同一问题 SO-1003，轨迹逐行一致——点菜 → 上菜 → 回答。**封装只是把这张图画好打包了，你随时能抄回来自己改。**

## 四、真实缺陷案例：agent 表现 = 图结构 × 工具质量

首次实跑发现：模型把用户问题"七天无理由退货**怎么算**"自动改写成了 `query="七天无理由退货**政策**"` 再调 `search_knowledge`——我的检索用整串子串匹配，改写后的措辞在知识库文本里不存在 → **漏检**。

关键观察分两层：
- **agent 行为是对的**：工具返回"未找到"后，模型如实转述"知识库没覆盖、建议换问法"，**没有编造政策**——系统提示里的防幻觉规则生效了。
- **工具质量拖了后腿**：循环没问题，是工具的检索匹配太脆（模型措辞一变就 miss）。

修复：检索改为 **n-gram 子串匹配**（取 query 的 4~8 字连续片段，任一命中块文本即中），本地验证 4 种问法（含模型改写的）全部命中；重跑后政策问题正常回答。

**教训**：agent 是"图结构（循环怎么转）× 决策输入（工具 schema/提示词）× 工具质量（上菜准不准）"三者的乘积。P2 讲图结构的护栏，P4 讲工具结果的可靠性——但工具检索本身的质量从第一天就在影响表现。

## 五、三问法精读指引（对着 `scripts/agent1_whitebox.py`）

1. **`search_knowledge` 吃什么吐什么**？——吃 query 字符串，吐知识库命中块（前 3 块）。为什么不直接整库给模型？token 与噪声（这个 demo 库小，但机制要对，P4 检索质量再深挖）。
2. **`call_model` 为什么拼 SystemMessage + state["messages"]**？——模型是无状态的，每次调用要自己带全上下文。黑盒的 `prompt=` 参数干的就是这件事。
3. **`tools_condition` 返回什么**？——返回**节点名**（`"tools"` 或 `END`），条件边按返回的节点名决定流向。这就是"图"的语义：边不只是直线，还可以按运行时结果分流。

## 六、本课产出与证据

| 产出 | 路径 |
|------|------|
| 脚本（黑盒 + 白盒 + 检索修复） | `scripts/agent1_whitebox.py` |
| 黑盒实跑轨迹 | `outputs/agent1_blackbox_run.log` |
| 白盒对照轨迹 | `outputs/agent1_whitebox_run.log` |
| 运行时图结构 | 见上文第二节（`agent.get_graph()` 可复现） |

复现命令：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent1_whitebox.py`（需 .env 配好 DEEPSEEK_API_KEY）
