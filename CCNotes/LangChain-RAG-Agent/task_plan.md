# Task Plan: LLM 自动化协议生成工作流

## Goal
搭建一个基于 LangChain + Python 的自动化工作流，实现"输入需求文档 → 大模型分析 → 输出协议规范"的完整管线。

## Current Phase
Phase 2

## Phases

### Phase 1: Prompt Engineering 基本功
- [x] 1.1 理解 Prompt 的核心要素：角色、指令、上下文、输出格式
- [x] 1.2 掌握 Few-shot Prompting（给示例让模型模仿协议风格）
- [x] 1.3 掌握结构化输出控制：让 LLM 输出 JSON / 固定字段格式
- [x] 1.4 实操：纯 Python SDK 写一个"需求 → 协议字段表"的 Prompt 并调通
- **Status:** complete

### Phase 2: LangChain 核心概念
- [ ] 2.1 理解 LangChain 的三大核心：PromptTemplate、Model、Parser
- [ ] 2.2 学习 LCEL（LangChain Expression Language）管道写法
- [ ] 2.3 掌握 StrOutputParser / JsonOutputParser 的使用
- [ ] 2.4 实操：用 LangChain 重写第一阶段的功能，对比差异
- **Status:** in_progress

### Phase 3: 构建协议生成工作流
- [ ] 3.1 文档输入：解析 Markdown / TXT 需求文档，提取关键信息
- [ ] 3.2 设计协议生成的 Prompt 模板链（需求分析 → 字段定义 → 约束规则 → 最终协议）
- [ ] 3.3 学习 LangChain 的 Chain 串联：SequentialChain / RunnableSequence
- [ ] 3.4 实操：完整跑通"输入需求文档 → 输出协议规范"
- **Status:** pending

### Phase 4: 增强与优化
- [ ] 4.1 RAG 基础：用向量数据库（Chroma/FAISS）存历史协议模板，检索后注入 Prompt
- [ ] 4.2 学习 Function Calling / Tool Use，让模型能调用工具（如校验字段类型）
- [ ] 4.3 加入人工审核环节：输出草稿 → 人确认 → 生成最终版
- **Status:** pending

### Phase 5: 部署上线
- [ ] 5.1 用 Streamlit 搭一个简易 Web UI（上传文档 → 查看协议 → 下载）
- [ ] 5.2 加入错误处理、重试、日志
- [ ] 5.3 整体串联测试，用真实同事需求文档跑一遍
- **Status:** pending

## Key Questions
1. 选用哪个 LLM API？（Claude API vs OpenAI API vs 国产模型 API）
2. 协议输出格式是什么？（JSON Schema / YAML / 自定义模板 / Markdown 表格）
3. 是否有公司内部协议模板/规范需要遵守？
4. 部署环境：本地运行还是需要部署到服务器？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 学习路径：方案二（LangChain + Python）为主，融合方案三（Prompt Engineering） | 用户 Python 基础好，代码级控制灵活，不依赖第三方平台 |
| 学习深度：快速落地型（A） | 目标 1-2 周内产出可用工具 |
| 5 阶段学习计划 | 覆盖从 Prompt 基本功到部署上线的完整链路 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       |         |            |

## Notes
- 用户背景：C++ / Python / Java 应用软件工程师
- 有基本的 LLM API 调用经验
- 核心场景：同事需求文档 → 大模型分析 → 输出通信协议规范
- 用户做协议制定工作，需要将需求转化为协议定义
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions (attention manipulation)
- Log ALL errors - they help avoid repetition
- Never repeat a failed action - mutate your approach instead
