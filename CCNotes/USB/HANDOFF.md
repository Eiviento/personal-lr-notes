# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-08-01（第四会话）
> 主线学习进度：32/67 知识点（48%）— 暂停在 Phase 4 入口
> 副线任务：✅ 已完成 — 新增「实战描述符剖析」笔记 + 独立可视化页面

---

## 一、这个项目在做什么（给完全没有上下文的新会话）

### 主线任务：USB 协议系统学习

带一位 C/C++ 应用软件工程师从零开始学 USB 协议，最终目标是构建一个 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）。

### 副线任务：笔记 Web 可视化（本次会话新增）

把学习笔记做成**单文件离线 HTML 页面**，含交互式包结构图、描述符 byte-map、架构图。零外部依赖，双击打开。

现有两个独立 HTML 页面：
- `usb-notes.html` — Phase 1-3 理论知识可视化（描述符 byte-map、包结构、帧时间线）
- `descriptor-viewer.html` — **本次新增**，三台真实设备的描述符实战对比（标准 byte-map + 三栏设备对照表 + UVC 类专用剖析）

---

## 二、过去会话完成了什么

### 第一~三会话：Phase 1-3 理论学习（32/67 知识点）

| 阶段 | 内容 | 产物 |
|------|------|------|
| Phase 1 | USB 概述：拓扑、速度、总线架构 | `notes/phase1-usb-overview.md` |
| Phase 2 | 通信模型：包结构、四种传输、Token/Data/Handshake | `notes/phase2-communication-model.md` |
| Phase 3 | 描述符体系：Device/Config/IAD/Interface/Endpoint 逐字节 | `notes/phase3-descriptors.md` |

### 第四会话（本次）：真实设备描述符实战剖析

用户提供了三台海康 USB 设备的描述符 dump（用 USB Device Tree Viewer 抓取），要求做一份独立笔记 + 独立 HTML 可视化页面。

**产出：**

| 文件 | 行数 | 说明 |
|------|------|------|
| `notes/real-device-descriptor-analysis.md` | ~1240 | 5 章 + 3 附录实战手册 |
| `descriptor-viewer.html` | ~1290 | 单文件交互式对比查看器 |

**三台设备：**

| 设备 | VID:PID | 类型 | 数据完整度 |
|------|---------|------|-----------|
| 设备1 | 0x2BDF:0x0101 | HikCamera (UVC 1.10) | 完整 USB dump + UVC 类专用 |
| 设备2 | 0x2BDF:0x0101 | HikCamera 同型号第二台 | 完整 + Device Qualifier + Other Speed Config |
| 设备3 | 0x2BDF:0x028A | 2K USB Camera + Audio | 仅 KS 层数据，无原始 USB 描述符 |

**笔记内容（`real-device-descriptor-analysis.md`）：**
- 第 1 章：描述符是什么 — TLV 铁律、获取流程、层级树
- 第 2 章：标准描述符逐字节 — Device(18B)/Config(9B)/IAD(8B)/Interface(9B×2)/Endpoint(7B×2)，每种含标准定义表 + ASCII byte-map + 三设备对照表 + 关键字段深入
- 第 3 章：类专用描述符机制 — 0x24/0x25 分发原理、UVC VC Header 逐字节拆解、UVC 拓扑图
- 第 4 章：综合实战 — 设备1 433B 全链追踪、设备1 vs 设备2 差异分析（Device Qualifier / Other Speed Config）、设备3 KS 反推
- 第 5 章：FAQ — 7 个经典问题
- 附录 A/B/C — 三台设备原始数据

**HTML 页面组件（`descriptor-viewer.html`）：**
- 侧边栏导航树 + 暗色/亮色主题切换（localStorage 持久化）
- 每种标准描述符：byte-map 色块图 + 三栏设备对照表（差异行黄色高亮、缺失数据灰色斜体）
- UVC 类专用：分发机制表、VC Header byte-map、拓扑图、子类型码速查
- 综合实战：433B 链追踪 pre 块、设备差异表、设备3 推断
- 7 个折叠 FAQ
- JS：scroll spy 自动高亮当前章节、主题切换

### 提交记录（12 commits，第四会话）

