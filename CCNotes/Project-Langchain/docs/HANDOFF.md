# HANDOFF — 交接文档

> 写给完全没有上下文的新会话。读完即能接手。
> 更新日期：2026-09-06（W1/W2 完成、进入 W3 前，会话收尾）

## 一、我们在做什么

**目标**：带用户（应用软件工程师 C++/Python/Java，已学完姊妹项目 LangChain-RAG-Agent 的 LangChain 五阶段基础）深度学习 **Agent**。从空目录建一个 LangGraph 技术支持客服 Agent demo，按已批准计划走 6 Phase，每 Phase = 代码 + 实跑证据 + 知识点落盘 lessons + 带用户三问法精读。

**用户当前状态**：概念层已打通（agent 循环/图机制/护栏原理），Python 语法补课完成（@tool/闭包/TypedDict/Annotated/类型标注）。**精读完成第一份代码 `scripts/agent1_whitebox.py`（245 行全文逐段读完）**；agent2 概念讲过但未逐段精读（用户中途转去补语法，计划中的"实验 2 熔断精读"可后续补或跳过）。

**已批准计划**：`docs/superpowers/plans/全量-agent-深度研学-langgraph-技术支持助手-6-phase-从零到成品.md`
**项目文档**：README（进度表/结构/快速开始）；docs/progress.md、docs/findings.md；**lessons/qa_notes_20260906.md（用户今日问题链 + 语法速查——后续知识手册的生长点，新会话务必先读它了解用户已懂什么）**

## 二、已完成（commit 均在 main）

| Wave | 内容 | 提交 |
|------|------|------|
| W0 | 项目骨架（README/AGENTS/.rivet/requirements/.env.example/.gitignore）+ data 假数据 + API 基线探针 `scripts/probe_api.py`（fail-closed） | 3d3b0b4 |
| W0 修复 | 审查修复：probe 基线语义 / README 可跑 / orders 反例改 absent-id / requirements 补 langchain | 410ea56 |
| W1 (P1) | `scripts/agent1_whitebox.py`：黑盒 create_react_agent + 手写白盒 StateGraph 对照 + 检索 n-gram 修复；`lessons/lesson_agent1_whitebox.md` | 054bfc7 |
| W2 (P2) | `scripts/agent2_guardrails.py`：三类护栏实验；`lessons/lesson_agent2_guardrails.md` | fc484c6 |

实跑证据留档 `outputs/`：agent1_blackbox_run.log、agent1_whitebox_run.log、agent2_guardrails_run.log（均"单次实跑未挑选"）。
教学用探针在 `.rivet/scratch/`：py_syntax_demo.py、graph_walkthrough.py、graph_api_probe.py（不入库，可复跑参考）。

## 三、当前卡点 / 待决策

1. **无阻塞。** DEEPSEEK_API_KEY 已配置（用户提供 sk- 开头 35 字符 key，写入项目 .env；.env 是 gitignore，新会话不要读不要提交）。
2. **P3 持久化方案待定（W3 开头问用户）**：SqliteSaver 需独立包 `langgraph-checkpoint-sqlite`（agent_env 未装）。选项：① pip 清华镜像安装实现真落盘（推荐，P3 教学价值在"重启不丢"）；② 用 MemorySaver 降级（进程内）。装包属环境变更，先经用户同意。

## 四、下一步（W3 / Phase 3 记忆与状态）

计划要点（详见已批准计划 Wave 3）：
1. `scripts/agent3_memory.py`：先 MemorySaver + thread_id 教概念（进程内记忆）→ 装 SqliteSaver 后演示"重启进程不丢"
2. 历史治理对照实验：全量重发 vs trim_messages 窗口 vs 摘要，20 轮实测 token 消耗表（lesson 第五节已预告"token 治理是 P3 的病根"）
3. `lessons/lesson_agent3_memory.md` 落盘 + 带用户三问法讲解
4. 后续 P4 interrupt 人工审批 / P5 eval / P6 V2 迁移+subgraph（用户此前已连答对多个理解题，可提速，但每 Phase 仍要实跑证据）

## 五、教学纪律（用户立的规矩，一条不破）

