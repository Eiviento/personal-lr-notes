# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-07-26（第二会话）
> 学习进度：21/67 知识点（31%）— 暂停在 Phase 2 结束
> Web 可视化：✅ 已完成（usb-notes.html）

---

## 一、这个项目在做什么（给完全没有上下文的新会话）

### 主线任务：USB 协议系统学习

带一位 C/C++ 应用软件工程师从零开始学 USB 协议，最终目标是构建一个 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）。

用户画像和教学约定见下方「快速参考」和「不要踩的坑」。

### 副线任务（本次会话新增）：笔记 Web 可视化

用户要求把已学的 21 个知识点的笔记做成一个**单文件离线 HTML 页面**，含交互式包结构图和 SVG 架构流程图。该页面已开发完成。

---

## 二、本次会话完成了什么

### Web 可视化页面：`usb-notes.html`

| 内容 | 数量 | 说明 |
|------|------|------|
| 知识卡片 | 21 张 | Phase 1 (5 张) + Phase 2 (16 张)，全部内容来自笔记 |
| 包结构图 | 4 张 | Token、SOF、Data、Handshake — JS 驱动 DOM 渲染，按 bit 比例着色，hover 显示 tooltip |
| SVG 架构图 | 7 张 | 版本时间轴、拓扑树、软件栈、三层模型、传输对比、传输映射、控制传输时序 |
| 暗色/亮色主题 | ✅ | CSS 变量驱动，localStorage 记住偏好 |
| 侧边栏导航 | ✅ | 8 阶段可展开，scroll spy 高亮当前卡片 |
| Phase 3-8 占位 | ✅ | 虚线卡片 + 知识点清单，待后续学习后填充 |

**零外部依赖**，双击 `usb-notes.html` 即可在浏览器打开，完全离线。

### 设计文档

```
docs/superpowers/specs/2026-07-26-usb-notes-web-design.md   ← 设计规格
docs/superpowers/plans/2026-07-26-usb-notes-web-plan.md     ← 实现计划（10 任务）
```

### 开发过程

使用 Subagent-Driven Development，10 个任务各由一个独立子代理实现 + 一个审查代理验证，最终 Opus 全分支审查通过。提交记录（共 10 个 commit，全部在 main 分支上）：

```
4b1acf4 feat: add Phase 3-8 placeholders and final polish
d291bdc feat: add Phase 2 SVG diagrams (3-layer model, transfer comparison, mapping, control sequence)
38d0204 feat: add packet diagram JS engine + render 4 diagrams + theme toggle
514b86b feat: add Phase 2 transfer type detail cards (2.10–2.16)
1d7140f feat: add Phase 2 PID/Token/Data/Handshake cards (2.6–2.9)
a2a895d feat: add Phase 2 content cards part 1 (2.1–2.5)
268ede4 feat: add Phase 1 SVG diagrams (version timeline, topology tree, software stack)
0ba1862 feat: add Phase 1 content cards (5 knowledge points)
72dff1a feat: add navigation sidebar with 8 phases and scroll spy
dbbaf25 feat: scaffold HTML with CSS foundation and theme system
```

---

## 三、当前文件结构

```
D:\CC\personal-lr-notes\CCNotes\USB\
├── HANDOFF.md                          ← 你正在看的这份交接文档
├── usb-protocol-learning-plan.md       ← 完整学习计划（67知识点清单）
├── usb-notes.html                      ← 🆕 Web 可视化页面（本会话产出）
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-07-26-usb-notes-web-design.md   ← 🆕 可视化设计规格
│       └── plans/
│           └── 2026-07-26-usb-notes-web-plan.md     ← 🆕 可视化实现计划
├── notes/
│   ├── phase1-usb-overview.md          ← 第一阶段笔记（完整，220行）
│   └── phase2-communication-model.md   ← 第二阶段笔记（完整，708行）
└── .superpowers/
    └── sdd/
        ├── progress.md                 ← SDD 进度账本
        ├── task-*-brief.md             ← 各任务 Brief
        ├── task-*-report.md            ← 各任务 Report
        └── review-*.diff               ← 各任务 Review Package
```

---

## 四、当前卡在哪

**主线（USB 学习）：没有卡住。** Phase 1 和 Phase 2 已完成（21/67），正常暂停在进入 Phase 3 之前。

**下一站：Phase 3 — USB 描述符体系逐字节解剖（11 个知识点）**

用户说"继续"时应该从 3.1（描述符层级关系）开始讲。

**副线（Web 可视化）：已完成，无需继续。**

### 后续更新 usb-notes.html 的方式

当用户学完 Phase 3（或后续阶段）后：
1. 将占位符 `<div class="placeholder">` 替换为实际的知识卡片 `<article class="card" id="kp-X-Y">`
2. 更新侧边栏对应阶段的 `badge`（从 `phase-current` / `phase-pending` 改为 `phase-done`）
3. 新学到的包结构（如 Device Descriptor 18 字节）添加到 JS 的 `PACKET_DATA` 数组中，自动渲染
4. 新的架构图（如描述符层级树、枚举时间线）以 `<svg>` 内联到对应卡片

---

## 五、不要踩的坑

### 关于用户和教学（主线任务）

