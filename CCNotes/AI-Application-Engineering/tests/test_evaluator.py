"""evaluator 单元测试（TDD）

把「检索得准不准」变成可计算的三指标：
  hit_rate  — Top-K 里至少命中一个相关文档的问题占比
  recall@k  — Top-K 覆盖了多少比例的相关文档（平均）
  MRR       — 第一个相关文档排名的倒数（排越前越高）

契约：evaluate(retrieve_fn, eval_set, k) -> dict，retrieve_fn(query, k) -> list[(Chunk, score)]
"""
from src.evaluation.evaluate import evaluate
from src.rag.splitter import Chunk


def _hit(source):
    return (Chunk("内容", {"source": source}), 0.9)


def test_perfect_retrieval():
    eval_set = [{"q": "a", "relevant": ["d1.md"]}, {"q": "b", "relevant": ["d2.md"]}]

    def fake(q, k):
        return [_hit("d1.md")] if q == "a" else [_hit("d2.md")]

    m = evaluate(fake, eval_set, k=1)
    assert m["hit_rate"] == 1.0
    assert m["mrr"] == 1.0
    assert m["recall"] == 1.0


def test_miss_lowers_hit_rate():
    eval_set = [{"q": "a", "relevant": ["d1.md"]}, {"q": "b", "relevant": ["d2.md"]}]

    def fake(q, k):
        return [_hit("d1.md")]  # b 永远查不到

    m = evaluate(fake, eval_set, k=1)
    assert m["hit_rate"] == 0.5


def test_mrr_reflects_rank():
    """正确文档排第 2 → 该条 rr = 1/2"""
    eval_set = [{"q": "a", "relevant": ["d1.md"]}]

    def fake(q, k):
        return [_hit("other.md"), _hit("d1.md")]

    m = evaluate(fake, eval_set, k=2)
    assert abs(m["mrr"] - 0.5) < 1e-9


def test_recall_with_multiple_relevant():
    """一条问题有 2 个相关文档，只命中 1 个 → recall = 0.5"""
    eval_set = [{"q": "a", "relevant": ["d1.md", "d2.md"]}]

    def fake(q, k):
        return [_hit("d1.md")]

    m = evaluate(fake, eval_set, k=1)
    assert abs(m["recall"] - 0.5) < 1e-9
