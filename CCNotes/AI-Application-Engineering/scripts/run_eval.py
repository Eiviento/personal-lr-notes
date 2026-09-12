"""检索质量评估：三档策略 × 20 题真实分数

产出一份可对比的报告：纯向量 / 混合 / 混合+rerank 三档的
hit_rate（命中率）、recall（召回率）、MRR（平均倒数排名）。
这是 Wave 4 的核心证据——「检索到底行不行」用数字说话，不靠感觉。

运行：PYTHONIOENCODING=utf-8 <agent_env python> scripts/run_eval.py
"""
import shutil
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.evaluate import evaluate, load_eval_set  # noqa: E402
from src.rag.bm25 import BM25Index  # noqa: E402
from src.rag.embedder import get_embedder  # noqa: E402
from src.rag.reranker import Reranker  # noqa: E402
from src.rag.retriever import HybridRetriever  # noqa: E402
from src.rag.splitter import split  # noqa: E402
from src.rag.store import VectorStore  # noqa: E402

DOCS_DIR = ROOT / "data" / "documents"
DB_DIR = ROOT / "data" / "chroma_db_eval"
EVAL_SET = ROOT / "data" / "eval_set.json"
K = 5


def build():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    store = VectorStore(path=DB_DIR, embedder=get_embedder(), name="docqa_eval")
    all_chunks = []
    for md in sorted(DOCS_DIR.glob("*.md")):
        chunks = split(md.read_text(encoding="utf-8"), strategy="markdown", size=500)
        for c in chunks:
            c.metadata["source"] = md.name
            c.metadata["id"] = f"{md.name}-{c.metadata['index']}"
        all_chunks.extend(chunks)
        store.add(chunks)
    return store, all_chunks


def main():
    t0 = time.time()
    store, all_chunks = build()
    bm25 = BM25Index(all_chunks)
    retriever = HybridRetriever(store, bm25)
    reranker = Reranker()
    cases = load_eval_set(EVAL_SET)
    print(f"语料 {len(all_chunks)} 块 · 评测集 {len(cases)} 题 · Top-K={K}\n")

    strategies = {
        "纯向量": lambda q, k: store.query(q, k),
        "混合RRF": lambda q, k: retriever.retrieve(q, k),
        "混合+rerank": lambda q, k: reranker.rerank(q, retriever.retrieve(q, 20), top_n=k),
    }
    print(f"{'策略':<12}{'hit_rate':>10}{'recall':>10}{'MRR':>10}")
    print("-" * 42)
    for name, fn in strategies.items():
        m = evaluate(fn, cases, k=K)
        print(f"{name:<12}{m['hit_rate']:>10.2f}{m['recall']:>10.2f}{m['mrr']:>10.2f}")
    print(f"\n耗时 {time.time() - t0:.1f}s（单次实跑、未挑选）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
