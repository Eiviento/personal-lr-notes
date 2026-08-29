# LLM 协议自动生成工作流（学习项目）

用 LangChain + Python 搭建"同事需求文档 → 大模型分析 → 协议规范"的自动化管线。

## 当前进度

| Phase | 内容 | 状态 |
|-------|------|------|
| 1 | Prompt Engineering 基本功 | ✅ |
| 2 | LangChain 核心概念 | ✅ |
| 3 | 构建协议生成工作流 | 🔄 进行中（3.1/3.2 完成） |
| 4 | 增强与优化（RAG / Tool Calling / 人工审核） | ✅ |
| 5 | 部署上线（Streamlit UI） | 🔄 进行中（5.1 UI 完成） |

## 目录结构

```
├── docs/        # 规划文件：task_plan（计划）/ progress（进度）/ findings（决策）/ HANDOFF（交接）
├── lessons/     # 知识点讲解文档（学理论看这里）
├── scripts/     # 各阶段实操脚本
├── inputs/      # 示例需求文档（模拟同事写法）
└── outputs/     # 脚本生成的协议 JSON / 文本
```

## 快速开始

环境要求：
- Python：conda 环境 `agent_env`（已装 langchain / langchain-openai / openai）
- API Key：环境变量 `DEEPSEEK_API_KEY`（已配置）
- Windows 下跑脚本需加 `PYTHONIOENCODING=utf-8`（控制台 GBK 编码问题）

示例（在项目根目录执行）：

```bash
# 一段式：文档 → 字段表
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe \
  scripts/phase3_1_doc_input.py inputs/sample_requirement.md

# 四步链：文档 → 分析 → 字段 → 约束 → 完整协议
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe \
  scripts/phase3_2_prompt_chain.py inputs/sample_requirement.md
```

结果写入 `outputs/`。

## 文档导航

- 学知识点 → `lessons/`（每 Phase 一份，含知识点 + 原理 + 坑）
- 看计划/进度/决策 → `docs/`
- 交接给新会话 → `docs/HANDOFF.md`
