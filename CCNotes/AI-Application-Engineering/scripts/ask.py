"""ask —— DocQA 服务的命令行客户端示例

演示如何调用 /qa 接口（也用于端到端验证服务）。
用 httpx 的 json= 参数发请求，自动处理 UTF-8（避免手拼 JSON 的编码坑）。

用法：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/ask.py "你的问题"
  （服务需先启动：uvicorn src.api.main:create_app --factory --port 8000）
"""
import sys

import httpx

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

URL = "http://127.0.0.1:8000/qa"


def ask(question: str, k: int = 3):
    r = httpx.post(URL, json={"question": question, "k": k}, timeout=120)
    if r.status_code != 200:
        print(f"[错误] HTTP {r.status_code}: {r.text[:300]}")
        return 1
    data = r.json()
    print("答：", data["answer"])
    print("\n引用来源：", data["sources"])
    return 0


def main():
    q = sys.argv[1] if len(sys.argv) > 1 else "混合检索是怎么融合关键词和向量的"
    print(f"问：{q}\n")
    return ask(q)


if __name__ == "__main__":
    sys.exit(main())
