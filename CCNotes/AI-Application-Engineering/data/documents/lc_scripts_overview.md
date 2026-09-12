# 全部代码速查：调用流程 + 每份总结

> 每份代码一章：**调用流程**（数据怎么流）+ **一句话总结**（这份代码教会你什么）。
> 深挖细节看 `code_walkthrough_phase1~5.md` 精读系列；概念总览看 `00_beginner_guide.md`。

---

## 1. phase1_4_req_to_protocol.py（纯 SDK 版，地基）

**位置**：`scripts/phase1_4_req_to_protocol.py`

**调用流程**：
```
命令行 argv[1]（需求文本）
  → main()：参数不足 → 打印用法退出（sys.exit(1)）
  → analyze_requirement()
       ├─ OpenAI(api_key, base_url=DeepSeek) 创建客户端
       ├─ SYSTEM_PROMPT（四要素说明书）+ 需求 拼成 messages（system/user）
       ├─ client.chat.completions.create() 调 API（temperature=0.3, max_tokens=4096）
       └─ 拿到文字 → _parse_response() 四道保险（剥围栏 → loads → 截取{} → 带证据报错）
  → print_protocol_table() 打印字段表
  → json.dump 存 outputs/protocol_output.json（全程 try/except 兜底）
```

**总结**：整个项目的地基——不装任何框架，纯 openai SDK 调 DeepSeek。先手写一遍（手拼消息、四道保险、try 兜底），后面 LangChain 的每个盒子替代了什么就一目了然。

---

## 2. phase2_1_langchain_basics.py（LangChain 重写版）

**位置**：`scripts/phase2_1_langchain_basics.py`

**调用流程**：
```
命令行 argv[1]
  → 三盒子：PROTOCOL_PROMPT（模板，{requirement} 占位符）
             llm（ChatOpenAI 统一接口）
             parser（JsonOutputParser，= phase1_4 的四道保险）
  → chain = PROTOCOL_PROMPT | llm | parser      ← LCEL 管道声明
  → main: chain.invoke({"requirement": ...})    ← 一行 = 填模板+调API+解析
  → print_table() → 存 outputs/protocol_output_langchain.json
```

**总结**：同一功能用 LangChain 重写——代码变短不是删了功能，是把重复劳动搬进别人测好的盒子。学到的核心：**模板占位符、统一接口、管道声明**（组装前置，main 只剩按开关）。

---

## 3. phase2_2_lcel_pipeline.py（并行分叉）

**位置**：`scripts/phase2_2_lcel_pipeline.py`

**调用流程**：
```
命令行 argv[1]
  → base_chain = PROMPT | llm | parser         （2.1 的直线）
  → validation_chain = RunnableParallel(
        field_check  = RunnableLambda(validate_fields)    ← 普通函数+转接头
        timing_check = RunnableLambda(validate_timing)
        byte_count   = RunnableLambda(calculate_total_bytes)
        protocol     = RunnablePassthrough()               ← 透传原样
    )
  → full_chain = base_chain | validation_chain  （积木套积木）
  → invoke → 结果 = 4 键大字典
  → print_result 按分支名取键（result["field_check"]...）→ 存含校验结果的 json
```

**总结**：给直线管道装"分叉"。两个新零件：RunnableParallel（并行分支，分支名=输出键名）、RunnablePassthrough（透传）。重要模式：**业务逻辑写普通函数，组装时才装接口**。边界认知：校验只查形式（字段齐不齐），查不了内容（设计对不对）。

---

## 4. phase2_3_output_parsers.py（Parser 三路对比）

**位置**：`scripts/phase2_3_output_parsers.py`

**调用流程**：
```
命令行 argv[1]（不传用默认需求）
  → 两份说明书：SUMMARY_PROMPT（要纯文本）/ JSON_PROMPT（要 JSON）
  → 同一需求走三条路：
       路1 (SUMMARY_PROMPT | llm)                     → AIMessage 对象（文字在 .content）
       路2 (SUMMARY_PROMPT | llm | StrOutputParser)   → TextAccessor（str 子类）
       路3 (JSON_PROMPT | llm | JsonOutputParser)     → dict
  → 存 outputs/protocol_summary.txt（路2）+ protocol_output_parser.json（路3）
```

