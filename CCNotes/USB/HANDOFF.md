# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-08-02（第七会话）
> 主线学习进度：32/67 知识点（48%）— 暂停在 Phase 4 入口
> 本会话重点：usb-notes.html 全面翻新——单文件拆 3 文件，暗色 IDE 风格，可访问性补全
> **⚠️ 工作分支: `redesign/usb-notes-3file`（未合并到 main）**

---

## 一、这个项目在做什么（给完全没有上下文的新会话）

### 主线任务：USB 协议系统学习

带一位 C/C++ 应用软件工程师从零开始学 USB 协议，最终目标是构建一个 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）。

用户选的是**方案 A（自底向上）**：先讲协议理论，最后才写代码。

### 副线任务：笔记 Web 可视化

把学习笔记做成**离线 HTML 页面**，零外部依赖，双击打开。已从单文件翻新为 3 文件架构：
- `usb-notes.html` — Phase 1-3 理论可视化（纯 HTML 结构，2,239 行）
- `usb-notes.css` — 10 层分层样式（1,153 行，暗色默认 IDE 风格）
- `usb-notes.js` — 4 模块脚本（885 行，数据/渲染/交互/初始化）
- `descriptor-viewer.html` — 三台真实海康设备的描述符实战对比（未翻新，仍为单文件）

---

## 二、各会话完成了什么

### 第一~三会话：Phase 1-3 理论学习（32/67 知识点，48%）

| 阶段 | 内容 | 产物 |
|------|------|------|
| Phase 1 | USB 概述：拓扑、速度、总线架构 | `notes/phase1-usb-overview.md` |
| Phase 2 | 通信模型：四种传输、包结构 | `notes/phase2-communication-model.md` |
| Phase 3 | 描述符体系：逐字节解剖 | `notes/phase3-descriptors.md` |

### 第四会话：真实设备描述符实战剖析

用户提供三台海康设备 USB dump → 生成独立实战笔记 `real-device-descriptor-analysis.md`（~1300 行） + 独立 HTML `descriptor-viewer.html`。

### 第五会话：控制传输深层剖析 + SETUP 逐位 + UVC 扩展协议设计

控制传输 SETUP/DATA/STATUS 三阶段模型深层追问 → UVC XU CS_ID+SubFunc 二级命名空间协议设计。

### 第六会话：Ubuntu 实战——从零打通 XU 通信

用户在 Ubuntu 虚拟机上用热成像摄像头（HIK 2bdf:0101），从 `lsusb` 查描述符到写代码跑通第一条 XU 命令，中间踩坑 → 建立了一套完整的新设备上手方法论。

### 第七会话（本次）：usb-notes.html 全面翻新

将 `usb-notes.html` 从单文件 3,266 行全面翻新为 3 文件架构，使用 Subagent-Driven Development 流程执行。

**翻新动机**：用户要求优化前端页面，包括视觉设计（技术文档/IDE 风）、数据可视化、导航体验、代码质量、可访问性五个维度。经 brainstorming → spec → plan → implement 完整流程。

**本次会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| HTML | `usb-notes.html` | **重写**：单文件 3,266 行 → 纯结构 2,239 行。去掉 `<style>`/`<script>`，4 空格统一缩进，38/38 卡片完整迁移 |
| CSS | `usb-notes.css` | **新建**：1,153 行，10 层分层（变量→重置→排版→布局→组件→可视化→工具→响应式→减少动画→打印） |
| JS | `usb-notes.js` | **新建**：885 行，4 模块（Data→Renderers→Interaction→Init） |
| 备份 | `usb-notes-old.html` | **保留**：翻新前单文件完整备份 |
| 文档 | `docs/superpowers/specs/2026-08-02-usb-notes-redesign.md` | **新建**：设计规格 |
| 文档 | `docs/superpowers/plans/2026-08-02-usb-notes-redesign.md` | **新建**：实现计划（8 个 Task） |

