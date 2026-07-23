"""
Phase 2.2：LCEL 管道写法进阶
=============================
在 2.1 的 prompt | model | parser 基础上，演示：
  1. RunnableLambda — 插入自定义处理步骤
  2. RunnableParallel — 并行执行
  3. .assign() — 往中间结果追加字段
  4. RunnablePassthrough — 透传

数据流示意：
  用户输入
    │
    ▼
  {"requirement": "设备上报温度湿度"}
    │
    ▼
  prompt | model | parser        ← 基础链（2.1）
    │
    ▼
  {"protocol_name": "环境数据...", "fields": [...], "timing": {...}}
    │
    ├─► validate_fields(fields)   ← RunnableParallel 并行
    ├─► count_bytes(fields)       ← 三个校验同时跑
    └─► check_timing(timing)
    │
    ▼
  合并结果 → 打印
"""

import json
import os
import sys

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI

# ─── 配置 ─────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ─── 基础链（同 2.1） ─────────────────────────────────
PROTOCOL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
你是一位资深的通信协议工程师。分析需求，输出协议字段表 JSON。
严格输出 JSON，不要包含其他内容。
{{
  "protocol_name": "协议名称",
  "description": "协议用途",
  "fields": [{{"name":"...","chinese_name":"...","type":"...","length":字节数,"unit":"...","range":"...","description":"..."}}],
  "timing": {{"report_interval":"...","direction":"上行/下行/双向"}}
}}

Few-shot:
需求：设备定时上报位置（经纬度、海拔），每 5 秒一次
输出：{{"protocol_name":"设备位置上报协议","fields":[{{"name":"longitude","chinese_name":"经度","type":"float32","length":4,"unit":"度","range":"-180~180"}},{{"name":"latitude","chinese_name":"纬度","type":"float32","length":4,"unit":"度","range":"-90~90"}},{{"name":"altitude","chinese_name":"海拔","type":"float32","length":4,"unit":"米","range":"-500~9000"}}],"timing":{{"report_interval":"5s","direction":"上行"}}}}
""",
        ),
        ("user", "请分析以下需求，按规范输出协议字段表：\n\n{requirement}"),
    ]
)

llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.3,
    max_tokens=4096,
)

parser = JsonOutputParser()
base_chain = PROTOCOL_PROMPT | llm | parser


# ─── 2.2 新增：用 RunnableLambda 插入自定义处理 ───────
# RunnableLambda 把普通 Python 函数包装成管道可用的 Runnable
# 这样就能在 LLM 输出之后插入校验、转换等自定义逻辑

def validate_fields(result: dict) -> dict:
    """校验字段完整性 —— 这就是一个普通 Python 函数"""
    fields = result.get("fields", [])
    issues = []
    for i, f in enumerate(fields):
        if not f.get("name"):
            issues.append(f"字段 {i} 缺少 name")
        if not f.get("type"):
            issues.append(f"字段 {f.get('name', i)} 缺少 type")
        if f.get("length") is None:
            issues.append(f"字段 {f.get('name', i)} 缺少 length")
    return {"valid": len(issues) == 0, "issues": issues, "field_count": len(fields)}


def validate_timing(result: dict) -> dict:
    """校验上报频率是否合理"""
    timing = result.get("timing", {})
    interval = timing.get("report_interval", "")
    if not interval:
        return {"timing_valid": False, "timing_issue": "未指定上报频率"}
    return {"timing_valid": True, "timing_issue": None, "interval": interval}


def calculate_total_bytes(result: dict) -> dict:
    """计算报文总字节数"""
    total = sum(f.get("length", 0) for f in result.get("fields", []))
    return {"total_bytes": total, "field_count": len(result.get("fields", []))}


# ═══════════════════════════════════════════════════════
# 2.2 核心演示：RunnableParallel 并行执行多个后处理
# ═══════════════════════════════════════════════════════
# 三个校验函数同时跑，最后合并结果
# RunnablePassthrough() 原样保留 LLM 的输出

validation_chain = RunnableParallel(
    # 三个分支并行执行：
    field_check=RunnableLambda(validate_fields),        # 分支1: 校验字段
    timing_check=RunnableLambda(validate_timing),       # 分支2: 校验上报频率
    byte_count=RunnableLambda(calculate_total_bytes),   # 分支3: 计算总字节
    # 保留原始 LLM 输出（不做任何处理，原样透传）
    protocol=RunnablePassthrough(),
)

# ─── 完整管道：base_chain → validation_chain ──────────
full_chain = base_chain | validation_chain


def print_result(result: dict) -> None:
    """打印完整结果"""
    protocol = result["protocol"]

    # 协议基本信息
    print(f"\n{'='*60}")
    print(f"协议名称：{protocol.get('protocol_name', 'N/A')}")
    print(f"描述：{protocol.get('description', 'N/A')}")
    timing = protocol.get("timing", {})
    print(f"上报频率：{timing.get('report_interval', 'N/A')}")
    print(f"通信方向：{timing.get('direction', 'N/A')}")
    print(f"{'='*60}\n")

    # 字段表
    fields = protocol.get("fields", [])
    header = f"{'字段名':<20} {'中文名':<12} {'类型':<10} {'字节':<6}"
    print(header)
    print("-" * len(header))
    for f in fields:
        print(
            f"{f.get('name', ''):<20} "
            f"{f.get('chinese_name', ''):<12} "
            f"{f.get('type', ''):<10} "
            f"{str(f.get('length', '')):<6}"
        )

    # ─── 校验结果（来自三个并行分支） ───
    print(f"\n{'─'*60}")
    print("【校验结果】（LCEL RunnableParallel 并行产出）")

    field_ok = result["field_check"]
    print(f"  字段完整性：{'✅ 通过' if field_ok['valid'] else '❌ 有问题'}")
    for issue in field_ok["issues"]:
        print(f"    ⚠ {issue}")

    timing_ok = result["timing_check"]
    print(f"  上报频率：{'✅ 已指定' if timing_ok['timing_valid'] else '❌ 缺失'} ({timing_ok.get('interval', 'N/A')})")

    byte_info = result["byte_count"]
    print(f"  报文总字节：{byte_info['total_bytes']} bytes ({byte_info['field_count']} 个字段)")

    print(f"{'─'*60}\n")


def main():
    if len(sys.argv) < 2:
        print("用法：python phase2_2_lcel_pipeline.py \"<需求描述>\"")
        sys.exit(1)

    requirement = sys.argv[1]
    print(f"📋 需求：{requirement}")
    print("⏳ 正在通过 LCEL 管道处理（LLM 生成 → 并行校验）...")

    try:
        result = full_chain.invoke({"requirement": requirement})
        print_result(result)

        output_path = "protocol_output_lcel.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ 完整 JSON 已保存至 {output_path}")

    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
