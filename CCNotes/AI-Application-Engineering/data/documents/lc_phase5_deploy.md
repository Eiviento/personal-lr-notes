# Phase 5：部署上线

> 对应文件：`app.py`（项目根目录，运行 `streamlit run app.py`）
> 目标：让同事不用命令行，上传需求文档就能用。

---

## 5.1 Streamlit Web UI

### 心智模型：脚本全量重跑

和普通 Web 框架不同，Streamlit 没有 HTML/JS，就一个 Python 脚本。**每次交互（点按钮/上传/勾选）整个脚本从头执行**。两个机制应对这个模型：

| 机制 | 解决的问题 | 用法 |
|------|-----------|------|
| `st.session_state` | 重跑后普通变量清零；**LLM 调用很贵，不能每次重跑重新生成** | 生成结果存 session_state，重跑直接读 |
| `st.cache_resource` | 链/向量库被重建（ONNX 模型加载 1-2 秒） | 缓存链和向量库，只建一次 |

### 架构原则：UI 是薄壳

逻辑零新增，全部复用：

```python
from phase3_3_batch_stream import clean_chain   # 无 RAG 链
from phase4_1_rag import rag_chain              # RAG 链
from generate_protocol import render_markdown   # Markdown 渲染
```

UI 只干四件事：**上传（编码自适应，同 3.1）→ 触发（spinner 提示）→ 展示（tabs 分栏）→ 下载（JSON/MD 双按钮）**。

### 实战要点

- 按钮用 `disabled=uploaded is None` 常驻禁用，比"没上传就不显示按钮"的 UX 好
- 验证方式：Streamlit 官方 `AppTest`（`from streamlit.testing.v1 import AppTest`）做无浏览器冒烟测试：0 异常 + 组件齐全
- 4.1 的 `retrieve` 加了 `functools.lru_cache` 缓存向量库会话——CLI 和 UI 都受益
- 运行：`streamlit run app.py`（已实测 HTTP 200）

## 5.2 错误处理 / 重试 / 日志

> 对应脚本：`scripts/phase5_2_robust.py`

### 三种失败，两种对策

| 失败类型 | 表现 | 对策 |
|---------|------|------|
| 超时 | 网络慢/模型卡 | 重试 ✅ |
| 限流 429 | 并发太高被拒 | 重试 + **指数退避** ✅ |
| 服务器 5xx | 服务端抖动 | 重试 ✅ |
| 4xx（认证/参数错） | 重试一万次也没用 | **快速失败** + 明确报错 |

### 两个关键设计

1. **指数退避 + 随机抖动**：重试间隔 1s/2s/4s 递增外加随机量——所有失败请求同一秒重试会形成"惊群"把服务再打挂一次
2. **重试挂在 llm 上，不挂整条链**：`llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)` 只重试真正的模型调用——读文件失败、JSON 解析失败重试没意义

### 实测发现的细节：两层重试

模拟 API 不可达的日志显示 6 行 "Retrying request"——**OpenAI SDK 层（ChatOpenAI 内置 max_retries）和 LangChain 的 with_retry 层都在重试**（SDK 在每次 with_retry 尝试内部又重试）。生产环境要意识到这两层，调参数时别只动一个。

### 日志三板斧

- `logging.basicConfig(handlers=[RotatingFileHandler, StreamHandler])`：文件（自动滚动防膨胀）+ 控制台双输出
- 记录关键节点：开始（文件名/字符数）→ 成败 → 耗时/字段数
- 错误用 `log.error` 带完整异常信息，排查时 `outputs/app.log` 一条龙

---

*5.3 真实文档验收——后续小节补充。*
