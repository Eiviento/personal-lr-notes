# usb-notes.html 全面翻新 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 usb-notes.html 从单文件 3266 行拆分为 3 文件（HTML/CSS/JS），全面翻新视觉为技术文档/IDE 风格，暗色默认，桌面优先，补全可访问性。

**Architecture:** 3 文件同目录双击即用。CSS 10 层分层（变量→重置→排版→布局→组件→可视化→工具→响应式→减少动画→打印）。JS 4 模块（数据→渲染→交互→初始化）。HTML 纯语义结构 + 4 空格缩进。

**Tech Stack:** 纯 HTML/CSS/JS，零外部依赖，无构建工具。CSS 自定义属性做主题切换，`<details>` 原生折叠，`defer` 加载 JS。

## Global Constraints

- 零外部依赖，双击 HTML 即可打开
- 暗色为默认主题，亮色为辅助（`.light` class 覆盖）
- 所有文件 4 空格缩进，LF 换行，UTF-8 编码
- CSS class 命名沿用现有 kebab-case 风格（`.packet-diagram`, `.txn-fold`, `.desc-byte-map`）
- 保留所有现有 `#kp-X-Y` anchor ID（不改变 URL hash 路由）
- 保留现有 PACKET_DATA 和 FRAME_TRANSACTIONS 数据内容不变
- 字体仅用系统栈，不引入 Web Font
- 桌面 ≥1024px，移动 <1024px 单一断点

---

### Task 1: 创建 usb-notes.css — 变量、重置、排版、布局

**Files:**
- Create: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.css`

**Interfaces:**
- Produces: CSS 层 1-4，定义全部 `:root` 变量、reset、字体体系、页面 Grid 布局

- [ ] **Step 1: 写层 1 — Variables（暗色默认）**

```css
/* ===================================
   1. Variables — 自定义属性
   =================================== */

:root {
    /* === 文档色板（暗色默认） === */
    --bg: #1a1b1e;
    --surface: #1e1f24;
    --card-bg: #25262b;
    --card-border: #373a40;
    --code-bg: #141517;
    --text: #c1c6cc;
    --text-heading: #e9ecef;
    --text-muted: #868e96;
    --accent: #4da6ff;
    --accent-dim: rgba(77, 166, 255, 0.12);
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    --table-stripe: rgba(255, 255, 255, 0.03);

    /* === 语义色（暗色，用于协议可视化） === */
    --color-sync-pid: #8ab4f8;
    --color-addr: #63e6be;
    --color-data: #ffc078;
    --color-crc: #b197fc;
    --color-eop: #dee2e6;
    --color-frame: #69db7c;
    --txn-control: #b197fc;
    --txn-interrupt: #ff8787;
    --txn-bulk: #63e6be;
    --txn-isoch: #69db7c;
    --txn-sof: #dee2e6;
    --txn-nak: #ffc078;

    /* === 字体 === */
    --font-sans: "Inter", "SF Pro Text", -apple-system, BlinkMacSystemFont,
                 "Segoe UI", "Noto Sans SC", sans-serif;
    --font-mono: "JetBrains Mono", "Cascadia Code", "Fira Code",
                 "Consolas", "Courier New", monospace;

    /* === 字号 === */
    --fs-h1: 28px;
    --fs-h2: 22px;
    --fs-h3: 17px;
    --fs-body: 15.5px;
    --fs-caption: 12px;

    /* === 间距（4px grid） === */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-7: 28px;
    --space-8: 32px;

    /* === 圆角 === */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-full: 999px;
}

/* 亮色主题覆盖 */
.light {
    --bg: #ffffff;
    --surface: #f6f8fa;
    --card-bg: #ffffff;
    --card-border: #d0d7de;
    --code-bg: #f6f8fa;
    --text: #1f2328;
    --text-heading: #0d1117;
    --text-muted: #656d76;
    --accent: #0969da;
    --accent-dim: rgba(9, 105, 218, 0.08);
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    --table-stripe: rgba(0, 0, 0, 0.02);

    --color-sync-pid: #1e90ff;
    --color-addr: #20c997;
    --color-data: #ffa94d;
    --color-crc: #845ef7;
    --color-eop: #adb5bd;
    --color-frame: #51cf66;
    --txn-control: #845ef7;
    --txn-interrupt: #ff6b6b;
    --txn-bulk: #20c997;
    --txn-isoch: #51cf66;
    --txn-sof: #adb5bd;
    --txn-nak: #ffa94d;
}
```

- [ ] **Step 2: 写层 2 — Reset**

```css
/* ===================================
   2. Reset — 重置与基础
   =================================== */

*,
*::before,
*::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    scroll-behavior: smooth;
    scroll-padding-top: 20px;
}

body {
    font-family: var(--font-sans);
    font-size: var(--fs-body);
    line-height: 1.7;
    color: var(--text);
    background: var(--bg);
    min-height: 100vh;
}
```

- [ ] **Step 3: 写层 3 — Typography**

```css
/* ===================================
   3. Typography — 字体与排版
   =================================== */

h1 { font-size: var(--fs-h1); line-height: 1.3; font-weight: 700; color: var(--text-heading); }
h2 { font-size: var(--fs-h2); line-height: 1.35; font-weight: 600; color: var(--text-heading); }
h3 { font-size: var(--fs-h3); line-height: 1.4; font-weight: 600; color: var(--text-heading); }
h4 { font-size: var(--fs-body); line-height: 1.5; font-weight: 600; color: var(--text-heading); }

p { margin-bottom: var(--space-3); }

ul, ol { padding-left: 1.5em; margin-bottom: var(--space-3); }
li { margin-bottom: var(--space-1); }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

code {
    font-family: var(--font-mono);
    font-size: 13px;
    background: var(--code-bg);
    padding: 1px 5px;
    border-radius: var(--radius-sm);
}

pre {
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.5;
    background: var(--code-bg);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-sm);
    overflow-x: auto;
    margin: var(--space-3) 0;
    border: 1px solid var(--card-border);
}

pre code {
    background: none;
    padding: 0;
    font-size: inherit;
}

strong { font-weight: 600; color: var(--text-heading); }
small { font-size: var(--fs-caption); color: var(--text-muted); }
```

- [ ] **Step 4: 写层 4 — Layout**

```css
/* ===================================
   4. Layout — 布局
   =================================== */

body {
    display: grid;
    grid-template-columns: 260px 1fr;
}

.sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    background: var(--surface);
    border-right: 1px solid var(--card-border);
    overflow-y: auto;
    padding: var(--space-5);
    z-index: 10;
}

.main {
    grid-column: 2;
    padding: var(--space-6) var(--space-8) 80px;
    max-width: 960px;
}
```

- [ ] **Step 5: 验证** — 在浏览器打开 `usb-notes.html`（目前只有骨架），确认 CSS 变量生效、body 网格布局正常、无 Console 错误

---

### Task 2: 创建 usb-notes.css — 组件

**Files:**
- Modify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.css` — 追加层 5