**翻新要点：**
- 🎨 视觉：双色板体系（文档色板 + USB 语义色），暗色默认 IDE 风格，4px 间距网格，五级字号
- 📊 可视化：包图 tooltip 多行重设计、byte-map hover 发光、时间线胶囊形+左侧色条、Bus Hound CSS 行号
- 🧭 导航：260px 侧边栏 + 实时搜索过滤 + 48% 进度条 + rAF 节流滚动监听 + 回到顶部按钮
- ⚡ 代码质量：CSS 10 层分层、JS 4 模块、`<head>` 防闪白同步脚本阻断、meta 标签补全
- ♿ 可访问性：跳过链接、全部 ARIA 属性、`:focus-visible` 统一 focus 样式、`prefers-reduced-motion`、打印样式、移动端汉堡菜单 overlay
- 📱 响应式：≤1023px 单断点，侧边栏 → 顶部 sticky 导航条 + overlay

**翻新过程中发现并修复的 Bug：**
1. `txnDetail` 详情面板原放在 `<main>` 最底部（距时间线 700+ 行），点击展开屏幕外不可见 → 移至时间线正下方内嵌
2. 旧文件 kp-2-19 折叠区 HTML 结构断裂，Phase 3 卡片被错误嵌套其中 → 从 git 历史恢复完整结构
3. 坑 6 代码示例中 `</article>` 未转义 → 浏览器提前关闭卡片，坑 7/8 掉到卡片外 → 转义为 `&lt;/article&gt;`
4. 缺少旧 CSS 变量 `--svg-line`/`--svg-text`/`--svg-fill` 导致 SVG 图渲染异常 → 补入 CSS Layer 1
5. 移动端 overlay 为静态 HTML 副本 → JS `NavOverlay.open()` 改为 clone `.sidebar`

**本次会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 代码 | `code/xu_minimal_get.c` | **新增**：最小示例，直接读 CS_ID=0x04 协议版本（无 SubFunc） |
| 代码 | `code/xu_interactive.c` | **新增**：交互式 XU 调试工具，预置设备列表、手动选 CS_ID/SubFunc、每步展示 SETUP 8 字节包结构 |
| 笔记 | `notes/xu-new-device-setup-guide.md` | **新增**：新设备上手实操指南（8 章）——lsusb → 参数 → SETUP 包构造 → 取流流程 |
| 笔记 | `notes/phase2-communication-model.md` | 末尾新增「补充问答七：接口与端点的归属关系」——四条规则 + 真实设备数据验证 |
| HTML | `usb-notes.html` | 新增 **2.3a 接口与端点的归属关系**（四条规则 + 设备树 + libusb 对比表 + Alternate Setting 折叠区）<br>新增 **✏ 开发实战踩坑记录**（8 条折叠坑） |

**用户已彻底掌握的新概念：**

1. **lsusb 三件套**：`lsusb`（找 VID/PID）→ `sudo lsusb -v -d VID:PID`（找 bUnitID/bInterfaceNumber/bmControls）→ 参数填入代码
2. **SETUP 包 8 字节换设备只改一处**：wIndex 高字节 = XU Unit ID，其他 7 字节照抄 UVC 规范
3. **libusb_control_transfer = 完整控制传输**（不是单个事务）= SETUP + DATA + STATUS 三阶段，Bus Hound 显示为 CTL + IN/OUT 两行
4. **Interface ≠ Endpoint**：Interface 是功能分类（bmRequestType 选 Inerface），Endpoint 是数据管道（批量传输直接走端点地址）。EP0 所有 Interface 共用
5. **端点归属规则**：非 EP0 端点只属于一个 Interface，两个 Interface 不能声明同一 EndpointID，Alternate Setting 可复用端点号
6. **标准 UVC 取流**：Probe(SET_CUR→GET_CUR) → Commit → SET_INTERFACE(Standard, 不是 Class!) → libusb_bulk_transfer
7. **三种 wIndex**：VC XU = `(XU_ID<<8)|VC_IF`，VS = `VS_IF`，SET_INTERFACE = Standard bmRequestType + alt_setting
8. **bmControls 位图**：`0xFF, 0x03` = bit 0~9 置位 → CS_ID 0x01~0x0A 存在

---

## 三、当前文件结构

