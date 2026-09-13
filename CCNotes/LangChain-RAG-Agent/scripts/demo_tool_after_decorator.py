"""
加 @tool 之后，原来的调用方式还能用吗？—— 最小对照实验
==========================================================
结论先给：**不能。** @tool 把函数名字换成了工具对象，原来那些「把函数当函数调」
的写法会集体报错。本脚本拿**同一个函数的两份拷贝**，用一样的 6 种调用方式
各试一遍，让你亲眼看到哪几种死了、哪几种活着。

用法（在项目根目录下）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/demo_tool_after_decorator.py

对照阅读：lessons/extra_python_decorator.md 第三节「名字是标签」
"""

import sys
import warnings

warnings.filterwarnings("ignore")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.tools import tool


# ══════════════════════════════════════════════════════════════════
# 对照组 A：普通函数（不加 @tool）
# ══════════════════════════════════════════════════════════════════
def add_plain(a: int, b: int) -> int:
    """两数相加。"""
    return a + b


# ══════════════════════════════════════════════════════════════════
# 实验组 B：同一个函数，加一个 @tool
# ══════════════════════════════════════════════════════════════════
@tool
def add_tooled(a: int, b: int) -> int:
    """两数相加。"""
    return a + b


# ── 6 种调用方式，对两组各跑一遍 ────────────────────────────────
def probe(label: str, thunk) -> None:
    """试一次调用：成功打 ✅，失败打 ❌ 并显示异常类型"""
    try:
        print(f"  ✅ {label}\n       → {thunk()!r}")
    except Exception as e:
        print(f"  ❌ {label}\n       → {type(e).__name__}: {e}")


def apply(fn, a, b):
    """把函数当参数传进来调用——很常见的一种写法"""
    return fn(a, b)


def run_all(f, tag: str) -> None:
    print(f"\n{'─' * 62}\n{tag}\n{'─' * 62}")
    print(f"  f 的类型 = {type(f).__name__} | callable(f) = {callable(f)}\n")
    probe("① 直接调用        f(1, 2)", lambda: f(1, 2))
    probe("② 关键字调用      f(a=1, b=2)", lambda: f(a=1, b=2))
    probe('③ 放进字典再调    d["add"](1, 2)      ← 项目里 FUNC_MAP 的用法',
          lambda: {"add": f}["add"](1, 2))
    probe("④ 当参数传给别的函数  apply(f, 1, 2)", lambda: apply(f, 1, 2))
    probe("⑤ 看身份          f.__name__", lambda: f.__name__)
    probe('⑥ 工具的标准调法  f.invoke({"a": 1, "b": 2})', lambda: f.invoke({"a": 1, "b": 2}))


print("=" * 62)
print("同一个函数的两份拷贝，6 种调用方式各试一遍")
print("=" * 62)

run_all(add_plain, "【对照组 A】普通函数 def add_plain(...)，没有 @tool")
run_all(add_tooled, "【实验组 B】同一个函数，头上加了 @tool")

# ── 还想拿回原来那个函数？它躲在 .func 里 ────────────────────
print(f"\n{'─' * 62}\n补充：原函数没死，躲在 .func 里\n{'─' * 62}")
print(f"  add_tooled.func        → {add_tooled.func}")
print(f"  add_tooled.func(1, 2)  → {add_tooled.func(1, 2)}   ← 掀开盖子，原地满血")
print(f"  它是上面 add_plain 那个对象吗？ {add_tooled.func is add_plain}"
      f"   ← False 很正常：本脚本 def 了两次，是两份独立拷贝")

# ── 名字和文档去哪儿了 ───────────────────────────────────────
print(f"\n{'─' * 62}\n补充：名字和 docstring 也换了地方\n{'─' * 62}")
print(f"  add_plain.__name__      → {add_plain.__name__!r}")
print(f"  add_tooled.__name__     → {getattr(add_tooled, '__name__', '（没有这个属性了）')!r}")
print(f"  add_tooled.name         → {add_tooled.name!r}   ← 改用 .name 了")
print(f"  add_tooled.description  → {add_tooled.description!r}   ← docstring 搬到了这里")

print(f"""
{'=' * 62}
结论
{'=' * 62}
  加了 @tool 之后，原来 4 种『把函数当函数调』的写法全部失效（①②③④），
  连 __name__ 都没了。只有 ⑥ f.invoke({{...}}) 这一种调法活着。

  这就是为什么项目 phase4_2_tool_calling.py 第 73 行必须写：

      result = str(FUNC_MAP[name].invoke(args))

  而不是想象中的：

      result = str(FUNC_MAP[name](**args))     ← 这行会 TypeError

  ③ 是最容易踩的一个坑：字典本身没问题，值（工具对象）被调用了才炸。
  而模型的 tool_calls 回传的参数本来就是 JSON 字典，.invoke() 正好对上。
""")
