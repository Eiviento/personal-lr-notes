# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-07-28（第三会话）
> 学习进度：32/67 知识点（48%）— 暂停在 Phase 4 入口
> Web 可视化：✅ 持续更新中（usb-notes.html，Phase 1-3 完整）

---

## 一、这个项目在做什么（给完全没有上下文的新会话）

### 主线任务：USB 协议系统学习

带一位 C/C++ 应用软件工程师从零开始学 USB 协议，最终目标是构建一个 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）。

### 副线任务：笔记 Web 可视化

把学习笔记做成**单文件离线 HTML 页面**，含交互式包结构图、描述符 byte-map、架构图。零外部依赖，双击打开。

---

## 二、本次会话完成了什么

### 主线：完成了 Phase 2 收尾 + 全部 Phase 3（11 知识点）

| 阶段 | 知识点 | 状态 |
|------|--------|------|
| Phase 2 补充 | SOF vs SETUP / SETUP 为什么必须 ACK / 127 设备带宽分析 | ✅ 笔记 + HTML |
| Phase 3 (3.1-3.11) | 描述符体系完整讲解 | ✅ 笔记 + HTML |

### HTML 页面新增卡片

| 卡片 | 内容 |
|------|------|
| 2.14 扩展 | SOF vs SETUP Token 7 维度对比表 |
| 2.17 | SETUP 必须 ACK 的三个根因（状态机/EP0 缓冲/不可重试语义）|
| 2.18 ⟐ | 完整帧内数据全景图：12 个事务的交互式时间线，点击展开内部包细节 |
| 2.19 | 127 设备带宽分析（折叠卡）：理论极限 vs 现实制约 |
| 3.1 | 描述符层级关系 + 两个 Q&A 折叠（端点 vs 接口、接口分类码） |
| 3.2 ⛁ | Device Descriptor 18 字节 byte-map + HEX 示例 |
| 3.3 | BCD 编码细节 + 三个坑 |
| 3.4 ⛁ | Configuration Descriptor 9 字节 byte-map + bmAttributes 位图 |
| 3.5 ⛁ | Interface Descriptor 9 字节 byte-map + 三级分类速查 + Q&A（端点共享+UVC） |
| 3.6 ⛁ | Endpoint Descriptor 7 字节 byte-map + bEndpointAddress/bmAttributes 位拆解 |
| 3.7 | bInterval 六种速率×传输类型公式总表 |
| 3.8 ⛁ | String Descriptor UTF-16LE 编码示例 |
| 3.9 | Device Qualifier 10 字节 byte-map |
| 3.10 | BOS Descriptor TLV 链表 + Capability 速查 |
| 3.11 | 类型码全集 + CDC 67 字节完整描述符链综合示例（默认展开）|

### 新增的文件

- `notes/phase3-descriptors.md` — Phase 3 全 11 节笔记（1242 行），含嵌入 Q&A 和 CDC 综合示例

### 提交记录（5 commits）

```
e082509 feat: add Phase 3 descriptor system notes and HTML cards (3.1–3.11)
6187a63 USB
ca6e65d feat: add 127-device bandwidth analysis (card 2.19) — foldable card
8681675 feat: add SOF vs SETUP comparison, SETUP ACK card, and interactive frame timeline diagram
077690b docs: add Phase 2 supplementary Q&A (transfer direction, endpoint authority, Token role)
```

---

## 三、当前文件结构

```
D:\CC\personal-lr-notes\CCNotes\USB\
├── HANDOFF.md                          ← 你正在看的这份交接文档
├── usb-protocol-learning-plan.md       ← 完整学习计划（67知识点清单）
├── usb-notes.html                      ← Web 可视化页面（2522行，Phase 1-3 完整）
├── docs/
│   └── superpowers/
│       ├── specs/2026-07-26-usb-notes-web-design.md
│       └── plans/2026-07-26-usb-notes-web-plan.md
├── notes/
│   ├── phase1-usb-overview.md          ← Phase 1（219行）
│   ├── phase2-communication-model.md   ← Phase 2（1048行，含6个补充问答）
│   └── phase3-descriptors.md           ← Phase 3（1242行，新增）
└── .superpowers/
    └── sdd/                            ← SDD 进度账本
```

---

## 四、当前卡在哪

**没有卡住。** Phase 3 刚刚完成（32/67，48%）。

**下一站：Phase 4 — USB 枚举过程逐包逐事务追踪（12 个知识点）**

从 4.1（枚举完整时间线：插入→检测→复位→Default→Address→Configured）开始讲。

---

## 五、不要踩的坑

### 关于用户和教学