```
8e23999 fix: address final review issues — remove dead code, fix reference leak, add null guards
426cabf chore: final verification — cross-check notes vs HTML consistency
c16cdd1 feat: add JS interactivity — theme toggle, scroll spy, device tabs
3c60498 feat: add class-specific descriptors, comprehensive analysis, FAQ, and device 3 inference sections
5ba5336 fix: correct VC Header and H264 GUID hex values, UVC subtype references
d2d6408 feat: add Config, IAD, Interface, and Endpoint descriptor sections
7174d40 feat: add Device Descriptor section with byte-map, comparison table, and foldable explanations
8a46436 feat: add sidebar navigation tree with device color legend
3a460cd feat: add descriptor-viewer HTML skeleton with CSS design system
ee2f204 docs: add real-device descriptor analysis notes (5 chapters + appendices)
dd55c0c docs: add real-device descriptor analysis notes (5 chapters + appendices)
5ab582c docs: add real-device descriptor analysis design spec
2f9e637 docs: add implementation plan for real-device descriptor analysis
```

---

## 三、当前文件结构

```
D:\CC\personal-lr-notes\CCNotes\USB\
├── HANDOFF.md                                    ← 你正在看的这份交接文档
├── usb-protocol-learning-plan.md                 ← 完整学习计划（67知识点清单）
├── usb-notes.html                                ← Phase 1-3 理论可视化（2522行）
├── descriptor-viewer.html                        ← ★ 新增：三设备描述符实战对比（~1290行）
├── usb设备1的描述符.txt                            ← 设备1 原始 dump
├── usb设备2的描述符.txt                            ← 设备2 原始 dump
├── usb设备3的描述符.txt                            ← 设备3 原始 dump（KS数据）
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   ├── 2026-07-26-usb-notes-web-design.md
│       │   └── 2026-08-01-real-device-descriptor-analysis-design.md  ← ★ 新增
│       └── plans/
│           ├── 2026-07-26-usb-notes-web-plan.md
│           └── 2026-08-01-real-device-descriptor-analysis-plan.md    ← ★ 新增
├── notes/
│   ├── phase1-usb-overview.md                    ← Phase 1（219行）
│   ├── phase2-communication-model.md             ← Phase 2（1048行）
│   ├── phase3-descriptors.md                     ← Phase 3（1242行）
│   └── real-device-descriptor-analysis.md        ← ★ 新增：实战手册（~1240行）
└── .superpowers/
    └── sdd/                                      ← SDD 进度账本
```

---

## 四、当前卡在哪 + 下一步计划

### 主线学习：停在 Phase 4 入口

**没有卡住。** Phase 3 理论已完成（32/67，48%）。

**下一步：Phase 4 — USB 枚举过程逐包逐事务追踪（12 个知识点）**

从 4.1（枚举完整时间线：插入→检测→复位→Default→Address→Configured）开始讲。

当用户说"继续"时，从这里开始。

### 副线：描述符实战已独立完成

`descriptor-viewer.html` 和 `real-device-descriptor-analysis.md` 是独立产物，不依赖主线进度。如果用户想看描述符实战，直接双击 `descriptor-viewer.html`。

---

## 五、不要踩的坑

### 关于用户和教学（继承自之前会话）

1. **用户选的是方案 A（自底向上）。** 不要催他写代码。先把协议理论讲完，最后才是 libusb（Phase 8）。
2. **用户需要 MQTT 级别的精度。** 每个 byte 的每个 bit 含义都要展开。含糊带过他会追问。
3. **一次只讲一个知识点。** 每节等用户说"继续"才推进。不要一次塞多个。
4. **方向永远从 Host 视角。** IN = Device→Host, OUT = Host→Device。
5. **"会用+懂原理"（B档），不是内核驱动级别（C档）。** 不要跳 rabbit hole。
6. **用户喜欢类比。** MQTT 类比对他有效。用得好他会说"懂了"。
7. **计划文件是唯一真相源。** 用户要求调整计划 → 先更新计划文件再执行。
8. **用户会在学习过程中插入追问。** 回答完后主动问"要不要保存到笔记？要不要补充到 HTML？"
9. **讲完一个阶段后，用户可能要求把所有内容保存到笔记 + 更新 HTML。** 笔记用 .md，HTML 用 Edit/Write。
10. **HTML 的 Edit 匹配对空格/制表符敏感。** Edit 报 "not found" 时，用 Grep 找到确切行内容再匹配。

### 关于 HTML 页面（继承 + 新增）

