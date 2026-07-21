# HANDOFF.md — BLE 协议学习任务交接

## 用户身份与背景

- **身份**：Android 应用层开发者，零 BLE 基础起步
- **设备**：OPPO Enco Air2 蓝牙耳机（用于练习）
- **最终目标**：给学校同学讲解 BLE 协议全栈，需要一份系统化的教学参考资料
- **学习风格**：自底向上（PHY→Link Layer→HCI→L2CAP→SMP/ATT），追问底层原理，喜欢类比

---

## 当前任务：重写 BLE 协议交互报文完整手册

### 做了什么

用户在学习完 BLE 全部 7 个阶段 36 个知识点后，要求整理一份**树状层级结构的协议报文参考手册**，作为教学用途。

**第一版**（旧会话）：26 个扁平"情况"排列（广告5→连接10→SMP6→加密5），每个 case 补了 PDU Header 字段表。

**第二版**（本会话）：**完全重写**为 10 章树状结构，核心思路是"沿着协议栈自底向上，每到一层就把该层的包头格式、字段定义、操作码全集就地展开，到 L2CAP 层后分两条路——SMP（安全）和 ATT/GATT（数据），最后在加密章节两条路汇合"。

### 已完成 ✅

**`附录-BLE协议交互报文完整手册.md`**（1253 行），10 章结构：

| 章 | 内容 | 核心速查表 |
|----|------|-----------|
| 一 | 协议栈总览 | ASCII 树状图 + 各层一句话定位 + 完整 27 步报文序列全景 |
| 二 | 物理层 | 空中帧结构、Access Address 广告/数据区别、MIC vs CRC 对比 |
| 三 | 链路层-广播阶段 | 广告 PDU Header 16-bit 位布局、AdvData LTV 格式、**8 种常用 AD Type 速查表**（含字节级实例）、CONNECT_IND 10 字段 |
| 四 | 链路层-连接阶段 | 数据 PDU Header 16-bit 位布局、LL Data vs Control 区别、**LL Control Opcode 20 个全集**、7 个 Control PDU Payload 字段表 |
| 五 | HCI | 简述（不过空中）、Host↔Controller 架构图 |
| 六 | L2CAP | 包格式 [Len\|CID\|Payload]、**CID 4 个**、L2CAP Signaling 控制命令表、LL Control vs L2CAP Signaling 改参数的两条路对比 |
| 七 | SMP（左分叉） | SMP PDU 格式 + **Code 15 个全集**、配对四阶段流程图、四种认证路径分叉图、SC vs Legacy 对比、密钥派生链、密钥分发 5 种 PDU |
| 八 | ATT/GATT（右分叉） | ATT PDU 格式 + **Opcode 22 个全集**（按读/写/通知/错误/MTU 分组）、GATT 数据层级（含 CCCD 详解）、服务发现三 Round、MTU 协商 |
| 九 | 加密完整流程 | 跨层总览（SMP→LL 协作）、三次握手 Payload 表、SessionKey 派生公式、加密范围图（标注哪些字段明文/密文+原因）、重连跳过 SMP 直接加密、异常情况 3 种 |
| 十 | 综合速查表 | **五合一速查**：LL Control / SMP / ATT / L2CAP CID / AD Type |
| 附录 | 典型报文序列 | OPPO 耳机 27 步完整序列（广告→连接→SMP SC NumComp→加密→ATT 写 CCCD），每步标注层和信道 |

### 与旧版的核心区别

| 维度 | 旧版（26 情况平铺） | 新版（10 章树状层级） |
|------|-------------------|---------------------|
| 组织方式 | 按场景枚举 | 按协议分层 + 时序双线 |
| AD Type | 一笔带过 | LTV 格式详解 + 8 种速查表 + 字节级实例 |
| L2CAP Signaling | 缺失 | CID=0x0005 命令表 + 与 LL Control 对比 |
| SMP | 与加密混在第四/五章 | 独立成章，四阶段流程图 + 四条认证路径 |
| ATT | 分散 | Opcode 全集按类别分组（读/写/通知/错误/MTU） |
| 加密 | 孤立章节 | 跨层总览，标注每层职责 |
| 速查表 | 一张综合表 | 五张独立速查表（LL/SMP/ATT/CID/AD Type） |
| 学习入口 | 需按情况序号逐条读 | 可从总览树跳到任意章节 |

