# Phase 3 · 记忆与状态：让 agent 记住对话

> 2026-09-06。回答"agent 怎么记住多轮对话"。三类记忆机制实验全部实跑（零 API——记忆是框架层机制，用 FakeLLM 正好证明"记忆不在模型、在框架"）。配套脚本 `scripts/agent3_memory.py`。

## 一、核心论断：LLM 没有记忆，记忆在框架层

你已从 P1/P2 慢镜头看到：每次 `agent` 节点调用，模型收到的是"系统提示 + **全部历史**"（消息数 2→4→7→10 增长）。因为 **LLM 是无状态的**——它不记得上一轮，你必须每轮把历史全喂给它。

那"记住对话"靠谁？**框架层**。LangGraph 的 **checkpointer（检查点）**：图每执行完一步，把当时的 state（含 messages）落盘存起来；下次用**同一个 thread_id** 的 invoke 进来时，先从检查点恢复历史，再接着跑。**模型还是那个没记忆的模型，但框架替它把历史保管好了。**

```
无 checkpointer：  invoke → 从空 state 开始 → 每次都是全新会话（失忆）
有 checkpointer：  invoke(config thread_id="a") → 找到"a"的检查点 → 恢复历史 → 接着跑
```

## 二、三类实验证据（outputs/ 无日志——零 API，看终端输出即可复现）

### A · 失忆对照（不挂 checkpointer）
两次 invoke 都从空开始。实测：第二轮 FakeLLM **只看到 1 条消息**（用户新问的话），第一轮"记住我的订单号是 SO-1003"根本没进来 → 模型对上一轮一无所知。

### B · MemorySaver + thread_id（进程内记忆）
```python
graph.compile(checkpointer=MemorySaver())
graph.invoke(input, config={"configurable": {"thread_id": "alice"}})
```
实测（`python scripts/agent3_memory.py`）：
- thread `alice` 第 2 轮 → FakeLLM 看到 **3 条**（第 1 轮 user+ai + 本轮）——历史累积了
- thread `bob` 第 1 轮只看到 1 条 → 不同 thread **完全隔离**，bob 看不到 alice 说过的话

**thread_id = 会话钥匙**：同一个 id = 同一段连续对话；不同 id = 不同用户/不同会话。多用户客服系统的"每人一段记忆"就是靠它。

### C · SqliteSaver（落盘持久化，"进程重启不丢"）
```python
# 用法是生成器工厂（langgraph-checkpoint-sqlite 3.1.1 实测形态）
with SqliteSaver.from_conn_string("outputs/memory_demo.db") as saver:
    graph.compile(checkpointer=saver)
```
实测（分两个进程）：
- `python agent3_memory.py store`：进程 1 在 thread `carol` 下聊两轮 → 关闭连接，对话落盘（db 28KB）
- `python agent3_memory.py ask`：进程 2（= 新进程/重启）重开同一 db → thread `carol` 再问 → FakeLLM **看到 5 条消息**（4 条历史 + 本轮）→ 跨进程恢复成功

**这就是"关掉程序对话还在"的原理**：state 不在内存、在磁盘文件里。生产上换 PostgreSQL/Redis checkpointer 即可支持多实例共享。

## 三、token 治理：历史会无限膨胀，三种策略的取舍

记忆带来的副作用：每轮全量重喂 → 对话越长 token 越贵。实测 20 轮后（`~2字符/token` 近似，脚本见本课复现）：

| 策略 | 保留 | 估算 token | 优点 | 代价 |
|------|------|-----------|------|------|
| ① 全量重发 | 40 条 | 561 | 细节全保留 | 随对话线性涨，最贵 |
| ② 固定窗口（最近 5 轮） | 10 条 | 142 | 规模恒定 | 早期事实全丢（用户开头报的订单号会忘） |
| ③ 摘要 + 保留近期 | 11 条 | 249 | 早期要点仍在、规模小 | 细节丢（要再调 LLM 生成摘要） |

工程实践：②③ 组合（长对话把早期压成摘要、近期留原文）最常用。LangChain 有现成 `trim_messages` / 摘要工具，但 **1.4.9 实测其 token_counter 按"整个列表"调用、总量超 max_tokens 时返回空列表**（与"保留尾部"的直觉不符）——用法疑点已记录，正确姿势需读源码确认后再用于生产；本课三策略为自实现（逻辑透明，权衡同理）。

## 四、关键代码认知（对照 agent3_memory.py 读）

1. **加记忆 = 只在 compile 加一个参数**：`compile(checkpointer=None)` → `compile(checkpointer=MemorySaver())`——图结构一行没改。这是"手写图才有改装权"的又一例（黑盒 create_react_agent 也支持 checkpointer 参数）。
2. **thread_id 藏在 config 里**：`config={"configurable": {"thread_id": "..."}}`——invoke 时告诉框架"这是哪个会话"。
3. **checkpointer 与 model 无关**：FakeLLM 跑完全成立 → 证明"记忆能力是框架白给的，换什么模型都有"。
4. **db 文件路径**：`outputs/memory_demo.db`（gitignore，运行时产物）。

## 五、复现与证据

```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent3_memory.py            # A + B
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent3_memory.py store      # C 进程1
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent3_memory.py ask        # C 进程2
```

## 六、踩坑记录

- `SqliteSaver` 在独立包 `langgraph-checkpoint-sqlite`（3.1.1，W3 装）；**只导出同步 SqliteSaver，无 AsyncSqliteSaver**；`from_conn_string` 是**生成器工厂**（`with ... as saver`），不是 0.x 的 `SqliteSaver(conn)`。
- `trim_messages`（langchain-core 1.4.9）实测语义与直觉不符（counter 按整列表调用、超限返回空）——用前读源码。

## 七、三问法精读指引

1. `build_agent(llm, checkpointer)`：checkpointer 参数传到 compile 还是别处？为什么"加记忆不改图结构"？（答：compile 时注入，图拓扑与记忆机制解耦）
2. run_turn 的 `config={"configurable":{"thread_id":...}}`：thread_id 是给谁看的？（答：checkpointer 用它做"钥匙"找历史，不是给模型的）
3. FakeLLM 演示为什么能证明"记忆在框架"？（答：模型是假的、无记忆能力，历史却累积了——只能是框架存的）
