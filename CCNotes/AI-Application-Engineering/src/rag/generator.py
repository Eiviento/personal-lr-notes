"""generator —— 基于检索结果生成答案（RAG 的 G：Generation）

RAG 的最后一环：把检索到的块作为「参考资料」拼进 prompt，让模型**只依据资料回答**。
关键纪律（继承前项目的防幻觉原则）：
  - 资料不足时如实说「资料里没有」，绝不凭印象编造
  - 答案给出引用来源（哪些文档支撑了这句）

LLM：DeepSeek（OpenAI 兼容）。key 从环境变量或 .env 读取（脚本用 python-dotenv 加载）。
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parent.parent.parent  # AI-Application-Engineering/

SYSTEM_PROMPT = """你是技术文档助手。规则：
- 只根据【参考资料】回答，不要编造资料里没有的内容
- 资料不足以回答时，如实说「资料中没有提到」，不要凭印象补充
- 回答用中文，简洁，需要时列要点
- 末尾用一行列出引用的文档来源"""


def _load_env():
    """加载 .env：优先本项目，其次复用兄弟项目的 key（脚本行为，不读内容）。"""
    for p in [
        ROOT / ".env",
        ROOT.parent / "Project-Langchain" / ".env",
        ROOT.parent / "LangChain-RAG-Agent" / ".env",
    ]:
        if p.exists():
            load_dotenv(p)
            return


class Generator:
    def __init__(self, llm=None):
        self.llm = llm if llm is not None else self._default_llm()

    @staticmethod
    def _default_llm():
        _load_env()
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("未找到 DEEPSEEK_API_KEY：请在 .env 配置（见 .env.example）")
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=key,
            base_url="https://api.deepseek.com",
            temperature=0.3,
            max_tokens=1024,
        )

    def generate(self, query: str, hits: list) -> dict:
        """hits: list[(Chunk, score)] → 返回 {answer, sources}"""
        context = "\n\n".join(
            f"[{i + 1}] 来源：{c.metadata.get('source', '?')}\n{c.text}"
            for i, (c, _) in enumerate(hits)
        )
        msgs = [
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(f"【参考资料】\n{context}\n\n【问题】{query}"),
        ]
        resp = self.llm.invoke(msgs)
        return {
            "answer": str(resp.content),
            "sources": [c.metadata.get("source") for c, _ in hits],
        }
