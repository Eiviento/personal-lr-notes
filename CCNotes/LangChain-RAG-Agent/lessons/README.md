# 知识点讲解文档索引

**新手入口 → [00_beginner_guide.md](00_beginner_guide.md)**：从零看懂整个项目——每一步做什么、为什么这么做、不做会怎样。不预设任何前置知识。

每完成一个 Phase 的知识点教学，更新对应文档。**讲解内容以这里的文档为准，对话只是现场演示。**

| 文档 | 覆盖内容 | 对应脚本 |
|------|---------|---------|
| [00_beginner_guide.md](00_beginner_guide.md) | **总纲（新手从这里开始）**：底层概念 → 管线地图 → 每步详解 → 文件地图 → 术语表 | 全部 |
| [code_walkthrough_phase1.md](code_walkthrough_phase1.md) | **代码精读**：phase1_4 逐块讲解（六块 + 自测清单），读代码的"三问法"示范 | `scripts/phase1_4_req_to_protocol.py` |
| [code_walkthrough_phase2.md](code_walkthrough_phase2.md) | **代码精读**：phase2_1 LangChain 重写版逐块对比 + 途中概念追问（f-string vs 占位符的准确区别 / 工具箱边界 / RunnableLambda） | `scripts/phase2_1_langchain_basics.py` |
| [code_walkthrough_phase3.md](code_walkthrough_phase3.md) | **代码精读**：phase3_1 喂文件版（编码自适应/大小检查/噪声提取）+ 实测示例 | `scripts/phase3_1_doc_input.py` |
| [code_walkthrough_phase4.md](code_walkthrough_phase4.md) | **代码精读**：phase4_1 RAG（分词/推理/池化内部三步 + 踩坑三连 + 语义检索实测） | `scripts/phase4_1_rag.py` |
| [code_walkthrough_phase5.md](code_walkthrough_phase5.md) | **代码精读**：app.py Web UI（重跑模型/session_state/cache_resource/薄壳原则/AppTest） | `app.py` |
| [scripts_overview.md](scripts_overview.md) | **速查总览**：全部 18 份代码——每份一张调用流程图 + 一句话总结 | 全部 |
| [phase1_prompt_basics.md](phase1_prompt_basics.md) | Prompt 四要素 / Few-shot / 结构化输出三法 / 纯 SDK 实操 | `scripts/phase1_4_req_to_protocol.py` |
| [phase2_langchain_core.md](phase2_langchain_core.md) | 三大核心 / LCEL 管道 / Lambda·Parallel·Passthrough / Parser 选型 | `scripts/phase2_*.py` |
| [phase3_workflow.md](phase3_workflow.md) | 文档输入三问题 / 四步 Prompt 链 / assign 挂键 / LLM·Python 分工 | `scripts/phase3_*.py` |
| [phase3_3_chain_assembly.md](phase3_3_chain_assembly.md) | 组装三原理（一切皆 Runnable / 代码=数据流 / 没有魔法）、组装 5 步法、invoke/batch/stream | `scripts/phase3_3_batch_stream.py` |
| [phase4_rag.md](phase4_rag.md) | RAG 三件套 / embedding 内部三步 / 向量库检索 / 实测对比 / 环境坑三连（镜像、S3、MiniLM 中文失效） | `scripts/phase4_1_rag.py` |
| [phase4_tool_calling.md](phase4_tool_calling.md) | 模型点菜代码上菜 / 何时用工具 / @tool + bind_tools + 工具循环 / 与 LLM 评审互补 | `scripts/phase4_2_tool_calling.py` |
| [phase4_human_review.md](phase4_human_review.md) | 人在回路 / 机审两层分工 / 草稿终稿分离 / 审计留痕 / 交互设计 | `scripts/phase4_3_human_review.py` |
| [phase5_deploy.md](phase5_deploy.md) | Streamlit 心智模型（重跑/session_state/cache_resource）/ UI 薄壳原则 / AppTest 冒烟 | `app.py` |
| [extra_langchain_langgraph.md](extra_langchain_langgraph.md) | LangChain=积木箱 / LCEL 天花板 / LangGraph=图编排（循环·分支·暂停）/ 决策表 / 进阶路线 | `scripts/extra_langgraph_intro.py` |
| [extra_lcel_explained.md](extra_lcel_explained.md) | LCEL=组装约定（a\|b = 输出接输入）/ 最小演示 / 真实数据流追踪 / 三种组合 / 四个好处 | 全部 phase2/3 脚本 |
| [extra_langsmith_studio.md](extra_langsmith_studio.md) | LangSmith Studio：图可视化调试器 / 独立 studio_env（3.11）/ 三配置文件 / 踩坑四连（GBK/colorama/PYTHONUTF8） | `scripts/studio_graphs.py` + `langgraph.json` |
| [langchain_api_reference.md](langchain_api_reference.md) | **API 手册（查词条来这里）**：9 章 26 词条七段式（签名/参数表/真实输出示例/项目出处/原理/踩坑）+ 配套 demo 脚本 | `scripts/demo_api_reference.py` |

约定：
- 每个文档 = 知识点（表格优先）+ 为什么（原理）+ 踩过的坑
- 新 Phase 开始或旧 Phase 补充内容时，同步更新这里
