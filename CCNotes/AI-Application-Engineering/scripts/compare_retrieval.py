"""三档检索对比：纯向量 vs 混合(RRF) vs 混合+rerank

看什么：不同类型的查询，三档的 Top-3 命中差异——
  - 语义类查询：向量本就强
  - 专有名词类查询（create_agent / thread_id 等）：向量易漏、BM25 补位

这是「为什么生产级 RAG 要混合检索」的直接证据。

运行：PYTHONIOENCODING=utf-8 <agent_env python> scripts/compare_retrieval.py
"""
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.bm25 import BM25Index  # noqa: E402
from src.rag.embedder import get_embedder  # noqa: E402
from src.rag.reranker import Reranker  # noqa: E402
from src.rag.retriever import HybridRetriever  # noqa: E402
from src.rag.splitter import split  # noqa: E402
from src.rag.store import VectorStore  # noqa: E402

DOCS_DIR = ROOT / "data" / "documents"
DB_DIR = ROOT / "data" / "chroma_db_cmp"

QUERIES = [
    ("专有名词", "create_agent 和 create_react_agent 有什么区别"),
    ("专有名词", "thread_id 是干什么用的"),
    ("语义", "怎么让 agent 在写操作前停下来等人工审批"),
    ("语义", "怎么判断检索系统好不好"),
]


def build():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    store = VectorStore(path=DB_DIR, embedder=get_embedder(), name="docqa_cmp")
    all_chunks = []
    for md in sorted(DOCS_DIR.glob("*.md")):
        chunks = split(md.read_text(encoding="utf-8"), strategy="markdown", size=500)
        for c in chunks:
            c.metadata["source"] = md.name
            c.metadata["id"] = f"{md.name}-{c.metadata['index']}"  # 唯一键供 RRF
        all_chunks.extend(chunks)
        store.add(chunks)
    return store, all_chunks


def show(label, hits):
    parts = []
    for chunk, score in hits:
        parts.append(f"{chunk.metadata.get('source', '?')[:22]}({score:.3f})")
    print(f"    {label:<10}{' | '.join(parts)}")


def main():
    store, all_chunks = build()
    bm25 = BM25Index(all_chunks)
    retriever = HybridRetriever(store, bm25)
    reranker = Reranker()
    print(f"语料 {len(all_chunks)} 块\n")
    for tag, q in QUERIES:
        print(f"[{tag}] {q}")
        show("纯向量", store.query(q, k=3))
        show("混合RRF", retriever.retrieve(q, k=3))
        show("混合+rerank", reranker.rerank(q, retriever.retrieve(q, k=20), top_n=3))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
