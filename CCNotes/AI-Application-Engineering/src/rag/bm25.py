"""bm25 —— 关键词检索（补向量检索的短板）

为什么需要它（混合检索的另一半）：
  向量检索擅长「语义相近但用词不同」，却容易漏掉**专有名词/编号/精确术语**
  （比如订单号 SO-1003、函数名 create_agent）——这些在语义空间里不突出。
  BM25 是经典的关键词打分（词频 + 逆文档频率），正好补这一块。两者融合 = 混合检索。

分词：教学用「中文单字 + 英文/数字词」的轻量切分（够用）；生产可换 jieba 等。

接口：BM25Index(chunks).query(text, k) -> list[(Chunk, score)]（降序，只留命中>0）
"""
import re

from rank_bm25 import BM25Plus

from .splitter import Chunk


def tokenize(text: str) -> list:
    """轻量分词：英文/数字/连字符词 + 中文单字。"""
    tokens = re.findall(r"[a-z0-9\-_]+", text.lower())
    tokens += re.findall(r"[一-鿿]", text)
    return tokens


class BM25Index:
    def __init__(self, chunks: list):
        self.chunks = list(chunks)
        self._corpus = [tokenize(c.text) for c in self.chunks]
        # 用 BM25Plus 而非 BM25Okapi：Okapi 的 IDF 在小语料上可能为 0/负
        # （词恰好出现在一半文档时会失真），BM25Plus 的 IDF 恒非负，更稳。
        self._bm25 = BM25Plus(self._corpus) if self._corpus else None

    def query(self, text: str, k: int = 5) -> list:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(tokenize(text))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked[:k]:
            if scores[i] > 0:
                out.append((self.chunks[i], float(scores[i])))
        return out
