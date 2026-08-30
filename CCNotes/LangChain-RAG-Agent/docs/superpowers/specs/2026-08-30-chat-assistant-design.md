# 设计规格：混合式协议助手（聊天窗口版 app.py）

> 日期：2026-08-30 · 状态：已获用户确认（方案 A：create_react_agent + Streamlit 聊天组件）

## 一、目标

把 app.py 从"上传→按钮→出结果"的一次性 UI 升级为**聊天窗口式协议助手**：能闲聊问答、上传需求文档后围着文档对话（生成协议 / 校验字段 / 追问），形态对齐公司内部 agent 助手。

**核心教学点**（这是"现成框架"的活例子）：
1. `create_react_agent` = 手写 `run_tool_loop`（4.2）+ Graph B（extra_langgraph_intro）的官方成品版，文档里逐行对照
2. 工具 = 把整条 rag_chain 包成 `@tool`（"业务逻辑写普通函数，组装时才装接口"的终极版）
3. token 级打字机（`stream_mode="messages"` + `st.write_stream`，兑现 HANDOFF 待办 #2）

**边界（不做）**：不做多会话管理/登录/审计/持久化到数据库；历史只在 session_state（关页面即丢）；不做 Chainlit/Dify 迁移。

## 二、架构

```
聊天窗口（st.chat_input / st.chat_message 气泡渲染历史）
   │ messages 存 st.session_state（重跑不丢）
   ▼
create_react_agent(llm, tools=[generate_protocol, validate_field_type], prompt=SYSTEM)
   │ 模型"思考"：要不要调工具？
   ├─ generate_protocol(text)  → 跑 rag_chain（4.1 零件复用）→ 回传协议摘要
   ├─ validate_field_type(...) → 从 phase4_2_tool_calling 导入（照抄复用）
   └─ 不调工具 → 直接答复
   ▼
st.write_stream 打字机（stream_mode="messages" 逐 token）
```

数据流不变式：**LLM 做推理，Python 做执行**（工具 = 执行）；**历史每轮全量重发**（会话本质）。

## 三、文件与接口

| 文件 | 改动 | 责任 |
|------|------|------|
| `scripts/chat_agent.py` | 新建 | 两个工具 + SYSTEM_PROMPT + `build_chat_agent()` 返回编译好的 agent |
| `app.py` | 重写为聊天窗口 | 薄壳：上传控件、聊天渲染、下载按钮、历史管理 |
| `lessons/extra_chat_assistant_build.md` | 新建 | 构建全解（三零件拼装 + create_react_agent 内部对照 + 实跑对话输出） |

### scripts/chat_agent.py 接口

- `generate_protocol(requirement: str) -> str`（@tool）：
  - docstring 告诉模型使用时机："用户要求生成/起草协议时调用。参数可选，不传则用当前已上传的文档。"
  - 参数为空 → 读 `st.session_state["current_doc"]`；仍为空 → 返回错误文本"还没有上传需求文档"（让模型转述给用户，而非抛异常）
  - 执行：`rag_chain.invoke({"requirement": text})`（4.1 的链，默认带 RAG）
  - 返回：紧凑摘要文本（协议名 / 字段清单 name:type / 约束条数 / 评审 warning 条数）——长结果不整段塞回模型（省 token）
  - 副作用：完整结果 + render_markdown 存 `st.session_state["last_protocol"]` / `["last_md"]`（下载按钮用）
- `validate_field_type(field_name, field_type, length)`：从 `phase4_2_tool_calling` 导入，不改一行
- `SYSTEM_PROMPT`：协议助手人设（四要素：角色=资深协议工程师助手；指令=可聊天可办事，生成协议用工具；上下文=已上传文档情况由工具自己读；输出格式=中文、简洁、表格优先）
- `build_chat_agent()`：`create_react_agent(llm, [两个工具], prompt=SYSTEM_PROMPT)`；llm 复用 `phase3_2_prompt_chain.llm`（或重建同参数实例，避免跨脚本耦合——用重建，参数同 2.1）

### app.py 接口

