"""
Python 基础补课：lambda 和 dunder（__name__ 这类名字）
==========================================================
起因：demo_tool_after_decorator.py 里出现了两种没解释过的写法——
        probe("① 直接调用", lambda: f(1, 2))     # ← lambda 是什么？
        f.__name__                                # ← __name__ 是什么？

上半场 lambda：
  A1  lambda 就是个函数，和 def 等价（除了没有名字）
  A2  **为什么 demo 里非用 lambda 不可**——不用它，try 就白写了（本课重点）
  A3  lambda 最常见的真实用处：sorted/max 的 key
  A4  项目里的 lambda：RunnableLambda
  A5  lambda 的限制——为什么工具函数绝对不能用它

下半场 dunder：
  B1  __name__ 只是函数身上一个普通属性（存的是字符串）
  B2  同一个 __name__，模块身上也有一份 → if __name__ == "__main__" 的真相
  B3  四种下划线写法对比
  B4  dunder 是给解释器留的钩子——顺带解答上节课那个 not callable

用法（在项目根目录下）：
  PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe scripts/extra_python_lambda_dunder.py
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 便于 import 兄弟模块


def section(text: str) -> None:
    print(f"\n{'=' * 66}\n{text}\n{'=' * 66}")


# #################################################################
# 上半场：lambda
# #################################################################
section("A1｜lambda 就是个函数，和 def 等价")


def square_def(x):
    """平方（def 版）"""
    return x * x


square_lam = lambda x: x * x  # noqa: E731  平方（lambda 版）

print(f"  def 版：type={type(square_def).__name__}  square_def(5)={square_def(5)}"
      f"  __name__={square_def.__name__!r}")
print(f"  lambda版：type={type(square_lam).__name__}  square_lam(5)={square_lam(5)}"
      f"  __name__={square_lam.__name__!r}")
print("""
读完这行输出，请把 lambda 从『神秘魔法』降级为『一个简写』：

    lambda x: x * x        等价于        def 无名(x):
                                            return x * x

差别只有两点：
  1. lambda 是**表达式**（能写在参数位置、能当值赋值），def 是**语句**
  2. lambda 没有名字，所以 __name__ 只能是 '<lambda>'
""")


section("A2｜为什么 demo 里非用 lambda 不可——本课重点")

print("先看两个 probe 的区别（只差一个字）：")


def probe_value(label, value):
    """收『值』：参数传进来之前就已经算好了"""
    try:
        print(f"  ✅ {label} → {value!r}")
    except Exception as e:
        print(f"  ❌ {label} → {type(e).__name__}: {e}")


def probe_action(label, thunk):
    """收『动作』：参数是个还没执行的函数，由我决定何时执行"""
    try:
        print(f"  ✅ {label} → {thunk()!r}")
    except Exception as e:
        print(f"  ❌ {label} → {type(e).__name__}: {e}")


def broken(a, b):
    """一个必炸的函数"""
    raise ValueError("我是故意的")


print("\n── 错误示范：写成 probe_value('调用', broken(1, 2)) ──")
try:
    probe_value("调用 broken(1, 2)", broken(1, 2))
except ValueError as e:
    print(f"  💥 崩在 probe 外面：ValueError: {e}")
    print("     ↑ probe_value 里那个 try 完全没帮上忙")
print("""
为什么？因为执行顺序是：

    第 1 步：算出 broken(1, 2)   ← 现在就炸了，Python 走不到第 2 步
    第 2 步：把结果传给 probe_value
    第 3 步：probe_value 开始执行（含它的 try）  ← 永远到不了这里

**异常发生在『准备参数』的阶段，而 try 在函数体里面。** 护不住。
""")

print("── 正确示范：把调用包进 lambda，推迟到 probe 内部再执行 ──")
probe_action("调用 broken(1, 2)", lambda: broken(1, 2))
print("""
现在执行顺序变成：

    第 1 步：造一个『还没执行的调用』——lambda 函数对象（不报错，它只是个值）
    第 2 步：把这个值传给 probe_action
    第 3 步：probe_action 的 try 开始生效
    第 4 步：try 内部执行 thunk() → 这才真的去调 broken → 异常被接住 ✅

这个套路叫**延迟执行**（英文 thunk / lazy evaluation）：
用 lambda 把『调用动作』打包成一个**值**，先传着走，等真正需要时才执行。

demo_tool_after_decorator.py 里 6 个 probe 全都这么写，就是为了让
①~④ 那几个必炸的调用能在 try 里被接住、优雅地打出 ❌ 而不是让脚本崩掉。

同一个套路你在别处也见过：

    sorted(rows, key=lambda r: r[1])     # ← 不是现在排序，是把"取哪个值"先存着
    btn.on_click(lambda: print("点了"))   # ← 不是现在就打印，是把动作存着等点击
