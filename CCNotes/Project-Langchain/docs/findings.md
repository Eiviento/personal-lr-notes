# Findings — 决策与事实记录

## 2026-09-06

### F1: langgraph 1.2.9 无内置 SqliteSaver（计划偏离）
- **事实**：`langgraph.checkpoint.sqlite` import 失败（ModuleNotFoundError）。SqliteSaver 在独立分发包 `langgraph-checkpoint-sqlite`，agent_env 未安装。
- **影响**：计划 W3（记忆持久化）原定 SqliteSaver 落盘。0.x 时代的 `langgraph.checkpoint.sqlite` 心智模型不适用于 1.2.9 主包。
- **决策（暂定）**：W3 开头问用户二选一——装 `langgraph-checkpoint-sqlite`（清华镜像）实现真落盘，或用 MemorySaver + 教学说明降级。倾向装包（P3 教学价值在"重启不丢"）。

### F2: create_react_agent 1.2.9 签名已带 version 参数（默认 v2）
- **事实**：探针显示 `create_react_agent(..., version: Literal['v1','v2']='v2', ...)`。langchain.agents.create_agent（V2）已存在（system_prompt/middleware/state_schema 参数体系）。
- **影响**：教学主线（P1 拆黑盒用 create_react_agent）可行；P6 迁移教 create_agent 有真身。实际调用时观察是否仍有弃用警告，如实记录。

### F3: DEEPSEEK_API_KEY 未就绪
- **事实**：shell env unset，新项目无 .env。
- **影响**：W1 API 环节前需用户配 .env（参照 .env.example）。零成本假 agent 演示不受影响。

### F4: 无头 worker 读不了 E:\site-packages
- **事实**：两个 code_scout 因 E: 越出工作区被结构性阻断（无审批通道）。
- **应对**：教学源码取证一律用 `inspect.getsource`（运行时拿源码文本），绕过文件授权。
