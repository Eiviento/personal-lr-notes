"""ask_local —— 本地端到端 RAG：一条命令跑完「检索 + 生成」，无需起服务

对比 scripts/ask.py（那个是 HTTP 客户端，要先起 uvicorn）：
本脚本把 api/main.py 的 _build_default() 那套组装逻辑搬到命令行里直接跑，
适合「我就想看看完整 RAG 出来的答案长什么样」的场景。

用法：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/ask_local.py "你的问题"
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/ask_local.py "你的问题" 5
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/ask_local.py --rebuild "你的问题"

参数：
  位置参数 1  问题（省略则用内置示例问题）
  位置参数 2  Top-K，默认 5
  --rebuild   强制重建向量索引（语料改动后用）

行为：
  - 检索阶段零成本，不需要 API key。
  - 生成阶段需要 DEEPSEEK_API_KEY（环境变量或 .env）。未配置时自动跳过生成，
    只打印检索候选并给出提示——脚本仍然可用（不会崩）。
  - 索引落在 outputs/chroma_db_local（outputs/ 已 gitignore），首次运行构建、
    之后复用；不触碰 api/main.py 用的 data/chroma_db_api。
"""
import shutil
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.bm25 import BM25Index            # noqa: E402
from src.rag.embedder import get_embedder     # noqa: E402
from src.rag.retriever import HybridRetriever  # noqa: E402
from src.rag.splitter import split            # noqa: E402
from src.rag.store import VectorStore         # noqa: E402

DOCS_DIR = ROOT / "data" / "documents"
DB_DIR = ROOT / "outputs" / "chroma_db_local"
DB_NAME = "docqa_local"

DEFAULT_QUESTION = "混合检索是怎么融合关键词和向量的"


def load_chunks(strategy: str = "markdown", size: int = 500) -> list:
    """切分语料 → 文本块列表（与 api/main.py 的 _build_index 同一套切法）。"""
    chunks = []
    for md in sorted(DOCS_DIR.glob("*.md")):
        for c in split(md.read_text(encoding="utf-8"), strategy=strategy, size=size):
            c.metadata["source"] = md.name
            c.metadata["id"] = f"{md.name}-{c.metadata['index']}"
            chunks.append(c)
    return chunks


def build_store(chunks: list, rebuild: bool = False) -> VectorStore:
    """建/复用向量库。rebuild=True 先清空自己的库（不碰 api 的库）。"""
    if rebuild and DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    store = VectorStore(path=DB_DIR, embedder=get_embedder(), name=DB_NAME)
    if store.count() == 0:
        t0 = time.time()
        added = store.add(chunks)
        print(f"[索引] 新建 {added} 块，耗时 {time.time() - t0:.1f}s", file=sys.stderr)
    else:
        print(f"[索引] 复用已有库 {store.count()} 块（--rebuild 可重建）", file=sys.stderr)
    return store


def main() -> int:
    raw = sys.argv[1:]
    flags = {a for a in raw if a.startswith("--")}
    pos = [a for a in raw if not a.startswith("--")]

    question = pos[0] if pos else DEFAULT_QUESTION
    k = int(pos[1]) if len(pos) > 1 else 5

    print(f"问：{question}\n")

    chunks = load_chunks()
    store = build_store(chunks, rebuild="--rebuild" in flags)
    retriever = HybridRetriever(store, BM25Index(chunks))
    hits = retriever.retrieve(question, k)

    print(f"检索：命中 {len(hits)} 个候选（混合检索 RRF）")
    for i, (c, s) in enumerate(hits, 1):
        src = c.metadata.get("source", "?")
        snippet = c.text.replace("\n", " ")[:88]
        print(f"  [{i}] {s:.4f}  {src}")
        print(f"       {snippet}…")

    print()
    try:
        from src.rag.generator import Generator
        gen = Generator()
    except RuntimeError as e:
        print(f"[跳过生成] {e}")
        print("→ 检索链路已完成；配置 DEEPSEEK_API_KEY 后重跑即可看到答案。")
        return 0

    try:
        out = gen.generate(question, hits)
    except Exception as e:
        print(f"[生成失败] {type(e).__name__}: {str(e)[:300]}")
        print("→ 检索链路已完成（上方即检索结果）。生成失败常见原因：key 失效 / 网络不通 / 余额不足。")
        return 0

    print("答：", out["answer"])
    print("\n引用来源：", out["sources"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
