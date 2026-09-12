"""api 单元测试（TDD，零 API）

用 FastAPI TestClient + 假检索器/假生成器，验证 HTTP 层（路由/校验/序列化）不崩，
不调真实 LLM。契约：
  GET  /health        -> {"status": "ok"}
  POST /qa {question} -> {"answer", "sources"}
  空问题 -> 422（Pydantic 校验）
"""
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.rag.splitter import Chunk


class FakeRetriever:
    def retrieve(self, query, k=5):
        return [(Chunk("示例内容", {"source": "demo.md"}), 0.9)]


class FakeGenerator:
    def generate(self, query, hits):
        return {"answer": "这是测试答案", "sources": [c.metadata["source"] for c, _ in hits]}


def _client():
    return TestClient(create_app(retriever=FakeRetriever(), generator=FakeGenerator()))


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_qa_returns_answer_and_sources():
    r = _client().post("/qa", json={"question": "什么是混合检索"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "这是测试答案"
    assert body["sources"] == ["demo.md"]


def test_qa_rejects_empty_question():
    r = _client().post("/qa", json={"question": ""})
    assert r.status_code == 422  # Pydantic 校验：问题不能为空