---

## ✅ 已完成：HTML 交互学习页面

基于手册内容制作的单文件交互式 HTML 页面已完成。

### 产出

- **`ble-protocol-manual.html`**（~3276 行，单文件，零外部依赖，双击即可在浏览器打开）

### 实现功能

| 组件 | 说明 |
|------|------|
| 📑 10 章全覆盖 | 协议栈总览 → PHY → 链路层(广播+连接) → HCI → L2CAP → SMP → ATT/GATT → 加密 → 速查表 → 27 步序列 |
| 🌳 左侧树形导航 | 44 个锚点，滚动跟踪高亮（IntersectionObserver），移动端抽屉收起 |
| 🎨 位布局可视化 | 5 个位布局组件（广告 PDU Header / 数据 PDU Header / 空中帧 / CONNECT_IND / LTV），色块条 + 详细表格联动高亮，精细到每个 bit 的类型和含义 |
| 🖼 完整帧视图 | 3.1 / 4.1 / 6.1 / 8.5 节：展示当前层在外层封装中的嵌套位置，讲解目标段白色高亮 + 放大，其余字段半透明。已覆盖：广告帧(PDU Header)、数据帧(PDU Header)、L2CAP帧(LL→L2CAP→Payload)、MTU帧(LL→L2CAP→ATT PDU) |
| 📖 字段折叠详释 | 基于用户 Q&A 记录，为 9 个高频追问字段添加可折叠深入解释（3.1：PDU Type/ChSel/TxAdd/Length；4.1：LLID/SN&NESN/MD/CP/Length；6.1：L2CAP Length） |
| 🔗 SMP 触发链路 | 7.1 节新增：三种触发方式 + LL 加密命令（LL_ENC_REQ/RSP → LL_START_ENC_REQ/RSP）的完整 ASCII 流程图，明确 SMP（协商密钥）与 LL（启用加密）的分层职责 |
| 📦 MTU 协商完整拆解 | 8.5 节重写：从 LL Header 每一个 bit → L2CAP 头 → ATT PDU 的三层完整报文拆解，含 Request/Response 逐字段对比 + 默认 vs 协商后 MTU 影响对比表 |
| ⏱ 27 步时序图 | 完整报文序列（广告→连接→SMP→加密→ATT→断开），点击步骤展开详情，可选自动播放/调速(0.5x/1x/2x) |
| 📊 五合一速查表 | LL Control Opcode / SMP Code / ATT Opcode / L2CAP CID / AD Type，Tab 切换 + 即时搜索过滤 |
| 🔄 纯 CSS 流程图 | 协议栈 7 层层叠块、配对四阶段流程、四种认证路径分支、加密范围标注（明文/密文分色） |
| 🌓 主题切换 | 默认跟随系统 `prefers-color-scheme`，支持手动切换深色/浅色（教学投影友好） |
| 🔍 全局搜索 | 搜索章节标题 + 表格内容，匹配高亮，Escape 清除 |
| 📱 响应式 | 900px 以下侧栏变抽屉，600px 以下表格横向滚动 |

### 架构

- 文案为静态 HTML，结构化数据（位布局、时序步骤、速查表）以 JS 对象存储，页面加载时渲染函数替换占位标记生成 DOM
- 冷色系配色（蓝/青/绿/紫/橙/灰），CSS 变量驱动主题切换
- **新增组件**：`FRAME_VIEWS` 数据驱动完整帧视图（`renderFrameView()`），已覆盖 4 个场景（adv/data/l2cap/mtu-exchange）；字段详释通过 CSS `.field-detail` 折叠块 + 内联 onclick 实现（零 JS 依赖）
- 零依赖：无 CDN、无 node_modules、无外部字体/图标库

