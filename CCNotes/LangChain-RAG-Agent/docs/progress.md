# Progress Log

## Session: 2026-07-12

### Phase 1: Prompt Engineering 基本功
- **Status:** complete
- **Started:** 2026-07-12
- **Completed:** 2026-07-19
- Actions taken:
  - 完成用户背景调研（技术栈、LLM 经验、学习目标、使用场景）
  - 产出 3 种学习路径方案并确定方案二 + 方案三组合
  - 拆解 5 阶段学习计划并获用户确认
  - 创建 task_plan.md、findings.md、progress.md 规划文件
  - 完成 1.1 Prompt 四要素教学
  - 完成 1.2 Few-shot Prompting 教学（示例模板待用户补充）
  - 完成 1.3 结构化输出控制教学（三种方式 + Python 容错代码）
  - 创建 HANDOFF.md 交接文档
  - 完成 1.4 实操：用 DeepSeek API + OpenAI SDK 调通"需求 → 协议字段表"脚本
- Files created/modified:
  - task_plan.md (created)
  - findings.md (created)
  - progress.md (created)
  - HANDOFF.md (created)

### Phase 2: LangChain 核心概念
- **Status:** complete
- **Started:** 2026-07-19
- **Completed:** 2026-08-29
- Actions taken:
  - 完成 2.1 LangChain 三大核心（PromptTemplate + Model + Parser），用 LCEL 管道重写 Phase 1.4 脚本并调通
  - 完成 2.2 LCEL 管道进阶：RunnableLambda / RunnableParallel / RunnablePassthrough，并行校验（字段完整性、上报频率、总字节数）跑通，输出保存 protocol_output_lcel.json
  - 完成 2.3 StrOutputParser / JsonOutputParser 对比实操：同一需求走三条路（无 Parser → AIMessage / Str → 纯文本 / Json → dict），输出保存 protocol_summary.txt、protocol_output_parser.json
  - 2.4 内容已在 2.1 重写中覆盖（原生 SDK vs LCEL 逐项对比），勾选完成
- Files created/modified:
  - phase2_1_langchain_basics.py (created)
  - protocol_output_langchain.json (created)
  - phase2_2_lcel_pipeline.py (created)
  - protocol_output_lcel.json (created)
  - phase2_3_output_parsers.py (created)
  - protocol_summary.txt (created)
  - protocol_output_parser.json (created)

### Phase 3: 构建协议生成工作流
- **Status:** complete
- **Started:** 2026-08-29
- **Completed:** 2026-08-29
- Actions taken:
  - 完成 3.1 文档输入：编码自适应读取（utf-8-sig → utf-8 → gb18030 顺序尝试）、token 估算与超长警告、全文直塞 LLM 提取字段；UTF-8 与 GBK 两份样本均跑通，7 字段提取成功
  - 完成 3.2 Prompt 模板链：4 步链（①需求分析 Str → ②字段定义 Json → ③约束规则 Json → ④Python 合并），用 RunnablePassthrough.assign 逐步挂键；跑通并输出 6 条约束 + 3 条评审 warning（一段式发现不了的）
  - 完成 3.3 Chain 串联：组装三原理（一切皆 Runnable / 代码结构=数据流结构 / invoke 无魔法）、组装 5 步法、invoke/batch/stream；batch 实测 2 份文档（环境监测 + 智能水表）跑通，stream 打字机演示成功；用户明确要求讲解"怎么组装、为什么这么写、原理"
  - 完成 3.4 验收：generate_protocol.py 单一入口（文件进 → JSON + Markdown 双输出），数据/呈现分离（LLM 出 JSON，Python 渲染 Markdown）；2 份文档跑通，Phase 3 完成
- Files created/modified:
  - phase3_1_doc_input.py (created)
  - sample_requirement.md (created, 模拟同事写法的带噪声需求文档)
  - sample_requirement_gbk.txt (created, GBK 编码副本用于验证编码自适应)
  - sample_requirement_protocol.json (created)
  - sample_requirement_gbk_protocol.json (created)
  - phase3_2_prompt_chain.py (created)
  - sample_requirement_protocol_full.json (created)
  - phase3_3_batch_stream.py (created)
  - sample_requirement2.md (created, 智能水表需求：下行控制/校验/告警场景)
  - batch_sample_requirement_protocol.json (created)
  - batch_sample_requirement2_protocol.json (created)
  - generate_protocol.py (created, Phase 3 最终交付物)
  - sample_requirement_protocol.md (created)
  - sample_requirement2_protocol.md (created)

