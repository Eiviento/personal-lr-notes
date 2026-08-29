"""
Phase 4.1：RAG 基础 —— 向量库存历史协议模板，检索后注入 Prompt
================================================================
解决两个问题：
  1. 上下文窗口有限 —— 只检索相关片段注入，不塞全文（3.1 的截断是权宜之计）
  2. Few-shot 素材会变多 —— 历史协议模板存向量库，按语义检索最相关的当参考

RAG 三件套：
  Retrieval 检索 —— 向量库相似度检索
  Augmented 增强 —— 检索结果拼进 Prompt
  Generation 生成 —— 链照常运行，只是上下文更"懂行"

Embedding 原理：文本 → 向量（语义相近 → 距离近）。
"设备位置上报"和"GPS 经纬度"没有共同关键词但语义相关——关键词搜索做不到。

环境说明：DeepSeek 无 embedding API；chromadb 内置 ONNX 模型的 S3 下载国内不通，
故从 hf-mirror 下载 BGE-small-zh-v1.5（中文语义模型，Xenova 的 ONNX 导出）到
models/bge-small-zh/，用 onnxruntime 本地推理（自定义 EmbeddingFunction，完全离线）。
实测 MiniLM（英文模型）对中文检索排序错乱 → 换 BGE 中文模型解决，
这就是"换 embedding 模型不改管道代码"的活例子。

用法：
  python phase4_1_rag.py build              # 把 inputs/templates/*.md 写入向量库
  python phase4_1_rag.py query "<需求描述>"   # 演示检索：看什么模板会被命中
  python phase4_1_rag.py run <需求文档>       # 对比：无 RAG vs 有 RAG 的协议生成
"""

import functools
import json
import os
import re
import sys
from pathlib import Path

import chromadb
import numpy as np
import onnxruntime as ort
from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import analyze_chain, rules_chain, merge_final, llm
from phase3_3_batch_stream import clean_chain  # 无 RAG 基线（3.4 同款）

# 资源与输出目录以脚本文件位置为基准：在任何目录下运行都能找到
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models/bge-small-zh"
DB_DIR = BASE_DIR / "rag_db"
TEMPLATES_DIR = BASE_DIR / "inputs/templates"
OUTPUT_DIR = BASE_DIR / "outputs"

# ═══════════════════════════════════════════════════════
# 1. 本地 Embedding 函数 —— embedding 内部就三步，没有魔法
# ═══════════════════════════════════════════════════════
class WordPieceTokenizer:
    """BERT 系模型的 WordPiece 分词：中文逐字成 token，英文走子词最长匹配"""

    def __init__(self, vocab_path: str):
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


class LocalBertEmbedding(EmbeddingFunction):
    """本地 ONNX 推理的 embedding 函数（实现 chromadb 的 EmbeddingFunction 接口）
    三步：WordPiece 分词 → ONNX 推理 → 池化 + 归一化
    pooling="cls"：取 [CLS] 向量（BGE 系列用）；pooling="mean"：全 token 平均（MiniLM 用）"""

    def __init__(self, model_dir: str, pooling: str = "cls"):
        self.pooling = pooling
        self.tokenizer = WordPieceTokenizer(os.path.join(model_dir, "vocab.txt"))
        self.session = ort.InferenceSession(
            os.path.join(model_dir, "model.onnx"), providers=["CPUExecutionProvider"]
        )

    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            ids, mask = self.tokenizer.encode(text)
            outs = self.session.run(
                None,
                {
                    "input_ids": ids[None, :],
                    "attention_mask": mask[None, :],
                    "token_type_ids": np.zeros_like(ids)[None, :],
                },
            )
            hidden = outs[0][0]  # [seq, dim]
            if self.pooling == "cls":
                pooled = hidden[0]  # BGE：取 [CLS] 向量
            else:
                pooled = (hidden * mask[:, None]).sum(0) / mask.sum()  # MiniLM：平均池化
            pooled = pooled / np.linalg.norm(pooled)  # 归一化 → 余弦相似度
            vectors.append(pooled.astype(np.float32))
        return vectors


# ═══════════════════════════════════════════════════════
# 2. 向量库：入库 + 检索
# ═══════════════════════════════════════════════════════
def get_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    # metadata 只在首次创建时生效：显式指定余弦空间（chroma 默认是 l2）
    return client.get_or_create_collection(
        "protocol_templates",
        embedding_function=LocalBertEmbedding(MODEL_DIR, pooling="cls"),
        metadata={"hnsw:space": "cosine"},
    )


