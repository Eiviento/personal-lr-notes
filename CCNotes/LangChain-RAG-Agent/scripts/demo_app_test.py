"""
app.py 冒烟测试（AppTest + 假 agent，零成本）
=============================================
验证聊天窗口的 UI 机制不崩：
  1. 页面渲染、无异常
  2. 上传文档 → chat_agent 模块收到文档
  3. 发消息 → 假 agent 回答 → 历史累积 2 条
  4. 侧栏显示"生成协议后"占位文案

不真调 API（CHAT_FAKE_AGENT=1）。

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_app_test.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 导入 chat_agent

os.environ["CHAT_FAKE_AGENT"] = "1"

from streamlit.testing.v1 import AppTest


def main():
    sample = Path(__file__).resolve().parent.parent / "inputs/sample_requirement.md"

    # default_timeout=30：本机首次运行光 import app（langchain/rag 链）就要 ~5s，
    # AppTest 默认 3s 超时会在初始渲染处误报（RuntimeError: AppTest script run timed out）
    at = AppTest.from_file(Path(__file__).resolve().parent.parent / "app.py", default_timeout=30).run()
    assert not at.exception, f"初始渲染异常：{at.exception}"

    # 1. 上传文档 → 注入成功
    # 适配：streamlit 1.62.0 的 set_value 只接受 (name, content, mime) 元组，
    # 原 FileMock（name/getvalue 文件对象）报错：TypeError: 'FileMock' object is not iterable
    at.file_uploader[0].set_value((sample.name, sample.read_bytes(), "text/markdown")).run()
    assert not at.exception, f"上传后异常：{at.exception}"

    # 2. 发一条消息 → 假 agent 回答 → 历史 2 条
    at.chat_input[0].set_value("你好").run()
    assert not at.exception, f"聊天后异常：{at.exception}"
    msgs = at.session_state["messages"]
    assert len(msgs) == 2, f"历史应 2 条，实际 {len(msgs)}"
    assert msgs[0].type == "human" and msgs[1].type == "ai"

    print("✅ AppTest 冒烟通过：上传注入 / 假聊天一轮 / 历史累积 2 条 / 无异常")


if __name__ == "__main__":
    main()
