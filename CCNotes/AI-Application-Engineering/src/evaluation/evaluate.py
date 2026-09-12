"""evaluate —— 检索质量评估（把"感觉准"变成"测得准"）

三个可编程指标（不靠第二个 LLM 评判，透明可复现）：
  hit_rate — Top-K 里至少命中一个相关文档的问题占比（覆盖"有没有找到"）
  recall@k — Top-K 覆盖的相关文档比例（覆盖"找全了没"，一条问题可有多相关文档）
  MRR      — 第一个相关文档排名的倒数（覆盖"排得靠不靠前"）

契约：evaluate(retrieve_fn, eval_set, k) -> dict
      retrieve_fn(query, k) -> list[(Chunk, score)]
      eval_set: list[{"q": str, "relevant": [文件名, ...]}]
"""
import json


def evaluate(retrieve_fn, eval_set: list, k: int = 5) -> dict:
    details = []
    for case in eval_set:
        q = case["q"]
        rel = set(case["relevant"])
        hits = retrieve_fn(q, k)
        sources = [c.metadata.get("source") for c, _ in hits]
        got = set(s for s in sources if s)

        hit = any(s in rel for s in got)
        # MRR：第一个相关文档的排名倒数
        rr = 0.0
        for i, s in enumerate(sources, start=1):
            if s in rel:
                rr = 1.0 / i
                break
        recall = len(rel & got) / len(rel) if rel else 0.0
        details.append({"q": q, "hit": hit, "rr": rr, "recall": recall, "got": sources})

    n = len(details) or 1
    return {
        "n": len(details),
        "hit_rate": sum(d["hit"] for d in details) / n,
        "mrr": sum(d["rr"] for d in details) / n,
        "recall": sum(d["recall"] for d in details) / n,
        "details": details,
    }


def load_eval_set(path) -> list:
    data = json.loads(open(path, encoding="utf-8").read())
    return data["cases"] if isinstance(data, dict) else data
