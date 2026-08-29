"""
Phase 3.3：Chain 串联 —— RunnableSequence 与 invoke / batch / stream
=====================================================================
组装程序的思维模型（为什么这么写）：
  1. 一切组件都是 Runnable —— 统一"输入 → 输出"接口，所以能任意组合
  2. 代码结构 = 数据流结构 —— 写代码就是画数据流图
  3. 零件可复用 —— 同样的 analyze/fields/rules 子链，能装出
     带 tap 的调试版（3.2）和干净的批量版（本脚本）

三种调用方式（同一条链，换调用方法）：
  invoke → 单输入单输出
  batch  → 多输入多输出，内部并发 —— 批量处理同事文档
  stream → 流式输出，打字机效果 —— UI 展示用

用法：
  python phase3_3_batch_stream.py batch <文档1> <文档2> ...
  python phase3_3_batch_stream.py stream <文档>
"""

import json
import sys
from pathlib import Path

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import analyze_chain, fields_chain, rules_chain, merge_final

# ─── 组装：同样的零件，去掉 tap 的干净版 ──────────────
# 零件（子链）在 3.2 里定义过，这里重新组装一遍：
# 教学点：组装是自由的，零件不动，换个装法就是另一条流水线
clean_chain = (
    RunnablePassthrough.assign(key_points=analyze_chain)
    | RunnablePassthrough.assign(fields=fields_chain)
    | RunnablePassthrough.assign(checks=rules_chain)
    | RunnableLambda(merge_final)
)


def show_structure():
    """拆开链看内部结构：没有魔法，就是一张步骤表"""
    print("【clean_chain 的结构】（| 串联的本质 = RunnableSequence）")
    for i, step in enumerate(clean_chain.steps):
        print(f"  {i}: {type(step).__name__}")
    print("\n【analyze_chain 的内部】（子链本身也是三步串联）")
    for i, step in enumerate(analyze_chain.steps):
        print(f"  {i}: {type(step).__name__}")
    print()


def do_batch(paths):
    """batch：多输入多输出，内部自动并发，适合批量处理同事文档"""
    docs = [read_doc(p) for p in paths]
    print(f"⏳ batch 处理 {len(docs)} 份文档（每份 3 次 LLM 调用，内部并发）...\n")
    results = clean_chain.batch([{"requirement": d} for d in docs])

    for path, r in zip(paths, results):
        print(f"  ✓ {path}")
        print(f"      → {r.get('protocol_name')}（{len(r.get('fields', []))} 字段，"
              f"{len(r.get('constraints', []))} 条约束）")
        out_path = OUTPUT_DIR / f"batch_{Path(path).stem}_protocol.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存至 outputs/batch_*_protocol.json")


def do_stream(path):
    """stream：流式输出，逐字吐出（打字机效果），UI 展示用"""
    doc = read_doc(path)
    print("⏳ stream 流式输出（需求分析步骤）...\n")
    print("── ", end="", flush=True)
    for chunk in analyze_chain.stream({"requirement": doc}):
        print(chunk, end="", flush=True)
    print("\n\n✅ 流式输出完成")


def main():
    if len(sys.argv) < 2:
        print("用法：")
        print("  python phase3_3_batch_stream.py batch <文档1> <文档2> ...")
        print("  python phase3_3_batch_stream.py stream <文档>")
        sys.exit(1)

    show_structure()

    cmd = sys.argv[1]
    if cmd == "batch" and len(sys.argv) >= 3:
        do_batch(sys.argv[2:])
    elif cmd == "stream" and len(sys.argv) >= 3:
        do_stream(sys.argv[2])
    else:
        print(f"❌ 未知命令或参数不足：{sys.argv[1:]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