```
D:\CC\personal-lr-notes\CCNotes\USB\
├── HANDOFF.md                                    ← 你正在看的这份交接文档
├── usb-protocol-learning-plan.md                 ← 完整学习计划（67知识点清单）
├── usb-notes.html                                ← Phase 1-3 理论可视化（纯 HTML 结构）
├── usb-notes.css                                 ← 10 层分层样式（暗色默认 IDE 风格）
├── usb-notes.js                                  ← 4 模块脚本（数据/渲染/交互/初始化）
├── usb-notes-old.html                            ← 旧版备份（翻新前单文件版本）
├── descriptor-viewer.html                        ← 三设备描述符实战对比
├── usb设备1的描述符.txt                            ← 设备1 原始 dump
├── usb设备2的描述符.txt                            ← 设备2 原始 dump
├── usb设备3的描述符.txt                            ← 设备3 原始 dump（无 Extension Unit）
├── docs/superpowers/
│   ├── specs/
│   └── plans/
├── code/
│   ├── HIKVISION_TM76_libusb_3.c                 ← 海康 TM76 完整参考（伪彩/码流/视频流）
│   ├── uvc_xu_subfunc_framework.c                ← UVC XU 扩展协议封装库
│   ├── xu_minimal_get.c                          ← ★ 新增：最简示例（读 CS_ID=0x04）
│   └── xu_interactive.c                          ← ★ 新增：交互式 XU 调试工具
├── notes/
│   ├── phase1-usb-overview.md                    ← Phase 1
│   ├── phase2-communication-model.md             ← Phase 2（新增接口-端点关系问答）
│   ├── phase3-descriptors.md                     ← Phase 3
│   ├── real-device-descriptor-analysis.md        ← 实战手册（FAQ 10 个）
│   ├── uvc-xu-extension-protocol-design.md       ← UVC XU 扩展协议设计
│   └── xu-new-device-setup-guide.md              ← ★ 新增：新设备上手实操指南（8章）
└── .superpowers/sdd/                             ← SDD 进度账本
```

---

## 四、当前卡在哪 + 下一步计划

### 主线学习：停在 Phase 4 入口

**没有卡住。** Phase 1-3 已完成（32/67，48%）。

**下一步：Phase 4 — USB 枚举过程（12 个知识点）**

从 4.1（枚举完整时间线：插入→检测→复位→Default→Address→Configured）开始讲，一次一个知识点。

当用户说"继续"时，从这里开始。

### 副线：usb-notes.html 翻新已完成基础，待合并

**⚠️ 翻新工作在分支 `redesign/usb-notes-3file` 上，未合并到 main。**

合并前需用户在浏览器中验证：
- 双击 `usb-notes.html` → 确认侧边栏搜索、主题切换、滚动监听、包图渲染、时间线点击展开均正常
- 缩窄浏览器窗口到 <1024px → 确认移动端汉堡菜单 overlay 正常
- 确认 `descriptor-viewer.html`（单文件旧版）不受影响

验证通过后合并：
```bash
git checkout main
git merge redesign/usb-notes-3file
git branch -d redesign/usb-notes-3file
```

合并后可删除备份文件 `usb-notes-old.html`。

### 未来可能的前端优化

- `descriptor-viewer.html` 同样做 3 文件翻新
- 时间线详情面板加键盘 Escape 关闭的 focus 自动移回
- 移动端 overlay 克隆的搜索框目前是装饰（未绑定 JS），需要让克隆的搜索也能工作
- `color-mix()` 在极旧浏览器（<Chrome 111, <Safari 16.2）不支持，可视需要加 fallback

- `xu_minimal_get.c` 成功读到协议版本 `"2.0"`
- `xu_interactive.c` 可以交互式探索任意 CS_ID/SubFunc
- 新设备上手方法论已沉淀为 `xu-new-device-setup-guide.md`

用户未来可能要求：
- 在 `xu_interactive.c` 中集成 SET_CUR 写操作
- 对未知 CS_ID 做暴力扫描（遍历 bmControls 位图置位的所有 CS_ID）
- 把海康 TM76 的时间戳解析逻辑写进代码
- 实现完整的 Probe/Commit/SET_INTERFACE 取流流程
- 读取实际视频帧

