# HANDOFF — 交接文档

> **写给一个完全没有上下文的新会话。** 读完这份文档你应该能立刻接手继续。
> 更新日期：2026-08-30

---

## 一、我们在做什么

**目标**：帮用户（应用软件工程师，C++/Python/Java 背景，**LLM 开发零基础新手**）搭建一个 LLM 自动化工作流：

> 同事的需求文档（Markdown/TXT）→ 大模型分析 → 自动输出协议规范（字段表 + 约束规则 + 评审，JSON 给程序、Markdown 给同事）

**技术路线**：LangChain + Python + Prompt Engineering，DeepSeek API（OpenAI 兼容接口）。

**最近几轮会话的形式**：用户在**逐行精读代码**（每份脚本按"三问法"——干什么/吃什么吐什么/为什么这么写——逐块讲解），**每次讲解必须附带实际运行的执行示例**（用户 2026-08-29 明确要求），途中用户随时追问概念。已形成一套文档体系支撑教学。

---

## 二、已经完成了什么

### 功能层面：5 个 Phase 全部完成

| Phase | 内容 | 状态 |
|-------|------|------|
| 1 | Prompt 基本功（四要素/Few-shot/结构化输出/纯 SDK 实操） | ✅ |
| 2 | LangChain 核心（三大核心/LCEL/Parallel/Parser） | ✅ |
| 3 | 协议生成工作流（读文件→四步链→三种调用→验收入口） | ✅ |
| 4 | 增强（RAG 向量检索 / Function Calling / 人在回路） | ✅ |
| 5 | 部署（Streamlit Web UI / 重试+日志） | ✅（5.3 验收除外，见"卡在哪"） |

### 教学层面：全部 18 份代码已精读

- 13 份核心脚本 + app.py + 4 份 demo 全部**逐行讲解过**，每次带执行示例
- 落盘产物：
  - `lessons/code_walkthrough_phase1~5.md`：逐块精读（含用户追问的概念修正，如 f-string vs 占位符的准确区别、stream 首字延迟）
  - `lessons/scripts_overview.md`：全部代码速查（每份一张调用流程图 + 一句话总结）
  - `lessons/00_beginner_guide.md`：零基础总纲
  - `lessons/extra_*.md`：专题（LCEL 详解、LangChain vs LangGraph、RAG、工具调用、人工审核、LangSmith Studio）
  - `lessons/langchain_api_reference.md`：API 手册（9 章 26 词条七段式，查词条入口）
- 途中用户自己设计出了"并行分支 + 合并汇总"模式（demo_parallel_merge.py，实测效果超过串行链）

### 工程层面

- 目录重组：docs/（规划）+ lessons/（知识文档）+ scripts/（脚本）+ inputs/（示例与模板）+ outputs/（产物）
- 全部脚本输出路径已改为以 `__file__` 为基准（任何目录运行都正确）
- 运行环境固化：conda `agent_env`（langchain 1.x 全家桶 + streamlit + chromadb + langgraph），本地 BGE ONNX 模型在 `models/`（gitignore）

---

## 三、当前卡在哪

**没有卡点。** 仅剩的未完成事项：

1. **5.3 整体验收**（Phase 5 最后一项）：需要**用户提供一份真实的同事需求文档**，跑 `generate_protocol.py` 全流程。这一步依赖用户出素材。顺带兑现坑 #2：教学用假 Few-shot 示例/模板，届时替换成用户真实协议。
2. **app.py 的 stream 升级**（可选）：目前 UI 用 invoke（spinner 转圈），可接 `st.write_stream` 做打字机效果（教学时讲过"首字延迟"，用户对 stream 的价值已有认知）。

---

## 四、下一步计划（接手后立刻做）

1. 读 `docs/task_plan.md`、`docs/progress.md`（含完整错误日志）、`lessons/README.md`（文档地图）
2. **首选**：向用户要 5.3 的真实需求文档 → 跑 `PYTHONIOENCODING=utf-8 ... python scripts/generate_protocol.py <文档>` → 对比教学假例差距 → 必要时回补 Few-shot/`inputs/templates/`
3. 按用户节奏继续：用户可能选"继续深挖专题"（LangGraph interrupt / Streamlit stream 升级 / 复习文档提问），也可能暂停消化
4. 教学纪律（用户已明确立下的规矩）：
   - **每次讲解必须带实际运行的执行示例**（零成本 demo 优先，用户最喜欢）
   - 一次只问一个问题
   - **知识点必须落盘 lessons/ 文档**（零基础可读：做什么/为什么/不做会怎样），对话只是演示
   - 代码讲解用"三问法"：干什么 / 吃什么吐什么 / 为什么这么写

---

## 五、踩过的坑 & 绝对不要再踩

