# Findings & Decisions

## Requirements
- 输入：同事的需求文档（Markdown / TXT 格式）
- 处理：大模型分析需求内容，拆解为协议要素
- 输出：结构化的协议规范（字段定义、类型、约束规则等）
- 用户背景：C++ / Python / Java 应用软件工程师，有基础 LLM API 调用经验
- 学习深度：快速落地型，1-2 周产出可用工具
- 技术路线：LangChain + Python 为主，融合 Prompt Engineering 基本功

## Research Findings
- LangChain 是当前最主流的 LLM 应用框架，Python 生态成熟
- LCEL（LangChain Expression Language）是 LangChain 推荐的现代写法，比旧式 Chain 更简洁
- Prompt Engineering 是所有 LLM 应用的基础，框架只是锦上添花
- Streamlit 适合快速搭建 ML/AI 工具的 Web UI，比 Gradio 更灵活
- Chroma 和 FAISS 是轻量级向量数据库，适合小规模 RAG 场景

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| LangChain + Python 作为主框架 | 用户 Python 基础好，生态成熟，灵活性高 |
| 先用纯 SDK 练 Prompt，再用 LangChain | 先理解本质再学框架，避免被抽象层迷惑 |
| 后续用 Streamlit 做 UI | 快速搭建，Python 原生，适合内部工具 |
| 暂不引入数据库，先从文件读写开始 | 控制复杂度，快速落地 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
- LangChain 官方文档: https://python.langchain.com/
- Claude API 文档: https://docs.anthropic.com/
- Streamlit 文档: https://docs.streamlit.io/
- Chroma 向量数据库: https://docs.trychroma.com/

## Visual/Browser Findings
-

---
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
