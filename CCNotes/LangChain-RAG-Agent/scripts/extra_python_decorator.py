"""
Python 装饰器（decorator）：@ 到底是什么
============================================
场景：项目里到处都是 @ —— phase4_2 的 @tool、demo_mcp_server 的
      @mcp.tool()、@mcp.resource("protocol-tools://...")。
      有的带括号有的不带，这不是魔法，是 Python 同一个语法：装饰器。

实验 1  @ 只是语法糖：手写等价形式，证明 @deco 就等于 f = deco(f)
实验 2  两种形态：裸装饰器 @deco vs 装饰器工厂 @deco()
实验 3  两种哲学：注册型（原函数留着）vs 替换型（原函数被换掉）——真实库对照
实验 4  回到项目：真实 FastMCP + 项目的 validate_field_type，
        看 docstring 和类型注解怎么变成模型的"参数说明书"

全程零 LLM 成本、不联网。

用法：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/extra_python_decorator.py
"""

import asyncio
import functools
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # 屏蔽三方库版本告警，保持输出干净
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 复用兄弟模块的死规则表


def section(n: int, text: str) -> None:
    """打印实验标题（纯排版，和装饰器无关）"""
    print(f"\n{'=' * 66}\n实验 {n}｜{text}\n{'=' * 66}")


# ══════════════════════════════════════════════════════════════════
section(1, "@ 只是语法糖：@deco 等价于 f = deco(f)")
# ══════════════════════════════════════════════════════════════════


def shout(func):
    """一个最朴素的装饰器：把一个无参函数的结果套上【】"""
    def wrapper():                 # ← 内层函数：将来真正被调用的那个
        return f"【{func()}】"      # ← func 被"关"在里面（闭包）
    return wrapper                 # ← 返回内层函数，不是原函数


# 写法 A：不用 @，手动包
def hello_a():
    return "你好"


hello_a = shout(hello_a)           # ← 这一行就是 @shout 干的事

# 写法 B：用 @，一行搞定
@shout
def hello_b():
    return "你好"


def hello_c():
    return "你好"


print("写法A（手动包）:", hello_a())
print("写法B（用 @ ）:", hello_b())
print("两者跟『原样包一遍』产出一样吗？", hello_a() == hello_b() == shout(hello_c)())

print("""
关键认知：@ 不改变执行顺序，它只是把『函数定义完』之后紧接着做的那次赋值
写到了函数头顶。

    @shout
    def hello(): ...       等价于
                            def hello(): ...
                            hello = shout(hello)

理解这一步，后面所有 @ 都能自己拆开看。
""")

# ── 坑：不加 functools.wraps，函数的名字和文档会被 wrapper 顶掉 ──


@shout
def lonely():
    """我是一个有文档字符串的函数"""


def shout_with_wraps(func):
    @functools.wraps(func)         # ← 把原函数的 __name__/__doc__ 复制到 wrapper 上
    def wrapper():
        return f"【{func()}】"
    return wrapper


@shout_with_wraps
def named():
    """我是一个有文档字符串的函数"""


print("不用 functools.wraps →  名字:", lonely.__name__, "| 文档:", lonely.__doc__)
print("用了 functools.wraps →  名字:", named.__name__, "| 文档:", named.__doc__)
print("（MCP/LangChain 要靠 __name__ 和 __doc__ 生成工具说明书，所以这里必须加）")


# ══════════════════════════════════════════════════════════════════
section(2, "两种形态：@deco（裸）vs @deco()（带括号 = 装饰器工厂）")
# ══════════════════════════════════════════════════════════════════


def tag(func):
    """形态一：裸装饰器。它自己就是装饰器，直接收函数"""
    def wrapper():
        return f"<{func()}>"
    return wrapper


def tag_with(symbol: str):
    """形态二：装饰器工厂。它先收『配置参数』，再返回一个装饰器"""
    def decorator(func):           # ← 这才是真正的装饰器
        def wrapper():
            return f"{symbol}{func()}{symbol}"
        return wrapper
    return decorator


@tag
def bare():
    return "裸用"


@tag_with("<<")                    # ← 注意括号：先调 tag_with("<<") 拿到装饰器
def with_args():
    return "带括号"


print("@tag          →", bare())
print('@tag_with("<<")→', with_args())

print("""
拆开看 @tag_with("<<") 的两步：

    第一步：tag_with("<<")   → 执行，返回 decorator 这个函数   ← 括号在这里用掉
    第二步：decorator(函数)   → decorator 再去包函数

所以带括号的 @ 表示：『先跟工厂打个招呼，告诉它我要什么配置』。
项目里三种写法对照：

    @tool                              # 裸用：不要配置
    @mcp.tool()                        # 带括号：要配置，但这次一个都不传（用默认值）
    @mcp.resource("protocol-tools://…") # 带括号 + 参数：资源地址是必填配置

为什么 @mcp.tool() 明明没参数也非得写括号？因为 FastMCP.tool() 被设计成
**只支持带括号**的形态——它的函数签名长这样（实验 4 会打印）：

    def tool(self, name=None, title=None, ...) -> Callable[[AnyFunction], AnyFunction]
                                                     └─ 返回值是一个装饰器 ─┘

它收到调用后才返回装饰器，所以括号不能省。而 LangChain 的 @tool 两种都行
（实验 3 验证），这是两个库的设计选择不同，不是 Python 语法不同。
""")


# ══════════════════════════════════════════════════════════════════
section(3, "两种哲学：注册型（原函数留着）vs 替换型（原函数被换掉）")
# ══════════════════════════════════════════════════════════════════

# ── 哲学 A：注册型 ──────────────────────────────────────────────
REGISTRY = []                      # 假装这是 MCP 服务器内部的工具清单


