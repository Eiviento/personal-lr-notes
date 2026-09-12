# Progress Log

## 2026-09-12 · 项目启动（Wave 0-1：搭骨架 + 路线图）

### 背景
- 用户（应用软件工程师）问「已学的 LangChain/LangGraph/MCP 三线还有哪里要优化 + 为达标企业 AI 应用开发 JD 该学什么」，并附 JD 六条。
- 诊断结论：现有三项目是「理解层」（知识点驱动），缺「生产层」（系统能力）。
- 用户要求：单独建学习文件夹 + 详细学习计划。
- 计划批准：`.rivet/plans/ai-应用开发学习项目-对标企业-jd-差距诊断-详细路线.md`

### Wave 0 完成
- **Status:** complete
- 环境探针 `.rivet/scratch/probe_env.py` exit 0；结论见 `docs/findings.md` F1
- 关键结论：FastAPI/uvicorn/chromadb/psycopg2/PostgreSQL/RTX 4060 均可用；Redis/Docker/qdrant 缺 → 计划内降级

### Wave 1 完成
- **Status:** complete
- 目录骨架（13 目录：docs/lessons/src{rag,memory,agents,graphrag,api,finetune}/data/outputs/tests）
- `README.md`（路线总览 + 导航 + 环境事实）
- `docs/learning-plan.md`（★ 详细路线手册，6 阶段 × 知识点 × 产出 × 验证）
- `docs/progress.md`（本文件）/ `docs/findings.md`（探针结论）
- `requirements.txt` / `.env.example` / `.gitignore`

### 状态
本计划（搭家 + 路线图）完成。阶段 1-6 的实际学习按用户节奏逐个另开推进。

### 下一步（供后续会话）
- 从**阶段 1（生产级 RAG 服务）**起步：切分策略 → 混合检索 → rerank → 评估 → FastAPI 服务化
- 按用户节奏：讲解 → 实跑（零成本冒烟优先）→ 三问法精读 → 落盘 lessons
- 每阶段开工前先跑该项的最小 API/依赖探针（项目铁律）
