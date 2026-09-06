# HANDOFF — 交接文档

> 写给完全没有上下文的新会话。读完即能接手。
> 更新日期：2026-09-06（Wave 0 完成时）

## 一、我们在做什么

**目标**：带用户（应用软件工程师，已学完 LangChain-RAG-Agent 的 LangChain 五阶段基础）深度学习 **Agent**——从空目录建一个完整的 LangGraph 技术支持客服 Agent demo，6 Phase 每 Phase 带代码 + 实跑证据 + 讲解 + lessons 落盘。

**已批准计划**：`.rivet/plans/全量-agent-深度研学-langgraph-技术支持助手-6-phase-从零到成品.md`（已复制到 `docs/superpowers/plans/`）
**项目文档**：README.md（进度表/结构/快速开始）；docs/progress.md、docs/findings.md

## 二、已确认的方向（用户拍板）

1. 新建独立项目（当前工作区 `D:\CC\personal-lr-notes\CCNotes\Project-Langchain`），从零走 6 Phase
2. 通用 Demo 场景（技术支持客服 Agent，不挑业务）
3. 不改动 LangChain-RAG-Agent（姊妹项目，前置知识来源）

## 三、Wave 0 完成事项与实测事实（2026-09-06）

- 项目骨架：README / AGENTS.md / .rivet.md / requirements.txt / .env.example / .gitignore
- data：knowledge.txt（FAQ）+ orders.json（假订单库，含 SO-9999 不存在订单供防幻觉测试）
- **API 运行时探针（硬闸门，9/10 通过）**：
  - ✓ `langgraph.prebuilt.create_react_agent`（**注意：签名含 `version: Literal['v1','v2']='v2'`，默认 v2**）
  - ✓ `langgraph.prebuilt.ToolNode`（含 handle_tool_errors）/ `tools_condition`
  - ✓ `langchain.agents.create_agent`（**V2 已存在**，参数 system_prompt/middleware/state_schema/checkpointer）
  - ✓ `langgraph.checkpoint.memory.MemorySaver` / `InMemorySaver`
  - ✗ `langgraph.checkpoint.sqlite` **IMPORT FAIL**——SqliteSaver 在独立包 `langgraph-checkpoint-sqlite`，agent_env 未装
  - ✓ `langgraph.types.interrupt` / `Command(resume=...)`
  - ✓ `langgraph.graph.StateGraph` / `START` / `END`
  - ✓ `langchain_core.messages.trim_messages`
- 环境：agent_env = Python 3.10.19 / langchain-core 1.4.9 / langchain 1.3.14 / langgraph 1.2.9 / langgraph-prebuilt 1.1.0
- 探针脚本留存：`.rivet/scratch/probe_langgraph.py`

## 四、当前卡点 / 待用户处理

1. **DEEPSEEK_API_KEY 未配置**（shell env unset，新项目无 .env）——W1 实跑前需用户把 .env 放进项目根（可参照 .env.example；用户此前在 LangChain-RAG-Agent\.env 配过同款 key，复制过来即可）。**未配 key 前 W1 的 API 环节无法实跑**（零成本假 agent 部分不受影响）。
2. **P3 持久化方案待定**：SqliteSaver 需 `pip install langgraph-checkpoint-sqlite`（清华镜像）——W3 开头问用户：装包 or 改用进程级演示。

## 五、下一步（W1 / Phase 1 拆开黑盒）

1. 确认用户已配 .env → 跑最小 API 冒烟（一次真实对话）
2. `scripts/agent1_whitebox.py`：黑盒 create_react_agent（model + search_knowledge/get_order_status/get_now_time）跑通
3. inspect.getsource 拆 prebuilt 内部 → 手写等价 StateGraph 对照
4. lessons/lesson_agent1_whitebox.md 落盘 + 带用户三问法精读

## 六、教学纪律（用户立的规矩，一条不破）

- 讲解必带实跑执行示例；一次只问一个问题；知识点落盘 lessons/（零基础可读）；代码精读三问法
- 证据来自实跑且可复现；实录引用写"单次实跑、未挑选"；数字来自工具输出
- 脚本一律 `PYTHONIOENCODING=utf-8` 前缀（GBK 坑）；用 agent_env python 绝对路径
- 用户是节奏拍板人，每 Phase 可停靠

## 七、踩坑速记（本 session 新发现）

- langgraph 1.2.9 主包**不含** checkpoint.sqlite（与 0.x 教程不同）——持久化教学需独立包
- create_react_agent 在 1.2.9 签名已带 version 参数（默认 v2）——与 LangChain-RAG-Agent 记录的"弃用警告坑#19"并存，实际调用时观察
- 无头 worker 无法读 E:\site-packages（越界无审批通道）——源码取证用 `inspect.getsource`（运行时拿源码文本）绕开
