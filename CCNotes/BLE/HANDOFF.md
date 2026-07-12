# HANDOFF.md — BLE 协议深度学习任务交接

## 任务概览

**用户身份**：Android 应用层开发者，需要开发蓝牙 APP 对接公司仪器仪表设备（流量计等）。

**用户背景**：对 BLE 零基础。

**学习目标**：真正理解 BLE 协议的工作过程（不是"能调 API 就行"的深度）。

**学习策略**：自底向上——从 PHY 物理层 → Link Layer → HCI + L2CAP → SM 安全管理器 → ATT + GATT → Android API 实战。

---

## 已完成（All Done ✅）

### 阶段一：BLE 全景概览 ✅
- 1.1 BLE vs 经典蓝牙
- 1.2 协议栈三层架构（含物理归属补充问答）
- 1.3 核心概念速览
- 1.4 学习路线图

### 阶段二：物理层 PHY ✅
- 2.1 2.4GHz ISM 频段
- 2.2 40 信道设计
- 2.3 GFSK 调制与三种 PHY（含问答：频率突变为何占用宽频谱）
- 2.4 发射功率/接收灵敏度/链路预算/RSSI
- 2.5 与 Wi-Fi/经典蓝牙/Zigbee 对比

### 阶段三：链路层 Link Layer ✅
- 3.1 链路层状态机（5 状态：Standby/Advertising/Scanning/Initiating/Connection）
- 3.2 三个广播信道深度分析
- 3.3 广播 PDU 类型（含问答：Header 格式、四种广播能否同时发、定向广播 InitA 来源、ADV_IND 能否直连）
- 3.4 广播参数（含问答：SCAN_REQ/RSP 状态变化、设备隔离方案）
- 3.5 连接建立全过程（CONNECT_IND 的 36 字节参数）
- 3.6 连接事件与自适应跳频（150μs IFS、AFH、空包、Latency）
- 3.7 链路层 PDU 格式（LL Data PDU、Control PDU、加密范围、数据封装旅程）

### 阶段四：HCI + L2CAP ✅
- 4.1 HCI（五类包、传输层、Snoop Log）
- 4.2 L2CAP（CID 协议复用、SAR 分片重组、Credit 流控）

### 阶段五：安全管理器 SM ✅
- 5.1 安全流程全景（配对→加密→密钥分发→绑定）
- 5.2 配对方式总览（IO Capabilities、Just Works/Passkey/Numeric/OOB）
- 5.3 LE Legacy Pairing 详解（TK→STK→AES-CMAC）
- 5.4 LE Secure Connections 详解（ECDH P-256、F4/F5/F6、防 MITM 原理）
- 5.5 密钥分发与绑定（LTK/IRK/CSRK、Resolvable Private Address、含问答：为何无 CA 证书）
- 5.6 链路层加密（AES-CCM、Session Key 派生、加密三次握手）

### 阶段六：ATT + GATT ✅
- 6.1 ATT 协议基础（Client-Server、Handle/UUID/Permissions）
- 6.2 ATT PDU 类型全解（12 种核心 PDU）
- 6.3 GATT 数据组织（Service/Characteristic/Descriptor 树）
- 6.4 UUID 体系（16-bit vs 128-bit、Base UUID 模板）
- 6.5 服务发现流程（三 Round：Service→Characteristic→Descriptor）
- 6.6 读写与通知操作（含 CCCD 写流程、重连必重写 CCCD）
- 6.7 MTU 协商（默认 23→协商 251、requestMtu 须在 discoverServices 前）
- 6.8 标准 Profile 参考（流量计 GATT 表设计建议）

### 阶段七：GAP + Android 实战 ✅
- 7.1 GAP 角色（Android 固定为 Central）
- 7.2 广播与扫描（ScanSettings/ScanFilter/ScanRecord/RSSI）
- 7.3 Android BLE API 分层（BluetoothAdapter→Gatt→Service→Char→Desc→Callback）
- 7.4 综合实战（FlowMeterBleManager 完整代码）

### 附：方法论文档
- `方法论-概念深度学习提示词模板.md` — 完整方法论
- `提示词卡片.md` — 极简可复制的 5 段提示词
- `概念速查手册-阶段一+阶段六.md` — 阶段一+六合并速查

---

## 当前卡在哪

**没有卡住。** 全部 7 个阶段、36 个知识点任务已全部完成。

---

## 下一步计划

用户可以：

