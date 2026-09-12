"""DocQA · API 模块包

FastAPI 服务层：把 RAG 链路暴露为 HTTP 接口（/qa、/ingest、/health）。
只做编排与请求校验，不含检索逻辑（业务在 src/rag/）。
"""
