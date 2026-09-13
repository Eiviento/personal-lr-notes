"""e4 —— RRF 融合：手算 vs 项目代码，逐行核对

这个实验要回答的问题：
  两路检索的分数尺度完全不同（向量 0~1，BM25 几十上百），为什么不能相加？
  RRF 用「只看排名」绕开了它——但 1/(k+rank) 到底怎么算的？

做法：先用一个 5 个文档的玩具榜单，把每一项贡献**手算**出来；
     再调用项目真实的 reciprocal_rank_fusion()，逐行对照。
     最后一位是判据：手算顺序 == 代码顺序，脚本才 exit 0。

运行：PYTHONIOENCODING=utf-8 <python> notes-rag/examples/e4_fusion_rrf.py
"""
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent  # AI-Application-Engineering/
sys.path.insert(0, str(ROOT))

from src.rag.retriever import reciprocal_rank_fusion  # noqa: E402
from src.rag.splitter import Chunk                    # noqa: E402

K = 60

# 两路榜单（按排名先后，从 1 开始）
VEC_RANK = ["A", "B", "C", "D"]
BM_RANK = ["C", "A", "E", "B"]


def key_of(chunk) -> str:
    return chunk.metadata.get("id") or chunk.text[:50]


def manual_rrf(named_lists, k=K):
    """手算版 RRF：第 rank 名给该文档贡献 1/(k+rank)，多路求和。"""
    scores = {}
    trace = []
    for name, lst in named_lists:
        for rank, key in enumerate(lst, start=1):
            contrib = 1.0 / (k + rank)
            scores[key] = scores.get(key, 0.0) + contrib
            trace.append((name, key, rank, contrib))
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked, trace


def main():
    print("两路榜单（分数已被扔掉，只剩排名）")
    print(f"  向量榜：{VEC_RANK}")
    print(f"  BM25榜：{BM_RANK}")

    print(f"\n[1] 逐项贡献  1/(k+rank)，k={K}")
    ranked, trace = manual_rrf([("向量", VEC_RANK), ("BM25", BM_RANK)])
    for name, key, rank, c in trace:
        print(f"    {name:<5} 文档 {key}  排名#{rank}  ->  1/({K}+{rank}) = {c:.6f}")

    print("\n[2] 汇总求和（手算）")
    for key, s in ranked:
        parts = [f"1/{K + r}" for nm, kk, r, _ in trace if kk == key]
        print(f"    {key}  = {' + '.join(parts)}  =  {s:.6f}")

    print("\n[3] 调用项目真实的 reciprocal_rank_fusion()")
    def mk(key):
        return Chunk(text=f"{key} 的内容", metadata={"id": key})

    vec_hits = [(mk(x), 0.9) for x in VEC_RANK]   # 分数随便给，RRF 不看它
    bm_hits = [(mk(x), 12.3) for x in BM_RANK]
    fused = reciprocal_rank_fusion([vec_hits, bm_hits], k=K)
    for c, s in fused:
        print(f"    {key_of(c)}  {s:.6f}")

    manual_order = [k for k, _ in ranked]
    code_order = [key_of(c) for c, _ in fused]
    print(f"\n[4] 核对")
    print(f"    手算顺序：{manual_order}")
    print(f"    代码顺序：{code_order}")
    ok = manual_order == code_order
    print(f"    一致？　{'YES ✔' if ok else 'NO ✘ —— 教学材料有错！'}")

    print("\n[5] k 的作用（k 越大，排名差异被压得越平）")
    for kk in (1, 60, 1000):
        r, _ = manual_rrf([("v", VEC_RANK), ("b", BM_RANK)], k=kk)
        top3 = "  ".join(f"{a}={b:.4f}" for a, b in r[:3])
        print(f"    k={kk:<5} 前三： {top3}")
    print("    -> k 小的时候，第 1 名几乎通吃；k 大的时候，名次差被抹平。")
    print("       k=60 是常用默认值（各名次贡献接近、又不至于完全一样）。")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
