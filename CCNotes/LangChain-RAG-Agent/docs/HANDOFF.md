# HANDOFF — 交接文档

> **写给一个完全没有上下文的新会话。** 读完这份文档你应该能立刻接手继续。
> 更新日期：2026-08-30

---

## 一、我们在做什么

**目标**：帮用户（应用软件工程师，C++/Python/Java 背景，**LLM 开发零基础新手**）搭建 LLM 自动化工作流：

> 同事的需求文档（Markdown/TXT）→ 大模型分析 → 自动输出协议规范（字段表 + 约束规则 + 评审，JSON 给程序、Markdown 给同事）

**技术路线**：LangChain + Python + Prompt Engineering，DeepSeek API（OpenAI 兼容接口）。

**会话形式已两阶段演进**：
- 早期：用户逐行精读代码（"三问法"——干什么/吃什么吐什么/为什么这么写），每次讲解带实跑示例
- 现在：用户提产品级需求（"帮我装 LangSmith Studio"、"公司助手都有聊天窗口，咱们怎么做"），走完整工程流程：**头脑风暴 → 设计规格 → 实施计划 → 子代理逐任务执行 + 逐任务审查 → 终审 → 系统化调试**。用户是产品形态与关键决策的拍板人

---

## 二、已经完成了什么

### 功能层面：5 个 Phase + 3 个专题扩展

| Phase | 内容 | 状态 |
|-------|------|------|
| 1 | Prompt 基本功（四要素/Few-shot/结构化输出/纯 SDK 实操） | ✅ |
| 2 | LangChain 核心（三大核心/LCEL/Parallel/Parser） | ✅ |
| 3 | 协议生成工作流（读文件→四步链→三种调用→验收入口） | ✅ |
| 4 | 增强（RAG 向量检索 / Function Calling / 人在回路） | ✅ |
| 5 | 部署（**聊天窗口协议助手**：create_react_agent + 两工具 + token 打字机 / 重试+日志） | ✅（5.3 验收除外，见"卡在哪"） |
| 专题 | **LangSmith Studio**：studio_env（3.11）+ langgraph.json + studio_graphs.py + studio.bat，pipeline/agent 两图已接入，key 已配置验证通过 | ✅ |
| 专题 | **LangChain API 参考手册**：lessons/langchain_api_reference.md，9 章 26 词条七段式，全部示例输出来自实跑日志；头部含官方文档与中文资源链接（链接已验证可达） | ✅ |
| 专题 | **对话式 Agent**：概念（extra_chat_agent.md）+ 聊天助手构建全解（extra_chat_assistant_build.md），含 4 份真实对话实录 + 对照实验证据 | ✅ |

### 聊天助手（最新交付物）结构

- `scripts/chat_agent.py`：大脑——`create_react_agent` + `generate_protocol`（包 RAG 链，只回摘要）+ `validate_field_type`（复用 4.2）+ `stream_turn` 打字机（🔧 点菜标记按 id 去重）+ **文档已加载信号**（临时 SystemMessage，不进历史）
- `app.py`：聊天窗口薄壳（st.chat_input/chat_message/write_stream + 侧栏下载）
- `scripts/demo_chat_cli.py`：无 UI 版（交互 + 非交互模式）；`demo_app_test.py`：零成本 AppTest 冒烟（CHAT_FAKE_AGENT=1）
- 实录×4：主实录（上传生成+校验追问）、no_signal（无信号模型反问）、paste（贴需求生成+贴字段表校验，注入错误被揪出）、multi（4 轮多轮对话，模型纠正用户说错的字段名）；对照实验：demo_reconstruction_control.py（证明"模型长答复=先验重构"）

### 教学层面：文档体系齐全

- 18 份代码逐行精读（code_walkthrough_phase1~5）+ 全部脚本速查（scripts_overview）+ 零基础总纲（00_beginner_guide）
- 专题：LCEL / LangChain vs LangGraph / RAG / 工具调用 / 人工审核 / LangSmith Studio / 对话式 Agent / 聊天助手构建
- **API 手册**（查词条入口，Ctrl+F 直达）
- 用户自己设计出"并行分支 + 合并汇总"模式（demo_parallel_merge.py）

### 工程层面

- 目录：docs/（规划+设计规格+实施计划）+ lessons/（知识文档）+ scripts/ + inputs/ + outputs/
- 输出路径一律 `__file__` 基准；API Key 一律环境变量；`.env`/`models/`/`rag_db/` gitignore
- 环境：agent_env（langchain 1.x 全家桶）；studio_env（3.11，仅 Studio）；DeepSeek API；本地 BGE ONNX
- 全部直接提交 main（用户明确约定不分分支），commit 带 Co-Authored-By

---

## 三、当前卡在哪

**没有卡点。** 未完成事项：