### 设计文档

- Spec: `docs/superpowers/specs/2026-07-19-ble-protocol-html-design.md`
- Plan: `docs/superpowers/plans/2026-07-19-ble-protocol-html-plan.md`
- 开发审查记录: `.superpowers/sdd/`（9 个任务 × 实现报告 + 审查报告，最终审查 Spec 10/10 ✅，准确性 8/8 ✅）

---

## 绝对不要再踩的坑

### 1. BLE 规范层面的精确性问题

- **PDU Type 是 4 bit 不是 2 bit**（广告信道 PDU Header）。用户曾亲自纠正这个错误。数据信道用 LLID（2 bit），广告信道用 PDU Type（4 bit），两者在同一个 16-bit 头但字段结构完全不同。
- **广播 PDU Header 的 Length 位数**：3.3 笔记中用的 6 bit，手册用的 8 bit。两者都正确（BLE 4.0~4.1 是 6 bit，4.2+ 扩展为 8 bit），但**手册内必须统一**，不要混用。
- **SMP Confirm (Code=0x03) 在 SC 和 Legacy 中含义不同**：Legacy 中是 AES-CMAC(TK, Rand)；SC 中 Numeric Comparison 用户确认后也发 Confirm 但意义不同。不要混淆。
- **LL_START_ENC_REQ/RSP 本身是明文**——这个很容易想当然写成"加密后发送"，但逻辑上对方必须先读到"即将切换到加密"才能切换解密引擎。

### 2. 手册编写约定

- **禁止凭空捏造**——用户强调"因为是要给整个学校的同学讲解"。手册中每个 Opcode 值、字段名、位布局都必须可追溯（已有笔记验证或蓝牙 Core Spec 确认）。
- **不要用模糊表述**：例如 "大概 20 个左右" → 必须精确到具体数字。"可能有" → 要么确认、要么删掉。
- **手册和深度问答是正本-答疑关系**：手册为主，问答为补。不要在手册中引入问答里未确认的新内容。

### 3. 用户交互偏好

- 用户喜欢**树状图/流程图**辅助理解（ASCII art 即可，不必复杂图表）
- 用户对**协议分层**的上下关系非常关注（"这条数据经过哪几层，每层给它加了什么头"）
- "底层都是广播"这类概念需要精确区分物理广播 vs 协议广播包

### 4. 关键 BLE 知识高频点（手册中已覆盖但教学时容易讲错）

- Access Address 不是 PDU 字段，是帧头（Preamble 后面、PDU 前面）
- 广告包 Access Address = 0x8E89BED6（固定），数据包 = 随机值（CONNECT_IND 下发）
- CONNECT_IND 发出后从设备不回复 ACK——确认发生在第一次连接事件（150μs 内必须回复）
- CCCD 连接断开自动归零——重连必须重写
- 加密协商全过程不使用广播包（都在连接建立后走 LL Data PDU）
- SC Just Works：加密了但 MITM 可以解密（攻击者在 Phase 2 替换公钥）
- LL Control PDU 和 LL Data PDU 是平级关系，不是嵌套关系

### 5. 文件管理

