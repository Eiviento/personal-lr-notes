"""
app.py 冒烟测试（AppTest + 假 agent，零成本）
=============================================
验证客服工作台 UI 机制不崩：
  1. 页面渲染、无异常
  2. 发消息 → 历史渲染（FakeAgent 应答）
  3. 触发退款 → 出现审批卡片（批准/拒绝按钮）
  4. 点批准 → 卡片消失、恢复结果渲染

不真调 API（CHAT_FAKE_AGENT=1 走 FakeAgent）。
用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent7_app_test.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import app 用（app.py 在项目根）

os.environ["CHAT_FAKE_AGENT"] = "1"

from streamlit.testing.v1 import AppTest


def _all_texts(at) -> list[str]:
    """收集页面所有可见文本（chat 气泡内的 markdown + warning/info）。"""
    out = []
    for cm in at.chat_message:
        for md in cm.markdown:
            if md.value:
                out.append(str(md.value))
    for w in at.warning:
        if w.value:
            out.append(str(w.value))
    for i in at.info:
        if i.value:
            out.append(str(i.value))
    return out


def main():
    APP = Path(__file__).resolve().parent.parent / "app.py"

    # default_timeout=30：本机 import agent7_webapp（langchain 全家桶）要 ~2-3s
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception, f"初始渲染异常：{at.exception}"
    print("✓ 页面初始渲染无异常")

    # 1. 发一条普通消息 → FakeAgent 应答 → 历史渲染
    at.chat_input[0].set_value("你好").run()
    assert not at.exception, f"聊天后异常：{at.exception}"
    texts = _all_texts(at)
    assert any("假agent" in str(t) for t in texts), f"应出现假 agent 应答，实际：{texts}"
    print(f"✓ 普通消息一轮：气泡文本 {len(texts)} 条，含假 agent 应答")

    # 2. 触发退款（FakeAgent 对含"退"+"SO-"的消息返回 __interrupt__）→ 出现审批卡片
    at.chat_input[0].set_value("我要退 SO-1003，质量问题").run()
    assert not at.exception, f"触发退款后异常：{at.exception}"
    texts2 = _all_texts(at)
    assert any("待审批" in str(t) for t in texts2), f"应出现待审批卡片，实际：{texts2}"
    btn_labels = [b.label for b in at.button]
    assert "✅ 批准" in btn_labels and "❌ 拒绝" in btn_labels, f"应出现批准/拒绝按钮，实际：{btn_labels}"
    print(f"✓ 退款触发审批：待审批卡片 + 批准/拒绝按钮出现（按钮：{btn_labels}）")

    # 3. 点批准 → 卡片消失、恢复结果渲染
    at.button(key="approve").click().run()
    assert not at.exception, f"批准后异常：{at.exception}"
    texts3 = _all_texts(at)
    assert not any("待审批" in str(t) for t in texts3), f"批准后卡片应消失，实际：{texts3}"
    assert any("批准" in str(t) for t in texts3), f"批准后应渲染恢复结果，实际：{texts3}"
    print(f"✓ 点批准：卡片消失，恢复结果渲染（气泡文本 {len(texts3)} 条）")

    print("\n✅ AppTest 冒烟通过：渲染 / 历史累积 / 审批卡片出现与消失 / 恢复结果 / 无异常")


if __name__ == "__main__":
    main()