1. **5.3 整体验收**（Phase 5 最后一项）：需要**用户提供一份真实的同事需求文档**，跑 `generate_protocol.py` 全流程。依赖用户出素材。顺带兑现坑 #2：教学假 Few-shot/模板换成真实协议。
2. **用户手动跑一次 `streamlit run app.py`**：聊天助手目前被 AppTest + CLI 实录覆盖，真浏览器体验这环只有用户自己能闭环（我们没法点浏览器）。

---

## 四、下一步计划（接手后立刻做）

1. 读 `docs/task_plan.md`、`docs/progress.md`（含完整错误日志）、`lessons/README.md`（文档地图）
2. **首选**：向用户要 5.3 的真实需求文档 → 跑全流程 → 对比教学假例差距 → 必要时回补 Few-shot/`inputs/templates/`；顺带请用户在浏览器里跑一次 `streamlit run app.py`
3. 用户可能选的深挖方向（都问过或提过）：
   - 聊天助手增强：会话历史持久化（关页面不丢）/ 多会话 / create_react_agent 迁移到 `langchain.agents.create_agent`（V2 前换导入，坑 #19）
   - LangGraph interrupt（人在回路暂停）
   - Dify / FastGPT 对比（extra_chat_agent.md 提过）
   - 复习文档提问 / 继续读 API 手册
4. 教学纪律（用户已立下的规矩，一条都别破）：
   - **每次讲解必须带实际运行的执行示例**（零成本 demo 优先，用户最喜欢）
   - **一次只问一个问题**
   - **知识点必须落盘 lessons/ 文档**（零基础可读：做什么/为什么/不做会怎样），对话只是演示
   - 代码讲解用"三问法"：干什么 / 吃什么吐什么 / 为什么这么写
5. 复杂任务的工程流程（本项目已固化的惯例）：头脑风暴 → 规格（docs/superpowers/specs/）→ 实施计划（docs/superpowers/plans/）→ 子代理逐任务执行 + 逐任务审查 + 终审。**实录/证据必须来自实跑且可复现**（坑 #18/#24）

---

## 五、踩过的坑 & 绝对不要再踩

| # | 坑 | 教训 |
|---|-----|------|
| 1 | 一次问多个问题（1.3 结束时犯过） | 一次只问一个，用户答了再问下一个 |
| 2 | Few-shot 用教学假例（GPS 心跳等） | 教学可以假，最终模板/素材库必须换用户真实协议 |
| 3 | 用户说"暂时拿不出"还反复纠缠 | 果断跳过标记待办 |
| 4 | 起步阶段推 Tool Calling | 按阶段来；现在已到 4.2+ 可以用了 |
| 5 | Windows 控制台 GBK 吃不下 emoji | 跑脚本一律 `PYTHONIOENCODING=utf-8` 前缀 |
| 6 | 用错 Python（base 环境没装包） | 一律 `E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe` |
| 7 | 教完不更新 task_plan/progress | 每完成一个子任务立刻同步记录 |
| 8 | 知识点只放对话不落盘 | 必须写 lessons/，且零基础可读 |
| 9 | pip 直连 PyPI 失败 | 加清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 10 | chromadb 内置 ONNX 模型 S3 下载超时（URL 写死） | 用 `models/bge-small-zh/` 本地模型 + 自定义 EmbeddingFunction |
| 11 | MiniLM（英文）中文检索错乱 | 用 BGE 中文模型 + CLS 池化 + `hnsw:space=cosine`；**换 embedding 模型必须删 rag_db 重建** |
| 12 | 相对路径坑：从 scripts/ 目录跑脚本 Errno 2 | 输出路径一律 `Path(__file__).resolve().parent.parent / "outputs"` |
| 13 | 变量名记混（phase2_1 的 `chain` ≠ phase2_2 的 `full_chain`）；RunnableParallel 分支表在 `.steps__`（双下划线） | 演示/引用前先验证，报错信息里的 "Did you mean" 就是答案 |
| 14 | 讲 stream 说"更快" | 准确说法：总耗时一样，差别是**首字延迟**（用户追问过"没感觉"） |
| 15 | langchain_core 1.x 细节：StrOutputParser 返回 `TextAccessor`（str 子类，用 isinstance 判断）；`tool.invoke()` 返回 str 用 `str()` 包 | 版本差异属正常，报错照实修 |
| 16 | `langgraph dev` 要求 Python 3.11+，agent_env 是 3.10 装不上 | Studio 用独立 conda `studio_env`（3.11 + langgraph-cli[inmem] + langchain 系 + colorama），不动主环境 |
| 17 | 中文 Windows 跑 langgraph dev 连炸三连：dotenv 按 GBK 读 .env / structlog 缺 colorama / langgraph-api 读包内文件按 GBK | `.env` 纯 ASCII；`pip install colorama`；启动命令加 `PYTHONUTF8=1` |
| 18 | **模型长答复能"重构"出它没看过的内容**（实录像伪造/泄露）：只有 172 字摘要，模型却能答出 -40~85℃、0.1℃ 等"文档细节"——凭领域先验重构，教学文档又是教科书标准写法，先验常命中同样数值；对照组（进程从未出现文档）也能重构出同样数值，还会把 60 秒说成 30 秒 | **模型流利 ≠ 模型看到过**；判断它是否真看过，看输入日志/对照实验，别看答得像不像；事实必须来自工具/检索；证据脚本 `scripts/demo_reconstruction_control.py` 可复现 |
| 19 | `create_react_agent` 在 langgraph 1.2.9 有弃用警告（`LangGraphDeprecatedSinceV10`） | 现在能用；V2 前迁移到 `langchain.agents.create_agent` |
| 20 | agent 不知道代码里的状态：文档明明已加载，模型却反问"有没有文档"不点菜 | 要让模型知道，**写进消息里**（临时 SystemMessage 前置，不进历史），见 chat_agent.stream_turn |
| 21 | 重写 .gitignore 时丢了 `__pycache__/` `*.pyc`，`git add -A` 把 pyc 和 `.langgraph_api/` 运行时文件塞进提交 | 改 gitignore 后先 `git status` 核对；运行时目录（.langgraph_api/）也要 ignore；误提交用 `git rm -r --cached` + amend 修 |
| 22 | AppTest 冷启动 ~5.2s 超过默认 3s 超时；file_uploader set_value 不接受文件对象（streamlit 1.62） | `AppTest(..., default_timeout=30)`；set_value 用 `(name, bytes, mime)` 元组 |
| 23 | 给用户的命令用了 Git Bash 语法（`VAR=值 cmd`），用户在 cmd 里跑直接报"不是内部或外部命令" | 给用户的启动方式一律打包成 .bat（如 studio.bat），抹平 shell 差异 |
| 24 | 文档引用实录的措辞：写"已裁掉"但日志原样保留；实录重跑后仍写"未修改、未重跑" | 日志原样保留、引用处写"**引用时已裁掉**"；重跑后的实录写"**单次实跑、未挑选**"；未复现的旧说法必须删干净（终审抓过两次） |

