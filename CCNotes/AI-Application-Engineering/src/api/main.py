"""api.main —— FastAPI 服务层（把 RAG 链路暴露为 HTTP）

三个接口：
  GET  /health         健康检查
  POST /qa             问答：{question, k} -> {answer, sources}
  POST /ingest         重建索引（把 data/documents 重新切分/向量化入库）

设计：create_app(retriever, generator) 支持注入——测试用假件（零 API），
生产用 --factory 走 _build_default()（真 ONNX + DeepSeek）。
只做编排与校验，检索/生成逻辑在 src/rag/。

启动：uvicorn src.api.main:create_app --factory --port 8000
"""
import shutil
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent.parent  # AI-Application-Engineering/
DOCS_DIR = ROOT / "data" / "documents"
DB_DIR = ROOT / "data" / "chroma_db_api"


class QARequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题，不能为空")
    k: int = Field(5, ge=1, le=20, description="检索返回的候选块数")


class QAResponse(BaseModel):
    answer: str
    sources: list


def create_app(retriever=None, generator=None) -> FastAPI:
    """创建 FastAPI 应用；retriever/generator 为 None 时构建真实依赖。"""
    if retriever is None or generator is None:
        real_r, real_g = _build_default()
        retriever = retriever or real_r
        generator = generator or real_g

    app = FastAPI(title="DocQA", description="技术文档问答服务（RAG）")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/qa", response_model=QAResponse)
    def qa(req: QARequest):
        hits = retriever.retrieve(req.question, req.k)
        out = generator.generate(req.question, hits)
        return QAResponse(answer=out["answer"], sources=out["sources"])

    @app.post("/ingest")
    def ingest():
        _build_index()  # 重建索引（会清空旧库）
        return {"status": "rebuilt"}

    return app


def _build_index():
    """切分语料 → 嵌入 → 写入向量库。返回 (store, all_chunks)。"""
    from ..rag.embedder import get_embedder
    from ..rag.splitter import split
    from ..rag.store import VectorStore

    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    store = VectorStore(path=DB_DIR, embedder=get_embedder(), name="docqa_api")
    all_chunks = []
    for md in sorted(DOCS_DIR.glob("*.md")):
        chunks = split(md.read_text(encoding="utf-8"), strategy="markdown", size=500)
        for c in chunks:
            c.metadata["source"] = md.name
            c.metadata["id"] = f"{md.name}-{c.metadata['index']}"
        all_chunks.extend(chunks)
        store.add(chunks)
    return store, all_chunks


def _build_default():
    """构建真实依赖：混合检索器 + DeepSeek 生成器。"""
    from ..rag.bm25 import BM25Index
    from ..rag.generator import Generator
    from ..rag.retriever import HybridRetriever

    store, all_chunks = _build_index()
    retriever = HybridRetriever(store, BM25Index(all_chunks))
    return retriever, Generator()
