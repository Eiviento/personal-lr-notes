# Python 基础补课：`lambda` 和 dunder（`__name__` 这类名字）

> 2026-09-13 实操跑通（`scripts/extra_python_lambda_dunder.py`，八个实验，附真实运行输出）。覆盖：lambda 是什么 / **为什么非用不可（延迟执行）** / 排序 key / 项目里的 RunnableLambda / 为什么工具函数不能用 lambda；`__name__` 是属性 / `if __name__ == "__main__"` 的真相 / 四种下划线 / dunder 钩子。
>
> 学习动线：`scripts/demo_tool_after_decorator.py` 里出现了两种没解释过的写法——`probe("①", lambda: f(1, 2))` 和 `f.__name__`。这课把它们各自补上，顺带把上节课那个 `not callable` 报错也解释到底。

---

# 上半场：lambda

## 一、一句话理解

**`lambda` 就是"没名字的函数"，一个简写而已。** 它不是新概念，`def` 能干的它基本都能干（除了写多行），唯一区别是它以**表达式**的形式出现——能直接写在参数位置。

```python
square_lam = lambda x: x * x
# 等价于
def square_lam(x):
    return x * x
```

实测（实验 A1）：

```
  def 版：type=function  square_def(5)=25  __name__='square_def'
  lambda版：type=function  square_lam(5)=25  __name__='<lambda>'
```

**`type` 都是 `function`**——从 Python 眼里看，这就是同一种东西。差别只在 `__name__`：一个记着真名字，一个只能是 `'<lambda>'`。

> **为什么要有 lambda？** 有些场景你需要的函数**只用一次、就写在使用现场**——比如告诉 `sorted()` "按第几列排"。为它专门 `def` 一个还要起名字，反而碍事。
>
> **不做会怎样？** 那就多写三行 `def`。不是不行，就是啰嗦。

## 二、为什么那个 demo 里非用 lambda 不可（本课重点）

这是 `demo_tool_after_decorator.py` 里 6 个 `probe(...)` 全用 `lambda` 的原因。**不用它，`try` 就白写了。**

先看两个只差一个字的函数：

```python
def probe_value(label, value):      # 收『值』：参数传进来之前就已经算好了
    try:
        print(f"✅ {label} → {value!r}")
    except Exception as e:
        print(f"❌ {label} → {e}")

def probe_action(label, thunk):     # 收『动作』：参数是个还没执行的函数，由我决定何时执行
    try:
        print(f"✅ {label} → {thunk()!r}")
    except Exception as e:
        print(f"❌ {label} → {e}")
```

配一个必炸的函数 `broken()`，两种写法实测对比：

```
── 错误示范：写成 probe_value('调用', broken(1, 2)) ──
  💥 崩在 probe 外面：ValueError: 我是故意的
     ↑ probe_value 里那个 try 完全没帮上忙

── 正确示范：把调用包进 lambda，推迟到 probe 内部再执行 ──
  ❌ 调用 broken(1, 2) → ValueError: 我是故意的
```

**同样是"调用一个必炸的函数"，一个把整个脚本搞崩，一个被优雅接住。** 区别在执行顺序：

| 步骤 | `probe_value(label, broken(1,2))` | `probe_action(label, lambda: broken(1,2))` |
|------|----------------------------------|-------------------------------------------|
| 第 1 步 | **算出** `broken(1, 2)` ← 现在就炸 | 造一个"还没执行的调用"（lambda 对象，只是个值，不炸） |
| 第 2 步 | 把结果传给 `probe_value` | 把这个值传给 `probe_action` |
| 第 3 步 | `probe_value` 开始执行（含它的 `try`）← 永远到不了这里 | `try` 开始生效 |
| 第 4 步 | — | `try` 内部执行 `thunk()` → 这才真去调 → **异常被接住 ✅** |

**根本原因：异常发生在「准备参数」的阶段，而 `try` 在函数体里面。** 护不住。

> 这个套路叫**延迟执行**（英文 thunk / lazy evaluation）：**用 lambda 把"调用动作"打包成一个值**，先传着走，等真正需要时才执行。
>
> 同一个套路你在别处也见过：
>
> ```python
> sorted(rows, key=lambda r: r[1])     # 不是现在排序，是把"取哪个值"先存着
> btn.on_click(lambda: print("点了"))   # 不是现在就打印，是把动作存着等点击
> ```

## 三、lambda 最常见的用处：排序的 key

这个函数**只用一次、还要写在调用现场、起名字反而碍事**——`lambda` 最标准的用武之地。

