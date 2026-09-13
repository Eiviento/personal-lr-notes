# Lesson 04 · 检索评估与服务化：让「好不好」变成数字，让 RAG 变成服务

> 阶段 1 / Wave 4。代码：`src/evaluation/evaluate.py`、`src/api/main.py`、`src/rag/generator.py`｜测试：`tests/test_evaluator.py`、`tests/test_api.py`｜脚本：`scripts/run_eval.py`、`scripts/ask.py`

## 一、为什么必须评估：调优不能靠感觉

前三个 Wave 做了切分/向量/混合/精排——但「哪个策略更好」不能凭嘴说。评估把「感觉准」变成**可计算的三指标**：

| 指标 | 问的问题 | 怎么算 |
|------|---------|--------|
| **hit_rate** | Top-K 里有没有命中相关文档？ | 有命中的问题数 / 总问题数 |
| **recall@k** | 相关文档被找全了吗？（一条问题可有多篇相关文档） | Top-K 覆盖的相关文档比例，取平均 |
| **MRR** | 正确的排得靠前吗？ | 第一个相关文档排名的倒数（第 1 名=1，第 2 名=0.5…），取平均 |

指标全用**可编程判据**（子串/集合运算），不靠第二个 LLM 评判——透明、可复现、零成本。

## 二、实跑评估报告（621 块语料 · 20 题 · Top-5，单次实跑、未挑选）

```
策略            hit_rate    recall       MRR
------------------------------------------
纯向量               0.90      0.88      0.82
混合RRF             1.00      1.00      0.83        ← 最优
混合+rerank         0.95      0.95      0.64        ← 反而更差
```

**三个结论（重要）**：
1. **混合检索确实赢**：纯向量 0.90 → 混合 1.00（20 题全命中）。呼应 Wave3 的观察——BM25 补上了向量对术语/编号的短板。
2. **降级 rerank 是负优化**：加了 coverage 重排后，hit/recall 掉到 0.95，**MRR 从 0.83 暴跌到 0.64**——重排打乱了 RRF 已经不错的顺序。**实证：没有真 cross-encoder 模型时，别加"假精排"**。
3. 这组数字本身就是一份**可对比基线**：以后换切分策略/ embedding 模型/ RRF 参数，重跑 `run_eval.py` 就能知道变好还是变坏（这就是「单变量回归」的雏形）。

## 三、服务化：把 RAG 链路变成 HTTP 接口

`src/api/main.py` 三个接口：

| 接口 | 作用 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /qa` | `{question, k}` → `{answer, sources}` |
| `POST /ingest` | 重建索引 |

**关键设计——依赖注入**：`create_app(retriever, generator)` 允许把检索器/生成器换掉。
- 测试时注入**假件**（零 API、快）→ `tests/test_api.py` 用 TestClient 跑通路由/校验/序列化
- 生产时用 `--factory` 走 `_build_default()`（真 ONNX + DeepSeek）

启动：`uvicorn src.api.main:create_app --factory --port 8000`

## 四、真实端到端：从"未完成"到已复验

**测试项**：起 uvicorn + 真实 DeepSeek 问答。

**结果**：`/health` 返回 200 ✅；`/qa` 返回 **500**——根因是 `openai.AuthenticationError: 401 ... api key is invalid`。

**排查过程（供参考）**：
1. 服务端日志显示：请求走到了 `generator.generate`，是**LLM 调用那一步 401**——说明**检索链路正常**（检索成功返回了候选、拼好了 prompt），只是生成环节的 key 失效。
2. 独立验证：用 `Project-Langchain/.env` 的 key 直连 DeepSeek → 同样 401（key 尾号 a3b2）。
3. 结论：**key 本身失效**（可能过期/轮换），属环境问题，非代码问题。

**因此**：
- ✅ HTTP 层由 `tests/test_api.py`（假件）覆盖——26 passed
- ✅ 检索质量由 `run_eval.py` 真实分数覆盖
- ⚠️ **「真实 DeepSeek 生成答案」这一环未完成验证**——等 key 更新后，重跑 `scripts/ask.py "问题"` 即可补上

**纪律**：不假装通过。这一项明确标记为「未验证（key 失效）」，而不是"跑通了"。

### 更新（2026-09-13）：key 更新后已复验通过

用户提供新 key（尾号 087b）后重跑，本项**由「未验证」更新为「已验证」**：

- **方式**：新 key 经 **shell 环境变量注入**（未写入 `.env`——运行时敏感文件策略拦截了 `write_file(.env)`）；`Generator._load_env()` 在本项目无 `.env` 时回落 `os.getenv`，且 `load_dotenv` 默认不覆盖已有环境变量，故注入生效。
- **最小探针**：`deepseek-chat` 直连 → 返回「有效」，exit 0。
- **端到端**：`uvicorn src.api.main:create_app --factory --port 8000` + `scripts/ask.py` 三问（混合检索 / 文档切分策略 / MCP 原语），三次均 **exit 0 / HTTP 200 / 真实 DeepSeek 生成**。
- **观察**：三个问题都因语料库（`data\documents\`，姊妹项目笔记）未覆盖对应主题，模型如实答「资料中没有提到」并列出实际命中的来源——**这不是失败，而是 System Prompt 防幻觉规则按设计生效**（只据资料回答、资料不足如实说），同时证明生成环节真实读取了检索内容。

**遗留**：本次 key 未落盘（安全策略所限）；下次运行需自行在 `AI-Application-Engineering\.env` 配置 `DEEPSEEK_API_KEY`（已 gitignore）或用环境变量注入。

## 五、三问法精读指引

1. **`create_app(retriever, generator)` 为什么要能注入？**（答：测试用假件隔离 HTTP 层、零成本；生产用真件；同一份路由代码两种场景复用——这就是依赖注入对可测试性的价值）
2. **为什么 `run_eval` 的指标用集合运算而不是让 LLM 打分？**（答：透明、可复现、零成本、不引入第二个模型的随机性；LLM 评判会引入裁判自身的偏差）
3. **降级 rerank 的 MRR 为什么暴跌？**（答：coverage 只看「查询词是否出现」，不理解语义重排——它把 RRF 已排好的顺序打乱，把词面偶然匹配但语义不相关的块提前了）
