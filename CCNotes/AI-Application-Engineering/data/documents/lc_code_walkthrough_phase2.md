# 代码精读 2：phase2_1_langchain_basics.py（LangChain 重写版）

> 同一功能（需求 → 字段表），用 LangChain 重写。读法主线：**每个原生零件，看 LangChain 用什么盒子替代了它**。
> 读前先过一遍 `code_walkthrough_phase1.md`（原生版）。

## 四大块

### 第 A 块：导入 + 配置（12~26 行）

| 新导入 | 替代的原生物 |
|--------|-------------|
| `ChatPromptTemplate`（langchain_core.prompts） | `SYSTEM_PROMPT` 字符串 + 手拼 messages |
| `JsonOutputParser`（langchain_core.output_parsers） | `_parse_response` 四道保险容错 |
| `ChatOpenAI`（langchain_openai） | `OpenAI()` + `.chat.completions.create` |

配置区与 phase1_4 完全一致（环境变量 Key、DeepSeek base_url）——换模型只改参数，从此兑现。

### 第 B 块：PROTOCOL_PROMPT 模板（34~73 行）

- 元组简写 `("system", """...""")` ≡ 原生 `{"role": "system", "content": ...}`，纯书写简洁
- 占位符 `{requirement}` 是"留坑"，invoke 时填充；`{{ }}` 是花括号字面量（JSON 骨架必须双写）——LangChain 新手第一坑
- 说明书四要素与 phase1_4 完全一样——好 Prompt 不随框架变

### 第 C 块：三件套组装（75~110 行）

- `ChatOpenAI`：创建+调用打包成统一盒子，参数与原生完全一样（底层还是 OpenAI 协议）
- `JsonOutputParser()`：四道保险变 1 行——不是魔法，是"常见坑被 LangChain 打包维护"，你手写过所以知道它挡什么
- `chain = PROMPT | llm | parser`：三个不同类型盒子凭**统一接口**拼成 RunnableSequence（透视实验：`.steps` 依次是 ChatPromptTemplate / ChatOpenAI / JsonOutputParser）
- 框架边界：打印、try/except、存文件**不被框架吸收**——框架帮通用，不替业务

### 第 D 块：main 入口（144~169 行）

- 核心调用两行变一行：`chain.invoke({"requirement": requirement})`——组装前置到声明处，main 只剩"按开关"
- 传参从裸字符串变成**字典**：管道输入是"带标签的包裹"，键名 = 占位符名（3.2 多步链的伏笔）
- 其余（保护/try/存文件/哨兵）与 phase1_4 一模一样

## 全景结论

**代码变短不是删了功能，是把重复劳动搬进盒子——总工作量没消失，只是"你每次写"变成"别人替你写好了、测好了"。** 这就是用框架的全部理由。

## 精读途中用户追问的概念（修正与补充）

### 1. f-string 也能复用模板，那和占位符的区别到底是什么？

**修正**：区别不在"能不能复用"（f-string/format 也能拆出常量模板复用），而在**接口**：

| | 手写模板函数 | ChatPromptTemplate |
|---|---|---|
| 产出 | dict 列表（碰巧 OpenAI 接受） | 标准消息对象（LangChain 负责翻译） |
| 管道资格 | ❌ 无 invoke 接口，`\|` 报 TypeError | ✅ 标准积木 |
| 想进管道 | 自己包 RunnableLambda（手搓弱化版模板） | 现成 |

判断标准：**要进管道用积木，不组装直接拼**。phase1_4 用 f-string 完全正确。

### 2. 用 LangChain 必须搭配模板吗？

不必须。工具箱不是规矩。phase4_2 的工具循环直接手写 `SystemMessage`/`HumanMessage`（消息动态增长，模板不适合）。口诀：**固定用模板，动态用手写；要进管道，得有接口。**

### 3. RunnableLambda 是什么？

普通函数的"乐高转接头"：把 `def f(x)` 包装成带 `.invoke` 的标准积木，行为不变、接口变标准，从而能进管道。项目实例：3.2 的 `RunnableLambda(merge_final)`、4.1 的检索步骤、3.2 的 tap。

## 自测清单

1. 三个盒子类型不同，凭什么能拼成 chain？
2. `{{ }}` 和 `{requirement}` 在模板里分别是什么？
3. 为什么 chain.invoke 的输入是字典而不是裸字符串？
4. 哪些部分没有被框架吸收？为什么？

---

# 代码精读 3：phase2_2_lcel_pipeline.py（并行分叉）

> 在 2.1 的直线上装"分叉"。数据流形状：直线 → 钻石形（分叉再合并）。

## 数据流

