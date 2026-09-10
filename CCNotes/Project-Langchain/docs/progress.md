# Progress Log

## Session: 2026-09-06（Wave 0：项目骨架 + API 探针）

### 项目启动
- 用户拍板：新建独立项目 + 通用 Demo（技术支持客服 Agent）+ 6 Phase 全量
- 计划批准：`.rivet/plans/全量-agent-深度研学-langgraph-技术支持助手-6-phase-从零到成品.md`
- 复制计划到 `docs/superpowers/plans/` 入库存档

### Wave 0 完成
- **Status:** complete
- 骨架：README.md / AGENTS.md / .rivet.md / requirements.txt / .env.example / .gitignore
- 数据：data/knowledge.txt（SmartHome Hub FAQ，8 主题）+ data/orders.json（假订单库含 SO-9999 反例）
- API 运行时探针：9/10 组通过，SqliteSaver 需独立包（见 findings.md）
- Files created: README.md, AGENTS.md(.gitignore 追加配置段), requirements.txt, .env.example, .gitignore, data/knowledge.txt, data/orders.json, docs/HANDOFF.md, docs/progress.md(本文件), docs/findings.md, lessons/README.md, .rivet/scratch/probe_langgraph.py

## Session: 2026-09-06（W1-W6 完整收官，6 Phase 全部完成）

### W1-W6 完成记录（详见 lessons/ 各 lesson + outputs/ 各 log）
- **W1 (P1 拆开黑盒)** `054bfc7`：agent1_whitebox.py（黑盒 create_react_agent + 手写白盒 StateGraph 对照 + 检索 n-gram 修复）；lesson_agent1；实跑 exit 0 留档 agent1_*_run.log
- **W2 (P2 护栏)** `fc484c6`：agent2_guardrails.py 三类护栏（recursion_limit 误杀实验 / 重复熔断 / 工具异常默认 raise 实测坑）；lesson_agent2
- **W3 (P3 记忆)** `97ae7a8`：装 langgraph-checkpoint-sqlite 3.1.1 + agent3_memory.py（失忆对照 / MemorySaver thread 隔离 / SqliteSaver 跨进程"重启不丢"）；lesson_agent3；probe 基线更新
- **W4 (P4 可靠)** `da4e0ff`：agent4_interrupt.py（interrupt 退款审批 approve/deny + 防幻觉验证节点两场景）；lesson_agent4
- **W5 (P5 评估)** `cfad20b`：agent5_eval.py（7 case eval 集 + 判据三迭代 + 单变量回归 V1 6/7 vs V2 7/7）；lesson_agent5
- **W6 (P6 规模化)** `44ad987`：agent6_scale.py（create_agent V2 迁移对照 0 警告 + subgraph 父/子图）；lesson_agent6
- **教学资产**：lessons/qa_notes_20260906.md（Q1-Q16 概念问答+语法速查）；README 进度表 0-6 全 ✅
- 全部提交已推送远程（push 验证 ahead=0 behind=0）

### 状态：6 Phase 全部完成（计划 EXECUTED）

## Session: 2026-09-08（Phase 7 客服工作台：把 6 机制拼成可交互 Streamlit Demo）

- 触发：用户问"在 6 Phase 基础上额外深入学习什么" → 主线建议 Phase 7（web 无状态↔agent 长时运行的桥）→ 用户拍板"主线吧"
- 计划：`.rivet/plans/phase-7-客服工作台-把-6-个机制拼成可交互-streamlit-demo.md`（APPROVED）
- **W0 API 锚点探针**（`.rivet/scratch/probe_p7_api.py`，零 API）：H1 create_agent 支持 checkpointer ✅ / H2 工具内 interrupt+resume ✅ / H3 V2+SqliteSaver 组合 ✅ → 方案 A（V2 主图）成立。首跑 H2 报 ❌ 系探针自身两个 bug（`bind_tools` 缺 `tool_choice` 参数 / tool_call 缺 `question` 参数），非架构问题——修复后全 ✅
- **W1 业务后端** `scripts/agent7_webapp.py`：复用 agent1 工具 + 新增 `request_refund`（工具内 interrupt）· build_agent（V2 create_agent + checkpointer）· run_turn/resume_turn/get_history · FakeAgent/FakeLLM · 零 API self-test。证据 `outputs/agent7_selftest.log`（exit 0）：记忆累积 2→6 条 / 审批批准+拒绝 / 会话隔离
- **W2 UI 薄壳** `app.py` + 冒烟 `scripts/agent7_app_test.py`：Streamlit 会话管理（thread_id）+ 历史从 checkpointer 拉 + 审批卡片（批准/拒绝 → resume）。`outputs/agent7_apptest.log`（exit 0）
- **W2b 真实渲染**：browser_debug 连系统 Chrome CDP（9222）——FakeAgent 模式走通"发消息→审批卡片→点批准→恢复结果"，0 控制台错误
- **W3 真实 API 实跑**：`outputs/agent7_live.log`（exit 0）查知识 / 查订单 / 退款 interrupt 暂停 / 批准恢复（登记 approved）；真实浏览器端到端（8766 端口）真实 DeepSeek 走通全链路
- **W3 修复**：真实 LLM 暴露 UI 渲染噪音（中间英文 preamble + 工具原始返回被渲染成气泡）→ app.py 改为只渲染用户消息 + 无 tool_calls 的最终答复；重验干净
- Files: `app.py`, `scripts/agent7_webapp.py`, `scripts/agent7_app_test.py`, `lessons/lesson_agent7_webapp.md`, `lessons/README.md`(索引), `README.md`(进度表), `requirements.txt`(+streamlit), `docs/progress.md`(本段), `docs/findings.md`(F8), `docs/HANDOFF.md`

### 状态：Phase 7 完成（客服工作台）

