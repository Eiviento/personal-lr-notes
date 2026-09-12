"""store —— 向量库封装（chromadb）

职责：把 Chunk 写进向量库、按语义检索。
- embeddings 由外部 embedder 计算后**显式传入**（不让 chromadb 用自己的 embedding function，
  避免它去下载内置模型）——这也让 store 可用假 embedder 独立测试。
- 相似度用**余弦**（metadata 指定 hnsw:space=cosine）；chroma 返回的是距离，
  本模块换算成相似度 score = 1 - distance（越大越相似）。

接口：
  VectorStore(path, embedder, name).add(chunks) -> int
  .query(text, k) -> list[(Chunk, score)]
  .count() -> int
"""
import chromadb

from .splitter import Chunk


class VectorStore:
    def __init__(self, path, embedder, name: str = "docqa"):
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list) -> int:
        if not chunks:
            return 0
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        start = self.collection.count()
        ids = [f"chunk-{start + i}" for i in range(len(chunks))]
        metadatas = [c.metadata or {"index": start + i} for i, c in enumerate(chunks)]
        self.collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        return len(chunks)

    def query(self, text: str, k: int = 5) -> list:
        qv = self.embedder.embed([text])[0]
        res = self.collection.query(query_embeddings=[qv], n_results=k)
        out = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            out.append((Chunk(doc, dict(meta)), 1.0 - dist))  # 距离→相似度
        return out

    def count(self) -> int:
        return self.collection.count()
