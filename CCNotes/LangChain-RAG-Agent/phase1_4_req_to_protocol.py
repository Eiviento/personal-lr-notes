"""
Phase 1.4 实操：需求文档 → 协议字段表
========================================
纯 Python + DeepSeek API，用 Prompt 约束输出格式。
对应 Phase 1.1-1.3 所学内容：
  - 1.1: Prompt 四要素（角色/指令/上下文/输出格式）
  - 1.2: Few-shot 示例（教学用假例子，后续替换真实协议）
  - 1.3: 结构化输出 —— 这里用「Prompt 约束」方式（非 JSON Mode/Tool Calling）

使用方式：
  python phase1_4_req_to_protocol.py "设备需要上报温度、湿度、电池电量，每秒上报一次"
"""

import json
import os
import sys

from openai import OpenAI

# ─── 配置 ─────────────────────────────────────────────
# DeepSeek API 兼容 OpenAI SDK，只需改 base_url
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek v4 Pro 用 deepseek-chat

# ─── Prompt 模板（融合 Phase 1.1 ~ 1.3） ─────────────
SYSTEM_PROMPT = """\
你是一位资深的通信协议工程师，擅长将模糊的需求描述转化为规范的协议字段定义。

## 你的任务
分析用户输入的需求描述，提取所有需要通信的数据字段，输出结构化的协议字段表。

## 输出要求
你必须严格按以下 JSON 格式输出，不要输出任何其他内容：
{
  "protocol_name": "协议名称（简短中文）",
  "description": "一句话概括本协议用途",
  "fields": [
    {
      "name": "字段名（英文驼峰）",
      "chinese_name": "中文名称",
      "type": "数据类型（uint8/uint16/float32/string 等）",
      "length": "字节数（数字）",
      "unit": "单位（如 ℃、%、无）",
      "range": "取值范围说明",
      "description": "字段说明"
    }
  ],
  "timing": {
    "report_interval": "上报频率（如 1s、100ms、事件触发）",
    "direction": "通信方向（上行/下行/双向）"
  }
}

## 注意事项
1. 字段的数据类型必须是协议领域常用类型（uint8/uint16/int16/float32/string 等）
2. 字节数要合理（uint8=1, uint16=2, float32=4, string 按最大长度估算）
3. 如果有多种报文类型（如心跳 + 数据上报），请在 fields 中分报文组织，用 "message_type" 额外标识

## Few-shot 示例

示例需求：设备需要定时上报位置信息（经纬度、海拔），每 5 秒发一次
示例输出：
{
  "protocol_name": "设备位置上报协议",
  "description": "设备定时上报 GPS 位置信息至服务器",
  "fields": [
    {
      "name": "longitude",
      "chinese_name": "经度",
      "type": "float32",
      "length": 4,
      "unit": "度",
      "range": "-180.0 ~ 180.0",
      "description": "GPS 经度坐标，东经为正"
    },
    {
      "name": "latitude",
      "chinese_name": "纬度",
      "type": "float32",
      "length": 4,
      "unit": "度",
      "range": "-90.0 ~ 90.0",
      "description": "GPS 纬度坐标，北纬为正"
    },
    {
      "name": "altitude",
      "chinese_name": "海拔高度",
      "type": "float32",
      "length": 4,
      "unit": "米",
      "range": "-500.0 ~ 9000.0",
      "description": "GPS 海拔高度"
    }
  ],
  "timing": {
    "report_interval": "5s",
    "direction": "上行"
  }
}
"""


def analyze_requirement(requirement: str) -> dict:
    """调用 DeepSeek API，分析需求并返回协议字段表 JSON"""
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下需求，按规范输出协议字段表：\n\n{requirement}"},
        ],
        temperature=0.3,  # 低温度保证输出稳定
        max_tokens=4096,
    )

    raw_output = response.choices[0].message.content.strip()
    return _parse_response(raw_output)


def _parse_response(raw: str) -> dict:
    """容错解析：处理 LLM 可能包裹 markdown 代码块的情况（Phase 1.3 教的容错手段）"""
    # 去掉可能的 markdown 代码块包裹
    if raw.startswith("```"):
        lines = raw.split("\n")
        # 去掉首行 ```json 和末行 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # JSON 解析失败时，尝试从文本中提取 JSON 部分
        # 查找第一个 { 和最后一个 }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise ValueError(f"无法解析 LLM 输出为 JSON，原始输出：\n{raw}")


def print_protocol_table(result: dict) -> None:
    """将解析结果格式化打印为表格"""
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

    # 表头
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
        print("用法：python phase1_4_req_to_protocol.py \"<需求描述>\"")
        print("示例：python phase1_4_req_to_protocol.py \"设备需要上报温度、湿度、电池电量，每秒上报一次\"")
        sys.exit(1)

    requirement = sys.argv[1]
    print(f"📋 需求：{requirement}")
    print("⏳ 正在调用 DeepSeek API 分析...")

    try:
        result = analyze_requirement(requirement)
        print_protocol_table(result)

        # 同时输出完整 JSON 到文件，方便后续使用
        output_path = "protocol_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 完整 JSON 已保存至 {output_path}")

    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