- 讲解必带实跑执行示例；一次只问一个问题；知识点落盘 lessons/（零基础可读：做什么/为什么/不做会怎样）；代码精读三问法
- 证据来自实跑可复现；实录引用写"单次实跑、未挑选"；数字来自工具输出不凭记忆
- 脚本一律 `PYTHONIOENCODING=utf-8` 前缀 + 文件内 `sys.stdout.reconfigure(encoding="utf-8")`；用 agent_env python 绝对路径
- 用户是节奏拍板人，每 Phase 可停靠；**用户会中途插入概念问题，先答透再继续主线**
- 用户 C++ 背景但 Python 特性（装饰器/闭包/Annotated）需要补——**读复杂代码前先确认语法层没有洞**（本次教训见坑 #7）

## 六、踩过的坑——绝对不要再踩

| # | 坑 | 规避 |
|---|-----|------|
| 1 | **deliver_task 归属台账在子目录项目持续漂移**（路径前缀格式每调用变、.env 被卷入提交范围、误报 stale"已被他会话提交"） | 交付改走**受控 bash git**：`git add 明确文件路径`（不 add -A）→ `git status --short` 核实暂存区干净 → `git commit`。deliver_task 仅用于无子目录归属问题的场景 |
| 2 | **用户/旧文档说"key 已配好"≠ 文件里真有**。LangChain-RAG-Agent\.env 只有 LANGSMITH_API_KEY，多次误报 key 就绪；浪费多轮 | 配 key 一律 `python -c "from dotenv import dotenv_values; print(sorted(dotenv_values('.env').keys()))"` 实测键名（不打印值）；本项目 .env 需用户提供 DEEPSEEK key |
| 3 | 无头 worker（delegate code_scout）读不了 E:\site-packages（越出工作区无审批通道） | 主会话用 `inspect.getsource()` 运行时拿源码文本；或 bash sed 读（bash 无此限制） |
| 4 | langgraph 1.2.9 主包**无** checkpoint.sqlite；SqliteSaver 在独立包 langgraph-checkpoint-sqlite | 见第三节决策点；probe_api.py 已把 sqlite 组标 expected=False（fail-closed 基线） |
| 5 | **ToolNode 默认 handle_tool_errors 只兜 ToolInvocationError，业务异常默认 raise 炸穿**（实测崩溃 exit 1） | 兜业务异常要显式 `ToolNode(tools, handle_tool_errors=True)`；lesson_agent2 第四节有源码证据 |
| 6 | outputs/ 与 .rivet/ 已 gitignore → read_file 拒读 | 读日志用 `bash cat outputs/*.log` |
| 7 | **教学节奏：一次甩 200+ 行代码给用户会直接看不懂**（本次 W2 后用户明说"代码看不懂"） | 讲解按段（3-5 段/轮）拆，先给"楼层图"再逐层；用户卡住先问"卡在哪层"再对症 |
| 8 | create_react_agent 在 1.2.9 签名带 `version='v2'` 参数（默认 v2），且有弃用警告（LangGraphDeprecatedSinceV10）；V2 `langchain.agents.create_agent` 已存在 | P1-P5 教学沿用 create_react_agent（经典先学透），P6 教迁移；实际调用时观察警告如实记录 |
| 9 | CRLF/LF warning（Windows 换行）每次提交出现 | 无害，忽略 |
| 10 | 工具函数改名/加参会破坏 agent2 import（agent2 `from agent1_whitebox import ...`） | 改 agent1 工具前 grep 消费方 |

## 七、给新会话的第一句话建议

"你好！读了 HANDOFF：项目是 LangGraph 技术支持客服 Agent 深度研学，W0-W2（骨架/拆黑盒/护栏）已完成并提交，用户已精读 agent1_whitebox.py、概念与 Python 语法已打通。当前无阻塞，只剩 W3 一个待你问用户的决策：记忆持久化装不装 langgraph-checkpoint-sqlite 独立包。建议开场：先读 lessons/qa_notes_20260906.md 了解用户已懂什么 → 问 SqliteSaver 装包决策 → 开始 Phase 3 记忆与状态。"
