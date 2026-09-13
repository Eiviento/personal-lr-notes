# Python 装饰器：`@` 到底是什么（读懂 `@tool` / `@mcp.tool()`）

> 2026-09-13 实操跑通（`scripts/extra_python_decorator.py` 四个实验，附真实运行输出）。覆盖：一句话理解 / `@` 是语法糖 / 带括号与不带括号 / 注册型 vs 替换型 / 逐行点名项目里那段代码 / 三个坑 / 速记表。
>
> 学习动线：`scripts/phase4_2_tool_calling.py` 的 `@tool`、`scripts/demo_mcp_server.py` 的 `@mcp.tool()`——一个不带括号、一个带括号。这不是魔法，是 Python 同一个语法：**装饰器**。这课把地基补上。

## 一、一句话理解

**装饰器 = 一个"接收函数、返回函数"的函数。`@` 是把「定义完函数后紧接着做的包装动作」写到函数头顶的语法糖。**

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

## 二、`@` 是语法糖：拆开看就三步

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

## 三、带括号 vs 不带括号：装饰器工厂

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

它**必须被调用一次**才能拿到装饰器。而 LangChain 的 `@tool` 两种写法都支持（实验 3 验证：`@tool` 和 `@tool("named_add")` 都跑通）——因为它的第一个参数是 `name_or_callable`，收到函数就当裸用、收到字符串就当工厂。

> **两个库设计不同，不是 Python 语法不同。** 记不住就记住这句：**看到括号，就说明先执行了一次函数调用。**

## 四、装饰器返回什么，决定原函数还在不在

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

实验 3 实测：

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

## 五、逐行点名：项目里 `@tool` 那段代码

```python
@tool                                    # ← ① 装饰器：把下面的函数变成 StructuredTool
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    #    ② 类型注解 ──→ 变成 JSON Schema 的参数表，模型的"怎么填"
    """校验协议字段的类型与字节数是否匹配。参数：..."""
    #   ③ docstring ──→ 变成 description，模型的"什么时候用"
    ...
```

实验 4 用真实 FastMCP 跑了一遍同一个函数，把"注解+docstring 怎么变成说明书"直接打了出来：

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

## 六、实测输出（`scripts/extra_python_decorator.py`）

零 LLM 成本、不联网，四个实验一次跑完：

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

实验 3｜两种哲学：注册型（原函数留着）vs 替换型（原函数被换掉）
add_bare  现在是什么类型: StructuredTool | 名字: add_bare
当普通函数调 → TypeError: 'StructuredTool' object is not callable
正确调法 → 3

实验 4｜回到项目：真实 FastMCP 把 docstring + 类型注解变成 JSON Schema
装饰一下之后，validate_field_type 还是普通函数吗？ function
  | 直接调 → seq: uint8 标准 1 字节，声明 1 → 合法
但服务器内部已经悄悄记下了它。问服务器要工具清单： 名字: validate_field_type
```

完整输出存于 `outputs/extra_python_decorator.log`。

## 七、三个坑

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

## 八、速记表

| 你看到 | 它是什么 | 拆开等价于 |
|--------|---------|-----------|
| `@deco` | 裸装饰器 | `f = deco(f)` |
| `@deco()` | 装饰器工厂 | `f = deco()(f)` |
| `@deco("参数")` | 装饰器工厂（带配置） | `f = deco("参数")(f)` |
| `@a` `@b` 叠着 | 顺序从下往上 | `f = a(b(f))` |
| `@tool`（LangChain） | 双形态，返回 `StructuredTool` | 原函数被**替换**，用 `.invoke()` |
| `@mcp.tool()`（FastMCP） | 只支持带括号，返回原函数 | 原函数**保留**，同时登记进服务器 |

**一句话记忆：`@` 就是把"包装"写到函数头顶；括号表示先执行一次拿到装饰器；装饰器返回什么，原函数就变成什么。**
