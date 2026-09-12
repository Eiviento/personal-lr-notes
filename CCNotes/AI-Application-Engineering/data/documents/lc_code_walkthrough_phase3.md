# 代码精读 5：phase3_1_doc_input.py（喂文件版）

> 功能升级：从"命令行一句话"升级到"喂整个文档文件"。三个新问题：编码 / 大小 / 噪声。

## 执行示例（实测）

| 示例 | 命令 | 证明什么 |
|------|------|---------|
| 零成本编码演示 | 同一堆 GBK 字节用三种编码解读 | utf-8-sig/utf-8 失败、gb18030 成功——编码自适应防的就是这个 |
| 真实运行 | `phase3_1_doc_input.py inputs/sample_requirement_gbk.txt` | GBK 文件直喂不崩不乱码；503 字符≈503 token；噪声文档提取出干净 6 字段协议 |

## 四块

### A. read_doc 编码自适应

```python
for encoding in ("utf-8-sig", "utf-8", "gb18030"):
    try: return Path(...).read_text(encoding=encoding)
    except UnicodeDecodeError: continue
raise ValueError(...)   # 三种都不行，带着证据报错
```

- 顺序原则：**常用优先（utf-8 现代主流），超集兜底（gb18030 ⊃ GBK）**
- 前两次失败发生在 except 里，对调用者透明

### B. 大小检查

- 估算：中文 1 字符 ≈ 1 token
- 上限 30000：64K 上下文留一半余量
- 超限截断 + 警告 = **权宜之计**；根治是 Phase 4 RAG（切片+检索）

### C. 噪声提取（本讲核心思想）

- 输入文档含硬件选型/部门分工/背景故事（全是废话），输出干净协议
- **全文直塞，不写解析规则**：需求千变万化写不出规则；"从噪声提关键信息"是 LLM 强项
- Prompt 只加一行："忽略与协议无关的内容"
- 实测连"时间戳不用我们加（网关会加）"这种反直觉要求都正确执行了

### D. main 流程

三个变化：argv[1] 是文件路径；输出名跟输入走（`<stem>_protocol.json`）；链和 Prompt 复用 2.1——**零件复用第一次真实兑现**。

---

# 代码精读 6：phase3_2_prompt_chain.py（四步链，项目心脏）

> 读法核心一个词：**物流标签**——占位符名 = 挂键名 = 下游取用名，三处一致。

## 执行示例（实测）

`phase3_2_prompt_chain.py inputs/sample_requirement.md`：三个【中间产物】区块逐段打印（①8 条要点 → ②6 字段 JSON → ③6 约束 + 4 评审发现），最终合并协议。③ 抓到一段式发现不了的交叉约束（"固件版本仅在 0x03 消息有效"）。

## 五块

### A. 三份说明书：占位符 = 物流接口

| Prompt | 占位符 | 产出 |
|--------|--------|------|
| ANALYZE_PROMPT | `{requirement}` | key_points 纯文本 |
| FIELDS_PROMPT | `{key_points}` | fields JSON |
| RULES_PROMPT | `{key_points}` + `{fields}` | checks JSON |

每步占位符名 = 上一步产物的名字。

### B. 三条子链 + tap

- 子链与 2.1 完全同构（prompt \| llm \| parser）——组装能力复用为零件
- ① 用 Str、②③ 用 Json：兑现 2.3 选型口诀
- `tap` = RunnableLambda 观察者：打印中间产物后**原样返回**，不污染数据流；调试完摘掉链照跑

### C. full_chain：assign 挂键

`assign(键名=子链)` = "跑子链，结果挂到 dict 的这个键上"，dict 逐步长胖：requirement → +key_points → +fields → +checks → merge。

坑（实测撞过）：挂键名必须与下游占位符同名，否则管道当场报错——报错是防漏配的保护机制。

### D. merge_final：纯 Python 合并

机械活不用 LLM：省一次调用、绝不手滑改字段。**LLM 做推理，Python 做拼装。**

### E. main

同 3.1；print_result 多打约束规则与评审发现两段。

## 自测

1. 三个 Prompt 的占位符分别是什么？为什么不同？
2. assign 挂键名的规则？
3. ④ 为什么 Python 不用 LLM？

---

# 精读 6.5：并行分支 + 合并汇总（用户自己设计的模式）

> 用户（2026-08-29）在学习中独立提出：两段提示词分别读文件、各自解析、合并后喂一次 API 出最终结果。已实现为 `scripts/demo_parallel_merge.py`，业界叫 Map-Reduce 简化版。

## 数据流

```
文档 → ├─ 提示词A（数据字段视角）→ 结果A ─┐
       └─ 提示词B（异常场景视角）→ 结果B ─┤（并行）
                                          ▼
                 RunnableParallel 自动合并成 {"a":…, "b":…}
                                          ▼
                 FINAL_PROMPT（占位符 {a} {b}）→ 最终协议
```

## 三个要点

1. 两分支互不依赖（都只读原始文档）→ 可并行；有依赖就退回 3.2 串行链
2. **合并是免费的**：RunnableParallel 产出天然是合并后的 dict，连 Python 合并代码都不用写
3. 最终 Prompt 占位符与分支键名（a/b）直接对接

## 实测效果（比 3.2 串行链更强）

两视角平级并行，异常视角信息从源头喂给汇总：
- 分支 B 产出 15 条异常场景（传感器故障 0xFF 特殊值、低电量告警迟滞区间 18%~22%、alarm_flag 位图、向前兼容）
- 最终协议 7 字段，每个字段 description 写清异常处理——3.2 的"事后评审"发现不了的东西，源头分析直接带进去了

