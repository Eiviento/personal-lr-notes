"""
Phase 5 · 观察与评估 —— 把"调优"从感觉变成测量
=================================================
核心论断先行：改 prompt / 工具 / 护栏后，怎么知道 agent 真的变好了？
靠感觉不行——要建【eval 集】（一组代表场景 + 可编程判据）批量跑，
用分数说话。单变量回归：一次只改一个变量（这里是系统提示的一句规则），
其余全不动，对比分数变化——变好/变坏/无差异，一测便知。

脚本结构：
  EVAL_CASES  : 6 个代表场景（覆盖 知识检索/查单/不存在订单诚实/政策/时间/组合）
               每个 case 带判据：应该调用哪些工具 + 回答必须含/绝不能含什么
  PROMPT_V1/V2: 单变量——V2 比 V1 只多一句防幻觉规则
  evaluate()  : 逐 case 跑 agent，记录 工具调用序列 + 最终回答，判据打分
  分数 = 通过的 case 数 / 总数

运行（需 .env key；单次实跑未挑选）：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/agent5_eval.py
"""

import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from agent1_whitebox import _build_llm, get_now_time, get_order_status, search_knowledge

SEP = "─" * 66
TOOLS = [search_knowledge, get_order_status, get_now_time]

# ─── 单变量：两个系统提示，唯一差异是 V2 多一句防幻觉规则 ─────────────
PROMPT_V1 = """你是 SmartHome 智能家居产品的技术支持客服助手。
你有工具：search_knowledge(产品知识库)、get_order_status(查订单)、get_now_time(时间)。
用户问政策/故障先调 search_knowledge；给订单号就调 get_order_status；问时间调 get_now_time。
回答用中文，简洁，需要时列要点。"""

PROMPT_V2 = PROMPT_V1 + """
规则：工具返回"未找到/不存在/没有"时，必须如实转述并请用户核对，绝不编造订单状态或政策内容。"""


# ─── eval 集：6 个代表场景 + 判据 ────────────────────────────────────
def _calls_of(state_msgs):
    """从最终 state 的消息里收集所有工具调用名。"""
    names = []
    for m in state_msgs:
        if isinstance(m, AIMessage) and m.tool_calls:
            names.extend(tc["name"] for tc in m.tool_calls)
    return names


def _final_answer(state_msgs):
    for m in reversed(state_msgs):
        if isinstance(m, AIMessage) and not m.tool_calls:
            return str(m.content)
    return ""


EVAL_CASES = [
    # must_have 每项 = 同义词组（list），组内任一出现即视为满足——判据测"行为达成"
    # 而非"逐字措辞"（教训：V1 版判据把"没有找到"误判为缺"未找到"，假阴性失真）
    {
        "id": "policy_refund",
        "q": "七天无理由退货怎么算？",
        "want_tools": ["search_knowledge"],
        "must_have": [["七天", "7 天", "七天内"], ["无理由"]],
        "must_not": [],
    },
    {
        "id": "order_status",
        "q": "帮我查一下订单 SO-1003 到哪了？",
        "want_tools": ["get_order_status"],
        "must_have": [["SO-1003"], ["delivered", "已送达", "送达"]],
        "must_not": [],
    },
    {
        "id": "order_missing",  # ★ 防幻觉关键 case：不存在订单，绝不编造状态
        "q": "查一下订单 SO-0000 现在什么状态？",
        "want_tools": ["get_order_status"],
        "must_have": [["未找到", "没有找到", "不存在", "找不到"]],
        # 只禁"编造状态动作"特征词；"处理中/送达"等允许出现（礼貌转述可能带出，前版误伤）
        "must_not": [["已退款", "退款成功", "已到账"]],
    },
    {
        "id": "wifi_trouble",
        "q": "网关连不上 Wi-Fi 怎么办？",
        "want_tools": ["search_knowledge"],
        "must_have": [["2.4G", "2.4GHz"]],
        "must_not": [],
    },
    {
        "id": "current_time",
        "q": "现在几点了？",
        "want_tools": ["get_now_time"],
        "must_have": [],
        "must_not": [],
    },
    {
        "id": "mixed_question",
        "q": "我刚买的 SO-1001 想退，政策允许吗？",
        "want_tools": ["get_order_status", "search_knowledge"],
        "must_have": [],
        "must_not": [],
    },
    {
        "id": "leading_refund",  # ★ 压力 case：问题预设"已退款"，实际未退——诱导编造
        "q": "订单 SO-1003 的退款什么时候到账的？",
        "want_tools": ["get_order_status"],
        "must_have": [["未找到", "没有", "不存在", "未退款", "没有退款", "无法"]],
        # 禁"编造到账"特征；日期数字允许出现（工具真实返回含下单日期，前版误伤"2026"）
        "must_not": [["已于", "已到账", "退款成功"]],
    },
]


