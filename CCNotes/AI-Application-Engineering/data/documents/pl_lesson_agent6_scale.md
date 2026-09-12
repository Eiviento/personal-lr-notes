# Phase 6 · 规模化与版本演进：V2 迁移 + subgraph 子图

> 2026-09-06。最后一课：处理版本演进（弃用警告→迁移）+ 规模化拆分（子图）。配套脚本 `scripts/agent6_scale.py`，实跑 exit 0（Part A 真实 API 两次小对话；Part B 零 API），留档 `outputs/agent6_scale_run.log`。

## 一、版本演进：create_react_agent → create_agent

**背景**：从 W1 起每个脚本都伴着一句弃用警告（实测原文）：
```
create_react_agent has been moved to `langchain.agents`.
Deprecated in LangGraph V1.0 to be removed in V2.0.
```
它没坏、能用，但官方已宣布 V2.0 移除——**不迁移就是在攒技术债**。迁移的差异小得惊人（实测对照）：

| | V1（旧） | V2（新） |
|---|---|---|
| 导入 | `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| 人设参数名 | `prompt=PROMPT` | `system_prompt=PROMPT` |
| 其余（model/tools/checkpointer/interrupt…） | 同 | 同 |
| 构建弃用警告 | **1 条** | **0 条** |

实跑：同一问题（查 SO-1003）V1/V2 都正确回答；V1 构建时 1 条弃用警告、V2 干净。
**迁移 = 换一行 import + 参数名 prompt→system_prompt**，其余不动。这是 LangChain 生态"API 会演进"的实例——P2 学的"显式优于默认、用前读源码"在这里又应验一次：跟着弃用警告走，别等它真的移除。

## 二、规模化：subgraph（子图）

**问题**：agent 功能越来越多（检索、查单、退款、审批…）全塞一张图会失控。**拆分 = 把一小段流程编成独立小图（subgraph），当节点嵌进大图**。

本课演示：客服主图 = `classify(分类) → 路由 → 订单子图 或 知识子图 → 结束`。实测：
- 用户问"我的订单 SO-1003 在哪？" → classify 判 `order` → **订单子图**返回 `订单 SO-1003：SmartHome 温湿度传感器（Zigbee）`
- 用户问"七天无理由退货怎么算？" → classify 判 `knowledge` → **知识子图**返回 `退换货政策`

关键认知（对应代码）：
1. **子图就是 compile 过的 StateGraph**（`build_order_subgraph()` / `build_knowledge_subgraph()` 各自独立小图，可单独测试）。
2. **父图把子图当普通节点**：`p.add_node("order", to_order)`——`to_order` 内部调 `order_sub.invoke({...})` 喂子图自己的 state 字段、取回结果。子图对父图是黑盒。
3. **子图有自己的 state 形状**（`OrderState` 只要 order_id/result），父图只需在节点函数里做字段搬运。
4. **路由照旧用条件边**：`classify` 输出 kind → `route` 返回节点名 → 引擎走向对应子图。

**价值**：每块能力独立可测（子图单独跑）、可复用（换个父图照样嵌）、可扩展（加新能力=加个子图+路由分支），是 agent 从 demo 走向产品的标准拆法。对标 LangChain-RAG-Agent 的 RAG 链/审批流程——都能包装成子图嵌进大 agent。

## 三、六课收官：你现在掌握的 agent 全景

| Phase | 你获得的能力 |
|-------|-------------|
| 1 拆黑盒 | 理解 agent=循环、图机制、封装无魔法 |
| 2 护栏 | recursion_limit / 重复熔断 / 异常回流——循环不失控 |
| 3 记忆 | checkpointer 持久化、thread_id、token 治理——不失忆 |
| 4 可靠 | interrupt 人审、验证节点防幻觉——不擅动不编造 |
| 5 评估 | eval 集 + 判据 + 单变量回归——能证明改好改坏 |
| 6 规模化 | 版本演进应对、subgraph 拆分——能长大能续命 |

## 四、复现与证据

```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent6_scale.py
```

## 五、踩坑速记

- create_agent（V2）的**人设参数是 `system_prompt` 不是 `prompt`**——用旧参数名会 TypeError 或静默不生效（实测迁移成功路径见 Part A）。
- 子图 invoke 用**子图自己的 state 字段**，父图节点做字段搬运——别指望子图自动共享父图 state（两者 state 形状独立）。

## 六、三问法精读指引

1. Part A 为什么 V1/V2 "其余参数同"？迁移为什么这么小？（答：create_agent 就是官方把同一张 agent 图换个家——本质没变，只是移进 langchain.agents 并统一命名）
2. 子图对父图是什么？父图节点 `to_order` 做了什么搬运？（答：子图=黑盒节点；父图把父 state 字段组装成子图输入、调用、把子图输出写回父 state 字段）
3. classify 节点和 P2 的条件边路由是什么关系？（答：同一机制——节点产出判断、条件边函数按判断返回节点名；只是这里"目的地"是子图）