""")


section("A3｜lambda 最常见的真实用处：排序的 key")

rows = [("banana", 3), ("apple", 10), ("cherry", 1)]
print(f"  原始：{rows}")
print(f"  按名字排序 sorted(rows, key=lambda r: r[0]) → {sorted(rows, key=lambda r: r[0])}")
print(f"  按数量排序 sorted(rows, key=lambda r: r[1]) → {sorted(rows, key=lambda r: r[1])}")
print(f"  按数量倒序 sorted(..., reverse=True)      → {sorted(rows, key=lambda r: r[1], reverse=True)}")
print("""
  key= 收的就是一个函数：『我给你一行数据，你告诉我该按哪个值排』。
  这个函数只用一次、还要写在调用现场，起个名字反而碍事 → lambda 正合适。

  如果取的不是"第几列"而是"算一下"（比如按字符串长度），lambda 更省事：
""")
print(f"  按名字长度 sorted(rows, key=lambda r: len(r[0])) →"
      f" {sorted(rows, key=lambda r: len(r[0]))}")


section("A4｜项目里的 lambda：RunnableLambda")

print("""  scripts/phase4_1_rag.py 第 209 行：

      RunnablePassthrough.assign(retrieved=RunnableLambda(lambda s: retrieve(s["requirement"])))

  scripts/demo_api_reference.py 第 103 行：

      chain = prompt | RunnableLambda(lambda m: m.to_messages()[0].content) | ...

  拆开看：LCEL 管道（a | b）要求每一节都是『可运行对象』（Runnable）。
  可你手头常常只有一行普通代码要插进去——拿 RunnableLambda 包一下，它就成了
  一个合格的管道零件。里面那坨逻辑用 lambda 写最省事，因为：

      - 只有一行表达式（取字段、调个函数）
      - 只用这么一次，不值得单独 def
      - 就写在使用现场，读代码不用来回跳

  换句话说：lambda 的定位是『**胶水**』——把一小段逻辑塞进某个需要函数的接口里。
""")


section("A5｜lambda 的限制——为什么工具函数绝对不能用它")

print('''  lambda 的函数体只能写**一个表达式**。下面这些统统不行：

      lambda x: print(x); return x        # ❌ 不能有分号多语句
      lambda x: if x > 0: x               # ❌ 不能有 if 语句（但可以用 x if x > 0 else -x）
      lambda x: (y = 1, x + y)            # ❌ 不能赋值
      lambda x: "文档字符串"               # ❌ 没有 docstring
      lambda x: x + 1                     # ⚠️ 没有类型注解
''')

from langchain_core.tools import tool  # noqa: E402


@tool
def named_tool(a: int, b: int) -> int:
    """两数相加。"""
    return a + b


print("  ① 用 def + docstring 定义工具（正确写法）：")
print(f"     name        = {named_tool.name!r}")
print(f"     description = {named_tool.description!r}")

print("\n  ② 用 lambda 定义工具（不给 description）：")
try:
    tool(lambda a, b: a + b)
except ValueError as e:
    print(f"     ❌ {type(e).__name__}: {e}")

print("\n  ③ 硬塞一个 description 绕过检查：")
anon = tool(lambda a, b: a + b, description="两数相加。")
print(f"     能建出来，但 name = {anon.name!r}   ← 名字成了字面量 '<lambda>'")

print("\n  ④ 用 def 但忘了写 docstring：")
try:
    def no_docstring(a: int, b: int) -> int:
        return a + b

    tool(no_docstring)
except ValueError as e:
    print(f"     ❌ {type(e).__name__}: {e}")

print("""
  ★ 注意 ④：报错和 lambda 一模一样。所以真正的要求不是『必须 def』，
    而是**必须有一份说明书**——docstring 或者显式传 description，二选一。

    但即使绕过去（③），lambda 还有个绕不开的硬伤：**name 固定是 '<lambda>'**。
    上一课讲过，MCP 和 LangChain 都靠 __name__ / __doc__ 给模型生成说明书：

        - 挂两个 lambda 工具 → 名字全叫 '<lambda>'，一个服务器里直接撞名
        - 想按名字分发（FUNC_MAP[name]）→ 全是同一个键，彻底没法用

  结论：**工具函数用 def 写、老老实实加 docstring**，哪怕只有一行。
  lambda 是『用完就扔的胶水』，不能拿来当对外暴露的接口。
""")


# #################################################################
# 下半场：dunder
# #################################################################
section("B1｜__name__ 只是函数身上一个普通属性")


def hello():
    """打个招呼"""
    return "hi"


print(f"  hello.__name__  → {hello.__name__!r}   类型是 {type(hello.__name__).__name__}")
print("\n  函数对象身上挂着一堆这种『双下划线开头结尾』的属性：\n")
for attr in ("__name__", "__doc__", "__module__", "__qualname__", "__dict__"):
    print(f"      {attr:<14} = {getattr(hello, attr, None)!r}")
print("""
  关键认知：**__name__ 不是魔法，它就是个普通的属性，值是个字符串。**
  跟 obj.color = "red" 里的 color 是同一回事，只不过这个名字是 Python
  解释器在创建函数时自动帮你填好的。

  所以 f.__name__ 读作：『去 f 这个盒子上，找那张写着名字的标签』。
