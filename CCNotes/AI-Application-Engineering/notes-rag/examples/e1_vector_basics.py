"""e1 —— 向量的最小模型：3 维玩具向量，能手算

为什么先讲「玩具向量」：
  真实模型吐出的是 512 维向量（见 e2），你既看不见也算不动。
  但「相似度」这件事的原理和维度无关——先用 3 维把公式看清，
  再去看 512 维就不会懵。

运行：PYTHONIOENCODING=utf-8 <python> notes-rag/examples/e1_vector_basics.py
"""
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return sum(x * x for x in a) ** 0.5


def cosine(a, b):
    """余弦相似度 = 点积 / (模长乘积)，取值 [-1, 1]。"""
    return dot(a, b) / (norm(a) * norm(b))


def normalize(a):
    n = norm(a)
    return [x / n for x in a]


def line(n=60):
    print("-" * n)


# 想象这个 3 维空间的三个轴是：[技术, 生活, 情感]
QUERY = [1.0, 0.0, 0.0]        # 一个"纯技术"的查询

DOCS = {
    "doc_a": [0.9, 0.1, 0.0],  # 很像 query
    "doc_b": [0.6, 0.5, 0.1],  # 有点像
    "doc_c": [0.0, 0.1, 0.9],  # 基本无关
}


def main():
    print("1. 向量就是坐标（3 个轴 = [技术, 生活, 情感]）")
    line()
    print(f"  query = {QUERY}")
    for name, vec in DOCS.items():
        print(f"  {name} = {vec}")

    print("\n2. 余弦相似度 = 点积 / (模长 x 模长)，取值 [-1, 1]")
    line()
    print("  cos(query, doc_a)")
    print(f"    = (1.0*0.9 + 0.0*0.1 + 0.0*0.0) / ({norm(QUERY):.4f} * {norm(DOCS['doc_a']):.4f})")
    print(f"    = {dot(QUERY, DOCS['doc_a']):.4f} / {norm(QUERY) * norm(DOCS['doc_a']):.4f}")
    print(f"    = {cosine(QUERY, DOCS['doc_a']):.4f}")

    print("\n3. 三个文档与 query 的相似度（降序 = 检索返回的顺序）")
    line()
    scored = sorted(DOCS.items(), key=lambda kv: cosine(QUERY, kv[1]), reverse=True)
    for rank, (name, vec) in enumerate(scored, 1):
        print(f"  #{rank}  {name}   cos = {cosine(QUERY, vec):.4f}   向量={vec}")
    print("\n  → doc_a 最靠前（0.994），doc_c 最靠后——这就是「检索」的全部：")
    print("    按相似度排序，取前 K 个。剩下的都是工程细节。")

    print("\n4. 关键性质：归一化之后，点积 == 余弦")
    line()
    qn = normalize(QUERY)
    print(f"  query 归一化后 = {[round(x, 4) for x in qn]}（模长变成 1）")
    print(f"  {'文档':<8}{'归一化后的点积':>16}{'余弦相似度':>14}")
    for name, vec in DOCS.items():
        vn = normalize(vec)
        print(f"  {name:<8}{dot(qn, vn):>16.4f}{cosine(QUERY, vec):>14.4f}")
    print("\n  → 两列完全一样。这就是 embedder.py 最后要归一化的原因：")
    print("    模长都变成 1 以后，分母消失，排序直接用点积就行（省一次除法）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
