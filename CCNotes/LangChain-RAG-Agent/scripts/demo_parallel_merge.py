"""
并行分支 + 合并汇总 演示（Map-Reduce 简化版）
============================================
你设想的结构：两段提示词分别读文件 → 各自解析 → 合并 → 一次 API 出最终结果。

数据流：
  需求文档
    ├─► 提示词A（数据字段视角）→ 结果A ─┐
    └─► 提示词B（异常场景视角）→ 结果B ─┤（两分支互不依赖，同时跑）
                                        ▼
                      合并（A+B 拼成一段上下文）
                                        ▼
                      最后一次 API 请求 → 最终协议 JSON

关键条件：两个分支必须互不依赖（都只读原始文档）。
如果 B 需要 A 的产出，就退回 3.2 的串行链。

用法：python demo_parallel_merge.py <需求文档>
"""

import json
import sys

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel

from phase3_1_doc_input import read_doc
from phase3_2_prompt_chain import llm

# 提示词A：数据字段视角
PROMPT_A = ChatPromptTemplate.from_messages([
    ("system", "你是协议工程师。从【数据字段视角】分析需求文档：需要上报哪些数据字段、"
               "什么类型、上报频率。输出中文要点列表，纯文本。"),
    ("user", "{requirement}"),
])

# 提示词B：异常场景视角
PROMPT_B = ChatPromptTemplate.from_messages([
    ("system", "你是协议评审专家。从【异常场景视角】分析需求文档：有哪些告警、边界条件、"
               "异常情况需要协议处理。输出中文要点列表，纯文本。"),
    ("user", "{requirement}"),
])

# 最终提示词：吃合并后的 A+B
FINAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "综合以下两份分析结果，输出最终协议字段表 JSON。严格输出 JSON，不要包含其他内容：\n"
               "{{"
               "\"protocol_name\": \"协议名称\","
               "\"description\": \"协议用途\","
               "\"fields\": [{{\"name\":\"...\",\"chinese_name\":\"...\",\"type\":\"...\",\"length\":字节数,\"unit\":\"...\",\"range\":\"...\",\"description\":\"...\"}}],"
               "\"timing\": {{\"report_interval\":\"...\",\"direction\":\"上行/下行/双向\"}}"
               "}}"),
    ("user", "【数据字段视角分析】\n{a}\n\n【异常场景视角分析】\n{b}"),
])


def tap(name: str):
    """观察者：打印分支产出后原样返回"""
    def _tap(x):
        print(f"\n{'─'*60}\n【{name}】\n{x}")
        return x
    return RunnableLambda(_tap)


# 组装：并行两分支 → 分支结果合并成 {a, b} dict → 直接喂最终 Prompt（占位符 {a} {b}）
pipeline = (
    RunnableParallel(
        a=PROMPT_A | llm | StrOutputParser() | tap("分支A：数据字段视角"),
        b=PROMPT_B | llm | StrOutputParser() | tap("分支B：异常场景视角"),
    )
    | FINAL_PROMPT | llm | JsonOutputParser()
)


def main():
    doc = read_doc(sys.argv[1] if len(sys.argv) > 1 else "inputs/sample_requirement.md")
    print("⏳ 两分支并行分析 → 合并 → 最终 API 汇总...")
    result = pipeline.invoke({"requirement": doc})

    print(f"\n{'='*60}\n【最终结果】")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
