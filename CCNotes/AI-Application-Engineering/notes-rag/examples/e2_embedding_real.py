"""e2 —— 真实模型看到的世界：BGE 把一句话变成 512 维向量

和 e1 的区别：e1 的向量是我手写的 3 维玩具；这里用的是**项目真正在跑**的
BGE-small-zh（本地 ONNX 推理）。维度高得多，但「算相似度」的道理一模一样。

这个实验要回答的问题：
  两个**没有一个字相同**的句子（"设备位置上报" / "GPS 经纬度"），
  为什么真实模型会认为它们很像？这就是向量检索能命中「换词同义」的原因。

运行：PYTHONIOENCODING=utf-8 <python> notes-rag/examples/e2_embedding_real.py
"""
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent  # AI-Application-Engineering/
sys.path.insert(0, str(ROOT))

from src.rag.embedder import get_embedder  # noqa: E402


def dot(a, b):
    """模型输出已归一化，所以点积就是余弦相似度。"""
    return sum(x * y for x, y in zip(a, b))


SENTENCES = [
    "设备位置上报",       # 0
    "GPS 经纬度",         # 1 —— 与 0 无共同字，但语义相关
    "今天天气怎么样",     # 2 —— 与 0 无关
    "用户偏好深色主题",   # 3
    "用户喜欢深色界面",   # 4 —— 与 3 换词同义
]

PAIRS = [
    (0, 1, "无共同字，但语义相关"),
    (0, 2, "无关（对照组）"),
    (3, 4, "换词同义"),
]


def main():
    print("加载 BGE-small-zh（本地 ONNX，首次约 1-2 秒）...")
    emb = get_embedder()
    vecs = emb.embed(SENTENCES)
    dim = len(vecs[0])

    print(f"模型：bge-small-zh    向量维度 = {dim}")
    print(f'"{SENTENCES[0]}" -> {dim} 个浮点数。前 5 个：')
    print(f"  {[round(x, 4) for x in vecs[0][:5]]}  ...")

    print("\n" + "=" * 62)
    print("配对相似度（余弦）")
    print("=" * 62)
    for i, j, note in PAIRS:
        s = dot(vecs[i], vecs[j])
        print(f"  {SENTENCES[i]!r}")
        print(f"  vs {SENTENCES[j]!r}")
        print(f"     -> {s:+.4f}     [{note}]")
        print()

    print("=" * 62)
    print("全部两两相似度矩阵（行 = 左侧句子）")
    print("=" * 62)
    head = "".join(f"{i:>8}" for i in range(len(SENTENCES)))
    print(f"{'':<4}{head}")
    for i, vi in enumerate(vecs):
        row = "".join(f"{dot(vi, vecs[j]):>8.3f}" for j in range(len(SENTENCES)))
        print(f"[{i}] {row}")

    print("\n观察：")
    print(f"  0 vs 1 = {dot(vecs[0], vecs[1]):.3f}  <- 0 个共同字，却很像（模型懂语义）")
    print(f"  0 vs 2 = {dot(vecs[0], vecs[2]):.3f}  <- 对照组，明显更低")
    print(f"  3 vs 4 = {dot(vecs[3], vecs[4]):.3f}  <- 换词同义，接近 1")
    print("\n这就是「向量检索」能命中换词同义、而关键词检索不能的根本原因。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
