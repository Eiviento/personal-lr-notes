# Findings — 决策与事实记录

## 2026-09-06

### F1: langgraph 1.2.9 无内置 SqliteSaver（计划偏离）
- **事实**：`langgraph.checkpoint.sqlite` import 失败（ModuleNotFoundError）。SqliteSaver 在独立分发包 `langgraph-checkpoint-sqlite`，agent_env 未安装。
- **影响**：计划 W3（记忆持久化）原定 SqliteSaver 落盘。0.x 时代的 `langgraph.checkpoint.sqlite` 心智模型不适用于 1.2.9 主包。
- **决策（暂定）**：W3 开头问用户二选一——装 `langgraph-checkpoint-sqlite`（清华镜像）实现真落盘，或用 MemorySaver + 教学说明降级。倾向装包（P3 教学价值在"重启不丢"）。

### F2: create_react_agent 1.2.9 签名已带 version 参数（默认 v2）
- **事实**：探针显示 `create_react_agent(..., version: Literal['v1','v2']='v2', ...)`。langchain.agents.create_agent（V2）已存在（system_prompt/middleware/state_schema 参数体系）。
- **影响**：教学主线（P1 拆黑盒用 create_react_agent）可行；P6 迁移教 create_agent 有真身。实际调用时观察是否仍有弃用警告，如实记录。

### F3: DEEPSEEK_API_KEY 未就绪
- **事实**：shell env unset，新项目无 .env。
- **影响**：W1 API 环节前需用户配 .env（参照 .env.example）。零成本假 agent 演示不受影响。

### F5: SO-9999 反例改用"库中无此单"（审查修复）
- **问题**：初版 orders.json 把 SO-9999 实现为数组内 `status=not_found` 的真实行——线性查找会命中并返回"存在但状态特殊"的歧义信号，弱代理了"查无此单"。
- **修复**：删除该行。防幻觉/诚实测试用**库里不存在的订单号**（如 SO-0000），由 get_order_status 查找不到返回"未找到"承载。数据形状与真实语义对齐。

### F6: DEEPSEEK_API_KEY 不在 LangChain-RAG-Agent\.env
- **事实**：该 .env（325B）仅含 LANGSMITH_API_KEY；Windows cmd 环境变量也无 DEEPSEEK_API_KEY。
- **推论**：LangChain-RAG-Agent 跑 API 脚本时的 key 来自会话内临时设置（未持久化），或 key 另存他处。新项目 .env 待用户提供 DEEPSEEK_API_KEY 值后补入。脚本统一用 python-dotenv load_dotenv() 加载。

### F4: 无头 worker 读不了 E:\site-packages
- **事实**：两个 code_scout 因 E: 越出工作区被结构性阻断（无审批通道）。
- **应对**：教学源码取证一律用 `inspect.getsource`（运行时拿源码文本），绕过文件授权。

### F7: SqliteSaver 装包决策落地（2026-09-06，W3）
- **决策**：用户同意 → `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langgraph-checkpoint-sqlite` 已装，版本 **3.1.1**。
- **实测 API 形态**（import + inspect）：`langgraph.checkpoint.sqlite` 仅导出**同步 `SqliteSaver`**，**无 `AsyncSqliteSaver`**；`SqliteSaver.from_conn_string(conn_string)` 是**生成器工厂**（返回 `Iterator[SqliteSaver]`），用法 `with SqliteSaver.from_conn_string(...) as saver:`。与 0.x 教程的 `SqliteSaver(conn)` 构造不同，教学代码按 3.x 形态写。
- **probe_api.py 基线已更新**：SqliteSaver expected False→True；AsyncSqliteSaver 保持 False（包未导出）。探针验证 exit 0 = 与新基线一致。

## 2026-09-08（Phase 7 客服工作台）

### F8: V2 create_agent + checkpointer + 工具内 interrupt 组合成立（方案 A）
- **事实**（`.rivet/scratch/probe_p7_api.py`，agent_env 实测，exit 0）：
  - H1：`langchain.agents.create_agent` 签名含 `checkpointer`（完整参数：model/tools/system_prompt/middleware/response_format/state_schema/context_schema/checkpointer/store/interrupt_before/interrupt_after/debug/name/cache/transformers）
  - H2：工具函数内直接调 `interrupt({...})` → 图暂停，invoke 返回 `__interrupt__`；`Command(resume="approved")` 同 thread 恢复，`interrupt()` 返回 resume 值 ✅
  - H3：V2 create_agent 与 `langgraph.checkpoint.sqlite.SqliteSaver`（3.1.1 同步）组合编译成功 ✅
