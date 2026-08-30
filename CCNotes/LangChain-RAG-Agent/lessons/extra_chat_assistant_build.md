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

**不做会怎样**：长结果整段回传 → 每轮历史膨胀、延迟变高；模型复述长 JSON 时还容易抄错。

**顺带看清工具契约**：docstring 就是给模型看的说明书——"什么时候点这道菜、参数怎么传"。模型靠 docstring 学会"用户说生成协议→点 generate_protocol；没传需求→用已上传文档"。工具内不抛异常，没文档时返回错误文本让**模型转述给用户**（设计规格 4.4：工具错误由框架回传模型，模型自己解释，而不是 UI 弹错）。

### 3. SYSTEM_PROMPT：四要素落位

Prompt 四要素（phase1 学的）在 SYSTEM_PROMPT 里逐条落位：

| 要素 | 含义 | 落位（chat_agent.py） |
|------|------|----------------------|
| 角色 | 你是谁、服务谁 | "你是公司内部的协议规范助手，服务于通信协议工程师。" |
| 指令 | 能做什么、什么时候用什么工具 | "用 generate_protocol 工具把需求文档变成协议规范…" "用 validate_field_type 工具校验…" |
| 上下文 | 手头有什么、缺什么怎么办 | "先确认手头有没有需求内容：有已上传文档就直接调（不传参数）；没有就请用户上传" |
| 输出格式 | 回答长什么样 | "中文、简洁、表格优先" + "生成协议后主动提醒用户：完整规范在侧栏可下载" |

教学点：**四要素不只在"链"里有，在"agent 人设"里一样适用**——角色定口吻、指令定工具、上下文定"缺信息时的行为"、输出格式定答复形状。但要素是**引导不是保证**：本轮实录（第六节）里模型**没提过侧栏**——输出格式里"生成协议后主动提醒侧栏可下载"这条没有生效，模型连工具都没点。人设要素落位 ≠ 每轮都照要素执行，这正是"模型点菜"随机性的一部分。

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

**三规则**（对应代码里的三个分支）：

1. **模型点菜 → 🔧 标记，按 tool_call id 去重**：chunk 带 `tool_calls` 时，输出 `🔧 调用工具 X（参数）`。为什么按 id 去重：一个 tool_call 的参数是**跨多个 chunk 累加**的（id 不变、args 越拼越全），不去重同一个点菜会打出好几遍标记。🔧 标记是 `full` 的一部分，会随 AIMessage 存进历史并显示在 UI 气泡里——模型能容忍这类文本混入自己的历史（本次实录两轮都没点菜，没有直接取证机会，但机制必然如此），这是设计上的有意为之。
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

来源：`scripts/demo_chat_cli.py` 非交互模式跑 `sample_requirement.md` 的三轮对话，stdout/stderr 原样重定向到 `outputs/chat_demo_transcript.log`，**未修改、未重跑**。开头两行 requests 依赖警告（`urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4)` 版本不匹配，环境噪音）引用时已裁掉。命令：

```bash
PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe demo_chat_cli.py ../inputs/sample_requirement.md "你好，简单介绍下你自己" "帮我生成协议" "第一个字段的类型和字节数对吗"
```

### 第 1 轮：闲聊问答（无工具）

~~~
📄 已加载文档：../inputs/sample_requirement.md
👤 用户：你好，简单介绍下你自己
🤖 助手：你好！我是你的**协议规范助手**，专门服务于通信协议工程师。😊

我能帮你做这些事：

| 能力 | 说明 |
|------|------|
| 📖 **协议问答** | 直接回答字段类型、字节数、校验方式、上报频率等协议问题，中文简洁、表格优先 |
| 📄 **生成协议** | 把需求文档或需求文本变成规范的协议定义（上传文档或贴需求后说"生成协议"即可） |
| ✅ **字段校验** | 帮你校验字段的类型与字节数是否匹配（问"这个字段对吗"时我会主动调用） |

**使用小贴士：**
- 想生成协议？直接上传需求文档，或把需求文字贴给我，然后说 **"生成协议"**
- 想校验字段？告诉我字段名、类型和字节数，比如 *"校验一下 temperature 字段，float32，4字节"*

有什么协议相关的问题，尽管问我吧！🚀
============================================================
~~~

**模型在这一步做了什么**：识别这是自我介绍请求，**没点菜**（无 🔧 标记），直接按 SYSTEM_PROMPT 的角色和输出格式组织答复——能力清单（表格优先）+ 使用小贴士。注意这一轮模型**没有提"侧栏下载"**——SYSTEM_PROMPT 输出格式里"生成协议后主动提醒侧栏可下载"这条并没有生效：人设要素是引导不是保证，模型行为每轮有随机性，实录原样保留。

### 第 2 轮：帮我生成协议（没有点菜——模型反问需求来源）

~~~
👤 用户：帮我生成协议
🤖 助手：好的，我来帮你生成协议！

不过我需要先确认一下：**你手头有需求内容吗？**

- 📄 **如果已经上传了需求文档**，我直接基于文档生成
- ✍️ **如果还没有**，请把需求文字贴给我，或者上传需求文档

你可以直接说"生成协议"，我这边会检查是否有已上传的文档。让我先看看当前有没有可用的需求文档。

请确认一下你的需求来源，我好开始工作！
============================================================
~~~

**模型在这一步做了什么**（顺序即实录顺序）：

