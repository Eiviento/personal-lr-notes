# Spec: usb-notes.html 全面翻新设计

> 版本：v1.0 | 日期：2026-08-02 | 状态：待用户评审

---

## 概述

对 `usb-notes.html` 进行**全面翻新**（C 级），形态从单文件（3266 行, ~195KB）拆分为 3 文件结构。设计风格定位为**技术文档/IDE 风**（A），暗色主题为默认，桌面优先响应式策略，数据可视化保留 JS 渲染逻辑只升级 CSS，可访问性全面覆盖。

---

## 一、文件架构

### 1.1 拆分方案

从单文件拆为 3 文件，同目录，`usb-notes.html` 双击即用：

```
CCNotes/USB/
├── usb-notes.html      ← 纯 HTML 结构 (~1500行)
├── usb-notes.css       ← 全部样式 (~800行)
└── usb-notes.js        ← 全部脚本 (~500行)
```

### 1.2 编码规范

| 规范 | 值 |
|------|----|
| HTML 缩进 | **4 空格**（统一） |
| CSS 缩进 | **4 空格** |
| JS 缩进 | **4 空格** |
| 引号 | HTML/CSS 双引号，JS 单引号 |
| 换行 | LF |
| 编码 | UTF-8 |
| CSS 组织 | 10 层分层（见第五节） |
| JS 组织 | Data → Renderers → Interaction → Init |

### 1.3 引用方式

```html
<!-- usb-notes.html -->
<head>
  <link rel="stylesheet" href="usb-notes.css">
  <script src="usb-notes.js" defer></script>
</head>
```

---

## 二、视觉设计系统

### 2.1 配色方案

采用**双色板体系**——"语义色"用于协议可视化，"文档色板"用于页面 chrome。

#### 语义色（从现有继承，微调）

用于包结构图、byte-map、时间线的字段类型编码：

| 变量 | 用途 | 暗色值 | 亮色值 |
|------|------|--------|--------|
| `--color-sync-pid` | SYNC/PID 字段 | `#8ab4f8` | `#1e90ff` |
| `--color-addr` | 地址/端点字段 | `#63e6be` | `#20c997` |
| `--color-data` | 数据 payload | `#ffc078` | `#ffa94d` |
| `--color-crc` | CRC 校验字段 | `#b197fc` | `#845ef7` |
| `--color-eop` | EOP 结束信号 | `#dee2e6` | `#adb5bd` |
| `--color-frame` | 帧号字段 | `#69db7c` | `#51cf66` |
| `--txn-control` | 控制传输 | `#b197fc` | `#845ef7` |
| `--txn-interrupt` | 中断传输 | `#ff8787` | `#ff6b6b` |
| `--txn-bulk` | 批量传输 | `#63e6be` | `#20c997` |
| `--txn-isoch` | 等时传输 | `#69db7c` | `#51cf66` |
| `--txn-sof` | SOF 广播 | `#dee2e6` | `#adb5bd` |
| `--txn-nak` | NAK 无数据 | `#ffc078` | `#ffa94d` |

#### 文档色板（新增）

用于页面外壳：侧边栏、卡片、代码、文字。

**暗色主题（默认）**：

| 变量 | 值 | 用途 |
|------|----|------|
| `--bg` | `#1a1b1e` | 页面背景 |
| `--surface` | `#1e1f24` | 侧边栏底色 |
| `--card-bg` | `#25262b` | 卡片底色 |
| `--card-border` | `#373a40` | 卡片边框 |
| `--code-bg` | `#141517` | 代码块底色 |
| `--text` | `#c1c6cc` | 正文 |
| `--text-heading` | `#e9ecef` | 标题 |
| `--text-muted` | `#868e96` | 次要文字 |
| `--accent` | `#4da6ff` | 强调色（链接、激活态、focus） |
| `--accent-dim` | `rgba(77,166,255,0.12)` | 强调色浅底 |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.3)` | 默认阴影 |
| `--table-stripe` | `rgba(255,255,255,0.03)` | 表格斑马纹 |

**亮色主题**：

| 变量 | 值 |
|------|----|
| `--bg` | `#ffffff` |
| `--surface` | `#f6f8fa` |
| `--card-bg` | `#ffffff` |
| `--card-border` | `#d0d7de` |
| `--code-bg` | `#f6f8fa` |
| `--text` | `#1f2328` |
| `--text-heading` | `#0d1117` |
| `--text-muted` | `#656d76` |
| `--accent` | `#0969da` |
| `--accent-dim` | `rgba(9,105,218,0.08)` |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.06)` |
| `--table-stripe` | `rgba(0,0,0,0.02)` |

### 2.2 字体体系

#### 五级字号 scale

| 级别 | 字号 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| `h1` | 28px | 1.3 | 700 | 页面大标题（暂无） |
| `h2` | 22px | 1.35 | 600 | Phase 标题 |
| `h3` | 17px | 1.4 | 600 | Card 内标题 |
| `body` | 15.5px | 1.7 | 400 | 正文 |
| `caption` | 12px | 1.5 | 400 | 辅助标注、图例 |

#### 字体栈

```css
--font-sans: 'Inter', 'SF Pro Text', -apple-system, BlinkMacSystemFont,
             'Segoe UI', 'Noto Sans SC', sans-serif;