def register(func):
    """注册型装饰器：把函数登记进清单，然后把**原函数原样还回去**"""
    REGISTRY.append(func.__name__)
    return func


@register
def my_tool():
    return "我还能当普通函数用"


print("── 哲学 A：注册型 ──")
print("注册表里现在有:", REGISTRY)
print("函数还是函数吗？", type(my_tool).__name__, "| 直接调用 →", my_tool())

# ── 哲学 B：替换型 ──────────────────────────────────────────────
print("\n── 哲学 B：替换型（LangChain 的 @tool 就是这么干的）──")

from langchain_core.tools import tool  # noqa: E402  （放这里是为了让实验 3 的对比紧挨着）


@tool
def add_bare(a: int, b: int) -> int:
    """两数相加（裸用 @tool）。"""
    return a + b


@tool("named_add")
def add_named(a: int, b: int) -> int:
    """两数相加（@tool("名字") 工厂用法）。"""
    return a + b


print("add_bare  现在是什么类型:", type(add_bare).__name__, "| 名字:", add_bare.name)
print("add_named 现在是什么类型:", type(add_named).__name__, "| 名字:", add_named.name)
try:
    add_bare(1, 2)
except TypeError as e:
    print("当普通函数调 →", type(e).__name__ + ":", e)
print("正确调法 →", add_bare.invoke({"a": 1, "b": 2}))

print("""
对照表（这一格是新手最容易懵的地方）：

| | 注册型（FastMCP @mcp.tool()） | 替换型（LangChain @tool） |
|---|---|---|
| 装饰器返回什么 | 原函数本身 | 一个 StructuredTool 对象 |
| 装饰后还能 my_func(1,2) 吗 | 能 | 不能 → TypeError |
| 怎么调 | my_func(1, 2) | my_func.invoke({"a":1,"b":2}) |
| 谁去给模型看 | 服务器从注册表里翻出来 | 这个对象自己带着 schema |

为什么 FastMCP 选注册型：MCP 是"插头标准"，服务器只需要在启动时把函数
登记好、等客户端来调，原函数在内部还得被正常执行，留着最省事。
为什么 LangChain 选替换型：@tool 的结果要直接塞进 bind_tools([...])，
它必须是一个自带 name/description/args_schema 的 Runnable 对象。

共同点（最重要）：**两者都靠函数头上的类型注解和 docstring 生成 JSON Schema。**
所以写工具函数时，注解和 docstring 不是"注释"，是给模型的说明书正文。
""")


# ══════════════════════════════════════════════════════════════════
section(4, "回到项目：真实 FastMCP 把 docstring + 类型注解变成 JSON Schema")
# ══════════════════════════════════════════════════════════════════

from mcp.server.fastmcp import FastMCP  # noqa: E402

from phase4_2_tool_calling import FIXED_SIZE  # noqa: E402  项目里的死规则表

mcp = FastMCP("protocol-tools")


@mcp.tool()                        # ← demo_mcp_server.py 里就是这一行
def validate_field_type(field_name: str, field_type: str, length: int) -> str:
    """校验协议字段的类型与字节数是否匹配。
    参数：field_name 字段名；field_type 数据类型（uint8/int16/float32/string 等）；length 声明的字节数。"""
    if field_type == "string":
        return f"{field_name}: string 是变长类型，声明 {length} 字节 → 合法（约定为最大长度）"
    expected = FIXED_SIZE.get(field_type)
    if expected is None:
        return f"{field_name}: 未知类型 {field_type} → 不合法"
    if expected == length:
        return f"{field_name}: {field_type} 标准 {expected} 字节，声明 {length} → 合法"
    return f"{field_name}: {field_type} 应为 {expected} 字节，实际声明 {length} → 不合法"


print("装饰一下之后，validate_field_type 还是普通函数吗？",
      type(validate_field_type).__name__,
      "| 直接调 →", validate_field_type("seq", "uint8", 1))

print("\n但服务器内部已经悄悄记下了它。问服务器要工具清单：")
for t in asyncio.run(mcp.list_tools()):
    print(f"  名字: {t.name}")
    print(f"  描述: {t.description}")
    print(f"  参数说明书 (JSON Schema):")
    print("   ", t.inputSchema)

print("""
看懂这张 inputSchema 的来源：

    你写的代码                               模型看到的东西
    ─────────────────────────────────        ──────────────────────────────
    def validate_field_type(              →  "name": "validate_field_type"
    field_name: str,                      →  "field_name": {"type": "string"}
    field_type: str,                      →  "field_type": {"type": "string"}
    length: int)                          →  "length": {"type": "integer"}
    \"\"\"校验协议字段的类型与字节数…\"\"\"      →  "description": "校验协议字段的…"

MCP 服务器（和 LangChain 的 @tool）就是用 inspect 模块读这两样东西，
自动生成给模型看的说明书——所以模型才知道有这么一个工具、该怎么填参数。

这也解释了一条实用规则：**工具函数的类型注解必须写全、docstring 必须说清
"什么时候用"**。注解写漏一个，模型就少看到一行参数说明，调用就会出错。
""")

print("=" * 66)
print("一句话总结")
print("=" * 66)
print("""
1. @ 是语法糖：@deco 上面的函数 = deco(原函数) 的返回值。
2. 带括号 = 装饰器工厂：先执行 deco(配置)，拿到装饰器，再去包函数。
3. 装饰器返回什么，决定了原函数还在不在：
   FastMCP 返回原函数（注册型）→ 还能当函数调；
   LangChain 返回 StructuredTool（替换型）→ 只能用 .invoke()。
4. 注解 + docstring 是给模型的说明书，不是给人看的注释。
""")
