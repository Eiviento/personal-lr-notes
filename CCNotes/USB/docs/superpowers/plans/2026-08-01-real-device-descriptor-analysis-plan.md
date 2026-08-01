# Real-Device Descriptor Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two standalone files — a comprehensive markdown notes file analyzing USB descriptors through three real devices, and an interactive HTML page for visualizing each descriptor byte-by-byte with cross-device comparison.

**Architecture:** Two independent files created from scratch. The notes (`real-device-descriptor-analysis.md`) is pure markdown content. The HTML page (`descriptor-viewer.html`) is a single-file interactive viewer reusing the CSS design system from `usb-notes.html` (CSS variables, byte-map grid, foldable cards) but as a standalone page with no dependency on the existing HTML.

**Tech Stack:** Markdown, HTML5, CSS3 (Grid, custom properties), vanilla JavaScript, no external dependencies.

## Global Constraints

- HTML 单文件，零外部依赖（CSS 在 `<style>`，JS 在 `<script>`）
- 笔记用 .md 格式，中文撰写
- 颜色变量 `:root` 和 `.dark` 两个块都必须加
- 设备 3 缺失字段标注为 "无数据" 而非留空
- LF 换行符，制表符缩进
- 不修改 `usb-notes.html`、`notes/phase3-descriptors.md`、`HANDOFF.md`

---

### Task 1: Create notes file — all 5 chapters + 3 appendices

**Files:**
- Create: `notes/real-device-descriptor-analysis.md`

**Interfaces:**
- Consumes: `usb设备1的描述符.txt`, `usb设备2的描述符.txt`, `usb设备3的描述符.txt` (source data)
- Produces: Complete standalone markdown notes file

- [ ] **Step 1: Write the complete notes file**

Write `notes/real-device-descriptor-analysis.md` with the following structure. The file is ~1500-2000 lines covering all 5 chapters + 3 appendices.

**第 1 章：描述符是什么**
- TLV 铁律（bLength + bDescriptorType 前两字节）
- 描述符获取流程：GetDescriptor(Device) → GetDescriptor(Config) → 完整链一次性返回
- ASCII art 层级树图展示 Device → Config → IAD → Interface 0 (VC) / Interface 1 (VS) → Endpoint
- 三台设备速览表（VID/PID、类型、接口数、描述符链总长、数据完整度）