**Interfaces:**
- Consumes: 层 1-4 的 CSS 变量和基础布局
- Produces: `.sidebar` 完整样式、`.card`、`table`、`code`/`pre`、`.txn-fold`、`.theme-bar`、`.search-wrap`、`.progress-wrap`、`.skip-link`、`.scroll-top`

- [ ] **Step 1: 写层 5.1 — Sidebar 组件**

```css
/* ===================================
   5. Components — UI 组件
   =================================== */

/* 5.1 Sidebar */

.sidebar h2 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: var(--space-4);
    color: var(--text-heading);
}

.sidebar details {
    margin-bottom: var(--space-2);
}

.sidebar details > summary {
    cursor: pointer;
    font-weight: 600;
    font-size: 13.5px;
    padding: var(--space-1) 0;
    color: var(--text-heading);
    list-style: none;
    display: flex;
    align-items: center;
    gap: 6px;
}

.sidebar details > summary::-webkit-details-marker { display: none; }

.sidebar details > summary::before {
    content: "\25B8";
    font-size: 10px;
    transition: transform 0.15s ease;
    display: inline-block;
    width: 12px;
    color: var(--text-muted);
}

.sidebar details[open] > summary::before {
    transform: rotate(90deg);
}

.sidebar .sub-item {
    display: block;
    padding: var(--space-1) 0 var(--space-1) 24px;
    font-size: 13px;
    color: var(--text-muted);
    text-decoration: none;
    border-radius: var(--radius-sm);
    border-left: 3px solid transparent;
    transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.sidebar .sub-item:hover {
    color: var(--accent);
    background: var(--accent-dim);
}

.sidebar .sub-item.active {
    color: var(--accent);
    background: var(--accent-dim);
    border-left-color: var(--accent);
}

/* Phase 状态标记 */
.sidebar .badge {
    font-size: 11px;
    color: var(--text-muted);
    margin-left: auto;
}

.sidebar .phase-done { color: var(--color-frame); }
.sidebar .phase-current { color: var(--color-data); }
.sidebar .phase-pending { color: var(--text-muted); }
```

- [ ] **Step 2: 写层 5.2-5.4 — Card、Table、Code**

```css
/* 5.2 Card */

.phase-header {
    margin: var(--space-8) 0 var(--space-4);
    padding-bottom: var(--space-2);
    border-bottom: 2px solid var(--accent);
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
}

.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    padding: var(--space-5) var(--space-6);
    margin-bottom: var(--space-5);
    box-shadow: var(--shadow);
}

/* 卡片无 hover 上浮（IDE 风格克制） */
.card h3 {
    font-size: var(--fs-h3);
    margin-bottom: var(--space-3);
}

.card h4 {
    margin: var(--space-4) 0 var(--space-2);
}

/* 5.3 Table */

.card table {
    width: 100%;
    border-collapse: collapse;
    margin: var(--space-3) 0;
    font-size: 14px;
}

.card table th,
.card table td {
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--card-border);
    text-align: left;
}

.card table th {
    background: var(--code-bg);
    font-weight: 600;
    color: var(--text-heading);
}

.card table tr:nth-child(even) td {
    background: var(--table-stripe);
}

/* 5.4 Code & Pre 已在 Typography 层定义，此处只加组件级覆盖 */

.card pre {
    background: var(--code-bg);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-sm);
    overflow-x: auto;
    margin: var(--space-3) 0;
    border: 1px solid var(--card-border);
}
```

- [ ] **Step 3: 写层 5.5-5.6 — Folds、Theme Toggle**

```css
/* 5.5 Folds（可折叠详情区） */

.txn-fold {
    margin: var(--space-4) 0;
}

.txn-fold > summary {
    cursor: pointer;
    list-style: none;
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--code-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    transition: background 0.15s ease, border-color 0.15s ease;
}

.txn-fold > summary:hover {
    background: var(--accent-dim);
    border-color: var(--accent);
}

.txn-fold > summary::-webkit-details-marker { display: none; }

.txn-fold > summary::before {
    content: "\25B8";
    font-size: 12px;
    transition: transform 0.15s ease;
    display: inline-block;
    color: var(--accent);
}

.txn-fold[open] > summary::before {
    transform: rotate(90deg);
}

.txn-fold[open] > summary {
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    border-color: var(--accent);
}

.txn-fold .fold-title {
    font-weight: 700;
    font-size: 15px;
    color: var(--text-heading);
}

.txn-fold .fold-hint {
    font-size: var(--fs-caption);
    color: var(--text-muted);
    margin-left: auto;
}

.txn-fold .fold-content {
    padding: var(--space-5) var(--space-4);
    border: 1px solid var(--card-border);
    border-top: none;
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    background: var(--card-bg);
}

.txn-fold .fold-content h4 { margin: var(--space-4) 0 var(--space-2); }
.txn-fold .fold-content h4:first-child { margin-top: 0; }

/* 5.6 Theme Toggle */

.theme-bar {
    position: fixed;
    bottom: var(--space-5);
    right: var(--space-5);
    z-index: 30;
}

.theme-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    cursor: pointer;
    font-size: 20px;
    box-shadow: var(--shadow);
    transition: background 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-heading);
}

.theme-btn:hover {
    background: var(--accent-dim);
}
```

- [ ] **Step 4: 写层 5.7-5.10 — Search、Progress、Skip-link、Scroll-top**

```css
/* 5.7 Search Box */

.search-wrap {
    margin-bottom: var(--space-4);
}

.search-input {
    width: 100%;
    padding: var(--space-1) var(--space-2);
    font-size: 13px;
    font-family: var(--font-sans);
    color: var(--text);
    background: var(--code-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-sm);
    outline: none;
    transition: border-color 0.15s ease;
}

.search-input::placeholder {
    color: var(--text-muted);
}

.search-input:focus {
    border-color: var(--accent);
}

/* 5.8 Progress Bar */

.progress-wrap {
    margin-top: var(--space-4);
    padding-top: var(--space-3);
    border-top: 1px solid var(--card-border);
}

.progress-bar {
    height: 4px;
    background: var(--accent);
    border-radius: var(--radius-full);
    transition: width 0.3s ease;
}

.progress-label {
    display: block;
    margin-top: var(--space-1);
    font-size: var(--fs-caption);
    color: var(--text-muted);
    text-align: right;
}

/* 5.9 Skip Link */

.skip-link {
    position: fixed;
    top: -100%;
    left: var(--space-2);
    z-index: 999;
    padding: var(--space-2) var(--space-4);
    background: var(--accent);
    color: #fff;
    border-radius: var(--radius-sm);
    font-size: 14px;
    text-decoration: none;
}

.skip-link:focus {
    top: var(--space-2);
}

/* 5.10 Scroll-to-Top */

.scroll-top {
    position: fixed;
    bottom: 72px;
    right: var(--space-5);
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    cursor: pointer;
    font-size: 18px;
    box-shadow: var(--shadow);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    z-index: 30;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease, background 0.15s ease;
}

.scroll-top.visible {
    opacity: 1;
    pointer-events: auto;
}

.scroll-top:hover {
    background: var(--accent-dim);
    color: var(--accent);
}
```

