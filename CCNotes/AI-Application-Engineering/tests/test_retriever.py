"""retriever 单元测试（TDD）

混合检索 = 向量检索 + BM25，用 RRF（Reciprocal Rank Fusion）融合。
RRF 的精髓：只看**排名**、不看原始分数——因为向量相似度(0~1)与 BM25 分数(可任意大)
尺度不同，直接相加没意义；用 1/(k+rank) 求和就对两者公平。

契约：reciprocal_rank_fusion(list[list[(Chunk, score)]], k) -> list[(Chunk, score)]
"""
from src.rag.retriever import reciprocal_rank_fusion
from src.rag.splitter import Chunk


def _c(text, idx):
    return Chunk(text, {"index": idx})


def test_rrf_ranks_consensus_first():
    """在两个列表都靠前的项，融合后应排最前"""
    vec = [(_c("x", 0), 0.9), (_c("y", 1), 0.8)]
    bm = [(_c("y", 1), 5.0), (_c("z", 2), 1.0)]
    fused = reciprocal_rank_fusion([vec, bm])
    assert fused[0][0].metadata["index"] == 1  # y 两榜皆前列


def test_rrf_single_list_preserves_order():
    """只有一路结果时，顺序不变"""
    only = [(_c("a", 0), 0.9), (_c("b", 1), 0.5)]
    fused = reciprocal_rank_fusion([only])
    assert [c.metadata["index"] for c, _ in fused] == [0, 1]


def test_rrf_score_is_positive_and_desc():
    """融合分数为正、降序"""
    vec = [(_c("x", 0), 0.9)]
    bm = [(_c("y", 1), 3.0)]
    fused = reciprocal_rank_fusion([vec, bm])
    scores = [s for _, s in fused]
    assert all(s > 0 for s in scores)
    assert scores == sorted(scores, reverse=True)