**第 2 章：标准描述符逐字节** — 每种描述符 4 个小节：
2.1 Device Descriptor (18 bytes)
  - 标准定义表：offset/字段名/长度/含义 全 14 字段
  - ASCII byte-map 色块图（标明每个字节的颜色分类）
  - 三设备对照表：字段名 | 标准要求 | 设备1 (HikCamera #1) | 设备2 (HikCamera #2) | 设备3 (2K Camera) | 解读
  - 关键字段深入：bDeviceClass=0xEF(Miscellaneous) 为什么不是 0x0E(Video)——引出 IAD、bMaxPacketSize0=0x40=64B 是 HS EP0 标准值
2.2 Configuration Descriptor (9 bytes)
  - 标准定义表 + byte-map + 三设备对照表
  - 关键字段：wTotalLength=0x01B1(433B) 表示整个配置描述符链总长、bmAttributes bit7=1 是 USB spec 强制要求、MaxPower 单位 2mA
2.3 IAD Descriptor (8 bytes)
  - 标准定义表 + byte-map + 三设备对照表
  - 关键字段：bFirstInterface+bInterfaceCount 绑定接口范围、bFunctionClass=0x0E(Video) 这才是真正的功能分类
2.4 Interface Descriptor — VC (9 bytes) + VS (9 bytes)
  - 两张标准定义表 + 两张 byte-map
  - 关键字段：bInterfaceClass=0x0E/SubClass=0x01→VC, 0x02→VS、bAlternateSetting=0x00(默认)、bNumEndpoints
2.5 Endpoint Descriptor — Interrupt IN (7 bytes) + Bulk IN (7 bytes)
  - 两张标准定义表 + 两张 byte-map
  - 关键字段：bEndpointAddress bit7=方向(1=IN)、bmAttributes 低2位=传输类型(11=Interrupt, 10=Bulk)、wMaxPacketSize bit10..0=包大小 bit12..11=额外事务数、bInterval 在 HS 下的计算公式

**第 3 章：类专用描述符机制**
- 3.1 0x24/0x25 的分发原理图：同一个 bDescriptorType，靠 bInterfaceClass 区分含义
- 3.2 用设备1的 VC Header Descriptor (13 bytes) 做逐字节拆解示例（bcdUVC=0x0110, dwClockFreq=48MHz, bInCollection=1）
- 3.3 UVC 描述符拓扑图：Input Terminal(ITT_CAMERA) → Processing Unit → Extension Unit → Output Terminal(TT_STREAMING) → VS Formats/Frames
- 3.4 UVC 描述符类型码速查表（bDescriptorSubtype 1~13 对应含义）
- 3.5 USB Audio Class 简要提及（设备3 从 KS 数据可见音频接口）

**第 4 章：综合实战**
- 4.1 设备1 完整 433 字节描述符链追踪 —— 从 Device Descriptor 第一个字节到最后一个 Frame Descriptor，用 ASCII art 画出完整的描述符链顺序图，标注每个描述符的起始偏移和长度
- 4.2 设备1 vs 设备2 差异分析 —— 表格对比所有字段差异：Serial Number、Device Address、设备2 有 Device Qualifier + Other Speed Configuration（HS→FS 降级备胎机制，wMaxPacketSize 512→64 的原因）
- 4.3 设备3 从 KS 数据反推 —— 看到 MI_00(Camera)+MI_02(Audio) 推断描述符结构，最可能是 IAD 绑定 VC+VS+AC+AS 四接口组合，视频 2560×1440@30fps MJPEG 需要等时端点保证带宽

**第 5 章：FAQ**
- Q1: 为什么 bDeviceClass 不直接写 0x0E (Video)？
- Q2: Alternate Setting 在描述符里怎么体现？
- Q3: bMaxPacketSize0 对 HS 设备为什么固定 64 字节？
- Q4: Device Qualifier 什么情况下 Host 会请求？
- Q5: IAD 和 Interface Descriptor 里的 Class 有什么不同？
- Q6: UVC Extension Unit 的 15 个 vendor-specific controls 是干什么的？
- Q7: 设备1&2 的 bmControls 全是 0，怎么控制摄像头？

**附录 A**: 设备1 完整原始 dump (精简格式，去掉行号)
**附录 B**: 设备2 完整原始 dump (精简格式，去掉行号)
**附录 C**: 设备3 KS 数据摘要（主要视频格式表 + 音频参数）

- [ ] **Step 2: Verify notes are self-contained and readable**

Open `notes/real-device-descriptor-analysis.md` and check:
- All ASCII art renders correctly in monospace
- All tables have consistent column alignment
- All HEX values have `0x` prefix
- Device 3 missing data marked as "无数据" not blank
- No broken internal references

- [ ] **Step 3: Commit**

```bash
git add notes/real-device-descriptor-analysis.md
git commit -m "docs: add real-device descriptor analysis notes (5 chapters + appendices)"
```

---

### Task 2: Create HTML skeleton — CSS variables, layout, typography

**Files:**
- Create: `descriptor-viewer.html`

**Interfaces:**
- Produces: Complete CSS design system with `:root` + `.dark` variable blocks, Grid layout (sidebar 280px + main 1fr), all reusable component styles

- [ ] **Step 1: Write HTML boilerplate + full CSS**

Create `descriptor-viewer.html` with DOCTYPE, meta charset UTF-8, viewport meta, title "USB 描述符实战剖析 — 三设备对比". All CSS goes in a single `<style>` tag.

CSS structure to write (all in one file):

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>USB 描述符实战剖析 — 三设备对比</title>
<style>
/* ===== CSS Variables & Theme ===== */
:root {
  /* Base — same palette as usb-notes.html */
  --bg: #ffffff;
  --card-bg: #f8f9fa;
  --text: #212529;
  --text-muted: #868e96;
  --code-bg: #f1f3f5;
  --border: #dee2e6;
  --sidebar-bg: #f8f9fa;
  --sidebar-text: #212529;
  --heading: #1a1b1e;
  --color-sync-pid: #1e90ff;
  --color-addr: #20c997;
  --color-data: #ffa94d;
  --color-crc: #845ef7;
  --color-eop: #adb5bd;
  --color-frame: #51cf66;
  --svg-line: #495057;
  --svg-text: #212529;
  --svg-fill: #f8f9fa;
  --table-stripe: #f1f3f5;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --card-hover-shadow: 0 2px 8px rgba(0,0,0,0.12);
  --prose-max-width: 780px;
  --txn-control: #845ef7;
  --txn-interrupt: #ff6b6b;
  --txn-bulk: #20c997;
  --txn-isoch: #51cf66;
  --txn-sof: #adb5bd;
  --txn-nak: #ffa94d;
  /* New variables for this page */
  --diff-highlight: #fff3bf;
  --diff-highlight-dark: #3d3520;
  --missing: #adb5bd;
  --missing-dark: #6c757d;
  --dev1-accent: #845ef7;
  --dev2-accent: #20c997;
  --dev3-accent: #ffa94d;
}

.dark {
  --bg: #1a1b1e;
  --card-bg: #2c2e33;
  --text: #e9ecef;
  --text-muted: #868e96;
  --code-bg: #25262b;
  --border: #495057;
  --sidebar-bg: #212529;
  --sidebar-text: #e9ecef;
  --heading: #f8f9fa;
  --color-sync-pid: #8ab4f8;
  --color-addr: #63e6be;
  --color-data: #ffc078;
  --color-crc: #b197fc;
  --color-eop: #dee2e6;
  --color-frame: #69db7c;
  --svg-line: #adb5bd;
  --svg-text: #e9ecef;
  --svg-fill: #2c2e33;
  --table-stripe: #25262b;
  --shadow: 0 1px 3px rgba(0,0,0,0.3);
  --card-hover-shadow: 0 2px 8px rgba(0,0,0,0.5);
  --txn-control: #b197fc;
  --txn-interrupt: #ff8787;
  --txn-bulk: #63e6be;
  --txn-isoch: #69db7c;
  --txn-sof: #dee2e6;
  --txn-nak: #ffc078;
  --diff-highlight: #3d3520;
  --diff-highlight-dark: #3d3520;
  --missing: #6c757d;
  --missing-dark: #6c757d;
  --dev1-accent: #b197fc;
  --dev2-accent: #63e6be;
  --dev3-accent: #ffc078;
}

/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; scroll-padding-top: 20px; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
  font-size: 15px; line-height: 1.7; color: var(--text);
  background: var(--bg);
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}

/* ===== Sidebar ===== */
.sidebar {
  position: fixed; top: 0; left: 0; width: 280px; height: 100vh;
  background: var(--sidebar-bg); border-right: 1px solid var(--border);
  overflow-y: auto; padding: 20px 16px; z-index: 10;
}
.sidebar h2 { font-size: 16px; margin-bottom: 16px; color: var(--heading); }
.sidebar .nav-section { margin-bottom: 12px; }
.sidebar .nav-section > summary {
  cursor: pointer; font-weight: 600; font-size: 14px; padding: 4px 0;
  color: var(--heading); list-style: none;
  display: flex; align-items: center; gap: 6px;
}
.sidebar .nav-section > summary::-webkit-details-marker { display: none; }
.sidebar .nav-section > summary::before {
  content: '▸'; font-size: 10px; transition: transform 0.2s;
  display: inline-block; width: 12px;
}
.sidebar .nav-section[open] > summary::before { transform: rotate(90deg); }
.sidebar .nav-link {
  display: block; padding: 3px 0 3px 24px; font-size: 13px;
  color: var(--text-muted); text-decoration: none; border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}
.sidebar .nav-link:hover, .sidebar .nav-link.active {
  color: var(--color-sync-pid); background: rgba(30,144,255,0.08);
}
.sidebar .dev-legend { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); }
.sidebar .dev-legend .dev-dot {
  display: flex; align-items: center; gap: 8px; font-size: 12px; margin-bottom: 6px;
}
.sidebar .dev-legend .dev-dot .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* Theme toggle */
.theme-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border: 1px solid var(--border); border-radius: 14px;
  cursor: pointer; font-size: 13px; color: var(--text-muted);
  background: var(--code-bg); margin-bottom: 16px;
  transition: background 0.2s;
}
.theme-toggle:hover { background: var(--border); }