- [ ] **Step 5: 验证** — 检查所有组件 CSS 语法正确，变量引用完整，无孤立规则

---

### Task 3: 创建 usb-notes.css — 可视化 + 工具 + 响应式 + 主题

**Files:**
- Modify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.css` — 追加层 6-10

**Interfaces:**
- Consumes: 语义色变量、间距/圆角变量、组件基础样式
- Produces: 所有可视化样式、`.sr-only`、响应式断点、reduced-motion、打印样式

- [ ] **Step 1: 写层 6.1-6.2 — Packet Diagram + Descriptor Byte Map**

```css
/* ===================================
   6. Visualizations — 数据可视化
   =================================== */

/* 6.1 Packet Diagram */

.packet-diagram-wrapper {
    overflow-x: auto;
    padding-bottom: var(--space-1);
    margin: var(--space-4) 0;
}

.packet-title {
    font-weight: 600;
    color: var(--text-heading);
    margin: var(--space-4) 0 var(--space-2);
}

.packet-legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-4);
    font-size: var(--fs-caption);
    color: var(--text-muted);
    margin-bottom: var(--space-2);
}

.packet-legend-item {
    display: flex;
    align-items: center;
    gap: var(--space-1);
}

.packet-legend-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
}

.packet-diagram {
    display: flex;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--card-border);
    min-width: fit-content;
}

.packet-diagram .field {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 48px;
    padding: var(--space-1) var(--space-1);
    position: relative;
    cursor: default;
    transition: filter 0.15s ease;
    border-right: 1px solid rgba(0, 0, 0, 0.2);
    min-width: 0;
}

.packet-diagram .field:last-child { border-right: none; }

.packet-diagram .field:hover {
    filter: brightness(1.15);
}

.packet-diagram .field .fname {
    font-size: 11px;
    font-weight: 700;
    color: #fff;
    white-space: nowrap;
}

.packet-diagram .field .fbits {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.85);
    white-space: nowrap;
}

.packet-diagram .field .fval {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.7);
    white-space: nowrap;
    margin-top: 1px;
}

.packet-diagram .field .tooltip {
    display: none;
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #212529;
    color: #f8f9fa;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    font-size: var(--fs-caption);
    font-family: var(--font-mono);
    white-space: nowrap;
    z-index: 20;
    pointer-events: none;
    max-width: 280px;
    white-space: normal;
    line-height: 1.5;
}

.packet-diagram .field:hover .tooltip {
    display: block;
    animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* 字段颜色类 — 语义色背景 + 白色文字 */
.color-sync-pid { background: var(--color-sync-pid); }
.color-addr     { background: var(--color-addr); }
.color-data     { background: var(--color-data); }
.color-crc      { background: var(--color-crc); }
.color-eop      { background: var(--color-eop); }
.color-frame    { background: var(--color-frame); }

/* 6.2 Descriptor Byte Map */

.desc-byte-map {
    display: flex;
    border-radius: var(--radius-sm);
    overflow: hidden;
    margin: var(--space-3) 0;
    border: 1px solid var(--card-border);
    font-family: var(--font-mono);
    font-size: 11px;
}

.desc-byte-map .dcell {
    flex-shrink: 0;
    min-width: 32px;
    padding: var(--space-1) 2px;
    text-align: center;
    cursor: default;
    transition: filter 0.15s ease, box-shadow 0.15s ease;
    border-right: 1px solid rgba(255, 255, 255, 0.25);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
}

.desc-byte-map .dcell:last-child { border-right: none; }

.desc-byte-map .dcell:hover {
    filter: brightness(1.15);
    box-shadow: 0 0 6px currentColor;
}

.dcell .doff {
    font-size: 9px;
    color: rgba(255, 255, 255, 0.6);
}

.dcell .dval {
    font-size: 10px;
    font-weight: 600;
    color: #fff;
}

.dcell .dlabel {
    font-size: 9px;
    color: rgba(255, 255, 255, 0.8);
    white-space: nowrap;
}

.dc-bg-bglen   { background: var(--color-sync-pid); }
.dc-bg-bgtype  { background: var(--color-crc); }
.dc-bg-bcd     { background: var(--color-frame); }
.dc-bg-class   { background: var(--color-eop); }
.dc-bg-ep0     { background: var(--color-addr); }
.dc-bg-vidpid  { background: var(--color-data); }
.dc-bg-str     { background: var(--color-sync-pid); opacity: 0.7; }
.dc-bg-config  { background: var(--color-crc); opacity: 0.7; }
.dc-bg-iface   { background: var(--color-addr); }
.dc-bg-ep      { background: var(--color-data); opacity: 0.8; }
.dc-bg-attr    { background: var(--color-crc); }
.dc-bg-power   { background: var(--color-frame); opacity: 0.7; }
.dc-bg-ialt    { background: var(--txn-interrupt); }
.dc-bg-nep     { background: var(--color-eop); opacity: 0.7; }
.dc-bg-qual    { background: var(--color-sync-pid); opacity: 0.5; }
.dc-bg-rsvd    { background: var(--text-muted); }

/* bit 释义表 */
.desc-bit-table { margin: var(--space-2) 0; }
.desc-bit-table td:first-child {
    font-family: var(--font-mono);
    font-weight: 600;
    white-space: nowrap;
}
```

- [ ] **Step 2: 写层 6.3-6.5 — Frame Timeline + Detail Panel + Bus Hound**

```css
/* 6.3 Frame Timeline */

.txn-legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-4);
    margin: var(--space-3) 0 var(--space-4);
    font-size: var(--fs-caption);
    color: var(--text-muted);
}

.txn-legend-item {
    display: flex;
    align-items: center;
    gap: var(--space-1);
}

.txn-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
}

.txn-dot.txn-sof       { background: var(--txn-sof); }
.txn-dot.txn-control   { background: var(--txn-control); }
.txn-dot.txn-interrupt { background: var(--txn-interrupt); }
.txn-dot.txn-bulk      { background: var(--txn-bulk); }
.txn-dot.txn-isoch     { background: var(--txn-isoch); }
.txn-dot.txn-nak       { background: var(--txn-nak); }

.frame-timeline {
    display: flex;
    gap: 2px;
    margin: var(--space-1) 0 var(--space-4);
    overflow-x: auto;
    padding-bottom: var(--space-1);
}

.txn-block {
    flex-shrink: 0;
    border-radius: var(--radius-full);
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
    transition: box-shadow 0.15s ease, transform 0.15s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    min-width: 36px;
    position: relative;
}

.txn-block:hover { transform: translateY(-1px); }