```
{"requirement":...} → base_chain（2.1 直线）→ {protocol_name, fields, timing}
    ├─► RunnableLambda(validate_fields)   → field_check
    ├─► RunnableLambda(validate_timing)   → timing_check
    ├─► RunnableLambda(count_bytes)       → byte_count
    └─► RunnablePassthrough()             → protocol（原样保留）
    → 合并成 4 键大字典 → print_result 按分支名取键展示
```

## 三个要点

1. **业务与编排分离**：三个校验函数是纯普通函数（无 LangChain 痕迹），组装时才包 `RunnableLambda` 装接口。改校验规则不动管道，改管道不动规则。
2. **RunnableParallel**：输入同时发给所有分支，结果按"分支名=输出键名"合并成 dict——分支名就是数据流的物流标签。
3. **积木套积木**：`full_chain = base_chain | validation_chain`——2.1 拼好的 chain 在这里当零件再拼。

## 零成本实验（不调 API）

手工伪造 dict 喂 `validation_chain.invoke()`：三个分支各自独立干活（揪出缺 length 字段、发现 timing 空、算出字节数），protocol 透传原样——并行分支互不干扰。可运行文件：`scripts/demo_2_2_checks.py`。

## 重要边界：校验只能查"形式"，查不了"内容"

| 检查类型 | 例子 | 2.2 查得了吗 |
|---------|------|-------------|
| 形式：字段齐不齐、频率填没填、字节加对没加对 | 缺 length、timing 空 | ✅ |
| 内容：类型选得对不对、设计合不合理 | uint8 表示 -40℃（负数装不下） | ❌ |

实测：形式完美但内容荒谬的协议（temperature 用 uint8），field_check 返回 `valid: true`——**校验通过 ≠ 协议正确**。

"确认正确"没有单点答案，四层保险各管一层：代码查形式（2.2/4.2）、LLM 查内容（3.2 ③评审）、人做终审（4.3）。2.2 的校验只"旁路监督"（打印报告，不自动修错），闭环修复要到 4.3 才有。

## LCEL 三种组装汇总

| 组装 | 写法 |
|------|------|
| 串联 | `a \| b` |
| 并行 | `RunnableParallel(键=分支)` |
| 自定义 | `RunnableLambda(普通函数)` |

消费并行结果 = 按分支名取键（`result["field_check"]`）。

---

# 代码精读 4：phase2_3_output_parsers.py（Parser 三路对比）

> 核心命题：**模型输出永远是文字，Parser 决定它最后变成什么类型。** 同一条链，唯一区别是最后装不装 Parser、装哪个。

## 三条路（执行示例实测）

| 路 | 组装 | 输出类型 | 适用 |
|----|------|---------|------|
| 1 无 Parser | `SUMMARY_PROMPT \| llm` | `AIMessage`（文字在 `.content`，对象里还有元数据） | 基本不直接用 |
| 2 Str | `... \| StrOutputParser()` | `TextAccessor`——**str 的子类**（`isinstance str: True`），带懒转换方法 | 文本给人看/写文档/拼接 |
| 3 Json | `... \| JsonOutputParser()` | `dict` | 数据给程序算 |

彩蛋：LangChain 1.x 的 StrOutputParser 返回 `TextAccessor` 而非 `str`——判断类型用 `isinstance` 不用 `type()`。JsonOutputParser 内部就是 phase1_4 手写的四道保险（剥围栏 → loads → 截取花括号 → 带证据报错）。

选型口诀：**下游要文本用 Str，要结构化用 Json**。

入口风格细节：本脚本 `sys.argv[1] if len(sys.argv) > 1 else 默认值`——演示脚本给默认值；工具脚本（phase1_4/2_1）没参数就退出。两种入口风格。

### 四大块速览（完整精读版）

| 块 | 内容 | 要点 |
|----|------|------|
| A 导入配置 | 新面孔 `StrOutputParser` | 与 JsonOutputParser 同族 |
| B 两份说明书 | `SUMMARY_PROMPT`（要纯文本）vs `JSON_PROMPT`（要 JSON） | **说明书的目的决定输出形态**——Parser 解析的 JSON 是说明书先要求出来的 |
| C 三条链 | 唯一区别是"最后装了什么"：不装 / Str / Json | 路1 AIMessage（文字在 `.content`，对象还装元数据）；路2 TextAccessor（str 子类，用 `isinstance` 判断）；路3 dict（内部原理 = phase1_4 手写的四道保险，标准化成积木） |
| D main | 默认需求值 / 函数内 import os / 双文件保存 | 演示脚本给默认值 vs 工具脚本要参数 |

自测：① 模型为什么返回对象而不是字符串？② TextAccessor 用 `type()==str` 判断对不对？③ JsonOutputParser 的原理在哪份脚本手写过？