**总结**：模型输出永远是文字，**Parser 决定它变成什么类型**。选型口诀：下游要文本用 Str，要结构化用 Json。彩蛋：TextAccessor 用 isinstance 判断。JsonOutputParser 的原理就是 phase1_4 手写的容错。

---

## 5. phase3_1_doc_input.py（喂文件版）

**位置**：`scripts/phase3_1_doc_input.py`

**调用流程**：
```
命令行 argv[1]（文件路径）
  → read_doc()：utf-8-sig → utf-8 → gb18030 顺序尝试解码（常用优先、超集兜底）
  → 大小检查：字符数 ≈ token 数；超 30000 截断 + 警告（权宜之计，Phase 4 RAG 治本）
  → PROMPT | llm | parser 全文直塞（Prompt 加一行"忽略与协议无关的内容"）
  → print_table → 存 outputs/<输入名>_protocol.json（输出名跟输入走）
```

**总结**：从"一句话"升级到"喂文件"。三问题三对策：编码（顺序尝试解码）、大小（估算+截断警告）、噪声（全文直塞，提取是 LLM 强项，别写解析规则）。

---

## 6. phase3_2_prompt_chain.py（四步链，项目心脏）

**位置**：`scripts/phase3_2_prompt_chain.py`

**调用流程**：
```
命令行 argv[1] → read_doc
  → full_chain =（物流标签：挂键名 = 占位符名 = 下游取用名）
        assign(key_points = ①ANALYZE_PROMPT | llm | StrOutputParser | tap)   ← 需求分析
      | assign(fields     = ②FIELDS_PROMPT | llm | JsonOutputParser | tap)   ← 字段定义
      | assign(checks     = ③RULES_PROMPT | llm | JsonOutputParser | tap)    ← 约束规则（评审视角）
      | RunnableLambda(merge_final)                                          ← ④纯 Python 合并
  → invoke → dict 逐步长胖：requirement → +key_points → +fields → +checks → 最终协议
  → print_result（协议 + 约束 + 评审发现）→ 存 <输入名>_protocol_full.json
```

**总结**：把一段式拆成四步——每步职责单一、中间产物可见（tap 观察者）、可单步调。核心原则：**LLM 做推理，Python 做拼装**（④合并是机械活不用 LLM）。③评审视角能发现设计者视角漏掉的开放问题。

---

## 7. phase3_3_batch_stream.py（三种调用方式）

**位置**：`scripts/phase3_3_batch_stream.py`

**调用流程**：
```
子命令 batch / stream（sys.argv[1]）
  → clean_chain：3.2 的零件去掉 tap 重装（调试版 → 生产版）
  → batch：clean_chain.batch([{requirement: 文档1}, {requirement: 文档2}...])
           列表进列表出，内部并发 → 逐份存 outputs/batch_<输入名>_protocol.json
  → stream：analyze_chain.stream({...}) 逐块打印（打字机）
            （用 analyze_chain 而非 full_chain——RunnableLambda 是流式边界）
```

**总结**：同一条链三种用法：invoke 单个、batch 批量并发（处理同事文档的标准姿势）、stream 逐块（UI 打字机）。核心认知：**组装一次，三种用法全有**。stream 不省时间，省的是首字延迟带来的焦虑。

---

## 8. generate_protocol.py（3.4 验收入口，Phase 3 收官）

**位置**：`scripts/generate_protocol.py`

**调用流程**：
```
命令行 1 个或多个文件路径
  → read_doc × N
  → 1 份走 chain.invoke / 多份走 chain.batch（自动分流）
  → render_markdown()：dict → Markdown 文本（纯 Python：标题/字段表/约束/评审/页脚）
  → 每份输入两个产出：
       outputs/<名称>_protocol.json（机器用）
       outputs/<名称>_protocol.md （同事看）
```

