"""store 单元测试（TDD）

用「假嵌入器」隔离 chromadb 封装逻辑，不依赖真 ONNX 模型（快、稳）。
契约：
  VectorStore(path, embedder).add(chunks) -> int
  .query(text, k) -> list[(Chunk, score)]（score 越大越相似）
  .count() -> int
"""
import math

from src.rag.splitter import Chunk
from src.rag.store import VectorStore


class FakeEmbedder:
    """确定性假嵌入：把文本映射到固定 8 维向量（字符分布），无需真模型。"""

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * 8
            for ch in t:
                v[ord(ch) % 8] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


def test_add_and_count(tmp_path):
    store = VectorStore(path=tmp_path / "db", embedder=FakeEmbedder())
    n = store.add([Chunk("苹果", {"index": 0}), Chunk("香蕉", {"index": 1})])
    assert n == 2
    assert store.count() == 2


def test_query_returns_k_and_most_similar_first(tmp_path):
    store = VectorStore(path=tmp_path / "db", embedder=FakeEmbedder())
    store.add([Chunk("苹果", {"index": 0}), Chunk("香蕉", {"index": 1}), Chunk("西瓜", {"index": 2})])
    hits = store.query("苹果", k=2)
    assert len(hits) == 2
    assert hits[0][0].text == "苹果"  # 相同文本最相似，排第一
    # score 降序
    assert hits[0][1] >= hits[1][1]


def test_persistence_reopen(tmp_path):
    """落盘后重开（新实例）仍能查到——chromadb PersistentClient"""
    p = tmp_path / "db"
    s1 = VectorStore(path=p, embedder=FakeEmbedder())
    s1.add([Chunk("持久化测试", {"index": 0})])
    s2 = VectorStore(path=p, embedder=FakeEmbedder())
    assert s2.count() == 1