1. **用户选的是方案 A（自底向上）。** 不要催他写代码。先把协议理论讲完，最后才是 libusb（Phase 8）。
2. **用户需要 MQTT 级别的精度。** 每个 byte 的每个 bit 含义都要展开。含糊带过他会追问。
3. **一次只讲一个知识点。** 每节等用户说"继续"才推进。不要一次塞多个。
4. **方向永远从 Host 视角。** IN = Device→Host, OUT = Host→Device。用户容易搞反，需持续提醒。
5. **"会用+懂原理"（B档），不是内核驱动级别（C档）。** 不要跳 rabbit hole。
6. **用户喜欢类比。** MQTT 类比对他有效。
7. **计划文件是唯一真相源。** 用户要求调整计划 → 先更新 `usb-protocol-learning-plan.md` 再执行。

### 关于 Web 可视化页面（副线任务）

8. **usb-notes.html 是手动合并的单文件。** 不要尝试拆成多个文件或用构建工具。修改时直接编辑这个文件。
9. **所有颜色都在 CSS 变量中。** 包图的 6 色、主题的亮/暗色对都在 `:root` 和 `.dark` 里。不要硬编码色值到 SVG 或 JS 中。
10. **包图数据定义在 `PACKET_DATA` 数组中。** 新增包图只需 push 一个对象，不用改 `renderPacket()` 函数。
11. **SVG 使用 `var(--svg-line)` 等 CSS 变量。** 这些变量由主题系统自动切换，手写 SVG 时直接用 `var()` 引用。
12. **文件用 `Write` 工具编辑。** 不要用 Bash cat/echo/sed，HTML 中大量特殊字符容易转义出错。

### 关于平台和工具

13. **用户环境是 Windows + Git Bash。** Shell 用 Bash 语法，路径用正斜杠。
14. **git 仓库根目录在 `D:/CC/personal-lr-notes/`。** USB 项目是子目录 `CCNotes/USB/`。
15. **`.superpowers/sdd/` 目录在 git 仓库根目录下**，不在 USB 子目录下。进度账本、任务 Brief/Report 都在那里。

---

## 六、新会话启动步骤

当新会话被打开后，按以下顺序操作：

1. **读这份交接文档** — `Read HANDOFF.md`（你正在读）
2. **读学习计划** — `Read usb-protocol-learning-plan.md`，了解 67 知识点全景
3. **读笔记目录** — `Glob notes/*.md`，了解已讲过的内容
4. **如果用户说"继续"：**
   - 从 Phase 3 的 3.1（描述符层级关系）开始讲
   - 一次一个知识点，等用户说"继续"
5. **如果用户要看可视化页面：**
   - 告诉用户 `usb-notes.html` 已就绪，双击即可在浏览器打开
   - 学完 Phase 3 后可以更新该文件，把描述符的内容和包图加进去
6. **如果用户不确定到哪了：**
   - "Phase 1 和 Phase 2 已完成（21/67），接下来是 Phase 3 描述符体系，准备好了说继续"

---

## 七、快速参考

### USB 核心概念速查

- **PID 编码**：高 4 位 = ~低 4 位（按位取反），低 2 位分类：00=SPECIAL, 01=TOKEN, 10=HANDSHAKE, 11=DATA
- **Token 包**：SYNC(8) + PID(8) + ADDR(7) + ENDP(4) + CRC5(5) + EOP
- **Data 包**：SYNC + PID + DATA(0~1024B) + CRC16(16) + EOP
- **Handshake 包**：SYNC + PID + EOP（USB 最短的包，19 bit）
- **控制传输** = SETUP + DATA(可选) + STATUS（STATUS 方向与 DATA 相反）
- **四种传输**：控制(EP0) / 中断(bInterval 保证延迟) / 批量(吃剩饭，无带宽保证) / 等时(无握手，实时优先)
- **ADDR**：7 bit → 128 地址，0x00 保留 → 127 设备上限
- **HS Chirp**：HS 设备先冒充 FS(D+上拉)，然后通过 Chirp K/J 协商升级到 480Mbps
- **Split Transaction**：HS Hub 用 SSPLIT/CSPLIT 给后面的 FS/LS 设备做速度翻译
- **帧结构**：FS 1ms/帧，HS 125μs/微帧，Frame Number 0~2047 回卷

### usb-notes.html 关键架构

- **CSS**（`<style>`）：变量在 `:root`（亮色）和 `.dark`（暗色），布局用 CSS Grid（侧边栏 280px + 主区域 1fr）
- **HTML**（`<nav>` + `<main>`）：侧边栏用 `<details>/<summary>`，主内容用 `<article class="card" id="kp-X-Y">`
- **JS**（`<script>`）：`PACKET_DATA` 数组 + `renderPacket()` 函数 + 主题切换 + scroll spy
- **包图颜色**：sync-pid=蓝, addr=青, data=橙, crc=紫, eop=灰, frame=绿

### MQTT 类比速查（用户熟悉的参照系）

| MQTT | USB |
|------|-----|
| Client 可随时 PUBLISH | Device 只能被动应答（Host 中心化） |
| `$SYS/` 系统主题 | EP0（管理通道） |
| CONNECT/CONNACK | 消息管道（控制传输） |
| PUBLISH body | 流管道（中断/批量/等时） |
| QoS | ACK/NAK/STALL 握手机制 |
| Topic/Payload | 功能层 |
| MQTT 协议层 | USB 设备层 |
| TCP/IP | 总线接口层 |