```
  原始：[('banana', 3), ('apple', 10), ('cherry', 1)]
  按名字排序 sorted(rows, key=lambda r: r[0]) → [('apple', 10), ('banana', 3), ('cherry', 1)]
  按数量排序 sorted(rows, key=lambda r: r[1]) → [('cherry', 1), ('banana', 3), ('apple', 10)]
  按数量倒序 sorted(..., reverse=True)      → [('apple', 10), ('banana', 3), ('cherry', 1)]
  按名字长度 sorted(rows, key=lambda r: len(r[0])) → [('apple', 10), ('banana', 3), ('cherry', 1)]
```

`key=` 收的就是一个函数：**"我给你一行数据，你告诉我该按哪个值排。"** 取字段、算个长度、拼两个字段，都是一行表达式——lambda 的表达力刚好够。

## 四、项目里的 lambda：`RunnableLambda`

真实用例（本项目两处）：

```python
# scripts/phase4_1_rag.py 第 209 行
RunnablePassthrough.assign(retrieved=RunnableLambda(lambda s: retrieve(s["requirement"])))

# scripts/demo_api_reference.py 第 103 行
chain = prompt | RunnableLambda(lambda m: m.to_messages()[0].content) | ...
```

拆开看：LCEL 管道（`a | b`）要求每一节都是**可运行对象**（Runnable）。可你手头常常只有一行普通代码要插进去——拿 `RunnableLambda` 包一下，它就成了合格的管道零件。里面那坨逻辑用 lambda 写最省事，因为：

- 只有一行表达式（取字段、调个函数）
- 只用这么一次，不值得单独 `def`
- 就写在使用现场，读代码不用来回跳

**一句话定位：lambda 是"胶水"**——把一小段逻辑塞进某个需要函数的接口里。

## 五、lambda 的限制：为什么工具函数绝对不能用它

先说表达力：lambda 的函数体**只能写一个表达式**。

```python
lambda x: print(x); return x        # ❌ 不能有分号多语句
lambda x: if x > 0: x               # ❌ 不能有 if 语句（但可以 x if x > 0 else -x）
lambda x: (y = 1, x + y)            # ❌ 不能赋值
lambda x: "文档字符串"               # ❌ 不能挂 docstring
lambda x: x + 1                     # ⚠️ 不能写类型注解
```

然后是**真正致命的地方**。实验 A5 拿 LangChain 的 `@tool` 逐一试了四种写法：

```
  ① 用 def + docstring 定义工具（正确写法）：
     name        = 'named_tool'
     description = '两数相加。'

  ② 用 lambda 定义工具（不给 description）：
     ❌ ValueError: Function must have a docstring if description not provided.

  ③ 硬塞一个 description 绕过检查：
     能建出来，但 name = '<lambda>'   ← 名字成了字面量 '<lambda>'

  ④ 用 def 但忘了写 docstring：
     ❌ ValueError: Function must have a docstring if description not provided.
```

**注意 ④：报错和 lambda 一模一样。** 所以真正的要求不是"必须 `def`"，而是**必须有一份说明书**——docstring 或显式传 `description`，二选一。

但即使绕过去（③），lambda 还有个绕不开的硬伤：**名字固定是 `'<lambda>'`**。

> 上一课讲过，MCP 和 LangChain 都靠 `__name__` / `__doc__` 给模型生成说明书。于是：
>
> - 挂两个 lambda 工具 → 名字全叫 `'<lambda>'`，一个服务器里**直接撞名**
> - 想按名字分发（`FUNC_MAP[name]`）→ 全是同一个键，**彻底没法用**
>
> **结论：工具函数用 `def` 写、老老实实加 docstring，哪怕只有一行。** lambda 是"用完就扔的胶水"，不能拿来当对外暴露的接口。

---

# 下半场：dunder

## 六、`__name__` 只是函数身上一个普通属性

```
  hello.__name__  → 'hello'   类型是 str

  函数对象身上挂着一堆这种『双下划线开头结尾』的属性：

      __name__       = 'hello'
      __doc__        = '打个招呼'
      __module__     = '__main__'
      __qualname__   = 'hello'
      __dict__       = {}
```

**关键认知：`__name__` 不是魔法，它就是个普通的属性，值是个字符串。** 跟 `obj.color = "red"` 里的 `color` 是同一回事——只不过这个名字是 Python 在创建函数时自动帮你填好的。

所以 `f.__name__` 读作：**去 `f` 这个盒子上，找那张写着名字的标签。**

## 七、同一个 `__name__`，模块身上也有一份

这是最实用的一段：**`if __name__ == "__main__":` 到底在判断什么。**