### Phase 4: 增强与优化
- **Status:** complete
- **Started:** 2026-08-29
- **Completed:** 2026-08-29
- Actions taken:
  - 完成 4.1 RAG 基础：chromadb 向量库存 4 份历史协议模板；自定义本地 ONNX embedding 函数（WordPiece + onnxruntime + 池化）；RAG 链 = 3.4 链 + 检索步骤（仅换字段定义环节）；水表需求对比实测：RAG 版自动继承模板命名风格（meter_id/total_flow/crc16）
  - 完成 4.2 Function Calling / Tool Use：@tool 定义校验工具 + bind_tools + 手写工具循环（点菜/上菜）；实测模型自主发起 7 次字段校验，揪出人为注入的 msg_type 字节数错误并输出修正报告
  - 完成 4.3 人工审核（Human-in-the-loop）：机审两层（代码校验 + LLM 评审）→ 逐条人工处理（自动修正/忽略/待办）→ 终稿分离（_final.json/_final.md + 审核记录）；实测注入错误被代码和 LLM 各自独立发现，管道喂决策跑通全流程
- Files created/modified:
  - phase4_1_rag.py (created, build/query/run 三子命令)
  - inputs/templates/ 4 份模板 (created, 教学假例待替换真实协议)
  - models/bge-small-zh/ (hf-mirror 下载的 BGE ONNX，已 gitignore)
  - rag_db/ (向量库，已 gitignore)
  - rag_sample_requirement2_protocol.json (created)
  - phase4_2_tool_calling.py (created)
  - rag_sample_requirement2_protocol_validation.txt (created)
  - phase4_3_human_review.py (created)
  - rag_sample_requirement2_protocol_final.json / _final.md / _review_log.json (created)

### Phase 5: 部署上线
- **Status:** in_progress
- **Started:** 2026-08-29
- Actions taken:
  - 完成 5.1 Streamlit Web UI：app.py 薄壳封装（上传→触发→tabs 展示→双下载），session_state 防重生成 + cache_resource 缓存链；AppTest 冒烟 0 异常；streamlit run 实测 HTTP 200；4.1 检索加 lru_cache
  - 完成 5.2 错误处理/重试/日志：llm.with_retry（指数退避+抖动，挂 llm 不挂链）；RotatingFileHandler 日志落 outputs/app.log；模拟 API 不可达实测 3 次重试后快速失败（26.5s），正常路径 200 成功并留日志；发现 SDK 层与 LangChain 层双重重试现象
  - 额外（用户提问）：LangChain vs LangGraph 详解——LangChain=积木箱、LangGraph=图编排（循环/分支/暂停）；实操两个图：四步链的直线图 + 工具校验 agent 循环图（模型自动循环 9 次校验），均跑通
- Files created/modified:
  - app.py (created)
  - phase4_1_rag.py (modified: 检索缓存)
  - phase5_2_robust.py (created)
  - outputs/app.log (created)
  - extra_langgraph_intro.py (created)
  - outputs/langgraph_demo_result.json (created)

### 专题：LangSmith Studio 安装
- **Status:** complete
- **Started:** 2026-08-30
- Actions taken:
  - 调研现状：macOS 桌面版已废弃；官方形态 = 网页 Studio + 本地服务，`langgraph dev` 免 Docker
  - 安装踩坑四连并全部解决：agent_env 3.10 装不了 [inmem]（建 studio_env 3.11）→ dotenv 按 GBK 读 .env 炸（改纯 ASCII）→ structlog 缺 colorama（补装）→ langgraph-api 读文件按 GBK 炸（PYTHONUTF8=1）
  - 建 langgraph.json + scripts/studio_graphs.py（模块级编译图 pipeline/agent）+ .env（gitignore）
  - 冒烟测试通过：/ok 返回 {"ok":true}，/assistants/search 两图（agent/pipeline）注册成功
  - 知识点落盘 lessons/extra_langsmith_studio.md；HANDOFF 坑表新增 #16/#17
- Files created/modified:
  - langgraph.json (created)
  - scripts/studio_graphs.py (created)
  - .env (created, gitignored)
  - .gitignore (modified: .env)
  - lessons/extra_langsmith_studio.md (created)
  - lessons/README.md (modified: 索引)
  - docs/HANDOFF.md (modified: 坑表/产物/文件索引)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| 3.1 文档输入 | sample_requirement.md（UTF-8）+ sample_requirement_gbk.txt（GBK） | 两种编码均正确读入并提取协议字段 | 7 字段（含 messageType、预留扩展位），两次均跑通 | ✅ |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-08-29 | UnicodeEncodeError: 'gbk' codec can't encode emoji（Windows 控制台 GBK 编码） | 直接运行 phase2_3 脚本 | 运行时加 `PYTHONIOENCODING=utf-8` 环境变量；后续 Windows 跑脚本默认都带上 |