| # | 坑 | 教训 |
|---|-----|------|
| 1 | 一次问多个问题（1.3 结束时犯过） | 一次只问一个，用户答了再问下一个 |
| 2 | Few-shot 用教学假例（GPS 心跳等） | 教学可以假，最终模板/素材库必须换用户真实协议 |
| 3 | 用户说"暂时拿不出"还反复纠缠 | 果断跳过标记待办 |
| 4 | 起步阶段推 Tool Calling | 按阶段来；现在已到 4.2+ 可以用了 |
| 5 | Windows 控制台 GBK 吃不下 emoji | 跑脚本一律 `PYTHONIOENCODING=utf-8` 前缀 |
| 6 | 用错 Python（base 环境没装包） | 一律 `E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe` |
| 7 | 教完不更新 task_plan/progress | 每完成一个子任务立刻同步记录 |
| 8 | 知识点只放对话不落盘 | 必须写 lessons/，且零基础可读 |
| 9 | pip 直连 PyPI 失败 | 加清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 10 | chromadb 内置 ONNX 模型 S3 下载超时（URL 写死） | 用 `models/bge-small-zh/` 本地模型 + 自定义 EmbeddingFunction |
| 11 | MiniLM（英文）中文检索错乱 | 用 BGE 中文模型 + CLS 池化 + `hnsw:space=cosine`；**换 embedding 模型必须删 rag_db 重建** |
| 12 | 相对路径坑：从 scripts/ 目录跑脚本 Errno 2 | 输出路径一律 `Path(__file__).resolve().parent.parent / "outputs"` |
| 13 | 变量名记混（phase2_1 的 `chain` ≠ phase2_2 的 `full_chain`）；RunnableParallel 分支表在 `.steps__`（双下划线） | 演示/引用前先验证，报错信息里的 "Did you mean" 就是答案 |
| 14 | 讲 stream 说"更快" | 准确说法：总耗时一样，差别是**首字延迟**（用户追问过"没感觉"） |
| 15 | langchain_core 1.x 细节：StrOutputParser 返回 `TextAccessor`（str 子类，用 isinstance 判断）；`tool.invoke()` 返回 str 用 `str()` 包 | 版本差异属正常，报错照实修 |
| 16 | `langgraph dev` 要求 Python 3.11+，agent_env 是 3.10 装不上 | Studio 用独立 conda `studio_env`（3.11 + langgraph-cli[inmem] + langchain 系 + colorama），不动主环境 |
| 17 | 中文 Windows 跑 langgraph dev 连炸三连：dotenv 按 GBK 读 .env / structlog 缺 colorama / langgraph-api 读包内文件按 GBK | `.env` 纯 ASCII；`pip install colorama`；启动命令加 `PYTHONUTF8=1` |

---

## 六、关键文件索引

```
D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent\
├── README.md            # 项目说明、目录结构、快速开始
├── app.py               # 5.1 Web UI（streamlit run app.py）
├── requirements.txt     # 依赖清单（安装注释里有镜像命令）
├── langgraph.json       # LangSmith Studio 图入口（pipeline/agent 两图 → studio_graphs.py）
├── .env                 # Studio 环境变量（gitignore，纯 ASCII；LANGSMITH_API_KEY 待用户粘贴）
├── .gitignore           # models/、rag_db/、__pycache__/、.env 不入库
├── docs/                # task_plan（计划）/ progress（进度+错误日志）/ findings（决策）/ HANDOFF（本文）
├── lessons/             # 00 总纲 / code_walkthrough_×5 精读 / scripts_overview 速查 / extra_× 专题 / API 手册（9 章 26 词条）
├── scripts/             # 13 核心 + 4 demo + extra_langgraph_intro（各自开头 docstring 就是说明书）
├── inputs/              # sample_requirement×2（含 GBK 副本）/ templates/（4 份 RAG 模板素材）
├── outputs/             # 全部产物（草稿/终稿/评审/日志）
├── models/              # 本地 BGE ONNX（gitignore；重装从 hf-mirror 下载 Xenova/bge-small-zh-v1.5）
└── rag_db/              # 向量库（gitignore；scripts/phase4_1_rag.py build 重建）
```

---

## 七、用户画像速查

- **身份**：应用软件工程师（C++/Python/Java），做协议制定工作
- **LLM 水平**：零基础起步，但学得很快——从"完全不懂"到能独立设计并行合并工作流（Map-Reduce 简化版）
- **学习风格**：必须动手（要执行示例、要自己跑命令）；追问精准（常指出讲解不准确处，如"f-string 也能复用"）；实用主义，不纠结术语
- **沟通偏好**：话不多（"继续"/"合理"），但会主动打断纠正教学节奏
- **已立规矩**：讲解带执行示例、一次一问、知识点落盘、文档零基础可读

---

> **给新会话的第一句话建议**：
> "你好！我读了交接文档：项目是 LLM 协议自动生成工作流，5 个 Phase 功能全部完成，18 份代码已全部精读并落盘文档。当前只剩 5.3 验收——你手头有真实的同事需求文档吗？有的话我们跑全流程收尾。"
