"""
Phase 3.2：Prompt 模板链 —— 需求分析 → 字段定义 → 约束规则 → 最终协议
========================================================================
为什么把"一段式大 Prompt"拆成链：
  1. 长任务塞一个 Prompt，模型容易丢步骤（比如忘了"留扩展位"这种小要求）
  2. 中间产物看不见，结果错了不知道哪一步出错
  3. 无法针对单步调整（分析可高温发散，字段定义要低温严谨）

链设计（每步职责单一）：
  需求文档
    │
    ▼ ① 需求分析   Prompt → StrOutputParser    关键需求点（纯文本）
    │
    ▼ ② 字段定义   Prompt → JsonOutputParser   字段表（JSON）
    │
    ▼ ③ 约束规则   Prompt → JsonOutputParser   范围/边界/异常/扩展（JSON）
    │
    ▼ ④ 最终协议   纯 Python 合并（不是 LLM！） 完整协议（JSON）

LCEL 知识点：
  - RunnablePassthrough.assign(键=子链)：每步往数据流挂一个键，下游自动可见
  - 合并是确定性操作用 Python 做：省一次调用，且模型不会改写/丢字段
    → 原则：LLM 做推理，Python 做拼装
"""

import json
import os
import sys
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from phase3_1_doc_input import read_doc  # 复用 3.1 的编码自适应读文件

# ─── 配置 ─────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# ═══ ① 需求分析：全文 → 关键需求点（纯文本） ═══════════
ANALYZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是通信协议需求分析师。阅读需求文档，提取与通信协议相关的关键需求点，
忽略无关内容（硬件选型、部门分工、背景介绍等）。
输出中文要点列表，每行一条，覆盖：通信内容、上报频率/触发条件、精度要求、特殊规则（告警阈值、扩展预留等）。""",
        ),
        ("user", "需求文档：\n\n{requirement}"),
    ]
)

# ═══ ② 字段定义：关键需求点 → 字段表（JSON） ═══════════
FIELDS_PROMPT = ChatPromptTemplate.from_messages(
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

Few-shot:
需求：设备定时上报位置（经纬度、海拔），每 5 秒一次
输出：{{"protocol_name":"设备位置上报协议","fields":[{{"name":"longitude","chinese_name":"经度","type":"float32","length":4,"unit":"度","range":"-180~180"}}],"timing":{{"report_interval":"5s","direction":"上行"}}}}""",
        ),
        ("user", "需求分析结果：\n\n{key_points}"),
    ]
)

# ═══ ③ 约束规则：字段表 + 需求点 → 约束/问题（JSON） ═══
RULES_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是协议评审专家。对照需求分析结果审查字段表，输出 JSON：
{{
  "constraints": [{{"field":"字段名","rule":"约束规则描述"}}],
  "issues": [{{"severity":"warning|error","field":"字段名","message":"问题描述"}}]
}}
检查项：字段是否遗漏、类型/长度是否合理、取值范围是否正确、
边界与异常场景（告警阈值、数值溢出）、扩展预留是否满足。
没有问题的检查项不要写进 issues。""",
        ),
        ("user", "需求分析结果：\n{key_points}\n\n字段表：\n{fields}"),
    ]
)

llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key-here"),
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.3,
    max_tokens=4096,
)

# ─── 三条子链 ─────────────────────────────────────────
analyze_chain = ANALYZE_PROMPT | llm | StrOutputParser()
fields_chain = FIELDS_PROMPT | llm | JsonOutputParser()
rules_chain = RULES_PROMPT | llm | JsonOutputParser()


def tap(name: str):
    """给中间环节加打印：输出中间产物后原样返回，不影响数据流"""
    def _tap(x):
        print(f"\n{'─'*60}")
        print(f"【中间产物 {name}】")
        if isinstance(x, str):
            print(x)
        else:
            print(json.dumps(x, ensure_ascii=False, indent=2, default=str))
        return x
    return RunnableLambda(_tap)


def merge_final(state: dict) -> dict:
    """④ 最终协议：纯 Python 合并。
    合并是确定性操作，不需要 LLM——省一次调用，且模型不会改写/丢字段。"""
    final = dict(state["fields"])
    final["constraints"] = state["checks"].get("constraints", [])
    issues = state["checks"].get("issues", [])
    if issues:
        final["issues"] = issues
    return final


# ─── 完整链：assign 逐步挂键，下游自动可见 ────────────
# 数据流：{"requirement": 文档} 进入，依次挂上 key_points / fields / checks
# 注意：挂的键名必须和下游 Prompt 的占位符一致，不一致当场报错（防漏配）
full_chain = (
    RunnablePassthrough.assign(key_points=analyze_chain | tap("① 需求分析"))
    | RunnablePassthrough.assign(fields=fields_chain | tap("② 字段定义"))
    | RunnablePassthrough.assign(checks=rules_chain | tap("③ 约束规则"))
    | RunnableLambda(merge_final)  # ④ Python 合并
)


def print_result(result: dict) -> None:
    """打印最终协议"""
    print(f"\n{'='*60}")
    print(f"协议名称：{result.get('protocol_name', 'N/A')}")
    print(f"描述：{result.get('description', 'N/A')}")
    if timing := result.get("timing"):
        print(f"上报频率：{timing.get('report_interval', 'N/A')}")
        print(f"通信方向：{timing.get('direction', 'N/A')}")
    print(f"{'='*60}\n")

    fields = result.get("fields", [])
    header = f"{'字段名':<20} {'中文名':<12} {'类型':<10} {'字节':<6} {'范围':<20}"
    print(header)
    print("-" * len(header))
    for f in fields:
        print(
            f"{f.get('name', ''):<20} "
            f"{f.get('chinese_name', ''):<12} "
            f"{f.get('type', ''):<10} "
            f"{str(f.get('length', '')):<6} "
            f"{f.get('range', ''):<20}"
        )

    constraints = result.get("constraints", [])
    print(f"\n{'─'*60}")
    print(f"【约束规则】{len(constraints)} 条")
    for c in constraints:
        print(f"  • {c.get('field', '?')}: {c.get('rule', '')}")

    issues = result.get("issues", [])
    if issues:
        print(f"\n【评审发现】{len(issues)} 条")
        for i in issues:
            print(f"  • [{i.get('severity', '?')}] {i.get('field', '?')}: {i.get('message', '')}")
    else:
        print("\n【评审发现】无问题")


def main():
    if len(sys.argv) < 2:
        print("用法：python phase3_2_prompt_chain.py <需求文档路径>")
        sys.exit(1)

    doc_path = sys.argv[1]
    doc = read_doc(doc_path)
    print(f"📄 文档：{doc_path}（{len(doc)} 字符）")
    print("⏳ 运行 4 步链：需求分析 → 字段定义 → 约束规则 → 最终协议")

    try:
        result = full_chain.invoke({"requirement": doc})
        print_result(result)

        out_path = OUTPUT_DIR / f"{Path(doc_path).stem}_protocol_full.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 完整协议 JSON 已保存至 {out_path}")

    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
