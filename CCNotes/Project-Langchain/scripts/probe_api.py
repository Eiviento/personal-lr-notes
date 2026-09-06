"""
Agent 深度研学项目 API 基线探针（W0 硬闸门资产）
=================================================
作用：核验 agent_env 里 langgraph/langchain 关键 API 的真实存在性，与教学基线比对。
     探针 exit 0 = 环境与基线一致，可开始落教学代码；不一致则非零退出并列出差异（fail-closed）。

用法（Windows 控制台必须 UTF-8 前缀）：
  PYTHONIOENCODING=utf-8 <agent_env python> scripts/probe_api.py

基线说明（2026-09-06 实测）：
  - langgraph.checkpoint.sqlite 在 1.2.9 主包中不存在（SqliteSaver 拆分到独立包
    langgraph-checkpoint-sqlite，agent_env 未装）——属已知缺失，expected=False。
    若将来安装该包，本探针会红并提示更新基线（即 W3 持久化方案的决策点信号）。
"""

import importlib
import sys

# (module, name) -> 基线期望：True = 应存在 / False = 已知缺失（出现即环境已变，需更新基线）
EXPECTED: dict[tuple[str, str], bool] = {
    ("langgraph.prebuilt", "create_react_agent"): True,
    ("langgraph.prebuilt", "ToolNode"): True,
    ("langgraph.prebuilt", "tools_condition"): True,
    ("langchain.agents", "create_agent"): True,
    ("langgraph.checkpoint.memory", "MemorySaver"): True,
    ("langgraph.checkpoint.memory", "InMemorySaver"): True,
    ("langgraph.checkpoint.sqlite", "SqliteSaver"): False,  # 需独立包，见 docstring
    ("langgraph.checkpoint.sqlite", "AsyncSqliteSaver"): False,
    ("langgraph.types", "interrupt"): True,
    ("langgraph.types", "Command"): True,
    ("langgraph.graph", "StateGraph"): True,
    ("langgraph.graph", "START"): True,
    ("langgraph.graph", "END"): True,
    ("langchain_core.messages", "trim_messages"): True,
}


def main() -> int:
    print(f"API 基线探针 — {len(EXPECTED)} 个符号，比对教学基线")
    print("-" * 60)
    module_cache: dict[str, object | None] = {}
    for module_name, _ in EXPECTED:
        if module_name in module_cache:
            continue
        try:
            module_cache[module_name] = importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            module_cache[module_name] = None
            print(f"[import] {module_name}: ModuleNotFoundError: {e}")

    violations: list[str] = []
    for (module_name, name), expected in EXPECTED.items():
        mod = module_cache.get(module_name)
        present = mod is not None and hasattr(mod, name)
        status = "OK  " if present == expected else "FAIL"
        print(f"[{status}] {module_name}.{name}  present={present} expected={expected}")
        if present != expected:
            note = "应在但缺失！" if expected else "不应在但出现了（环境已变，需更新基线或调整装包决策）！"
            violations.append(f"{module_name}.{name}: {note}")

    print("-" * 60)
    if violations:
        print(f"基线不符 {len(violations)} 项（fail-closed）：")
        for v in violations:
            print("  -", v)
        return 1
    print("全部符号与基线一致 → 环境就绪，可落教学代码")
    return 0


if __name__ == "__main__":
    sys.exit(main())
