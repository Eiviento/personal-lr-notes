# AI-Application-Engineering · AI 应用开发学习项目

> 对标企业「AI 应用开发工程师」招聘要求，用一条贯穿始终的**企业级 AI 助手平台**主线，把从「会搭 Agent」到「能交付生产级 AI 应用」的缺口逐个补齐。

## 这是什么

这是用户在完成三条 AI 学习线之后的**第二条主线**：

| 阶段 | 项目 | 定位 |
|------|------|------|
| 理解层 | `..\LangChain-RAG-Agent` | LangChain 基础 + RAG + 对话 Agent |
| 理解层 | `..\Project-Langchain` | LangGraph 7 Phase（机制全景） |
| 理解层 | `..\mcp-hello1` | MCP 协议 |
| **生产层** | **本项目** | **把机制组装成可部署/可观测/可扩展的系统** |

**一句话区别**：旧项目回答「这个机制是什么」，本项目回答「怎么把它做成能上线的服务」。

## 学习路线总览

六个阶段，环环相扣（详见 `docs/learning-plan.md`）：

| 阶段 | 主题 | 对标 JD | 可跑产出 |
|------|------|---------|---------|
| 1 | 生产级 RAG 服务 | ③⑥② | 可 `curl` 的检索问答 API + 检索策略评估报告 |
| 2 | 记忆体系 | ③④ | 跨会话长期记忆 + 遗忘实验 |
| 3 | 多 Agent 协同 + Skill 编排 | ①④ | 多 Agent 客服系统（含 MCP 工具） |
| 4 | GraphRAG / 知识图谱融合 | ④ | 建图 + GraphRAG 问答 + 对比实验 |
| 5 | 工程化与生产部署 | ②⑤⑥ | 多进程/容器化服务 + 限流 + 监控 + 成本统计 |
| 6 | 模型微调适配 | ⑤ | 小模型 LoRA 微调实验（本机 RTX 4060） |

## 目录结构

```
AI-Application-Engineering\
├── README.md            # 本文件：路线总览 + 导航
├── requirements.txt     # 依赖清单
├── .env.example         # 环境变量键名示例（.env 本体 gitignore）
├── docs\
│   ├── learning-plan.md # ★ 详细学习路线手册（每个阶段的目标/知识点/产出/验证）
│   ├── progress.md      # 进度日志
│   └── findings.md      # 决策与踩坑（含 Wave0 环境探针结论）
├── lessons\             # 每阶段知识落盘（零基础可读：做什么/为什么/不做会怎样）
├── src\
│   ├── rag\             # 阶段1：生产级 RAG
│   ├── memory\          # 阶段2：记忆体系
│   ├── agents\          # 阶段3：多 Agent 协同 + Skill 编排
│   ├── graphrag\        # 阶段4：知识图谱融合 RAG
│   ├── api\             # 阶段5：FastAPI 服务 + 中间件
│   └── finetune\        # 阶段6：微调适配
├── data\                # 知识库 / 语料 / 评测集
├── outputs\             # 实跑日志与产物（gitignore）
└── tests\               # 零成本冒烟（假模型/假 agent，不调 API）
```

## 环境事实（Wave 0 探针实测，2026-09）

| 能力 | 状态 | 影响 |
|------|------|------|
| Python FastAPI 0.133.1 + uvicorn 0.41.0 | ✅ agent_env 已装 | 阶段 1/5 的 API 服务可行 |
| pydantic 2.12.5 / httpx 0.28.1 | ✅ | 请求校验 + 客户端 |
| chromadb 1.5.9 | ✅ | 阶段 1 向量库（已有经验） |
| psycopg2 2.9.10 + PostgreSQL（5432 在跑） | ✅ | 阶段 5 关系库持久化 |
| **NVIDIA RTX 4060 Laptop 8GB** | ✅ | **阶段 6 可做小模型 LoRA/QLoRA** |
| Redis（客户端 + 服务） | ✗ 缺失 | 阶段 5 缓存 → 降级内存/文件方案 |
| Docker | ✗ 未装 | 阶段 5 部署 → 降级本地多进程编排脚本 |
| qdrant-client / qdrant 服务 | ✗ 缺失 | 阶段 1 向量库备选，按需安装 |

> 探针脚本与完整输出见 `.rivet\scratch\probe_env.py`（属 Project-Langchain 的 scratch，一次实跑）

## 阶段 1 成果（DocQA · 已实现）

- **模块**：`src/rag/{splitter,embedder,store,bm25,retriever,reranker,generator}.py` + `src/api/main.py` + `src/evaluation/evaluate.py`
- **测试**：`tests/` 26 个单测全绿（零成本假件，不调 API）
- **评估**：`scripts/run_eval.py` → 混合检索 hit_rate/recall = 1.00（20 题）最优；降级 rerank 反而拖低 MRR（详见 `lessons/lesson_01..04`）
- **服务**：`uvicorn src.api.main:create_app --factory --port 8000`；客户端 `scripts/ask.py "问题"`
- ⚠️ **真实 DeepSeek 生成环节未验证**：API key 失效（401），检索链路正常（见 `lessons/lesson_04_eval_api.md`）

## 运行方式

- 解释器：`E:\software\OfficeWorkLife\Anaconda\envs\agent_env\python.exe`
- 脚本一律加 UTF-8 前缀：`PYTHONIOENCODING=utf-8 <python> <script>`（Windows GBK 坑）
- `.env` 存 `DEEPSEEK_API_KEY`（gitignore，勿读勿提交）

## 教学约定（继承前三个项目，一条不破）

- 每阶段：讲解 → 写代码实跑（零成本冒烟优先）→ 三问法精读 → 落盘 `lessons\`
- 一次只问一个问题；知识点必须落盘且零基础可读
- 证据纪律：声称跑通须 exit 0 + 日志；引用实录写「单次实跑、未挑选」
- API 锚点以 agent_env 实测为准（先跑最小探针再落教学代码）
