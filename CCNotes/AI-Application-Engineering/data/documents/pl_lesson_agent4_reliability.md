# Phase 4 · 可靠性与人在回路：interrupt 审批 + 防幻觉验证节点

> 2026-09-06。回答"agent 怎么在写操作前停下来等批准、怎么防它编造"。两个实验零 API 实跑（确定性演示机制），配套脚本 `scripts/agent4_interrupt.py`。

## 一、人在回路：interrupt 原语（实验 1）

**为什么需要**：退款是**写操作**（真金白银），不能让 agent 自己拍板——万一模型误判就真退款了。正确设计：图跑到"执行退款"前**暂停**，把待审信息抛给外部（人/审批系统），拿到批准才继续。

LangGraph 的 `interrupt()` 就是这个"暂停键"。实测流程（1.2.9）：

```
[用户] 申请退款 SO-1003（理由：商品质量问题）
① 收集退款请求 → 走到 approval 节点
② ⏸ approval 调 interrupt({...待审信息}) → 图暂停，invoke 返回 __interrupt__ 快照
   （state 里带 __interrupt__: [Interrupt(value={order_id, reason}, id=...)] —— 不抛异常！）
[外部审批者 客服经理] 决定：approved
③ 再次 invoke + Command(resume="approved") → 从断点恢复，
   approval 节点里的 interrupt() 返回 "approved" → 图继续 → finalize 执行退款
流程历史: ['请求退款 SO-1003', '退款已执行']
```

**两个实测关键点（写代码前必须知道）**：
1. **中断不抛异常**：第一次 invoke 正常返回，暂停信息在结果 state 的 `__interrupt__` 键里（含你传给 interrupt 的 payload + 一个 id）。
2. **恢复必须挂 checkpointer**：`Command(resume=...)` 需要能定位"停在哪一步"→ 必须 `compile(checkpointer=...)` 且两次 invoke 用**同一 thread_id**。**P4 的人机协作依赖 P3 的记忆快照**——interrupt 是"断点续跑"，checkpointer 是断点的存档。

拒绝分支对照：外部决定 `denied` → resume 后 finalize 走拒绝路径，**不执行退款**。审批决策权完全在外部代码手里，模型碰不到。

**设计原则**：把"请求"和"执行"分开——collect 只收集，approval 只暂停，finalize 才真正动钱。interrupt 之前的节点都是无副作用的准备，副作用全在恢复之后。生产里审批者可换成真实 API/人审界面。

## 二、防幻觉纵深：验证节点（实验 2）

背景（继承 LangChain-RAG-Agent 坑 #18）：模型会编造"听起来对"的内容——它不知道订单 SO-0000 不存在，照样声称"已退款 399 元"。

**纵深防御 = 不信模型的嘴，只信工具的返回**。加一个验证节点：模型生成回答后，把回答里的**关键事实主张**提取出来交给真实工具核对，对不上就拦截/修正。实测两个场景：

```
场景 A · 模型对不存在的 SO-0000 声称已退款
  [模型生成] 订单 SO-0000 已经为您办理退款了…
  【验证拦截】订单 SO-0000 根本不存在——模型编造了订单号。已改为如实答复。

场景 B · SO-1003 真实存在但状态是 delivered（未退款），模型仍声称已退款
  【验证拦截】工具显示状态未退款——模型声称已退款是编造。已改为如实转述工具结果。
  工具返回: 状态：delivered
```

**对照（为什么必须有验证节点）**：不加验证，模型那句"已退款请放心"就会原样发给用户——用户以为退成功了，实际没有。加了验证节点后，**模型生成 → 工具核对 → 不一致就替换成工具的事实**。这与 P1/P2 学的"工具返回错误要如实转述"是同一根：**事实来自工具/检索，模型输出只是候选，要过验证关**。

## 三、两个机制的关系（P3→P4 的递进）

| 机制 | 防什么 | 依赖 |
|------|--------|------|
| interrupt 人在回路（P4） | 模型擅自执行写操作 | checkpointer 状态快照（P3） |
| 验证节点（P4） | 模型编造事实/动作 | 可靠的工具（P1/P2） |
| 护栏（P2） | 循环失控 | 图条件边 |

可靠 agent = 图结构护栏（P2）× 记忆（P3）× 写操作交人审 + 输出过验证（P4）。

## 四、复现与证据

```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/agent4_interrupt.py
```
（零 API；输出见终端。interrupt 机制探针在 .rivet/scratch/interrupt_probe.py——记录了 1.2.9 实测：无 checkpointer 时 Command(resume) 报 RuntimeError）

## 五、踩坑记录（实测）

- `Command(resume=...)` 无 checkpointer → `RuntimeError: Cannot use Command(resume=...) without checkpointer`。
- 中断返回形态是 state 带 `__interrupt__`（非异常）——从 `out.get("__interrupt__")[0].value` 取待审 payload。
- TypedDict schema 严格要求：节点返回 dict 的键必须都在 state 类型里声明（漏 `decision` 键会报 unknown channel）——先声明字段再写节点。

## 六、三问法精读指引

1. approval 节点的 `interrupt()` 在批准/拒绝两条路径里各执行到哪？为什么"副作用只能在恢复后"？（答：interrupt 前是无副作用准备；真正动钱在 finalize——保证暂停时没发生不可逆操作）
2. 实验 2 验证节点的"拦截"改成了什么？（答：把模型编造文本替换成工具的真实返回——诚实信号优先于流畅表述）
3. 为什么两次 invoke 必须同一 thread_id？（答：resume 要靠 checkpointer 按 thread 找回断点 state）