- **影响**：Phase 7 主图采用方案 A（V2 create_agent 一条龙），无需退回 P4 的手写 StateGraph。P4 的 interrupt 在**节点**里，P7 首次验证在**工具**里——这是真实 ReAct agent 里审批落点的正确位置。
- **探针首跑假失败教训**：H2 首次报 ❌ 并非机制不支持，而是探针自身缺陷——① 假模型 `bind_tools()` 未接受 create_agent 传入的 `tool_choice` 关键字；② 假模型发的 tool_call `args={}` 缺工具必填参数，pydantic 校验在 interrupt **之前**就报错。修复探针（`**kwargs` + 传参）后全 ✅。**归族**：验证"机制支持性"时，须确认失败发生在被测机制层，而非测试脚手架自身的错误。

### F9: streamlit 已可用 + UI 渲染噪音坑（Phase 7 实测）
- **事实**：agent_env 已装 streamlit 1.62（姊妹项目 requirements 含）；`browser_debug` 自带 chromium 未装，改用系统 Chrome `--remote-debugging-port=9222` + `connect_url` 连 CDP 成功。
- **UI 坑**：真实 LLM 的一条用户消息内部 jsonl 会 produce「带 tool_calls 的中间 AIMessage + ToolMessage（工具原始返回）+ 最终答复」；初版 UI 全渲染 → 界面出现英文 preamble 与订单原始数据。修复 = 只渲染 `HumanMessage` 与「无 tool_calls 的 AIMessage」。见 lesson_agent7 第六节。
- **streamlit rerun 坑**：审批按钮回调里若手动渲染 resume 结果又 `st.rerun()`，rerun 后从 checkpointer 拉的历史会重复渲染一次。修复 = 回调只 resume+清 pending+rerun，结果由 rerun 后的历史渲染带出（印证"checkpointer 即真相源"）。

### F10: streamlit 条件 import 导致 NameError（Phase 7 用户实跑抓到的 bug）
- **现象**（用户实跑）：点侧栏「🆕 新建会话」→ `NameError: name 'uuid' is not defined`（app.py:68）。
- **根因**：`import uuid` 写在 `if "thread_id" not in st.session_state:` 块内。streamlit 每次交互**重新执行整个脚本**（模块命名空间重建），而 `st.session_state` **跨 rerun 持久**——首次运行后 thread_id 已在，if 分支不再进入 → `import uuid` 不再执行 → 点新建会话时用到 uuid 即 NameError。
- **修复**：`import uuid` 移到模块顶部；给按钮加 `key="new_chat"` 便于测试定位。
- **测试缺口**：原 AppTest 只覆盖「渲染/发消息/审批/批准」，未覆盖「点新建会话」→ 漏网。已补回归断言（点击后断言无异常 + thread_id 变更），修复前该断言 RED（复现同一 NameError），修复后 GREEN。
- **教训**：streamlit 脚本里 import 一律放模块顶部——rerun 重建命名空间，任何"条件才执行"的 import 都可能在某次 rerun 被跳过。

### F11: 刷新丢历史——thread_id 未持久化（Phase 7 用户实跑抓到）
- **现象**（用户："历史会话没看到"）：F5 刷新页面后 thread_id 变、聊天历史清空。
- **根因**：`thread_id` 只存 `st.session_state`，而 session_state 绑定浏览器会话，**F5 刷新即重置** → 生成新 thread → 虽然旧对话仍在 checkpointer 里，UI 却找不回那个 thread。**checkpointer 存了数据 ≠ UI 能找回**。
- **实测**（browser_debug + Chrome CDP）：修复前刷新 thread `web-344f3790` → `web-0e816de0`（历史丢）；修复后 URL `?thread_id=web-bd20b0b6` 刷新不变、历史保留。
- **修复**：thread_id 持久化到 URL query param（`st.query_params`），刷新后从 URL 恢复同一 thread；新建会话同步更新 URL。附带好处：把带 `?thread_id=` 的 URL 分享出去即接续同一会话。
- **教训（重要）**：lesson 初稿写"刷新不丢"是**未验证的断言**——当时只测了"消息存在 checkpointer"，没测"刷新后 UI 能否找回"。真相是：checkpointer 只是数据存档，**thread_id 本身也必须持久化**，两者齐备才叫"刷新不丢"。测机制要测完整链路，不能只测一半就下结论。