--font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code',
             'Consolas', 'Courier New', monospace;
```

- 正文/标题：`var(--font-sans)`
- 代码/byte-map/时间线标注：`var(--font-mono)`

### 2.3 间距系统

基于 4px 网格：

| 变量 | 值 | 用途 |
|------|----|------|
| `--space-1` | 4px | 最密间距（图标与文字） |
| `--space-2` | 8px | 紧凑间距（行内元素间） |
| `--space-3` | 12px | 默认内边距 |
| `--space-4` | 16px | 段落间距 |
| `--space-5` | 20px | 卡片内边距 |
| `--space-6` | 24px | 卡片间距 |
| `--space-7` | 28px | 段落组间距 |
| `--space-8` | 32px | Section 间距 |

### 2.4 圆角

| 变量 | 值 | 用途 |
|------|----|------|
| `--radius-sm` | 4px | 代码块、标签 |
| `--radius-md` | 8px | 卡片、折叠区 |
| `--radius-lg` | 12px | 大面板 |
| `--radius-full` | 999px | 时间线胶囊、按钮 |

### 2.5 设计原则

- 暗色默认，亮色为辅助
- 卡片无 hover 上浮效果（IDE 风格克制）
- 过渡统一 `0.15s ease`，非必要不加动画
- 色彩饱和度降低 10-15%（相对于当前版本，更舒适长时间阅读）

---

## 三、布局与导航

### 3.1 桌面布局（≥1024px）

```
┌──────────────────┬───────────────────────────────┐
│  Sidebar         │  Main Content                 │
│  260px fixed     │  max-width: 960px             │
│                  │  margin: 0 auto               │
│  ┌搜索框──────┐  │                               │
│  │ filter... │  │  ┌─ Phase Header ────────────┐ │
│  └───────────┘  │  │  2.1 三层通信模型          │ │
│                  │  └──────────────────────────┘ │
│  ▸ Phase 1 ✓     │  ┌─ Card ───────────────────┐ │
│    · 1.1         │  │  内容...                  │ │
│    · 1.2         │  └──────────────────────────┘ │
│  ▾ Phase 2 ✓     │                               │
│    · 2.1 ●       │  ┌─ Card ───────────────────┐ │
│    · 2.2         │  │  内容...                  │ │
│  ▸ Phase 3 ✓     │  └──────────────────────────┘ │
│  ▸ Phase 4 ○     │                               │
│                  │                               │
│  ┌进度条 48%──┐  │                               │
│  └────────────┘  │                               │
└──────────────────┴───────────────────────────────┘
```

### 3.2 侧边栏

- 宽度 260px，`position: fixed`, `height: 100vh`
- 背景 `--surface`（与页面背景区分 1-2 级）
- 右侧 1px `--card-border` 分割线
- 顶部标题 "USB 协议学习笔记" + 版本号 small
- 搜索框：`<input type="search">` 实时过滤章节（见 3.5）
- Phase 折叠菜单：
  - Phase 1-3 默认展开（`open`）
  - Phase 4-8 折叠，标注"即将更新"
  - 子项 `.active` 样式：左边框 3px `--accent` + 文字 `--accent` + 浅底 `--accent-dim`
- 底部进度条：`48%` 宽度，`role="progressbar"`

### 3.3 搜索框

- 位置：侧边栏标题下方
- 行为：`input` 事件触发 → 遍历侧边栏 `.sub-item` → 匹配 `textContent` → `display: none/block`
- 若某 Phase 下所有子项均隐藏，整个 Phase 折叠区也隐藏
- 清空搜索框恢复全部显示
- CSS `::placeholder` = "过滤章节..."

### 3.4 进度条

```html
<div class="progress-wrap" role="progressbar" aria-valuenow="48" aria-valuemin="0" aria-valuemax="100" aria-label="学习进度 48%">
  <div class="progress-bar" style="width:48%"></div>
  <span class="progress-label">32/67 (48%)</span>
