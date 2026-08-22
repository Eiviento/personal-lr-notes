# BLE 协议解析树设计文档

- 日期：2026-08-22
- 需求来源：《ble-protocol-manual.html》（同目录）
- 交付物：`CCNotes/BLE/ble-protocol-tree.html`（单文件，零依赖，双击即开）

## 1. 目标

把手册中的 BLE 空中帧协议结构做成一张**可折叠展开的纵向目录树**，从「完整空中帧」逐层下钻到 ATT/SMP 的 Opcode 全集，帮助按层理解协议封装。

## 2. 布局与深度

- **布局**：纵向目录树（根在最上，子节点向右缩进），非经典左右分叉图。原因：树深 6~7 层、标签为长中文，纵向布局不会横向溢出。
- **深度**：完整展开到最细——字段逐字节拆解、Opcode/Code 全集。
- **默认展开到第 3 层**：可见「空中帧 → PDU → 广播/数据 → Header/Payload/DATA/CONTROL」主干，细节按需下钻。

## 3. 树内容大纲

```
BLE 完整空中帧（Preamble│AA│PDU│MIC│CRC）
└─ PDU = LL Header(2B) + Payload(0~251B)
   ├─ 链路层·广播（广告信道 37/38/39）
   │  ├─ PDU Header 16bit：Length(8b)│RxAdd│TxAdd│ChSel│RFU│PDU Type(4b)，每位可展开说明
   │  ├─ PDU Type(4b) 7 种：ADV_IND / ADV_DIRECT_IND / ADV_NONCONN_IND /
   │  │   SCAN_REQ / SCAN_RSP / CONNECT_IND / ADV_SCAN_IND，各自 Payload 结构
   │  │  └─ CONNECT_IND：12 字段逐字节（InitA/AdvA/AA/CRCInit/WinSize/WinOffset/
   │  │      Interval/Latency/Timeout/ChM/Hop/SCA）
   │  └─ AdvData = AD Structure LTV：Length│AD Type│AD Data，解析规则 + 实例 + 常用 AD Type 表
   └─ 链路层·数据（数据信道 0~36）
      ├─ PDU Header 16bit：Length(8b)│RFU(2b)│CP│MD│SN│NESN│LLID(2b)，每位可展开说明
      ├─ LL Control (LLID=11)：Opcode(1B)+CtrData；19 个 Opcode 全集，
      │   关键 8 个（CONNECTION_UPDATE/CHANNEL_MAP/TERMINATE/VERSION/FEATURE/PHY/LENGTH/REJECT）有 Payload 字段表
      └─ LL Data (LLID=10 完整或起始 / LLID=01 续传或空包)
         ├─ 空包（Length=0）：仅 LL Header + CRC
         └─ L2CAP：Length(2B)│CID(2B)│Payload
            ├─ ATT (CID=0x0004)：Opcode(1B，bit7 签名/bit6 命令标志/bit5:0 方法)
            │   └─ Opcode 全集 4 组：读 / 写 / 通知与指示 / 错误与 MTU
            ├─ SMP (CID=0x0006)：Code(1B)+Data；14 个 Code 全集 + 配对四阶段简述
            └─ L2CAP Signaling (CID=0x0005)：3 条命令 + 与 LL 层改连接参数的对比
```

## 4. 交互规格

- 点击行首箭头或整行 toggle 展开/折叠，带平滑动画。
- 顶部工具条：**展开全部 / 折叠全部 / 展开至第 N 层 / 搜索过滤**。
- 搜索：过滤节点、高亮命中、自动展开命中路径。
- 顶部显示完整空中帧字节条；悬停帧内字段时，树中对应节点高亮（双向联动）。

## 5. 样式规格

- 中文标签 + 英文协议名；字节数用等宽字体。
- 节点按协议层配色：物理层 / 链路层广播 / 链路层数据 / LL Control / L2CAP / ATT / SMP / Signaling 各一色，字段节点统一中性色。
- 浅色主题，风格与手册一致；无外部字体/图片/CSS。

## 6. 实现结构

- 单文件：内嵌 CSS + 原生 JS。
- 树数据存为 JS 对象数组（节点字段：id、label、en、size、desc、kind、children）；kind 决定配色与图标。
- 递归渲染函数 + 展开状态管理（Set 记录展开节点 id，便于「展开全部/至第 N 层」）。

## 7. 验证

- 浏览器打开页面：JS 无报错；默认展开第 3 层；展开/折叠/搜索/展开至第 N 层均正常。
- 内容与手册第 2~8 章核对一致。

## 8. 范围外

- 不改动手册本身；不引入任何外部依赖；以桌面浏览器为主（不做移动端触控专项优化）。
