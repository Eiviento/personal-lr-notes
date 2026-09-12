# 聊天助手构建全解：三零件拼装 → create_react_agent → 打字机 → 实跑对话

> 2026-08-30。把 [extra_chat_agent.md](extra_chat_agent.md) 的"图纸"（三零件 + 选型结论）变成"实物"：`scripts/chat_agent.py`（大脑）+ `app.py`（聊天窗口）+ `scripts/demo_chat_cli.py`（headless 版），最后贴出真调 DeepSeek 的对话原文。
> 前置：先读 [extra_chat_agent.md](extra_chat_agent.md)（三零件 / 框架选型）和 `scripts/extra_langgraph_intro.py` 的 Graph B（图版工具循环）；再回头看本文就是"官方成品 vs 手写图"的逐行对照。

---

## 一、一张图看懂：三零件怎么拼

[extra_chat_agent.md](extra_chat_agent.md) 二、讲过：对话窗口 = **会话历史 + Agent 循环 + 聊天 UI** 三个零件，项目里全有现成的。本实现就是按那张零件表拼的：

| 零件 | 干什么 | 本实现 |
|------|--------|--------|
| 会话历史 | messages 列表，每轮追加，**全量重发**（第 6 章） | `st.session_state["messages"]`（app.py）/ `messages` 列表（CLI，同一套历史逻辑） |
| Agent 循环 | 模型↔工具来回直到说完（4.2 手写 while + Graph B 的官方成品版） | `scripts/chat_agent.py` 的 `build_chat_agent()` = `create_react_agent(llm, [两个工具], prompt=SYSTEM_PROMPT)` |
| 聊天 UI | 输入框 + 消息气泡 + 打字机 | `app.py` 薄壳：`st.chat_input` / `st.chat_message` / `st.write_stream` |

拼法（数据流）：

```
用户输入
   │
   ▼
app.py（UI 薄壳）── 历史 messages ──► chat_agent.build_chat_agent()
   │                                      │ 模型"思考"：要不要点菜？
   │                                      ▼
   │                        ┌─ generate_protocol（包整条 rag_chain，回传摘要）
   │                        └─ validate_field_type（照抄 4.2，不改一行）
   │                                      │ 工具结果（摘要）回喂模型
   │                                      ▼
   │                              模型输出最终答复（逐 token 流）
   ▼
st.write_stream 打字机逐字上屏；完整产物走侧栏下载
```

三份文件三个职责，**大脑和脸完全解耦**：

- `scripts/chat_agent.py`：大脑。会话历史由调用方传进来（一个 messages 列表），它只负责"模型↔工具循环 + 流式输出"，**不含任何 UI 逻辑**。
- `app.py`：脸。渲染气泡、收输入、打字机、侧栏下载，**零业务逻辑**（薄壳原则不变）。
- `scripts/demo_chat_cli.py`：同一个大脑的控制台版——不装 Streamlit 也能聊，教学时把"思考→点菜→执行→答复"的完整节奏打印出来看。

为什么这样拆？**同一个大脑两个入口**（网页 + 命令行），还能在测试里用假 agent 替换大脑（见第七节）。如果大脑里混进 `st.session_state`，CLI 立刻没法用——这是下一节的第一个问题。

---

## 二、大脑 chat_agent.py 逐块导读

### 1. 模块级状态：为什么不用 st.session_state

```python
# chat_agent.py
_current_doc: str | None = None      # 当前上传的需求文档
_last_result: dict | None = None     # 最近一次 generate_protocol 的完整结果

def set_current_doc(text: str | None) -> None: ...   # 上传文档时注入
def get_last_protocol() -> dict | None: ...          # 侧栏下载按钮用
```

**做什么**：工具要读的"当前文档"和"最近产物"放在模块级变量，由 app.py（上传后）或 CLI（启动时）通过 `set_current_doc()` 注入。

**为什么不用 `st.session_state`**：
- `st.session_state` 只在 Streamlit 脚本运行上下文里存在。CLI 没有 Streamlit，一 import 就崩。
- 大脑要保持"环境无关"：同一份代码，网页用、命令行用、测试替身用。**状态注入（`set_current_doc`）和状态读取（`get_last_protocol`）都是普通函数**，谁都能调。

**不做会怎样**：大脑绑定 UI → CLI 得另写一份循环逻辑 → "同一套大脑"的承诺破灭，AppTest 冒烟也得额外 mock 掉 Streamlit 运行时。

**诚实的代价**：模块级变量是进程级单例——多用户/多会话会互相串。设计规格明确"不做多会话管理/登录/持久化"（单用户单窗口够用）；真有此需求时，大脑改造成"每次调用传上下文对象"即可，UI 不用动。

**状态还给 stream_turn 读**：`_current_doc` 非空时，`stream_turn` 会在每轮推理输入前置一条临时 SystemMessage（"文档已加载信号"，见第四节）——**模型看不到代码里的状态，要让它知道，就得写进消息里**。这条信号不进历史，只参与当轮推理。

### 2. generate_protocol：为什么返回摘要不返回全文