---

## 六、关键文件索引

```
D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent\
├── README.md            # 项目说明、目录结构、快速开始
├── app.py               # 聊天窗口协议助手（streamlit run app.py）
├── studio.bat           # LangSmith Studio 一键启动（cmd 双击/输 studio）
├── langgraph.json       # Studio 图入口（pipeline/agent 两图 → studio_graphs.py）
├── .env                 # Studio 环境变量（gitignore，纯 ASCII；LANGSMITH_API_KEY 已配置验证过）
├── requirements.txt     # 依赖清单（安装注释里有镜像命令）
├── .gitignore           # models/、rag_db/、__pycache__/、.env、.langgraph_api/ 不入库
├── docs/                # task_plan / progress（进度+错误日志）/ findings / HANDOFF（本文）/ superpowers（specs 规格 + plans 计划）
├── lessons/             # 00 总纲 / code_walkthrough_×5 / scripts_overview / extra_× 专题（含聊天助手构建全解+对话例子速查）/ API 手册
├── scripts/             # 23 份：核心 13 + demo 系列 + chat_agent / demo_chat_cli / demo_app_test / demo_chat_loop / demo_reconstruction_control / studio_graphs（各自开头 docstring 就是说明书）
├── inputs/              # sample_requirement×2（含 GBK 副本）/ templates/（4 份 RAG 模板素材）
├── outputs/             # 全部产物 + 实录日志（chat_demo_transcript*.log ×4 + chat_reconstruction_control.log）
├── models/              # 本地 BGE ONNX（gitignore）
└── rag_db/              # 向量库（gitignore；scripts/phase4_1_rag.py build 重建）
```

---

## 七、用户画像速查

- **身份**：应用软件工程师（C++/Python/Java），做协议制定工作
- **LLM 水平**：零基础起步，但学得很快——从"完全不懂"到能独立设计并行合并工作流（Map-Reduce 简化版）；现在能提产品级需求（聊天助手/LangSmith Studio）
- **学习风格**：必须动手（要执行示例、要自己跑命令）；追问精准（常指出讲解不准确处）；实用主义，不纠结术语；喜欢"和公司内部工具对齐"的产品化视角
- **沟通偏好**：话不多（"继续"/"合理"），但会主动打断纠正教学节奏
- **已立规矩**：讲解带执行示例、一次一问、知识点落盘、文档零基础可读

---

> **给新会话的第一句话建议**：
> "你好！我读了交接文档：项目是 LLM 协议自动生成工作流，5 个 Phase + 3 个专题（聊天助手 / LangSmith Studio / API 手册）全部完成，18 份代码已精读落盘。当前只剩两件小事：5.3 验收（需要你的一份真实同事需求文档跑全流程）和你亲自在浏览器里跑一次 `streamlit run app.py` 聊天助手。手头有真实需求文档吗？"
