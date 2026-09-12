"""embedder 单元测试（TDD）

embedder 是本地 ONNX 推理，无需 API——可以直接对真模型测（但仍属"零成本"）。
契约：get_embedder().embed(texts: list[str]) -> list[list[float]]（归一化向量）
"""
from src.rag.embedder import get_embedder


def test_embed_shape_and_normalized():
    """嵌入形状正确且已归一化（模长 ≈ 1）"""
    emb = get_embedder()
    vecs = emb.embed(["文档切分是 RAG 的第一道杠杆"])
    assert len(vecs) == 1
    assert len(vecs[0]) > 0
    norm = sum(x * x for x in vecs[0]) ** 0.5
    assert abs(norm - 1.0) < 1e-2, f"向量未归一化：模长={norm}"


def test_batch_embedding():
    """批量编码返回条数与输入一致"""
    emb = get_embedder()
    vecs = emb.embed(["第一段", "第二段", "第三段"])
    assert len(vecs) == 3
    assert all(len(v) == len(vecs[0]) for v in vecs)


def test_semantic_similarity_ordering():
    """语义相近的文本，余弦相似度应高于不相关的文本"""
    emb = get_embedder()
    v = emb.embed([
        "混合检索",
        "关键词检索与向量检索结合的检索方式",
        "今天天气晴朗适合出门散步",
    ])

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))  # 已归一化，点积即余弦

    sim_related = cos(v[0], v[1])
    sim_unrelated = cos(v[0], v[2])
    assert sim_related > sim_unrelated, (
        f"语义相近({sim_related:.3f}) 应 > 不相关({sim_unrelated:.3f})"
    )