```python
@tool
def generate_protocol(requirement: str = "") -> str:
    """当用户要求生成、起草、整理协议规范时调用。参数可选：
    用户直接贴出了需求文本就传进来；否则留空，用当前已上传的需求文档。"""
    text = requirement.strip() or _current_doc
    if not text:
        return "错误：手头没有需求文档。请告诉用户：先上传需求文档..."
    result = rag_chain.invoke({"requirement": text})   # 4.1 的链：检索模板 + 四步链
    global _last_result
    _last_result = result                               # 完整结果走"副作用出口"
    summary = f"协议《{result.get('protocol_name', '未命名')}》已生成：\n"
              f"- 共 {len(fields)} 个字段：msg_type:uint8、temperature:int16、...\n"
              f"- {len(constraints)} 条约束规则，{len(issues)} 条评审提示\n"
              f"- 完整规范已保存，请提醒用户到侧栏下载"
    return summary
```

**做什么**：把整条 rag_chain（检索 + 四步链）包成一个 `@tool`。模型点这道菜，工具执行，**回传的是几十字的紧凑摘要，不是上千字的完整 JSON**。

**为什么返回摘要**：工具结果会作为 ToolMessage **整段塞回模型的上下文**，而会话历史又是每轮全量重发——完整 JSON 每轮对话都要跟着重发一次，token 白白翻倍，还容易把模型的注意力带偏。摘要只给模型"够答复的最小信息"（协议名、字段名:类型、条数）。

**为什么完整结果不丢**：`_last_result = result` 存进模块级变量——这是工具的"副作用出口"。app.py 的侧栏通过 `get_last_protocol()` 读它做下载按钮。**给模型看摘要，给用户看全文**，各取所需。

**不做会怎样**：长结果整段回传 → 每轮历史膨胀、延迟变高；模型照抄长 JSON 时还容易抄错。

**顺带看清工具契约**：docstring 就是给模型看的说明书——"什么时候点这道菜、参数怎么传"。模型靠 docstring 学会"用户说生成协议→点 generate_protocol；没传需求→用已上传文档"。工具内不抛异常，没文档时返回错误文本让**模型转述给用户**（设计规格 4.4：工具错误由框架回传模型，模型自己解释，而不是 UI 弹错）。

### 3. SYSTEM_PROMPT：四要素落位

Prompt 四要素（phase1 学的）在 SYSTEM_PROMPT 里逐条落位：

| 要素 | 含义 | 落位（chat_agent.py） |
|------|------|----------------------|
| 角色 | 你是谁、服务谁 | "你是公司内部的协议规范助手，服务于通信协议工程师。" |
| 指令 | 能做什么、什么时候用什么工具 | "用 generate_protocol 工具把需求文档变成协议规范…" "用 validate_field_type 工具校验…" |
| 上下文 | 手头有什么、缺什么怎么办 | "先确认手头有没有需求内容：有已上传文档就直接调（不传参数）；没有就请用户上传" |
| 输出格式 | 回答长什么样 | "中文、简洁、表格优先" + "生成协议后主动提醒用户：完整规范在侧栏可下载" |

教学点：**四要素不只在"链"里有，在"agent 人设"里一样适用**——角色定口吻、指令定工具、上下文定"缺信息时的行为"、输出格式定答复形状。但要素是**引导不是保证**：本轮实录（第六节）里模型点菜了、也提了侧栏（"完整规范已保存，请到侧栏下载查看详细内容"），输出格式要素这次生效了；可换一轮、换个模型，照样可能不照做——人设要素落位 ≠ 每轮都照要素执行，这正是"模型点菜"随机性的一部分。想让"有文档就点菜"这条**更稳**，靠的不是把人设写得更用力，而是"文档已加载信号"（第四节）：把环境状态直接写进当轮消息。

### 4. build_chat_agent：一行组装

```python
def build_chat_agent():
    return create_react_agent(llm, [generate_protocol, validate_field_type], prompt=SYSTEM_PROMPT)
```

三个参数：模型（重建的 `ChatOpenAI` 实例，参数同 2.1 的 deepseek-chat 配置，**不复用别的脚本的 llm 实例**，避免跨脚本耦合）、工具清单（模型点菜的范围就这两道菜）、人设。`validate_field_type` 是从 phase4_2 **原样 import 的**——零件复用，不改一行。这一行背后就是一张图，下一节逐项对照。

---

## 三、create_react_agent vs 手写循环对照表

`extra_langgraph_intro.py` 的 Graph B 用了 3 个函数 + 3 条边声明工具循环；`create_react_agent` 是它的**官方成品版**，逐项对应：

| Graph B（手写图，extra_langgraph_intro.py） | create_react_agent 内置 | 干什么 |
|------|------|------|
| `AgentState`：messages 用 `Annotated[list, add]`（追加不替换） | 内置 `MessagesState`（同款语义） | 状态：历史只增不换 |
| `node_model`：`llm_with_tools.invoke(state["messages"])` | 内置 model 节点 | 把全部历史发给带工具的模型，得到答复或 tool_calls |
| `node_tools`：循环执行每个 tool_call → 追加 ToolMessage | 内置 tools 节点 | 代码上菜：按模型点的菜逐个执行，结果回填 |
| `should_continue` 条件边：有 tool_calls → `"tools"`，否则 `END` | 内置条件路由（同款逻辑） | 判循环还是结束：模型还在点菜就继续 |
| `g.add_edge("tools", "model")` | 内置 tools → model 边 | 工具结果回喂模型，进入下一轮思考 |
| 手写 while 上限 5 轮（4.2） | **recursion limit 内置** | 防死循环（见下） |

