# Lesson 02 · 向量检索：把文本变成能「算相似度」的东西

> 阶段 1 / Wave 2。代码：`src/rag/embedder.py`、`src/rag/store.py`｜测试：`tests/test_embedder.py`、`tests/test_store.py`｜Demo：`scripts/demo_retrieve.py`

## 一、做什么 / 为什么 / 不做会怎样

**做什么**：把 Wave1 切出的文本块**向量化**（embedding），存进向量库；查询时把问题也向量化，找「语义最近」的块。

**为什么**：关键词匹配做不到「语义相关但用词不同」。比如问「怎么防止模型编造订单号」，文档里写的是「防幻觉纵深：验证节点」——**没有一个字相同**，但语义相关。向量检索能命中，关键词检索不能。

**不做会怎样**：退化成关键词搜索，用户换个说法就搜不到——这正是 RAG 要解决的核心痛点之一。

## 二、embedding 内部就三步（没有魔法）

```
文本 → WordPiece 分词 → ONNX 前向推理 → 池化(BGE 取 [CLS]) + 归一化 → 向量
```

- **分词**：中文逐字成 token，英文走子词最长匹配（WordPiece 约定）
- **推理**：BGE-small-zh 的 ONNX 导出，CPU 推理
- **池化 + 归一化**：取 `[CLS]` 位置的向量（BGE 系列的约定），除以模长做归一化
- **归一化的意义**：归一化后，两个向量的**点积 == 余弦相似度**，检索时排序只需点积，省一次除法

**为什么用本地 ONNX 而不是 API**：DeepSeek 没有 embedding API；chromadb 内置模型的 S3 下载国内不通。旧项目已下载好 BGE 中文模型，本模块**复用**它——这就是「不重新发明轮子」。

## 三、向量库：chromadb 的封装要点

`VectorStore` 两处设计值得记：

1. **embeddings 由外部算好显式传入**，不让 chromadb 用自己的 embedding function——否则它会去下载内置模型（国内会卡）。副作用是 `store` 能用**假嵌入器**独立测试（`tests/test_store.py` 就用了 FakeEmbedder，又快又稳）。
2. **相似度用余弦**（`metadata={"hnsw:space": "cosine"}`）；chroma 返回的是**距离**，本模块换算成相似度 `score = 1 - distance`（越大越相似，符合直觉）。

## 四、实跑证据（单次实跑、未挑选）

建索引：33 篇文档 → markdown 切分 → **621 块**（本 demo 用 markdown 策略）。查询命中：

| 问题 | 命中（Top-1） | 相似度 |
|------|--------------|--------|
| checkpointer 有什么用 | `pl_lesson_agent7_webapp.md`（checkpointer 一段） | 0.670 |
| 怎么防止模型编造不存在的订单号 | `pl_lesson_agent4_reliability.md`「防幻觉纵深：验证节点」 | 0.650 |
| MCP 协议里 server 和 client 是什么关系 | `lc_extra_mcp.md`「架构三件套」 | 0.674 |

**关键观察**：三个问题命中的都是**语义最相关**的块，且**用词不同**（问题问"编造订单号"，命中块写"防幻觉验证节点"）——这正是向量检索相对关键词检索的价值。原始日志见 `outputs/wave2_demo_retrieve.log`。

## 五、TDD 过程与踩坑（真实记录）

- **测试先行**：`test_embedder.py`（形状/归一化/语义序）+ `test_store.py`（增删查/持久化），先跑到 RED（模块不存在）
- **踩坑**：实现 `store.py` 时列表推导 `[c.metadata or {...} for i,c in ...]` 漏写 `enumerate`，pytest 立刻报 `NameError: name 'c' is not defined` → 修正 → 12 passed。**这就是先写测试的价值：bug 在几秒内暴露，而不是等到跑 demo 才发现。**

## 六、三问法精读指引

1. **为什么归一化后「点积 = 余弦」？**（答：余弦 = 点积 / (模长乘积)；归一化让两个模长都=1，分母变 1，点积即余弦）
2. **`VectorStore` 为什么不自己算 embedding、而要外部传入？**（答：① 不让 chromadb 下载内置模型；② 解耦——store 可用假嵌入器独立测试；③ embedder 可替换而不改 store）
3. **chroma 返回的 distance 和我们的 score 什么关系？**（答：cosine 空间下 distance = 1 - 余弦相似度，故 score = 1 - distance；换算后语义是「越大越相似」）