| 2026-08-29 | ChatPromptTemplate 报 missing variables {'fields'} | 3.2 链中 assign 挂的键名 `protocol` 与 ③ Prompt 占位符 `{fields}` 不一致 | 键名与占位符对齐（挂 `fields` 键）；教训：assign 挂键必须和下游占位符同名，报错是防漏配的保护机制 |
| 2026-08-29 | pip 装 chromadb 失败（PyPI 连接被重置 + 依赖解析失败） | 直连 pypi.org | 用清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 成功 |
| 2026-08-29 | chromadb 内置 ONNX embedding 模型下载超时（S3 国内不通，URL 写死） | 首次 add() 触发模型下载 | 从 hf-mirror 下载 Xenova/bge-small-zh-v1.5 的 onnx 到 models/，自定义 EmbeddingFunction 本地推理 |
| 2026-08-29 | MiniLM（英文模型）中文检索排序错乱：查"水表阀门"命中环境监测模板 | 直接诊断两两余弦 | 换 BGE-small-zh-v1.5（CLS 池化）+ hnsw:space=cosine，检索正确（top-1 命中水表，距离 0.364） |
| 2026-08-29 | `[Errno 2] No such file or directory: 'outputs/...'`——用户从 scripts/ 目录运行脚本，相对路径以当前工作目录为基准 | 用户实操 phase1_4 时踩中 | 全部脚本输出路径改为以 `__file__` 为基准（`Path(__file__).resolve().parent.parent / "outputs"`），任何目录运行都正确；教训：**相对路径不相对脚本文件，相对运行目录** |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 1 - Prompt Engineering 基本功 |
| Where am I going? | Phase 2 (LangChain) → Phase 3 (工作流) → Phase 4 (增强) → Phase 5 (部署) |
| What's the goal? | 搭建基于 LangChain + Python 的协议自动生成工作流 |
| What have I learned? | See findings.md |
| What have I done? | 完成需求调研、方案设计、计划拆解、文件初始化 |

---
*Update after completing each phase or encountering errors*

### 专题：LangChain API 参考手册
- **Status:** complete
- **Started:** 2026-08-30
- Actions taken:
  - 收集素材：版本基线 / 26 词条签名 / 行号引用 → docs/api_ref_notes.md
  - 编写 scripts/demo_api_reference.py（9 节，零成本优先）并全量实跑
  - 真实输出捕获至 outputs/demo_api_reference_run.log（手册示例的唯一来源）
  - 手册 9 章完成（输出全部抄自实跑日志）
  - 索引更新
  - 全量验证通过
  - 素材笔记删除

### 专题：聊天助手（Streamlit 聊天窗口 + agent 大脑 + 真调实录）
- **Status:** complete
- **Started:** 2026-08-30
- Actions taken:
  - 升级 app.py 为聊天窗口：st.chat_message 气泡 / st.chat_input / st.write_stream 打字机 / 侧栏双下载，薄壳原则不变
  - 新建 scripts/chat_agent.py 大脑：create_react_agent + 两个 @tool（generate_protocol 包整条 rag_chain 回传摘要、validate_field_type 照抄 4.2）+ SYSTEM_PROMPT 四要素；模块级状态（headless CLI 可复用）
  - AppTest 冒烟：CHAT_FAKE_AGENT=1 假 agent 替身，不真调 API（default_timeout=30 适配冷启动 ~5.2s；file_uploader.set_value 适配 streamlit 1.62.0 元组 API）
  - 真调实录：demo_chat_cli.py 三轮回话（闲聊 / 生成协议 / 字段校验）真调 DeepSeek，模型自主点菜两次，完整对话存 outputs/chat_demo_transcript.log
  - 教学文档 lessons/extra_chat_assistant_build.md（三零件拼装 / create_react_agent vs 手写循环对照 / 打字机三规则 / 实跑原文 / 踩坑）+ 索引与规划文件同步
- Files created/modified:
  - app.py (modified: 聊天窗口重写)
  - scripts/chat_agent.py (created)
  - scripts/demo_app_test.py (created)
  - scripts/demo_chat_cli.py (created)
  - outputs/chat_demo_transcript.log (created)
  - lessons/extra_chat_assistant_build.md (created)
  - lessons/README.md (modified: 索引)
  - docs/HANDOFF.md (modified: 待办 #2 完成 / 文件索引)
