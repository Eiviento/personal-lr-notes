"""
Phase 2.1：LangChain 三大核心 —— PromptTemplate、Model、Parser
================================================================
用 LangChain 重写 Phase 1.4 的"需求 → 协议字段表"功能，对比原生 SDK 写法。

LangChain 三层 vs 原生写法：
  原生:  手拼字符串 → openai.OpenAI() → 手写 json.loads + 容错
  LCEL:  ChatPromptTemplate → ChatOpenAI → JsonOutputParser
         这三者通过 | 管道符串联成一条链
"""

import json
import os
import sys

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

# ─── 配置 ─────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ═══════════════════════════════════════════════════════
# 核心 1：ChatPromptTemplate — 替代手写字符串拼接
# ═══════════════════════════════════════════════════════
# Phase 1 做法：
#   SYSTEM_PROMPT = "你是一个协议工程师..."  (一大坨固定字符串)
#   messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": requirement}]
#
# LangChain 做法：用模板把 system 和 user 分开管理，{input} 是占位符

PROTOCOL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
你是一位资深的通信协议工程师，擅长将模糊的需求描述转化为规范的协议字段定义。

## 你的任务
分析用户输入的需求描述，提取所有需要通信的数据字段，输出结构化的协议字段表。

## 输出要求
严格输出 JSON，不要包含其他内容。JSON 结构如下：
{{
  "protocol_name": "协议名称",
  "description": "协议用途说明",
  "fields": [
    {{
      "name": "字段名（英文驼峰）",
      "chinese_name": "中文名称",
      "type": "数据类型（uint8/uint16/float32/string 等）",
      "length": "字节数",
      "unit": "单位",
      "range": "取值范围",
      "description": "字段说明"
    }}
  ],
  "timing": {{
    "report_interval": "上报频率",
    "direction": "通信方向（上行/下行/双向）"
  }}
}}

## Few-shot 参考
需求：设备定时上报位置信息（经纬度、海拔），每 5 秒发一次
输出：{{"protocol_name":"设备位置上报协议","fields":[{{"name":"longitude","chinese_name":"经度","type":"float32","length":4,"unit":"度","range":"-180~180","description":"GPS经度"}},{{"name":"latitude","chinese_name":"纬度","type":"float32","length":4,"unit":"度","range":"-90~90","description":"GPS纬度"}},{{"name":"altitude","chinese_name":"海拔","type":"float32","length":4,"unit":"米","range":"-500~9000","description":"海拔高度"}}],"timing":{{"report_interval":"5s","direction":"上行"}}}}
""",
        ),
        ("user", "请分析以下需求，按规范输出协议字段表：\n\n{requirement}"),
    ]
)

# ═══════════════════════════════════════════════════════
# 核心 2：ChatOpenAI — 统一的模型调用接口
# ═══════════════════════════════════════════════════════
# Phase 1 做法：
#   client = OpenAI(api_key=..., base_url=...)
#   response = client.chat.completions.create(model=..., messages=...)
#
# LangChain 做法：ChatOpenAI 封装了所有 LLM 调用,无论底层是 OpenAI / DeepSeek / 其他
#   统一用 .invoke() 调用，换模型只改参数不改代码

llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.3,
    max_tokens=4096,
)

# ═══════════════════════════════════════════════════════
# 核心 3：JsonOutputParser — 自动解析 JSON，内置容错
# ═══════════════════════════════════════════════════════
# Phase 1 做法：
#   手写 _parse_response() 函数，处理 markdown 代码块、json.loads 异常...
#
# LangChain 做法：JsonOutputParser 自动处理，链式调用

parser = JsonOutputParser()

# ═══════════════════════════════════════════════════════
# LCEL 管道：用 | 把三者串联
# ═══════════════════════════════════════════════════════
# 这是 LangChain 最核心的写法 —— LCEL (LangChain Expression Language)
# prompt | model | parser
# 数据流：用户输入 → 填充模板 → 发送给 LLM → 解析 JSON → 返回 dict

chain = PROTOCOL_PROMPT | llm | parser


def print_table(result: dict) -> None:
    """格式化打印协议字段表"""
    print(f"\n{'='*60}")
    print(f"协议名称：{result.get('protocol_name', 'N/A')}")
    print(f"描述：{result.get('description', 'N/A')}")
    if timing := result.get("timing"):
        print(f"上报频率：{timing.get('report_interval', 'N/A')}")
        print(f"通信方向：{timing.get('direction', 'N/A')}")
    print(f"{'='*60}\n")

    fields = result.get("fields", [])
    if not fields:
        print("（无字段）")
        return

    header = f"{'字段名':<20} {'中文名':<12} {'类型':<10} {'字节':<6} {'单位':<8} {'范围':<20}"
    print(header)
    print("-" * len(header))

    for f in fields:
        print(
            f"{f.get('name', ''):<20} "
            f"{f.get('chinese_name', ''):<12} "
            f"{f.get('type', ''):<10} "
            f"{str(f.get('length', '')):<6} "
            f"{f.get('unit', ''):<8} "
            f"{f.get('range', ''):<20}"
        )
    print(f"\n共 {len(fields)} 个字段")


def main():
    if len(sys.argv) < 2:
        print("用法：python phase2_1_langchain_basics.py \"<需求描述>\"")
        sys.exit(1)

    requirement = sys.argv[1]
    print(f"📋 需求：{requirement}")
    print("⏳ 正在通过 LangChain 管道调用 DeepSeek...")

    try:
        # 核心调用：一行搞定 prompt 填充 → LLM 调用 → JSON 解析
        result = chain.invoke({"requirement": requirement})
        print_table(result)

        output_path = "protocol_output_langchain.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 完整 JSON 已保存至 {output_path}")

    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