- 所有 BLE 笔记在 `D:\CC\personal-lr-notes\CCNotes\BLE\`
- 笔记用 `[[文件名]]` WikiLink 互相关联
- 手册是 `附录-BLE协议交互报文完整手册.md`
- 深度问答是 `附录-报文手册深度问答.md`
- 不要修改已有的阶段笔记（1.x~7.x），它们是学习过程的原始记录

---

## 关键文件索引

```
D:\CC\personal-lr-notes\CCNotes\BLE\
├── 00-学习计划.md                        ← 总学习计划
├── HANDOFF.md                            ← 本文件
├── 附录-BLE协议交互报文完整手册.md         ← 核心参考资料（1253 行）
├── 附录-报文手册深度问答.md               ← 手册答疑副册
├── ble-protocol-manual.html              ← HTML 交互学习页面（~3276 行，双击打开）
│
├── docs/superpowers/
│   ├── specs/2026-07-19-ble-protocol-html-design.md   ← HTML 页面设计文档
│   └── plans/2026-07-19-ble-protocol-html-plan.md     ← HTML 页面实现计划
│
├── 1.x-*.md ~ 7.x-*.md                  ← 7 阶段 36 个知识点（已完成，勿改）
│
└── 8.1-OPPO耳机练手App-MainActivity.java  ← 练习 App 源码
    8.1-OPPO耳机练手App-配置说明.md         ← App 配置说明
```

---

## HTML 任务完成记录

### 首次开发（2026-07-19）

任务于 2026-07-19 完成。实现过程中遵循了以下原则：

1. **用真内容，不用 Lorem Ipsum**。手册中每个 Opcode 值、字段名、位值都经过验证，HTML 中直接使用。
2. **先确认再码代码**。设计阶段逐项确认：页面结构（全内容覆盖）、交互方式（点击展开）、视觉风格（冷色系简洁）、深色模式（跟随系统 + 手动切换）。
3. **测试覆盖面**：手册中所有表格（Opcode 速查表、AD Type 表、CID 表等）均在 HTML 中正确渲染。
4. **不引入新框架**：单文件 HTML，零外部依赖。

### 改进（2026-07-20 第一批）

基于用户反馈完成三项改进：

1. **合并重复字段介绍**：3.4 节 (a)-(d) 各 PDU 类型不再重复 PDU Header 各字段描述，改为链接引用 3.1 节。
2. **新增完整帧视图**：3.1 / 4.1 节增加完整空中帧色块条（Preamble→AA→PDU→Payload→CRC），PDU Header 段白色高亮。
3. **新增字段折叠详释**：基于 Q&A 为 9 个高频追问字段添加可折叠深入解释。

### 改进（2026-07-20 第二批）

基于用户继续反馈完成四项改进：

4. **L2CAP 帧视图**：6.1 节新增 L2CAP 嵌套帧视图（LL Header → L2CAP Header 高亮 → Payload），展示"L2CAP 不直接面对空中，被封装在 LL Payload 里"。L2CAP Length 字段新增折叠详释（来自 Q11）。
5. **SMP 触发链路**：7.1 节开头新增完整 ASCII 流程图，说明三种触发方式（Security Request / Pairing Request / GATT 按需）+ LL 加密四命令（LL_ENC_REQ/RSP → LL_START_ENC_REQ/RSP），明确 SMP（协商密钥）与 LL（启用加密）的分层职责。
6. **MTU 协商完整拆解**：8.5 节重写为三层完整报文格式，逐层展示每一位的选择理由（LL Header 每个 bit 值 + L2CAP 头 + ATT PDU），含 Request/Response 对比 + MTU 影响对比表 + 链路层限制提醒。
7. **Q19 新增**：ATT/GATT Handle 本质（16 位查找键、属性表结构、不定长存储、单次读写上限公式）。

### 后续建议

- 如需修改内容（如新增 BLE 5.1+ 特性），编辑 JS 数据层即可（BIT_LAYOUTS / TIMING_STEPS / REF_TABLES），HTML 文案可直接修改对应 `<section>`
- 如需添加新章节，同时在 TREE 导航数据和 HTML `<section>` 中新增
- 位布局色块条颜色在 `BIT_LAYOUTS` 各字段的 `color` 属性中修改

---

*交接时间：2026-07-20（更新：L2CAP 帧视图 + SMP 触发链路 + MTU 三层拆解 + Q19）*
*旧会话记录：`C:\Users\fdl\.claude\projects\D--CC-personal-lr-notes-CCNotes-BLE\42366f4e-55c1-4825-b45e-192bf9174bde.jsonl`*
