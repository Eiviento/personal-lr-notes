# LangSmith Studio：把项目的图搬进可视化调试器

> 2026-08-30 实测安装并跑通。覆盖：是什么 / 环境怎么建 / 三个配置文件 / 怎么跑 / 踩坑四连。

## 一、是什么

LangChain 官方的**图调试 IDE**。现在的形态 = **网页版 Studio**（smith.langchain.com/studio）+ 你机器上的**本地服务**；macOS 桌面版已废弃，`langgraph dev` 不需要 Docker。

在 Studio 里能看到：

- 图的**节点和边**（可视化，点开就是项目里的函数）
- 一次运行的**完整轨迹**：每个节点的输入/输出、中间状态
- agent 循环（工具图）里模型每一轮"点菜/上菜"的来回
- 修了代码热重载，图结构立刻更新

对比本项目之前的方式：只有 `print` + 存 JSON，中间状态靠 tap 观察——Studio 把"中间产物可见"做到了极致（3.2 教学里讲过这个原则）。

## 二、环境：为什么单独建 studio_env

`langgraph-cli[inmem]`（内存版本地服务）**硬性要求 Python 3.11+**，而项目主环境 agent_env 是 3.10。

```bash
# 1) 建 Python 3.11 环境（--override-channels 绕过 .condarc 里失效的 pkgs/pro 镜像）
E:/software/OfficeWorkLife/Anaconda/Scripts/conda.exe create -n studio_env python=3.11 -y --override-channels -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main

# 2) 装 CLI + 项目依赖 + colorama（坑 #3 见下）
E:/software/OfficeWorkLife/Anaconda/envs/studio_env/python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "langgraph-cli[inmem]" langchain-openai langgraph colorama
```

不动 agent_env：Studio 环境独立，坏了重来不伤主环境（与"草稿终稿分离"同一个思路）。

## 三、三个配置文件（都已在项目里）

| 文件 | 干什么 |
|------|--------|
| `langgraph.json` | 告诉 CLI 有哪些图：`graphs` 指向 `scripts/studio_graphs.py` 的两个模块级变量 `pipeline_graph` / `agent_graph`；`env` 指向 `.env` |
| `scripts/studio_graphs.py` | 为什么单独建：extra_langgraph_intro.py 里是 build 函数，而 Studio 需要**模块级已编译图变量**。这文件做两件事：把 scripts/ 补进 sys.path（复用兄弟模块的链）、调 build 函数编译成模块级变量 |
| `.env` | `LANGSMITH_API_KEY`（注册后粘贴）；**必须纯 ASCII**（坑 #2）；已被 gitignore |

## 四、怎么跑

```bash
cd "D:\CC\personal-lr-notes\CCNotes\LangChain-RAG-Agent"
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 E:/software/OfficeWorkLife/Anaconda/envs/studio_env/Scripts/langgraph.exe dev
```

看到 `API: http://127.0.0.1:2024` 就是起来了，然后浏览器打开它打印的 Studio UI 链接：

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

需要 LangSmith 账号（免费）：smith.langchain.com 注册 → 设置里创建 API Key → 粘贴到 `.env` → 重跑 dev。健康检查：`curl http://127.0.0.1:2024/ok` 应返回 `{"ok":true}`；图列表 `POST /assistants/search` 应看到 `pipeline` 和 `agent` 两个图（实测都有）。

## 五、踩坑四连（Windows + 中文系统专属，全踩过）

| # | 现象 | 原因 | 解法 |
|---|------|------|------|
| 1 | `langgraph dev` 报 "in-mem server requires Python 3.11 or higher" | agent_env 是 3.10，[inmem] 装不上 langgraph-api | 建 studio_env（3.11） |
| 2 | `UnicodeDecodeError: 'gbk' codec can't decode byte 0xaf`（读 .env 时） | python-dotenv 按系统默认编码 GBK 读文件，中文注释是 UTF-8 | `.env` 纯 ASCII，中文说明放文档 |
| 3 | `SystemError: ConsoleRenderer with colors=True on Windows requires the colorama package` | structlog 彩色日志在 Windows 需要 colorama | `pip install colorama` |
| 4 | `UnicodeDecodeError: 'gbk' codec can't decode byte 0x94`（langgraph_api/validation.py 读 openapi.json） | 包自身代码读文件没写 encoding="utf-8"，用系统默认 GBK | 启动命令加 `PYTHONUTF8=1`（Python UTF-8 模式，PEP 540，默认编码全局变 UTF-8） |

坑 #2~#4 是同一种病的三个表现：**中文 Windows 默认编码 GBK，Python 里读文件不写 encoding 就按 GBK 来**。项目的坑 #5（控制台吃不下 emoji）也是这病的亲戚。

## 六、深挖

- 官方文档（英文）：https://docs.langchain.com/langsmith/local-dev-testing
- 图的概念（State/Node/Edge/条件边）：[extra_langchain_langgraph.md](extra_langchain_langgraph.md)
- 两个图的源码精读：`scripts/extra_langgraph_intro.py`（Graph A 直线图 / Graph B 工具循环图）
