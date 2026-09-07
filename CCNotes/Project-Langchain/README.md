# Project-Langchain · Agent 深度研学（技术支持客服 Agent）

用 LangGraph + DeepSeek 从零搭一个**技术支持客服 Agent** 的深度学习项目。与 LangChain-RAG-Agent（协议生成工作流）是姊妹篇——那边学完了 LangChain 五阶段基础，这个项目专攻 **Agent 本身**：从拆开 `create_react_agent` 黑盒，到护栏、记忆、人工审批、评估、版本演进的完整 6 Phase。

> 学习方式：每个 Phase 一段代码 + 实跑证据 + 知识点落盘 `lessons\`（零基础可读）。讲解带执行示例、一次一问、证据来自实跑。

## 业务 Demo（通用场景，不挑业务）

一个**技术支持客服 Agent**：能多轮对话、查产品知识库、查订单状态、申请退款（需人工审批）。

| 工具 | 干什么 | 数据来源 |
|------|--------|---------|
| `search_knowledge` | 检索 FAQ 知识库（轻量关键词，无向量库） | `data\knowledge.txt` |
| `get_order_status` | 查订单状态 | `data\orders.json`（假订单库） |
| `request_refund` | 申请退款（**写操作 → 人工审批**） | — |
| `get_now_time` | 当前时间（P1/P2 教学用最小工具） | — |

## 当前进度

| Phase | 主题 | 状态 |
|-------|------|------|
| 0 | 项目骨架 + API 探针核验 | ✅ |
| 1 | 拆开黑盒：白盒 ReAct（手写 StateGraph 对照 create_react_agent） | ✅ |
| 2 | 阀门与护栏（recursion_limit / 重复熔断 / 异常回流） | ✅ |
| 3 | 记忆与状态（checkpointer 持久化 / 多会话 / token 治理） | ✅ |
| 4 | 可靠性与人在回路（interrupt 退款审批 / 防幻觉验证） | ✅ |
| 5 | 观察与评估（eval 集 / 单变量回归调优） | ✅ |
| 6 | 规模化与版本演进（create_agent V2 迁移 / subgraph） | ⬜ |

## 快速开始

环境：复用 conda `agent_env`（Python 3.10.19，已装 langchain-core 1.4.9 / langchain 1.3.14 / langgraph 1.2.9 / langgraph-prebuilt 1.1.0）。

```bash
# 1. 配置 API Key：把 .env.example 复制为 .env，填入 DEEPSEEK_API_KEY
# 2. 核验环境与教学基线一致（exit 0 = 就绪；失败会非零退出并列出差异）
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/probe_api.py
```

> 各 Phase 的可运行脚本（agent1_whitebox.py 起）随进度表就绪——当前可用脚本见 `scripts\` 目录。

## 目录结构

```
├── docs/        # HANDOFF / progress / findings / superpowers(计划与规格)
├── lessons/     # 每 Phase 一份知识点文档（零基础可读，含实跑证据）
├── scripts/     # agent1_whitebox → agent6_scale 逐步演进（每份 docstring 说明书）
├── data/        # knowledge.txt（FAQ）+ orders.json（假订单库）
├── outputs/     # 实跑日志与产物（gitignore，教学证据引用时标注"单次实跑未挑选"）
└── tests/       # 零成本冒烟（假 agent 模式，不真调 API）
```

## 教学约定

- 每 Phase：讲解 → 写代码实跑（输出留 `outputs\`）→ 三问法精读 → 落盘 `lessons\`
- 实跑证据纪律：声称跑通必须有 exit 0 + 日志；引用实录写"单次实跑、未挑选"
- 你（项目 owner）是节奏拍板人，每 Phase 可停靠可回看

## 姊妹项目导航

LangChain 基础（Prompt / LCEL / RAG / Tool Calling / 对话助手）在 `..\LangChain-RAG-Agent\`，那里的 lessons 是前置知识。
