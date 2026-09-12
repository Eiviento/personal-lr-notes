"""Wave 0 · 语料准备：把两个旧项目的 lessons 技术文档复制到 data/documents/

为什么用这些文档当知识库：
  - 真实技术文档（LangChain/LangGraph 的概念、API、机制），术语密集、篇幅够长
    —— 足够体现「切分粒度 / 检索策略」的差异（太小的语料测不出区别）
  - 是用户自己整理过的内容，能判断 RAG 答案的对错
  - 本地已有，不依赖联网（GitHub / 官方文档站直连超时）

命名：加来源前缀（pl_ / lc_）避免两个 lessons 目录里的同名文件冲突。
幂等：重复运行结果一致（覆盖同名前缀文件）。

运行：PYTHONIOENCODING=utf-8 <agent_env python> scripts/prepare_corpus.py
"""
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 项目根 = 本脚本上一级（AI-Application-Engineering/）
ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "documents"

# (前缀, 源目录)：前缀避免同名冲突
SOURCES = [
    ("pl", ROOT.parent / "Project-Langchain" / "lessons"),
    ("lc", ROOT.parent / "LangChain-RAG-Agent" / "lessons"),
]


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for prefix, src in SOURCES:
        if not src.exists():
            print(f"[警告] 源目录不存在，跳过：{src}")
            continue
        mds = sorted(src.glob("*.md"))
        for md in mds:
            dst = DOCS_DIR / f"{prefix}_{md.name}"
            shutil.copy2(md, dst)
            count += 1
        print(f"  {prefix}: {len(mds)} 篇 ← {src}")
    print(f"✅ 语料复制完成：{count} 篇 → {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