1. **用户选的是方案 A（自底向上）。** 不要催他写代码。先把协议理论讲完，最后才是 libusb（Phase 8）。
2. **用户需要 MQTT 级别的精度。** 每个 byte 的每个 bit 含义都要展开。含糊带过他会追问。
3. **一次只讲一个知识点。** 每节等用户说"继续"才推进。不要一次塞多个。
4. **方向永远从 Host 视角。** IN = Device→Host, OUT = Host→Device。
5. **"会用+懂原理"（B档），不是内核驱动级别（C档）。** 不要跳 rabbit hole。
6. **用户喜欢类比。** MQTT 类比对他有效。用得好他会说"懂了"。
7. **计划文件是唯一真相源。** 用户要求调整计划 → 先更新计划文件再执行。
8. **用户会在学习过程中插入追问。** 这些追问通常很有价值——回答完后主动问"要不要保存到笔记？要不要补充到 HTML？"用户几乎总说"要"。
9. **讲完一个阶段后，用户可能要求把所有内容保存到笔记 + 更新 HTML。** 这是常规操作，记住笔记用 .md 文件，HTML 用 Edit/Write 工具。
10. **HTML 的 Edit 匹配对空格/制表符敏感。** 如果 Edit 报 "not found"，用 Grep 找到确切的行内容再匹配，或考虑用 Bash head/tail 拼接。

### 关于 HTML 页面

11. **usb-notes.html 是单文件。** 不要拆成多个文件。所有 CSS 在 `<style>`，所有 JS 在 `<script>`。
12. **CSS 变量在 `:root` 和 `.dark` 块中。** 新增颜色变量必须两个块都加。暗色模式颜色值更亮（如 `#845ef7` → `#b197fc`）。
13. **描述符 byte-map 用 `.desc-byte-map` + `.dcell` + `.dc-bg-*` 类。** 已有 15 个 bg 类可用。flex 比例 = 字段字节数（1字节=flex:1, 2字节=flex:2）。
14. **折叠内容用 `<details class="txn-fold">`。** 带三角箭头动画、hover 高亮。不要在折叠区嵌另一个折叠区（嵌套 `<details>` 容易出 CSS 问题）。
15. **新增卡片需要同步更新：** (a) 侧边栏 nav 项 (b) 侧边栏 badge 计数 (c) 卡片 HTML。
16. **帧时间线交互的 `FRAME_TRANSACTIONS` 在 JS 中定义。** 新增事务 push 一个对象即可，`showTxnDetail()` 自动渲染内部包细节。
17. **文件用 `Edit` 工具编辑，不要用 Bash cat/sed。** HTML 中大量特殊字符容易转义出错。但如果 Edit 匹配失败（大段替换），可用 Write 写临时文件 + Bash head/tail 拼接。
18. **usb-notes.html 用 LF 换行符，制表符缩进。**

### 关于平台

19. **用户环境是 Windows + Git Bash。** Shell 用 Bash 语法，路径用正斜杠。
20. **git 仓库根目录在 `D:/CC/personal-lr-notes/`。** USB 项目在 `CCNotes/USB/` 子目录。

---

## 六、新会话启动步骤

1. **读这份交接文档** — `Read HANDOFF.md`
2. **读学习计划** — `Read usb-protocol-learning-plan.md`
3. **读笔记目录** — `Glob notes/*.md`
4. **如果用户说"继续"：**
   - 从 Phase 4 的 4.1（枚举完整时间线）开始讲
   - 一次一个知识点，等用户说"继续"
5. **如果用户要看可视化页面：**
   - 告诉用户双击 `usb-notes.html` 即可在浏览器打开
   - Phase 3 已有完整的描述符 byte-map 和折叠 Q&A
   - Phase 4 学完后需要新增卡片（枚举时间线/各阶段抓包），可以用帧时间线的交互模式做枚举序列图
6. **如果用户不确定到哪了：**
   - "Phase 1-3 已完成（32/67），接下来 Phase 4 枚举过程。之前讲过的核心概念：描述符层级树、Device/Config/Interface/Endpoint 四种描述符逐字节、SOF vs SETUP、四种传输类型、包结构（Token/Data/Handshake）。准备好了说继续。"

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

### usb-notes.html 关键架构

- **CSS**：Grid 布局（sidebar 280px + main 1fr），主题变量 35 个在 `:root` + `.dark`
- **包图 6 色**：sync-pid=蓝, addr=青, data=橙, crc=紫, eop=灰, frame=绿
- **传输类型 6 色**（txn-* 变量）：sof=灰, control=紫, interrupt=红, bulk=青, isoch=绿, nak=橙
- **描述符 byte-map**：`.desc-byte-map` flex 布局，15 个 `.dc-bg-*` 颜色类
- **折叠卡**：`<details class="txn-fold">`，带三角动画
- **交互式帧时间线**：JS 数据驱动，`FRAME_TRANSACTIONS` 数组 + `renderTxnTimeline()` + `showTxnDetail()`
- **JS 模块**：`PACKET_DATA`(包图), `FRAME_TRANSACTIONS`(帧时间线), 主题切换, scroll spy

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