11. **这两个 HTML 是独立文件。** `usb-notes.html` 和 `descriptor-viewer.html` 互不依赖，不要改动错文件。
12. **两个 HTML 共享同一套 CSS 变量体系**（`:root` + `.dark` 双主题，35 个变量）。新增变量必须两个块都加。
13. **描述符 byte-map 用 `.desc-byte-map` + `.dcell` + `.dc-bg-*` 类。** 15 个 bg 颜色类在两个 HTML 中完全一致。flex 比例 = 字段字节数。
14. **折叠内容用 `<details class="txn-fold">`。** 不要嵌套折叠区。
15. **单文件原则：零外部依赖。** CSS 在 `<style>`，JS 在 `<script>`，字体用系统栈。
16. **LF 换行符，2空格缩进**（`descriptor-viewer.html`）或**制表符缩进**（`usb-notes.html`），不要混用。
17. **文件用 `Edit` 工具编辑，不要用 Bash cat/sed。** 大段替换可先用 `Write` 写临时文件再 `Bash` 拼接。

### 关于 SDD 工作流（本次新增）

18. **用 `superpowers:brainstorming` 先澄清需求再动手。** 用户给出了材料但没说清楚方向 → 问清楚再设计。
19. **用 `superpowers:writing-plans` 写实现计划。** 8 个 Task 每个都有独立 brief + report + review。
20. **用 `superpowers:subagent-driven-development` 执行计划。** 一个 Task 一个子代理，每次 commit 独立。
21. **子代理调度用文件传递上下文，不要全粘贴到 prompt。** 用 `task-brief` / `review-package` 脚本生成文件，传递文件路径。
22. **子代理的 report 会覆盖同路径的旧 report。** 不同 plan 的 report 共享 `.superpowers/sdd/` 目录，可能读到上次的残留。
23. **第一版往往有 hex 错误。** 描述符的 LE 字节序容易写错（如 `6C DC` 写成 `6C 2C`），实现后必须让子代理交叉验证源文件。
24. **最终 review 几乎总能发现 dead code。** spec 里列了但实际没用到的组件（如 device tabs），review 会指出——删掉就好。

### 关于平台

25. **用户环境是 Windows + Git Bash。** Shell 用 Bash 语法，路径用正斜杠。
26. **git 仓库根目录在 `D:/CC/personal-lr-notes/`。** USB 项目在 `CCNotes/USB/` 子目录。
27. **Git 配置了 autocrlf 警告。** 提交时 blob 是 LF，checkout 时可能转 CRLF——不要慌，文件实际是 LF。
28. **网络需要代理（127.0.0.1:7890）。** `git push` 需要代理可用。

---

## 六、新会话启动步骤

1. **读这份交接文档** — `Read HANDOFF.md`
2. **读学习计划** — `Read usb-protocol-learning-plan.md`
3. **读笔记目录** — `Glob notes/*.md`
4. **确定用户意图：**
   - 如果用户说"继续" → 从 Phase 4 的 4.1（枚举完整时间线）开始讲，一次一个知识点
   - 如果用户要看描述符实战 → 告诉用户双击 `descriptor-viewer.html`
   - 如果用户要看理论学习 → 告诉用户双击 `usb-notes.html`
5. **如果用户不确定到哪了：**
   > "Phase 1-3 已完成（32/67），暂停在 Phase 4 入口。本会话新增了三台真实设备（2×HikCamera + 1×2K Camera+Audio）的描述符实战剖析笔记和独立 HTML 页面。准备好了说继续。"

---

## 七、快速参考

### USB 核心概念速查（Phase 1-2）

- **PID 编码**：高 4 位 = ~低 4 位（按位取反），低 2 位分类：00=SPECIAL, 01=TOKEN, 10=HANDSHAKE, 11=DATA
- **Token 包**：SYNC(8) + PID(8) + ADDR(7) + ENDP(4) + CRC5(5) + EOP = 35 bit
- **Data 包**：SYNC + PID + DATA(0~1024B) + CRC16 + EOP
- **Handshake 包**：SYNC + PID + EOP = 19 bit（USB 最短的包）
- **SOF 包**：SYNC + PID(0xA5) + Frame#(11) + CRC5 + EOP（广播，无地址）
- **SETUP vs SOF**：SETUP 点对点(含 ADDR+ENDP)，SOF 广播(ADDR+ENDP 挪用为帧号)
- **控制传输** = SETUP(固定DATA0) + DATA(可选,DATA1起) + STATUS(方向相反)
- **四种传输**：控制/中断(bInterval)/批量(吃剩饭)/等时(无握手)
- **ADDR**：7 bit → 127 设备上限（不含 0x00）
- **帧**：FS 1ms，HS 125μs×8 微帧，Frame# 0~2047 回卷
- **SETUP 必须 ACK**：EP0 独立硬件缓冲 + SETUP=状态机清零信号 + 不可重试语义

