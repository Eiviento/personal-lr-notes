# Task 1 审查：HTML 骨架 + CSS 基础系统

审查人：Claude 代码审查员
审查时间：2026-07-19
审查提交：203b36a — feat: create BLE protocol manual HTML skeleton with CSS foundation

---

## 判决

### 1. 规范遵从性：❌（发现违反全局约束的行为）

### 2. 任务质量：需要修复（存在 1 个关键性问题）

---

## 发现的问题

### 问题 1（关键）：localStorage 持久化违反了全局约束

**来源：** 计划第 15 行、设计规范第 249 行，以及审查输入中明确注明的全局约束。

**约束文本**："不持久化状态到 localStorage"

**实现结果：** 主题切换 JS 在 `localStorage` 中读写 `ble-manual-theme`：

```js
try { saved = localStorage.getItem('ble-manual-theme'); } catch(e){}
if(saved === 'dark' || saved === 'light'){
  setTheme(saved);
}
// ...稍后...
try { localStorage.setItem('ble-manual-theme', next); } catch(e){}
```

报告甚至将其列为功能："启动时优先读取 localStorage，回退到 prefers-color-scheme 系统检测"

任务计划（第 222-248 行）中提供的代码示例**根本没有使用 `localStorage`**——它只使用 `prefers-color-scheme` 媒体查询和点击切换。添加 `localStorage` 分支违反了约束。

**修复：** 移除所有 `localStorage` 读取/写入。主题状态必须是临时的——仅限会话。使用 `prefers-color-scheme` 进行初始检测，并为切换仅使用内存中的变量。例如：

```js
(function() {
  const html = document.documentElement;
  const btn = document.getElementById('themeBtn');
  const mq = window.matchMedia('(prefers-color-scheme: dark)');

  function setTheme(t) {
    html.setAttribute('data-theme', t);
    btn.textContent = t === 'dark' ? '\u{1F319}' : '☀️';
  }

  // 仅从系统偏好设置——没有 localStorage
  setTheme(mq.matches ? 'dark' : 'light');

  btn.addEventListener('click', function() {
    const cur = html.getAttribute('data-theme');
    setTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // 监听系统变化
  mq.addEventListener('change', function(e) {
    setTheme(e.matches ? 'dark' : 'light');
  });
})();
```

---

### 问题 2（重要）：布局类名与规范接口不匹配

**来源：** 任务计划第 41 行接口：
```
布局类（`.layout`, `.sidebar`, `.topbar`, `.main`）
```

**实现：** 使用 `.app-layout` 而不是 `.layout`。在开发过程中，后续任务（任务 2-9）将引用 `.layout` 作为容器包装器，导致它们在选择器中不匹配而失败。

**修复：** 将 `<div class="app-layout">` 重命名为 `<div class="layout">`，或将 CSS 类从 `.app-layout` 重命名为 `.layout`。

---

### 问题 3（重要）：类名模式与计划中指定的不同

实现使用 BEM 风格的类名（`.topbar__title`、`.topbar__theme-btn`、`.topbar__search-input`），而计划指定了扁平名称（`.topbar-title`、`.theme-btn`、`.topbar-search`）。

此外：
- 计划有在侧边栏外部的单独 `.sidebar-toggle` 按钮；实现将汉堡按钮放在顶栏内作为 `.topbar__hamburger`
- 主题按钮 ID 是 `themeToggle` 而不是计划的 `themeBtn`
- 侧边栏 ID 是 `sidebarContent` 而不是计划的 `sidebar`

虽然这是风格选择，但类名的差异意味着：
(a) 任务 1 没有匹配其指定的接口
(b) 引用这些类的后续任务将无法正确工作

**修复：** 将类名和 ID 与计划规范对齐，或更新接口文档。

---

### 问题 4（次要）：字体值偏离计划

**`--font`：** 计划指定 `"Noto Sans SC"`，实现使用 `"Hiragino Sans GB"` 并添加了 `"Helvetica Neue"`、`Helvetica`、`Arial`——不在规范中。

**`--font-mono`：** 完整的后备链被替换：
- 计划：`"SF Mono", "Cascadia Code", "Consolas", "Microsoft YaHei", monospace`
- 实现：`"SF Mono","Fira Code","Fira Mono","Roboto Mono","JetBrains Mono",Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace`

这是一个较小的可用性问题，不如 `Cascadia Code` 可靠（微软的一款优秀的等宽字体，在中文字符下对齐良好）。

---

### 问题 5（次要）：`html` 元素上缺少 `scroll-behavior: smooth`

计划在第 94 行有 `html { scroll-behavior: smooth; }`。实现没有。在任务 2 引入导航点击时，这将导致跳动而不是平滑滚动。

---

### 问题 6（次要）：添加了计划范围之外的装饰性 CSS

- `backdrop-filter: blur(8px)` 添加到顶栏（不在计划中，其他方面无害）
- 自定义滚动条样式（无意义，但不在计划中）
- `body` 使用 `min-height: 100vh` 而不是计划的 `height: 100vh; overflow: hidden;`

这些都不是破坏性的，但增加了与规范的偏差。

---

## 做得好的方面

- 所有 17 个 CSS 变量都已存在，值正确，并且 `[data-theme="dark"]` 覆盖完整
- 基本三栏布局（顶栏 + 侧边栏 + 主要内容区域）功能正常
- 响应式断点 900px 和 600px 如规范所定义
- 侧边栏抽屉逻辑（`.open` 类、点击内容关闭、窗口大小调整复位）正确实现
- 顶栏搜索框存在，样式正确（边框焦点、过渡）
- HTML 验证通过（正确的 doctype、元视口、aria 标签）
- 媒体查询监听器包括 `addEventListener` 回退到 `addListener`，实现了良好的兼容性

---

## 总结

该实现创建了一个可用的骨架，并正确实现了大部分 CSS 变量系统。然而，由于**localStorage 持久化**这一关键问题——违反了严格的全局约束——不能认为它符合规范。此外，类名与计划接口不匹配意味着后续任务将遇到故障。

需要在合并之前移除 localStorage 使用。在解决关键问题后，对类名和缺少的 `scroll-behavior` 进行小修将确保其他任务正常完成。
