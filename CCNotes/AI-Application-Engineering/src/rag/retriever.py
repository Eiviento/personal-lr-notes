"""retriever —— 混合检索（向量 + BM25 → RRF 融合）

为什么需要混合：
  向量检索强在「语义」，弱在「精确术语/编号」；BM25 反之。
  两者结果**融合**能取长补短——这是生产级 RAG 的标配。

为什么用 RRF 而不是「分数相加」：
  向量相似度是 0~1，BM25 分数可达几十上百——**尺度不同，直接相加没意义**。
  RRF（Reciprocal Rank Fusion）只看**排名**：每个结果对某项贡献 1/(k + rank)，
  排名越靠前贡献越大；k（默认 60）起平滑作用。对异构分数天然公平。

接口：
  reciprocal_rank_fusion(list[list[(Chunk, score)]], k) -> list[(Chunk, score)]
  HybridRetriever(store, bm25_index).retrieve(query, k) -> list[(Chunk, score)]
"""
from .splitter import Chunk  # noqa: F401  (类型提示用)


def _key(chunk) -> str:
    """融和时的唯一键：优先 metadata['id']，否则取文本前缀。"""
    return chunk.metadata.get("id") or chunk.text[:50]


def reciprocal_rank_fusion(result_lists: list, k: int = 60) -> list:
    """把多路检索结果按排名融合（RRF）。"""
    scores: dict = {}
    items: dict = {}
    for rlist in result_lists:
        for rank, (chunk, _score) in enumerate(rlist, start=1):
            key = _key(chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items[key] = chunk
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(items[key], s) for key, s in ranked]


class HybridRetriever:
    """向量 + BM25 混合检索器。"""

    def __init__(self, store, bm25_index, rrf_k: int = 60, vec_k: int = 20, bm25_k: int = 20):
        self.store = store
        self.bm25 = bm25_index
        self.rrf_k = rrf_k
        self.vec_k = vec_k
        self.bm25_k = bm25_k

    def retrieve(self, query: str, k: int = 5) -> list:
        vec_hits = self.store.query(query, k=self.vec_k)
        bm_hits = self.bm25.query(query, k=self.bm25_k)
        fused = reciprocal_rank_fusion([vec_hits, bm_hits], k=self.rrf_k)
        return fused[:k]