.txn-block:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* 时间线类型样式：纯色浅底 + 左侧色条 */
.txn-block.txn-sof       { background: color-mix(in srgb, var(--txn-sof) 12%, var(--card-bg)); border-left: 3px solid var(--txn-sof); }
.txn-block.txn-control   { background: color-mix(in srgb, var(--txn-control) 12%, var(--card-bg)); border-left: 3px solid var(--txn-control); }
.txn-block.txn-interrupt { background: color-mix(in srgb, var(--txn-interrupt) 12%, var(--card-bg)); border-left: 3px solid var(--txn-interrupt); }
.txn-block.txn-bulk      { background: color-mix(in srgb, var(--txn-bulk) 12%, var(--card-bg)); border-left: 3px solid var(--txn-bulk); }
.txn-block.txn-isoch     { background: color-mix(in srgb, var(--txn-isoch) 12%, var(--card-bg)); border-left: 3px solid var(--txn-isoch); }
.txn-block.txn-nak       { background: color-mix(in srgb, var(--txn-nak) 8%, var(--card-bg)); border: 1px dashed var(--txn-nak); border-left: 3px dashed var(--txn-nak); }

.txn-block .txn-device { font-size: 10px; color: var(--text-muted); white-space: nowrap; }
.txn-block .txn-label  { font-size: 11px; font-weight: 600; color: var(--text-heading); white-space: nowrap; }
.txn-block .txn-type   { font-size: 9px; color: var(--text-muted); white-space: nowrap; }
.txn-block .txn-hint   { font-size: 9px; color: var(--accent); margin-top: 1px; }

/* 6.4 Transaction Detail Panel */

.txn-detail {
    margin: 0 0 var(--space-5);
    border: 1px solid var(--accent);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    background: var(--code-bg);
    animation: fadeIn 0.15s ease-out;
}

.txn-detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-3);
    padding-bottom: var(--space-2);
    border-bottom: 1px solid var(--card-border);
}

.txn-detail-header span {
    font-weight: 700;
    font-size: 15px;
    color: var(--text-heading);
}

.txn-detail-close {
    background: none;
    border: 1px solid var(--card-border);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s ease, border-color 0.15s ease;
}

.txn-detail-close:hover { color: var(--text); border-color: var(--text); }

.txn-packet-list { display: flex; flex-direction: column; gap: var(--space-2); }

.txn-packet-item {
    background: var(--card-bg);
    border-radius: var(--radius-sm);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--card-border);
}

.txn-packet-item .pkt-name {
    font-weight: 600;
    font-size: 13px;
    color: var(--text-heading);
    margin-bottom: var(--space-1);
}

.txn-packet-flow {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    align-items: center;
    margin-top: var(--space-1);
}

.txn-packet-flow .pkt-bit {
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-family: var(--font-mono);
    color: #fff;
    white-space: nowrap;
    cursor: default;
    transition: filter 0.15s ease;
}

.txn-packet-flow .pkt-bit:hover { filter: brightness(1.2); }

.txn-packet-flow .pkt-arrow {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0 2px;
}

.txn-note {
    margin-top: var(--space-3);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--txn-nak) 15%, var(--card-bg));
    font-size: 13px;
    color: var(--txn-nak);
    border-left: 3px solid var(--txn-nak);
}

/* 6.5 Bus Hound Annotations */

.txn-annot-block {
    margin: var(--space-2) 0 var(--space-4) 0;
    counter-reset: bh-line;
}

.txn-annot-line {
    font-family: var(--font-mono);
    padding: var(--space-1) var(--space-3);
    margin: 1px 0;
    border-radius: var(--radius-sm);
    position: relative;
}

.txn-annot-line::before {
    counter-increment: bh-line;
    content: counter(bh-line);
    display: inline-block;
    width: 24px;
    margin-right: var(--space-2);
    text-align: right;
    color: var(--text-muted);
    font-size: 10px;
    user-select: none;
}

.txn-annot-bh {
    background: var(--code-bg);
    font-weight: 600;
    font-size: 13px;
}

.txn-annot-usb {
    background: transparent;
    font-size: 11px;
    color: var(--text-muted);
    padding-left: 52px;
    border-left: 2px dashed var(--card-border);
    margin-left: 6px;
    line-height: 1.6;
}
```

- [ ] **Step 3: 写层 7-10 — Utilities、Responsive、Reduced Motion、Print**

```css
/* ===================================
   7. Utilities — 工具类
   =================================== */

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* 全局 focus 样式 */
:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* ===================================
   8. Responsive — 响应式 (< 1024px)
   =================================== */

@media (max-width: 1023px) {
    body {
        grid-template-columns: 1fr;
    }

    .sidebar {
        display: none;
    }

    .main {
        grid-column: 1;
        padding: var(--space-4);
        max-width: 100%;
    }

    /* 顶部 sticky 导航条 */
    .mobile-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: sticky;
        top: 0;
        height: 48px;
        padding: 0 var(--space-4);
        background: var(--surface);
        border-bottom: 1px solid var(--card-border);
        z-index: 50;
    }

    .mobile-nav-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-heading);
    }

    .mobile-nav-btn {
        background: none;
        border: 1px solid var(--card-border);
        color: var(--text);
        font-size: 20px;
        width: 36px;
        height: 36px;
        border-radius: var(--radius-sm);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 侧边栏 overlay */
    .sidebar-overlay {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: none;
    }

    .sidebar-overlay.open {
        display: block;
    }

    .sidebar-overlay-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
    }

    .sidebar-overlay-content {
        position: absolute;
        top: 0;
        left: 0;
        width: 280px;
        height: 100%;
        background: var(--surface);
        overflow-y: auto;
        padding: var(--space-5);
        box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
    }
}

@media (min-width: 1024px) {
    .mobile-nav { display: none; }
    .sidebar-overlay { display: none; }
}

/* ===================================
   9. Reduced Motion — 减少动画
   =================================== */

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }

    html {
        scroll-behavior: auto;
    }
}

/* ===================================
   10. Print — 打印样式
   =================================== */

