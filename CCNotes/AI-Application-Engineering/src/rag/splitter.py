"""splitter —— 文档切分（RAG 第一道杠杆）

为什么切分这么重要：
  向量检索是对「一块文本」算语义相似度。块太大 → 一块里混多个主题，
  检索命中但答案淹没在无关内容里；块太小 → 语义不完整，检索不到。
  切分粒度直接决定召回质量，是 RAG 调优的第一个旋钮。

三种策略（本模块都实现，便于对比）：
  - fixed     固定窗口：按字符数硬切，可设重叠。简单、可控，但会切断句子/段落。
  - recursive 递归切分：按分隔符优先级（段落→换行→句号→空格）尽量在语义边界切。
  - markdown  按标题切：以 Markdown 二级标题 (## ) 为界，每节一块。最贴合技术文档结构。

接口：split(text, strategy, size, overlap) -> list[Chunk]
"""
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """一个文本块 + 元数据（index 便于溯源到原文位置）。"""
    text: str
    metadata: dict = field(default_factory=dict)


def split(text: str, strategy: str = "recursive", size: int = 500, overlap: int = 50) -> list[Chunk]:
    """按指定策略把文本切成块。未知策略显式报错（不静默返回空）。"""
    if strategy == "fixed":
        return _fixed(text, size, overlap)
    if strategy == "recursive":
        return _recursive(text, size, overlap)
    if strategy == "markdown":
        return _markdown(text, size, overlap)
    raise ValueError(f"未知切分策略: {strategy!r}（可选: fixed / recursive / markdown）")


def _fixed(text: str, size: int, overlap: int) -> list[Chunk]:
    """固定窗口：每 size 字符一块，相邻块重叠 overlap 字符。"""
    step = max(size - overlap, 1)
    chunks: list[Chunk] = []
    for i in range(0, len(text), step):
        piece = text[i:i + size]
        if piece.strip():
            chunks.append(Chunk(piece, {"index": len(chunks), "strategy": "fixed", "start": i}))
        if i + size >= len(text):
            break
    return chunks


def _recursive(text: str, size: int, overlap: int) -> list[Chunk]:
    """递归切分：按分隔符优先级尝试在语义边界切。"""
    separators = ["\n\n", "\n", "。", "！", "？", " ", ""]
    pieces = _rec_split(text, separators, size)
    chunks: list[Chunk] = []
    for p in pieces:
        if p.strip():
            chunks.append(Chunk(p, {"index": len(chunks), "strategy": "recursive"}))
    return chunks


def _rec_split(text: str, separators: list[str], size: int) -> list[str]:
    """递归核心：用当前分隔符切，合并到不超过 size；单块仍超长则降级到下一级分隔符。"""
    if len(text) <= size:
        return [text]
    # 无分隔符可用（最后一级 ""）：硬切
    sep = separators[0]
    if sep == "":
        return [text[i:i + size] for i in range(0, len(text), size)]

    result: list[str] = []
    cur = ""
    for part in text.split(sep):
        candidate = (cur + sep + part) if cur else part
        if len(candidate) <= size:
            cur = candidate
        else:
            if cur:
                result.append(cur)
            if len(part) > size:
                result.extend(_rec_split(part, separators[1:], size))
                cur = ""
            else:
                cur = part
    if cur:
        result.append(cur)
    return result


def _markdown(text: str, size: int, overlap: int) -> list[Chunk]:
    """按 Markdown 二级标题 (## ) 切节；单节超 size 时用递归切分再切。"""
    # 前瞻分割：保留 "## " 在每段开头
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks: list[Chunk] = []
    for p in parts:
        p = p.strip()
        if not p or not p.startswith("## "):
            continue  # 跳过首个 ## 之前的引言部分
        if len(p) > size:
            for sub in _rec_split(p, ["\n\n", "\n", "。", " "], size):
                if sub.strip():
                    chunks.append(Chunk(sub, {"index": len(chunks), "strategy": "markdown"}))
        else:
            chunks.append(Chunk(p, {"index": len(chunks), "strategy": "markdown"}))
    return chunks