</div>
```

### 3.5 滚动监听（Scroll Spy）

- 当前所在 Card 对应的侧边栏链接高亮
- 同时高亮所属 Phase 的 summary 文字（加粗 + 颜色）
- `requestAnimationFrame` 节流（替代当前无节流的 `scroll` 事件）
- 触发阈值：Card 顶部距视口顶部 ≤ 150px

### 3.6 响应式断点

| 断点 | 行为 |
|------|------|
| ≥1024px | 桌面：侧边栏 260px + 内容 max-width 960px |
| <1024px | 平板/手机：侧边栏 → 顶部 sticky 窄导航条（汉堡菜单 overlay），内容全宽 |

**顶部 sticky 导航条**（<1024px）：
- 高度 48px，暗色背景，左对齐标题 + 右对齐汉堡图标
- 点击汉堡 → overlay 显示完整侧边栏（`position: fixed; inset: 0; z-index: 100`）
- overlay 背景半透明遮罩，点击遮罩关闭
- `<details>` 在 overlay 内正常工作

---

## 四、数据可视化升级

### 4.1 包结构图（`.packet-diagram`）

**保留**：`PACKET_DATA` 数据模型 + `renderPacket()` 渲染逻辑

**升级 CSS**：
- 字段条高度：固定 48px（当前 `padding: 10px 4px` → 不固定）
- 字段分隔：`border-right: 1px solid rgba(0,0,0,0.2)` 暗色 / `rgba(0,0,0,0.08)` 亮色
- tooltip 重设计：从单行 → 多行卡片
  ```
  ┌──────────────────┐
  │ ADDR   7 bits    │
  │ 0x01~0x7F        │
  │ 设备地址，7bit    │
  │ → 128个，0x00保留 │
  └──────────────────┘
  ```
  动画 `fadeIn` 0.15s，`position: absolute; bottom: calc(100% + 8px)`
- tooltip 智能定位：如果字段靠左 → 左对齐；靠右 → 右对齐（用 JS 判断 `getBoundingClientRect`）
- 新增"图例行"：包图上方一行小标签
  ```
  ■ SYNC/PID  ■ ADDR/ENDP  ■ DATA  ■ CRC  ■ EOP
  ```
  用 `display: flex; gap: var(--space-4); font-size: var(--caption)`

### 4.2 描述符 byte-map（`.desc-byte-map`）

**保留**：HTML 结构（`.dcell` 系列）

**升级 CSS**：
- cell 最小宽度：`min-width: 32px`（当前 `min-width: 0`，可能过窄）
- cell 内部 3 行：
  - `.doff` = offset（上）
  - `.dval` = 值（中，加粗）
  - `.dlabel` = 标签（下）
- hover 发光：`box-shadow: 0 0 6px currentColor`
- 水平滚动条美化（webkit scrollbar 伪元素，暗色主题用细暗条）

### 4.3 帧时间线（`.frame-timeline`）

**保留**：`FRAME_TRANSACTIONS` 数据 + `renderTxnTimeline()` + `showTxnDetail()` 交互

**升级 CSS**：
- 事务块形状：从方角矩形 → 圆角胶囊 `border-radius: 20px`
- 颜色方案：从 `color-mix()` 背景 → 纯色浅底 + 左侧 3px 实色条
  ```css
  .txn-block.txn-control {
    background: color-mix(in srgb, var(--txn-control) 12%, var(--card-bg));
    border-left: 3px solid var(--txn-control);
  }
  ```
- NAK 块：虚线边框 + 更低对比度底色（明确"无数据"语义）
- 详情面板：从"弹出面板需要 scrollIntoView" → 时间线下方内嵌展开（`details` 模拟），不跳转

### 4.4 Bus Hound 抓包注释

**保留**：`.txn-annot-*` 结构和数据

**升级**：
- 代码行号：纯 CSS `counter-reset: bh-line` + `counter-increment` + `::before { content: counter(bh-line) }`
- SETUP 包 8 字节分色标注：
  - Byte 0 (bmRequestType) → `--color-sync-pid`
  - Byte 1 (bRequest) → `--color-crc`
  - Byte 2-3 (wValue) → `--color-data`
  - Byte 4-5 (wIndex) → `--color-addr`
  - Byte 6-7 (wLength) → `--color-frame`

---

## 五、性能与代码质量

### 5.1 CSS 分层组织

```css
/* ===================================
   1. Variables — 自定义属性
   =================================== */
   :root { ... }    /* 暗色主题变量（默认） */
   .light { ... }   /* 亮色主题变量 */

