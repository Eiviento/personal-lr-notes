"""
invoke vs stream：用时间戳把差别钉死（零 API 成本）
==================================================
真实场景里"生成协议"要 10~30 秒：
  invoke → 用户盯着空白 20 秒，然后"啪"全出来
  stream → 1 秒内看到第一个字，之后一个字一个字蹦

用法：python demo_stream_feel.py
"""

import time

from langchain_core.runnables import RunnableLambda


def slow_text(x):
    """模拟慢输出：3 秒产出 6 个词，每个词隔 0.5 秒"""
    for word in ["设备", "上报", "温度", "湿度", "电量", "完成"]:
        time.sleep(0.5)
        yield word + " "


chain = RunnableLambda(slow_text)

print("═══ 方式 1：invoke（等 3 秒，一次拿全）═══")
t0 = time.time()
result = chain.invoke("x")
print(f"   [{time.time() - t0:.1f}s] 一次性收到完整结果：{result}")
print("   ↑ 注意：前 3 秒屏幕上一片空白，什么反馈都没有\n")

print("═══ 方式 2：stream（每 0.5 秒收到一个词）═══")
t0 = time.time()
for chunk in chain.stream("x"):
    print(f"   [{time.time() - t0:.1f}s] 收到一块 → {chunk!r}", flush=True)
print("   ↑ 注意：第 1 秒就有字可看，之后持续有新进展\n")

print("真实场景（生成协议 20 秒）：")
print("   invoke：盯着空白转圈 20 秒 → 焦虑，以为卡死了")
print("   stream：1 秒看到开头 → 边等边读，体验完全不同")