@functools.lru_cache(maxsize=1)
def get_collection_cached():
    """检索用缓存版：ONNX 会话加载要 1-2 秒，避免每次检索重载（UI 里尤其重要）"""
    return get_collection()


def build_db():
    col = get_collection()
    count = 0
    for md in sorted(Path(TEMPLATES_DIR).glob("*.md")):
        text = md.read_text(encoding="utf-8")
        title = text.split("\n", 1)[0].lstrip("# ").strip()
        col.upsert(
            documents=[text],
            metadatas=[{"title": title, "source": md.name}],
            ids=[md.stem],
        )
        count += 1
    print(f"✅ 向量库已写入 {count} 份模板：{DB_DIR}/")
    print(f"   以后拿到真实协议模板，放进 {TEMPLATES_DIR}/ 再 build 一次即可")


def retrieve(query: str, k: int = 2) -> str:
    """按语义检索最相似的 k 份模板，拼成一段上下文文本"""
    hits = get_collection_cached().query(query_texts=[query], n_results=k)
    parts = []
    for doc, meta, dist in zip(hits["documents"][0], hits["metadatas"][0], hits["distances"][0]):
        parts.append(f"【{meta['title']}】（距离 {dist:.3f}，越小越相似）\n{doc}")
    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════
# 3. RAG 链：字段定义 Prompt 增加"历史模板"上下文
# ═══════════════════════════════════════════════════════
FIELDS_PROMPT_RAG = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是通信协议工程师。根据需求分析结果设计协议字段表。
严格输出 JSON，不要包含其他内容：
{{
  "protocol_name": "协议名称",
  "description": "协议用途",
  "fields": [{{"name":"...","chinese_name":"...","type":"...","length":字节数,"unit":"...","range":"...","description":"..."}}],
  "timing": {{"report_interval":"...","direction":"上行/下行/双向"}}
}}

## 参考：公司历史协议模板（帧结构、命名、类型风格请与其保持一致）
{retrieved}""",
        ),
        ("user", "需求分析结果：\n\n{key_points}"),
    ]
)

rag_fields_chain = FIELDS_PROMPT_RAG | llm | JsonOutputParser()

# 完整 RAG 链 = 3.4 的链 + 开头多一个检索步骤（零件复用，只换字段定义这环）
rag_chain = (
    RunnablePassthrough.assign(retrieved=RunnableLambda(lambda s: retrieve(s["requirement"])))
    | RunnablePassthrough.assign(key_points=analyze_chain)
    | RunnablePassthrough.assign(fields=rag_fields_chain)
    | RunnablePassthrough.assign(checks=rules_chain)
    | RunnableLambda(merge_final)
)


def compare(requirement: str, stem: str) -> None:
    """同一需求跑两条链，对比字段差异"""
    print("=" * 60)
    print("【无 RAG】3.4 原链（固定 Few-shot GPS 例子）")
    plain = clean_chain.invoke({"requirement": requirement})
    print(f"  {plain.get('protocol_name')}")
    print("  字段：" + " / ".join(f"{f.get('name')}:{f.get('type')}" for f in plain.get("fields", [])))

    print("\n【有 RAG】4.1 链（检索历史模板注入）")
    raged = rag_chain.invoke({"requirement": requirement})
    print(f"  {raged.get('protocol_name')}")
    print("  字段：" + " / ".join(f"{f.get('name')}:{f.get('type')}" for f in raged.get("fields", [])))

    with open(OUTPUT_DIR / f"rag_{stem}_protocol.json", "w", encoding="utf-8") as f:
        json.dump(raged, f, ensure_ascii=False, indent=2)
    print(f"\n✅ RAG 结果已保存至 outputs/rag_{stem}_protocol.json")


def main():
    if len(sys.argv) < 2:
        print("用法：")
        print("  python phase4_1_rag.py build")
        print('  python phase4_1_rag.py query "<需求描述>"')
        print("  python phase4_1_rag.py run <需求文档>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        build_db()

    elif cmd == "query" and len(sys.argv) >= 3:
        query_text = sys.argv[2]
        print(f"🔍 检索：{query_text}\n")
        print(retrieve(query_text))

    elif cmd == "run" and len(sys.argv) >= 3:
        doc = read_doc(sys.argv[2])
        compare(doc, Path(sys.argv[2]).stem)

    else:
        print(f"❌ 未知命令或参数不足：{sys.argv[1:]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