/* ===================================
   2. Reset — 重置与基础
   =================================== */
   *, *::before, *::after { box-sizing: border-box; }
   /* ... 基础 reset */

/* ===================================
   3. Typography — 字体与排版
   =================================== */
   body { font-family, font-size, line-height }
   h1, h2, h3, h4 { ... }
   code, pre { ... }

/* ===================================
   4. Layout — 布局
   =================================== */
   body { display: grid; ... }
   .sidebar { ... }
   .main { ... }

/* ===================================
   5. Components — UI 组件
   =================================== */
   /* 5.1 Sidebar */
   /* 5.2 Card */
   /* 5.3 Table */
   /* 5.4 Code & Pre */
   /* 5.5 Folds (details/summary) */
   /* 5.6 Theme toggle */
   /* 5.7 Search box */
   /* 5.8 Progress bar */
   /* 5.9 Skip link */
   /* 5.10 Scroll-to-top */

/* ===================================
   6. Visualizations — 数据可视化
   =================================== */
   /* 6.1 Packet diagram */
   /* 6.2 Descriptor byte map */
   /* 6.3 Frame timeline */
   /* 6.4 Transaction detail panel */
   /* 6.5 Bus Hound annotations */

/* ===================================
   7. Utilities — 工具类
   =================================== */
   .sr-only { ... }
   .focus-ring { ... }

/* ===================================
   8. Responsive — 响应式
   =================================== */
   @media (max-width: 1023px) { ... }

/* ===================================
   9. Reduced Motion — 减少动画
   =================================== */
   @media (prefers-reduced-motion: reduce) { ... }

/* ===================================
   10. Print — 打印样式
   =================================== */
   @media print { ... }
```

### 5.2 JS 模块化

```javascript
// usb-notes.js

// ===== 1. DATA =====
const PACKET_DATA = [ ... ];
const FRAME_TRANSACTIONS = [ ... ];

// ===== 2. RENDERERS =====
const PacketRenderer = {
  render(data) { ... },
  renderAll() { ... }
};

const TimelineRenderer = {
  render(txn) { ... },
  renderAll() { ... },
  showDetail(txn, block) { ... },
  closeDetail() { ... }
};

// ===== 3. INTERACTION =====
const ThemeManager = {
  init() { ... },
  toggle() { ... },
  getSaved() { ... }
};

const ScrollSpy = {
  init() { ... },
  update() { ... }      // rAF-throttled
};

const SearchFilter = {
  init() { ... },
  filter(query) { ... }
};

const NavOverlay = {
  init() { ... },
  open() { ... },
  close() { ... }
};

// ===== 4. INIT =====
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  ScrollSpy.init();
  SearchFilter.init();
  NavOverlay.init();
  PacketRenderer.renderAll();
  TimelineRenderer.renderAll();
});
```

### 5.3 关键实现要点

- **主题防闪白**：`<head>` 顶部加 6 行同步阻塞脚本
  ```html
  <script>
  (function(){var t=localStorage.getItem('usb-notes-theme');
  if(t==='light')document.documentElement.classList.add('light');
  else document.documentElement.classList.add('dark');})();
  </script>
  ```
  然后用 CSS `.dark` / `.light` 控制变量，无需 JS 等待 DOMContentLoaded

- **默认暗色**：CSS `:root` 写暗色变量，`.light` 写亮色覆盖。无 localStorage 时默认暗色

- **时间线详情展开**：从 `scrollIntoView` 改为 inline expand——在时间线容器内追加一个详情行，不打断阅读流

- **dark/light class 挂载**：从 `<html class="dark">` 切换，不是 `<body>`

### 5.4 HTML meta 标签

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="USB 协议系统学习笔记 — 逐字节精讲，含包结构图、描述符 byte-map、帧时间线">
<meta name="theme-color" content="#1a1b1e" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<title>USB 协议学习笔记 — 逐字节精讲</title>
<link rel="stylesheet" href="usb-notes.css">
<script src="usb-notes.js" defer></script>
```

### 5.5 迁移策略