- `st.chat_message("user"/"assistant")` 渲染 `st.session_state["messages"]`（Human/AIMessage 对，SystemMessage 由 create_react_agent 内部挂）
- 上传控件在聊天框上方：`decode_doc`（沿用现有编码自适应）→ 存 `session_state["current_doc"]` → `st.info` 提示已加载
- `st.chat_input` 新消息 → 追加 HumanMessage → 流式生成：
  ```python
  def stream_agent(agent, messages):
      for chunk, _ in agent.stream({"messages": messages}, stream_mode="messages"):
          if chunk.content:
              yield chunk.content
  full = st.write_stream(stream_agent(agent, st.session_state["messages"]))
  ```
  `st.write_stream` 返回值 = 完整文本 → 追加 AIMessage(full) 进历史
- 侧栏：`last_protocol` 存在时显示 JSON / Markdown 双下载（沿用现有 render_markdown）
- 异常：agent 调用失败 → `st.error` + 失败文本以 assistant 气泡呈现（历史不追加错误为 AIMessage，直接提示）

## 四、详细设计

### 4.1 会话历史

- `st.session_state["messages"] = []` 初始化（Human/AIMessage 两类）
- 每轮：`messages = messages + [HumanMessage(q)]` → 全量传给 agent → 追加 AIMessage(full)
- 历史本质已在 `lessons/extra_chat_agent.md` 三、讲清，构建文档引用之

### 4.2 工具循环（create_react_agent）

- 内部做的事 = Graph B：model 节点 → 条件边（有 tool_calls? → tools 节点 → 回 model）→ 无 tool_calls → END。构建文档逐行对照 extra_langgraph_intro.py:102-116
- 防死循环：create_react_agent 有内置 recursion limit（25），构建文档验证并记录实测行为

### 4.3 打字机

- `stream_mode="messages"` 出 token 级 chunk；`stream_turn` 过滤规则：AIMessageChunk 的 tool_calls → 输出"🔧 调用工具 X（参数）"标记（按 tool_call id 去重）；str 内容 → 逐 token 输出；ToolMessage 的 content 不上屏
- 这样打字机里能看到完整节奏：模型思考（点菜标记）→ 工具执行 → 最终答复逐字输出——"思考→执行→回答"可见化，LangSmith Studio 里还能看更细轨迹
- 首字延迟教学：聊天场景打字机有感（3.3/demo_stream_feel 的结论）

### 4.4 错误处理

- 工具内不抛异常（返回错误文本让模型转述）——工具错误由框架回传模型，模型自己解释
- UI 层 try/except：agent 崩溃（网络/限流）→ st.error 友好提示（沿用 5.2 的"快速失败+友好报错"原则）

### 4.5 文档已加载信号

- stream_turn 在 _current_doc 存在时给推理输入前置一条临时 SystemMessage（不进历史）——模型不知道代码里的状态，让它点菜必须先告诉它。

## 五、验证标准（完成定义）

1. `scripts/chat_agent.py` + 新版 `app.py` 提交；AppTest 冒烟通过（假 agent monkeypatch，不真调 API；验证上传/聊天/历史渲染不崩）
2. `streamlit run app.py` 手动实测：完整对话录屏输出贴入 lessons 文档——至少两轮：①闲聊问答；②上传 sample_requirement.md → "帮我生成协议"（真调 DeepSeek，模型点菜 generate_protocol → 协议摘要 → 下载按钮出现）→ 追问"第一个字段类型对吗"（点菜 validate_field_type）
3. lessons/extra_chat_assistant_build.md：三零件拼装 / create_react_agent vs 手写循环对照表 / 实跑对话原文 / 踩坑
4. lessons/README.md 索引 + docs/progress.md + docs/HANDOFF.md（待办 #2 标记完成）同步
5. git 直接提交 main（用户约定），commit 带 Co-Authored-By

## 六、全局约束

- 中文注释与文档；零基础可读；讲解带实跑输出
- 跑脚本：`PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe`
- 输出/路径一律 `Path(__file__).resolve()` 基准（坑 #12）；API Key 环境变量读取（坑 #6）
- UI 薄壳原则：业务逻辑全部在 scripts/，app.py 零业务新增
