"""
Phase 5.2：错误处理 / 重试 / 日志
=================================
LLM API 三种典型失败（都是"重试有效"型）：
  1. 超时（网络慢/模型卡）
  2. 限流 429（并发太高）→ 重试 + 指数退避
  3. 服务器 5xx（抖动）
不可重试的（4xx 认证/参数错）：快速失败 + 明确报错——重试是浪费。

LangChain 一行加自动重试：
  llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
  - 指数退避 + 随机抖动：避免失败后所有请求同一秒重试（惊群）
  - 挂在 llm 上而非整条链：只重试真正的模型调用

日志：logging + RotatingFileHandler（outputs/app.log，自动滚动防膨胀），
记录每次生成的文件名/耗时/成败。

用法：
  python phase5_2_robust.py <需求文档>                  # 正常路径
  python phase5_2_robust.py --simulate-failure <需求文档>  # 演示重试（连一个打不开的地址）
"""

import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import (
    ANALYZE_PROMPT, FIELDS_PROMPT, RULES_PROMPT, merge_final, llm,
)
from generate_protocol import render_markdown

# ─── 日志：文件（自动滚动）+ 控制台 ────────────────────
_handler = RotatingFileHandler("outputs/app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)
log = logging.getLogger("protocol-tool")

# 输出目录以脚本文件位置为基准：在任何目录下运行，都写到项目根的 outputs/
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def build_robust_chain():
    """同 3.2 四步链，唯一区别：llm 换成带重试的版本（指数退避 + 抖动）"""
    retry_llm = llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
    return (
        RunnablePassthrough.assign(key_points=ANALYZE_PROMPT | retry_llm | StrOutputParser())
        | RunnablePassthrough.assign(fields=FIELDS_PROMPT | retry_llm | JsonOutputParser())
        | RunnablePassthrough.assign(checks=RULES_PROMPT | retry_llm | JsonOutputParser())
        | RunnableLambda(merge_final)
    )


def generate(chain, path: str) -> None:
    """带日志的完整生成流程"""
    doc = read_doc(path)
    log.info("开始生成：%s（%d 字符）", path, len(doc))
    t0 = time.time()
    try:
        result = chain.invoke({"requirement": doc})
    except Exception as e:
        log.error("生成失败：%s → %s", path, e)
        print(f"\n❌ 生成失败（重试后仍失败）：{e}\n   请检查 API Key / 网络 / 服务状态。")
        sys.exit(1)

    elapsed = time.time() - t0
    log.info("生成成功：%s → %s（%d 字段，耗时 %.1fs）",
             path, result.get("protocol_name"), len(result.get("fields", [])), elapsed)

    stem = Path(path).stem
    with open(OUTPUT_DIR / f"{stem}_protocol.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_DIR / f"{stem}_protocol.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(result))
    print(f"✅ 已保存 outputs/{stem}_protocol.json / _protocol.md，日志见 outputs/app.log")


def simulate_failure(path: str) -> None:
    """演示：连一个打不开的地址，观察 3 次重试 + 最终快速失败"""
    print(f"⏳ 模拟 API 不可达（3 次尝试 × 2 秒超时 + 指数退避）...")
    bad_llm = ChatOpenAI(
        model="deepseek-chat",
        api_key="fake-key",
        base_url="http://127.0.0.1:9",   # 打不开的端口
        request_timeout=2,
    ).with_retry(stop_after_attempt=3, wait_exponential_jitter=True)

    log.info("开始生成（模拟失败）：%s", path)
    t0 = time.time()
    try:
        bad_llm.invoke("测试")
    except Exception as e:
        elapsed = time.time() - t0
        log.error("生成失败（模拟）：%s（耗时 %.1fs，重试 3 次后放弃）", type(e).__name__, elapsed)
        print(f"\n❌ {type(e).__name__}（耗时 {elapsed:.1f}s = 3 次尝试 + 退避等待）")
        print("   如果这是 429/5xx，重试很可能成功；如果是 4xx 认证错，重试永远失败。")
        sys.exit(1)


def main():
    args = sys.argv[1:]
    if not args or (args[0] == "--simulate-failure" and len(args) < 2):
        print("用法：")
        print("  python phase5_2_robust.py <需求文档>")
        print("  python phase5_2_robust.py --simulate-failure <需求文档>")
        sys.exit(1)

    if args[0] == "--simulate-failure":
        simulate_failure(args[1])
    else:
        generate(build_robust_chain(), args[0])


if __name__ == "__main__":
    main()