---

## 五、本次会话用户建立的深层理解（关键！）

以下概念用户已彻底搞懂，不要重复讲解，但可以用做类比基础：

1. **ACK vs STATUS**：ACK = 包级确认（快递扫码），STATUS = 传输级确认（合同盖章）—— 来自第五会话
2. **SETUP 包 8 字节解析**：bmRequestType 的 D7(方向) + D6-5(字典) + D4-0(接收者) 三把钥匙决定其余 7 字节含义
3. **Bus Hound 局限性**：软件层抓包（URB 层），看不到 Token/PID/CRC/STATUS 阶段
4. **CS_ID + SubFunc 二级命名空间**：FUNC_SWITCH → GET_LEN → GET_CUR 三阶段
5. **STALL vs 错误码两层拒绝**：STALL=硬件拒绝，错误码=语义拒绝
6. **libusb_control_transfer = 完整控制传输**：一次调用 = 2~3 个总线事务，不是单个事务 — ★ 本次
7. **换新设备只改 wIndex 高字节**：XU Unit ID 从 lsusb -v 的 bUnitID 获取，其他 7 字节照抄 — ★ 本次
8. **Interface ≠ Endpoint**：Interface=功能分类（控制传输用），Endpoint=数据管道（批量传输用），EP0 共用 — ★ 本次
9. **端点归属**：非 EP0 端点只属于一个 Interface，Alternate Setting 可复用端点号 — ★ 本次
10. **三种 wIndex 填法**：VC XU(带 Unit ID)、VS(只有接口号)、SET_INTERFACE(Standard bmRT+alt) — ★ 本次
11. **bmControls 位图**：小端字节序，bit N=1 → CS_ID(N+1) 存在 — ★ 本次

---

## 六、不要踩的坑

### 关于用户和教学（继承）

1. **方案 A（自底向上）。** 不要催写代码。先讲协议理论，Phase 8 才是 libusb。
2. **MQTT 级别的精度。** 每个 byte 的每个 bit 含义都要展开。
3. **一次只讲一个知识点。** 等用户说"继续"才推进。
4. **方向永远从 Host 视角。** IN = Device→Host, OUT = Host→Device。
5. **"会用+懂原理"（B 档），不是内核驱动级。**
6. **用户喜欢类比。** MQTT、TCP/HTTP、快递/合同——用得好的比单纯列表有效 10 倍。
7. **计划文件是唯一真相源。**
8. **回答完追问后主动问"要不要保存到笔记？要不要补充到 HTML？"** —— 用户几乎总是说"要"。
9. **用户现在喜欢在 HTML 2.10 附近积累控制传输的知识。** 新增内容优先放那里。如果要加的内容自成体系，就开新章节。

### 关于 HTML 编辑（已翻新 — 2026-08-02）

10. **usb-notes 已翻新为 3 文件架构**：`usb-notes.html`（纯结构）+ `usb-notes.css`（全部样式）+ `usb-notes.js`（全部脚本）。编辑 HTML 时无需再处理 `<style>`/`<script>` 块。
10a. **全部文件统一 4 空格缩进**，不再有 Tab/空格混用问题。Edit 前无需用 `cat -A` 检查缩进。
10b. **零外部依赖原则不变**：CSS 和 JS 在同目录，`<link>` + `<script defer>` 引用，双击 HTML 即用。
15. **折叠用 `<details class="txn-fold">`。** 不要嵌套折叠区。
16. **描述符 byte-map 用 `.desc-byte-map` + `.dcell` + `.dc-bg-*` 类。**
17. **新增的 `.txn-annot-*` CSS 类**：用于在 Bus Hound 抓包下方标注 USB 总线事务。

### Ubuntu 实战踩坑（★ 第六会话）

