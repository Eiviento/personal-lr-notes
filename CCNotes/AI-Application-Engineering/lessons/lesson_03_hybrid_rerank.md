# Lesson 03 · 混合检索与精排：召回与排序是两件事

> 阶段 1 / Wave 3。代码：`src/rag/bm25.py`、`src/rag/retriever.py`、`src/rag/reranker.py`｜测试：`tests/test_bm25.py`、`tests/test_retriever.py`｜对比：`scripts/compare_retrieval.py`

## 一、为什么需要「混合」：向量和 BM25 是互补的两个瞎子

| | 强在 | 弱在 |
|---|------|------|
| 向量检索 | 语义相近（换词也能命中） | **专有名词/编号/精确术语**在语义空间不突出，易漏 |
| BM25 | 关键词精确命中（术语、函数名、订单号） | 换个说法就搜不到 |

一个用户在找 `create_agent`，向量可能给你一堆「讲 agent 是什么」的泛泛段落；BM25 则死死盯住 `create_agent` 这个词。**两者融合 = 混合检索**，是生产级 RAG 的标配。

## 二、融合为什么用 RRF 而不是「分数相加」

向量相似度 ∈ [0,1]，BM25 分数可达几十上百——**尺度不同，直接相加没意义**（BM25 会主导排序）。

**RRF（Reciprocal Rank Fusion）只看排名**：每个结果列表里，第 `rank` 名给该文档贡献 `1/(k + rank)`，多路结果求和。排名越靠前贡献越大，`.k`（默认 60）起平滑作用。这样向量榜和 BM25 榜对融合的贡献是公平的。

## 三、精排（rerank）：召回之后再筛一遍

**召回 ≠ 排序**。混合检索先「召回」一批候选（如 20 个），但它们的顺序未必准。精排模型（cross-encoder）把「查询 + 候选」拼在一起喂模型打分，比向量距离准得多——代价是慢，所以只对少量候选做。

**本项目的诚实降级**：真正的 cross-encoder（如 BGE-reranker）需要额外下载模型（国内可能受阻，本项目**未验证可获取性**）→ 采用降级实现：用「查询词在候选中的覆盖率」重排。下面的数据会显示**这个降级版并不总优于 RRF**——这正是"没有真精排模型就别吹精排"的实证。

## 四、实跑对比（621 块语料，单次实跑、未挑选）

```
[专有名词] create_agent 和 create_react_agent 有什么区别
    纯向量       pl_lesson_agent6_scale(0.683) | ...
    混合RRF     lc_extra_chat_assistan(0.031) | pl_lesson_agent6_scale(0.031) | ...
[专有名词] thread_id 是干什么用的
    纯向量       pl_lesson_agent3_memor(0.647) | ...
    混合RRF     pl_lesson_agent4_relia(0.032) | pl_lesson_agent7_webap(0.032) | ...
[语义] 怎么让 agent 在写操作前停下来等人工审批
    纯向量       pl_lesson_agent4_relia(0.661) | ...
    混合+rerank pl_lesson_agent4_relia(0.706) | ...
[语义] 怎么判断检索系统好不好
    纯向量       lc_code_walkthrough_ph(0.544) | ...        ← 泛化段落，没抓到 eval
    混合RRF     pl_lesson_agent5_eval.(0.032) | ...          ← 命中 agent5_eval（正确！）
    混合+rerank pl_lesson_agent1_white(0.700) | ...          ← 反而打乱
```

**怎么读（诚实分析）**：
1. **混合检索确实有效**：最后一例问「怎么判断检索系统好不好」，纯向量给的是泛化的 walkthrough 段落，而**混合 RRF 把 `lesson_agent5_eval`（讲评估的）提到第一**——这正是混合想解决的事。
2. **降级 rerank 不稳定**：最后一例里，覆盖率重排反而把正确的 eval 文档挤掉、换成了 agent1。**结论：没有真正的 cross-encoder 模型时，别迷信"加了 rerank 就更好"**——这也是一个要记住的工程判断。
3. RRF 分数（0.03 量级）比向量相似度（0.6 量级）小很多，属正常——RRF 是**排名分**，不是相似度，别跨档比绝对值。

## 五、TDD 过程与踩坑（真实记录）

- **踩坑（BM25 的一个反直觉行为）**：先用 `BM25Okapi`，测试挂了——两个小测试失败（一个 IndexError、一个排序错）。根因：**BM25Okapi 的 IDF 公式在小语料上会失真**——词恰好出现在一半文档时，IDF = log((N-n+0.5)/(n+0.5)) = log(1) = **0**，导致正确块得 0 分被过滤。改用 `BM25Plus`（IDF 恒非负）解决。
  - 教训：经典算法在小数据上有边界行为，**测试小语料反而更容易暴露它**。
- RRF 的 3 条测试（共识项优先 / 单路保序 / 分数正且降序）先红后绿。

## 六、三问法精读指引

1. **RRF 为什么能容忍两路分数尺度不同？**（答：它只用 rank 不看 score，`1/(k+rank)` 把任意尺度的分数都归一成"排名贡献"）
2. **为什么不干脆把向量和 BM25 分数加权相加？**（答：尺度不可比，权重极难调；RRF 免调参、对异构源更稳）
3. **`Reranker(mode="coverage")` 和真 cross-encoder 差在哪？**（答：coverage 只看词是否出现，不懂语义；cross-encoder 把 query+doc 一起过模型，理解语义相关度，但需模型且慢）
