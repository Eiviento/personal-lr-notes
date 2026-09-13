# Python 装饰器：`@` 到底是什么（读懂 `@tool` / `@mcp.tool()`）

> 2026-09-13 实操跑通（`scripts/extra_python_decorator.py` 五个实验，附真实运行输出）。覆盖：一句话理解 / 语法糖是什么 / `@` 是语法糖 / **名字是标签（包完之后 `validate_field_type` 指向谁）** / 带括号与不带括号 / 注册型 vs 替换型 / 逐行点名项目里那段代码 / 三个坑 / 速记表。
>
> 学习动线：`scripts/phase4_2_tool_calling.py` 的 `@tool`、`scripts/demo_mcp_server.py` 的 `@mcp.tool()`——一个不带括号、一个带括号。这不是魔法，是 Python 同一个语法：**装饰器**。这课把地基补上。

## 一、一句话理解

**装饰器 = 一个"接收函数、返回函数"的函数。`@` 是把「定义完函数后紧接着做的包装动作」写到函数头顶的语法糖。**

用三句话就能说清：

1. `@tool` 让 Python 去做 `validate_field_type = tool(validate_field_type)` 这件事。
2. 这个赋值**把函数名字重新贴到了 `tool()` 的返回值上**——所以装饰之后你再写 `validate_field_type(...)`，调到的已经不是原来那个函数了。
3. 至于原函数还在不在、还能不能调，取决于 `tool()` 返回了什么。LangChain 的 `@tool` 返回工具对象（原函数藏进 `.func`），FastMCP 的 `@mcp.tool()` 返回原函数本身。

不带 `@` 你要这么写：

```python
def validate_field_type(...):
    ...

validate_field_type = tool(validate_field_type)   # ← 手动包一层
```

带 `@` 就变成：

```python
@tool                                              # ← 同一件事，写在头顶
def validate_field_type(...):
    ...
```

**两者完全等价，一个字节的差别都没有。** 这就是全部。剩下所有看似复杂的花样（带括号、带参数、多个叠着写）都是这条规则的推论。

## 二、"语法糖"是什么，以及 `@` 是哪种糖

**语法糖（syntactic sugar）= 一种让代码更好写、更好读的简写形式，它不提供任何新能力。** 解释器会在背后把它翻译成原本那套更啰嗦的写法——糖衣在里面，药是一样的。

这个名字是"糖衣"的比喻：真正的药（底层那一堆啰嗦代码）还是得吃，但裹上糖衣就好咽了。

你早就在用的糖：

| 糖（好写） | 它其实的意思（啰嗦但本质） |
|-----------|--------------------------|
| `a += 1` | `a = a + 1` |
| `for x in [1,2]:` | 手写迭代器：`while` + `__next__()` + 捕获 `StopIteration` |
| `f"你好{name}"` | `"你好" + str(name)`（f-string 就是拼字符串的糖） |
| `a, b = b, a` | 用临时变量 `tmp` 三步交换 |
| `@deco` | `def f(): ...` 之后紧接着 `f = deco(f)` ← **本课主角** |

**为什么要有糖？** 因为"定义完函数后立刻包一层、再赋回原名字"这个动作在框架里出现得太频繁（每个工具、每个路由都要来一次）。手写一是容易漏，二是会把函数本体埋进一堆赋值里。`@` 把这件事挪到函数头顶，一眼就能看出"这个函数被谁管着"。

**不做会怎样？** 也不报错——你完全可以全部手写。但在 MCP 服务器里，一个函数没被 `@mcp.tool()` 包过，就**根本不会出现在工具清单里**：客户端看不见它，模型永远调不到，而且不报错。这就是为什么这个语法值得搞清楚。

### `@` 拆开看就三步

Python 解释器遇到 `@deco` 时，实际执行的是：

```
第 1 步：正常定义函数，得到一个函数对象          →  func
第 2 步：把它交给装饰器                        →  deco(func)
第 3 步：用返回值覆盖原来的名字                 →  func = 上面那个返回值
```

实测（`scripts/extra_python_decorator.py` 实验 1）：

```
写法A（手动包）: 【你好】
写法B（用 @ ）: 【你好】
两者跟『原样包一遍』产出一样吗？ True
```