18. **`lsusb -v` 必须加 `sudo`。** 不加只能看到基本设备信息，"Couldn't open device"意味着深层描述符树（Extension Unit 等）读不到。
19. **VID/PID 不要假设。** 即使是同厂商不同型号，PID 也可能不同。永远从 `lsusb` 确认。
20. **VC_IF_NUM 从 `bInterfaceNumber` 获取，不固定。** 同一个厂商的海康摄像头，TM76 的 VC 接口是 1，但 2bdf:0101 是 0。从 `lsusb -v` 找 `bInterfaceClass=14(Video) + bInterfaceSubClass=1(Video Control)` 的 `bInterfaceNumber`。
21. **`gcc -o output source.c` 不要写反。** `gcc -o xu_minimal_get.c -lusb-1.0` 会把源文件覆盖为空文件！`-o` 后面是输出文件名，源文件在后面。编译后检查 `wc -c source.c`。
22. **Linux 必须先 detach 内核驱动再 claim 接口。** `libusb_kernel_driver_active()` → `libusb_detach_kernel_driver()` → `libusb_claim_interface()`，释放时反向：release → attach。Windows 不需要这步（WinUSB 自动替换驱动）。
23. **运行程序也要 `sudo`（除非配了 udev 规则）。** 长期使用建议写 `/etc/udev/rules.d/99-thermal.rules`。
24. **GET_LEN 返回 0 是合法的，不一定是错误。** 可能是该 SubFunc 号不存在、无参数、或是触发型命令。先换已知 CS_ID（如 0x04）确认通道正常。
25. **libusb_control_transfer 是一次完整控制传输，不是单个事务。** 对应 Bus Hound 里的一行 CTL + 一行 IN/OUT = USB 总线上的 2~3 个事务。
26. **wIndex 填法取决于你在操作 VC 还是 VS。** VC XU 命令：`wIndex = (XU_ID<<8) | VC_IF`；VS 命令（Probe/Commit）：`wIndex = VS_IF`（没有 Unit ID！）；SET_INTERFACE：`bmRequestType=0x01(Standard)`，`wValue=altsetting`，`wIndex=VS_IF`。

### HTML 翻新踩坑（★ 第七会话新增）

27. **`<pre><code>` 里的 HTML 标签仍需转义！** 浏览器在 `<pre>` 内**仍然解析 HTML 标签**，`<pre>` 只保留空格/换行。代码示例中出现 `</article>` 会把外层卡片提前关闭。永远写成 `&lt;/article&gt;`。旧文件就有这个 bug，只是因为浏览器容错没暴露。
28. **详情面板必须放在触发元素附近。** `txnDetail` 面板放在页面底部 → 点击时间线块后 `display:block` 生效但面板在屏幕外，用户感知为"点不动"。详情面板紧贴触发元素下方（内嵌在同级 DOM 中）。
29. **移动端 overlay 要用 JS clone 侧边栏，不要写静态副本。** 静态副本不会同步搜索框、进度条、active 状态。`NavOverlay.open()` 应 `cloneNode(true)` 把 `.sidebar` 完整复制进 overlay。
30. **旧 CSS 变量迁移要全量覆盖。** 翻新时新增的 CSS 变量体系可能漏掉旧页面使用的变量（如 SVG 图的 `--svg-line`、占位区的 `.placeholder`）。翻新后用浏览器 DevTools "Styles 面板"检查所有未解析的 `var(--xxx)`。
31. **子代理（subagent）不提交代码。** 用 Subagent-Driven Development 时，每个 implementer agent 只创建/修改文件但不 `git commit`。调度者（controller）必须在每个 task 完成后手动 commit，否则所有改动堆在工作区无法分离。
32. **`task-brief` 脚本输出路径 = git repo root，不是当前子目录。** brief 文件写入 `.superpowers/sdd/` 下（git root），给 agent 的文件路径要指向正确位置。

### 关于协议知识（继承）

27. **Bus Hound 显示控制传输为两行：`CTL` = SETUP 包 8 字节，`OUT`/`IN` = DATA 阶段数据。** STATUS 阶段 Bus Hound 不显示（驱动层已合并）。
28. **数据走 OUT/IN 端点时 wLength 就是 Bus Hound 显示的那一行长度。**
29. **SETUP 包里 wValue/wIndex 含义由 bmRequestType 的 D6-5 和 D4-0 决定。** 不是"CS_ID 永远在 wValue 高字节"——那是 UVC Class 请求的惯例。

