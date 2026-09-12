# 知识点文档索引（Agent 深度研学）

每完成一个 Phase 更新本索引与对应文档。**讲解内容以这里的文档为准，对话只是现场演示。**

| 文档 | 覆盖内容 | 对应脚本 |
|------|---------|---------|
| qa_notes_20260906.md | **学习日志（2026-09-06）**：用户问题链 Q&A×12（tool vs MCP / 黑盒白盒 / call_model / 条件边等）+ Python 语法速查 + LangGraph 概念速查——后续知识手册生长点 | 全部 |
| lesson_agent1_whitebox.md | 拆开黑盒：agent=循环（LLM 调用=工具执行+1）/ 运行时图揭示 4 节点 4 边 / 手写白盒对照 / 检索漏检案例 | `scripts/agent1_whitebox.py` |
| lesson_agent2_guardrails.md | 阀门与护栏：recursion_limit 大坝 / 重复熔断闸门 / 异常回流（默认只兜 ToolInvocationError 的实测坑） | `scripts/agent2_guardrails.py` |
| lesson_agent3_memory.md | 记忆与状态：LLM 无记忆/记忆在框架(checkpointer)/thread_id 会话钥匙/MemorySaver→SqliteSaver 跨进程/token 治理三策略 | `scripts/agent3_memory.py` |
| lesson_agent4_reliability.md | 可靠性与人在回路：interrupt 暂停恢复（依赖 checkpointer）/ 审批 approve+deny / 防幻觉验证节点（工具核对拦编造） | `scripts/agent4_interrupt.py` |
| lesson_agent5_eval.md | 观察与评估：eval 集+判据 / 单变量回归实测（V1 6/7 vs V2 7/7，诱导 case 显差异）/ 判据防假阴假阳三迭代 / 调优方法论总纲 | `scripts/agent5_eval.py` |
| lesson_agent6_scale.md | 规模化与版本演进：create_react_agent→create_agent 迁移对照（prompt→system_prompt）/ subgraph 子图拆父图 | `scripts/agent6_scale.py` |
| lesson_agent7_webapp.md | **客服工作台（综合）**：把 6 机制拼进可交互系统——web 无状态↔agent 长时运行的 thread_id 桥 / checkpointer 即真相源 / 工具内 interrupt（P4 升级）/ UI 只渲染面向用户的消息 | `scripts/agent7_webapp.py` + `app.py` |

**前置知识**（姊妹项目 LangChain-RAG-Agent）：Tool Calling（phase4_2）、LangGraph 概念（extra_langgraph_intro）、对话 Agent 三零件（extra_chat_agent）、聊天助手构建（extra_chat_assistant_build）。