@media print {
    .sidebar,
    .theme-bar,
    .skip-link,
    .scroll-top,
    .mobile-nav,
    .sidebar-overlay {
        display: none !important;
    }

    body {
        display: block;
        background: #fff;
        color: #000;
    }

    .main {
        max-width: 100%;
        padding: 0;
        grid-column: auto;
    }

    .card {
        break-inside: avoid;
        box-shadow: none;
        border: 1px solid #ccc;
        background: #fff;
    }

    .packet-diagram .field {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
```

- [ ] **Step 4: 验证** — 检查所有可视化 CSS 语法正确，响应式断点逻辑正确，打印样式无遗漏

---

### Task 4: 创建 usb-notes.js — 数据层 + 渲染层

**Files:**
- Create: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.js`

**Interfaces:**
- Produces: `PACKET_DATA`（4 个包图数据对象）、`FRAME_TRANSACTIONS`（12 个时间线事务）、`PacketRenderer`、`TimelineRenderer`

- [ ] **Step 1: 从现有 usb-notes.html 提取 PACKET_DATA 和 FRAME_TRANSACTIONS**

从现有 `usb-notes.html` 中完整复制以下两个常量的内容（数据不变）：

```javascript
// usb-notes.js

// ===== 1. DATA =====

// PACKET_COLORS 映射（从旧文件复制）
var PACKET_COLORS = {
    'sync-pid': 'color-sync-pid',
    'addr':     'color-addr',
    'data':     'color-data',
    'crc':      'color-crc',
    'eop':      'color-eop',
    'frame':    'color-frame',
};

// PACKET_DATA — 4 个包结构图数据（完整复制旧文件内容）
var PACKET_DATA = [
    {
        id: 'pkt-token',
        title: 'Token 包 (IN/OUT/SETUP) — 共 35 bits',
        fields: [
            { name: 'SYNC',  bits: 8, val: '00000001', desc: '同步序列, LSB first。7个0让接收方PLL锁定时钟', color: 'sync-pid' },
            { name: 'PID',   bits: 8, val: 'IN=0x69, OUT=0xE1, SETUP=0x2D', desc: '包标识符, 高4位=~低4位。IN=1001, OUT=0001, SETUP=1101', color: 'sync-pid' },
            { name: 'ADDR',  bits: 7, val: '0x01~0x7F', desc: '设备地址。7bit → 128个, 0x00保留, 可分配1~127。Host分配地址, 设备被动接受', color: 'addr' },
            { name: 'ENDP',  bits: 4, val: '0x0~0xF', desc: '端点号。4bit → 0~15。EP0固定用于控制传输', color: 'addr' },
            { name: 'CRC5',  bits: 5, val: '校验和', desc: '多项式 x⁵+x²+1 (0x25), 校验范围 ADDR(7b)+ENDP(4b)=11bits。CRC5不匹配→地址或端点号损坏→丢弃包', color: 'crc' },
            { name: 'EOP',   bits: 3, val: 'SE0+J', desc: '包结束信号。SE0持续2个bit时间 + J状态1个bit时间', color: 'eop' },
        ]
    },
    // ... [其余 3 个数据对象完整复制，此处省略以防止计划文件过长]
    // pkt-sof, pkt-data, pkt-handshake — 全部从旧文件逐字复制
];

// FRAME_TRANSACTIONS — 12 个时间线事务（完整复制旧文件内容）
var FRAME_TRANSACTIONS = [
    // ... [12 个事务对象完整复制，此处省略]
];

// TXN_COLORS 和 TXN_COLOR_VARS 映射（从旧文件复制）
var TXN_COLORS = {
    sof: 'txn-sof', control: 'txn-control', interrupt: 'txn-interrupt',
    bulk: 'txn-bulk', isoch: 'txn-isoch', nak: 'txn-nak',
};

var TXN_COLOR_VARS = {
    sof: 'var(--txn-sof)', control: 'var(--txn-control)', interrupt: 'var(--txn-interrupt)',
    bulk: 'var(--txn-bulk)', isoch: 'var(--txn-isoch)', nak: 'var(--txn-nak)',
};
```

> **实现说明**：上述 `...` 省略部分在实施时从 `usb-notes.html` L2602-L3169 逐字复制，不做任何修改。数据量约 470 行，为避免计划文件膨胀，此处只展示接口签名。

- [ ] **Step 2: 写 PacketRenderer**

```javascript
// ===== 2. RENDERERS =====

var PacketRenderer = {
    /**
     * 渲染单个包结构图。
     * @param {Object} data — PACKET_DATA 元素
     *    data.id   : string — 目标容器元素 ID
     *    data.title: string — 图表标题（渲染到 .packet-title 元素中，由 HTML 预置）
     *    data.fields: Array<{name, bits, val, desc, color, flexFactor?}>
     */
    render: function(data) {
        var container = document.getElementById(data.id);
        if (!container) return;

        var totalBits = data.fields.reduce(function(sum, f) {
            return sum + (f.flexFactor || f.bits);
        }, 0);

        var diagram = document.createElement('div');
        diagram.className = 'packet-diagram';

        data.fields.forEach(function(field) {
            var widthBits = field.flexFactor || field.bits;
            var flexGrow = widthBits;

            var div = document.createElement('div');
            div.className = 'field ' + (PACKET_COLORS[field.color] || 'color-sync-pid');
            div.style.flexGrow = flexGrow;
            div.style.flexBasis = (widthBits / totalBits * 100) + '%';
            div.setAttribute('aria-label', field.name + ', ' + field.bits + ' bits, ' + field.val);

            // 多行 tooltip（相对于旧版的单行升级）
            var tooltipHtml = '<span class="tooltip">' +
                '<strong>' + field.name + '</strong>  ' + field.bits + ' bits<br>' +
                field.val + '<br>' +
                field.desc +
                '</span>';

            div.innerHTML =
                '<span class="fname">' + field.name + '</span>' +
                '<span class="fbits">' + (field.bits === 0 ? '0~8192' : field.bits + ' bit') + '</span>' +
                '<span class="fval">' + field.val + '</span>' +
                tooltipHtml;

            diagram.appendChild(div);
        });

        container.innerHTML = '';
        container.appendChild(diagram);
    },

    renderAll: function() {
        PACKET_DATA.forEach(function(data) { PacketRenderer.render(data); });
    }
};
```

- [ ] **Step 3: 写 TimelineRenderer**

```javascript
var TimelineRenderer = {
    activeTxnBlock: null,

    render: function(txn) {
        var block = document.createElement('div');
        block.className = 'txn-block ' + (TXN_COLORS[txn.type] || 'txn-sof');
        block.style.flexGrow = txn.width;
        block.setAttribute('tabindex', '0');
        block.setAttribute('role', 'button');
        block.setAttribute('aria-expanded', 'false');
        block.title = '点击查看 ' + txn.label + ' 内部包细节';

        var dataIndicator = txn.hasData ? '' : ' ❌';
        block.innerHTML =
            '<span class="txn-device">' + txn.device + ' (Addr' + txn.addr + ')</span>' +
            '<span class="txn-label">' + txn.label + dataIndicator + '</span>' +
            '<span class="txn-type">' + txn.transferType + '</span>' +
            '<span class="txn-hint">🔍 点击展开</span>';

        var self = this;
        block.addEventListener('click', function() { self.showDetail(txn, block); });
        block.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                self.showDetail(txn, block);
            }
        });

        return block;
    },

    renderAll: function() {
        var container = document.getElementById('frameTimeline');
        if (!container) return;

        var totalWidth = FRAME_TRANSACTIONS.reduce(function(s, t) { return s + t.width; }, 0);

        var self = this;
        FRAME_TRANSACTIONS.forEach(function(txn) {
            var block = self.render(txn);
            block.style.flexBasis = (txn.width / totalWidth * 100) + '%';
            container.appendChild(block);
        });
    },

    showDetail: function(txn, block) {
        var detail = document.getElementById('txnDetail');
        var title = document.getElementById('txnDetailTitle');
        var body = document.getElementById('txnDetailBody');
        var closeBtn = document.getElementById('txnDetailClose');

        if (!detail || !title || !body) return;

        // 更新 active 状态
        if (this.activeTxnBlock) {
            this.activeTxnBlock.setAttribute('aria-expanded', 'false');
            this.activeTxnBlock.style.boxShadow = '';
        }
        this.activeTxnBlock = block;
        block.setAttribute('aria-expanded', 'true');
        block.style.boxShadow = '0 0 0 3px ' + TXN_COLOR_VARS[txn.type];

        // 填充数据
        var dataBadge = txn.hasData
            ? '<span style="color:var(--txn-isoch);font-size:12px;">✅ 有数据</span>'
            : '<span style="color:var(--txn-nak);font-size:12px;">❌ 无数据（NAK）</span>';

        title.innerHTML = txn.device + ' → ' + txn.label + ' (' + txn.transferType + ') ' + dataBadge;

        var html = '';
        txn.packets.forEach(function(pkt, i) {
            html += '<div class="txn-packet-item">';
            html += '<div class="pkt-name">' + (i === 0 ? '▶ ' : '↑ ') + pkt.name +
                    ' <span style="font-size:11px;color:var(--text-muted);">' + pkt.direction + '</span></div>';
            html += '<div class="txn-packet-flow">';
            pkt.flow.forEach(function(seg, j) {
                html += (j > 0 ? '<span class="pkt-arrow">▸</span>' : '');
                html += '<span class="pkt-bit" style="background:' + seg.color + ';" title="' + seg.bits + ' bits">' +
                        seg.text + ' (' + seg.bits + 'b)</span>';
            });
            html += '</div></div>';
        });

        if (txn.note) {
            html += '<div class="txn-note">💡 ' + txn.note + '</div>';
        }

        body.innerHTML = html;
        detail.style.display = 'block';

        var self = this;
        closeBtn.onclick = function() { self.closeDetail(); };
    },

    closeDetail: function() {
        var detail = document.getElementById('txnDetail');
        if (!detail) return;
        detail.style.display = 'none';
        if (this.activeTxnBlock) {
            this.activeTxnBlock.setAttribute('aria-expanded', 'false');
            this.activeTxnBlock.style.boxShadow = '';
            this.activeTxnBlock = null;
        }
    }
};
```

- [ ] **Step 4: 验证** — 在 `DOMContentLoaded` 中临时调用 `PacketRenderer.renderAll()` 和 `TimelineRenderer.renderAll()` 确认无 JS 错误，数据正确渲染

---

### Task 5: 创建 usb-notes.js — 交互层 + 初始化

**Files:**
- Modify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.js` — 追加层 3-4

**Interfaces:**
- Consumes: 全局 DOM 结构（`.sidebar`, `.card`, `#themeToggle` 等 ID）
- Produces: `ThemeManager`, `ScrollSpy`, `SearchFilter`, `NavOverlay` + Init 入口

- [ ] **Step 1: 写 ThemeManager**

```javascript
// ===== 3. INTERACTION =====

var ThemeManager = {
    STORAGE_KEY: 'usb-notes-theme',

    init: function() {
        // CSS :root 默认暗色；若 localStorage 存了 'light'，切到亮色
        var saved = localStorage.getItem(this.STORAGE_KEY);
        var html = document.documentElement;

        if (saved === 'light') {
            html.classList.add('light');
            html.classList.remove('dark');
        } else {
            // 默认暗色（localStorage 无记录 或 存了 'dark'）
            html.classList.add('dark');
            html.classList.remove('light');
        }

        this._updateButton();
        this._bind();
    },

    toggle: function() {
        var html = document.documentElement;
        if (html.classList.contains('dark')) {
            html.classList.replace('dark', 'light');
            localStorage.setItem(this.STORAGE_KEY, 'light');
        } else {
            html.classList.replace('light', 'dark');
            localStorage.setItem(this.STORAGE_KEY, 'dark');
        }
        this._updateButton();
    },

    _updateButton: function() {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        var isDark = document.documentElement.classList.contains('dark');
        btn.textContent = isDark ? '\u{1F319}' : '\u{2600}';  // 🌙 / ☀
        btn.setAttribute('aria-label', isDark ? '切换到亮色模式' : '切换到暗色模式');
    },

    _bind: function() {
        var btn = document.getElementById('themeToggle');
        var self = this;
        if (btn) {
            btn.addEventListener('click', function() { self.toggle(); });
        }
    }
};
```

- [ ] **Step 2: 写 ScrollSpy + SearchFilter + NavOverlay**

```javascript
var ScrollSpy = {
    ticking: false,

    init: function() {
        var self = this;
        window.addEventListener('scroll', function() {
            if (!self.ticking) {
                requestAnimationFrame(function() { self._update(); self.ticking = false; });
                self.ticking = true;
            }
        }, { passive: true });
    },

    _update: function() {
        var cards = document.querySelectorAll('.card[id]');
        var links = document.querySelectorAll('.sidebar .sub-item');
        var current = null;

        cards.forEach(function(card) {
            var rect = card.getBoundingClientRect();
            if (rect.top <= 150) current = card.id;
        });

        links.forEach(function(link) {
            var href = link.getAttribute('href');
            var isActive = href === '#' + current;
            link.classList.toggle('active', isActive);

            // 高亮所属 Phase 的 summary
            if (isActive) {
                var details = link.closest('details');
                if (details) {
                    // 取消所有 summary 高亮
                    document.querySelectorAll('.sidebar details > summary').forEach(function(s) {
                        s.style.fontWeight = '';
                        s.style.color = '';
                    });
                    var summary = details.querySelector('summary');
                    if (summary) {
                        summary.style.fontWeight = '700';
                        summary.style.color = 'var(--accent)';
                    }
                }
            }
        });
    }
};

var SearchFilter = {
    init: function() {
        var input = document.getElementById('sidebarSearch');
        if (!input) return;

        var self = this;
        input.addEventListener('input', function() {
            self.filter(this.value);
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') { this.value = ''; self.filter(''); }
        });
    },

    filter: function(query) {
        var q = query.toLowerCase().trim();
        var items = document.querySelectorAll('.sidebar .sub-item');
        var detailsList = document.querySelectorAll('.sidebar details');

        items.forEach(function(item) {
            var text = item.textContent.toLowerCase();
            item.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
        });

        // 若 Phase 下所有子项隐藏，隐藏整个 Phase
        detailsList.forEach(function(details) {
            var visibleItems = details.querySelectorAll('.sub-item[style*="display: none"]');
            var allItems = details.querySelectorAll('.sub-item');
            if (allItems.length > 0 && visibleItems.length === allItems.length) {
                details.style.display = 'none';
            } else {
                details.style.display = '';
            }
        });
    }
};

var NavOverlay = {
    init: function() {
        var btn = document.getElementById('mobileNavBtn');
        var overlay = document.getElementById('sidebarOverlay');
        var backdrop = overlay ? overlay.querySelector('.sidebar-overlay-backdrop') : null;

        if (!btn || !overlay) return;

        var self = this;
        btn.addEventListener('click', function() { self.open(); });
        if (backdrop) {
            backdrop.addEventListener('click', function() { self.close(); });
        }

        // Escape 关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && overlay.classList.contains('open')) {
                self.close();
            }
        });
    },

    open: function() {
        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) overlay.classList.add('open');
    },

    close: function() {
        var overlay = document.getElementById('sidebarOverlay');
        if (overlay) overlay.classList.remove('open');
    }
};
```

- [ ] **Step 3: 写 Scroll-to-Top + Init 入口**

```javascript
// ===== Scroll to Top =====
function initScrollTop() {
    var btn = document.getElementById('scrollTopBtn');
    if (!btn) return;

    window.addEventListener('scroll', function() {
        var scrolled = window.scrollY > 400;
        btn.classList.toggle('visible', scrolled);
    }, { passive: true });

    btn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ===== 4. INIT =====
document.addEventListener('DOMContentLoaded', function() {
    ThemeManager.init();
    ScrollSpy.init();
    SearchFilter.init();
    NavOverlay.init();
    initScrollTop();
    PacketRenderer.renderAll();
    TimelineRenderer.renderAll();
});
```

- [ ] **Step 4: 验证** — `node --check usb-notes.js` 语法检查通过，确认所有依赖的 DOM ID 都在 HTML 中存在

---

### Task 6: 重写 usb-notes.html

**Files:**
- Create: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.html`（覆盖现有文件）
- Backup: 先将现有文件重命名为 `usb-notes-old.html`

**Interfaces:**
- Consumes: `usb-notes.css`（`<link>` 引用）、`usb-notes.js`（`<script defer>` 引用）
- Produces: 完整 HTML 结构，所有语义化标签、ARIA 属性、响应式骨架

- [ ] **Step 1: 备份旧文件**

```bash
cp D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.html D:/CC/personal-lr-notes/CCNotes/USB/usb-notes-old.html
```

- [ ] **Step 2: 写 HTML `<head>`（含防闪白脚本）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="USB 协议系统学习笔记 — 逐字节精讲，含包结构图、描述符 byte-map、帧时间线">
<meta name="theme-color" content="#1a1b1e" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<title>USB 协议学习笔记 — 逐字节精讲</title>
<link rel="stylesheet" href="usb-notes.css">

<!-- 防闪白：同步检查 localStorage，阻塞渲染前设好 class -->
<script>
(function(){var t=localStorage.getItem('usb-notes-theme');
if(t==='light')document.documentElement.classList.add('light');
else document.documentElement.classList.add('dark');})();
</script>

<script src="usb-notes.js" defer></script>
</head>
<body>
```

- [ ] **Step 3: 写跳过链接 + 侧边栏（含搜索框 + 进度条）**

```html
<a class="skip-link" href="#main-content">跳到内容</a>

<!-- 移动端顶部导航条 -->
<nav class="mobile-nav" aria-label="移动端导航">
    <span class="mobile-nav-title">USB 协议学习笔记</span>
    <button class="mobile-nav-btn" id="mobileNavBtn" aria-label="打开目录" type="button">☰</button>
</nav>

<!-- 移动端侧边栏 overlay -->
<div class="sidebar-overlay" id="sidebarOverlay">
    <div class="sidebar-overlay-backdrop"></div>
    <div class="sidebar-overlay-content" id="sidebarOverlayContent">
        <!-- JS 将 .sidebar 克隆到此 或 直接复用 .sidebar -->
    </div>
</div>

<nav class="sidebar" aria-label="目录导航">
    <h2>USB 协议学习笔记</h2>

    <div class="search-wrap">
        <input type="search" class="search-input" id="sidebarSearch"
               placeholder="过滤章节..." aria-label="过滤章节">
    </div>

    <details open>
        <summary><span>📡 Phase 1: USB 概览与总线拓扑</span><span class="badge phase-done">5/5 ✓</span></summary>
        <a class="sub-item" href="#kp-1-1">1.1 USB 设计目标与历史</a>
        <a class="sub-item" href="#kp-1-2">1.2 USB 版本演进全景</a>
        <a class="sub-item" href="#kp-1-3">1.3 总线拓扑结构</a>
        <a class="sub-item" href="#kp-1-4">1.4 主机控制器类型</a>
        <a class="sub-item" href="#kp-1-5">1.5 物理层与电气特性</a>
    </details>

    <details open>
        <summary><span>📡 Phase 2: USB 通信模型</span><span class="badge phase-done">19/19 ✓</span></summary>
        <a class="sub-item" href="#kp-2-1">2.1 三层通信模型</a>
        <a class="sub-item" href="#kp-2-2">2.2 端点(Endpoint)深入</a>
        <a class="sub-item" href="#kp-2-3">2.3 管道(Pipe)深入</a>
        <a class="sub-item" href="#kp-2-3a">⟐ 接口与端点的归属关系</a>
        <a class="sub-item" href="#kp-2-4">2.4 四种传输类型全景</a>
        <!-- ... [其余 Phase 2 子项完整列出，内容从旧文件复制] -->
    </details>

    <details open>
        <summary><span>📡 Phase 3: 描述符体系</span><span class="badge phase-done">11/11 ✓</span></summary>
        <!-- ... [Phase 3 子项完整列出] -->
    </details>

    <!-- Phase 4-8 待实现，折叠状态 -->
    <details>
        <summary><span>📡 Phase 4: 枚举过程</span><span class="badge phase-pending">0/12 ○ · 即将更新</span></summary>
    </details>
    <details>
        <summary><span>📡 Phase 5: 标准请求</span><span class="badge phase-pending">0/6 ○ · 即将更新</span></summary>
    </details>
    <details>
        <summary><span>📡 Phase 6: HID/CDC/UVC</span><span class="badge phase-pending">0/26 ○ · 即将更新</span></summary>
    </details>
    <details>
        <summary><span>📡 Phase 7: 协议分析工具</span><span class="badge phase-pending">0/7 ○ · 即将更新</span></summary>
    </details>
    <details>
        <summary><span>📡 Phase 8: libusb 编程</span><span class="badge phase-pending">0/5 ○ · 即将更新</span></summary>
    </details>

    <div class="progress-wrap" role="progressbar" aria-valuenow="48" aria-valuemin="0"
         aria-valuemax="100" aria-label="学习进度 48%">
        <div class="progress-bar" style="width:48%"></div>
        <span class="progress-label">32/67 (48%)</span>
    </div>
</nav>
```

- [ ] **Step 4: 写 `<main>` 内容区 — Phase 1 示例（完整迁移所有 `.card`）**

```html
<main class="main" id="main-content" aria-label="学习笔记正文">

    <div class="phase-header" id="phase-1">
        <h2>Phase 1: USB 概览与总线拓扑</h2>
        <span style="font-size:14px;color:var(--color-frame);">5/5 ✓</span>
    </div>

    <!-- 1.1 -->
    <article class="card" id="kp-1-1">
        <h3>1.1 USB 设计目标与历史</h3>
        <h4>USB 之前的七种接口和七种痛</h4>
        <table>
            <tr><th>接口</th><th>痛点</th></tr>
            <tr><td>RS-232 串口</td><td>速度慢(115.2kbps)、不能热插拔、一端口一设备、需手动设参数</td></tr>
            <!-- ... [其余行完整复制] -->
        </table>
        <!-- ... [完整内容从旧文件迁移，4空格缩进] -->
    </article>

    <!-- [继续迁移所有 .card 文章，内容不变，只改缩进为 4空格] -->

</main>
```

> **实现说明**：HTML body 内容从旧文件逐卡迁移。每个 `<article class="card" id="kp-X-Y">` 内的内容**完全不变**——只做 3 件事：(1) 缩进统一为 4 空格；(2) 去掉旧的 `<style>` 和 `<script>` 块；(3) 加新的 `<head>` 和 `<body>` 框架。预计 HTML 从 3266 行减到 ~1500 行（CSS 和 JS 已外提）。

- [ ] **Step 5: 写页面底部元素（主题按钮 + 回到顶部 + 时间线详情面板）**

```html
    <!-- 帧时间线详情面板 -->
    <div class="txn-detail" id="txnDetail" style="display:none;" aria-label="事务详情">
        <div class="txn-detail-header">
            <span id="txnDetailTitle"></span>
            <button class="txn-detail-close" id="txnDetailClose" type="button" aria-label="关闭详情">✕</button>
        </div>
        <div class="txn-packet-list" id="txnDetailBody"></div>
    </div>

</main>

<!-- 主题切换按钮 -->
<div class="theme-bar">
    <button class="theme-btn" id="themeToggle" type="button"
            aria-label="切换到亮色模式" title="切换主题">🌙</button>
</div>

<!-- 回到顶部按钮 -->
<button class="scroll-top" id="scrollTopBtn" type="button"
        aria-label="回到顶部" title="回到顶部">↑</button>

</body>
</html>
```

- [ ] **Step 6: 验证** — 用浏览器打开 `usb-notes.html`，确认：
  - 侧边栏搜索框可输入过滤
  - 主题按钮可切换暗/亮（且无闪白）
  - 包结构图 4 个全部渲染
  - 帧时间线渲染并可点击展开详情
  - 所有旧内容完整保留
  - Console 无 JS 错误

---

### Task 7: 集成验证 + 清理

**Files:**
- Verify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.html`
- Verify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.css`
- Verify: `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.js`

- [ ] **Step 1: 完整对比 — 内容完整性**
  用 `grep` 统计新旧两版的 `.card[id]` 数量一致：
  ```bash
  grep -c 'class="card" id="kp-' usb-notes.html
  grep -c 'class="card" id="kp-' usb-notes-old.html
  ```
  期望：两个数字相等

- [ ] **Step 2: 检查所有可视化的 DOM 容器 ID 匹配**
  确认 JS 中引用的 ID（`pkt-token`, `pkt-sof`, `pkt-data`, `pkt-handshake`, `frameTimeline`, `txnDetail` 等）在 HTML 中均存在：
  ```bash
  for id in pkt-token pkt-sof pkt-data pkt-handshake frameTimeline txnDetail txnDetailTitle txnDetailBody txnDetailClose themeToggle sidebarSearch sidebarOverlay mobileNavBtn scrollTopBtn; do
    grep -q "id=\"$id\"" usb-notes.html && echo "✓ $id" || echo "✗ MISSING: $id"
  done
  ```

- [ ] **Step 3: 可访问性审计**
  在浏览器 DevTools 中运行 Lighthouse (Desktop, Accessibility only)，目标分数 ≥ 90

- [ ] **Step 4: 手动走查清单**
  - [ ] Tab 键遍历全部交互元素（skip-link→搜索→侧边栏链接→时间线块→主题按钮→回到顶部）
  - [ ] Enter/Space 激活时间线块展开/关闭
  - [ ] Escape 关闭时间线详情 + 关闭移动端 overlay
  - [ ] 搜索 "SETUP" → 侧边栏过滤 → 清空搜索 → 恢复全显
  - [ ] 浏览器窗口缩到 <1024px → 侧边栏隐藏、移动端导航出现、汉堡菜单可用
  - [ ] 打印预览 → 侧边栏和按钮隐藏、卡片无阴影
  - [ ] 暗色主题 → 刷新 → 保持暗色（无闪白）
  - [ ] 切到亮色 → 刷新 → 保持亮色
  - [ ] `prefers-reduced-motion: reduce` → 所有动画停止

- [ ] **Step 5: 删除旧文件（或归档）**
  ```bash
  # 验证无误后可删除备份：
  rm usb-notes-old.html
  ```

- [ ] **Step 6: Git commit**
  ```bash
  git add usb-notes.html usb-notes.css usb-notes.js
  git rm usb-notes-old.html   # 如果删除了
  git commit -m "refactor: full redesign of usb-notes.html

  Split 3266-line monolithic HTML into 3 files (HTML/CSS/JS).
  Dark-first IDE-style visual design with improved accessibility.

  - CSS: 10-layer organization, dual-palette (doc + semantic), 4px grid spacing
  - JS: 4 modules (Data→Renderers→Interaction→Init)
  - HTML: 4-space indentation, skip-link, search, progress bar, ARIA attributes
  - Responsive: single breakpoint at 1024px with hamburger menu overlay
  - Anti-flash theme: synchronous localStorage check in <head>
  - Print styles and reduced-motion support

  Co-Authored-By: Claude <noreply@anthropic.com>"
  ```

---

### Task 8: (收尾) 更新 HANDOFF.md

**Files:**
- Modify: `D:/CC/personal-lr-notes/CCNotes/USB/HANDOFF.md`

- [ ] **Step 1: 更新文件结构中关于 usb-notes 的描述**

将 HANDOFF.md 中：
```
├── usb-notes.html                                ← Phase 1-3 理论可视化
```
替换为：
```
├── usb-notes.html                                ← Phase 1-3 理论可视化（纯 HTML 结构）
├── usb-notes.css                                 ← 10 层分层样式（暗色默认 IDE 风格）
├── usb-notes.js                                  ← 4 模块脚本（数据/渲染/交互/初始化）
```

- [ ] **Step 2: 更新 HTML 编辑缩进提示**

在"关于 HTML 编辑"踩坑区域补充：
```
10a. usb-notes 已翻新为 3 文件架构，CSS/JS 已外提。HTML 编辑时无需再处理 <style>/<script> 块。
10b. 全部文件统一 4 空格缩进，不再有 Tab/空格混用问题。
```

- [ ] **Step 3: Git commit**
  ```bash
  git add HANDOFF.md
  git commit -m "docs: update HANDOFF for usb-notes 3-file redesign"
  ```