> **为什么要有这个语法？** 因为"包装"这件事在框架里出现得太频繁了——每个工具函数都要注册一次、每个路由都要登记一次。如果全靠手写 `xxx = deco(xxx)`，一是容易漏，二是会把函数本体埋在一堆赋值里。`@` 把这件事**挪到函数头顶**，一眼就能看出"这个函数被谁管着"。
>
> **不做会怎样？** 也不是不行——你完全可以手动写。但在 MCP 服务器里，一个函数没被 `@mcp.tool()` 包过，就**根本不会出现在工具清单里**，客户端看不见它，模型也就永远调不到。这是静默失败：不报错，就是没反应。

## 三、名字是标签：包完之后，`validate_field_type` 指向谁？

这是第二步 `f = deco(f)` 里**最反直觉的一格**。既然写的是 `validate_field_type = tool(validate_field_type)`，那"我平时调用 `validate_field_type` 的时候，到底在调什么？"

**答案：装饰之后，你就不是在调那个函数了。**

把名字理解成**贴在盒子上的标签**，不是盒子本身：

```
第 ① 步：造了个函数盒子        ── 贴上标签『subtract』
第 ② 步：tool(函数) 造了个工具盒子（把①装进去）
                                ── 标签还贴在①上，此时①和工具盒子同时存在
第 ③ 步：subtract = 工具盒子    ── 把标签从①上撕下来，贴到工具盒子上
```

实验 3 用 `id()` 把这个过程拍了下来：

```
① 刚 def 完      → subtract 指向: function      | id = 2041696393760
② tool() 的产物  → 类型: StructuredTool | id = 2041753677200 | 是①那个对象吗? False
③ 覆盖之后       → subtract 指向: StructuredTool | id = 2041753677200

旧盒子躲在哪儿？ function | id = 2041696393760 | 还是①那个盒子吗? True
```

**关键：旧盒子没被销毁，只是眼下没有名字指着它了。它还活着，躲在 `.func` 属性里。**

同一个函数，三种叫法：

```
subtract(5, 3)                 → TypeError: 'StructuredTool' object is not callable
subtract.func(5, 3)            → 2  ← 掀开盖子，直接调原函数
subtract.invoke({"a":5,"b":3}) → 2  ← 打包后的标准调法
```

> 注意第一行的 `TypeError: 'StructuredTool' object is not callable`——它不是说"没有这个对象"，而是说"这个对象**不能被这样调用**"。变量名叫 `subtract`，值却是个工具对象，Python 找不到它的 `__call__` 方法，就报这个错。
>
> **反过来看 FastMCP**：`@mcp.tool()` 返回的是原函数本身，标签贴回原来的盒子，所以 `validate_field_type(5, 3)` 照样能调。这就是下一节要讲的"两种哲学"。

### 想自己跑一遍看效果？→ `scripts/demo_tool_after_decorator.py`

一个 60 行的最小对照脚本，拿同一个函数的两份拷贝，用**一样的 6 种调用方式**各试一遍：

```
【对照组 A】普通函数，没有 @tool     f 的类型 = function | callable(f) = True
  ✅ ① 直接调用        f(1, 2)                        → 3
  ✅ ② 关键字调用      f(a=1, b=2)                    → 3
  ✅ ③ 放进字典再调    d["add"](1, 2)   ← FUNC_MAP 用法 → 3
  ✅ ④ 当参数传给别的函数  apply(f, 1, 2)              → 3
  ✅ ⑤ 看身份          f.__name__                     → 'add_plain'
  ❌ ⑥ 工具的标准调法  f.invoke({"a": 1, "b": 2})
       → AttributeError: 'function' object has no attribute 'invoke'

【实验组 B】同一个函数，头上加了 @tool   f 的类型 = StructuredTool | callable(f) = False
  ❌ ① 直接调用        f(1, 2)
       → TypeError: 'StructuredTool' object is not callable
  ❌ ② 关键字调用      f(a=1, b=2)                    → 同上 TypeError
  ❌ ③ 放进字典再调    d["add"](1, 2)   ← FUNC_MAP 用法 → 同上 TypeError
  ❌ ④ 当参数传给别的函数  apply(f, 1, 2)              → 同上 TypeError
  ❌ ⑤ 看身份          f.__name__
       → AttributeError: 'StructuredTool' object has no attribute '__name__'
  ✅ ⑥ 工具的标准调法  f.invoke({"a": 1, "b": 2})      → 3
```

