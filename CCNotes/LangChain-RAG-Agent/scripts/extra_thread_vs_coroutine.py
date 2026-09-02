"""
线程 vs 协程：三个实验看出本质区别
========================================
场景设定：你要同时做 3 个"请求大模型"任务（每个模拟网络等待 0.5 秒）。
LLM 应用里 90% 的时间花在这种"等网络返回"上，CPU 其实闲着。

实验 1  等网络：同步 / 多线程 / 协程 三种写法比耗时  → 等待时间能被叠起来
实验 2  算 CPU：纯计算任务，线程和协程都救不了你     → Python 的 GIL
实验 3  协程里误用同步等待：整个事件循环被卡死       → 新手第一大坑

用法：
  PYTHONIOENCODING=utf-8 python scripts/extra_thread_vs_coroutine.py
"""

import asyncio
import time
from threading import Thread

TASKS = ["翻译", "总结", "提取"]          # 3 个"请求"，名字随便起
WAIT = 0.5                               # 每个请求模拟的网络等待秒数

# ---------------------------------------------------------------- 公共部分


def llm_sync(name: str) -> str:
    """同步版『请求大模型』：time.sleep = 模拟网络往返（纯等待，CPU 空闲）"""
    time.sleep(WAIT)
    return f"[{name}] 好了"


# ---------------------------------------------------------------- 实验 1


def sync_serial():
    """写法一：同步，一个等完再发下一个"""
    t0 = time.perf_counter()
    out = [llm_sync(n) for n in TASKS]
    return time.perf_counter() - t0, out


def threads_parallel():
    """写法二：3 条线程同时发，谁先回来谁先算"""
    out = {}

    def worker(name: str):               # 线程要跑的函数
        out[name] = llm_sync(name)

    t0 = time.perf_counter()
    ts = [Thread(target=worker, args=(n,)) for n in TASKS]
    for t in ts:
        t.start()                        # start = 把执行权交给操作系统去调度
    for t in ts:
        t.join()                         # join = 主线程在这等所有线程干完
    return time.perf_counter() - t0, out


async def llm_async(name: str) -> str:
    """协程版『请求大模型』：await = 主动把执行权让出去，水开了再回来"""
    await asyncio.sleep(WAIT)
    return f"[{name}] 好了"


def async_event_loop():
    """写法三：一个线程里，事件循环同时等 3 个协程"""
    async def main():
        t0 = time.perf_counter()
        results = await asyncio.gather(*(llm_async(n) for n in TASKS))
        return time.perf_counter() - t0, results

    return asyncio.run(main())           # run = 建一个事件循环，把 main 协程丢进去


# ---------------------------------------------------------------- 实验 2

TOTAL_WORK = 36_000_000                  # 固定总量：3600 万次加法（纯 CPU 计算）
N_THREADS = 3


def burn(work: int) -> None:
    """干烧 CPU：什么也不等，纯算"""
    x = 0
    for _ in range(work):
        x += 1


def cpu_sync():
    t0 = time.perf_counter()
    burn(TOTAL_WORK)                     # 一个人把全部活干完
    return time.perf_counter() - t0


def cpu_threads():
    t0 = time.perf_counter()
    chunk = TOTAL_WORK // N_THREADS
    ts = [Thread(target=burn, args=(chunk,)) for _ in range(N_THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return time.perf_counter() - t0


# ---------------------------------------------------------------- 实验 3


def blocking_mix():
    """同一个协程程序里：先用阻塞写法（time.sleep），再用正确写法（asyncio.sleep）"""
    async def bad(n: int) -> int:
        time.sleep(WAIT)                 # ← 坏：同步阻塞函数卡住整个事件循环
        return n

    async def good(n: int) -> int:
        await asyncio.sleep(WAIT)        # ← 好：异步等待，让出执行权
        return n

    async def main():
        t0 = time.perf_counter()
        await asyncio.gather(*(bad(n) for n in range(3)))
        bad_dur = time.perf_counter() - t0

        t0 = time.perf_counter()
        await asyncio.gather(*(good(n) for n in range(3)))
        good_dur = time.perf_counter() - t0
        return bad_dur, good_dur

    return asyncio.run(main())


# ---------------------------------------------------------------- 主流程


def fmt(sec: float) -> str:
    return f"{sec:.2f} 秒"


def main():
    print("实验 1｜3 个'网络请求'(每个等 0.5 秒)，三种写法各跑一次")
    d_sync, out1 = sync_serial()
    print(f"  同步  : {fmt(d_sync)}   ← 一个一个等，总共 {WAIT*3:.1f}s")
    print(f"    结果: {out1}")
    d_thr, out2 = threads_parallel()
    print(f"  线程  : {fmt(d_thr)}   ← 3 条执行线同时等，等待叠在一起")
    print(f"    结果: {list(out2.values())}（注意顺序不一定和发请求一致）")
    d_asy, out3 = async_event_loop()
    print(f"  协程  : {fmt(d_asy)}   ← 1 个线程 + 事件循环，同样叠起来等")
    print(f"    结果: {list(out3)}")

    print("\n实验 2｜纯 CPU 计算 {:,} 次加法：线程能变快吗".format(TOTAL_WORK))
    d_cpu_s = cpu_sync()
    d_cpu_t = cpu_threads()
    print(f"  单线程一口气做完 : {fmt(d_cpu_s)}")
    print(f"  {N_THREADS} 条线程分着做   : {fmt(d_cpu_t)}")
    print("  → 没变快。Python 同一时刻只能执行一个线程（GIL），分线程还得倒贴切换开销")

    print("\n实验 3｜协程里误用同步阻塞函数（time.sleep）会怎样")
    d_bad, d_good = blocking_mix()
    print(f"  坏写法 time.sleep(0.5)   : {fmt(d_bad)}   ← 又一个一个等了！循环被卡死")
    print(f"  好写法 await asyncio.sleep: {fmt(d_good)}   ← 等待叠起来")

    print("\n一句话总结：")
    print("  等网络(IO) → 线程/协程都能叠等待；Python 里协程更省、不用锁、开几万个不心疼")
    print("  算 CPU     → 只能靠多进程(ProcessPoolExecutor)，线程和协程都救不了")
    print("  LLM 应用   = 全是网络等待 → LangChain/MCP 客户端清一色 async/await")


if __name__ == "__main__":
    main()