**总结**：最终交付物——**文件进 → 协议规范出**。新原则：JSON 是数据（LLM 出），Markdown 是呈现（Python 出）——确定性工作交给代码，文档长什么样不该有 AI 随机性。

---

## 9. phase4_1_rag.py（RAG：历史模板语义检索）

**位置**：`scripts/phase4_1_rag.py`

**调用流程**：
```
子命令 build / query / run
  → 本地 BGE ONNX 模型（WordPiece 分词 → ONNX 推理 → CLS 池化 → 归一化）
  → build：inputs/templates/*.md → 向量化 → upsert 入库（ids=文件名，幂等）
  → query：需求 → 向量 → 查 top-k 最相似模板（cosine 距离越小越近）
  → run：rag_chain =
        assign(retrieved = RunnableLambda(检索))          ← 3.4 链开头加一步
      | assign(key_points = ①同 3.4)
      | assign(fields     = ②RAG 版（吃 {retrieved} 参考历史模板）)
      | assign(checks     = ③同 3.4)
      | RunnableLambda(merge_final)                       ← ④同 3.4
    → 与无 RAG 的 clean_chain 并排对比 → 存 outputs/rag_<名称>_protocol.json
```

**总结**：历史协议资产用起来——新协议自动继承公司模板命名风格（实测 meter_id/total_flow/crc16 逐字一致）。踩坑三连：pip 镜像、chroma S3 下载失败（自写本地 embedding）、MiniLM 中文失效（换 BGE）。教训：**embedding 模型必须匹配语言**。

---

## 10. phase4_2_tool_calling.py（Function Calling）

**位置**：`scripts/phase4_2_tool_calling.py`

**调用流程**：
```
命令行 argv[1]（协议 JSON 路径）
  → 演示注入一处字段错误
  → @tool validate_field_type（类型注解→JSON Schema，docstring→使用时机）+ FIXED_SIZE 死规则表
  → llm.bind_tools([validate_field_type]) 把说明书发给模型
  → run_tool_loop：
        invoke → while response.tool_calls（模型还在点菜就继续上菜，上限 5 轮）
          → FUNC_MAP[name].invoke(args) 代码执行（执行权永远在代码手里）
          → ToolMessage(带回执编号) 回传 → 模型继续
  → 模型汇总校验报告 → 存 outputs/<名称>_validation.txt
```

**总结**：模型"点菜"，代码"上菜"——死规则交给代码算（永不出错），判断与汇总交给模型。安全边界：模型只能请求调用，执行权在代码。实测：模型自主发起 7 次校验，揪出注入的错误并输出修正报告。

---

## 11. phase4_3_human_review.py（人在回路，Phase 4 收官）

**位置**：`scripts/phase4_3_human_review.py`

**调用流程**：
```
命令行 argv[1]（草稿 JSON）
  → 演示注入一处错误
  → 机审两层：code_check（FIXED_SIZE 死规则，精确）
              + review_chain（LLM 评审，开放问题洞察）——互补不替代
  → human_review：逐条交互 [1]自动修正（仅确定性 fix）/ [2]忽略 / [3]记录待办
                  （EOF 容错 → 管道可喂答案）
  → 确认（n 取消，草稿不动）→ apply_fixes
  → 终稿三件套：outputs/<名称>_final.json / _final.md（带审核记录+已审核页脚）
               / _review_log.json（审核日志）
```

**总结**：LLM 产出不能直接发布，最后一关必须是人。三个设计：草稿终稿分离（可回退）、自动修正只给确定性 fix、全程留痕（每项决定可追溯）。

---

## 12. app.py（5.1 Streamlit Web UI）

**位置**：`app.py`（根目录）

**调用流程**：
```
浏览器 → Streamlit（用户每次交互 = 整个脚本重跑）
  → get_chains()（@st.cache_resource：链只建一次，重跑复用）
  → 上传文件 → decode_doc（编码自适应，字节版）
  → 勾选 RAG → 选链（rag_chain / clean_chain）
  → 点"生成协议"（没文件时 disabled）→ spinner 转圈 → chain.invoke
  → 结果存 st.session_state（重跑不丢、不重复花钱调 API）
  → 四标签页展示（字段表 dataframe / 约束 / 评审 / 原始 JSON）+ 双下载按钮
```

