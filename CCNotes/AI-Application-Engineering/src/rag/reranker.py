"""reranker —— 候选精排

为什么需要（召回 vs 排序是两件事）：
  混合检索（向量+BM25）先「召回」一批候选（如 20 个），但它们的**排序**未必准。
  精排模型（cross-encoder）把「查询 + 候选」拼在一起喂模型打分，比向量相似度更准，
  代价是慢——所以只对少量候选做。

**本实现的诚实说明（降级）**：
  真正的 cross-encoder（如 BGE-reranker）需要额外下载模型（国内可能受阻），
  本项目未验证其可获取性 → 采用**降级实现**：用「查询词在候选中的覆盖率」重排
  （BM25 思路的轻量版），可解释、无需模型。真实 cross-encoder 作为后续增强项。

接口：Reranker().rerank(query, candidates, top_n) -> list[(Chunk, score)]
     candidates: list[(Chunk, score)]
"""
from .bm25 import tokenize


class Reranker:
    def __init__(self, mode: str = "coverage"):
        self.mode = mode

    def rerank(self, query: str, candidates: list, top_n: int = 5) -> list:
        if self.mode == "identity" or not candidates:
            return list(candidates[:top_n])

        q_tokens = set(tokenize(query))
        scored = []
        for chunk, base in candidates:
            c_tokens = set(tokenize(chunk.text))
            coverage = len(q_tokens & c_tokens) / max(len(q_tokens), 1)
            # 主序=覆盖率（精排），次序=原融合分（保底）
            scored.append((chunk, coverage, base))
        scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [(chunk, cov) for chunk, cov, _ in scored[:top_n]]
