"""
LangSmith Studio 入口：把项目里的图暴露成模块级编译图
======================================================
langgraph.json 的 graphs 指向这里（"pipeline" / "agent" 两个图），
LangSmith Studio / langgraph dev 加载的就是这两个模块级变量。

为什么要单独建这个文件：extra_langgraph_intro.py 里是 build 函数，
而 Studio 需要"模块级的已编译图变量"。这里做两件事：
  1. 把 scripts/ 目录放进 sys.path（无论从哪里加载都能找到兄弟模块）
  2. 复用 extra_langgraph_intro 的 build 函数，编译成模块级变量

用法：
  langgraph dev          # 启动本地服务（2024 端口），Studio 网页接入
"""

import sys
from pathlib import Path

# Studio 加载本文件时不保证 scripts/ 在 sys.path，手动补上（复用 3.1/3.2/4.2 的链）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extra_langgraph_intro import build_agent_graph, build_pipeline_graph

# ─── 模块级编译图：langgraph.json 的 graphs 就指向这两个名字 ───
pipeline_graph = build_pipeline_graph()  # Graph A：四步链的直线图
agent_graph = build_agent_graph()        # Graph B：工具校验循环图（条件边）
