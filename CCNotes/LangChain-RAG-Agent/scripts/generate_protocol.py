"""
Phase 3.4 验收：完整跑通"输入需求文档 → 输出协议规范"
======================================================
Phase 3 最终交付物。把 3.1（读文件）+ 3.2（四步链）+ 3.3（组装）串成单一入口。

用法：
  python generate_protocol.py <需求文档1> [<需求文档2> ...]

输出（outputs/ 下，每份输入文档两个文件）：
  <名称>_protocol.json   机器可读的结构化协议（给程序用）
  <名称>_protocol.md     人可读的协议规范文档（给同事看）

设计要点：
  - JSON 是"数据"，Markdown 是"呈现"——两者分离。
    LLM 负责推理（JSON），渲染用纯 Python（确定性、可改样式）。
    → 3.2 的原则"LLM 做推理，Python 做拼装"在输出端同样成立。
  - 单文件走 invoke，多文件走 batch（3.3）。
"""

import json
import sys
from pathlib import Path

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import analyze_chain, fields_chain, rules_chain, merge_final

# ─── 组装（同 3.3 的干净版链） ────────────────────────
chain = (
    RunnablePassthrough.assign(key_points=analyze_chain)
    | RunnablePassthrough.assign(fields=fields_chain)
    | RunnablePassthrough.assign(checks=rules_chain)
    | RunnableLambda(merge_final)
)


def render_markdown(protocol: dict, audit: list = None) -> str:
    """纯 Python 把协议 dict 渲染成 Markdown 规范文档（确定性，样式可改）
    audit: 审核记录列表（4.3 人工审核后传入），非 None 表示已过人工审核"""
    lines = [f"# {protocol.get('protocol_name', '协议规范')}", ""]

    if desc := protocol.get("description"):
        lines += [f"> {desc}", ""]

    timing = protocol.get("timing", {})
    lines += [
        "## 基本信息",
        "",
        f"- 上报频率：{timing.get('report_interval', 'N/A')}",
        f"- 通信方向：{timing.get('direction', 'N/A')}",
        "",
        "## 字段定义",
        "",
        "| 字段名 | 中文名 | 类型 | 字节 | 单位 | 范围 | 说明 |",
        "|--------|--------|------|------|------|------|------|",
    ]
    for f in protocol.get("fields", []):
        lines.append(
            f"| {f.get('name', '')} | {f.get('chinese_name', '')} | {f.get('type', '')} "
            f"| {f.get('length', '')} | {f.get('unit', '')} | {f.get('range', '')} | {f.get('description', '')} |"
        )

    constraints = protocol.get("constraints", [])
    if constraints:
        lines += ["", "## 约束规则", ""]
        for i, c in enumerate(constraints, 1):
            lines.append(f"{i}. **{c.get('field', '?')}**：{c.get('rule', '')}")

    issues = protocol.get("issues", [])
    if issues:
        lines += ["", "## 评审发现（待人工确认）", ""]
        for i in issues:
            lines.append(f"- [{i.get('severity', '?')}] **{i.get('field', '?')}**：{i.get('message', '')}")

    if audit is not None:
        lines += ["", "## 审核记录", "", "| 字段 | 问题 | 处理 |", "|------|------|------|"]
        for d in audit:
            lines.append(f"| {d.get('field', 'N/A')} | {d.get('message', '')} | {d.get('decision', '')} |")

    footer = "*本文档由 generate_protocol.py 自动生成"
    footer += "，已通过人工审核。*" if audit is not None else "，请人工审核后发布。*"
    lines += ["", "---", footer]
    return "\n".join(lines)


def main():
    paths = sys.argv[1:]
    if not paths:
        print("用法：python generate_protocol.py <需求文档1> [<需求文档2> ...]")
        sys.exit(1)

    try:
        docs = [read_doc(p) for p in paths]
        inputs = [{"requirement": d} for d in docs]
        print(f"⏳ 处理 {len(paths)} 份需求文档（{'batch 并发' if len(paths) > 1 else 'invoke'}）...\n")
        results = chain.batch(inputs) if len(inputs) > 1 else [chain.invoke(inputs[0])]

        for path, result in zip(paths, results):
            stem = Path(path).stem
            json_out = OUTPUT_DIR / f"{stem}_protocol.json"
            md_out = OUTPUT_DIR / f"{stem}_protocol.md"
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            with open(md_out, "w", encoding="utf-8") as f:
                f.write(render_markdown(result))
            print(f"  ✓ {path}")
            print(f"      → {json_out}（结构化 JSON）")
            print(f"      → {md_out}（Markdown 规范文档）")

    except FileNotFoundError as e:
        print(f"❌ 文件不存在：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理失败：{e}")
        sys.exit(1)

    print(f"\n✅ Phase 3 验收通过：需求文档 → 协议规范，完整跑通。")


if __name__ == "__main__":
    main()
