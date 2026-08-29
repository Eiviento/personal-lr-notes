"""
Phase 2.3：StrOutputParser / JsonOutputParser
==============================================
模型返回的是 AIMessage 对象（不是字符串），Parser 负责把它转成你要的类型：

  无 Parser          → AIMessage 对象（要自己取 .content，原始文本）
  StrOutputParser()  → str 纯字符串（写文档、概述、拼接文本）
  JsonOutputParser() → dict（程序要拿字段做计算，2.1/2.2 一直在用）

数据流示意：
  需求 "设备每 10 分钟上报心跳，开机上报固件版本"
    │
    ├─► prompt | llm                     → AIMessage  ← 路的起点
    ├─► prompt | llm | StrOutputParser   → str        ← 要文本时
    └─► prompt | llm | JsonOutputParser  → dict       ← 要结构化数据时
"""

import json
import sys
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# ─── 配置 ─────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
# API Key 从环境变量 DEEPSEEK_API_KEY 读取（见 main()）
# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# ═══════════════════════════════════════════════════════
# 1. 无 Parser：看看模型到底返回什么
# ═══════════════════════════════════════════════════════
SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一位通信协议工程师。用两三句话概述用户需求的协议要点，纯文本输出。",
        ),
        ("user", "{requirement}"),
    ]
)

# ═══════════════════════════════════════════════════════
# 2. JSON 输出链（同 2.1 的字段表，这里用精简版 Prompt）
# ═══════════════════════════════════════════════════════
JSON_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
你是通信协议工程师。分析需求，严格输出 JSON，不要包含其他内容：
{{
  "fields": [{{"name":"字段名","type":"类型","length":字节数,"description":"说明"}}],
  "timing": {{"interval":"上报周期","direction":"上行/下行"}}
}}""",
        ),
        ("user", "需求：{requirement}"),
    ]
)


def main():
    import os

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请先设置环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=4096,
    )

    requirement = sys.argv[1] if len(sys.argv) > 1 else "设备每 10 分钟上报一次心跳，开机时上报固件版本和型号"
    print(f"📋 需求：{requirement}\n")

    # ─── 路 1：无 Parser ───────────────────────────────
    raw = (SUMMARY_PROMPT | llm).invoke({"requirement": requirement})
    print("=" * 60)
    print("【路 1：无 Parser】")
    print(f"  返回类型：{type(raw).__name__}")
    print(f"  .content 前 60 字：{raw.content[:60]}...")
    print("  → 是对象不是字符串，直接 print 或写文件都会很别扭")

    # ─── 路 2：StrOutputParser ─────────────────────────
    summary_chain = SUMMARY_PROMPT | llm | StrOutputParser()
    summary = summary_chain.invoke({"requirement": requirement})
    print("=" * 60)
    print("【路 2：StrOutputParser】")
    print(f"  返回类型：{type(summary).__name__}（isinstance str: {isinstance(summary, str)}）")
    print(f"  内容：\n    {summary}")
    print("  → 纯字符串，可直接 print / 写入 .md / 拼接到其他 Prompt")

    # ─── 路 3：JsonOutputParser ────────────────────────
    json_chain = JSON_PROMPT | llm | JsonOutputParser()
    result = json_chain.invoke({"requirement": requirement})
    print("=" * 60)
    print("【路 3：JsonOutputParser】")
    print(f"  返回类型：{type(result).__name__}")
    print(f"  字段数：{len(result.get('fields', []))}")
    for f in result.get("fields", []):
        print(f"    {f.get('name', '?'):<16} {f.get('type', '?'):<10} {f.get('length', '?'):<4}字节  {f.get('description', '')}")
    print("  → 直接是 dict，result['fields'] 随便拿")

    # ─── 保存 ──────────────────────────────────────────
    with open(OUTPUT_DIR / "protocol_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    with open(OUTPUT_DIR / "protocol_output_parser.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("=" * 60)
    print("✅ 已保存：protocol_summary.txt（纯文本）、protocol_output_parser.json（结构化）")


if __name__ == "__main__":
    main()
