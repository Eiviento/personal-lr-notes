# HANDOFF — AI 应用工程 · 阶段 1 笔记 Web 化

> **面向：完全没有上下文的新会话。** 读完这一份就能接手，不需要翻历史对话。
> 写于 2026-09-13 会话结束前。

---

## 一、我们在做什么

**项目**：`CCNotes\AI-Application-Engineering` —— 「AI 应用开发学习项目」的**生产层**主线
（对标企业 AI 应用开发 JD，六个阶段；阶段 1「生产级 RAG 服务」= DocQA，已实现完毕）

**两个关键路径概念（别搞混）**：
- **git 仓库根** = `D:\CC\personal-lr-notes`（**不是** `AI-Application-Engineering`，它是子目录）
- **工作目录** = `D:\CC\personal-lr-notes\CCNotes\AI-Application-Engineering`
- 远程：`origin` → `https://github.com/Eiviento/personal-lr-notes.git`

**本次会话（2026-09-13）做了四条线**：

| # | 工作线 | 产物 |
|---|--------|------|
| 1 | 补验证：跑通阶段 1 遗留的「真实 DeepSeek 生成」环节 | 更新 `README.md` / `docs\findings.md` / `lessons\lesson_04` |
| 2 | 笔记 Web 化：把 md 笔记做成可离线阅读的 HTML | `notes-web\index.html`（新目录） |
| 3 | RAG 原理讲义 + 4 个可跑实验 | `notes-rag\`（新目录） |
| 4 | 一条命令跑完整 RAG 的脚本 | `scripts\ask_local.py` |

**用户画像**：应用软件工程师，正在按阶段学习 AI 应用工程。偏好：讲清原理、要能跑的实验、不喜欢纯 md 阅读、对「数字有没有实跑依据」很敏感。

---

## 二、已完成（全部已 commit）

本次会话贡献的 commit（按时间）：

```
f36c2bf  feat(scripts): 新增 ask_local.py——本地一条命令跑完整 RAG（检索+生成），无有效 key 自动降级
0833d1f  feat(notes-web): 新增笔记阅读页 index.html——阶段1四课+导航，单文件自包含可离线
4a05fb2  feat(notes-rag): RAG 原理讲义（向量化/检索/融合）+ 4 个可跑实验 + 小语料 + 导读
08b5ca3  feat(notes-rag): 为 e3 加 RRF 对照输出，讲义补「三种融合方式并排对比」
e70bba5  fix(notes-rag): 审查修复——ask_local 注释路径；e2 观察段补全对照
dc90404  fix(notes-web): 标注数据时点——语料 33→37 篇，说明当前值与结论不变
```
（另有 `f28ac20`「补 F3 真实 DeepSeek 生成验证」也是本次会话的）

### 交付物详解

**`notes-web\index.html`**（819 行 / 59KB）
- 内容：阶段 1 四课（切分 / 向量 / 混合+精排 / 评估+服务化）+ 首页（路线图、RAG 全链路、环境事实）
- 特性：单文件自包含、零外部依赖、可离线双击打开、浅/深主题（`?theme=dark` 可直链）

**`notes-rag\`**（7 文件 / 1148 行）—— 讲「向量化 / 检索 / 融合」的原理
- `index.html`：讲义主体（直觉 → 公式 → 真实输出）
- `examples\e1~e4`：4 个可独立运行的实验（e1 玩具向量、e2 真实 BGE、e3 两路检索对照、e4 RRF 手算）
- `data\sample_docs.md`：6 段自制小语料（故意做小，便于观察）
- `README.md`：导读

**`scripts\ask_local.py`**：不起 HTTP 服务，一条命令跑完「检索 + 生成」；无有效 key 时优雅降级为只出检索结果

---

## 三、当前状态 / 卡在哪

**没有硬阻塞。** 但有几点必须知道：

### 1. 环境事实（跑任何脚本都要遵守）
```bash
# 解释器（必须用它，系统 python 缺依赖）
E:\software\OfficeWorkLife\Anaconda\envs\agent_env\python.exe
# 所有脚本命令都要加 UTF-8 前缀（Windows GBK 坑）
PYTHONIOENCODING=utf-8 <上面的解释器> <脚本>
```

### 2. API key 现状
- **本项目 `.env` 不存在**（写入被运行时安全策略拦截，见「坑 5」）
- `generator._load_env()` 会按 `本项目\.env → ..\Project-Langchain\.env → ..\LangChain-RAG-Agent\.env` 回落，**总能捡到兄弟项目的 key**
- 兄弟项目的 key **已失效**（401，尾号 `a3b2`）
- 用户曾给过一个有效 key（尾号 `087b`），上次验证时可用；**建议用户早已轮换，不要指望它**

### 3. 工作区有未提交项 —— **都不是本次会话的产物，别乱动**
```
 D data/chroma_db_api/5a5f3ab3-.../{data_level0,header,length,link_lists}.bin   ← 被跟踪的向量库，被脚本 rmtree 掉