### 关于平台

30. **用户环境是 Windows + Git Bash。** Shell 用 Bash 语法，路径用正斜杠。
31. **git 仓库根目录在 `D:/CC/personal-lr-notes/`。** USB 项目在 `CCNotes/USB/` 子目录。
32. **网络需要代理（127.0.0.1:7890）。**
33. **用户也有 Ubuntu 虚拟机**（`fdl@fdl-virtual-machine`），工作目录 `~/桌面/hikusb/`。在 Ubuntu 上做实际 XU 通信开发和测试。

---

## 七、新会话启动步骤

1. **读这份交接文档** — `Read HANDOFF.md`
2. **检查 git 分支** — `git branch`。如果仍在 `redesign/usb-notes-3file` 分支上，说明翻新还未合并。确认是否继续翻新工作还是切回 `main`。
3. **读学习计划** — `Read usb-protocol-learning-plan.md`
4. **读笔记目录** — `Glob notes/*.md`
5. **确定用户意图：**
   - 如果用户说"继续" → 从 Phase 4 的 4.1（枚举完整时间线）开始讲，一次一个知识点
   - 如果用户要看理论学习/控制传输详解 → 告诉用户双击 `usb-notes.html`（3 文件架构，CSS 和 JS 在外部文件）
   - 如果用户要看描述符实战 → 告诉用户双击 `descriptor-viewer.html`
   - 如果用户要看 **新设备上手方法** → `notes/xu-new-device-setup-guide.md`（8 章实操指南）
   - 如果用户要看 UVC XU 协议设计 → `notes/uvc-xu-extension-protocol-design.md` + `code/uvc_xu_subfunc_framework.c`
   - 如果用户要调试 XU 通信 → `code/xu_interactive.c`
   - 如果用户要看最小示例 → `code/xu_minimal_get.c`
   - 如果用户要看海康 TM76 完整代码 → `code/HIKVISION_TM76_libusb_3.c`
   - 如果用户问 Bus Hound 抓包 → 指向 `usb-notes.html` 2.10 的 SETUP 8 字节折叠区和 2.20 的带注释抓包
   - 如果用户问 Interface vs Endpoint → 指向 `usb-notes.html` 2.3a
   - 如果用户问标准 UVC 取流 → `notes/xu-new-device-setup-guide.md` 第八章
   - 如果用户想继续前端翻新 → `descriptor-viewer.html` 还没翻新，或者合并 `redesign/usb-notes-3file` 分支
   - 如果用户说提交/pr/合并 → 先确认在哪个分支，验证通过后合并到 main
   - 如果用户要编辑 HTML → `usb-notes.html` 现在只是纯结构（4 空格缩进），CSS 改 `usb-notes.css`，JS 改 `usb-notes.js`
6. **如果用户不确定到哪了：**
   > "Phase 1-3 已完成（32/67，48%），暂停在 Phase 4 入口。上上次会话在 Ubuntu 跑通了第一条 XU 命令。上次会话做了 usb-notes.html 全面翻新——单文件拆成 HTML/CSS/JS 三文件，暗色 IDE 风格，补了搜索框/进度条/移动端适配/可访问性。翻新在 `redesign/usb-notes-3file` 分支上，还没合并到 main。准备好了说继续。"

---

## 八、快速参考

### SETUP 包 8 字节速查（最常用）

```
Byte 0: bmRequestType    0x21=OUT Class IF   0xA1=IN Class IF   0x01=Standard
Byte 1: bRequest         0x01=SET_CUR        0x81=GET_CUR       0x85=GET_LEN
Byte 2-3: wValue (LE)   高字节=CS_ID, 低字节=0
Byte 4-5: wIndex  (LE)  高字节=XU Unit ID, 低字节=接口号  — 换设备只改这里！
Byte 6-7: wLength (LE)  DATA 阶段字节数
```

### 三种 wIndex 填法