/* ===== Main ===== */
.main { grid-column: 2; padding: 24px 32px 80px; max-width: 1200px; }

/* ===== Cards ===== */
.card {
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 10px; padding: 24px 28px; margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.card:hover { box-shadow: var(--card-hover-shadow); }
.card h3 { font-size: 18px; color: var(--heading); margin-bottom: 12px; }
.card h4 { font-size: 15px; color: var(--heading); margin: 16px 0 8px; }
.card p { margin-bottom: 10px; color: var(--text); }
.card code {
  background: var(--code-bg); padding: 1px 5px; border-radius: 3px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace; font-size: 13px;
}
.card pre {
  background: var(--code-bg); padding: 14px 18px; border-radius: 6px;
  overflow-x: auto; margin: 12px 0; font-size: 13px; line-height: 1.5;
  border: 1px solid var(--border);
}
.card pre code { background: none; padding: 0; }

/* ===== Tables ===== */
.card table {
  width: 100%; border-collapse: collapse; margin: 12px 0;
  font-size: 14px;
}
.card table th, .card table td {
  padding: 8px 12px; border: 1px solid var(--border); text-align: left;
}
.card table th { background: var(--code-bg); font-weight: 600; color: var(--heading); }
.card table tr:nth-child(even) td { background: var(--table-stripe); }

/* ===== Comparison Table (3-column) ===== */
.cmp-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
.cmp-table th, .cmp-table td {
  padding: 6px 10px; border: 1px solid var(--border); text-align: left;
}
.cmp-table th { background: var(--code-bg); font-weight: 600; color: var(--heading); }
.cmp-table .col-field { width: 160px; }
.cmp-table .col-dev1 { width: auto; border-left: 3px solid var(--dev1-accent); }
.cmp-table .col-dev2 { width: auto; border-left: 3px solid var(--dev2-accent); }
.cmp-table .col-dev3 { width: auto; border-left: 3px solid var(--dev3-accent); }
.cmp-table .col-note { width: 200px; font-size: 12px; color: var(--text-muted); }
.cmp-table .row-diff { background: var(--diff-highlight); }
.dark .cmp-table .row-diff { background: var(--diff-highlight-dark); }
.cmp-table .row-missing { color: var(--missing); font-style: italic; }
.dark .cmp-table .row-missing { color: var(--missing-dark); }

/* ===== Descriptor Byte-Map ===== */
.desc-byte-map {
  display: flex; border-radius: 6px; overflow: hidden;
  margin: 12px 0; border: 1px solid var(--border);
  font-family: 'Consolas', 'Cascadia Code', monospace; font-size: 11px;
}
.desc-byte-map .dcell {
  flex-shrink: 0; padding: 6px 2px; text-align: center;
  cursor: default; transition: filter 0.15s;
  border-right: 1px solid rgba(255,255,255,0.25);
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  min-width: 0;
}
.desc-byte-map .dcell:last-child { border-right: none; }
.desc-byte-map .dcell:hover { filter: brightness(1.15); }
.dcell .doff { font-size: 9px; color: rgba(255,255,255,0.6); }
.dcell .dval { font-size: 10px; font-weight: 600; color: #fff; }
.dcell .dlabel { font-size: 9px; color: rgba(255,255,255,0.8); white-space: nowrap; }
/* 15 dc-bg-* classes — same as usb-notes.html */
.dc-bg-bglen   { background: var(--color-sync-pid); }
.dc-bg-bgtype  { background: var(--color-crc); }
.dc-bg-bcd     { background: var(--color-frame); }
.dc-bg-class   { background: var(--color-eop); }
.dc-bg-ep0     { background: var(--color-addr); }
.dc-bg-vidpid  { background: var(--color-data); }
.dc-bg-str     { background: var(--color-sync-pid); opacity:0.7; }
.dc-bg-config  { background: var(--color-crc); opacity:0.7; }
.dc-bg-iface   { background: var(--color-addr); }
.dc-bg-ep      { background: var(--color-data); opacity:0.8; }
.dc-bg-attr    { background: var(--color-crc); }
.dc-bg-power   { background: var(--color-frame); opacity:0.7; }
.dc-bg-ialt    { background: var(--txn-interrupt); }
.dc-bg-nep     { background: var(--color-eop); opacity:0.7; }
.dc-bg-qual    { background: var(--color-sync-pid); opacity:0.5; }
.dc-bg-rsvd    { background: var(--text-muted); }
/* Additional bg classes for this page */
.dc-bg-uvc     { background: var(--dev1-accent); opacity: 0.8; }
.dc-bg-audio   { background: var(--dev3-accent); opacity: 0.8; }

/* ===== Foldable Details ===== */
.txn-fold {
  margin: 10px 0; padding: 10px 14px;
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 6px; cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.txn-fold:hover { background: var(--table-stripe); border-color: var(--color-sync-pid); }
.txn-fold > summary {
  font-weight: 600; font-size: 14px; color: var(--heading); list-style: none;
  display: flex; align-items: center; gap: 6px;
}
.txn-fold > summary::-webkit-details-marker { display: none; }
.txn-fold > summary::before {
  content: '▸'; font-size: 10px; transition: transform 0.2s;
  display: inline-block; width: 14px;
}
.txn-fold[open] > summary::before { transform: rotate(90deg); }
.txn-fold .fold-content { padding-top: 10px; }

/* ===== Breadcrumb ===== */
.breadcrumb {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 10px 14px; margin-bottom: 20px;
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 6px; font-size: 13px;
}
.breadcrumb .crumb { color: var(--color-sync-pid); text-decoration: none; }
.breadcrumb .crumb:hover { text-decoration: underline; }
.breadcrumb .crumb-sep { color: var(--text-muted); }
.breadcrumb .crumb-current { color: var(--text); font-weight: 600; }

/* ===== Device Tabs ===== */
.dev-tabs {
  display: flex; gap: 0; margin: 16px 0;
  border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
}
.dev-tab {
  flex: 1; padding: 8px 16px; text-align: center; cursor: pointer;
  font-size: 13px; font-weight: 600; border: none;
  background: var(--code-bg); color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
}
.dev-tab:not(:last-child) { border-right: 1px solid var(--border); }
.dev-tab.active { background: var(--card-bg); color: var(--heading); }
.dev-tab:hover { color: var(--heading); }
.dev-tab.dev1.active { box-shadow: inset 0 -3px 0 var(--dev1-accent); }
.dev-tab.dev2.active { box-shadow: inset 0 -3px 0 var(--dev2-accent); }
.dev-tab.dev3.active { box-shadow: inset 0 -3px 0 var(--dev3-accent); }

/* ===== Section Header ===== */
.section-header {
  margin: 32px 0 16px; padding-bottom: 8px;
  border-bottom: 2px solid var(--color-sync-pid);
}
.section-header h2 { font-size: 22px; color: var(--heading); }
.section-header .section-desc { font-size: 14px; color: var(--text-muted); margin-top: 4px; }

/* ===== Responsive ===== */
@media (max-width: 768px) {
  body { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .main { grid-column: 1; padding: 16px; }
}
</style>
</head>
<body>
<!-- Sidebar placeholder -->
<nav class="sidebar" id="sidebar">
  <h2>📋 USB 描述符剖析</h2>
  <button class="theme-toggle" id="themeToggle" title="切换暗色/亮色模式">🌓 主题</button>
  <!-- Navigation tree will be added in Task 3 -->
</nav>

<!-- Main content placeholder -->
<main class="main" id="mainContent">
  <!-- Descriptor sections will be added in Tasks 4-6 -->
</main>

<!-- JS placeholder -->
<script>
// JavaScript will be added in Task 7
</script>

</body></html>
```

- [ ] **Step 2: Verify HTML skeleton renders without errors**

Open `descriptor-viewer.html` in a browser. Check:
- Page has correct title in tab
- No console errors
- Sidebar renders on the left (280px), main area blank on the right
- Theme toggle button is visible (non-functional for now)
- Responsive: narrow viewport hides sidebar

- [ ] **Step 3: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add descriptor-viewer HTML skeleton with CSS design system"
```

---

### Task 3: Build sidebar navigation tree

**Files:**
- Modify: `descriptor-viewer.html` — fill in `#sidebar` content

**Interfaces:**
- Consumes: Sidebar CSS classes from Task 2
- Produces: Complete navigation tree with collapsible sections linking to descriptor sections

- [ ] **Step 1: Replace sidebar placeholder with full navigation tree**

Replace the `<!-- Navigation tree will be added in Task 3 -->` comment inside `<nav class="sidebar" id="sidebar">` with:

```html
<button class="theme-toggle" id="themeToggle" title="切换暗色/亮色模式">🌓 主题</button>

<details class="nav-section" open>
  <summary>📖 概述</summary>
  <a class="nav-link" href="#overview">描述符是什么</a>
  <a class="nav-link" href="#device-summary">三台设备速览</a>
</details>

<details class="nav-section" open>
  <summary>🔧 标准描述符</summary>
  <a class="nav-link" href="#desc-device">Device Descriptor (18B)</a>
  <a class="nav-link" href="#desc-config">Configuration Descriptor (9B)</a>
  <a class="nav-link" href="#desc-iad">IAD Descriptor (8B)</a>
  <a class="nav-link" href="#desc-interface-vc">Interface — VC (9B)</a>
  <a class="nav-link" href="#desc-interface-vs">Interface — VS (9B)</a>
  <a class="nav-link" href="#desc-endpoint-int">Endpoint — Interrupt IN</a>
  <a class="nav-link" href="#desc-endpoint-bulk">Endpoint — Bulk IN</a>
</details>

<details class="nav-section">
  <summary>🎯 类专用描述符</summary>
  <a class="nav-link" href="#class-mechanism">0x24/0x25 分发机制</a>
  <a class="nav-link" href="#uvc-vc-header">UVC VC Header 拆解</a>
  <a class="nav-link" href="#uvc-topology">UVC 拓扑图</a>
  <a class="nav-link" href="#uvc-subtypes">UVC 子类型码速查</a>
</details>

<details class="nav-section">
  <summary>⚔️ 综合实战</summary>
  <a class="nav-link" href="#trace-dev1">设备1 433B 全链追踪</a>
  <a class="nav-link" href="#diff-dev1-dev2">设备1 vs 设备2 差异</a>
  <a class="nav-link" href="#infer-dev3">设备3 KS反推</a>
</details>

<details class="nav-section">
  <summary>❓ FAQ</summary>
  <a class="nav-link" href="#faq">7 个常见问题</a>
</details>

<details class="nav-section">
  <summary>📎 附录</summary>
  <a class="nav-link" href="#appendix-a">A: 设备1 原始 dump</a>
  <a class="nav-link" href="#appendix-b">B: 设备2 原始 dump</a>
  <a class="nav-link" href="#appendix-c">C: 设备3 KS 数据</a>
</details>

<div class="dev-legend">
  <div style="font-size:13px;font-weight:600;color:var(--heading);margin-bottom:8px;">设备颜色标识</div>
  <div class="dev-dot"><span class="dot" style="background:var(--dev1-accent);"></span> 设备1 HikCamera #1</div>
  <div class="dev-dot"><span class="dot" style="background:var(--dev2-accent);"></span> 设备2 HikCamera #2</div>
  <div class="dev-dot"><span class="dot" style="background:var(--dev3-accent);"></span> 设备3 2K Camera</div>
</div>
```

- [ ] **Step 2: Verify navigation structure**

Open `descriptor-viewer.html` in browser:
- All 5 navigation sections visible with expand/collapse arrows
- Clicking summary toggles section open/close
- Hovering nav links shows blue highlight
- Device color legend shows 3 colored dots at bottom
- All links are smooth-scroll anchors (non-functional until target sections exist)

- [ ] **Step 3: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add sidebar navigation tree with device color legend"
```

---

### Task 4: Build Device Descriptor section — the template for all descriptor cards

**Files:**
- Modify: `descriptor-viewer.html` — append to `#mainContent`

**Interfaces:**
- Consumes: Card/table/byte-map CSS classes from Task 2
- Produces: Complete Device Descriptor section serving as the pattern for Tasks 5-6

- [ ] **Step 1: Add Device Descriptor card with byte-map + comparison table + foldable explanation**

Append the following inside `<main class="main" id="mainContent">`:

```html
<div class="section-header" id="desc-device">
  <h2>Device Descriptor (设备描述符) — 18 字节</h2>
  <p class="section-desc">设备级别的"身份证"。每个 USB 设备有且仅有一个 Device Descriptor。</p>
</div>

<div class="card">
  <h3>📐 标准 byte-map</h3>
  <div class="desc-byte-map">
    <div class="dcell dc-bg-bglen" style="flex:1"><span class="doff">0</span><span class="dval">0x12</span><span class="dlabel">bLength</span></div>
    <div class="dcell dc-bg-bgtype" style="flex:1"><span class="doff">1</span><span class="dval">0x01</span><span class="dlabel">bDescType</span></div>
    <div class="dcell dc-bg-bcd" style="flex:2"><span class="doff">2-3</span><span class="dval">bcdUSB</span><span class="dlabel">USB版本</span></div>
    <div class="dcell dc-bg-class" style="flex:1"><span class="doff">4</span><span class="dval">bDevCls</span><span class="dlabel">设备类</span></div>
    <div class="dcell dc-bg-class" style="flex:1"><span class="doff">5</span><span class="dval">bDevSub</span><span class="dlabel">子类</span></div>
    <div class="dcell dc-bg-class" style="flex:1"><span class="doff">6</span><span class="dval">bDevProt</span><span class="dlabel">协议</span></div>
    <div class="dcell dc-bg-ep0" style="flex:1"><span class="doff">7</span><span class="dval">EP0Max</span><span class="dlabel">EP0包大小</span></div>
    <div class="dcell dc-bg-vidpid" style="flex:2"><span class="doff">8-9</span><span class="dval">idVendor</span><span class="dlabel">VID</span></div>
    <div class="dcell dc-bg-vidpid" style="flex:2"><span class="doff">10-11</span><span class="dval">idProduct</span><span class="dlabel">PID</span></div>
    <div class="dcell dc-bg-bcd" style="flex:2"><span class="doff">12-13</span><span class="dval">bcdDevice</span><span class="dlabel">设备版本</span></div>
    <div class="dcell dc-bg-str" style="flex:1"><span class="doff">14</span><span class="dval">iManuf</span><span class="dlabel">制造商</span></div>
    <div class="dcell dc-bg-str" style="flex:1"><span class="doff">15</span><span class="dval">iProd</span><span class="dlabel">产品名</span></div>
    <div class="dcell dc-bg-str" style="flex:1"><span class="doff">16</span><span class="dval">iSerial</span><span class="dlabel">序列号</span></div>
    <div class="dcell dc-bg-config" style="flex:1"><span class="doff">17</span><span class="dval">nConf</span><span class="dlabel">配置数</span></div>
  </div>

  <h4>📊 三设备对照表</h4>
  <table class="cmp-table">
    <thead>
      <tr><th class="col-field">字段 (Offset)</th><th class="col-dev1">设备1 (HikCamera #1)</th><th class="col-dev2">设备2 (HikCamera #2)</th><th class="col-dev3">设备3 (2K Camera)</th><th class="col-note">解读</th></tr>
    </thead>
    <tbody>
      <tr><td>bLength (0)</td><td>0x12 (18)</td><td>0x12 (18)</td><td class="row-missing">无数据</td><td>USB spec 规定 Device Descriptor 固定 18 字节</td></tr>
      <tr><td>bDescriptorType (1)</td><td>0x01</td><td>0x01</td><td class="row-missing">无数据</td><td>0x01 = Device Descriptor</td></tr>
      <tr><td>bcdUSB (2-3)</td><td>0x0200 (USB 2.0)</td><td>0x0200 (USB 2.0)</td><td class="row-missing">无数据</td><td>BCD 编码，0x0200=2.0。不能直接当整数比较</td></tr>
      <tr><td>bDeviceClass (4)</td><td>0xEF (Misc)</td><td>0xEF (Misc)</td><td class="row-missing">无数据</td><td>⚠️ 为什么不是 0x0E(Video)？见下方详解</td></tr>
      <tr><td>bDeviceSubClass (5)</td><td>0x02</td><td>0x02</td><td class="row-missing">无数据</td><td>0xEF+0x02+0x01 = IAD 模式</td></tr>
      <tr><td>bDeviceProtocol (6)</td><td>0x01 (IAD)</td><td>0x01 (IAD)</td><td class="row-missing">无数据</td><td>告诉 Host：用 IAD 而非逐个 Interface 解析</td></tr>
      <tr><td>bMaxPacketSize0 (7)</td><td>0x40 (64B)</td><td>0x40 (64B)</td><td class="row-missing">无数据</td><td>HS 设备 EP0 固定 64 字节。FS 可选 8/16/32/64</td></tr>
      <tr><td>idVendor (8-9)</td><td>0x2BDF (Hikvision)</td><td>0x2BDF (Hikvision)</td><td>0x2BDF (Hikvision)</td><td>三台设备同一厂商，VID 由 USB-IF 分配</td></tr>
      <tr><td>idProduct (10-11)</td><td>0x0101</td><td>0x0101</td><td>0x028A</td><td>PID 不同 → 不同产品型号。设备1&2 同型号</td></tr>
      <tr><td>bcdDevice (12-13)</td><td>0x0409</td><td>0x0409</td><td class="row-missing">无数据</td><td>设备版本号 4.09，固件版本标识</td></tr>
      <tr><td>iManufacturer (14)</td><td>0x01 → "HIK"</td><td>0x01 → "HIK"</td><td class="row-missing">无数据</td><td>指向 String Descriptor 1</td></tr>
      <tr><td>iProduct (15)</td><td>0x02 → "HikCamera"</td><td>0x02 → "HikCamera"</td><td class="row-missing">无数据</td><td>指向 String Descriptor 2</td></tr>
      <tr><td>iSerialNumber (16)</td><td>0x03 → "G11376317"</td><td class="row-diff">0x03 → "E83518457"</td><td class="row-missing">无数据</td><td>⚠️ 同型号不同序列号——唯一差异字段</td></tr>
      <tr><td>bNumConfigurations (17)</td><td>0x01</td><td>0x01</td><td class="row-missing">无数据</td><td>仅 1 套配置</td></tr>
    </tbody>
  </table>

  <h4>🔍 关键字段深入</h4>

  <details class="txn-fold">
    <summary>bDeviceClass = 0xEF 而不是 0x0E：为什么要"绕路"？</summary>
    <div class="fold-content">
      <p>USB spec 规定：如果设备在 Device Descriptor 层面声明了设备类（如 0x0E=Video），那么该设备的<strong>所有 Interface</strong> 都必须属于该类。但我们的设备 3 既有 Camera (Video) 又有 Audio，是复合设备。即使设备 1&2 只有 Video，海康也统一用了 IAD 模式——这是现代 USB 复合设备的最佳实践。</p>
      <p><code>bDeviceClass=0xEF</code> + <code>bDeviceSubClass=0x02</code> + <code>bDeviceProtocol=0x01</code> 的组合告诉 Host："别在 Device 层面判断我的类型，去读 IAD Descriptor。"</p>
      <p>好处：每个 Interface 可以有自己的 Class/SubClass/Protocol，由 IAD 将多个 Interface 绑定为一个"功能"。例如 UVC 摄像头 = VC Interface + VS Interface，由 IAD 声明这两个是一体的。</p>
    </div>
  </details>

  <details class="txn-fold">
    <summary>bMaxPacketSize0 = 0x40 (64 字节)：HS 设备的"硬编码"选择</summary>
    <div class="fold-content">
      <p>EP0 是控制端点，用于枚举阶段的描述符请求和标准请求。USB 2.0 spec 规定：</p>
      <ul>
        <li>FS 设备：EP0 最大包可选 8、16、32 或 64 字节</li>
        <li><strong>HS 设备：EP0 最大包固定 64 字节</strong></li>
      </ul>
      <p>为什么 HS 固定 64？因为枚举阶段 Host 还不知道设备速度（枚举第一步就是读 Device Descriptor 前 8 字节来判断），HS 设备在这之前就已经被 Hub 检测为 HS 了，Host 直接用 64 字节包通信。</p>
    </div>
  </details>

  <details class="txn-fold">
    <summary>VID/PID 的 Little-Endian 陷阱</summary>
    <div class="fold-content">
      <p>USB 描述符中所有多字节字段都是 <strong>Little-Endian</strong>（小端序）。<code>idVendor = 0x2BDF</code> 在描述符中的实际字节序列是 <code>DF 2B</code>（低字节在前）。</p>
      <p>这是 USB 新手最容易踩的坑——如果你用 hexdump 看到 <code>DF 2B</code>，不要读成 <code>0xDF2B</code>。</p>
      <p>同理：<code>bcdUSB = 0x0200</code> 在字节流中是 <code>00 02</code>，<code>idProduct = 0x0101</code> 是 <code>01 01</code>。</p>
    </div>
  </details>
</div>
```

- [ ] **Step 2: Verify Device Descriptor renders correctly**

Open `descriptor-viewer.html` in browser:
- Byte-map shows 14 colored cells in a flex row, each with offset/value/label
- Comparison table has 14 data rows, device 1 column has purple left border, device 2 has green left border, device 3 has orange left border
- Row for iSerialNumber has yellow diff highlight background (`row-diff`) between devices 1 & 2
- Device 3 cells show "无数据" in italic gray
- Three foldable detail sections expand/collapse on click with triangle arrow animation
- Sidebar link "Device Descriptor (18B)" navigates to this section

- [ ] **Step 3: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add Device Descriptor section with byte-map, comparison table, and foldable explanations"
```

---

### Task 5: Build Config + IAD + Interface + Endpoint descriptor sections

**Files:**
- Modify: `descriptor-viewer.html` — append to `#mainContent` after Device Descriptor card

**Interfaces:**
- Consumes: Card/table/byte-map CSS, comparison table pattern from Task 4
- Produces: 6 descriptor sections following the template established in Task 4

- [ ] **Step 1: Add Configuration Descriptor card**

Append after the Device Descriptor `</div>` closing card. Follow the same pattern:

```html
<div class="section-header" id="desc-config">
  <h2>Configuration Descriptor (配置描述符) — 9 字节</h2>
  <p class="section-desc">定义设备的"运行模式"：功耗、接口数量、自供电/总线供电。</p>
</div>

<div class="card">
  <h3>📐 标准 byte-map</h3>
  <div class="desc-byte-map">
    <div class="dcell dc-bg-bglen" style="flex:1"><span class="doff">0</span><span class="dval">0x09</span><span class="dlabel">bLength</span></div>
    <div class="dcell dc-bg-bgtype" style="flex:1"><span class="doff">1</span><span class="dval">0x02</span><span class="dlabel">bDescType</span></div>
    <div class="dcell dc-bg-bcd" style="flex:2"><span class="doff">2-3</span><span class="dval">wTotalLen</span><span class="dlabel">总长度</span></div>
    <div class="dcell dc-bg-iface" style="flex:1"><span class="doff">4</span><span class="dval">bNumIfs</span><span class="dlabel">接口数</span></div>
    <div class="dcell dc-bg-config" style="flex:1"><span class="doff">5</span><span class="dval">bConfVal</span><span class="dlabel">配置值</span></div>
    <div class="dcell dc-bg-class" style="flex:1"><span class="doff">6</span><span class="dval">iConf</span><span class="dlabel">字符串</span></div>
    <div class="dcell dc-bg-attr" style="flex:1"><span class="doff">7</span><span class="dval">bmAttr</span><span class="dlabel">属性</span></div>
    <div class="dcell dc-bg-power" style="flex:1"><span class="doff">8</span><span class="dval">bMaxPwr</span><span class="dlabel">功耗</span></div>
  </div>

  <h4>📊 三设备对照表</h4>
  <table class="cmp-table">
    <thead><tr><th class="col-field">字段</th><th class="col-dev1">设备1</th><th class="col-dev2">设备2</th><th class="col-dev3">设备3</th><th class="col-note">解读</th></tr></thead>
    <tbody>
      <tr><td>bLength</td><td>0x09</td><td>0x09</td><td class="row-missing">无数据</td><td>标准 9 字节</td></tr>
      <tr><td>bDescriptorType</td><td>0x02</td><td>0x02</td><td class="row-missing">无数据</td><td>0x02 = Configuration</td></tr>
      <tr><td>wTotalLength</td><td>0x01B1 (433B)</td><td>0x01B1 (433B)</td><td class="row-missing">无数据</td><td>⚠️ 整个描述符链 433 字节——远超 9B Config 自身</td></tr>
      <tr><td>bNumInterfaces</td><td>0x02</td><td>0x02</td><td class="row-missing">无数据</td><td>2 个 Interface (VC + VS)</td></tr>
      <tr><td>bConfigurationValue</td><td>0x01</td><td>0x01</td><td class="row-missing">无数据</td><td>SetConfiguration(1) 激活此配置</td></tr>
      <tr><td>iConfiguration</td><td>0x04 → "Config 1"</td><td>0x04 → "Config 1"</td><td class="row-missing">无数据</td><td>配置名称</td></tr>
      <tr><td>bmAttributes</td><td>0xC0</td><td>0xC0</td><td class="row-missing">无数据</td><td>bit7=1(必须), bit6=1(自供电), bit5=0(不支持远程唤醒)</td></tr>
      <tr><td>MaxPower</td><td>0x01 (2mA)</td><td>0x01 (2mA)</td><td class="row-missing">无数据</td><td>⚠️ 自供电设备只需 2mA——实际功耗远超此值</td></tr>
    </tbody>
  </table>

  <details class="txn-fold">
    <summary>wTotalLength = 433 字节：描述符链的"总账本"</summary>
    <div class="fold-content">
      <p>Host 通过 GetDescriptor(Configuration) 一次性读回整个描述符链，长度由 wTotalLength 告知。设备1&2 的 433 字节包括：Config(9) + IAD(8) + Interface(9)×2 + VC Header(13) + Input Terminal(18) + Processing Unit(12) + Extension Unit(29) + Output Terminal(9) + Endpoint(7)×2 + VS Input Header(16) + 3 种 Format Type(27+11+28) + 7 个 Frame Type(30×7) + Color Matching(6)。</p>
    </div>
  </details>

  <details class="txn-fold">
    <summary>bmAttributes bit7 必须为 1：USB spec 的历史遗留</summary>
    <div class="fold-content">
      <p>USB 1.0 spec 规定 bmAttributes 的 bit7 保留且必须为 1。虽然这个 bit 从未被使用，但所有符合 USB spec 的设备都必须设置它。如果你在抓包时看到 bmAttributes=0x40（bit7=0），那是设备固件的 bug。</p>
      <p>bit6=1 表示自供电（有自己的电源适配器），bit5=0 表示不支持远程唤醒（Host 不能通过网络/按键唤醒此设备）。</p>
    </div>
  </details>
</div>
```

- [ ] **Step 2: Add IAD Descriptor card**

Append after Config card. IAD byte-map (8 bytes: bLength, bDescType, bFirstInterface, bInterfaceCount, bFunctionClass, bFunctionSubClass, bFunctionProtocol, iFunction). Key insight: bFunctionClass=0x0E(Video) — this is where the real "I am a camera" declaration lives.

- [ ] **Step 3: Add Interface Descriptor — VC + VS cards**

Two separate `<div class="card">` blocks under a shared section header "Interface Descriptor (接口描述符) — 2×9 字节". Each card has its own byte-map and comparison table showing bInterfaceClass=0x0E(Video), SubClass 0x01(VC) vs 0x02(VS), bAlternateSetting=0x00.

- [ ] **Step 4: Add Endpoint Descriptor — Interrupt IN + Bulk IN cards**

Two cards. Interrupt IN: bEndpointAddress=0x83 (bit7=1→IN, EP#=3), bmAttributes=0x03(Interrupt), wMaxPacketSize=0x0010(16B), bInterval=8. Bulk IN: bEndpointAddress=0x81 (bit7=1→IN, EP#=1), bmAttributes=0x02(Bulk), wMaxPacketSize=0x0200(512B HS) / 0x0040(64B FS Other Speed), bInterval=0(ignored for Bulk).

- [ ] **Step 5: Verify all sections render**

Open `descriptor-viewer.html`:
- All 6 sections have byte-map with correct colors
- All comparison tables show device data
- Foldable explanations expand/collapse
- Sidebar links navigate to correct sections

- [ ] **Step 6: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add Config, IAD, Interface, and Endpoint descriptor sections"
```

---

### Task 6: Build class-specific descriptors + comprehensive analysis + FAQ + Device 3 sections

**Files:**
- Modify: `descriptor-viewer.html` — append remaining content sections to `#mainContent`

**Interfaces:**
- Consumes: All CSS components from Task 2, section patterns from Tasks 4-5
- Produces: Remaining 4 content sections (class-specific, comprehensive analysis, FAQ, device 3 inference)

- [ ] **Step 1: Add class-specific descriptors section**

Section header + cards:
1. "0x24/0x25 分发机制" card — a diagram-like explanation using a table showing how bDescriptorType=0x24 routes to different meanings based on bInterfaceClass/bInterfaceSubClass context. Show concrete examples from device 1: in VC Interface, 0x24+Subtype1=VC Header; in VS Interface, 0x24+Subtype1=VS Input Header.
2. "UVC VC Header 逐字节拆解" card — byte-map for 13 bytes: bLength(0x0D), bDescType(0x24), bDescSubtype(0x01), bcdUVC(0x0110), wTotalLength(0x0051), dwClockFreq(0x02DC6C00=48MHz), bInCollection(0x01), baInterfaceNr[1]=0x01
3. "UVC 描述符拓扑图" card — ASCII-art style connectivity diagram showing the terminal chain: Input Terminal(ID2, ITT_CAMERA) → Processing Unit(ID5) → Extension Unit(ID10) → Output Terminal(ID3, TT_STREAMING). Plus VS side: VS Input Header → Format Type ×3 → Frame Type ×7 → Color Matching.
4. "UVC 描述符子类型码速查" card — a compact table of bDescriptorSubtype values 1-13 with names (1=VC_HEADER, 2=VC_INPUT_TERMINAL, 3=VC_OUTPUT_TERMINAL, 4=VC_SELECTOR_UNIT, 5=VC_PROCESSING_UNIT, 6=VC_EXTENSION_UNIT, ... 13=VS_COLORFORMAT)

- [ ] **Step 2: Add comprehensive analysis section**

Section header "综合实战" with three cards:
1. "设备1 433B 完整描述符链追踪" — a scrollable ASCII-art or `<pre>` block showing the full descriptor chain layout with offsets: `[0x00] Device(18B) → [0x12] Config(9B) → [0x1B] IAD(8B) → [0x23] Interface0_VC(9B) → [0x2C] VC_Header(13B) → ... → [0x1B1] End`
2. "设备1 vs 设备2 差异分析" — comparison table focusing on the 3 differences: Serial Number string, Device Address (runtime), and device 2's extra Device Qualifier + Other Speed Config descriptors. Explain the HS→FS fallback mechanism.
3. "设备3 从 KS 数据反推描述符结构" — speculative reconstruction based on MI_00(Camera)+MI_02(Audio) interface indices. Explain the likely descriptor chain: IAD(Video, Interface 0-1) + VC + VS + IAD(Audio, Interface 2-3?) + AC + AS. Note the KS data shows 2560×1440@30fps MJPEG max resolution.

- [ ] **Step 3: Add FAQ section**

Section header "常见问题 FAQ" with 7 `<details class="txn-fold">` blocks for Q1-Q7 as specified in the notes plan (Task 1, Chapter 5).

- [ ] **Step 4: Verify all sections**

Open `descriptor-viewer.html`:
- Class-specific section has 4 cards with correct UVC data
- Comprehensive analysis has 3 cards with detailed content
- FAQ has 7 expandable Q&A items
- All sidebar links navigate correctly

- [ ] **Step 5: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add class-specific descriptors, comprehensive analysis, FAQ, and device 3 inference sections"
```

---

### Task 7: Add JavaScript interactivity

**Files:**
- Modify: `descriptor-viewer.html` — replace placeholder `<script>` tag content

**Interfaces:**
- Consumes: All DOM elements (sidebar nav links, theme toggle, device tabs, fold toggles, scroll spy targets)
- Produces: Working theme toggle, scroll spy active nav highlighting, device tab switching, smooth anchor scrolling

- [ ] **Step 1: Write JavaScript for theme toggle + scroll spy + device tabs**

Replace the `// JavaScript will be added in Task 7` comment inside `<script>` with:

```javascript
// ===== Theme Toggle =====
(function() {
  const toggle = document.getElementById('themeToggle');
  const html = document.documentElement;

  // Load saved theme
  const saved = localStorage.getItem('usb-desc-theme');
  if (saved === 'dark') { html.classList.add('dark'); }

  toggle.addEventListener('click', () => {
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    localStorage.setItem('usb-desc-theme', isDark ? 'dark' : 'light');
  });
})();

// ===== Scroll Spy — highlight active nav link =====
(function() {
  const navLinks = document.querySelectorAll('.nav-link');
  const sections = [];

  navLinks.forEach(link => {
    const id = link.getAttribute('href');
    if (id && id.startsWith('#')) {
      const el = document.querySelector(id);
      if (el) sections.push({ link, el });
    }
  });

  function updateActive() {
    let current = sections[0];
    for (const s of sections) {
      if (s.el.getBoundingClientRect().top <= 120) {
        current = s;
      }
    }
    navLinks.forEach(l => l.classList.remove('active'));
    if (current) current.link.classList.add('active');

    // Auto-open nav sections containing active link
    document.querySelectorAll('.nav-section').forEach(details => {
      if (details.contains(current.link)) {
        details.open = true;
      }
    });
  }

  window.addEventListener('scroll', updateActive, { passive: true });
  updateActive();
})();

// ===== Device Tab Switching =====
(function() {
  document.querySelectorAll('.dev-tabs').forEach(tabGroup => {
    const tabs = tabGroup.querySelectorAll('.dev-tab');
    const targetSelector = tabGroup.dataset.target; // e.g. "#desc-device .col-dev3"
    const parent = document.querySelector(targetSelector);
    if (!parent) return;

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show/hide device columns in comparison tables
        const table = parent.querySelector('.cmp-table');
        if (!table) return;

        const devIndex = parseInt(tab.dataset.dev); // 1, 2, or 3
        const colClass = '.col-dev' + devIndex;

        table.querySelectorAll('th' + colClass + ', td' + colClass).forEach(cell => {
          cell.style.display = tab.classList.contains('active') ? '' : 'none';
        });
      });
    });
  });
})();

// ===== Smooth scroll for anchor links (non-sidebar) =====
document.addEventListener('click', function(e) {
  const link = e.target.closest('a[href^="#"]');
  if (!link || link.closest('.sidebar')) return;
  e.preventDefault();
  const target = document.querySelector(link.getAttribute('href'));
  if (target) {
    target.scrollIntoView({ behavior: 'smooth' });
  }
});
```

- [ ] **Step 2: Verify interactivity**

Open `descriptor-viewer.html`:
- Click theme toggle → page switches dark/light, preference saved to localStorage
- Scroll page → sidebar nav link highlights based on visible section, parent nav-section auto-opens
- Click sidebar links → smooth scroll to target section
- Device tab switching (if tabs exist) shows/hides device columns

- [ ] **Step 3: Commit**

```bash
git add descriptor-viewer.html
git commit -m "feat: add JS interactivity — theme toggle, scroll spy, device tabs"
```

---

### Task 8: Final verification and cross-reference

**Files:**
- Verify: `notes/real-device-descriptor-analysis.md`
- Verify: `descriptor-viewer.html`

**Interfaces:**
- Consumes: All completed files
- Produces: Verified, consistent deliverables

- [ ] **Step 1: Cross-check notes ↔ HTML data consistency**

Read both files and verify:
- All HEX values in HTML match the notes
- All device differences (serial numbers, Other Speed Config) are consistent
- Device 3 missing data is consistently marked "无数据" in both files
- No broken internal anchor links in HTML
- HTML title, meta charset, viewport all present
- No JavaScript console errors on page load

- [ ] **Step 2: Verify file format constraints**

```bash
# Check line endings are LF (not CRLF)
file descriptor-viewer.html
# Should show "ASCII text" or "UTF-8 Unicode text" (not "with CRLF")

# Check no external dependencies
grep -E 'https?://|src="|href="[^#]' descriptor-viewer.html
# Should return empty (no external URLs in src/href)
```

- [ ] **Step 3: Final commit**

```bash
git add notes/real-device-descriptor-analysis.md descriptor-viewer.html
git commit -m "feat: complete real-device descriptor analysis — notes + interactive HTML viewer"
```
