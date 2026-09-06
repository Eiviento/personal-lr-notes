# HANDOFF — 交接文档

> 写给完全没有上下文的新会话。读完即能接手。
> 更新日期：2026-09-06（W4 完成、进入 W5 前）

## 一、我们在做什么

**目标**：带用户（应用软件工程师 C++/Python/Java，已学完姊妹项目 LangChain-RAG-Agent 的 LangChain 五阶段基础）深度学习 **Agent**。从空目录建一个 LangGraph 技术支持客服 Agent demo，按已批准计划走 6 Phase，每 Phase = 代码 + 实跑证据 + 知识点落盘 lessons + 带用户三问法讲解。

**用户当前状态**：W1-W4 全部学完并吸收（agent 循环/图机制/Python 语法/记忆/护栏/interrupt 概念问答对答如流）。**精读完成 agent1_whitebox.py 全文**；agent2/3/4 已讲透机制（未逐行精读，用户中途常插入 Python/概念问题，先答透再继续）。概念问答笔记 Q1-Q16 在 `lessons/qa_notes_20260906.md`（含 docstring 三命运、__init__=构造函数、鸭子类型、invoke vs stream 等——**新会话先读它了解用户已懂什么，避免重复教**）。

**已批准计划**：`docs/superpowers/plans/全量-agent-深度研学-langgraph-技术支持助手-6-phase-从零到成品.md`
**项目文档**：README（进度表）；docs/progress.md、docs/findings.md、docs/HANDOFF.md（本文）

## 二、已完成（commit 均在 main，已推远程）

| Wave | 内容 | 提交 |
|------|------|------|
| W0 | 骨架 + data + API 基线探针（probe_api.py fail-closed） | 3d3b0b4 / 410ea56 |
| W1 (P1) | agent1_whitebox.py 黑盒+白盒对照 + 检索 n-gram 修复 + lesson | 054bfc7 |
| W2 (P2) | agent2_guardrails.py 三类护栏 + lesson | fc484c6 |
| W3 (P3) | **装 langgraph-checkpoint-sqlite 3.1.1**（用户同意，probe 基线更新）+ agent3_memory.py（MemorySaver/thread_id/SqliteSaver 跨进程）+ token 治理对照 + lesson | 97ae7a8 |
| W4 (P4) | agent4_interrupt.py（interrupt 退款审批 approve/deny + 防幻觉验证节点）+ lesson | da4e0ff |
| 问答追加 | qa_notes：W3 三问(Q13-15)、invoke/stream(Q16) | bf07a38 / e354975 |

实跑证据留档 `outputs/`（gitignore）：agent1_blackbox_run.log、agent1_whitebox_run.log、agent2_guardrails_run.log、memory_demo.db（SqliteSaver 落盘演示产物）。教学探针在 `.rivet/scratch/`：py_syntax_demo / graph_walkthrough / graph_api_probe / interrupt_probe（不入库可复跑）。

## 三、当前卡点 / 待决策

**无阻塞、无待决策。** DEEPSEEK_API_KEY 已配（.env，用户提供，勿读勿提交）。W3 的 SqliteSaver 装包决策已落地（用户选装）。

## 四、下一步（W5 / Phase 5 观察与评估）

计划要点（已批准计划 Wave 5）：
1. `scripts/agent5_eval.py`：构造 N 个代表性客服场景 + 判据（工具调用正确 / 答案含事实 / 不编造），批量回放打分——把前四课所有"调优"从感觉升级成测量
2. 单变量回归实验：只改一句系统提示 → eval 分数前后对比（**一次只改一个变量的方法论收拢**）
3. `lessons/lesson_agent5_eval.md` 落盘 + 讲解
4. 后续 W6（P6 规模化）：V2 create_agent 迁移对照 + subgraph + 全项目收尾（HANDOFF/progress 终更 + plan close）

## 五、教学纪律（用户立的规矩，一条不破）