**recursion limit 内置说明**：图无限循环是真实风险（模型永远点菜不答复）。create_react_agent 不用你写 `while` 计数器，框架自带上限：langgraph 1.2.9 实测默认 **10007** 次迭代（`langgraph/_internal/_config.py` 的 `DEFAULT_RECURSION_LIMIT`），超限抛 `GraphRecursionError`。需要收紧就按调用传 `config={"recursion_limit": N}`，或环境变量 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 全局改。（设计规格曾写"默认 25"，实测当前版本是 10007——版本差异，以实测为准，见第八节踩坑 3。）

**对照结论**：一行 `create_react_agent(llm, tools, prompt)` = Graph B 的"3 函数 + 3 边" + 4.2 手写 while 的上限保护，全部封装。手写图的**教学价值**是看懂内部；生产用成品，省的是边界情况（多工具并行、tool_call 中断恢复、参数校验等）。

---

## 四、打字机三规则

打字机在 `stream_turn`（chat_agent.py），它消费 `agent.stream(..., stream_mode="messages")` 的流：

```python
for chunk, _ in agent.stream({"messages": messages}, stream_mode="messages"):
```

**流的形状**：`stream_mode="messages"` 产出 `(chunk, metadata)` 二元组——chunk 是消息的分片（token 级，`AIMessageChunk` 或 `ToolMessageChunk`），metadata 是调试信息（实测含 `langgraph_node`、`langgraph_step`、`langgraph_path` 等键，能看出这个分片来自哪个节点、第几步）。

**文档已加载信号（三规则之前的机制）**：`stream_turn` 开头先看模块级 `_current_doc`，已加载文档时给这轮推理的输入**前置一条临时 SystemMessage**（不进历史）：

```python
input_msgs = list(messages)              # 复制一份，不污染调用方的历史
if _current_doc:
    input_msgs.insert(0, SystemMessage(
        "【环境提示】当前已加载一份需求文档。用户要求生成协议时，"
        "直接调用 generate_protocol 工具（不传参数）；需要确认文档内容细节时再问用户。"))
```

**为什么要有它**：模型看不到代码里的 `_current_doc`——模块级变量不在对话里，模型连它存在都不知道。人设里写"有已上传文档就直接调"，模型可能照做，也可能反问"你手头有需求内容吗"（无信号实录就是这么被卡住的——`outputs/chat_demo_transcript_no_signal.log` 单轮实跑：文档明明已加载，模型却反问"我需要先确认一下需求内容。请问您是否已经上传了需求文档？"，没有点菜）。**模型不知道代码里的状态，要让它知道，就得写进消息里**——把环境状态翻译成消息，是 agent 应用里比提示词更硬的机制。**为什么不进历史**：这条信号只在"这轮该不该直接点菜"上有意义，存进历史会让每一轮重发都多一段废话；而且历史是 UI 渲染的依据（Human/AIMessage 气泡），SystemMessage 混进去渲染逻辑要额外处理。实测对照：本轮实录第 2、3 轮模型都直接点菜，没再反问需求来源。

**三规则**（对应代码里的三个分支）：

1. **模型点菜 → 🔧 标记，按 tool_call id 去重**：chunk 带 `tool_calls` 时，输出 `🔧 调用工具 X（参数）`。为什么按 id 去重：一个 tool_call 的参数是**跨多个 chunk 累加**的（id 不变、args 越拼越全），不去重同一个点菜会打出好几遍标记。🔧 标记是 `full` 的一部分，会随 AIMessage 存进历史并显示在 UI 气泡里——模型能容忍这类文本混入自己的历史（本轮实录的标记行就是取证：`🔧 调用工具 generate_protocol（{}）` 进了历史后，第 3 轮模型照常理解对话，见第六节），这是设计上的有意为之。
2. **`chunk.content` 是 str 且非空 → 逐 token 产出**：这就是打字机的"逐字"效果——最终答复一个字一个字冒出来。
3. **ToolMessage → 不上屏**：工具执行结果不打扰用户（想看执行细节有侧栏产物/日志）。

我用假 agent 复现的 chunk 序列（实测输出）：

| 到达的 chunk | stream_turn 做什么 |
|------|------|
| AIMessageChunk（内容 + tool_calls 第一片，args 还空着） | 打 🔧 标记（此时参数是 `{}`）+ 内容逐字 |
| AIMessageChunk（tool_calls 续片，args 补全） | id 已在 seen 里 → 跳过 |
| ToolMessage（工具结果） | 跳过不上屏 |
| AIMessageChunk（最终答复） | 逐字输出 |

**为什么这设计好**：屏幕上能看到完整节奏——**模型思考（点菜标记）→ 工具执行 → 最终答复逐字输出**，"思考→执行→回答"全程可见，这正是 4.2 手写循环时"模型点菜/代码上菜"的可见化。首字延迟的体感教学在 3.3 讲过，聊天场景下打字机让等待有了反馈，感知更好。

