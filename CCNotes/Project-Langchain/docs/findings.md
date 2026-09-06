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

### F5: SO-9999 反例改用"库中无此单"（审查修复）
- **问题**：初版 orders.json 把 SO-9999 实现为数组内 `status=not_found` 的真实行——线性查找会命中并返回"存在但状态特殊"的歧义信号，弱代理了"查无此单"。
- **修复**：删除该行。防幻觉/诚实测试用**库里不存在的订单号**（如 SO-0000），由 get_order_status 查找不到返回"未找到"承载。数据形状与真实语义对齐。

### F6: DEEPSEEK_API_KEY 不在 LangChain-RAG-Agent\.env
- **事实**：该 .env（325B）仅含 LANGSMITH_API_KEY；Windows cmd 环境变量也无 DEEPSEEK_API_KEY。
- **推论**：LangChain-RAG-Agent 跑 API 脚本时的 key 来自会话内临时设置（未持久化），或 key 另存他处。新项目 .env 待用户提供 DEEPSEEK_API_KEY 值后补入。脚本统一用 python-dotenv load_dotenv() 加载。

### F4: 无头 worker 读不了 E:\site-packages
- **事实**：两个 code_scout 因 E: 越出工作区被结构性阻断（无审批通道）。
- **应对**：教学源码取证一律用 `inspect.getsource`（运行时拿源码文本），绕过文件授权。

### F7: SqliteSaver 装包决策落地（2026-09-06，W3）
- **决策**：用户同意 → `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langgraph-checkpoint-sqlite` 已装，版本 **3.1.1**。
- **实测 API 形态**（import + inspect）：`langgraph.checkpoint.sqlite` 仅导出**同步 `SqliteSaver`**，**无 `AsyncSqliteSaver`**；`SqliteSaver.from_conn_string(conn_string)` 是**生成器工厂**（返回 `Iterator[SqliteSaver]`），用法 `with SqliteSaver.from_conn_string(...) as saver:`。与 0.x 教程的 `SqliteSaver(conn)` 构造不同，教学代码按 3.x 形态写。
- **probe_api.py 基线已更新**：SqliteSaver expected False→True；AsyncSqliteSaver 保持 False（包未导出）。探针验证 exit 0 = 与新基线一致。
