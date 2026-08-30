# 设计规格：LangChain API 参考手册

> 日期：2026-08-30 · 状态：已获用户确认（方案 A：模块字典式）

## 一、目标

给用户一份 **LangChain API 使用手册（字典）**：查词条即用，不依赖"记得它在哪个阶段学过"。覆盖范围 = **本项目实际用过的全部 LangChain / LangGraph / chromadb API**（9 章共 26 个词条），每条带**可运行的执行示例 + 真实输出**（用户教学规矩）。

**读者**：用户本人（LLM 零基础起步的应用软件工程师），已学完全部 18 份代码精读。

**边界（明确不做）**：
- 不覆盖项目没用过的 LangChain API（TextLoader、其他 Parser、Memory 等）
- 不重写概念教学（概念讲深在现有 lessons/ 精读系列，手册里链接过去）
- 不更新 `scripts_overview.md`（它是"按脚本查"，本手册是"按 API 查"，互补）

## 二、交付物

### 2.1 `lessons/langchain_api_reference.md`（单文件手册）

- 开头：一句话定位 + 用法说明（Ctrl+F 查类名直达）+ **版本基线表**（实现时实跑取 conda agent_env 中 langchain_core / langchain_openai / langchain-core 相关包 / chromadb 实际版本；呼应坑 #15 版本差异属正常）
- 顶部锚点目录（9 章 + 全部词条）

**章节与词条**：

| 章 | 模块 | 词条 |
|----|------|------|
| 1 | 提示词 | `ChatPromptTemplate` |
| 2 | 模型 | `ChatOpenAI`（构造参数全表）、`.with_retry`、`.bind_tools`（bind_tools 详解放第 7 章，本章只放签名入口） |
| 3 | 管道 | `\|` 运算符、`RunnableLambda`、`RunnablePassthrough`、`RunnableParallel`、`assign` |
| 4 | 调用 | `.invoke`、`.batch`、`.stream`（三合一对比表 + 各自签名） |
| 5 | 解析 | `StrOutputParser`、`JsonOutputParser` |
| 6 | 消息 | `SystemMessage`、`HumanMessage`、`ToolMessage` |
| 7 | 工具 | `@tool`、`.bind_tools`、工具循环模式（模型点菜/代码上菜） |
| 8 | 编排 | `StateGraph`、`START`、`END` |
| 9 | 向量 | chromadb `EmbeddingFunction`、`Embeddings`、`Documents` |

**词条七段式模板**（每个词条固定顺序）：

1. **一句话是什么**
2. **签名**（精确 import 路径 + 构造/调用签名，从源码/实测确认）
3. **参数表**（参数 / 类型 / 默认值 / 干什么用；只列项目用到或常见的参数）
4. **最小示例**（可复制运行的代码块 + 真实输出；输出来自 demo 脚本实跑，贴原样）
5. **本项目在哪用到**（`scripts/xxx.py:行号`，实现时逐个核对存在）
6. **原理要点**（为什么这么设计、替代了手写版的什么；一句话带过，深挖链接现有精读文档）
7. **踩坑**（引用 HANDOFF 坑表对应条目：TextAccessor、`.steps__` 双下划线、双层重试等）

### 2.2 `scripts/demo_api_reference.py`（配套演示脚本）

分节函数（一节对应一章），跑一遍生成手册所需的全部真实输出。**成本原则：能零成本就零成本，必须真模型才真调**（用户最喜欢零成本 demo）：

| 节 | 内容 | 成本 |
|----|------|------|
| 1 prompts | `ChatPromptTemplate.from_messages` 三种角色 + `invoke` 看格式化结果 | 0（纯模板） |
| 2 models | `ChatOpenAI` 实例化（打印参数）、`.with_retry` 用坏地址演示重试日志（phase5_2 simulate-failure 同款） | 0（连不上不花钱） |
| 3 runnables | 假函数 → `RunnableLambda` / `Passthrough` / `Parallel`（sleep 积木可视化并行）/ `assign` 挂键 | 0 |
| 4 调用 | 真链走 DeepSeek：invoke 1 次 / batch 2 小输入 / stream 逐块打印 | 真调 ~3 次 |
| 5 parsers | 假 `AIMessage` → `StrOutputParser` / `JsonOutputParser`（含 TextAccessor isinstance 演示） | 0 |
| 6 messages | 三种 Message 对象构造 + 打印字段 | 0 |
| 7 tools | `@tool` 定义打印 schema；`bind_tools` + 工具循环真调（模型点菜一次） | 真调 ~1 次 |
| 8 langgraph | `StateGraph` 直线图 + 条件边循环，纯 Python 节点演示图结构；真调版引用 `extra_langgraph_intro.py` | 0 |
| 9 chroma | `EmbeddingFunction` 定义 + `PersistentClient` 临时 collection add/query（本地 BGE ONNX） | 0（本地推理） |

- 运行方式：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_api_reference.py`
- 脚本开头 docstring 写"这是 API 手册第 4 段的输出来源"，与 lessons 索引呼应

## 三、与现有文档的集成

- `lessons/README.md` 索引表新增一行：`langchain_api_reference.md` — **API 手册（查词条来这里）**，定位写清："API 怎么调用查这里；概念原理看 00 总纲 / extra 专题；逐行讲解看 code_walkthrough 系列"
- 手册内第 6/7 段链接到对应精读/专题文档（相对路径）
- 不改动：`code_walkthrough_*`、`scripts_overview.md`、`00_beginner_guide.md`

## 四、验证标准（完成定义）

1. `demo_api_reference.py` 实跑通过，输出真实（贴进手册的是实跑原样输出，不是手编的）
2. 手册每个词条七段齐全；每处 `scripts/xxx.py:行号` 引用经 grep/读文件核对真实存在
3. 版本基线表数字来自实跑 `import langchain_core ...` 查询结果
4. `lessons/README.md` 索引已更新
5. 手册内相对链接可点通（同仓相对路径）
6. 全部改动 git commit（直接提交 main，符合用户 git 工作流约定）