?? AGENTS.md / .rivet-config.json / .rivet.md / .rivet/ / data/chroma_db_api/0a4ec66d-.../
```
处理建议：向量库二进制**本不该被 git 跟踪**（`.gitignore` 里有 `chroma_db/`，但 `chroma_db_api` 不匹配该 pattern）。要彻底解决应把它们从索引移除并补 gitignore——**这是个待决策项，先问用户**。

### 4. 未验证项
- **「生成成功」端到端路径**：只在有有效 key 时验过一次。当前环境无有效 key，只能验证两条降级路径（空 key / 无效 key），均已 exit 0
- **视觉验收**：本运行时**没有视觉通道**（`read_file` 读不了 PNG、`ask_image` 报「会话无可查询图片」），所以两份 HTML 的「好不好看」**从未被模型核验过**，只能靠用户自己打开看

---

## 四、下一步计划

### 用户可能的下一个动作（按优先级）

1. **阶段 2「记忆体系」**（`src\memory\`，尚未开始）
   - 计划见 `docs\learning-plan.md` 第三节；用户节奏是「一次一个阶段」
   - 开工前先跑该项的最小探针（项目铁律）

2. **等用户看完 HTML 后的调整**
   - `notes-web\index.html` 与 `notes-rag\index.html` 的视觉反馈（配色 / 字号 / 那几张图是否够清楚）
   - 用户曾问「要不要在 e3 里也打印 RRF 排序来对照」——**已做**（commit `08b5ca3`）

3. **待决策的遗留项**（见下）

### 遗留项（我列出来但**没动**，需用户拍板）

| 项 | 说明 | 建议 |
|----|------|------|
| `compare_splitter.py` 尾注硬编码 | 表格会实算刷新，但结尾三行「观察」永远打印旧的 `472/570/621`，自称「据本轮实跑数据」其实不成立 | 改成按实算结果动态生成 |
| `run_eval.py` / `compare_retrieval.py` 的 `rmtree` | 会删**被 git 跟踪**的 `data/chroma_db_eval`、`data/chroma_db_cmp`——这就是 `git status` 里 `deleted` 的来源 | 把库目录改为不跟踪，或在脚本里用独立目录 |
| `e2` 模型名硬编码（第 47 行） | 写死 `bge-small-zh`，换模型会与实际不符 | 低优先级 |
| `e2`/`e3`/`ask_local` 模型缺失时裸抛 `FileNotFoundError` | 消息可读但带 traceback | 低优先级，加友好提示即可 |
| `progress.md` 落后 | 只记到 Wave 1，实际阶段 1 的 Wave2-4 早已完成 | 补一条进度记录 |

---

## 五、踩过的坑（**绝对不要再踩**）

### 🔴 坑 1：语料会变，硬编码的数字必然过期
`data\documents\` 的语料被**其他并发会话**持续补充（33 篇 → 37 篇，可能还会涨）。
后果：所有基于语料规模的「实跑数据」都会过期。
- 切分块数：33 篇时 `472/570/621` → 37 篇时 `552/659/714`
- rerank 档指标：`0.95/0.95/0.64` → `0.85/0.85/0.62`
- 但**规律不变**（fixed 最少、markdown 最碎；rerank 拖低 MRR）

**对策**：讲这类数据时**必须标时点**（「录于 X 日，当时语料 N 篇」），并给出当前值。不要试图追着更新数字——追不完。

### 🔴 坑 2：讲义/报告里的每个数字都必须来自实跑
本次会话**真的犯过**：我在 `notes-rag/index.html` 里手算写了个 `4.5376`，核销脚本一查发现无实跑依据（同表还有一行「约 0.30」是编的）。
**对策**：先写可跑脚本 → 跑出真实输出 → 把输出抄进文档。核销方法（可复用）：
```python
# 把文档里所有 4 位小数抓出来，逐个回查脚本输出
nums = set(re.findall(r'\b\d\.\d{4,6}\b', html))
missing = [n for n in nums if n not in open('all_outputs.txt').read()]
```

### 🔴 坑 3：`write_file` 会校验 HTML 标签平衡
分块 append 一个不完整的 HTML 骨架会被**拒绝**（「unclosed tag」），且新文件会被移除。
**对策**：写 HTML 用「**骨架 + 占位符**」法——先 `write_file` 一个标签闭合完整的骨架（含 `<!-- @@SECTION@@ -->` 占位），再用 `edit_file` 逐个替换占位符。

### 🔴 坑 4：CSS 网格溢出（1024–1100px 区间）
`main{max-width:860px; margin:0 auto}` 放在 `display:grid` 的容器里时，**auto 外边距会让网格项的 stretch 失效**，元素按 content 撑开、超出轨道，产生横向滚动条。
**对策（两条一起用）**：
```css
body{grid-template-columns: 284px minmax(0,1fr);}  /* 轨道显式 min 0 */
main{width:100%; max-width:860px; margin:0 auto;}  /* 给网格项确定宽度 */
```
**验证方法**：headless Chrome + 临时 JS 探针，在 400/768/900/981/1024/1100/1280/1440/1920 九个宽度下检查 `scrollWidth > innerWidth`。

### 🔴 坑 5：`.env` 写入被运行时安全策略拦截
`write_file` 写 `.env` 会报 `Sensitive file blocked`（fail-closed）。这不是 bug，是设计。
**对策**：把 key 走 **shell 环境变量注入**（`DEEPSEEK_API_KEY='...' python ...`）。注意 `load_dotenv` 默认**不覆盖**已存在的环境变量，所以注入优先级高于 `.env`。

### 🔴 坑 6：key 会「幽灵回落」
`Generator._load_env()` 总能找到兄弟项目的 `.env`，所以「没有 key」的降级分支**不会触发**——脚本会直接崩在 API 调用上。
**对策**：错误处理要**同时覆盖初始化失败与调用失败**（`Generator()` 抛 `RuntimeError` + `generate()` 抛 `AuthenticationError`）。`ask_local.py` 已修好，见其 `except Exception`。

### 🔴 坑 7：浏览器工具的两个限制
- `browser_debug` **只支持 http/https**，`file://` 会被拒（「不支持的协议」）
- 它需要 chromium，**本机未装**（报 `Executable doesn't exist at ...ms-playwright\chromium-...`）