---

## 五、UI 薄壳导读（app.py）

| 组件 | 干什么 | 本实现 |
|------|--------|--------|
| `st.chat_message("user"/"assistant")` | 消息气泡容器 | `with st.chat_message(msg.type)` 里 `st.markdown(msg.content)` 渲染历史 |
| `st.chat_input(...)` | 聊天输入框，回车返回字符串 | `if question := st.chat_input("问我协议问题...")` |
| `st.write_stream(生成器)` | 接收生成器逐字渲染打字机 | `full = st.write_stream(stream_turn(agent, st.session_state["messages"]))`，返回值 = 完整文本 |
| `st.session_state["messages"]` | 重跑不丢的历史 | 初始化 `[]`；每轮追加 `HumanMessage(question)`，答完追加 `AIMessage(full)` |
| `st.sidebar` + `st.download_button` | 侧栏产物下载 | `get_last_protocol()` 非空时出 JSON / Markdown 双下载按钮（`render_markdown` 沿用 3.4） |

三个关键细节：

1. **历史只存 Human/AIMessage**，SystemMessage 不存——create_react_agent 内部自己挂人设。渲染时用 `msg.type` 决定左右气泡。
2. **`st.write_stream` 的返回值就是完整答复**——生成器吐完一遍，返回值把所有片段拼好了。把它追加进历史，而不是把片段逐条追加，否则重跑时历史里全是碎块。
3. **上传控件在聊天框上方**：`st.file_uploader` → `decode_doc`（3.1 的编码自适应）→ `set_current_doc()` 注入大脑 + `st.info` 提示。上传不触发任何链，模型下次点菜时工具自己读文档。

薄壳原则验收：app.py 里**没有**任何业务逻辑（不调 LLM、不跑链），全部业务在 chat_agent.py；app.py 只做"状态搬运 + 渲染"。

---

## 六、实跑对话原文（真调 DeepSeek，2026-08-30 实录）

来源：`scripts/demo_chat_cli.py` 非交互模式跑 `sample_requirement.md` 的三轮对话，stdout/stderr 原样重定向到 `outputs/chat_demo_transcript.log`，**单次实跑、未挑选**（一次运行的原样输出，不是多次运行里挑好的）。开头两行 requests 依赖警告（`urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4)` 版本不匹配，环境噪音）引用时已裁掉。另有一条无信号对照实录 `outputs/chat_demo_transcript_no_signal.log`（同一需求文档、单轮只发"帮我生成协议"、绕过 stream_turn 直接给 agent 裸消息，即不加"文档已加载信号"），第 2 轮对比时引用。命令：

```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe demo_chat_cli.py ../inputs/sample_requirement.md "你好，简单介绍下你自己" "帮我生成协议" "第一个字段的类型和字节数对吗"
```

### 第 1 轮：闲聊问答（无工具）

~~~
📄 已加载文档：../inputs/sample_requirement.md
👤 用户：你好，简单介绍下你自己
🤖 助手：你好！我是公司内部的**协议规范助手**，专门服务于通信协议工程师。😊

我的核心能力有这几项：

| 能力 | 说明 |
|------|------|
| 📖 **协议问答** | 直接回答字段类型、字节数、校验方式、上报频率等协议相关问题，中文简洁、表格优先 |
| 📄 **生成协议** | 把需求文档变成标准协议规范（上传文档或贴需求后说"生成协议"即可） |
| ✅ **字段校验** | 校验字段的类型与字节数是否匹配（问"这个字段对吗"时我会主动调用工具） |

**使用小贴士：**
- 想生成协议？直接说 **"生成协议"**，我会用当前已加载的需求文档来生成
- 想确认某个字段定义是否正确？把**字段名、类型、字节数**告诉我即可

有什么协议相关的问题，尽管问我吧！
============================================================
~~~

**模型在这一步做了什么**：识别这是自我介绍请求，**没点菜**（无 🔧 标记），直接按 SYSTEM_PROMPT 的角色和输出格式组织答复——能力清单（表格优先）+ 使用小贴士。注意开头 `📄 已加载文档`：文档此时已注入 `_current_doc`（"文档已加载信号"已在生效），但闲聊轮用不上它，模型不需要也不该提它。

### 第 2 轮：帮我生成协议（直接点菜 generate_protocol，参数为空（{}））

~~~
👤 用户：帮我生成协议
🤖 助手：好的，我来根据当前已加载的需求文档生成协议规范。