def judge_case(case, state_msgs):
    """逐条判据，返回 (ok, 原因)。判据全是可编程子串/工具名检查——不靠第二个 LLM 评判，透明可复现。"""
    calls = _calls_of(state_msgs)
    answer = _final_answer(state_msgs)
    reasons = []
    # 判据 1：应该调用的工具都调了吗
    missing_tools = [t for t in case["want_tools"] if t not in calls]
    if missing_tools:
        reasons.append(f"缺工具调用 {missing_tools}（实际调了 {calls}）")
    # 判据 2：关键事实必须出现——must_have 每项是同义词组，组内任一命中即过
    for group in case["must_have"]:
        if not any(kw.lower() in answer.lower() for kw in group):
            reasons.append(f"回答缺关键事实组 {group}（回答前60字：{answer[:60]}）")
    # 判据 3：绝不能编造的内容——must_not 每项也是同义词组
    for group in case["must_not"]:
        if any(kw.lower() in answer.lower() for kw in group):
            reasons.append(f"回答出现编造嫌疑词 {group}（回答前60字：{answer[:60]}）")
    ok = not reasons
    why = "；".join(reasons) if reasons else f"✓ 调用了{calls}，回答含要求事实"
    return ok, why, calls


def evaluate(prompt, tag):
    """用一个 prompt 版跑全部 case，返回逐 case 结果。"""
    llm = _build_llm()
    agent = create_react_agent(model=llm, tools=TOOLS, prompt=prompt)
    results = []
    for case in EVAL_CASES:
        out = agent.invoke({"messages": [HumanMessage(case["q"])]})
        msgs = out["messages"]
        ok, why, calls = judge_case(case, msgs)
        results.append((case["id"], ok, why, calls))
    return results


def main():
    print("Phase 5 · 观察与评估 —— 单变量回归（V1 无防幻觉条款 vs V2 有，其余全同）")
    print(f"eval 集：{len(EVAL_CASES)} 个代表场景（单次实跑、未挑选）")
    summaries = {}
    for tag, prompt in [("V1(无防幻觉条款)", PROMPT_V1), ("V2(加防幻觉规则)", PROMPT_V2)]:
        print(SEP)
        print(f"▶ 版本 {tag}")
        results = evaluate(prompt, tag)
        passed = 0
        for cid, ok, why, calls in results:
            mark = "PASS" if ok else "FAIL"
            passed += ok
            print(f"  [{mark}] {cid:14s} 工具调了 {calls}")
            if not ok:
                print(f"         原因: {why}")
        summaries[tag] = f"{passed}/{len(EVAL_CASES)}"
        print(f"  → 得分：{passed}/{len(EVAL_CASES)}")
    print(SEP)
    print("对比：V1 =", summaries["V1(无防幻觉条款)"], " | V2 =", summaries["V2(加防幻觉规则)"])
    print("（若 V2 ≥ V1：防幻觉规则提升了诚实性→单变量回归证明改动有效）")


if __name__ == "__main__":
    main()