**两个信息量最大的点：**

- `callable(f)` 从 `True` 变成 `False`——这就是①~④集体报 `not callable` 的根本原因，一行验完。
- **③ 是最容易踩的坑**：字典本身没问题（`FUNC_MAP` 那行代码写得对），是**里面的值被调用时**才炸。而模型的 `tool_calls` 回传的参数本来就是 JSON 字典，`.invoke()` 正好对上。

另外 `__name__` 也没了（改用 `.name`），docstring 搬到了 `.description`——这正是工具说明书的来源。原函数则完整地藏在 `.func` 里，`add_tooled.func(1, 2)` 照样返回 `3`。

完整输出存于 `outputs/demo_tool_after_decorator.log`。

## 四、带括号 vs 不带括号：装饰器工厂

这是新手最容易懵的一格。

| 写法 | 名字 | 谁在干装饰的活 |
|------|------|---------------|
| `@tool` | 裸装饰器 | `tool` 自己就是装饰器，直接收函数 |
| `@mcp.tool()` | **装饰器工厂** | `mcp.tool()` 先执行，**返回**一个装饰器，由它去包函数 |
| `@mcp.resource("protocol-tools://fixed-size/table")` | 装饰器工厂（带参数） | 同上，括号里的字符串是配置 |

拆开 `@mcp.tool()` 看两步：

```
第一步：mcp.tool()          → 执行！返回一个装饰器函数      ← 括号在这里就用掉了
第二步：(返回的装饰器)(函数)  → 这个装饰器再去包函数
```

为什么 `@mcp.tool()` 明明一个参数都不传也非得写括号？因为 FastMCP 的函数签名长这样：

```python
def tool(self, name=None, title=None, description=None, ...) -> Callable[[AnyFunction], AnyFunction]:
                                                              └──── 返回值是一个装饰器 ────┘
```

它**必须被调用一次**才能拿到装饰器。而 LangChain 的 `@tool` 两种写法都支持（实验 4 验证：`@tool` 和 `@tool("named_add")` 都跑通）——因为它的第一个参数是 `name_or_callable`，收到函数就当裸用、收到字符串就当工厂。

> **两个库设计不同，不是 Python 语法不同。** 记不住就记住这句：**看到括号，就说明先执行了一次函数调用。**

## 五、装饰器返回什么，决定原函数还在不在

这是整个知识点里最实用的一格。装饰器最后返回的那个东西，会**顶替掉原函数的名字**：

```
                        FastMCP @mcp.tool()          LangChain @tool
                        （注册型）                    （替换型）
─────────────────────────────────────────────────────────────────────────
返回什么                 原函数本身                    一个 StructuredTool 对象
装饰后 my_func(1,2)      能跑                          不能 → TypeError
正确调法                 my_func(1, 2)                 my_func.invoke({"a":1,"b":2})
模型怎么知道它           服务器从注册表里翻出来          这个对象自带 schema
```

实验 4 实测：

```
── 哲学 A：注册型 ──
注册表里现在有: ['my_tool']
函数还是函数吗？ function | 直接调用 → 我还能当普通函数用

── 哲学 B：替换型（LangChain 的 @tool 就是这么干的）──
add_bare  现在是什么类型: StructuredTool | 名字: add_bare
当普通函数调 → TypeError: 'StructuredTool' object is not callable
正确调法 → 3
```

> **为什么 FastMCP 选注册型？** MCP 是"插头标准"，服务器启动时把函数登记好、等客户端来调；原函数在服务器内部还得被正常执行，留着最省事。
>
> **为什么 LangChain 选替换型？** `@tool` 的产物要直接塞进 `bind_tools([...])` 交给模型，它必须是一个自带 `name` / `description` / `args_schema` 的 Runnable 对象——所以干脆整只换掉。

**共同点（最重要）：两者都靠函数头上的「类型注解 + docstring」生成 JSON Schema。**

## 六、逐行点名：项目里 `@tool` 那段代码