🔧 调用工具 generate_protocol（{}）
1. 通信内容：定时上报温度、湿度数据，温度范围-40~85度，湿度范围0~100%。
2. 上报频率：每60秒上报一次温湿度数据。
3. 精度要求：温度精度0.1度，湿度精度1%。
4. 告警规则：电池电量低于20%时，上报电池低电量告警。
5. 触发条件：设备开机时，上报一条上线消息，包含固件版本号。
6. 扩展预留：协议需预留扩展位，以支持未来增加光照传感器。
7. 时间戳：由网关添加，终端协议不包含时间戳字段。{
  "protocol_name": "温湿度上报协议",
  "description": "用于环境温湿度周期性上报、电池低电量告警及设备上线通知，预留扩展位以支持未来传感器扩展。",
  "fields": [
    {
      "name": "msg_type",
      "chinese_name": "消息类型",
      "type": "uint8",
      "length": 1,
      "unit": "",
      "range": "0x01=周期上报, 0x02=告警, 0x03=上线",
      "description": "区分不同消息类型"
    },
    {
      "name": "temperature",
      "chinese_name": "温度",
      "type": "int16",
      "length": 2,
      "unit": "0.1℃",
      "range": "-400~850",
      "description": "实际温度=原始值×0.1℃，范围-40.0~85.0℃"
    },
    {
      "name": "humidity",
      "chinese_name": "湿度",
      "type": "uint8",
      "length": 1,
      "unit": "%",
      "range": "0~100",
      "description": "相对湿度百分比"
    },
    {
      "name": "battery_voltage",
      "chinese_name": "电池电压",
      "type": "uint16",
      "length": 2,
      "unit": "mV",
      "range": "0~65535",
      "description": "电池电压，用于低电量判断"
    },
    {
      "name": "firmware_version",
      "chinese_name": "固件版本号",
      "type": "uint16",
      "length": 2,
      "unit": "",
      "range": "0~65535",
      "description": "上线消息携带，高字节主版本，低字节次版本"
    },
    {
      "name": "reserved",
      "chinese_name": "预留扩展位",
      "type": "uint8",
      "length": 1,
      "unit": "",
      "range": "0x00",
      "description": "预留，默认0x00，未来可扩展光照等传感器"
    }
  ],
  "timing": {
    "report_interval": "60秒",
    "direction": "上行"
  }
}```json
{
  "constraints": [
    {"field": "msg_type", "rule": "枚举值必须为0x01、0x02或0x03，其他值视为非法"},
    {"field": "temperature", "rule": "原始值范围-400~850，对应实际温度-40.0~85.0℃，超出范围视为异常"},
    {"field": "humidity", "rule": "取值范围0~100，超出范围视为非法"},
    {"field": "battery_voltage", "rule": "低电量告警阈值20%需由电压值换算，具体换算公式需在协议文档中明确"},
    {"field": "firmware_version", "rule": "仅在上线消息(msg_type=0x03)中有效，其他消息类型应置0"},
    {"field": "reserved", "rule": "当前必须为0x00，接收方应忽略非零值以兼容未来扩展"}
  ],
  "issues": [
    {"severity": "error", "field": "battery_voltage", "message": "需求要求电池电量低于20%时告警，但字段定义为电压(mV)，未提供电压与电量百分比的换算关系，无法判断20%阈值对应的电压值"},
    {"severity": "warning", "field": "temperature", "message": "温度精度要求0.1℃，int16可表示范围-3276.8~3276.7℃，当前范围-40.0~85.0℃仅使用约3.8%的表示空间，建议考虑使用uint16或缩小类型以节省带宽"},
    {"severity": "warning", "field": "msg_type", "message": "消息类型仅定义3种，但预留扩展位仅1字节，未来若增加新消息类型（如光照上报）可能需要扩展msg_type，建议明确扩展策略"},
    {"severity": "warning", "field": "reserved", "message": "预留扩展位仅1字节，若未来增加光照传感器可能需要多个扩展字段，建议评估是否足够或定义扩展机制"}
  ]
}
```✅ 协议《温湿度上报协议》已成功生成！

**协议概览：**

| 字段 | 类型 | 说明 |
|------|------|------|
| msg_type | uint8 | 消息类型 |
| temperature | int16 | 温度 |
| humidity | uint8 | 湿度 |
| battery_voltage | uint16 | 电池电压 |
| firmware_version | uint16 | 固件版本 |
| reserved | uint8 | 保留字段 |

**生成结果：**
- 📋 共 **6 个字段**
- 📏 **6 条约束规则**
- 🔍 **4 条评审提示**

📥 **提醒：完整规范已保存，请到侧栏下载查看详细内容**（包括字段偏移、字节序、校验规则、上报频率等完整定义）。

如需调整字段或补充需求，随时告诉我！
============================================================
~~~

**模型在这一步做了什么**（顺序即实录顺序）：

