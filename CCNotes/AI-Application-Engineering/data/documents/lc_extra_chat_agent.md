# 对话式 Agent：为什么公司内部助手都有聊天窗口

> 2026-08-30。回答"别人家的 agent 助手有对话窗口，咱们怎么没有"——拆解对话窗口的本质、三层零件、现成框架选型。**结论：零件你全学过，只差拼装。**

## 一、两种模式的区别

| | 我们现在的（批处理管道） | 对话式 Agent |
|---|---|---|
| 交互 | 上传文件 → 点按钮 → 出结果 | 聊天框发消息 → 回答 → 追问 → 再回答 |
| Prompt | 写死在代码/模板文件里 | 用户输入动态生成（人设/工具说明仍在 system 里写死） |
| 运行 | 一条链跑一遍 | **循环**：模型 →（思考/调工具）→ 工具结果 → 模型 → … → 答复 |
| 状态 | 无（每次独立） | 会话历史累积，每轮把全部历史重发 |
| LLM 调用次数 | 固定（如四步链 3 次） | 不固定，模型自己决定（4.2 实测模型自主发起 7 次校验） |

"大模型会进行思考"的真相没有魔法：**思考 = 模型输出 tool_calls（点菜）→ 代码执行 → 结果回传 → 模型继续**，直到模型不再点菜、输出最终答复。这正是 4.2 手写工具循环干的事（模型点菜/代码上菜），LangGraph Graph B 是它的图版。

## 二、对话窗口 = 三个零件（项目里都有现成的）

| 零件 | 干什么 | 项目里已有的 | 官方封装 |
|------|--------|------------|---------|
| 会话历史 | messages 列表，每轮追加，全量重发 | 第 6 章三种消息、4.2 的 `messages = messages + [response] + tool_msgs` | — |
| Agent 循环 | 模型↔工具来回直到说完 | `phase4_2_tool_calling.py` 手写 while（上限 5 轮） | `langgraph.prebuilt.create_react_agent` |
| 聊天 UI | 输入框 + 消息气泡 + 打字机输出 | `app.py` Streamlit 薄壳（5.1） | Streamlit 聊天组件 / Chainlit |

## 三、对话循环的最小内核（零成本演示）

去掉 UI 和真模型，对话助手的内核就是这么短（假模型不调 API，零成本）：

```python
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

def fake_llm(messages):
    rounds = sum(1 for m in messages if isinstance(m, HumanMessage))
    return AIMessage(content=f"我看到了 {rounds} 轮历史，这是第 {rounds} 次回答")

history = [SystemMessage("你是内部协议助手")]
for question in ["什么是协议字段表？", "字段要多少字节？"]:
    history.append(HumanMessage(question))
    answer = fake_llm(history)          # 关键：每轮把【全部历史】发出去
    history.append(answer)
    print(f"用户: {question}\n助手: {answer.content}\n")
print(f"messages 列表长度 = {len(history)}（历史在累积，这就是对话的本质）")
```

实际输出（`scripts/demo_chat_loop.py` 2026-08-30 实跑；开头一行 requests 依赖警告属环境噪音，已裁掉）：

```
用户: 什么是协议字段表？
助手: 我看到了 1 轮历史，这是第 1 次回答

用户: 字段要多少字节？
助手: 我看到了 2 轮历史，这是第 2 次回答

messages 列表长度 = 5（历史在累积，这就是对话的本质）
```

把 `fake_llm` 换成 `llm_with_tools`（4.2 的带工具模型），这个循环就"会思考"了；把 print 换成网页气泡，就是聊天窗口。

## 四、现成框架选型（三层分开选，别混着比）

### 1. Agent 循环层（对话的"大脑"）

| 方案 | 评价 |
|------|------|
| **LangGraph `create_react_agent`**（推荐） | Graph B 的官方成品版：循环、上限、工具执行全封装，一个函数搞定 |
| LangChain `AgentExecutor` | 旧 API，能用但官方主推 LangGraph |
| 手写 while | 教学价值最高（4.2 已做过）；生产别手搓，边缘情况多 |

### 2. Chat UI 层（对话的"脸"）

| 方案 | 特点 | 适合 |
|------|------|------|
| **Streamlit 聊天组件**（推荐） | `st.chat_input` + `st.chat_message` 原生聊天 UI；项目已用 Streamlit，升级成本最低 | 内部工具、快速验证 |
| Chainlit | 专为 LLM 聊天而生：消息流、步骤折叠、工具调用可视化开箱即用；pip 即装 | 想更好看的内部助手 |
| Gradio `ChatInterface` | 几行代码出聊天页，HF 出品 | 演示/分享 |
| Open WebUI / LibreChat | 自托管聊天产品，配 OpenAI 兼容接口即用（DeepSeek 直连） | 不想写任何代码 |
| React/Vue 手搓 + SSE | 可控性最强 | 只有品牌深度定制/权限/审计要求高才选 |

### 3. 开箱即用产品级（配置为主，写代码为辅）

- **Dify / FastGPT**（开源，可自部署）：拖拽配知识库 + 工具 + 工作流 + 自带聊天 UI。公司内部助手很多是这套
- 代价：平台锁定、深度定制难、自部署要运维

## 五、结论：要不要手搓？

- **循环层：不手搓**——LangGraph 已经替你封装了（你还会看图）
- **UI 层：90% 场景不手搓**——Streamlit/Chainlit 就是为这个场景设计的
- **只有品牌定制/权限审计要求高**，才值得手搓前端（且此时重头戏在权限和审计，不在聊天窗口本身）

对咱们项目的最短路径：`app.py` 升级聊天模式 = Streamlit 聊天组件 + 现有 agent 循环 + 现有 rag_chain，零件全复用。

## 六、深挖

- 工具循环原理：[phase4_tool_calling.md](phase4_tool_calling.md)
- 图与条件边：[extra_langchain_langgraph.md](extra_langchain_langgraph.md)
- Streamlit 心智模型：[phase5_deploy.md](phase5_deploy.md)
- 官方：https://docs.langchain.com/oss/python/langchain/agents / https://chainlit.io
