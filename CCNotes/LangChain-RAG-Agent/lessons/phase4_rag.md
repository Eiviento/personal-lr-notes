# Phase 4.1：RAG 基础 —— 历史协议模板检索注入

> 对应脚本：`scripts/phase4_1_rag.py`（build / query / run 三个子命令）
> 依赖：`chromadb`、`langchain-chroma`、`onnxruntime`、`numpy`（镜像安装见坑 #1）

---

## RAG 解决的两个问题

| 问题 | 现状 | RAG 的答案 |
|------|------|-----------|
| 上下文窗口有限 | 3.1 超长文档只能截断 | 切片存向量库，只检索相关片段注入 |
| Few-shot 素材会变多 | 1.2 教学假例还没换成真实协议 | 历史协议模板存向量库，按语义检索最相关的当参考 |

三件套：**R**etrieval 检索 → **A**ugmented 增强（拼进 Prompt）→ **G**eneration 生成（链照常运行）。

## Embedding 原理：为什么用向量而不是关键词

"设备位置上报"和"GPS 经纬度"没有共同关键词，但语义相关。Embedding 模型把文本变成向量，**语义相近 → 向量距离近**。

一个 embedding 函数内部就三步（`LocalBertEmbedding`，脚本里 ~50 行完整实现）：
1. **WordPiece 分词**：中文逐字成 token，英文子词最长匹配（`##` 前缀表示接续）
2. **ONNX 推理**：token ids → 神经网络 → 每个 token 一个向量
3. **池化 + 归一化**：BGE 取 `[CLS]` 向量（`pooling="cls"`）；MiniLM 用全 token 平均（`pooling="mean"`）；归一化后余弦相似度 = 点积

## 链怎么接：只换"字段定义"这一环

```python
rag_chain = (
    RunnablePassthrough.assign(retrieved=RunnableLambda(lambda s: retrieve(s["requirement"])))
    | RunnablePassthrough.assign(key_points=analyze_chain)
    | RunnablePassthrough.assign(fields=rag_fields_chain)   # ← Prompt 多了 {retrieved} 上下文
    | RunnablePassthrough.assign(checks=rules_chain)
    | RunnableLambda(merge_final)
)
```

零件复用：analyze/rules/merge 原封不动，只是字段定义 Prompt 增加"历史模板"参考段。

## 实测效果（同一份水表需求，两链对比）

| | 无 RAG（3.4 链） | 有 RAG（4.1 链） |
|---|---|---|
| 协议名 | 智能水表数据上报与控制协议 | 水表计量与告警协议 |
| 字段 | device_id / report_type / timestamp / cumulative_volume / ...（10 个，通用命名） | msg_type / meter_id / total_flow / valve_state / battery_voltage / crc16（7 个，**与公司水表模板命名一致**） |
| 风格 | 每次生成风格漂移 | 自动继承历史模板的命名/帧结构约定 |

RAG 的价值不在"更全"，在**一致性**：新协议自动沿用公司历史模板的命名和结构——历史协议资产终于能用起来（1.2 坑 #2 的归宿）。

## 环境坑三连（都踩过，别重蹈）

1. **pip 装包**：PyPI 直连被重置 → 用清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple`
2. **chromadb 内置 ONNX 模型**：从 S3 下载超时且路径写死 → 从 hf-mirror 下载 `Xenova/bge-small-zh-v1.5` 的 `onnx/model.onnx` + `vocab.txt` 到 `models/bge-small-zh/`，自定义 EmbeddingFunction 本地推理（`models/`、`rag_db/` 已 gitignore）
3. **MiniLM 中文失效**：all-MiniLM-L6-v2 是英文模型，中文检索排序错乱（查"水表阀门"命中"环境监测"）→ 换 BGE-small-zh-v1.5（CLS 池化）+ 显式 `hnsw:space=cosine`，检索立刻正确（水表查询 top-1 命中水表模板，距离 0.364）

**生产建议**：BGE-small-zh 够内部工具用；要更好换 `BAAI/bge-m3`（多语言）或 API 类 embedding（SiliconFlow 等），**换模型管道代码一行不动**——又是"换模型只改参数"。

---

*对应 progress.md 的 Phase 4 记录。*