1. **直接点菜，没再反问**：模型识别出"生成协议"请求后没有问"你手头有需求内容吗"，而是直接调 `generate_protocol`（开头那句"我来根据当前已加载的需求文档生成协议规范"是它伴随点菜吐出的预告）——这是"文档已加载信号"（临时 SystemMessage）的功劳：模型知道当前有文档、可以直接点菜。对比无信号实录（`outputs/chat_demo_transcript_no_signal.log`，同一需求文档、同样只发"帮我生成协议"、不走信号注入）：模型反问"我需要先确认一下需求内容。请问您是否已经上传了需求文档？如果没有，请把需求内容直接贴出来，我就可以为您生成协议规范。"，没有点菜——文档已加载但模型不知道，只能问。更早的无信号版本（accf9ed 那次实录）则是先犹豫"我需要先确认一下手头有没有需求内容"、随后还是点了菜——**无信号时模型行为不稳定**：可能反问、可能犹豫后点菜，人设要素是引导不是保证。
2. **标记行 `（{}）` 是踩坑 1 的直接证据**：`🔧 调用工具 generate_protocol（{}）`——标记在 tool_call 的第一个 chunk 就打出去了，此时 args 还是空的（参数跨 chunk 累加），之后按 id 去重不再补打。工具实际以空参数成功执行（= 工具内部读 `_current_doc`）。
3. **最终答复 = 摘要 + 领域先验的重构**：工具执行（跑整条 rag_chain）后，模型的最终答复很长：需求关键点列表（-40~85℃、0.1℃、20% 低电量告警、网关加时间戳……）、6 字段 JSON（msg_type/temperature/humidity/battery_voltage/firmware_version/reserved）、约束/评审 JSON、概览表和侧栏下载提醒——屏幕上的一切都是模型最终答复的 str 内容（工具执行细节 ToolMessage 不上屏）。但按第二节的设计，工具回传的只有 **172 字紧凑摘要**（协议名 + 6 个字段名:类型 + 条数）——模型从未见过完整文档，也没见过完整 JSON（需求原文和完整产物只在进程内部流转，不进模型上下文）。长答复是怎么来的？**重构**：模型拿摘要里的字段名当骨架，把"环境监测协议"的领域先验填进细节。这份教学需求文档恰好是**教科书标准写法**（温度 -40~85℃、精度 0.1℃、20% 低电量告警……），所以先验经常落在同一组数值上——看起来像"看到过文档"，其实只是猜对了。铁证见下方对照实验：强制展开对照组（`scripts/demo_reconstruction_control.py`，进程里从未出现需求文档）两次也都重构出 -40 / 0.1 / 固件版本——但 20%、60 秒、网关、光照等细节没有出现，命中的只是"教科书先验"的一部分，恰恰证明它是在重构、不是在读取。
4. **输出格式要素这次生效了**："📥 提醒：完整规范已保存，请到侧栏下载查看详细内容"——SYSTEM_PROMPT 里"生成协议后主动提醒侧栏可下载"这条照做了。人设要素是引导不是保证（可能不生效），但本轮生效了，实录原样保留。

**对照实验取证**（`scripts/demo_reconstruction_control.py`，完整输出 `outputs/chat_reconstruction_control.log`；temperature 0.3，进程里从未出现需求文档，只喂约 172 字的工具摘要）：

| 实验 | 条件 | 结果 |
|------|------|------|
| 强制展开 ×2 | 进程无文档：人设 + 环境提示 + 用户"帮我生成协议" + 假点菜 + 约 172 字工具摘要 + 用户"完整展开" | 1995/2065 字，两次都命中 -40、0.1、固件版本——"文档事实"没有文档也能编出来；但 20%、60 秒、网关、光照 未出现，先验只命中教科书写法的一部分 |
| 实录那次 | 完整 agent + stream | 长答复 + 细节全中——模型恰好进入"长答复模式"且这次重构对了 |

**这说明了什么**：① **模型流利 ≠ 模型看到过**——把细节说得有鼻子有眼是 LLM 的天性，流利的细节很可能是现场重构的，模型自己也不知道对不对；② **事实必须来自工具/检索**——这正是"工具回摘要 + 完整结果留侧栏下载"设计的价值：要精确的协议字段、字节序、约束规则，看下载的 JSON，别信聊天窗口里的重构细节。

### 第 3 轮：字段校验（直接点菜 validate_field_type，参数为空（{}））

~~~
👤 用户：第一个字段的类型和字节数对吗
🤖 助手：我来帮你校验第一个字段 `msg_type` 的类型与字节数是否匹配。

🔧 调用工具 validate_field_type（{}）
✅ **校验通过！**

| 项目 | 值 |
|------|-----|
| 字段名 | msg_type |
| 数据类型 | uint8 |
| 声明字节数 | 1 |
| 标准字节数 | 1 |
| 结果 | **合法** ✅ |

`uint8` 类型标准就是 **1 字节**，与声明的字节数完全匹配，定义正确。

还有其他字段需要校验吗？随时告诉我！
============================================================
~~~

**模型在这一步做了什么**（顺序即实录顺序）：

1. **直接点菜，没再要参数**：模型识别出这是字段校验请求，直接调 `validate_field_type`——它从上一轮历史（round 2 的完整答复里就有字段表和协议 JSON）知道第一个字段是 `msg_type`、uint8、1 字节，参数在点菜时按名字传入（标记行的 `（{}）` 只是第一个 chunk 的瞬时状态——参数跨 chunk 累加，工具执行前已补全，见踩坑 1）。这一步靠的是上一轮历史，不靠"文档已加载信号"——更早的无信号版本（accf9ed 那次实录）第 3 轮同样直接点菜，因为 round 2 的长答复已经把字段表留在历史里了；信号管的是 round 2"有文档就直接点菜"这一下。
2. **最终答复 = 结果表**：工具校验结果回喂模型后，模型把结果整理成"字段名/数据类型/声明字节数/标准字节数/结果"表格 + 一句结论。屏幕上的表格是模型最终答复的 str 内容（工具返回的校验原文不上屏，由模型转述）。
3. **标记混入历史的副作用在这里可见**：round 2 的 `🔧 调用工具 generate_protocol（{}）` 作为 `full` 的一部分进了历史，round 3 模型读历史时看到它没有困惑、照常理解对话——第四节的"标记混入历史是设计上的有意为之"得到实证。