| 场景 | wIndex | bmRequestType |
|------|--------|--------------|
| VC XU 命令 | `(XU_ID<<8) \| VC_IF` | 0x21/0xA1 (Class) |
| VS Probe/Commit | `VS_IF` | 0x21/0xA1 (Class) |
| SET_INTERFACE 开流 | `VS_IF` | 0x01 (Standard), bReq=0x0B |

### 控制传输核心

- **三阶段模型**：SETUP(必须ACK) + DATA(可选) + STATUS(方向与DATA相反，零长度包)
- **SETUP 包 8 字节**：bmRequestType(1) + bRequest(1) + wValue(2 LE) + wIndex(2 LE) + wLength(2 LE)
- **bmRequestType 三把钥匙**：D7=方向(IN/OUT), D6-5=字典(Standard/Class/Vendor), D4-0=接收者(Device/Interface/Endpoint)
- **ACK vs STATUS**：ACK=包级"CRC对了"，STATUS=传输级"交易关闭/拒绝"
- **STATUS 是拒绝唯一入口**：SETUP 必须 ACK → 不支持的请求只能在 STATUS 回 STALL
- **批量传输无 STATUS**：ACK 就是事务终点

### 新设备上线检查清单

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU Unit ID)
□                                       bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 IF 填对              → SETUP wIndex 高/低字节
□ 用 CS_ID=0x04 GET_LEN 试通         → 验证通道 + 拿到协议版本
□ 看 bmControls 位图                 → 了解支持哪些 CS_ID
□ 选一个已知 CS_ID 走三阶段          → FUNC_SWITCH → GET_LEN → GET_CUR
```

### Ubuntu 编译运行速查

```bash
# 编译
gcc -o xu_interactive xu_interactive.c -lusb-1.0

# 查描述符
sudo lsusb -v -d 2bdf:0101 > /tmp/cam.txt
grep -n "EXTENSION_UNIT\|bUnitID\|bInterfaceNumber" /tmp/cam.txt

# 运行
sudo ./xu_interactive
```

### 前端文件速查（★ 翻新后）

| 文件 | 行数 | 做什么 |
|------|------|--------|
| `usb-notes.html` | 2,239 | 纯 HTML 结构，4 空格缩进，不含 `<style>`/`<script>` |
| `usb-notes.css` | 1,153 | 全部样式，10 层分层（Layer 1 变量, Layer 5 组件, Layer 6 可视化…） |
| `usb-notes.js` | 885 | 全部脚本，4 模块（DATA → RENDERERS → INTERACTION → INIT） |
| `usb-notes-old.html` | 3,266 | 翻新前单文件备份 |

**编辑前端时**：
- 改样式 → `usb-notes.css`，找到对应 Layer
- 改行为 → `usb-notes.js`，找到对应 manager
- 改内容 → `usb-notes.html`，现在是纯结构，不再有缩进混用问题
- CSS 变量全在 Layer 1（`:root` 暗色 / `.light` 亮色）
- 不要直接在 HTML 里加 `<style>` 或 `<script>`

### descriptor-viewer.html 关键架构

- **未翻新**，仍为单文件（`<style>` + `<script>` 内嵌），2 空格缩进
- 与 usb-notes.html 共享 35 变量 CSS 体系（翻新后 CSS 变量独立，不再共享）
- 三栏对比表 `.cmp-table`：`.row-diff` 黄色差异高亮, `.row-missing` 灰色斜体
- 侧边栏 280px Grid 布局

### MQTT 类比速查

| MQTT | USB |
|------|-----|
| CONNECT 报文 | Device Descriptor |
| Topic 权限声明 | Configuration Descriptor |
| Topic QoS 定义 | Interface Descriptor |
| TCP 连接参数 | Endpoint Descriptor |
| `$SYS/` 系统主题 | EP0（控制端点） |
| PUBLISH body | 流管道（中断/批量/等时） |
| QoS | ACK/NAK/STALL 握手机制 |
| Topic 下挂子 Topic | Interface 下挂 Endpoint |
| 多个 Topic 共用一个 TCP 连接 | 多个 Interface 共用 EP0 |
