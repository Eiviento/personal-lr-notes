# 代码精读 9：phase4_1_rag.py（RAG：历史模板语义检索）

> Phase 4 开篇，项目最长的脚本。核心命题：**文本怎么变成向量**，以及**怎么按"意思"检索**。

## 执行示例（实测）

- `query "水表阀门远程控制，每天上报用水量"` → top-1 命中【水表计量协议模板】，距离 0.364（cosine 空间）
- `run sample_requirement2.md` → 无 RAG：device_id/cumulative_water_volume/timestamp；有 RAG：**meter_id/total_flow/crc16（与公司模板逐字一致）**，且模板没有 timestamp 就不带（恰好符合需求）

**RAG 的价值不是"更全"，是"风格一致性"**——新协议自动继承历史模板命名约定。

## A. WordPieceTokenizer（分词：文字 → 编号）

1. 中文**逐字**切（一字一 token），其余按空白切：`re.findall(r"[一-鿿]|[^\s一-鿿]+", text)`
2. 英文子词**最长匹配**：整词不在词表就逐字缩短找最长片段；`##` 前缀 = "前面词的接续"
3. 特殊标记：[CLS] 开头（整句代表）、[SEP] 结尾

## B. LocalBertEmbedding（推理 + 池化）

四步：①分词 → ②ONNX 推理（本地神经网络，每个 token 一个向量）→ ③池化（BGE 取 [CLS] 向量）→ ④归一化（长度变 1，点积 = 余弦相似度）。

## C. 三个踩坑故事（为什么模型要本地）

| 坑 | 解法 |
|----|------|
| pip 直连 PyPI 被重置 | 清华镜像 |
| chromadb 内置 ONNX 从 S3 下载超时（URL 写死） | 自写 EmbeddingFunction，hf-mirror 下载 BGE ONNX 到 models/ |
| MiniLM（英文）中文检索错乱 | 换 BGE-small-zh（中文）+ CLS 池化 + `hnsw:space=cosine` |

教训：embedding 模型必须匹配语言；换模型管道代码不动。

## 自测

1. 中文为什么逐字切？`##` 前缀是什么意思？
2. 归一化是为了什么？
3. BGE 和 MiniLM 的池化方式区别？

## D. 向量库读写

- `PersistentClient(path=DB_DIR)`：落盘，重启不丢
- **入库与查询必须用同一个 embedding_function**（两边坐标轴不同，距离无意义）
- `metadata={"hnsw:space": "cosine"}`：显式余弦（配套归一化）；**只在首次创建生效**——换模型必须删库重建
- `lru_cache` 缓存 collection：ONNX 会话加载 1~2s，UI 每次重跑都重载会废
- `build_db`：三个平行列表 documents（正文）/metadatas（标签）/ids（文件名，upsert 幂等）
- `retrieve`：query 返回 documents/metadatas/distances 平行列表，zip 拼参考文本；距离越小意思越近

## E. RAG 链 = 3.4 链 + 一步 + 换一环

```python
rag_chain = (
    RunnablePassthrough.assign(retrieved=RunnableLambda(lambda s: retrieve(s["requirement"])))  # 新增
    | RunnablePassthrough.assign(key_points=analyze_chain)      # 同 3.4
    | RunnablePassthrough.assign(fields=rag_fields_chain)       # 换成 RAG 版（吃 {retrieved}）
    | RunnablePassthrough.assign(checks=rules_chain)            # 同 3.4
    | RunnableLambda(merge_final)                               # 同 3.4
)
```

全部技能合流：零件复用（只换②只加一步）/ 转接头（检索是普通函数包 RunnableLambda）/ 物流标签（挂键 retrieved = 占位符 {retrieved}）/ 检索放最前（只需原始输入，先拿素材再推理）。

## F. compare + main

compare：同输入喂两条链并排打印；main：build/query/run 子命令分发（3.3 模式复用）。

## 自测

1. 入库和查询为什么必须同一个 embedding_function？
2. upsert 的 ids 用文件名有什么好处？
3. RAG 链比 3.4 链多了什么、换了什么？

---

# 代码精读 10：phase4_2_tool_calling.py（模型点菜，代码上菜）

> 执行示例实测：注入 msg_type 字节数错误 → 模型自主发起 7 次 validate_field_type 调用 → 代码揪出错误 → 模型汇总成修正报告。

## 四块

### A. @tool 装饰器

- **类型注解 → JSON Schema**：模型填的参数必然合法（1.3"最可靠的结构化输出"）
- **docstring → 使用时机说明**：告诉模型什么时候调用
- FIXED_SIZE 死规则表：规则放代码，模型只负责发起查询

### B. bind_tools

`llm.bind_tools([工具])`：把函数说明书发给模型——模型不更聪明，只多一个可请求的选项。

### C. run_tool_loop（手写循环）

1. `while response.tool_calls`：模型还在点菜就继续上菜
2. `FUNC_MAP[name].invoke(args)`：按名分派——**执行权永远在代码手里**（安全边界）
3. `rounds < 5`：防死循环（工具调用标准防御）
4. `ToolMessage(tool_call_id=...)`：结果带"回执编号"回传，模型才知道对应哪次请求

### D. main 两细节

- 注入错误演示：教学脚本主动造 bug 演示工具威力，真实使用删掉
- 手写 SystemMessage/HumanMessage 而非模板：消息反复追加，模板不适合（"固定用模板，动态用手写"）

## 自测

1. @tool 的类型注解和 docstring 分别变成了什么？
2. while 条件是什么？rounds 上限防什么？
3. 谁真正执行了函数？

---

# 代码精读 11：phase4_3_human_review.py（人在回路，Phase 4 收官）

> 执行示例实测：机审 7 条（1 代码 + 6 LLM 评审），管道喂决策（1 修正/3 待办/其余忽略）→ 终稿三件套 + 统计。

## 四块

### A. 两层机审（代码 + LLM 互补）

| 层 | 实测例子 | 特点 |
|----|---------|------|
| code_check（FIXED_SIZE 死规则） | "uint8 应为 1 字节，声明 2" | 精确必揪出 |
| LLM 评审（REVIEW_PROMPT） | "清零后未置溢出标志，数据丢失无法追溯" | 洞察开放问题 |

= 2.2"形式 vs 内容"的完整答案：形式交代码，内容交 LLM，互补不替代。

### B. human_review 交互循环

- 自动修正只给确定性 fix（`"fix" in issue`）——LLM 问题只有忽略/待办选项
- 逐条提问：人一次一个决定
- EOF 容错：管道喂答案/脚本化调用不卡死

### C. 终稿三件套 + 留痕

- `*_final.json` / `*_final.md`（带审核记录表 + "已通过人工审核"页脚）/ `*_review_log.json`
- 草稿与终稿分离：草稿永远不被动，可回退
- 审核记录两处留痕：MD 给人看，log 给程序/追溯

### D. main

注入错误演示 → 机审 → 人审 → 确认（n 可取消）→ 修 + 存 → 统计。

## 自测

1. 两层机审各自查什么？
2. 为什么 LLM 问题没有"自动修正"选项？
3. 草稿和终稿为什么要分开存？

---

*Phase 4 代码精读完结。app.py / phase5_2 / extras 的精读后续追加。*
