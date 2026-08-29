"""
2.2 配套演示（零 API 成本，随便跑）
====================================
三个实验：
  ① 透视 chain 结构：RunnableSequence 里装着哪三个盒子
  ② 并行分叉：手工伪造 dict 喂 validation_chain，看三个分支各自干活
  ③ 形式 vs 内容：形式校验全通过 ≠ 协议正确（uint8 表示不了 -40℃）

用法：python demo_2_2_checks.py
"""

import json

from phase2_2_lcel_pipeline import full_chain, validation_chain

print("=" * 60)
print("实验① 透视 chain 结构")
print("=" * 60)
print("full_chain 类型：", type(full_chain).__name__)
print("full_chain 的两层（积木套积木）：")
for i, step in enumerate(full_chain.steps):
    print(f"  {i}: {type(step).__name__}")
print("validation_chain 的四个分支：")
for name, branch in validation_chain.steps__.items():
    print(f"  {name}: {type(branch).__name__}")

print()
print("=" * 60)
print("实验② 并行分叉：三个分支各自干活，互不干扰")
print("=" * 60)
fake = {
    "protocol_name": "测试协议",
    "fields": [
        {"name": "temperature", "type": "uint8", "length": 1},
        {"name": "bad_field", "type": "uint8"},      # 故意缺 length
    ],
    "timing": {},                                     # 故意留空
}
result = validation_chain.invoke(fake)
print("输入 2 个键 → 输出 4 个键：")
for k, v in result.items():
    print(f"  {k}: {json.dumps(v, ensure_ascii=False)}")

print()
print("=" * 60)
print("实验③ 形式 vs 内容：校验通过 ≠ 协议正确")
print("=" * 60)
absurd = {
    "protocol_name": "环境监测协议",
    "fields": [
        # 形式完美（name/type/length 齐全），内容荒谬：
        # uint8 范围是 0~255，表示不了 -40℃
        {"name": "temperature", "type": "uint8", "length": 1},
        {"name": "humidity", "type": "uint8", "length": 1},
    ],
    "timing": {"report_interval": "60s", "direction": "上行"},
}
check = validation_chain.invoke(absurd)
print("field_check:", json.dumps(check["field_check"], ensure_ascii=False))
print("↑ 全通过，但没发现 uint8 表示不了负数——")
print("  形式校验是尺子：量得出零件齐不齐，量不出设计对不对")