## 决策标准

| 条件 | 选型 |
|------|------|
| 分支互不依赖 | 并行（本模式）——省时间、视角平等 |
| 后一步依赖前一步 | 串行（3.2 四步链） |

---

# 代码精读 7：phase3_3_batch_stream.py（三种调用方式）

> 同一条链，换调用方式：invoke / batch / stream。

## 执行示例（实测）

- batch 2 份文档：`✓ 环境监测协议（6 字段）` + `✓ 智能水表协议（9 字段）`，一次出
- stream：要点逐条吐（打字机效果）

## 四块

### A. clean_chain：同样的零件，两种装法

零件（analyze/fields/rules/merge）一字未改，只摘掉 tap：3.2 full_chain = 调试版（中间产物全打印），3.3 clean_chain = 生产版（安静跑）。透视：4 层 = 3×RunnableAssign + RunnableLambda（RunnableAssign 就是 assign() 的积木真名）。

### B. do_batch

`chain.batch([输入列表])` → 结果列表，顺序对应，**内部并发**。输出文件名跟输入走，批量不互相覆盖。用途：攒一批同事需求文档一次全生成。

### C. do_stream

`chain.stream(输入)` 逐块吐。**关键细节：RunnableLambda 是流式边界**——full_chain 里有 RunnableLambda(merge_final)，流到它面前被缓冲成完整结果，流式就断；analyze_chain 是纯 prompt|llm|parser，token 畅通。Web UI 的打字机效果靠它。

### D. main 子命令分发

`sys.argv[1]` 当子命令（batch/stream）——CLI 工具标准设计（git commit/git push 同款）。单功能脚本 → 多命令工具的第一次。

## 自测

1. clean_chain 和 full_chain 的零件一样吗？区别？
2. batch 和循环 invoke 的区别？
3. 流式为什么用 analyze_chain 不用 full_chain？

## invoke / batch / stream 详解（用户追问，零成本演示）

> 可运行：`scripts/demo_invoke_batch_stream.py`（sleep 函数包装成积木，让差异看得见）

| | 输入 | 输出 | 等待方式 | 类比 | 本项目场景 |
|---|---|---|---|---|---|
| `invoke(x)` | 1 个 | 1 个 | 同步全等 | 点一份外卖 | 日常单次生成 |
| `batch([x1,x2,x3])` | 列表 | 列表（**顺序与输入对应**） | **内部并发** | 同时点三份外卖 | 批量处理同事文档 |
| `stream(x)` | 1 个 | 逐块流（每 yield 收一块） | 边等边收 | 开放式厨房炒一道上一道 | UI 打字机效果 |

实测：3 个各需 1s 的任务，batch 总耗时 1.0s（并发，非串行 3s）；stream 每 0.4s 收到一个词。

关键点：三者是**同一条链上的三种方法**，链一个字不用改——LCEL 统一接口的红利：组装一次，三种用法全有。

### stream 的"感觉"问题（用户追问）

用户反馈 phase3_3 的 stream"没感觉"——原因：**DeepSeek 返回的块很大**（一次一整条要点），控制台里瞬间全出，和 invoke 视觉无差。

核心认知（时间戳演示 `scripts/demo_stream_feel.py`）：

- stream **不是更快**，总耗时一样；差别是**首字延迟**：invoke = 总时长（盯空白转圈 10~30s），stream ≈ 1s（立刻有字可看）
- 控制台里难感受是正常的（网络快 + 块大）；真正"有感觉"的地方是 **Web UI 打字机效果**（`st.write_stream`）
- app.py 目前用 invoke（spinner 转圈）——未来升级点：把中间文本流到页面

---

# 代码精读 8：generate_protocol.py（3.4 验收，Phase 3 收官）

> 最终交付物：**文件路径进 → 协议 JSON + Markdown 双文件出**。

## 执行示例（实测）

2 份文档 batch 并发 → 各产出 `<名称>_protocol.json` + `<名称>_protocol.md`。水表协议文档：9 字段、5 约束、8 条评审发现（含"时间戳 uint32 到 2038 年溢出"）。

## 三块

### A. chain 组装

与 3.3 clean_chain 一模一样，零新逻辑——**新功能 = 旧零件的重新排列**，零件库攒起来后的开发方式。

### B. render_markdown（唯一新知识）

**JSON 是数据（程序用，LLM 出），Markdown 是呈现（同事看，Python 出）**——与 ④ 合并不用 LLM 同一原则：确定性工作交给代码，渲染一万次一个样。

| 文档段落 | 代码 |
|---------|------|
| 标题/描述 | f-string 拼 `# ...` |
| 字段表 | 循环 fields 拼 `\|` 分割的 Markdown 表格 |
| 约束规则 | `enumerate(..., 1)` 编 1/2/3 号 |
| 评审发现 | 按 severity 加 `[error]`/`[warning]` 前缀 |
| 页脚 | "请人工审核后发布"常量 |

`audit` 参数是 4.3 加的：传入审核记录 → 文档多"审核记录"节，页脚变"已通过人工审核"。

### C. main 三个新细节

1. invoke/batch 自动分流（1 份 invoke，多份 batch）
2. 两层错误处理：FileNotFoundError 单独 catch + 通用 catch
3. 最后一行 `✅ Phase 3 验收通过` = Phase 3 的定义完成

## 自测

1. JSON 和 Markdown 的分工？
2. 为什么渲染用 Python 不用 LLM？
3. 1 份和 3 份输入分别走什么调用？

---

*Phase 3 代码精读完结。Phase 4（RAG/工具/人工审核）后续追加。*