---

## 六·五、不上传文档的三种用法（纯对话，实录 outputs/chat_demo_transcript_paste.log）

文档上传只是入口之一。三个工具参数/模型推理都能纯对话完成：

| 用法 | 怎么问 | 模型干什么 |
|------|--------|-----------|
| ① 贴需求生成 | "请根据以下需求生成协议：智能门锁，…" | 把需求文本作为**参数**传给 generate_protocol（工具本来就有 `requirement` 参数，上传只是省打字） |
| ② 贴字段定义校验 | "请校验这些字段定义是否符合规范：msg_type uint8 长度1字节；…" | 逐字段点菜 validate_field_type，汇总成校验表 |
| ③ 生成后追问 | 生成完接着问"第 3 个字段对吗" | 靠上一轮历史回答/点菜（第 3 轮的机制） |

2026-08-30 实跑（②的完整原文在 outputs/chat_demo_transcript_paste.log）：故意注入错误"status uint8 长度 2 字节"，模型**连点 3 次菜**（每字段一次），校验表揪出 status ❌ 不合法，并给出两条修正建议（长度改 1 或类型改 uint16）。

要点：**校验是死规则，永不出错**（4.2 的 FIXED_SIZE 表）；模型负责"该不该校验、结果怎么解读"。纯对话模式下这条原则照样成立。

---

## 六·六、对话例子速查（复制即用）

| # | 场景 | 你输入的话 | 模型会干什么 | 实录 |
|---|------|-----------|-------------|------|
| 1 | 贴需求生成 | `请根据以下需求生成协议：智能门锁，定时上报锁状态（开/关），每10秒一次，含电池电压，撬锁时立即告警` | 把需求文本当参数点菜 generate_protocol，返回协议概览 | `chat_demo_transcript_paste.log` 第 1 轮 |
| 2 | 上传后生成 | `帮我生成协议`（先上传文档） | 点菜 generate_protocol（无参，读已上传文档） | `chat_demo_transcript.log` 第 2 轮 |
| 3 | 贴字段表校验 | `请校验这些字段定义是否符合规范：msg_type uint8 长度1字节；status uint8 长度2字节；battery uint16 长度2字节` | 每字段点一次菜 validate_field_type，汇总校验表；注入了错误的 status 被揪出 | `chat_demo_transcript_paste.log` 第 2 轮 |
| 4 | 贴 JSON 校验 | `请检查这个协议 JSON 有没有问题：{"fields":[{"name":"temp","type":"float32","length":8}]}` | 点菜校验 float32=8 字节 → 不合法（标准 4） | 模板（与 #3 同机制） |
| 5 | 追问式校验 | `第一个字段的类型和字节数对吗` | 靠上一轮历史回答 + 点菜 | `chat_demo_transcript.log` 第 3 轮 |
| 6 | 咨询（无工具） | `uint8 和 int8 有什么区别？上报温度该用哪种？` / `CRC 放帧头还是帧尾好？` | 纯推理回答——**没有工具背书，正确性靠模型**（与 4.2 的边界认知一致） | 模板 |
| 7 | 改字段再校验 | `把 lock_state 字段改成 uint8 1字节，重新给我一份校验表` | 点菜校验 + 生成新校验表 | `chat_demo_transcript_multi.log` 第 3 轮 |
| 8 | 总结设计要点 | `总结一下这个协议的设计要点` | 纯推理汇总（含待完善项评审） | `chat_demo_transcript_multi.log` 第 4 轮 |
| 9 | 没文档就生成 | `帮我生成协议`（什么都不传） | 反问"是否已上传文档"——模型不知道代码里的状态（六·五的要点） | `chat_demo_transcript_no_signal.log` |

彩蛋（`chat_demo_transcript_multi.log` 第 3 轮）：用户把字段说成 `status`，协议里其实叫 `lock_state`——模型**纠正了用户**、按 lock_state 校验、并请用户确认。真实 agent 该有的样子。

---

## 七、AppTest 冒烟：CHAT_FAKE_AGENT 开关

**做什么**：`scripts/demo_app_test.py` 用 Streamlit 的 `AppTest` 驱动真实 `app.py` 跑四件事——页面渲染无异常 / 上传文档注入成功 / 发消息后历史累积 2 条 / 侧栏占位文案。**全程不真调 API**。

**开关怎么设计的**：

```python
# demo_app_test.py：先设环境变量，再 import app
os.environ["CHAT_FAKE_AGENT"] = "1"
at = AppTest.from_file(..., default_timeout=30).run()
```

```python
# app.py：get_agent() 读开关，假/真二选一
@st.cache_resource(show_spinner="加载模型组件中...")
def get_agent():
    if os.getenv("CHAT_FAKE_AGENT") == "1":
        return FakeAgent()
    return build_chat_agent()
```