1. **复习**：回顾任意阶段的笔记文件，文件在 `D:\CC\personal-lr-notes\CCNotes\BLE\` 下，命名格式 `X.X-标题.md`

2. **结合设备实践**：拿到实际的流量计设备后，用 nRF Connect App 扫描连接，对照笔记中的 GATT 表结构查看实际的 Service/Characteristic

3. **编码**：基于 7.4 的 `FlowMeterBleManager` 代码框架，替换 UUID 为实际设备的值，开始开发

4. **深入专题**：
   - BLE Mesh（如果公司后续需要多设备组网）
   - LE Audio（如果涉及音频）
   - Wireshark BLE 抓包分析（需要专用 Sniffer 硬件，如 nRF52840 Dongle）
   - BLE 5.x 新特性深入（Advertising Extensions、Periodic Advertising、AoA/AoD）

5. **开始新主题**：用 `提示词卡片.md` 中的模板启动另一个领域的学习

---

## 踩过的坑 & 重要约定（绝对不要再踩）

### 交互模式约定
- ✅ **内容先在对话中呈现**，用户确认没问题后再保存为笔记文件
- ✅ 每个知识点末尾问"有疑问吗？没问题我保存继续"
- ✅ 用户的提问和回答要融入笔记文件（QA 记录）
- ❌ 不要在用户没确认的情况下直接写文件（只适用于 BLE 学习，其他任务仍需确认是否需要）

### 用户提问风格
- 用户是技术背景（应用开发），但 BLE 零基础
- 用户会追问底层原理（如"频率突变为什么占用宽频谱"、"为什么没有 CA 证书"）
- 善用类比的解释方式非常有效（如"笛子吹音"、"广场喊话"、"邮局和卡车"）
- 用户喜欢的回答结构：直觉理解 → 技术细节 → 实际影响

### BLE 知识要点（高频问答点）
- 双芯片 vs 单芯片架构：手机是双芯片（Host 在主 CPU，Controller 在蓝牙 IC），IoT 设备是单芯片 SoC
- ADV_IND 可以直接被 CONNECT_IND 连接，不需要先转定向广播
- 重连后必须重新写 CCCD（连接断开 CCCD 自动归零）
- requestMtu() 必须在 discoverServices() 之前调用
- Android 不能同时扫描和发起连接（必须在 Standby 状态串行）
- Android 10 以下需要开 GPS 才能扫描 BLE

### 笔记管理
- 笔记文件命名：`X.X-标题.md`（如 `3.3-广播PDU类型.md`）
- 笔记间用 `[[文件名]]` WikiLink 格式互相关联
- 问答记录放在笔记末尾的"## 问答记录"节
- 学习计划进度在 `00-学习计划.md` 中用 checkbox 追踪

### 未解决的开放问题
- 无。所有学习过程中的疑问已当场解答并记录在对应笔记中。

---

## 文件索引

所有文件位于：`D:\CC\personal-lr-notes\CCNotes\BLE\`

```
00-学习计划.md                          ← 总计划 + 进度追踪
方法论-概念深度学习提示词模板.md           ← 完整方法论
提示词卡片.md                           ← 极简 5 段提示词
概念速查手册-阶段一+阶段六.md             ← 刚生成的合并速查

1.1-BLE是什么与经典蓝牙的区别.md
1.2-协议栈三层架构.md
1.2-补充-协议栈的物理归属.md
1.3-核心概念速览.md
1.4-学习路线图.md

2.1-2.4GHz-ISM频段与信道划分.md
2.2-40个信道.md
2.3-GFSK调制与速率.md
2.4-发射功率接收灵敏度链路预算.md
2.5-与WiFi经典蓝牙Zigbee物理层对比.md

3.1-链路层状态机.md
3.2-三个广播信道深度分析.md
3.3-广播PDU类型.md
3.4-广播参数.md
3.5-连接建立全过程.md
3.6-连接事件与自适应跳频.md
3.7-链路层PDU格式.md

4.1-HCI主机控制器接口.md
4.2-L2CAP逻辑链路控制与适配协议.md

5.1-安全流程全景.md
5.2-配对方式总览.md
5.3-LE-Legacy-Pairing详解.md
5.4-LE-Secure-Connections详解.md
5.5-密钥分发与绑定.md
5.6-链路层加密.md

6.1-ATT协议基础.md
6.2-ATT-PDU类型全解.md
6.3-GATT数据组织.md
6.4-UUID体系.md
6.5-服务发现流程.md
6.6-读写与通知操作.md
6.7-MTU协商.md
6.8-标准Profile参考.md

7.1-GAP角色.md
7.2-广播与扫描的Android实现.md
7.3-Android-BLE-API分层.md
7.4-综合实战.md
```

---

*生成时间：2026-07-12*
*总学习周期：2 天，7 阶段，36 个知识点，30+ 个问答*
