# 代码精读 12：app.py（5.1 Streamlit Web UI）

> 架构原则：**UI 是薄壳**——逻辑全部复用 scripts/ 零件，UI 只干上传/触发/展示/下载。
> 验证：AppTest 冒烟（0 异常、组件齐全、按钮未上传时 disabled）+ 真实启动 HTTP 200。

## A. Streamlit 心智模型（先懂这个再看代码）

用户每次交互（点按钮/上传/勾选）→ **整个脚本从头重跑**。两个必学机制：

| 机制 | 防的问题 | 类比 |
|------|---------|------|
| `st.session_state` | 重跑变量清零；AI 调用贵，结果必须存住 | 跨重跑保险箱 |
| `st.cache_resource` | 链/向量库重复构建（ONNX 加载 1-2s） | 只建一次的昂贵资产 |

生成一次 → 存 session_state → 之后重跑直接读：切标签/勾选框不丢结果、不重复花钱调 API。

## B. 薄壳组装

`sys.path.insert(0, scripts 目录)` + 三个 import（clean_chain / rag_chain / render_markdown）——**UI 零业务逻辑**。`decode_doc` 重写编码自适应（上传拿到的是字节不是路径）。

## C. UI 组件区（每行 = 浏览器一个元素）

set_page_config（标签页标题）/ title / file_uploader / checkbox（RAG 开关）/ button（`disabled=uploaded is None` 常驻置灰）。

## D. 生成与展示区

- 按勾选选链（rag/plain）→ spinner 转圈 → invoke → 存 session_state
- 展示：tabs 四标签（字段表 dataframe / 约束 / 评审 warning / 原始 JSON）+ 双下载按钮
- 第 74 行存入 + 第 78 行读取的配合 = "生成一次，反复展示"

## E. AppTest 验证

`AppTest.from_file("app.py").run()` 无浏览器冒烟：测"能加载、组件在、状态对"——重逻辑在 scripts/ 各自有执行示例。

## 自测

1. 重跑模型为什么需要 session_state？
2. app.py 里有几行业务逻辑？
3. 生成结果存在哪？

---

# 代码精读 13：phase5_2_robust.py（管线护甲）

> 全是防御，没有新功能。执行示例：模拟 API 不可达 26.3s（重试穷尽后快速失败）+ 正常路径 10.9s 成功（日志全程）。

## 四块

### A. 日志设置

- `RotatingFileHandler(maxBytes=1MB, backupCount=3)`：日志自动滚动，防撑爆磁盘
- 双 handler（文件 + 控制台）：文件事后排查，控制台当场看
- 时间戳格式：排查第一问是"什么时候发生的"

### B. build_robust_chain

- `llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)`：**挂 llm 不挂链**（只重试真模型调用）；指数退避 + 抖动防惊群
- 零件复用：Prompt 全来自 3.2，只换 llm 重新组装——加防御不动业务

### C. generate 三个日志节点

开始（谁、多大）→ 成功（产出、耗时）→ 失败（带异常）。排查一条龙。

### D. simulate_failure + 双层重试发现

日志出现 6 行 Retrying 而非 3 行：**OpenAI SDK 层（ChatOpenAI 内置 max_retries）+ LangChain 层（with_retry）叠加**——生产调参两层都要知道。重试穷尽 → 快速失败 + 友好提示 + exit(1)。

## 自测

1. with_retry 为什么挂 llm 不挂整条链？
2. 日志为什么用 RotatingFileHandler？
3. 为什么 Retrying 是 6 行不是 3 行？

---

*核心脚本精读全部完结（1.4 → 5.2 共 13 份）。extras（langgraph/demo 系列）可选追加。*