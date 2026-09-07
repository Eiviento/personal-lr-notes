# HANDOFF — 交接文档（收官版）

> 写给未来任何会话/用户自己：项目已完成，此文档是"成果地图 + 续玩入口"。
> 更新日期：2026-09-06（6 Phase 全部完成，计划 EXECUTED）

## 一、项目是什么（一句话）

从空目录完整走完 6 Phase 的 **LangGraph 技术支持客服 Agent 深度研学**：每 Phase = 可跑脚本 + 实跑证据 + 零基础 lesson + 带用户三问法讲解。姊妹项目 `..\LangChain-RAG-Agent`（LangChain 基础）。

## 二、最终成果地图（全部在 main，已推远程）

**6 个可跑脚本 + 6 份 lesson**（scripts\ ↔ lessons\lesson_agent{1..6}）：

| Phase | 脚本 | 学会什么 |
|-------|------|---------|
| 1 拆黑盒 | agent1_whitebox.py | agent=循环；黑盒/白盒同是图；封装无魔法 |
| 2 护栏 | agent2_guardrails.py | recursion_limit / 重复熔断 / 异常回流（默认只兜 ToolInvocationError 的坑） |
| 3 记忆 | agent3_memory.py | checkpointer 持久化 / thread_id / SqliteSaver 跨进程 |
| 4 可靠 | agent4_interrupt.py | interrupt 人审 / 防幻觉验证节点 |
| 5 评估 | agent5_eval.py | eval 集 + 判据 + 单变量回归（V1 6/7 vs V2 7/7） |
| 6 规模化 | agent6_scale.py | create_agent V2 迁移（0 警告）/ subgraph |

**教学资产**：`lessons/qa_notes_20260906.md` = 用户问题链 Q1-Q16 + Python 语法速查 + 概念速查（知识手册生长点）。README 进度表全 ✅。`outputs/` 全部实跑日志（gitignore）。probe_api.py 环境基线（fail-closed）。

## 三、跑通环境

conda `agent_env`（Python 3.10.19 / langgraph 1.2.9 / langgraph-prebuilt 1.1.0 / langchain-core 1.4.9 / langchain 1.3.14 / langgraph-checkpoint-sqlite 3.1.1）。脚本一律 `PYTHONIOENCODING=utf-8` + agent_env python 绝对路径。`.env` 需 DEEPSEEK_API_KEY（用户提供，勿读勿提交）。

## 四、用户画像与学习状态（供未来续教参考）

应用软件工程师（C++/Python/Java），从"LLM agent 零基础"到学完 6 Phase，概念问答对答如流（Q1-Q16 全吸收）。喜动手、要实跑示例、一次一问、知识落盘。中途会插 Python 语法/C++ 对照/API 机制问题——先答透再回主线。

## 五、续玩入口（可选深挖方向，按兴趣取）

1. 把技术支持客服 agent 拼成**完整可交互 demo**：真实对话 CLI（接 MemorySaver 持久化）+ 可选 Streamlit UI（对标 LangChain-RAG-Agent 的 app.py 薄壳模式）
2. **多 agent 协作**：主客服 + 审核 agent（subgraph 已铺垫，可组 supervisor/worker）
3. create_agent V2 全面迁移现有 agent1-5（脚本已留 V2 样板）
4. 把 qa_notes 扩展成正式知识手册（用户最初愿望：基于笔记做完整学习流程）

## 六、给未来会话的开场建议

"项目已 6 Phase 完成（见 README 进度表 + lessons/）。你可以：①带用户精读任一脚本（三问法）；②推进可选深挖（见 HANDOFF 第五节）；③把 qa_notes 扩成知识手册。用户概念已通，直接进应用层。"