1. **没有点菜**：模型识别出"生成协议"请求，但选择**先确认需求来源**——"你手头有需求内容吗？"——然后说"让我先看看当前有没有可用的需求文档"，就此打住：**没有调用 generate_protocol**（无 🔧 标记，工具没执行，`_last_result` 也没更新）。
2. **为什么没点菜**：SYSTEM_PROMPT 上下文要素写的是"有已上传文档就直接调（不传参数）；没有就请用户上传或贴出来"。但模型**看不到模块级 `_current_doc`**——它只知道人设里"先确认手头有没有需求内容"这句话，于是把规则理解成了"先跟用户确认需求来源"，而不是"直接调工具"。注意文档其实**已加载成功**（开头 `📄 已加载文档` 说明 `set_current_doc` 已注入），模型却选了保守路线——**真实模型行为，实录原样保留，没有修改**。
3. **教学价值**：这就是"模型点菜"随机性的实证——同样的人设，这轮没点。摘要-非-全文的设计（工具回传紧凑摘要，见第二节）本轮没有机会上场，但正因如此，实录恰好演示了"模型没点菜时会怎样"：它不编造结果，老老实实问用户。**工具调没调，完全由模型决定**——这正是"模型点菜，代码上菜"的本质。

### 第 3 轮：字段校验（没有点菜——模型要求补充字段信息）

~~~
👤 用户：第一个字段的类型和字节数对吗
🤖 助手：你提到了"第一个字段"，但我需要更多信息才能帮你校验。请告诉我：

- **字段名**是什么？
- **字段类型**是什么？（如 uint8 / int16 / float32 / string 等）
- **声明的字节数**是多少？

比如你可以这样说：
> "校验一下 device_id 字段，uint8，2字节"

或者如果你有具体的协议内容，直接把字段信息贴给我，我来帮你校验！😊
============================================================
~~~

**模型在这一步做了什么**：识别出这是字段校验请求，但**没有点菜** `validate_field_type`——它要求用户补充字段名 / 类型 / 字节数。原因很合理：`validate_field_type` 需要参数（字段名/类型/字节数，见 4.2），而上一轮协议没有生成（模型没拿到任何字段信息），"第一个字段"无从谈起——模型选择**先要参数再校验**，而不是拿着空参数硬调工具。整轮无 🔧 标记，纯对话答复。

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
# 期望输出：✅ AppTest 冒烟通过：上传注入 / 假聊天一轮 / 历史累积 2 条 / 无异常
```

**为什么值得做**：真调 API 的测试又慢又花钱又看运气；冒烟把"UI 机制不崩"这件事从人工验证变成一条命令，改动 app.py 后立刻能回归。测试不花钱的前提是**大脑可替换**——这正是第一节"解耦"设计带来的红利。

---

## 八、踩坑

| # | 坑 | 教训 / 处理 |
|---|-----|------------|
| 1 | **🔧 标记里参数显示 `（{}）`**：点菜发生时，标记打出的参数是空的，但工具实际执行成功（读到了文档、校验正确）。机制：`stream_mode="messages"` 下 tool_call 的 args 是**跨 chunk 累加**的，标记在第一个 chunk 就打出去了（此时 args 还没到），之后按 id 去重不再重打。第六节本次实录里模型两轮都没点菜（连 🔧 标记都没出现），但现象来自流式机制本身、与模型行为无关，机制说明照旧 | 标记是"模型点菜信号"，不是参数转储；要精确参数得自己拼后续 chunk 的 args。实录原样保留（含"没点菜"的轮次） |
| 2 | **create_react_agent 弃用警告**（langgraph 1.2.9 + langchain 1.3.14 实测）：构建 agent 时打 `LangGraphDeprecatedSinceV10: create_react_agent has been moved to 'langchain.agents'. Please update your import to 'from langchain.agents import create_agent'. Deprecated in LangGraph V1.0 to be removed in V2.0.` | **现在能用**，不用急着改；**V2 后要换导入路径**：`from langchain.agents import create_agent`。改时验证函数签名是否一致即可 |
| 3 | **recursion limit 设计值 vs 实测值**：设计规格写"内置上限 25"，实测 langgraph 1.2.9 默认 **10007**（`DEFAULT_RECURSION_LIMIT`，可被 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 环境变量或 `config={"recursion_limit": N}` 覆盖） | 版本差异正常，**以实测为准**；防死循环机制内置是真的，具体数值别写死进文档 |
| 4 | **AppTest 冷启动超时**：本机首次运行光 import app（langchain/rag 链）就要 ~5.2s，AppTest 默认 3s 超时在初始渲染处误报 `RuntimeError: AppTest script run timed out` | `AppTest.from_file(..., default_timeout=30)` |
| 5 | **file_uploader.set_value API 变化**：streamlit 1.62.0 只接受 `(name, content, mime)` 元组；旧写法传文件对象（FileMock）报 `TypeError: 'FileMock' object is not iterable` | `at.file_uploader[0].set_value((sample.name, sample.read_bytes(), "text/markdown"))` |
| 6 | **实录环境噪音**：transcript 开头两行 requests 依赖警告（urllib3/chardet 版本不匹配）不是程序行为 | 裁剪并注明"环境噪音"；本项目跑脚本一律 `PYTHONIOENCODING=utf-8` 前缀（坑 #5） |

---

## 深挖

- 三零件与选型：[extra_chat_agent.md](extra_chat_agent.md)
- Graph B 图版工具循环：`scripts/extra_langgraph_intro.py`（model/tools 节点 + 条件边，第 86-116 行）
- 手写工具循环（点菜/上菜）：[phase4_tool_calling.md](phase4_tool_calling.md)
- 把整条 rag_chain 包成工具：`scripts/chat_agent.py` 的 `generate_protocol`
- Streamlit 心智模型与 AppTest：[phase5_deploy.md](phase5_deploy.md)
