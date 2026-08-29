"""
Phase 4.2：Function Calling / Tool Use —— 让模型调用你的函数
==============================================================
原理一句话：模型不执行代码，它只"点菜"——输出结构化调用请求
（函数名 + 参数 JSON），真正执行的是你的代码，执行结果回传给模型。

流程：
  你的消息 + 函数签名(JSON Schema) → 模型
  模型 → "我要调用 validate_field_type(field_name=..., length=...)"
  代码 → 执行函数 → 结果文本回传（ToolMessage）
  模型 → 继续推理 → 最终答复（可能再次调用工具，循环直到不调用）

什么时候用工具：需要精确性的环节。"uint8 占几字节"是死规则——
让模型背会背错，让代码算永不出错。模型负责"该不该校验/结果怎么解读"，
代码负责执行。工具参数受 JSON Schema 硬约束（1.3 说的"最可靠的结构化输出"）。

用法：
  python phase4_2_tool_calling.py <协议JSON路径>
  演示会人为注入一处字段错误，看模型+工具能否揪出来。
"""

import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from phase3_2_prompt_chain import llm

# ═══ 1. 定义工具：普通 Python 函数 + 类型注解 + 文档字符串 ═══
# 类型注解自动变成 JSON Schema 传给模型，docstring 告诉模型什么时候用
FIXED_SIZE = {
    "uint8": 1, "int8": 1, "bool": 1,
    "uint16": 2, "int16": 2,
    "uint32": 4, "int32": 4,
    "float32": 4, "float64": 8,
}


@tool
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    """校验协议字段的类型与字节数是否匹配。参数：field_name 字段名，
    field_type 数据类型（uint8/int16/float32/string 等），length 声明的字节数。"""
    if field_type == "string":
        return f"{field_name}: string 是变长类型，声明 {length} 字节 → 合法（约定为最大长度）"
    expected = FIXED_SIZE.get(field_type)
    if expected is None:
        return f"{field_name}: 未知类型 {field_type} → 不合法"
    if expected == length:
        return f"{field_name}: {field_type} 标准 {expected} 字节，声明 {length} → 合法"
    return f"{field_name}: {field_type} 应为 {expected} 字节，实际声明 {length} → 不合法"


FUNC_MAP = {"validate_field_type": validate_field_type}

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# ═══ 2. 绑定工具：llm.bind_tools 把函数签名发给模型 ═══════
llm_with_tools = llm.bind_tools([validate_field_type])


def run_tool_loop(messages: list):
    """手写工具循环：模型点菜 → 代码上菜 → 模型继续，直到模型不再调用工具"""
    response = llm_with_tools.invoke(messages)
    rounds = 0
    while response.tool_calls and rounds < 5:  # 上限防死循环
        tool_msgs = []
        print(f"\n模型发起 {len(response.tool_calls)} 次工具调用：")
        for tc in response.tool_calls:
            name, args = tc["name"], tc["args"]
            result = str(FUNC_MAP[name].invoke(args))  # ← 真正执行的是你的代码
            print(f"  🔧 {name}({args})")
            print(f"     → {result}")
            tool_msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        messages = messages + [response] + tool_msgs
        response = llm_with_tools.invoke(messages)
        rounds += 1
    return response.content


def main():
    if len(sys.argv) < 2:
        print("用法：python phase4_2_tool_calling.py <协议JSON路径>")
        sys.exit(1)

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    fields = data.get("fields", [])

    # ─── 演示：人为注入一处错误，看工具能不能揪出来 ───
    for f in fields:
        if f.get("length") and isinstance(f["length"], int):
            f["length"] += 1
            print(f"⚠ 演示注入错误：{f['name']} 的 length 被改成 {f['length']}"
                  f"（{f['type']} 实际应为 {f['length'] - 1}）\n")
            break

    messages = [
        SystemMessage(
            "你是协议评审工程师。用户给出协议字段表。请逐个字段调用 validate_field_type "
            "工具校验类型与字节数是否匹配。全部校验完成后，汇总哪些字段有问题并给出修正建议；"
            "若全部合法，输出'全部字段类型校验通过'。"
        ),
        HumanMessage(json.dumps(fields, ensure_ascii=False)),
    ]

    print("⏳ 评审开始（模型会自己决定逐个调用校验工具）...")
    final = run_tool_loop(messages)

    print("\n" + "=" * 60)
    print("【模型最终评审结论】")
    print(final)
    print("=" * 60)

    stem = Path(sys.argv[1]).stem
    with open(OUTPUT_DIR / f"{stem}_validation.txt", "w", encoding="utf-8") as f:
        f.write(final)
    print(f"✅ 评审报告已保存至 outputs/{stem}_validation.txt")


if __name__ == "__main__":
    main()