### Phase 3 核心概念速查

- **描述符前 2 字节铁律**：bLength + bDescriptorType（TLV 的 L+V）
- **Device Descriptor**：18B，byte 7=bMaxPacketSize0, byte 8-11=VID+PID(LE)
- **bcdUSB**：BCD nibble 编码，0x0200=USB 2.0，不能直接当整数比较
- **Configuration Descriptor**：9B，wTotalLength=整个链总长，bMaxPower 单位 2mA
- **Interface Descriptor**：9B，三级分类码(Class/SubClass/Protocol)决定驱动匹配
- **Endpoint Descriptor**：7B，byte 2=地址+方向，byte 3=传输类型+等时同步模式
- **bInterval**：FS 中断=ms 线性，HS 中断=微帧指数，HS 等时=微帧线性
- **String Descriptor**：UTF-16LE，String#0=语言列表
- **Device Qualifier**：10B，HS→FS 降级备胎
- **BOS**：TLV 扩展容器，LPM/SuperSpeed/ContainerID 等 Capability
- **Alternate Setting**：同一接口的多形态(如 UVC Alt0=零带宽, Alt1=480p, Alt2=720p)
- **IAD (0x0B)**：绑定多个接口为一个功能(VC+VS=摄像头)
- **类专用描述符 0x24**：CDC/UVC/Audio 共用，靠 bInterfaceClass 上下文区分

### 实战描述符新增概念（第四会话）

- **bDeviceClass=0xEF + IAD**：复合设备的现代最佳实践。Device 层面声明 0xEF(Misc)，实际功能分类放在 IAD
- **bmAttributes bit7=1**：USB spec 历史遗留，所有设备必须设置
- **wTotalLength**：告诉 Host 一次性读多少字节——Config 自身 9B 但链总长可达数百字节
- **UVC 拓扑**：Input Terminal → Processing Unit → Extension Unit → Output Terminal → VS Formats/Frames
- **HS vs FS Other Speed**：Device Qualifier + Other Speed Config 描述 HS 设备降级到 FS 时的参数（wMaxPacketSize 512→64）
- **UVC Extension Unit**：vendor-specific controls 的容器——标准 UVC controls 全 0 时，实际控制走 XU

### descriptor-viewer.html 关键架构

- **CSS**：与 usb-notes.html 共享 35 变量体系，额外新增 `--dev1/2/3-accent`（紫/青/橙）和 `--diff-highlight`
- **布局**：Grid sidebar 280px + main 1fr，响应式 @media 768px 折叠
- **cmp-table**：三栏对比表，`.col-dev1/2/3` 带彩色左边框，`.row-diff` 黄色差异高亮，`.row-missing` 灰色斜体
- **导航**：6 个 `<details class="nav-section">` + 15 个 `<a class="nav-link">`
- **JS**：主题切换(localStorage)、scroll spy 自动高亮当前 nav-link、smooth scroll
- **删掉的组件**：device tabs（CSS+JS 已移除——没有 .dev-tabs 标记，是 dead code）

### MQTT 类比速查

| MQTT | USB |
|------|-----|
| Client 可随时 PUBLISH | Device 只能被动应答（Host 中心化）|
| CONNECT 报文 | Device Descriptor（设备身份）|
| Topic 权限声明 | Configuration Descriptor |
| Topic QoS 定义 | Interface Descriptor |
| TCP 连接参数 | Endpoint Descriptor（门牌号+方向+带宽）|
| `$SYS/` 系统主题 | EP0（管理通道）|
| PUBLISH body | 流管道（中断/批量/等时）|
| QoS | ACK/NAK/STALL 握手机制 |
| Fixed Header byte 0 | bLength+bDescriptorType（决定整体解析方式）|