1. 创建 `usb-notes.css` — 从零按分层写 CSS，不直接复制粘贴旧文件
2. 创建 `usb-notes.js` — 按模块重写 JS，复用 `PACKET_DATA` 和 `FRAME_TRANSACTIONS` 数据
3. 重写 `usb-notes.html` — 4 空格缩进，去掉 `<style>` 和 `<script>`，加 meta 标签和 skip-link
4. 保留 `usb-notes-old.html` 作为备份（或依赖 git 历史）

---

## 六、可访问性

### 6.1 键盘导航

| 元素 | 键盘行为 |
|------|---------|
| 侧边栏链接 | Tab 聚焦，Enter 跳转 |
| 折叠区 `<details>` | 原生键盘支持（Tab→summary，Enter/Space 展开） |
| 搜索框 | Tab 聚焦，输入即过滤，Escape 清空 |
| 时间线块 | Tab 聚焦，Enter/Space 展开详情，Escape 关闭 |
| 主题按钮 | Tab 聚焦，Enter/Space 切换 |
| 跳过链接 `.skip-link` | 第一个 Tab，Enter 跳到 `<main>` |

### 6.2 ARIA 属性

| 元素 | 属性 |
|------|------|
| `<nav class="sidebar">` | `aria-label="目录导航"` |
| `<main>` | `aria-label="学习笔记正文"` |
| 侧边栏 `<details>` | 保持原生（已自带 role） |
| 搜索框 | `aria-label="过滤章节"` |
| 进度条外框 | `role="progressbar" aria-valuenow="48" aria-valuemin="0" aria-valuemax="100" aria-label="学习进度 48%"` |
| 包结构图 `.field` | `aria-label` 由 JS 生成（例：`"ADDR, 7 bits, 设备地址 0x01-0x7F"`） |
| 时间线块 | `role="button" tabindex="0" aria-expanded="false/true"` |
| 时间线详情面板 | `aria-label="事务详情"` |
| 折叠区 `.txn-fold` | 保持原生 `<details>` |

### 6.3 对比度合规

暗色和亮色主题均满足 WCAG AA（≥4.5:1 正文，≥3:1 大号文字）：

| 元素 | 暗色对比度 | 亮色对比度 |
|------|-----------|-----------|
| 正文 `--text` vs `--bg` | ~10:1 | ~13:1 |
| 标题 `--text-heading` vs `--bg` | ~13:1 | ~17:1 |
| 次要文字 `--text-muted` vs `--bg` | ~5:1 | ~5.5:1 |
| 链接 `--accent` vs `--bg` | ~4.6:1 | ~5.7:1 |

### 6.4 Focus 样式

- 全局：`outline: 2px solid var(--accent); outline-offset: 2px`
- 替换浏览器默认 `:focus-visible` 虚线框
- 侧边栏链接 focus：与 active 同款左边框蓝条（只改颜色不改形状）

### 6.5 减少动画

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  html { scroll-behavior: auto; }
}
```

### 6.6 跳过链接

```html
<a class="skip-link" href="#main-content">跳到内容</a>
```

```css
.skip-link {
  position: fixed; top: -100%; left: 8px; z-index: 999;
  padding: 8px 16px; background: var(--accent); color: #fff;
  border-radius: var(--radius-sm); font-size: 14px;
}
.skip-link:focus { top: 8px; }
```

### 6.7 打印样式

```css
@media print {
  .sidebar, .theme-bar, .skip-link { display: none; }
  body { display: block; }
  .main { max-width: 100%; padding: 0; }
  .card { break-inside: avoid; box-shadow: none; border: 1px solid #ccc; }
}
```

---

## 七、非目标（明确不做）

- ❌ 不引入构建工具、PostCSS、minifier（保持零依赖双击打开）
- ❌ 不添加动画/微交互（除 tooltip fadeIn）
- ❌ 不改变 URL hash 路由策略（保持 `#kp-1-1` 风格）
- ❌ 不添加 PDF/EPUB 导出
- ❌ 不添加评论/用户系统
- ❌ 不引入 Web Font（字体全部用系统栈，`JetBrains Mono`/`Inter` 仅在已安装时使用）
- ❌ 不实现 Phase 4-8 内容（仅标注"即将更新"）

---

## 八、产物清单

| 文件 | 操作 | 预计行数 |
|------|------|---------|
| `usb-notes.html` | **重写** | ~1500 |
| `usb-notes.css` | **新建** | ~800 |
| `usb-notes.js` | **新建** | ~500 |
| `usb-notes-old.html` | **删除**（或归档） | — |
