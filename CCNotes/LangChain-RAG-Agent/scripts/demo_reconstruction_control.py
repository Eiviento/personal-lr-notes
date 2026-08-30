"""
先验重构对照实验（证明"长答复里的文档细节 = 先验重构，不是泄露"）
=====================================================================
进程里从头到尾不出现需求文档：只把工具摘要（172 字）喂给模型，
并要求它详细展开。实测模型能重构出 -40~85℃、0.1℃ 等"文档事实"，
也会重构错（把 60 秒说成 30 秒）——因为教学需求文档是教科书标准写法。

用法（真调 2 次，几分钱）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_reconstruction_control.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from chat_agent import SYSTEM_PROMPT

SUMMARY = "协议《环境监测上报协议》已生成：\n- 共 6 个字段：msg_type:uint8、temperature:int16、humidity:uint8、battery_voltage:uint8、firmware_version:uint16、reserved:uint8\n- 6 条约束规则，3 条评审提示\n- 完整规范已保存，请提醒用户到侧栏下载"
NOTE = SystemMessage("【环境提示】当前已加载一份需求文档。用户要求生成协议时，直接调用 generate_protocol 工具（不传参数）；需要确认文档内容细节时再问用户。")
FACTS = ["-40", "0.1", "20%", "网关", "60", "光照", "固件版本"]


def main():
    llm = ChatOpenAI(model="deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key-here"),
                     base_url="https://api.deepseek.com", temperature=0.3, max_tokens=4096)
    fake_tc = AIMessage(content="好的，当前已加载需求文档，我直接为您生成协议规范。",
                        tool_calls=[{"name": "generate_protocol", "args": {}, "id": "call_ctrl", "type": "tool_call"}])
    msgs = [SystemMessage(SYSTEM_PROMPT), NOTE, HumanMessage("帮我生成协议"), fake_tc,
            ToolMessage(content=SUMMARY, tool_call_id="call_ctrl"),
            HumanMessage("请把协议详情完整展开给我看，包括需求分析要点、字段的完整 JSON 定义（含取值范围和单位）、约束规则。")]
    for i in range(2):
        r = llm.invoke(msgs)
        hit = [f for f in FACTS if f in r.content]
        print(f"第{i+1}次: {len(r.content)} 字, 命中 {hit}")
        print(r.content[:300])
        print("-" * 60)


if __name__ == "__main__":
    main()