```
  本脚本自己的 __name__  → '__main__'
  导入的 json 模块       → 'json'
  项目里的 phase4_2      → 'phase4_2_tool_calling'
```

规律：

| 情况 | `__name__` 的值 |
|------|----------------|
| 直接运行的脚本 | `'__main__'` |
| 被 import 进来的模块 | 它的模块名 |

所以每个脚本末尾那句的真相是：

```python
if __name__ == "__main__":
    main()
```

翻译成人话：**"如果这个文件是被我直接跑的，就跑 `main()`；如果它是被别人 `import` 进来的，就什么都别做，只提供里面的函数。"**

> **为什么需要这道闸？** 因为 `import` 一个模块**会执行它的顶层代码**。如果没有它，你写 `from phase4_2_tool_calling import FIXED_SIZE` 的时候，整个演示脚本就会自己跑起来、开始调大模型——那显然不是你想要的。
>
> **这也是为什么 `demo_mcp_server.py` 和 `extra_python_lambda_dunder.py` 都能安全地被别人 import。**

**注意这是同一个 `__name__` 机制的两个用途：**

- 函数上的 `__name__` → 这个函数叫什么
- 模块上的 `__name__` → 这个模块是怎么被加载的

## 八、四种下划线写法，别搞混

| 写法 | 含义 |
|------|------|
| `name` | 普通名字，公开可用 |
| `_name` | 单下划线开头：**"内部使用，别碰"的信号**（纯约定，解释器不强制） |
| `__name` | 双下划线开头（最多一个尾下划线）：会触发**名字修饰**，用于类里的私有成员 |
| `__name__` | 双下划线开头**且**结尾：**dunder**，由解释器/框架特殊对待 |

**一句话记忆：开头结尾都是双下划线的，是 Python 自己留的坑位，别乱起这种名字。** 你自己定义 `__name__`、`__doc__` 这种东西，就是在跟解释器抢方向盘。

## 九、dunder 是给解释器留的钩子（顺带解答 `not callable`）

```
  len('abc')  其实是在调   'abc'.__len__()          → 3
  [1,2,3][0]  其实是在调   [1,2,3].__getitem__(0)   → 1
  'a'+'b'     其实是在调   'a'.__add__('b')         → 'ab'
```

你写代码时用的是**语法**（`len()`、`[]`、`+`），Python 在背后翻译成 **dunder 方法调用**。这就是为什么自定义类只要实现了 `__len__`，就能被 `len()` 用：

```python
class MyBox:
    def __len__(self): return 42
len(MyBox())     # → 42
```

### ★ 现在回看上一课那个报错

```
TypeError: 'StructuredTool' object is not callable
```

**"可调用"这件事本身也是一个 dunder 钩子——`__call__`：**

```
f(1, 2)   其实是在调   f.__call__(1, 2)
```

Python 检查"这个对象能不能加括号调用"，看的就是它**有没有 `__call__`**。两行实测：

```
  普通函数 hello       有 __call__ 吗？ True    → 所以 hello() 能用
  工具对象 named_tool  有 __call__ 吗？ False   → 所以 named_tool() 报 not callable

      callable(hello)       → True
      callable(named_tool)  → False
```

**所以再看到 `xxx object is not callable`，第一反应应该是：去查这个对象有没有 `__call__`**——而不是怀疑函数名写错了。

---

## 十、速记表

| 你看到 | 是什么 | 一句话 |
|--------|--------|--------|
| `lambda x: x*x` | 没名字的函数 | 就是 `def` 的表达式版，`__name__` 固定 `'<lambda>'` |
| `lambda: f(1,2)` | **延迟执行**（thunk） | 把"调用"包成值传着走，让 `try` 接得住 |
| `key=lambda r: r[1]` | 排序依据 | 只用一次、写在现场的函数 |
| `RunnableLambda(lambda s: ...)` | 项目里的胶水 | 把一行逻辑塞进 LCEL 管道 |
| 工具函数的写法 | **必须 `def` + docstring** | lambda 没名字没文档，模型看不到说明书 |
| `f.__name__` | 函数的属性 | 值是个字符串，就是"函数叫什么" |
| `__name__ == "__main__"` | 模块的属性 | "我是被直接跑的，还是被 import 的" |
| `__xxx__` | dunder | 解释器留的钩子：`__call__` / `__len__` / `__getitem__` … |
| `not callable` | 没有 `__call__` | 用 `callable(obj)` 一行验证 |

**一句话记忆：`lambda` 是没名字的简写函数，用来当胶水和做延迟执行；`__name__` 是函数/模块身上的一个普通字符串属性，`__xxx__` 这类名字是 Python 给解释器留的钩子。**
