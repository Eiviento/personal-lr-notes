# HANDOFF — 交接文档（收官版）

> 写给未来任何会话/用户自己：项目已完成，此文档是"成果地图 + 续玩入口"。
> 更新日期：2026-09-08（7 Phase 全部完成，Phase 7 客服工作台为收官综合）

## 一、项目是什么（一句话）

从空目录完整走完 7 Phase 的 **LangGraph 技术支持客服 Agent 深度研学**：每 Phase = 可跑脚本 + 实跑证据 + 零基础 lesson + 带用户三问法讲解。前 6 Phase 逐个拆解单 agent 机制（白盒/护栏/记忆/审批/评估/V2+子图），Phase 7 把 6 机制**拼成一个可交互 Streamlit 客服工作台**（web 无状态 ↔ agent 长时运行的 thread_id 桥）。姊妹项目 `..\LangChain-RAG-Agent`（LangChain 基础）。

## 二、最终成果地图（全部在 main，已推远程）

**7 个可跑脚本 + 7 份 lesson**（scripts\ ↔ lessons\lesson_agent{1..7}）：

| Phase | 脚本 | 学会什么 |
|-------|------|---------|
| 1 拆黑盒 | agent1_whitebox.py | agent=循环；黑盒/白盒同是图；封装无魔法 |
| 2 护栏 | agent2_guardrails.py | recursion_limit / 重复熔断 / 异常回流（默认只兜 ToolInvocationError 的坑） |
| 3 记忆 | agent3_memory.py | checkpointer 持久化 / thread_id / SqliteSaver 跨进程 |
| 4 可靠 | agent4_interrupt.py | interrupt 人审 / 防幻觉验证节点 |
| 5 评估 | agent5_eval.py | eval 集 + 判据 + 单变量回归（V1 6/7 vs V2 7/7） |
| 6 规模化 | agent6_scale.py | create_agent V2 迁移（0 警告）/ subgraph |
| 7 工作台 | agent7_webapp.py + app.py | 把 6 机制拼成可交互系统：thread_id 桥 / checkpointer 即真相源 / 工具内 interrupt / UI 只渲染面向用户的消息 |

**教学资产**：`lessons/qa_notes_20260906.md` = 用户问题链 Q1-Q18 + Python 语法速查 + 概念速查（含 P5 判据分层、P6 V2 迁移/subgraph 白话讲解——知识手册生长点）。README 进度表全 ✅。`outputs/` 全部实跑日志（gitignore）。probe_api.py 环境基线（fail-closed）。

## 三、跑通环境

conda `agent_env`（Python 3.10.19 / langgraph 1.2.9 / langgraph-prebuilt 1.1.0 / langchain-core 1.4.9 / langchain 1.3.14 / langgraph-checkpoint-sqlite 3.1.1）。脚本一律 `PYTHONIOENCODING=utf-8` + agent_env python 绝对路径。`.env` 需 DEEPSEEK_API_KEY（用户提供，勿读勿提交）。

## 四、用户画像与学习状态（供未来续教参考）

应用软件工程师（C++/Python/Java），从"LLM agent 零基础"到学完 6 Phase，概念问答对答如流（Q1-Q16 全吸收）。喜动手、要实跑示例、一次一问、知识落盘。中途会插 Python 语法/C++ 对照/API 机制问题——先答透再回主线。

## 五、续玩入口

- ✅ **可交互 demo** 已完成 = Phase 7 客服工作台（`app.py` + `scripts\agent7_webapp.py`，带审批中断）。详见 `lessons\lesson_agent7_webapp.md`。

按兴趣深挖（按性价比排序）：

1. **SqliteSaver 落盘**：Phase 7 默认 `MemorySaver`（进程内）——改 `SqliteSaver.from_conn_string(outputs\agent7_chat.db)` 一行即"服务重启也不丢"（见 lesson_agent7 延伸方向 + findings F7 的 3.1.1 生成器工厂用法）。
2. **多 agent 协作**：把"客服经理"审批从人换成审核 agent（subgraph 已铺垫，可组 supervisor/worker）。
3. **流式打字机 UI**：`st.write_stream` 接最终答复（姊妹项目 chat_agent.py 的 stream_turn 模式）。
4. **防幻觉验证节点入图**（P4 实验 2）：把"工具核对模型事实主张"做成节点接进客服主图。
5. 把 qa_notes 扩展成正式知识手册（用户最初愿望：基于笔记做完整学习流程）。

## 六、给未来会话的开场建议

"项目已 7 Phase 完成（见 README 进度表 + lessons/）。你可以：①带用户精读任一脚本（三问法，Phase 7 的 `app.py`/`agent7_webapp.py` 值得重点看 thread_id 桥与工具内 interrupt）；②跑客服工作台玩（`streamlit run app.py`，需 `.env` 配 DEEPSEEK_API_KEY；零成本验证用 `scripts/agent7_app_test.py`）；③推进可选深挖（见第五节）。用户概念已通，直接进应用层。"
