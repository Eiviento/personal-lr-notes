# Findings — 决策与踩坑

## 2026-09-12·Wave 0 环境探针

### F1: 环境可用性实测（决定阶段 1-6 技术选型）

**探针**：`.rivet\scratch\probe_env.py`（Project-Langchain 的 scratch），agent_env 解释器，单次实跑 exit 0。

| 能力 | 结果 | 对计划的影响 |
|------|------|-------------|
| FastAPI 0.133.1 | ✅ agent_env 已装 | 阶段 1/5 的 API 服务直接可用，无需安装 |
| uvicorn 0.41.0 | ✅ | 服务可起 |
| pydantic 2.12.5 / httpx 0.28.1 | ✅ | 请求校验 + 异步客户端 |
| chromadb 1.5.9 | ✅ | 阶段 1 向量库（复用 LangChain-RAG-Agent 经验） |
| psycopg2 2.9.10 | ✅ | 阶段 5 关系库客户端 |
| PostgreSQL 服务（5432 开放） | ✅ 本机在跑 | 阶段 5 持久化可行，无需装 |
| redis-py（客户端） | ✗ ModuleNotFoundError | 阶段 5 缓存 → 降级内存/文件方案；需时装 `redis` + 服务 |
| 5432/6379/6333 端口 | pg ✅ / redis ✗ / qdrant ✗ | 缓存与向量库服务需自行启动或降级 |
| Docker | ✗ PATH 无 docker | 阶段 5 部署 → 降级「本地多进程编排脚本」；需时装 Docker Desktop |
| **NVIDIA RTX 4060 Laptop 8GB** | ✅ | **阶段 6 可做小模型 LoRA/QLoRA**（8GB 显存适配 0.5B~1.5B 模型） |
| qdrant-client | ✗ | 阶段 1 向量库备选，按需安装 |

**结论**：六个阶段**全部可推进**。无硬阻塞，只有两处降级（Redis 缓存、Docker 部署），均已在本手册标注替代方案。GPU 到位使阶段 6 从「只能演示」升级为「可真跑」。

### F2: 学习项目的定位边界（防重复）

- 旧三项目 = **理解层**（机制是什么）：LangChain-RAG-Agent / Project-Langchain / mcp-hello1
- 本项目 = **生产层**（怎么组装成系统）：可部署/可观测/可扩展/可并发
- 复用而非重写：LLM 封装、工具定义、eval 判据、MCP 代码从旧项目搬，不重新发明

## 2026-09-12 · 阶段 1 实施中发现

### F3: DEEPSEEK_API_KEY 失效（401，环境问题）
- **现象**：Wave4 真实 API 端到端问答时，`/qa` 返回 500，服务端日志 `openai.AuthenticationError: 401 ... api key is invalid`（尾号 a3b2）。
- **排查**：① shell 环境变量无 `DEEPSEEK_API_KEY`（无污染）；② 加载的是 `../Project-Langchain/.env`；③ 用该 .env 的 key 直连 DeepSeek → 同样 401。→ **key 本身失效**（可能过期/轮换/欠费），非代码问题。
- **影响**：Wave4 的「真实 DeepSeek 生成」环节**未完成验证**；但检索链路在服务端日志中显示正常（请求走到 `generator.generate` 才 401，说明检索成功返回候选）。HTTP 层由 TestClient 假件覆盖、检索质量由评估报告覆盖。
- **处置**：待用户更新 key 后，重跑 `scripts/ask.py "问题"` 补验证。不假装通过。

### F3-补（2026-09-13）：key 更新后复验通过
- 用户提供新 `DEEPSEEK_API_KEY`（尾号 087b）。
- **方式**：`write_file(.env)` 被运行时敏感文件策略拦截 → 改用 **shell 环境变量注入**（`env DEEPSEEK_API_KEY=... <python> -m uvicorn ...`）；`generator._load_env()` 检测到本项目无 `.env` 时回落 `os.getenv`，且 `load_dotenv` 默认不覆盖已存在的环境变量，故注入生效。key **未落盘、未提交**。
- **最小探针**：agent_env python 直连 `deepseek-chat` → 返回「有效」，exit 0。
- **端到端**：`uvicorn src.api.main:create_app --factory --port 8000` + `scripts/ask.py` 三问（混合检索 / 文档切分策略 / MCP 原语）→ 三次均 **exit 0 / HTTP 200 / 真实 DeepSeek 生成**。
- **结论**：F3 的「真实 DeepSeek 生成环节未完成验证」→ **已验证**；检索 + 生成全链路通。
- **遗留**：本次 key 未落盘（安全策略所限），下次运行需自行在 `AI-Application-Engineering\.env` 配置 `DEEPSEEK_API_KEY`（该文件已 gitignore）或用环境变量注入。

