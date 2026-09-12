"""embedder —— 文本向量化（本地 ONNX BGE，零 API 依赖）

为什么用本地 ONNX BGE：
  - DeepSeek 无 embedding API；chromadb 内置模型的 S3 下载国内不通
  - 旧项目已下载好 BGE-small-zh 的 ONNX 导出（中文语义模型），本模块**复用**它
    —— 不重新发明轮子，只把它包成干净的接口

embedding 内部就三步（没有魔法）：
  文本 → WordPiece 分词 → ONNX 前向 → 池化(BGE 取 [CLS]) + 归一化 → 向量

归一化后，向量的点积 == 余弦相似度（后续检索据此排序）。

模型路径：默认复用 `../LangChain-RAG-Agent/models/bge-small-zh`，
        可用环境变量 `DOCQA_MODEL_DIR` 覆盖。
"""
import functools
import os
import re
from pathlib import Path

import numpy as np
import onnxruntime as ort

# 默认模型目录：CCNotes/LangChain-RAG-Agent/models/bge-small-zh
DEFAULT_MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "LangChain-RAG-Agent" / "models" / "bge-small-zh"
)


class WordPieceTokenizer:
    """BERT 系 WordPiece 分词：中文逐字成 token，英文走子词最长匹配。"""

    def __init__(self, vocab_path):
        with open(vocab_path, encoding="utf-8") as f:
            vocab = [line.strip() for line in f]
        self.token2id = {t: i for i, t in enumerate(vocab)}
        self.unk = self.token2id["[UNK]"]
        self.cls = self.token2id["[CLS]"]
        self.sep = self.token2id["[SEP]"]

    def _tokenize_word(self, word: str) -> list:
        tokens, start = [], 0
        while start < len(word):
            end = len(word)
            matched = None
            while start < end:  # 最长匹配：整词优先，逐字缩短
                sub = word[start:end]
                if start > 0:
                    sub = "##" + sub  # 非首段加 ## 前缀（WordPiece 约定）
                if sub in self.token2id:
                    matched = sub
                    break
                end -= 1
            if matched is None:
                tokens.append(self.unk)
                start += 1
            else:
                tokens.append(self.token2id[matched])
                start = end
        return tokens

    def encode(self, text: str, max_len: int = 256):
        text = text.lower()
        # 中文逐字切开，其余按空白分段（简化版 BERT 预处理）
        words = re.findall(r"[一-鿿]|[^\s一-鿿]+", text)
        ids = [self.cls]
        for w in words:
            ids.extend(self._tokenize_word(w))
            if len(ids) >= max_len - 1:
                break
        ids = ids[: max_len - 1] + [self.sep]
        mask = np.ones(len(ids), dtype=np.int64)
        return np.array(ids, dtype=np.int64), mask


class Embedder:
    """本地 ONNX BGE 嵌入器。接口：embed(list[str]) -> list[list[float]]（已归一化）。"""

    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir or os.getenv("DOCQA_MODEL_DIR") or DEFAULT_MODEL_DIR)
        vocab = self.model_dir / "vocab.txt"
        model = self.model_dir / "model.onnx"
        if not vocab.exists() or not model.exists():
            raise FileNotFoundError(
                f"未找到 ONNX 模型：{self.model_dir}（需要 model.onnx + vocab.txt）"
            )
        self.tokenizer = WordPieceTokenizer(vocab)
        self.session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
        self.dim = None  # 首次 embed 后填充

    def _embed_one(self, text: str) -> list:
        ids, mask = self.tokenizer.encode(text)
        outs = self.session.run(
            None,
            {
                "input_ids": ids[None, :],
                "attention_mask": mask[None, :],
                "token_type_ids": np.zeros_like(ids)[None, :],
            },
        )
        hidden = outs[0][0]          # [seq, dim]
        pooled = hidden[0]           # BGE 取 [CLS] 向量
        pooled = pooled / np.linalg.norm(pooled)  # 归一化 → 点积即余弦
        return pooled.astype(np.float32).tolist()

    def embed(self, texts: list) -> list:
        vecs = [self._embed_one(t) for t in texts]
        if vecs and self.dim is None:
            self.dim = len(vecs[0])
        return vecs


@functools.lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """单例（ONNX 会话加载要 1-2 秒，全局复用以免每次重载）。"""
    return Embedder()
