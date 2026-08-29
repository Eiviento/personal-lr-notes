"""
Phase 4.3：人工审核环节 —— 草稿 → 机审 → 人确认 → 终稿
========================================================
人在回路（Human-in-the-loop）：LLM 产出不能直接发布，最后一关必须是人。

流程：
  协议草稿 JSON
    │
    ▼ 机审两层
    ├─ 代码校验（4.2 的死规则，精确）—— 类型/字节数不匹配必被揪出
    └─ LLM 评审（3.2 式开放问题，洞察）—— "预留位不够"这类
    │
    ▼ 人工逐条处理：[1]自动修正（有确定性 fix 的）/ [2]忽略 / [3]记录待办
    │
    ▼ 终稿 JSON + MD（附审核记录）+ 审核日志

设计决策：
  - 草稿与终稿分离：*_protocol.json 是草稿，确认后另存 *_final.*，可回退
  - 自动修正只给确定性 fix：代码校验"uint8 声明 2 字节"→ 一键改回 1；
    LLM 的"建议增加故障状态"没有程序化 fix，只能人判断
  - 全程留痕：每条问题的处理决定写入审核记录

用法：
  python phase4_3_human_review.py <协议草稿JSON路径>
  交互式输入；stdin 可管道喂入（批量/测试场景）
"""

import json
import sys
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from phase3_2_prompt_chain import llm
from phase4_2_tool_calling import FIXED_SIZE
from generate_protocol import render_markdown

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# ─── 机审第二层：LLM 评审（开放问题，洞察） ────────────
REVIEW_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是协议评审专家。审查字段表，输出 JSON：
{{"issues": [{{"severity":"warning|error","field":"字段名","message":"问题描述","suggestion":"建议"}}]}}
检查：类型/长度合理性、取值范围、边界与异常场景、扩展预留、命名一致性。
没有问题的检查项不要写进 issues。""",
        ),
        ("user", "字段表：\n{fields}"),
    ]
)
review_chain = REVIEW_PROMPT | llm | JsonOutputParser()


# ─── 机审第一层：代码校验（死规则，精确） ──────────────
def code_check(fields: list) -> list:
    issues = []
    for f in fields:
        name, ftype, length = f.get("name", ""), f.get("type", ""), f.get("length")
        if ftype == "string":
            continue
        expected = FIXED_SIZE.get(ftype)
        if expected is None:
            issues.append({"kind": "code", "severity": "error", "field": name,
                           "message": f"未知类型 {ftype}"})
        elif length != expected:
            issues.append({"kind": "code", "severity": "error", "field": name,
                           "message": f"{ftype} 应为 {expected} 字节，声明 {length}",
                           "fix": f"length → {expected}", "expected": expected})
    return issues


def human_review(issues: list) -> list:
    """逐条人工处理。stdin 可管道喂入；EOF 默认忽略"""
    decisions = []
    for i, issue in enumerate(issues, 1):
        fixable = "fix" in issue
        print(f"\n问题 {i}/{len(issues)} [{issue['kind']}] {issue.get('severity', 'error')}")
        print(f"  字段：{issue.get('field', 'N/A')}")
        print(f"  描述：{issue['message']}")
        if fixable:
            print(f"  自动修正：{issue['fix']}")
        prompt = "  处理：[1]自动修正  [2]忽略  [3]记录待办 → " if fixable \
            else "  处理：[2]忽略  [3]记录待办 → "
        try:
            choice = input(prompt).strip()
        except EOFError:
            choice = "2"
        if choice == "1" and fixable:
            decisions.append({**issue, "decision": "自动修正", "applied": True})
        elif choice == "3":
            decisions.append({**issue, "decision": "记录待办"})
        else:
            decisions.append({**issue, "decision": "忽略"})
    return decisions


def apply_fixes(fields: list, decisions: list) -> None:
    for d in decisions:
        if d.get("applied") and "expected" in d:
            for f in fields:
                if f.get("name") == d.get("field"):
                    f["length"] = d["expected"]


def main():
    if len(sys.argv) < 2:
        print("用法：python phase4_3_human_review.py <协议草稿JSON路径>")
        sys.exit(1)

    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    fields = data.get("fields", [])

    # ─── 演示：注入一处错误，让代码校验有活干 ──────────
    for f in fields:
        if isinstance(f.get("length"), int):
            f["length"] += 1
            print(f"⚠ 演示注入错误：{f['name']} 的 length 改成 {f['length']}\n")
            break

    print("⏳ 机审中（代码校验 + LLM 评审）...")
    issues = code_check(fields)
    llm_issues = review_chain.invoke({"fields": json.dumps(fields, ensure_ascii=False)}).get("issues", [])
    for it in llm_issues:
        it["kind"] = "llm"
    issues += llm_issues

    print(f"机审完成：代码校验 {sum(1 for i in issues if i['kind'] == 'code')} 条，"
          f"LLM 评审 {sum(1 for i in issues if i['kind'] == 'llm')} 条\n")

    # ─── 人工处理 ─────────────────────────────────────
    decisions = human_review(issues)
    try:
        confirm = input("\n生成终稿？[回车确认 / n 取消] → ").strip().lower()
    except EOFError:
        confirm = ""
    if confirm in ("n", "no"):
        print("❌ 已取消，草稿未动。")
        sys.exit(0)

    apply_fixes(fields, decisions)
    data["fields"] = fields

    stem = src.stem
    with open(OUTPUT_DIR / f"{stem}_final.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_DIR / f"{stem}_final.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(data, audit=decisions))
    with open(OUTPUT_DIR / f"{stem}_review_log.json", "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)

    fixed = sum(1 for d in decisions if d.get("applied"))
    todo = sum(1 for d in decisions if d["decision"] == "记录待办")
    print(f"\n✅ 终稿已生成：outputs/{stem}_final.json / _{stem}_final.md")
    print(f"   处理统计：自动修正 {fixed} 条，忽略 {len(decisions) - fixed - todo} 条，待办 {todo} 条")
    print(f"   审核记录：outputs/{stem}_review_log.json")


if __name__ == "__main__":
    main()