**总结**：UI 是薄壳——业务逻辑零新增，全部复用 scripts/ 零件。两个必学机制：session_state（结果存住）、cache_resource（昂贵资源不重建）。

---

## 13. phase5_2_robust.py（管线护甲）

**位置**：`scripts/phase5_2_robust.py`

**调用流程**：
```
命令行 argv[1]（或 --simulate-failure）
  → 日志初始化：RotatingFileHandler（1MB 滚动×3）+ 控制台双输出
  → build_robust_chain：3.2 的 Prompt 零件 + llm.with_retry(3 次，指数退避+抖动) 重装
  → generate：log 开始 → invoke（自动重试）→ log 成功/失败 → 存 json + md
  → simulate-failure：坏地址 llm → 重试穷尽 → 快速失败 + 友好提示 + exit(1)
```

**总结**：生产三条底线——重试（挂 llm 不挂链）、日志（时间戳/滚动/双输出）、友好报错。意外发现：OpenAI SDK 层与 LangChain 层**双层重试**（日志 6 行 Retrying），调参两层都要知道。

---

## 14. extra_langgraph_intro.py（LangGraph 实操）

**位置**：`scripts/extra_langgraph_intro.py`

**调用流程**：
```
命令行 argv[1]
  → Graph A（直线图）：StateGraph + 4 节点（analyze→fields→rules→merge）+ 5 条边
      = LCEL 管道的超集表达 → invoke → 协议
  → Graph B（agent 循环图）：model 节点 → 条件边（还有 tool_calls?）
      → tools 节点 → 回 model → 循环直到不再调用 → END
      = 4.2 手写 while 的声明式版本
  → 存 outputs/langgraph_demo_result.json
```

**总结**：LangChain 提供积木，LangGraph 提供编排（图 = 节点+边+状态）。图是管道的超集：能表达直线，还能表达循环/分支/暂停等人工。能直线就直线，有环有岔才上图。

---

## 15~18. 零成本演示系列（demo_*.py）

### demo_2_2_checks.py
**流程**：透视 full_chain.steps → 伪造 dict 喂 validation_chain（看并行分叉）→ 形式完美内容荒谬的协议（校验通过≠正确）。
**总结**：2.2 的三个概念实验打包——透视、并行、形式 vs 内容的边界。

### demo_parallel_merge.py（你设计的模式）
**流程**：RunnableParallel（数据字段视角 + 异常场景视角两分支并行读同一文档）→ 自动合并 {a,b} → FINAL_PROMPT 汇总 → 协议 JSON。
**总结**：并行分支 + 合并汇总（Map-Reduce 简化版）。实测比 3.2 串行链更强——两视角平级，异常信息从源头进入。

### demo_invoke_batch_stream.py
**流程**：sleep 积木演示——invoke 单个等待 / batch 3 个 1s 任务 1s 干完（并发）/ stream 每 yield 收一块。
**总结**：三种调用方式的零成本可视化：点一份外卖 / 同时点三份 / 炒一道上一道。

### demo_stream_feel.py
**流程**：同一慢输出走两条路——invoke 前 3 秒空白一次全出 vs stream 每 0.5s 收一块（带时间戳）。
**总结**：stream 不省时间，省的是焦虑——首字延迟从总时长变 1 秒。控制台没感觉是正常的（块大+网络快），真正有感在 Web UI。

---

## 附加资源（非脚本）

- `inputs/templates/*.md`：4 份历史协议模板（RAG 素材库，拿到真实协议后替换）
- `inputs/sample_requirement*.md`：模拟同事写法的需求文档（含噪声）
- `models/`、`rag_db/`：本地 BGE 模型与向量库（gitignore，重建命令见 README）
- `outputs/`：全部生成结果（草稿/终稿/评审/日志）
