"""
Phase 3.1：文档输入 —— 解析 Markdown / TXT 需求文档
====================================================
从"命令行一句话输入"升级到"喂文件"。三个实际问题：
  1. 编码 —— 中文文档 UTF-8 / GBK 混杂，按序尝试解码（stdlib 搞定，无第三方库）
  2. 大小 —— 上下文窗口有限，估算 token 数，超限警告（Phase 4 用 RAG 治本）
  3. 噪声 —— 同事文档有大量背景废话，直接全文塞给 LLM 提取，这是模型的强项

设计原则：先跑通"全文直塞"，不要提前优化。

数据流：
  文件路径 ──read_doc(编码自适应)──► 文档全文 ──► prompt | llm | parser ──► 协议 JSON
"""

import json
import os
import sys
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# ─── 配置 ─────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
# DeepSeek-chat 上下文 64K token，输入上限留一半余量
# 粗略估算：中文 1 字符 ≈ 1 token
MAX_INPUT_CHARS = 30000

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def read_doc(file_path: str) -> str:
    """读文件，编码自适应：按 utf-8-sig → utf-8 → gb18030 顺序尝试。
    gb18030 是 GBK/GB2312 的超集，中文文档基本全覆盖。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return Path(file_path).read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别文件编码：{file_path}")


# ─── 字段表链（复用 Phase 2.1 的 Prompt，管道写法不变）──
PROTOCOL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
你是一位资深的通信协议工程师，擅长将模糊的需求描述转化为规范的协议字段定义。

## 你的任务
分析用户输入的需求文档，忽略与协议无关的内容（硬件选型、部门分工等），
提取所有需要通信的数据字段，输出结构化的协议字段表。

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
        ("user", "需求文档如下：\n\n{requirement}"),
    ]
)


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
    print(f"\n共 {len(fields)} 个字段")


def main():
    if len(sys.argv) < 2:
        print("用法：python phase3_1_doc_input.py <需求文档路径>")
        sys.exit(1)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 请先设置环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    doc_path = sys.argv[1]
    doc = read_doc(doc_path)

    # ─── 输入侧检查：编码已解决，这里看大小 ───────────
    print(f"📄 文档：{doc_path}")
    print(f"  字符数：{len(doc)}（约 {len(doc)} tokens，中文 1 字符 ≈ 1 token）")
    if len(doc) > MAX_INPUT_CHARS:
        print(f"⚠ 文档过长（>{MAX_INPUT_CHARS} 字符），可能超上下文窗口。"
              f"Phase 4 会用 RAG（切片+检索）解决，当前先截断后 {MAX_INPUT_CHARS} 字符")
        doc = doc[-MAX_INPUT_CHARS:]
    print("⏳ 正在把全文交给 LLM 提取协议字段...")

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=4096,
    )
    chain = PROTOCOL_PROMPT | llm | JsonOutputParser()

    try:
        result = chain.invoke({"requirement": doc})
        print_table(result)

        # 输出文件名跟输入文件走：xxx.md → xxx_protocol.json
        out_path = OUTPUT_DIR / f"{Path(doc_path).stem}_protocol.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 协议 JSON 已保存至 {out_path}")

    except Exception as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
