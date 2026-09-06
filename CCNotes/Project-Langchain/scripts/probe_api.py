import inspect, importlib, warnings
warnings.filterwarnings("ignore")

def probe(module_name, names):
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"[{module_name}] IMPORT FAIL: {type(e).__name__}: {e}")
        return
    for n in names:
        obj = getattr(mod, n, None)
        if obj is None:
            print(f"[{module_name}] {n}: NOT FOUND")
            continue
        try:
            sig = str(inspect.signature(obj))
        except (ValueError, TypeError):
            sig = "(no signature)"
        doc = (inspect.getdoc(obj) or "").split("\n")[0][:90]
        print(f"[{module_name}] {n}{sig}")
        if doc:
            print(f"    doc: {doc}")

probe("langgraph.prebuilt", ["create_react_agent", "ToolNode", "tools_condition"])
probe("langchain.agents", ["create_agent"])
probe("langgraph.checkpoint.memory", ["MemorySaver", "InMemorySaver"])
probe("langgraph.checkpoint.sqlite", ["SqliteSaver", "AsyncSqliteSaver"])
probe("langgraph.types", ["interrupt", "Command"])
probe("langgraph.graph", ["StateGraph", "START", "END"])
probe("langchain_core.messages", ["trim_messages"])
