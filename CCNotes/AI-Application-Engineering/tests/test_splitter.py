"""splitter 单元测试（TDD：先写测试定义行为契约，再实现）

splitter 是纯函数模块（无外部依赖），最适合 TDD 起步。
契约：split(text, strategy, size, overlap) -> list[Chunk]
"""
import pytest

from src.rag.splitter import Chunk, split


def test_fixed_window_chunk_count_and_size():
    """固定窗口：100 字符、窗口 30 无重叠 → 4 块（30/30/30/10）"""
    chunks = split("x" * 100, strategy="fixed", size=30, overlap=0)
    assert len(chunks) == 4
    assert all(isinstance(c, Chunk) for c in chunks)
    assert len(chunks[0].text) == 30
    assert len(chunks[-1].text) == 10


def test_fixed_window_overlap():
    """有重叠时，相邻块的重叠片段一致"""
    text = "abcdefghij" * 10  # 100 字符
    chunks = split(text, strategy="fixed", size=30, overlap=10)
    assert len(chunks) > 3
    # 第 2 块开头 10 字符 == 第 1 块结尾 10 字符（重叠）
    assert chunks[1].text[:10] == chunks[0].text[-10:]


def test_recursive_splits_on_separators():
    """递归：优先在段落分隔符处切，块长不超上限（容忍小幅溢出）"""
    text = "段落一。" * 20 + "\n\n" + "段落二。" * 20
    chunks = split(text, strategy="recursive", size=50, overlap=0)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 60 for c in chunks)


def test_markdown_heading_splits_by_section():
    """按 Markdown ## 标题切：每节一块（含标题）"""
    text = "# 大标题\n引言\n## 第一节\n内容A\n## 第二节\n内容B"
    chunks = split(text, strategy="markdown", size=1000)
    assert len(chunks) == 2
    assert "第一节" in chunks[0].text
    assert "第二节" in chunks[1].text


def test_metadata_records_index():
    """每个 chunk 带顺序索引，便于溯源"""
    chunks = split("x" * 60, strategy="fixed", size=30, overlap=0)
    assert [c.metadata["index"] for c in chunks] == [0, 1]


def test_unknown_strategy_raises():
    """未知策略应显式报错，不静默返回空"""
    with pytest.raises(ValueError):
        split("hello", strategy="nope", size=10)
