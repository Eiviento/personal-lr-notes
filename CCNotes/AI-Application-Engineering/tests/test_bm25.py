"""bm25 单元测试（TDD）

BM25 是关键词检索：靠「词出现频率 + 词稀有度」打分，补向量检索「专有名词/编号易漏」的短板。
契约：BM25Index(chunks).query(text, k) -> list[(Chunk, score)]（score 降序）
"""
from src.rag.bm25 import BM25Index
from src.rag.splitter import Chunk


def _chunks():
    return [
        Chunk("混合检索融合关键词与向量", {"index": 0}),
        Chunk("模型训练需要大量标注数据", {"index": 1}),
        Chunk("向量数据库存储嵌入", {"index": 2}),
    ]


def test_keyword_match_ranks_first():
    """含关键词「关键词」的块应排第一"""
    idx = BM25Index(_chunks())
    hits = idx.query("关键词", k=2)
    assert len(hits) == 2
    assert hits[0][0].metadata["index"] == 0


def test_returns_at_most_k():
    idx = BM25Index(_chunks())
    hits = idx.query("向量", k=1)
    assert len(hits) == 1


def test_rare_term_scores_higher():
    """命中稀有词（专有名词）的块应比命中常见词得分高"""
    chunks = [
        Chunk("order_id SO-1003 查询订单状态", {"index": 0}),
        Chunk("订单查询的一般说明", {"index": 1}),
    ]
    idx = BM25Index(chunks)
    hits = idx.query("SO-1003", k=2)
    assert hits[0][0].metadata["index"] == 0


def test_no_match_returns_empty_or_zero():
    """完全无匹配词时不报错（返回空或低分）"""
    idx = BM25Index(_chunks())
    hits = idx.query("完全不相关的英文词汇 zzzz", k=3)
    assert isinstance(hits, list)
