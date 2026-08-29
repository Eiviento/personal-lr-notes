"""
invoke / batch / stream 三兄弟详解演示（零 API 成本）
====================================================
用带 sleep 的普通函数包装成积木，让三种调用方式的区别"看得见"：

  invoke → 单个进、单个出（同步等待它干完才返回）
  batch  → 多个进、多个出（内部并发：3 个各需 1s 的任务 ≈ 1s 干完）
  stream → 一块一块地吐（打字机效果，实时看到进展）

用法：python demo_invoke_batch_stream.py
"""

import time

from langchain_core.runnables import RunnableLambda


def slow_process(x):
    """模拟慢任务（真实场景里是调 LLM，要等十几秒）"""
    time.sleep(1)
    return f"✅ 处理完成：{x}"


box = RunnableLambda(slow_process)

print("① invoke：单个进，单个出（同步等待）")
t0 = time.time()
result = box.invoke("需求A")
print(f"   {result}（耗时 {time.time() - t0:.1f}s）\n")

print("② batch：多个进，多个出（内部并发）")
t0 = time.time()
results = box.batch(["需求A", "需求B", "需求C"])
print(f"   {results}")
print(f"   3 个各需 1s 的任务，总耗时 {time.time() - t0:.1f}s——并发跑，不是串行 3s\n")


def slow_words(x):
    """生成器函数：每 yield 一次，外面就收到一块（=可流式）"""
    for word in str(x).split():
        time.sleep(0.4)
        yield word + " "


print("③ stream：一块一块地吐（打字机效果）")
for chunk in RunnableLambda(slow_words).stream("设备 上报 温度 湿度 电量"):
    print(f"   收到一块 → {chunk!r}")
print("   每 yield 一次，外面立刻收到一块，不用等全部完成\n")

print("三者的输入输出形状：")
print("   invoke(x)          单个 → 单个")
print("   batch([x1,x2,x3])  列表 → 列表（顺序对应，内部并发）")
print("   stream(x)          单个 → 逐块流（实时）")