```python
@tool                                    # ← ① 装饰器：把下面的函数变成 StructuredTool
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    #    ② 类型注解 ──→ 变成 JSON Schema 的参数表，模型的"怎么填"
    """校验协议字段的类型与字节数是否匹配。参数：..."""
    #   ③ docstring ──→ 变成 description，模型的"什么时候用"
    ...
```

**这一行 `@tool` 造成的连锁反应，在同一个文件里能顺着看下去**（`phase4_2_tool_calling.py`）：

```python
第 40 行   @tool
           def validate_field_type(...): ...
                                                  ↑ 此刻 validate_field_type 已经被
                                                    换成 StructuredTool（第三节讲的换标签）

第 55 行   FUNC_MAP = {"validate_field_type": validate_field_type}
                                          ↑ 进字典的是 StructuredTool，不是函数

第 61 行   llm_with_tools = llm.bind_tools([validate_field_type])
                                          ↑ bind_tools 要的正是工具对象，
                                            这也反过来说明 @tool 为什么必须替换型

第 73 行   result = str(FUNC_MAP[name].invoke(args))
                                     ↑ 所以 .invoke() 不是多余的包装，是必须的
```

> `.invoke(args)` 内部做的事：收一个字典 → 拆成关键字参数 → 转交给躲在 `.func` 里的那个真正的函数。
>
> 它为什么非得收字典？因为模型回传的 `tool_calls` 里，参数本来就是 JSON（字典形态）。LangChain 顺手把字典当成了所有工具的**统一入口**——这样不管原函数签名长什么样，调用方永远只用写 `.invoke({...})`。

实验 5 用真实 FastMCP 跑了一遍同一个函数，把"注解+docstring 怎么变成说明书"直接打了出来：

```
  名字: validate_field_type
  描述: 校验协议字段的类型与字节数是否匹配。
    参数：field_name 字段名；field_type 数据类型（uint8/int16/float32/string 等）；length 声明的字节数。
  参数说明书 (JSON Schema):
    {'properties': {'field_name': {'title': 'Field Name', 'type': 'string'},
                    'field_type': {'title': 'Field Type', 'type': 'string'},
                    'length': {'title': 'Length', 'type': 'integer'}},
     'required': ['field_name', 'field_type', 'length'], ...}
```

对应关系：

```
你写的代码                              模型看到的东西
──────────────────────────────────      ──────────────────────────────────
def validate_field_type(             →  "name": "validate_field_type"
field_name: str,                     →  "field_name": {"type": "string"}
length: int)                         →  "length": {"type": "integer"}
"""校验协议字段的类型与字节数…"""       →  "description": "校验协议字段的…"
```

两个库都是靠 Python 的 `inspect` 模块读这两样东西自动生成的。

> **实用推论：工具函数里的类型注解和 docstring 不是"注释"，是给模型看的说明书正文。**
>
> - 注解写漏一个 → 模型少看到一行参数说明 → 调用时瞎猜 → 报错。
> - docstring 只写"做什么"不写"什么时候用" → 模型不知道何时该调这个工具，可能该调的时候不调。
>
> 这就是为什么 `phase4_2` 的设计原则是"**死规则交给代码**"——写一次注解，模型每次都看到准确的那份说明书，不会像让它背 `uint8 占 1 字节` 那样背错。

## 七、实测输出（`scripts/extra_python_decorator.py`）

零 LLM 成本、不联网，五个实验一次跑完：