""")


section("B2｜同一个 __name__，模块身上也有一份")

import json  # noqa: E402

import phase4_2_tool_calling  # noqa: E402

print(f"  本脚本自己的 __name__  → {__name__!r}")
print(f"  导入的 json 模块       → {json.__name__!r}")
print(f"  项目里的 phase4_2      → {phase4_2_tool_calling.__name__!r}")
print("""
  看出规律了吗：

      - 直接运行的脚本         → __name__ 是 '__main__'
      - 被 import 进来的模块    → __name__ 是它的模块名

  这就是每个脚本末尾那句的真相：

      if __name__ == "__main__":
          main()

  翻译成人话：**『如果这个文件是被我直接跑的，就跑 main()；如果它是被别人
  import 进来的，就什么都别做，只提供里面的函数。』**

  为什么需要它？因为 import 一个模块会执行它的顶层代码。如果没有这道闸，
  你 `from phase4_2_tool_calling import FIXED_SIZE` 的时候，整个演示脚本
  就会自己跑起来、开始调大模型——那显然不是你想要的。

  注意这是**同一个 __name__ 机制的两个用途**：
      - 函数上的 __name__  →  这个函数叫什么
      - 模块上的 __name__  →  这个模块是怎么被加载的
""")


section("B3｜四种下划线写法，别搞混")

print("""      name        普通名字，公开可用
      _name       单下划线开头：『内部使用，别碰』的信号（纯约定，不强制）
      __name      双下划线开头（最多一个尾下划线）：会触发名字修饰，父类私有
      __name__    双下划线开头**且**结尾：dunder，由解释器/框架特殊对待

  一句话记忆：**开头结尾都是双下划线的，是 Python 自己留的坑位，别乱起这种名。**
  你自己定义 __name__、__doc__ 这种东西，就是在跟解释器抢方向盘。
""")


section("B4｜dunder 是给解释器留的钩子（顺带解答上节课那个 not callable）")

print(f"  len('abc')  其实是在调   'abc'.__len__()    → {len('abc')} / {'abc'.__len__()}")
print(f"  [1,2,3][0]  其实是在调   [1,2,3].__getitem__(0) → {[1,2,3][0]}")
print(f"  'a'+'b'     其实是在调   'a'.__add__('b')   → {'a'+'b'}")
print("""
  你在写代码时用的是**语法**（len()、[]、+），Python 在背后翻译成**dunder 方法调用**。
  这就是为什么自定义类只要实现了 __len__，就能被 len() 用：

      class MyBox:
          def __len__(self): return 42
      len(MyBox())     # → 42

  ★ 现在回看上节课那个报错：

      TypeError: 'StructuredTool' object is not callable

   『可调用』这件事本身也是一个 dunder 钩子——**__call__**：

      f(1, 2)   其实是在调   f.__call__(1, 2)

   Python 检查『这个对象能不能加括号调用』，看的就是它有没有 __call__。
""")

has_plain = hasattr(hello, "__call__")
has_tool = hasattr(named_tool, "__call__")
print(f"  普通函数 hello       有 __call__ 吗？ {has_plain}   → 所以 hello() 能用")
print(f"  工具对象 named_tool  有 __call__ 吗？ {has_tool}   → 所以 named_tool() 报 not callable")
print("""
  一行 `hasattr(obj, '__call__')` 就把上节课那个 TypeError 解释干净了。

  Python 内置函数 callable(obj) 干的就是这件事的封装：
""")
print(f"      callable(hello)       → {callable(hello)}")
print(f"      callable(named_tool)  → {callable(named_tool)}")
print("""
  所以再看到 'xxx object is not callable'，第一反应应该是：
  **去查这个对象有没有 __call__**——而不是怀疑函数名写错了。
""")

print("=" * 66)
print("一句话总结")
print("=" * 66)
print("""
  lambda  = 没名字的简写函数（表达式形态）。主要用途是『胶水』：
            塞进 sorted(key=)、RunnableLambda(...) 这类需要函数的接口；
            或者用『延迟执行』把一次调用包成值传着走（try 才管得住）。
            限制：只能一个表达式、没名字、没 docstring → 工具函数绝不能用。

  __name__ = 函数/模块身上的一个**普通属性**，值是个字符串。
            函数上：这个函数叫什么（工具说明书的来源之一）。
            模块上：怎么被加载的（'__main__' 还是模块名）→ if __name__ == "__main__"。
            这类双下划线开头结尾的名字统称 dunder，是 Python 给解释器留的钩子
            （__call__ / __len__ / __getitem__ …），别自己乱起。
""")