- 讲解必带实跑执行示例；一次只问一个问题；知识点落盘 lessons/（零基础可读）；代码精读三问法
- 证据来自实跑可复现；实录引用写"单次实跑、未挑选"；数字来自工具输出不凭记忆
- 脚本一律 `PYTHONIOENCODING=utf-8` 前缀 + 文件内 `sys.stdout.reconfigure(encoding="utf-8")`；用 agent_env python 绝对路径
- 用户是节奏拍板人，每 Phase 可停靠；**用户会中途插入概念问题（Python 语法/C++对照/API 机制），先答透再继续主线**
- 教学零成本优先：机制演示用 FakeLLM（假模型）零 API 已验证可行——记忆/护栏/interrupt 都与模型无关，假模型跑真框架机制

## 六、踩过的坑——绝对不要再踩

| # | 坑 | 规避 |
|---|-----|------|
| 1 | **deliver_task 归属台账在子目录项目持续漂移**（路径前缀格式每调用变、.env 被卷入提交、误报 stale） | 交付走**受控 bash git**：`git add 明确路径`（不 add -A）→ `git status --short` 核实 → `git commit` |
| 2 | **"key 配好了"≠ 文件里真有**。LangChain-RAG-Agent\.env 只有 LANGSMITH；用户两次误报 key 就绪 | 一律 `dotenv_values('.env')` 实测键名（不打印值）；本项目 .env 由用户提供 sk- 开头 key |
| 3 | 无头 worker（delegate）读不了 E:\site-packages（越界无审批） | 主会话 `inspect.getsource()` / bash sed 读源码 |
| 4 | SqliteSaver 是独立包 `langgraph-checkpoint-sqlite`（已装 3.1.1）；**只导出同步 SqliteSaver 无 Async**；`from_conn_string` 是生成器工厂（`with ... as`） | probe_api.py 基线：SqliteSaver True / Async False；写代码按 3.x 形态 |
| 5 | ToolNode 默认 handle_tool_errors **只兜 ToolInvocationError，业务异常默认 raise**（实测崩溃） | 显式 `handle_tool_errors=True`；lesson_agent2 有源码证据 |
| 6 | outputs/ 与 .rivet/ gitignore → read_file 拒读 | 读日志用 `bash cat outputs/*.log` |
| 7 | **一次甩 200+ 行代码用户直接看不懂**（W2 后用户明说） | 讲解按段拆、先给"楼层图"再逐层；卡住先问"卡在哪层" |
| 8 | create_react_agent 1.2.9 带 `version='v2'` 且有弃用警告；V2 `langchain.agents.create_agent` 已存在 | P1-P5 沿用 create_react_agent，P6 教迁移 |
| 9 | CRLF/LF warning | 无害忽略 |
| 10 | 工具改名/加参破坏跨脚本 import（agent2/3/4 `from agent1_whitebox import ...`） | 改 agent1 工具前 grep 消费方 |
| 11 | **`Command(resume=...)` 无 checkpointer → RuntimeError**；中断返回形态是 state 带 `__interrupt__`（非异常），payload 在 `.value` | interrupt 恢复必须 compile(checkpointer) + 同 thread_id；从 `out.get("__interrupt__")[0].value` 取待审内容 |
| 12 | **trim_messages（langchain-core 1.4.9）实测语义与直觉不符**：counter 按整列表调用、总量超 max_tokens 返回空列表 | P3 token 治理用自实现三策略（逻辑透明）；官方工具用法用前需读源码 |
| 13 | TypedDict state schema 严格要求节点返回键都在类型里声明（漏键报 unknown channel） | 节点要写回的新字段先加进 state 类 |

## 七、给新会话的第一句话建议

"你好！读了 HANDOFF：LangGraph 技术支持客服 Agent 研学项目，W0-W4（骨架/拆黑盒/护栏/记忆/interrupt+防幻觉）全完成已推送，用户概念已打通（先读 lessons/qa_notes_20260906.md 的 Q1-Q16 了解他已懂什么）。无阻塞无待决策。下一步 W5 观察与评估（eval 集 + 单变量回归）——建议开场：确认用户状态 → 开始 Phase 5。"
