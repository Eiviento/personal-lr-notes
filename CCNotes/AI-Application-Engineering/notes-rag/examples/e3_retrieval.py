"""e3 —— 两路检索：向量 vs BM25，同一个问题各返回什么

这个实验要回答的问题：
  为什么需要「混合检索」？因为向量和 BM25 是**互补的两个瞎子**——
  同一个问题，它们返回的结果不一样，甚至不重叠。

做法：把 notes-rag/data/sample_docs.md 切成块，然后对每个 query：
  - 向量路：给 query 和每个块编码，算余弦，排序
  - BM25 路：调项目真实的 BM25Index，拿到排名与分数
  两路并排打出来，你自己看差异。

运行：PYTHONIOENCODING=utf-8 <python> notes-rag/examples/e3_retrieval.py
"""
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent  # AI-Application-Engineering/
sys.path.insert(0, str(ROOT))

from src.rag.bm25 import BM25Index, tokenize   # noqa: E402
from src.rag.embedder import get_embedder      # noqa: E402
from src.rag.retriever import reciprocal_rank_fusion  # noqa: E402
from src.rag.splitter import split             # noqa: E402

CORPUS = ROOT / "notes-rag" / "data" / "sample_docs.md"

QUERIES = [
    "SO-1003",              # 专有名词：BM25 的强项
    "怎么知道设备的位置",     # 语义提问：向量路的强项
    "深色主题",              # 普通关键词
]

TOP = 3


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def title_of(chunk) -> str:
    """把块的第一行当标题用（sample_docs 每块以 ## 开头）。"""
    first = chunk.text.strip().splitlines()[0]
    return first.lstrip("# ").strip()


def main():
    text = CORPUS.read_text(encoding="utf-8")
    chunks = split(text, strategy="markdown", size=500)
    print(f"语料：{CORPUS.name}  ->  {len(chunks)} 个块")
    for i, c in enumerate(chunks):
        print(f"  [{i}] {title_of(c)}")
    print()

    emb = get_embedder()
    doc_vecs = emb.embed([c.text for c in chunks])
    bm25 = BM25Index(chunks)

    for q in QUERIES:
        print("=" * 64)
        print(f"问：{q}")
        print("=" * 64)

        # ---- 向量路：编码 -> 算余弦 -> 排序 ----
        qv = emb.embed([q])[0]
        vec_ranked = sorted(
            range(len(chunks)), key=lambda i: dot(qv, doc_vecs[i]), reverse=True
        )[:TOP]
        print("  【向量路】语义相近优先")
        for r, i in enumerate(vec_ranked, 1):
            print(f"    #{r}  cos={dot(qv, doc_vecs[i]):+.4f}   {title_of(chunks[i])}")

        # ---- BM25 路：关键词打分 ----
        bm_hits = bm25.query(q, k=TOP)
        print("  【BM25 路】关键词优先  (查询分词：" + " ".join(tokenize(q)) + ")")
        if not bm_hits:
            print("    （无命中：语料里没有任何查询词）")
        for r, (c, s) in enumerate(bm_hits, 1):
            print(f"    #{r}  score={s:6.3f}   {title_of(c)}")

        vset = {i for i in vec_ranked}
        bset = {chunks.index(c) for c, _ in bm_hits}
        only_v = [title_of(chunks[i]) for i in vset - bset]
        only_b = [title_of(chunks[i]) for i in bset - vset]
        print(f"  → 两路都命中：{[title_of(chunks[i]) for i in vset & bset]}")
        print(f"  → 只有向量命中：{only_v}")
        print(f"  → 只有 BM25 命中：{only_b}")

        # ---- 对照：如果「分数直接相加」会怎样（演示尺度问题）----
        union = sorted(vset | bset)
        vscore = {i: dot(qv, doc_vecs[i]) for i in union}
        bscore = {i: 0.0 for i in union}
        for c, s in bm_hits:
            bscore[chunks.index(c)] = s
        summed = sorted(union, key=lambda i: vscore[i] + bscore[i], reverse=True)[:TOP]
        print("  【如果直接相加】向量分 + BM25 分（演示：尺度不同导致 BM25 主导）")
        for r, i in enumerate(summed, 1):
            tot = vscore[i] + bscore[i]
            print(f"    #{r}  {vscore[i]:.4f} + {bscore[i]:7.3f} = {tot:8.4f}   {title_of(chunks[i])}")

        # ---- 对照：项目真实做法 RRF（只看排名，不看分数）----
        vec_full = sorted(range(len(chunks)), key=lambda i: dot(qv, doc_vecs[i]), reverse=True)
        bm_full = [(chunks.index(c), s) for c, s in bm25.query(q, k=len(chunks))]
        fused = reciprocal_rank_fusion(
            [[(chunks[i], 0.0) for i in vec_full], [(chunks[i], s) for i, s in bm_full]],
            k=60,
        )[:TOP]
        print("  【RRF 融合】只看排名，1/(60+rank) 求和（← 项目真实做法）")
        for r, (c, s) in enumerate(fused, 1):
            print(f"    #{r}  rrf={s:.6f}   {title_of(c)}")
        print()

    print("=" * 64)
    print("结论")
    print("=" * 64)
    print("  两路的排序和命中集经常不一样 —— 这就是「混合检索」存在的理由：")
    print("  谁都不能单独覆盖全部情况，融合起来才能取长补短。")
    print("  （注意：本项目 BM25 用的是「中文单字」轻量分词，容易撞字命中；")
    print("    生产环境会换 jieba 等更细的分词——但两路差异的大格局不变。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
