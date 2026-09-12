"""端到端检索 demo：语料 → 切分 → 向量化 → 建库 → 查询

第一次把 Wave1(切分) + Wave2(向量) 串起来：给几个问题，看检索命中哪些块。
这是「向量检索」最直观的证据——问题与命中块的语义是否对得上，肉眼可判断。

运行：PYTHONIOENCODING=utf-8 <agent_env python> scripts/demo_retrieve.py
"""
import shutil
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.embedder import get_embedder  # noqa: E402
from src.rag.splitter import split  # noqa: E402
from src.rag.store import VectorStore  # noqa: E402

DOCS_DIR = ROOT / "data" / "documents"
DB_DIR = ROOT / "data" / "chroma_db"

QUERIES = [
    "混合检索是怎么融合关键词和向量的",
    "checkpointer 有什么用",
    "怎么防止模型编造不存在的订单号",
    "MCP 协议里 server 和 client 是什么关系",
]


def build_index(strategy: str = "markdown", size: int = 500) -> VectorStore:
    """建索引：清空旧库 → 切分 → 嵌入 → 写入。"""
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)  # 每次重建，保证 demo 可重复
    store = VectorStore(path=DB_DIR, embedder=get_embedder(), name="docqa_demo")
    total = 0
    t0 = time.time()
    for md in sorted(DOCS_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        chunks = split(text, strategy=strategy, size=size)
        for c in chunks:
            c.metadata["source"] = md.name  # 记录来源，便于溯源
        total += store.add(chunks)
    print(f"建索引完成：{total} 块，耗时 {time.time() - t0:.1f}s（策略={strategy}）\n")
    return store


def main():
    store = build_index()
    for q in QUERIES:
        print(f"❓ {q}")
        hits = store.query(q, k=3)
        for chunk, score in hits:
            src = chunk.metadata.get("source", "?")
            snippet = chunk.text.replace("\n", " ")[:80]
            print(f"   [{score:.3f}] {src}  {snippet}…")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