- `FakeAgent` 在 chat_agent.py 里：`.stream()` 接口模仿真 agent 的 `stream_mode="messages"` 输出形状，固定吐一条 `AIMessageChunk`——**结构真、内容假**，UI 链路照常走，模型调用被替身挡住。
- **开关放环境变量而不是代码里**：正常 `streamlit run app.py` 不需要知道测试的存在；测试脚本在 import app 之前设好即可。
- 假 agent 还兼职"契约测试"：如果哪天真 agent 的 stream 输出形状变了，假 agent 的模仿就失真了，冒烟会失去意义——所以 FakeAgent 的注释写明"输出形状模仿真 agent"。

**怎么跑**：

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_app_test.py
# 期望输出：✅ AppTest 冒烟通过：上传注入（_current_doc 非空）/ 假聊天一轮 / 历史累积 2 条 / 侧栏占位 / 无异常
```

**为什么值得做**：真调 API 的测试又慢又花钱又看运气；冒烟把"UI 机制不崩"这件事从人工验证变成一条命令，改动 app.py 后立刻能回归。测试不花钱的前提是**大脑可替换**——这正是第一节"解耦"设计带来的红利。

---

## 八、踩坑

| # | 坑 | 教训 / 处理 |
|---|-----|------------|
| 1 | **🔧 标记里参数显示 `（{}）`**：点菜发生时，标记打出的参数是空的，但工具实际执行成功（读到了文档、校验正确）。机制：`stream_mode="messages"` 下 tool_call 的 args 是**跨 chunk 累加**的，标记在第一个 chunk 就打出去了（此时 args 还没到），之后按 id 去重不再重打。第六节本次实录两轮点菜都有直接取证：`🔧 调用工具 generate_protocol（{}）` 和 `🔧 调用工具 validate_field_type（{}）`——两个工具都以"标记上看着空参"的形态成功执行（generate_protocol 读 `_current_doc`；validate_field_type 的参数在后续 chunk 补全，否则工具会报错） | 标记是"模型点菜信号"，不是参数转储；要精确参数得自己拼后续 chunk 的 args。实录原样保留（含 `（{}）` 现象） |
| 2 | **create_react_agent 弃用警告**（langgraph 1.2.9 + langchain 1.3.14 实测）：构建 agent 时打 `LangGraphDeprecatedSinceV10: create_react_agent has been moved to 'langchain.agents'. Please update your import to 'from langchain.agents import create_agent'. Deprecated in LangGraph V1.0 to be removed in V2.0.` | **现在能用**，不用急着改；**V2 后要换导入路径**：`from langchain.agents import create_agent`。改时验证函数签名是否一致即可 |
| 3 | **recursion limit 设计值 vs 实测值**：设计规格写"内置上限 25"，实测 langgraph 1.2.9 默认 **10007**（`DEFAULT_RECURSION_LIMIT`，可被 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 环境变量或 `config={"recursion_limit": N}` 覆盖） | 版本差异正常，**以实测为准**；防死循环机制内置是真的，具体数值别写死进文档 |
| 4 | **AppTest 冷启动超时**：本机首次运行光 import app（langchain/rag 链）就要 ~5.2s，AppTest 默认 3s 超时在初始渲染处误报 `RuntimeError: AppTest script run timed out` | `AppTest.from_file(..., default_timeout=30)` |
| 5 | **file_uploader.set_value API 变化**：streamlit 1.62.0 只接受 `(name, content, mime)` 元组；旧写法传文件对象（FileMock）报 `TypeError: 'FileMock' object is not iterable` | `at.file_uploader[0].set_value((sample.name, sample.read_bytes(), "text/markdown"))` |
| 6 | **实录环境噪音**：transcript 开头两行 requests 依赖警告（urllib3/chardet 版本不匹配）不是程序行为 | 裁剪并注明"环境噪音"；本项目跑脚本一律 `PYTHONIOENCODING=utf-8` 前缀（坑 #5） |
| 7 | **模型会在长答复里重构出与文档一致的细节**：工具只回传约 172 字的摘要，模型却能在最终答复里补出与需求文档逐条吻合的细节（-40~85℃、0.1℃、20% 低电量告警……），看起来像"看到过文档"——实为摘要 + 领域先验的重构；这份教学需求是教科书标准写法，先验经常命中同样数值 | **别被流利误导**：判断模型是否真看过某内容，看它的输入日志（对照实验法），而不是看它答得像不像。证据见第六节：强制展开对照组（`scripts/demo_reconstruction_control.py`，进程从没见过文档）照样重构出 -40 / 0.1 / 固件版本——"看起来像看过文档"不等于真看过，先验命中而已。要精确协议看侧栏下载的 JSON，别信聊天里的重构细节 |

---

## 深挖

- 三零件与选型：[extra_chat_agent.md](extra_chat_agent.md)
- Graph B 图版工具循环：`scripts/extra_langgraph_intro.py`（model/tools 节点 + 条件边，第 86-116 行）
- 手写工具循环（点菜/上菜）：[phase4_tool_calling.md](phase4_tool_calling.md)
- 把整条 rag_chain 包成工具：`scripts/chat_agent.py` 的 `generate_protocol`
- Streamlit 心智模型与 AppTest：[phase5_deploy.md](phase5_deploy.md)