**对策（本次采用）**：用系统 Chrome 的 headless 模式直接截图 + dump DOM：
```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
"$CHROME" --headless=new --disable-gpu --dump-dom "<url>"      # 拿 JS 执行后的 DOM
"$CHROME" --headless=new --screenshot="out.png" --window-size=1440,1200 "<url>"
```
本地文件要跑就起 `python -m http.server <port>` 放在项目根。

### 🔴 坑 8：本运行时读不了图片
`read_file` 对 PNG 报「File is binary」；`ask_image` 报「本会话没有可查询的图片」。
**对策**：不要指望「看截图验证视觉」。改用**程序化验证**（DOM 结构、computed style、`scrollWidth` 探针），视觉部分**如实标注「未验证」并交给用户**。

### 🔴 坑 9：`outputs\` 被 gitignore，`read_file` 拒绝读
截图/日志放 `outputs\` 后读不出来（「File is gitignored」）。
**对策**：临时验证产物放 `.rivet\scratch\`（未被忽略）。

### 🔴 坑 10：`ruff` 和 `mypy` **没装**
项目 `.rivet-config.json` 声明了 `mypy .` 和 `ruff check .`，但 agent_env 和系统 python **都没有这两个模块**。
**对策**：跑不了就**如实标注「lint/typecheck 未运行」**，不要假装通过；可用的替代门禁是 `python -m py_compile <file>` + 实际执行脚本。

### 🟡 坑 11：Git Bash 中文输出乱码
命令行里 Python 打印的中文会显示成乱码（GBK 问题），但**文件内容和判断不受影响**。
**对策**：看结论时忽略终端乱码，必要时 `read_file` 读文件原文。

### 🟡 坑 12：bash 命令会被去重拦截
重复执行相同命令会提示「已用相同的 bash 命令读取过该文件」。
**对策**：换个参数（如加 `?t=123`）或先 `cat > /tmp/xxx` 落地再看。

### 🟡 坑 13：委派的审查员可能失败
本次派了 2 个审查员，**1 个 failed**（输出解析失败，零有效产出）。
**对策**：发现 worker 失败时，**自己补做它的核心检查**，并在报告里如实说明「该项由我自查，深度不如独立审查员」。不要假装审查完成了。

---

## 六、新会话建议的起手动作

```bash
cd "D:/CC/personal-lr-notes/CCNotes/AI-Application-Engineering"

# 1. 先看当前状态（不要重复跑 git status，上下文里已有注入块）
git log --oneline -8

# 2. 想跑 RAG 完整链路（无需起服务，无 key 也能出检索结果）
PYTHONIOENCODING=utf-8 "E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe" scripts/ask_local.py "混合检索是怎么融合关键词和向量的"

# 3. 想验证原理讲义里的数字
PYTHONIOENCODING=utf-8 "E:/software/OfficeWorkLife/Anaconda/envs/agent_env/python.exe" notes-rag/examples/e4_fusion_rrf.py   # exit 0 = 手算与代码一致

# 4. 想读笔记（双击即可，无需服务）
#    notes-web/index.html    —— 阶段 1 四课（实现过程）
#    notes-rag/index.html    —— 向量化/检索/融合（原理）
```

**开工前先读**：`AGENTS.md`（项目规则，含高危命令闸门）、`docs\learning-plan.md`（六阶段路线）。