```
实验 1｜@ 只是语法糖：@deco 等价于 f = deco(f)
写法A（手动包）: 【你好】
写法B（用 @ ）: 【你好】
两者跟『原样包一遍』产出一样吗？ True

不用 functools.wraps →  名字: wrapper | 文档: None
用了 functools.wraps →  名字: named | 文档: 我是一个有文档字符串的函数
（MCP/LangChain 要靠 __name__ 和 __doc__ 生成工具说明书，所以这里必须加）

实验 2｜两种形态：@deco（裸）vs @deco()（带括号 = 装饰器工厂）
@tag          → <裸用>
@tag_with("<<")→ <<带括号<<

实验 3｜名字去哪儿了：包完之后 validate_field_type 这个名字指向谁？
① 刚 def 完      → subtract 指向: function | id = 2041696393760
② tool() 的产物  → 类型: StructuredTool | id = 2041753677200 | 是①那个对象吗? False
③ 覆盖之后       → subtract 指向: StructuredTool | id = 2041753677200
旧盒子躲在哪儿？ function | id = 2041696393760 | 还是①那个盒子吗? True

同一个函数，三种叫法，结果对比：
  subtract(5, 3)                 → TypeError: 'StructuredTool' object is not callable
  subtract.func(5, 3)            → 2  ← 掀开盖子，直接调原函数
  subtract.invoke({"a":5,"b":3}) → 2  ← 打包后的标准调法

实验 4｜两种哲学：注册型（原函数留着）vs 替换型（原函数被换掉）
add_bare  现在是什么类型: StructuredTool | 名字: add_bare
当普通函数调 → TypeError: 'StructuredTool' object is not callable
正确调法 → 3

实验 5｜回到项目：真实 FastMCP 把 docstring + 类型注解变成 JSON Schema
装饰一下之后，validate_field_type 还是普通函数吗？ function
  | 直接调 → seq: uint8 标准 1 字节，声明 1 → 合法
但服务器内部已经悄悄记下了它。问服务器要工具清单： 名字: validate_field_type
```

完整输出存于 `outputs/extra_python_decorator.log`。

## 八、三个坑

### 坑 1：`@mcp.tool` 忘了括号

```
TypeError: The @tool decorator was used incorrectly.
Did you forget to call it? Use @tool() instead of @tool
```

这是**唯一的报错型坑**，还算幸运。但注意：这个友好报错是 FastMCP 特意写的防护。自己写的装饰器工厂忘了括号，通常不会报错，而是**静默失效**（函数没被注册，模型中永远看不到这个工具）。所以看到 `@xxx()` 时，请立刻确认括号在不在。

### 坑 2：`functools.wraps` 漏了 → 所有工具同名

自定义装饰器时，`wrapper` 会顶替原函数的 `__name__` 和 `__doc__`：

```
不用 functools.wraps →  名字: wrapper | 文档: None
```

一个工具叫 `wrapper` 还能忍，**十个工具全叫 `wrapper`**，服务器的注册表就彻底乱了，而且 docstring 丢失 = 模型的 description 为空。

```python
import functools

def my_decorator(func):
    @functools.wraps(func)          # ← 加这一行，把原函数的身份复制过来
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

> 用现成的 `@tool` / `@mcp.tool()` 不会遇到这个（库内部已经处理了），**但自己写装饰器时必须加**。

### 坑 3：多个装饰器叠着写，执行顺序是「从下往上」

```python
@a
@b
def f(): ...
```

等价于 `f = a(b(f))`：**离函数近的先包（b 先执行），离函数远的后包（a 后执行）**。读代码时从下往上读，写代码时最上面那个是"最外层"。

## 九、速记表

| 你看到 | 它是什么 | 拆开等价于 |
|--------|---------|-----------|
| `@deco` | 裸装饰器 | `f = deco(f)` |
| `@deco()` | 装饰器工厂 | `f = deco()(f)` |
| `@deco("参数")` | 装饰器工厂（带配置） | `f = deco("参数")(f)` |
| `@a` `@b` 叠着 | 顺序从下往上 | `f = a(b(f))` |
| `@tool`（LangChain） | 双形态，返回 `StructuredTool` | 原函数被**替换**，用 `.invoke()` |
| `@mcp.tool()`（FastMCP） | 只支持带括号，返回原函数 | 原函数**保留**，同时登记进服务器 |

三条最容易混的，单独记：

| 问题 | 答案 |
|------|------|
| 装饰之后 `my_func` 这个名字还指向原来那个函数吗？ | 不一定——看装饰器返回啥。LangChain 说不是，FastMCP 说是 |
| 那个原函数死了吗？ | 没死。它活在装饰器的返回值里（LangChain 是 `.func`），只是暂时没名字指着它 |
| 那 `.invoke({"a":1})` 里的字典是干嘛的？ | 拆成关键字参数转交给原函数。用字典是因为模型回传的参数本来就是 JSON |

**一句话记忆：`@` 就是把"包装"写到函数头顶；括号表示先执行一次拿到装饰器；装饰器返回什么，原函数那个名字就指向什么。**
