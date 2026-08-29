"""
Phase 5.1：Streamlit Web UI —— 上传文档 → 生成协议 → 查看/下载
================================================================
Streamlit 心智模型（理解这个就懂 90%）：
  - 脚本全量重跑：每次交互（点按钮/上传/勾选）整个脚本从头执行
  - st.session_state：跨重跑保存状态。LLM 调用很贵，生成结果必须存住，
    否则用户切个标签页结果就没了
  - st.cache_resource：缓存昂贵资源（链、向量库连接），重跑时复用

架构原则：UI 是薄壳。逻辑全部复用 scripts/ 里的零件
（3.3 的链、4.1 的 RAG 链、3.4 的 Markdown 渲染）。

运行：
  streamlit run app.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from phase3_3_batch_stream import clean_chain
from phase4_1_rag import rag_chain
from generate_protocol import render_markdown


@st.cache_resource(show_spinner="加载模型组件中...")
def get_chains():
    """链是昂贵资源（内含模型客户端），缓存后重跑不重建"""
    return clean_chain, rag_chain


def decode_doc(raw: bytes) -> str:
    """上传文件的编码自适应（同 3.1：utf-8-sig → utf-8 → gb18030）"""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文件编码")


st.set_page_config(page_title="协议自动生成工具", page_icon="📋", layout="wide")
st.title("📋 协议自动生成工具")
st.caption("上传需求文档 → 大模型分析 → 输出协议规范（草稿，发布前请人工审核）")

plain_chain, rag_chain_cached = get_chains()

col1, col2 = st.columns([3, 1])
with col1:
    uploaded = st.file_uploader("上传需求文档（.md / .txt，支持 GBK 编码）", type=["md", "txt"])
with col2:
    st.write("")
    use_rag = st.checkbox("启用 RAG（检索历史协议模板）", value=True)

if st.button("生成协议", type="primary", disabled=uploaded is None):
    try:
        text = decode_doc(uploaded.getvalue())
        chain = rag_chain_cached if use_rag else plain_chain
        with st.spinner("正在分析需求文档（约 10~30 秒）..."):
            result = chain.invoke({"requirement": text})
        # 存进 session_state：后续重跑直接读，不重复调用 LLM
        st.session_state["result"] = result
        st.session_state["md"] = render_markdown(result)
    except Exception as e:
        st.error(f"生成失败：{e}")

if "result" in st.session_state:
    r = st.session_state["result"]
    st.divider()
    st.subheader(f"📄 {r.get('protocol_name', '协议规范')}")
    st.write(r.get("description", ""))

    tab_fields, tab_rules, tab_issues, tab_raw = st.tabs(["字段表", "约束规则", "评审发现", "原始 JSON"])
    with tab_fields:
        st.dataframe(r.get("fields", []), hide_index=True)
    with tab_rules:
        for c in r.get("constraints", []):
            st.write(f"- **{c.get('field', '?')}**：{c.get('rule', '')}")
    with tab_issues:
        issues = r.get("issues", [])
        if issues:
            for i in issues:
                st.warning(f"[{i.get('severity', '?')}] **{i.get('field', '?')}**：{i.get('message', '')}")
        else:
            st.success("无评审问题")
    with tab_raw:
        st.json(r)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇ 下载 JSON（草稿）", json.dumps(r, ensure_ascii=False, indent=2),
                           file_name="protocol_draft.json", mime="application/json")
    with c2:
        st.download_button("⬇ 下载 Markdown 规范（草稿）", st.session_state["md"],
                           file_name="protocol_draft.md", mime="text/markdown")
