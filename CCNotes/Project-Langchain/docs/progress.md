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
