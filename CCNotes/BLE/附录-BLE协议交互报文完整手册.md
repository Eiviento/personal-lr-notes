# 附录：BLE 协议交互报文完整手册

> **面向读者**：已了解 BLE 基本概念，需要系统查阅各层报文格式、字段定义、操作码全集的开发者。
>
> **阅读路线**：第一章总览树 → 沿协议栈自底向上逐层查阅。到 L2CAP 层后分两路：**SMP（安全/加密路）**和 **ATT/GATT（数据路）**，最后在第九章"加密完整流程"两条路汇合。

---

## 一、协议栈总览与阅读路线

### 1.1 协议栈树状图

```
                           应用层 (App)
                               │
                    ┌──────────┴──────────┐
                    │                     │
              SMP (CID=0x0006)      ATT (CID=0x0004)
              安全管理器               属性协议
              [配对待加密]            [读写通知]
                    │                     │
                    └──────────┬──────────┘
                               │
                         L2CAP 层 (CID 复用/分片重组)
                               │
                         HCI (Host↔Controller 内部接口，不过空中)
                               │
                    链路层 (Link Layer)
                    ┌──────────┴──────────┐
                    │                     │
              广告信道 (37/38/39)     数据信道 (0~36)
              ADV_IND / SCAN /        LL Data PDU / LL Control PDU
              CONNECT_IND             [跳频 + 加密]
                    │                     │
                    └──────────┬──────────┘
                               │
                          物理层 (PHY)
                    2.4GHz GFSK, Preamble + Access Address
```

### 1.2 各层一句话定位

| 层 | 一句话 | 关键标识 |
|----|--------|---------|
| **PHY** | 无线电波怎么调制、帧头怎么同步 | Preamble 0xAA, Access Address |
| **Link Layer** | 包怎么发、怎么确认、怎么跳频 | PDU Header: PDU Type(广告) / LLID(数据) |
| **HCI** | 芯片内部 Host↔Controller 通信 | 不过空中，ATA 抓包看不到 |
| **L2CAP** | 协议复用（给 SMP 还是 ATT？）、分片重组 | CID 字段 |
| **SMP** | 配对、密钥交换、身份认证 | CID=0x0006, 7 种 PDU Code |
| **ATT/GATT** | 数据读写通知的"语言"和数据组织 | CID=0x0004, 20+ 种 Opcode |

### 1.3 一条完整连接的报文序列全景

```
设备B (Peripheral)                           设备A (Central)
  │                                               │
  │ ═══════════ 广播阶段 (37/38/39 信道) ═══════════│
  │ ADV_IND [AdvA + AdvData(LTV)] ───────────────→│
  │←─────────────── SCAN_REQ ────────────────────│  (可选)
  │ SCAN_RSP ───────────────────────────────────→│  (可选)
  │←─────────────── CONNECT_IND ────────────────│
  │                                               │
  │ ═══════════ 连接阶段 (数据信道 0~36) ════════════│
  │←──→ LL Data PDU / LL Control PDU ──←──→      │
  │   (参数协商: VERSION_IND, FEATURE_REQ/RSP)    │
  │                                               │
  │ ═══════════ SMP 配对 (L2CAP CID=0x0006) ═══════ │
  │←──→ Pairing Req/Rsp → Public Key →            │
  │     DHKey Check → Key Distribution            │
  │                                               │
  │ ═══════════ 链路加密 ═══════════════════════════ │
  │ LL_ENC_REQ/RSP → LL_START_ENC_REQ/RSP         │
  │ ═════════ 此后全部 AES-CCM 加密 ═══════════════ │
  │                                               │
  │ ═══════════ ATT 数据交互 (L2CAP CID=0x0004) ════ │
  │←──→ discoverServices → read/write/notify      │
  │                                               │
  │ ═══════════ 断开 ═══════════════════════════════ │
  │ LL_TERMINATE_IND ────────────────────────────→│
```

> 阅读建议：如果只想查某个字段/Opcode，直接跳到**第十章综合速查表**。

---

## 二、物理层 — 空中帧结构

### 2.1 完整空中帧

所有 BLE 包在空中的完整结构（从 PHY 层看）：

```
┌──────────┬──────────────┬──────────────────────────────────┬───────┬─────┐
│ Preamble │Access Address│              PDU                 │  MIC  │ CRC │
│  1 字节   │   4 字节      │ ┌──────────┬──────────────────┐ │ 4 字节 │3 字节│
│  0xAA    │              │ │LL Header │    Payload        │ │       │     │
│          │              │ │  2 字节   │  0~251 字节       │ │       │     │
└──────────┴──────────────┴─┴──────────┴──────────────────┴─┴───────┴─────┘
```

### 2.2 Access Address

| 阶段 | Access Address | 说明 |
|------|---------------|------|
| **广告包** | `0x8E89BED6` | 蓝牙规范固定值，所有 BLE 设备共用 |
| **数据包** | 32-bit 随机值 | CONNECT_IND 的 AA 字段下发，每个连接唯一 |

**作用**：
- 广告包：链路层硬件用 0x8E89BED6 识别"这是一个 BLE 广播包"
- 数据包：链路层硬件用 AA 过滤——匹配才收，不匹配直接丢弃（不消耗 CPU）

### 2.3 MIC 与 CRC

| | MIC (Message Integrity Check) | CRC (Cyclic Redundancy Check) |
|---|---|---|
| **位置** | 紧接 Payload 之后 | 帧末尾 3 字节 |
| **大小** | 4 字节 | 3 字节 |
| **目的** | 防**人为篡改**（安全） | 防**物理误码**（噪声干扰） |
| **算法** | AES-CBC-MAC（用 Session Key） | 多项式除法（公开算法） |
| **明文/密文** | 加密时随 Payload 一起加密 | 始终明文 |
| **何时出现** | 仅加密后的 Data PDU 有 | 所有包都有 |
| **验证方** | 只有持有 LTK 的配对双方 | 任何人都能算 |

> CRC 防天灾（无线噪声），MIC 防人祸（篡改攻击）。

---

## 三、链路层 — 广播阶段（广告信道）

链路层 PDU Header 有**两套格式**——广告信道和数据信道完全不同。本章讲广告信道。

### 3.1 广告信道 PDU Header 格式（16 bit）

```
 bit: [15:8]    [7]   [6]    [5]    [4]   [3:0]
     ┌────────┬──────┬──────┬──────┬─────┬──────────┐
     │ Length │RxAdd │TxAdd │ChSel │ RFU │ PDU Type │
     │ 8 bit  │ 1b   │ 1b   │ 1b   │ 1b  │  4 bit   │
     └────────┴──────┴──────┴──────┴─────┴──────────┘
```

| 字段 | 位宽 | 位范围 | 说明 |
|------|------|--------|------|
| **PDU Type** | 4 bit | [3:0] | 0000=ADV_IND, 0001=ADV_DIRECT_IND, 0010=ADV_NONCONN_IND, 0011=SCAN_REQ, 0100=SCAN_RSP, 0101=CONNECT_IND, 0110=ADV_SCAN_IND |
| RFU | 1 bit | [4] | Reserved (保留) |
| ChSel | 1 bit | [5] | 信道选择算法: 0=Algorithm1, 1=Algorithm2 |
| TxAdd | 1 bit | [6] | 发送方地址类型: 0=Public MAC, 1=Random MAC |
| RxAdd | 1 bit | [7] | 目标方地址类型: 0=Public MAC, 1=Random MAC（仅 ADV_DIRECT_IND 和 CONNECT_IND 使用） |
| **Length** | 8 bit | [15:8] | Payload 字节数（6~37） |

### 3.2 广告 PDU Payload 结构（AdvA + AdvData）

广播 PDU 的 Payload 格式因 PDU Type 而异：

```
ADV_IND / ADV_NONCONN_IND / ADV_SCAN_IND:
  [AdvA(6B)] [AdvData(0~31B)]
   └─── Payload ─────────────┘

ADV_DIRECT_IND:
  [AdvA(6B)] [InitA(6B)]     ← 无 AdvData
   └── Payload=12B ──────────┘

SCAN_REQ:
  [ScanA(6B)] [AdvA(6B)]
   └── Payload=12B ───┘

SCAN_RSP:
  [AdvA(6B)] [ScanRspData(0~31B)]
   └─── Payload ─────────────────┘

CONNECT_IND:
  [InitA(6B)] [AdvA(6B)] [LLData(22B)]
   └── Payload=34B ───────────────────┘
```

### 3.3 AdvData / ScanRspData — AD Structure LTV 格式

广播数据用 **LTV（Length-Type-Value）** 自描述格式编码，多个 AD Structure 依次拼接。

#### 3.3.1 单个 AD Structure 格式

```
┌──────────┬──────────┬─────────────────────┐
│  Length  │ AD Type  │      AD Data        │
│  1 字节   │  1 字节   │  (Length-1 字节)    │
└──────────┴──────────┴─────────────────────┘
```

| 字段 | 大小 | 含义 |
|------|------|------|
| **L (Length)** | 1 字节 | Type + Data 的总长度（不含自身）。值为 0 表示 AD 列表结束 |
| **T (Type)** | 1 字节 | 由蓝牙 SIG 统一分配的 AD Type 编号 |
| **V (Value)** | Length-1 字节 | 实际数据，格式取决于 AD Type |

#### 3.3.2 解析规则

```
逐字节解析：
  读 Length → 如果为 0，结束
            → 如果 > 0，读取 Type (1B) + Data (Length-1 B)
            → 指针前进 Length 字节 → 继续读下一个 Length
```

#### 3.3.3 实例

```
02 01 06        ← Length=2, Type=0x01(Flags), Data=0x06
03 03 0F 18     ← Length=3, Type=0x03(Complete 16-bit UUIDs), Data=0x0F 0x18
                   → UUID 列表: 0x180F (Battery Service)
09 09 46 4C 4F 57 4D 45 54 45 52
                ← Length=9, Type=0x09(Complete Local Name), Data="FLOWMETER"
00              ← Length=0, AD 列表结束
```

#### 3.3.4 常用 AD Type 速查表

| AD Type | 名称 | Data 格式 | 说明 |
|---------|------|-----------|------|
| **0x01** | Flags | 1 字节位掩码 | **必须排第一个**。bit0=LE Limited Discoverable, bit1=LE General Discoverable, bit2=BR/EDR Not Supported |
| 0x02 | Incomplete 16-bit Service UUIDs | 多个 16-bit UUID (小端) | 放不下的服务 UUID，需 SCAN_RSP 补全 |
| 0x03 | Complete 16-bit Service UUIDs | 多个 16-bit UUID (小端) | 完整的 16-bit 服务 UUID 列表 |
| 0x06 | Incomplete 128-bit Service UUIDs | 多个 128-bit UUID | 同上，128-bit 版本 |
| 0x07 | Complete 128-bit Service UUIDs | 多个 128-bit UUID | 同上，128-bit 版本 |
| 0x08 | Shortened Local Name | UTF-8 字符串 | 设备简称 |
| **0x09** | Complete Local Name | UTF-8 字符串 | 设备全名（如 "FLOWMETER"） |
| **0x0A** | TX Power Level | 1 字节有符号整数 | 发射功率 dBm（用于距离估算） |
| 0x16 | Service Data (16-bit UUID) | UUID(2B) + Data | 服务关联数据 |
| **0xFF** | Manufacturer Specific Data | Company ID(2B 小端) + 自定义 | 厂商自定义数据（如 iBeacon） |

> **LTV 的优势**：自描述格式——解析方不需要预先知道 31 字节里放了什么，逐字节解析即可。新增 AD Type 不影响兼容性。

### 3.4 广播→连接流程与各 PDU 报文

```
设备B (Peripheral)                        设备A (Central)
  │                                           │
  │ ADV_IND ─────────────────────────────────→│  (a) 37/38/39 信道轮发
  │   PDU Type=0000, AdvA, AdvData(LTV)       │
  │                                           │
  │←──────────── SCAN_REQ ──────────────────  │  (b) 可选，主动扫描时发
  │             PDU Type=0011                 │
  │ SCAN_RSP ───────────────────────────────→│  (c) 可选，额外 31 字节
  │   PDU Type=0100, AdvA, ScanRspData        │
  │                                           │
  │←──────────── CONNECT_IND ─────────────── │  (d) 发起连接
  │             PDU Type=0101, Payload=34B    │
  │                                           │
══╪══════════ Connection ═══════════════════╪══
```

#### (a) ADV_IND 报文

**PDU Header (16 bit)**：PDU Type=0000, RFU=0, ChSel=0, TxAdd=0/1, RxAdd=0, Length=6+AdvData长度

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | 广播方 MAC 地址 |
| AdvData | 0~31 字节 | AD Structure LTV 格式 |

#### (b) SCAN_REQ 报文

**PDU Header**：PDU Type=0011, Length=12

**PDU Payload (12 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| ScanA | 6 字节 | 扫描方 MAC 地址 |
| AdvA | 6 字节 | 目标广播方 MAC（确认是发给我的） |

#### (c) SCAN_RSP 报文

**PDU Header**：PDU Type=0100, Length=6+ScanRspData长度

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | 广播方 MAC |
| ScanRspData | 0~31 字节 | AD Structure LTV 格式（额外数据） |

> AdvData(31B) + ScanRspData(31B) = 最多 **62 字节**广播数据。

#### (d) CONNECT_IND 报文 — 最重要的一个包

**PDU Header**：PDU Type=0101, Length=34

**PDU Payload (34 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| InitA | 6 字节 | 发起方 MAC |
| AdvA | 6 字节 | 广播方 MAC |
| **AA** | **4 字节** | **32 位随机 Access Address** ← 后续所有数据包用这个值标识连接 |
| CRCInit | 3 字节 | CRC 计算初始值 |
| WinSize | 1 字节 | 传输窗口 = 1.25ms × WinSize |
| WinOffset | 2 字节 | 第一次连接事件偏移 = 1.25ms × WinOffset |
| **Interval** | 2 字节 | 连接间隔 = 1.25ms × Interval（7.5ms ~ 4s） |
| Latency | 2 字节 | 从设备可跳过的连接事件次数（0~499） |
| **Timeout** | 2 字节 | 监督超时 = 10ms × Timeout（100ms ~ 32s） |
| ChM | 5 字节 | 37 位信道图：bit=1 表示可用 |
| Hop | 1 字节 | 跳频增量（5~16，必须与 37 互质） |
| SCA | 1 字节 | 睡眠时钟精度（0~7，ppm） |

**关键约束**：

```
(1 + Latency) × Interval × 2 ≤ Timeout
```

违反此约束可能导致从设备跳过一次事件后被误判断连。

**CONNECT_IND 之后**：双方立即进入 Connection State。数据包用 Access Address = AA（替代 MAC 地址），按 ChM 指定的信道跳频通信。**从设备不回复 ACK**——真正的确认是第一次连接事件中从设备在 150μs 内回复。

### 3.5 广播 PDU 类型选择决策

```
需要被连接？
├── 是 → 限制谁能连？
│   ├── 是（已知 MAC） → ADV_DIRECT_IND (Payload=12B, 无 AdvData)
│   └── 否             → ADV_IND (最常用)
└── 否 → 需要更多广播数据？
    ├── 是 → ADV_SCAN_IND (+ SCAN_RSP = 62B)
    └── 否 → ADV_NONCONN_IND (纯信标)
```

| PDU Type | PDU Type 值 | 可扫描 | 可连接 | 有 AdvData | 典型场景 |
|----------|------------|--------|--------|-----------|---------|
| ADV_IND | 0000 | ✅ | ✅ | ✅ | 通用广播等连接 |
| ADV_DIRECT_IND | 0001 | ❌ | ✅ (仅 InitA) | ❌ | 快速重连已配对设备 |
| ADV_NONCONN_IND | 0010 | ❌ | ❌ | ✅ | iBeacon/Eddystone 信标 |
| ADV_SCAN_IND | 0110 | ✅ | ❌ | ✅ | 仅广播+额外信息 |

---

## 四、链路层 — 连接阶段（数据信道）

连接建立后，所有通信在数据信道（0~36）上进行。PDU Header 从"广告信道格式"切换为"数据信道格式"。

### 4.1 数据信道 PDU Header 格式（16 bit）

```
 bit: [15:8]    [7:6]  [5]   [4]   [3]   [2]   [1:0]
     ┌────────┬──────┬─────┬─────┬─────┬─────┬────────┐
     │ Length │ RFU  │ CP  │ MD  │ SN  │NESN │  LLID  │
     │ 8 bit  │ 2b   │ 1b  │ 1b  │ 1b  │ 1b  │ 2 bit  │
     └────────┴──────┴─────┴─────┴─────┴─────┴────────┘
```

| 字段 | 位宽 | 位范围 | 说明 |
|------|------|--------|------|
| **LLID** | 2 bit | [1:0] | **10**=LL Data PDU（起始片段）, **01**=LL Data PDU（空包/续传片段）, **11**=LL Control PDU |
| **NESN** | 1 bit | [2] | Next Expected SN——确认对方上一包已收，期望对方下一个包的 SN 值 |
| **SN** | 1 bit | [3] | Sequence Number——本包序列号（0/1 翻转=新包, 相同=重传包） |
| **MD** | 1 bit | [4] | More Data——1=本连接事件内还有更多数据要发 |
| **CP** | 1 bit | [5] | Coded PHY 指示（BLE 5.0: 0=非Coded PHY, 1=Coded PHY） |
| RFU | 2 bit | [7:6] | Reserved |
| **Length** | 8 bit | [15:8] | Payload 字节数（0=空包, 最大 27/251 取决于特性协商） |

**SN/NESN 确认重传机制**：

```
停等协议（Stop-and-Wait）：一次只发一包，收到回复才发下一包。

SN:  本包序列号，新包 0→1→0→1 交替翻转
     连续两包 SN 相同 → 这是重传
NESN: 告诉对方"我收到了你 SN=X 的包，期待你的下一个 SN=NESN"
     确认和期望打包在同一个字段里

例：Master(SN=0) → Slave 回复(NESN=1) → Master(SN=1) → ...
```

### 4.2 LLID 决定 PDU 类型

| LLID | PDU 类型 | 含义 |
|------|---------|------|
| 10 | **LL Data PDU** | 承载上层数据（L2CAP→ATT 或 SMP），起始片段 |
| 01 | **LL Data PDU** | 空包（维持心跳/确认）或分片续传片段 |
| 11 | **LL Control PDU** | 链路层自身管理命令 |

### 4.3 LL Data PDU 结构

```
┌──────────┬────────────────────────────────────┬───────┬─────┐
│LL Header │              Payload                │  MIC  │ CRC │
│  2 字节   │ ┌──────────┬─────────────────────┐ │ 4 字节 │3 字节│
│LLID=10   │ │ L2CAP头  │   上层协议数据       │ │(加密时)│     │
│          │ │Len(2)+CID│                     │ │       │     │
└──────────┴─┴──────────┴─────────────────────┴─┴───────┴─────┘
```

**Payload = L2CAP 包**（详见第六章）。LL Data PDU 本身不关心 Payload 里的内容——它只是"卡车"，把 L2CAP 包从 A 运到 B。

**LL Data PDU — 空包（LLID=01, Length=0）**：

```
┌──────────┬─────┐
│LL Header │ CRC │  ← 无 Payload, 无 MIC
│  2 字节   │3 字节│
└──────────┴─────┘
```

空包的作用：① 确认收到对方上一包（通过 NESN） ② 维持连接心跳 ③ 从设备没数据时"签到"。

### 4.4 LL Control PDU 结构

```
┌──────────┬────────┬──────────────────┬─────┐
│LL Header │ Opcode │  Control Data    │ CRC │
│  2 字节   │  1 字节 │  (可变长度)       │3 字节│
│LLID=11   │  始终明文│                  │     │
└──────────┴────────┴──────────────────┴─────┘
```

**LL Control PDU Opcode 全集**：

| Opcode | PDU 名称 | 方向 | 说明 |
|--------|---------|------|------|
| 0x00 | LL_CONNECTION_UPDATE_REQ | M→S | 更新连接参数 |
| 0x01 | LL_CHANNEL_MAP_REQ | M→S | 更新信道图 |
| 0x02 | LL_TERMINATE_IND | 双向 | 断开连接 |
| 0x03 | LL_ENC_REQ | M→S | 加密请求 |
| 0x04 | LL_ENC_RSP | S→M | 加密响应 |
| 0x05 | LL_START_ENC_REQ | M→S | 开始加密（明文！） |
| 0x06 | LL_START_ENC_RSP | S→M | 开始加密确认（明文！） |
| 0x07 | LL_UNKNOWN_RSP | 双向 | 收到未知 Control PDU |
| 0x08 | LL_FEATURE_REQ | 双向 | 特性交换请求 |
| 0x09 | LL_FEATURE_RSP | 双向 | 特性交换响应 |
| 0x0A | LL_PAUSE_ENC_REQ | 双向 | 暂停加密 (5.1+) |
| 0x0B | LL_PAUSE_ENC_RSP | 双向 | 暂停加密确认 |
| 0x0C | LL_VERSION_IND | 双向 | 版本通知（无 Req/Rsp，单向） |
| 0x0D | LL_REJECT_IND | 双向 | 拒绝不支持的 Control PDU |
| 0x0E | LL_SLAVE_FEATURE_REQ | S→M | 从设备主动特性请求 (4.2+) |
| 0x14 | LL_PHY_REQ | 双向 | PHY 更新请求 (5.0) |
| 0x15 | LL_PHY_RSP | 双向 | PHY 更新响应 |
| 0x16 | LL_LENGTH_REQ | 双向 | 数据长度扩展请求 (4.2) |
| 0x17 | LL_LENGTH_RSP | 双向 | 数据长度扩展响应 |
| 0x19 | LL_PERIODIC_SYNC_IND | — | 周期广播同步 (5.0) |

### 4.5 关键 Control PDU Payload 详解

#### LL_CONNECTION_UPDATE_REQ (Opcode=0x00, Length=11)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x00 |
| WinSize | 1 字节 | |
| WinOffset | 2 字节 | = 1.25ms × WinOffset |
| Interval | 2 字节 | 新连接间隔 |
| Latency | 2 字节 | 新从设备延迟 |
| Timeout | 2 字节 | 新监督超时 |
| Instant | 2 字节 | 生效时刻（连接事件计数器值） |

**无 Response**：接受则在 Instant 时刻自动切换；拒绝则回 LL_REJECT_IND。

#### LL_CHANNEL_MAP_REQ (Opcode=0x01, Length=8)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x01 |
| ChM | 5 字节 | 37 位信道图（bit=1=可用） |
| Instant | 2 字节 | 生效时刻 |

#### LL_TERMINATE_IND (Opcode=0x02, Length=2)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x02 |
| ErrorCode | 1 字节 | 断开原因码 |

#### LL_VERSION_IND (Opcode=0x0C, Length=6)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x0C |
| VersNr | 1 字节 | 蓝牙控制器版本号（如 9=4.2, 10=5.0） |
| CompId | 2 字节 | 公司 ID |
| SubVersNr | 2 字节 | 固件子版本号 |

#### LL_FEATURE_REQ/RSP (Opcode=0x08/0x09, Length=9)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x08(Req) / 0x09(Rsp) |
| FeatureSet | 8 字节 | 64 位特性位掩码 |

**FeatureSet 关键位**：

| 位 | 特性 | 说明 |
|----|------|------|
| bit 0 | LE Encryption | 支持链路层加密 |
| bit 1 | Connection Parameters Request | 支持连接参数请求 |
| bit 3 | Slave-initiated Features Exchange | 从设备可主动发起特性交换 |
| bit 5 | LE Data Packet Length Extension | 支持 251 字节 Payload (4.2+) |
| bit 8 | LE 2M PHY | 支持 2Mbps PHY (5.0) |
| bit 9 | LE Coded PHY | 支持 Coded PHY (5.0 长距离) |
| bit 10 | LE Extended Advertising | 支持扩展广播 (5.0) |

#### LL_PHY_REQ/RSP (Opcode=0x14/0x15, Length=3)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x14(Req) / 0x15(Rsp) |
| TX_PHYS | 1 字节 | bit0=1M, bit1=2M, bit2=Coded(S8), bit3=Coded(S2) |
| RX_PHYS | 1 字节 | 同上 |

#### LL_LENGTH_REQ/RSP (Opcode=0x16/0x17, Length=9)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x16(Req) / 0x17(Rsp) |
| MaxRxOctets | 2 字节 | 最大接收 Payload 字节数 (27~251) |
| MaxRxTime | 2 字节 | 最大接收时间（μs） |
| MaxTxOctets | 2 字节 | 最大发送 Payload 字节数 |
| MaxTxTime | 2 字节 | 最大发送时间（μs） |

#### LL_REJECT_IND (Opcode=0x0D, Length=3)

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x0D |
| RejectOpcode | 1 字节 | 被拒绝的 Control PDU Opcode |
| ErrorCode | 1 字节 | 拒绝原因 |

---

## 五、HCI — 主机控制器接口（简述）

HCI 是 Host（主 CPU）和 Controller（蓝牙 IC）之间的**内部通信协议**，不过空中。

```
┌──── Host（主 CPU）────┐          ┌── Controller（蓝牙 IC）──┐
│ App → GATT → ATT      │  HCI     │ 链路层 → PHY            │
│          ↓            │ ──────→  │   ↓                     │
│        L2CAP          │ UART/SPI │  拆 HCI 头 → 组装       │
│   [+HCI ACL 头]       │          │  LL Data PDU → 发出     │
└───────────────────────┘          └─────────────────────────┘
```

**HCI ACL 头的作用**：Host 发给 Controller 时标注"这是发给哪条连接的（Connection Handle）"。Controller 收到后撕掉 HCI 头，只把 L2CAP 包装到 LL Data PDU 里。

> **空中抓包看不到 HCI 头**——它在芯片之间的 UART/SPI 上跑，不进 2.4GHz。

---

## 六、L2CAP — 逻辑链路控制与适配协议

L2CAP 解决两个问题：
1. **协议复用**：同一个 LL Data PDU 通道里，区分 ATT 还是 SMP？靠 CID
2. **分片重组（SAR）**：上层数据大于链路层 Payload 时切分，接收方重组

### 6.1 L2CAP 包格式

```
┌──────────────────┬──────────────────┬─────────────────────────┐
│    Length        │       CID        │    Information Payload  │
│    2 字节         │     2 字节       │    (Length 字节)        │
└──────────────────┴──────────────────┴─────────────────────────┘
```

| 字段 | 大小 | 说明 |
|------|------|------|
| Length | 2 字节 | Payload 字节数（不含自身和 CID），纸面上限 65535 |
| CID | 2 字节 | 信道标识符——决定 Payload 交给哪个上层协议 |
| Payload | Length 字节 | 上层协议 PDU（ATT / SMP / L2CAP Signaling 等） |

> Length 是纯长度值，不含标志位。实际能传多少由 ATT MTU（~517）和 LL Payload（27/251）联合决定。

### 6.2 CID 全集

| CID | 协议 | 说明 |
|-----|------|------|
| **0x0004** | **ATT** | 属性协议——GATT 读写通知走这条路 |
| 0x0005 | L2CAP Signaling | L2CAP 层自身控制命令（参数更新等） |
| **0x0006** | **SMP** | 安全管理器——配对/加密/密钥分发 |
| 0x0020~0x003F | LE Credit Based | 面向连接的自定义信道 (4.2+) |

> CID 对 App 层透明，Android BLE 协议栈自动处理。

### 6.3 L2CAP Signaling（CID=0x0005）— 控制命令

用于 L2CAP 层自身的参数协商。BLE 中最常用的是**连接参数更新**：

| Code | 命令 | 说明 |
|------|------|------|
| 0x01 | Command Reject | 拒绝不支持的 L2CAP 命令 |
| 0x12 | Connection Parameter Update Request | **从设备主动请求修改连接参数** |
| 0x13 | Connection Parameter Update Response | Master 对更新请求的响应 |

**LL Control vs L2CAP Signaling 改连接参数的区别**：

| | LL_CONNECTION_UPDATE_REQ (LL层) | L2CAP Connection Parameter Update (L2CAP层) |
|---|---|---|
| **谁发起** | 仅 Master | Master 或 Slave |
| **响应** | 无 Response（接受=即时生效，拒绝=LL_REJECT_IND） | 有 Request/Response 配对 |
| **如何承载** | LL Control PDU (LLID=11) | LL Data PDU (LLID=10) → L2CAP CID=0x0005 |

两条路都能改连接参数，Slave 想改参数时必须走 L2CAP 路。

---

## 七、SMP — 安全管理器（左分叉，CID=0x0006）

SMP 负责配对、密钥交换、身份认证、密钥分发。所有 SMP PDU 承载在 LL Data PDU → L2CAP CID=0x0006 中。

### 7.1 SMP PDU 通用格式与 Code 全集

```
┌──────┬──────────────────────────┐
│ Code │        Data              │
│ 1 字节│    (可变，取决于 Code)    │
└──────┴──────────────────────────┘
```

| Code | PDU 名称 | 方向 | 说明 |
|------|---------|------|------|
| 0x01 | Pairing Request | 双向 | 配对特征交换（IO Cap/AuthReq） |
| 0x02 | Pairing Response | 双向 | 配对特征响应 |
| 0x03 | Pairing Confirm | 双向 | Legacy 配对确认值 |
| 0x04 | Pairing Random | 双向 | Legacy 配对随机数 |
| 0x05 | Pairing Failed | 双向 | 配对失败通知 |
| 0x06 | Encryption Information | 双向 | 分发 LTK |
| 0x07 | Master Identification | 双向 | 分发 EDIV + Rand |
| 0x08 | Identity Information | 双向 | 分发 IRK |
| 0x09 | Identity Address Information | 双向 | 分发身份地址 |
| 0x0A | Signing Information | 双向 | 分发 CSRK |
| 0x0B | Security Request | S→M | 从设备请求 Master 启动加密 |
| 0x0C | **Pairing Public Key** | 双向 | **SC: ECDH P-256 公钥（64 字节）** |
| 0x0D | **Pairing DHKey Check** | 双向 | **SC: DHKey 一致性校验** |
| 0x0E | Pairing Keypress Notification | 双向 | Passkey Entry 按键确认 |

### 7.2 配对完整四阶段流程

```
                     Phase 1              Phase 2          Phase 3        Phase 4
                配对特征交换             密钥交换            认证           密钥分发
                   ────────             ────────          ────────       ────────
                   SMP Req/Rsp     Public Key (ECDH)   NumComp/JustW   DHKey Check
                   交换 IO CAP     或 Confirm+Random     Passkey        分发 LTK/IRK
                                     (Legacy)                        /CSRK/地址
```

**四种配对方式路径**：

```
                     Phase1: 交换 IO Capabilities
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       都支持 SC?         Legacy 设备      任一方 NoInputNoOutput
              │                │                │
        ┌─────┴─────┐    ┌────┴────┐          ▼
        ▼           ▼    ▼         ▼      Just Works
  双方都有显示?  一方无显示  │   一方显示一方键盘   (不验证身份)
        │           │    │         │
        ▼           ▼    ▼         ▼
   Numeric      Just    Just    Passkey
   Comparison   Works   Works    Entry
   (用户比对)  (无验证) (TK=0)  (输PIN)
```

### 7.3 Phase 1：配对特征交换

```
设备A (Central)                          设备B (Peripheral)
  │                                         │
  │ SMP Pairing Request ───────────────────→│ Code=0x01
  │←────── SMP Pairing Response ───────────┤ Code=0x02
```

**SMP Pairing Request/Response PDU**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x01(Req) / 0x02(Rsp) |
| **IO Capability** | 1 字节 | 0x00=DisplayOnly, 0x01=DisplayYesNo, 0x02=KeyboardOnly, 0x03=NoInputNoOutput, 0x04=KeyboardDisplay |
| OOB Data Flag | 1 字节 | 0x00=不使用 OOB |
| **AuthReq** | 1 字节 | bit0=Bonding, bit2=MITM, bit3=SC, bit4=Keypress |
| Maximum Key Size | 1 字节 | 密钥长度 (7~16) |
| Initiator Key Dist | 1 字节 | 发起方要分发的密钥类型位图 |
| Responder Key Dist | 1 字节 | 响应方要分发的密钥类型位图 |

**IO Capability 决定配对方式的规则**：

```
任一方 IO=NoInputNoOutput → Just Works
双方 IO 都有显示能力 + 都支持 SC → Numeric Comparison
一方 DisplayOnly + 一方 KeyboardOnly → Passkey Entry
其他组合 → Just Works
```

### 7.4 Phase 2：密钥交换

#### LE Legacy Pairing（BLE 4.0/4.1）

用 **TK（Temporary Key）→ STK（Short Term Key）**。

```
Just Works: TK = 0  (不安全！)
Passkey:    TK = 6 位 PIN → 20 bit 安全强度
OOB:        TK = OOB 渠道交换的 128 bit

Mconfirm = AES-CMAC(TK, Mrand || 配对参数)
Sconfirm = AES-CMAC(TK, Srand || 配对参数)

交互序列:
  M → S: SMP Pairing Confirm (0x03) [Confirm=16B]
  S → M: SMP Pairing Confirm (0x03) [Confirm=16B]
  M → S: SMP Pairing Random  (0x04) [Random=16B]
  S → M: SMP Pairing Random  (0x04) [Random=16B]

双方验证: 自己算 Confirm == 收到 Confirm → 通过
STK = AES-CMAC(TK, Mrand || Srand)
```

**Legacy 关键弱点**：Just Works 时 TK=0 → 旁听者抓到 Mconfirm+Mrand 即可算出 STK → 完全透明解密。

#### LE Secure Connections（BLE 4.2+）

用 **ECDH P-256**，密钥强度 128-bit，不依赖 PIN。

```
双方各生成 ECDH P-256 密钥对:
  sk_a (256-bit 私钥) → Pka = sk_a × G (公钥, 64 字节)
  sk_b (256-bit 私钥) → Pkb = sk_b × G (公钥, 64 字节)

交互:
  M → S: SMP Public Key (0x0C) [Pka: X(32B) + Y(32B) = 64B]
  S → M: SMP Public Key (0x0C) [Pkb: X(32B) + Y(32B) = 64B]

双方各自计算: DHKey = ECDH(自己的私钥, 对方的公钥)
             = sk_a × Pkb = sk_b × Pka = sk_a × sk_b × G  ← 相同！
```

**公钥明文传输没关系**——ECDH 安全性不依赖公钥保密，而依赖椭圆曲线离散对数难题（从公钥反推私钥在数学上不可行）。

### 7.5 Phase 3：认证（四种路径）

#### 路径 A：Numeric Comparison（最安全）

```
M → S: Na (128-bit 随机数)
S → M: Nb (128-bit 随机数)

双方各自计算:
  C = f4(Pka, Pkb, Na, Nb, 0)
  → 取高 32 位 → 转 6 位十进制数字

双方屏幕各显示 6 位数字 → 用户肉眼比对 → 一致按确认

M → S: SMP Confirm (0x03) // 用户确认后发

为什么防 MITM:
  攻击者替换公钥 → 双方算出的数字不同 → 用户发现 → 拒绝
```

#### 路径 B：Just Works（SC 版本）

```
跳过 Phase 3 验证（不显示 6 位数字）。
密钥仍是 128-bit ECDH → 防被动窃听 ❌
不防主动 MITM → 攻击者可在 Phase 2 拦截并替换公钥
  Phone ←→ M(SessionKey₁) ←→ 耳机(SessionKey₂)
  M 完全透明读、改、转发一切

但比 Legacy Just Works 安全得多：
  Legacy: 旁听者也能解密（TK=0 → STK 极易算）
  SC:     至少需要攻击者主动介入配对过程
```

#### 路径 C：Passkey Entry（SC 版本）

```
一方显示 6 位 PIN → 用户输入到另一方
PIN 作为 Na/Nb 种子参与 f4
→ 只有输入相同 PIN 的双方才能生成相同确认码
→ PIN 起到身份验证作用
```

#### 路径 D：Legacy Just Works / Passkey

```
Legacy Just Works: TK=0, 旁听即可破
Legacy Passkey: TK=6位PIN, 20-bit安全, 可暴力破解
```

### 7.6 Phase 4：DHKey 校验 → 密钥派生 → 密钥分发

#### DHKey Check（仅 SC）

```
双方各自计算:
  MacKey = f5(DHKey, Na, Nb, "macKey", ...) 的第二部分
  Check  = AES-CMAC(MacKey, DHKey || Na || Nb || IO Caps || AddrA || AddrB)

M → S: SMP DHKey Check (0x0D) [Check=16B]
S → M: SMP DHKey Check (0x0D) [Check=16B]
→ 双方验证一致 = 密钥交换未被篡改
```

#### 密钥派生链

```
                ECDH(sk_a, Pkb) = DHKey
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
     f5 → LTK       f5 → MacKey    f6 → 校验值
      (128-bit)       (128-bit)      (128-bit)
     存入绑定表       用于SC验证      用于完整性校验


后续每条连接:
  LTK ──AES-CMAC(LTK, SKDm||SKDs)──→ SessionKey (128-bit)
                                        ↑ 每次连接全新随机数
```

#### 密钥分发

加密隧道建立后分发长期密钥（各 PDU 由新加密链路保护）：

| Code | PDU | 大小 | 内容 |
|------|-----|------|------|
| 0x06 | Encryption Info | 16B | **LTK**（长期密钥） |
| 0x07 | Master ID | 10B | EDIV(2B) + Rand(8B) ← 下次找 LTK 的索引 |
| 0x08 | Identity Info | 16B | **IRK**（身份解析密钥，解析 RPA 私有地址） |
| 0x09 | Identity Address | 7B | AddrType(1B) + Addr(6B) ← 对方的身份地址 |
| 0x0A | Signing Info | 16B | **CSRK**（连接签名密钥，用于数据签名） |

> **EDIV+Rand 的作用**：类似"钥匙串编号"——下次重连时，Master 在 LL_ENC_REQ 中带上这组值，Slave 用它在绑定表中查找对应的 LTK。

---

## 八、ATT / GATT — 属性协议（右分叉，CID=0x0004）

ATT 定义数据交互的"动词"（怎么读写），GATT 定义数据的"名词"（怎么组织）。承载于 LL Data PDU → L2CAP CID=0x0004。

### 8.1 ATT PDU 通用格式

```
┌────────┬──────────────────────────────┐
│ Opcode │       Parameters             │
│ 1 字节  │   (0 ~ MTU-1 字节)           │
└────────┴──────────────────────────────┘

Opcode 结构:
  Bit [5:0] = Method (具体操作)
  Bit [6]   = Command Flag (0=需响应, 1=无需响应)
  Bit [7]   = Authentication Signature Flag (0=无签名, 1=有CSRK签名)
```

### 8.2 ATT Opcode 全集

#### 读操作（Requests）

| Opcode | PDU 名称 | 参数 | 说明 |
|--------|---------|------|------|
| 0x0A | Read Request | Handle(2B) | 读取指定 Handle 的值 |
| 0x0B | Read Response | Value(变长) | 返回读取的数据 |
| 0x0C | Read Blob Request | Handle(2B) + Offset(2B) | 长数据分段续读 |
| 0x0D | Read Blob Response | Part Value(变长) | 返回一段数据 |
| 0x08 | Read By Type Request | StartHandle(2B) + EndHandle(2B) + UUID(2/16B) | 范围内搜索同类型属性 → 发现 Characteristic |
| 0x09 | Read By Type Response | 多个 [Handle(2B)+Value] | 返回匹配的属性列表 |
| 0x10 | Read By Group Type Request | StartHandle(2B) + EndHandle(2B) + UUID(2/16B) | 范围内搜索组类型属性 → 发现 Service |
| 0x11 | Read By Group Type Response | 多个 [StartHandle+EndHandle+Value] | 返回 Service 列表 |
| 0x04 | Find Information Request | StartHandle(2B) + EndHandle(2B) | 范围内发现所有属性 → 发现 Descriptor |
| 0x05 | Find Information Response | 多个 [Handle(2B)+UUID(2/16B)] | 返回属性信息列表 |
| 0x06 | Find By Type Value Request | StartHandle+EndHandle+Type(2B)+Value | 按类型+值搜索 |
| 0x07 | Find By Type Value Response | 多个 [Handle范围] | 返回匹配的属性 Handle |

#### 写操作（Requests & Commands）

| Opcode | PDU 名称 | 参数 | 确认？ | 说明 |
|--------|---------|------|--------|------|
| 0x12 | Write Request | Handle(2B) + Value(变长) | ✅ 有 | 带确认写 |
| 0x13 | Write Response | 无 | — | 写确认回复 |
| **0x52** | **Write Command** | Handle(2B) + Value(变长) | ❌ 无 | 无确认快速写（bit6=1 → 0x12\|0x40=0x52） |
| 0xD2 | Signed Write Command | Handle(2B) + Value + CSRK签名(12B) | ❌ 无 | 带 CSRK 签名写 |
| 0x16 | Prepare Write Request | Handle(2B) + Offset(2B) + PartValue | ✅ 有 | 长写准备（不立即生效） |
| 0x17 | Prepare Write Response | Handle(2B) + Offset(2B) + PartValue | — | 回显准备的内容 |
| 0x18 | Execute Write Request | Flags(1B: 0x00=取消, 0x01=原子提交) | ✅ 有 | 提交或取消所有 Prepare |
| 0x19 | Execute Write Response | 无 | — | 提交确认 |

#### 通知与指示（Server → Client 推送）

| Opcode | PDU 名称 | 参数 | 确认？ | 说明 |
|--------|---------|------|--------|------|
| **0x1B** | **Handle Value Notification** | Handle(2B) + Value(变长) | ❌ 无 | 通知推送（快，不可靠） |
| 0x1D | Handle Value Indication | Handle(2B) + Value(变长) | ✅ 有 | 指示推送（慢，可靠） |
| 0x1E | Handle Value Confirmation | 无 | — | 指示确认回复 |

**Notification vs Indication 选择**：

| | Notification | Indication |
|---|---|---|
| **可靠性** | 不可靠（丢了就丢了） | 可靠（等 CFM 才发下一个） |
| **速度** | 快 | 慢（必须等确认） |
| **适用场景** | 流速/累计流量（丢了下一包马上到） | 报警事件（绝对不能丢） |
| **CCCD 值** | 0x0001 | 0x0002 |

#### 错误与 MTU

| Opcode | PDU 名称 | 参数 | 说明 |
|--------|---------|------|------|
| 0x01 | Error Response | ReqOpcode(1B) + Handle(2B) + ErrorCode(1B) | 操作失败通知 |
| 0x02 | Exchange MTU Request | ClientRxMTU(2B) | MTU 协商请求 |
| 0x03 | Exchange MTU Response | ServerRxMTU(2B) | MTU 协商响应 → ATT MTU = min(两者) |

**常用 ATT Error Code**：

| 值 | 名称 | 含义 |
|----|------|------|
| 0x01 | Invalid Handle | Handle 不存在 |
| 0x02 | Read Not Permitted | 无读权限 |
| 0x03 | Write Not Permitted | 无写权限 |
| 0x05 | Insufficient Authentication | 未配对认证 |
| 0x08 | Insufficient Encryption | 未加密或加密强度不够 |

### 8.3 GATT 数据组织

```
Profile (概念层，不存在于 Attribute DB)
└── Service (功能模块)
    ├── Declaration [Handle=N][Type=0x2800/0x2801][Value=Service UUID]
    │
    └── Characteristic (具体数据项)
        ├── Declaration [Handle=M][Type=0x2803][Value=Properties(1B)+ValueHandle(2B)+UUID]
        ├── Value [Handle=ValueHandle][Type=UUID][Value=实际数据]
        └── Descriptor (CCCD/CUD等，可选)
            └── [Handle][Type][Value]
```

**UUID 分配规律**：

| UUID 前缀 | 类别 | 示例 |
|-----------|------|------|
| 0x18XX | Service | 0x180F=Battery Service, 0x180A=Device Information, 0x1800=GAP, 0x1801=GATT |
| 0x2AXX | Characteristic | 0x2A19=Battery Level, 0x2A6E=Temperature |
| 0x29XX | Descriptor | **0x2902=CCCD**（最重要） |

**CCCD（Client Characteristic Configuration Descriptor, UUID=0x2902）**：控制 Notification/Indication 的开关。

| CCCD 值 | 含义 |
|---------|------|
| 0x0000 | 关闭（默认值，连接断开时自动重置为此值） |
| 0x0001 | 启用 Notification |
| 0x0002 | 启用 Indication |

> ⚠️ **重连后必须重新写 CCCD**——连接断开时设备端 CCCD 自动归零。

### 8.4 服务发现流程（discoverServices）

三个 Round 逐一"探"出 GATT 表：

| Round | ATT PDU | 查询类型 | 发现内容 |
|-------|---------|---------|---------|
| 1 | Read By Group Type (0x2800) | Primary Service | 所有 Service UUID + Handle 范围 |
| 2 | Read By Type (0x2803) | Characteristic | 每个 Characteristic 的 Properties + ValueHandle + UUID |
| 3 | Find Information | 所有 Handle | Handle 间隙 → Descriptor (CCCD/CUD 等) |

### 8.5 MTU 协商

```
ATT 默认 MTU = 23 字节（ATT Payload = 23, 实际数据 = 20~22）
协商流程:
  Client → Server: Exchange MTU Request (0x02) [ClientRxMTU=512]
  Server → Client: Exchange MTU Response (0x03) [ServerRxMTU=251]
  → ATT MTU = min(512, 251) = 251

Android: gatt.requestMtu(512) → onMtuChanged(mtu, status)
```

**必须 `requestMtu` 再 `discoverServices`**——MTU 协商在连接早期完成，后续所有操作都受益于大 MTU。

---

## 九、加密完整流程（跨层总览）

加密是 SMP（生成 LTK）和链路层（LL_ENC_REQ/RSP 启动加密）的协作结果。

### 9.1 分层总览

```
┌───────────────────────────────────────────────┐
│        加密的跨层协作                            │
│                                               │
│  SMP (L2CAP CID=0x0006)                       │
│    ├── Phase 1~4: 配对 → 生成 LTK (128-bit)    │
│    └── LTK 存入绑定表                           │
│            ↓                                   │
│  链路层 LL Control PDU                         │
│    ├── LL_ENC_REQ/RSP:  交换 SKDm/SKDs         │
│    ├── SessionKey = AES-CMAC(LTK, SKDm||SKDs)  │
│    └── LL_START_ENC_REQ/RSP: 启动 AES-CCM      │
│            ↓                                   │
│  LL Data PDU: Payload + MIC 全程 AES-CCM 加密  │
└───────────────────────────────────────────────┘
```

### 9.2 首次加密：三次握手（LL_ENC_REQ → LL_ENC_RSP → LL_START_ENC）

```
设备A (Master)                            设备B (Slave)
  │                                         │
  │ LL_ENC_REQ ────────────────────────────→│ Opcode=0x03, Length=23
  │←─────────── LL_ENC_RSP ──────────────── │ Opcode=0x04, Length=13
  │                                         │
  │ SessionKey = AES-CMAC(LTK, SKDm||SKDs)  │ 双方各自计算
  │                                         │
  │ LL_START_ENC_REQ ──────────────────────→│ Opcode=0x05, Length=1  ← 明文！
  │←─────────── LL_START_ENC_RSP ────────── │ Opcode=0x06, Length=1  ← 明文！
  │                                         │
══╪══════════ 此后全部 AES-CCM 加密 ════════╪══
```

**LL_ENC_REQ / LL_ENC_RSP Payload**：

| 字段 | 大小 | 出现 | 说明 |
|------|------|------|------|
| Opcode | 1 字节 | 两者 | 0x03(REQ) / 0x04(RSP) |
| **Rand** | 8 字节 | REQ | 64-bit 随机数，配合 EDIV 查找 LTK |
| **EDIV** | 2 字节 | REQ | 加密分集——LTK 索引号 |
| **SKDm** | 8 字节 | REQ | Master Session Key Diversifier（每次连接全新随机） |
| **IVm** | 4 字节 | REQ | Master Initial Vector |
| **SKDs** | 8 字节 | RSP | Slave Session Key Diversifier（每次连接全新随机） |
| **IVs** | 4 字节 | RSP | Slave Initial Vector |

**LL_START_ENC_REQ/RSP**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x05(REQ) / 0x06(RSP) |

> LL_START_ENC_REQ/RSP **本身是明文**——对方必须先读到"即将切换到加密模式"这条指令才能切换解密引擎。

### 9.3 Session Key 派生

```
SessionKey = AES-CMAC(
    Key  = LTK (128 bit, 来自 SMP 配对/绑定),
    Data = SKDm (64 bit) || SKDs (64 bit)
)

SKDm/SKDs 每次连接都是全新随机数
→ SessionKey 每次都不同
→ 防重放攻击（同一个 LTK 不能重放旧的加密流量）
```

### 9.4 加密范围

```
┌──────────┬──────────────┬──────────────────┬───────┬─────┐
│Preamble  │Access Address│   PDU            │  MIC  │ CRC │
│  1 字节   │   4 字节      │ ┌──────┬───────┐│ 4 字节 │3 字节│
│  明文    │    明文       │ │Header│Payload││       │     │
│          │              │ │ 明文 │ 密文  ││ 密文  │ 明文 │
└──────────┴──────────────┴─┴──────┴───────┴─┴───────┴─────┘
```

| 字段 | 加密？ | 原因 |
|------|--------|------|
| Header (LLID/SN/NESN/MD/Length) | ❌ **明文** | 链路层必须先解析才能处理（SN/NESN 确认重传、Length 知道后面多长） |
| Payload (L2CAP→ATT/SMP 数据) | ✅ **密文** | AES-CCM CTR 模式加密 |
| MIC | ✅ **密文** | AES-CBC-MAC 生成的 4 字节防篡改标签，随 Payload 一起加密 |
| CRC | ❌ **明文** | 物理层误码检测，和加密无关 |

### 9.5 绑定设备重连 — 跳过 SMP 直接加密

```
设备A                                    设备B
  │                                         │
══╪═══════ 连接建立 ═══════════════════════╪══
  │                                         │
  │ LL_ENC_REQ (EDIV+Rand → 查LTK) ───────→│  ← 跳过全部 SMP 配对！
  │←─────────── LL_ENC_RSP ────────────────│
  │ LL_START_ENC_REQ ──────────────────────→│
  │←─────────── LL_START_ENC_RSP ────────── │
  │                                         │
══╪══════════ 加密通信 ════════════════════╪══
```

> LL_ENC_REQ 中携带的 EDIV+Rand 相当于"钥匙串编号"——Slave 用它们在自己的绑定表中查找对应的 LTK。找到 → 直接进入加密，不用重新配对。

### 9.6 异常情况

| 场景 | 触发条件 | 后果 |
|------|---------|------|
| **加密拒绝** | 设备不支持加密或密钥缺失 | LL_REJECT_IND (RejectOpcode=0x03)，连接继续(明文)或断开 |
| **MIC 校验失败** | 双方 LTK 不一致（常见：重装APP或清数据后重连） | 包丢弃 → 连续失败 → LL_TERMINATE_IND (ErrorCode=0x05) |
| **加密暂停** | BLE 5.1+ 需要更新密钥 | LL_PAUSE_ENC_REQ/RSP → 明文状态下分发新 LTK → 重新 ENC_REQ |

**MIC 失败排查**：最常见原因是双方 LTK 不一致——例如手机端 removeBond() 删了绑定但设备端还保留旧 LTK。解决：双方都清绑定 → 重新配对。

---

## 十、综合速查表

### 10.1 LL Control PDU Opcode

| Opcode | PDU | 方向 | 用途 |
|--------|-----|------|------|
| 0x00 | CONNECTION_UPDATE_REQ | M→S | 改连接参数 |
| 0x01 | CHANNEL_MAP_REQ | M→S | 改信道图 |
| 0x02 | TERMINATE_IND | 双向 | 断开 |
| 0x03 | ENC_REQ | M→S | 加密请求 |
| 0x04 | ENC_RSP | S→M | 加密响应 |
| 0x05 | START_ENC_REQ | M→S | 开始加密(明文) |
| 0x06 | START_ENC_RSP | S→M | 开始加密确认 |
| 0x07 | UNKNOWN_RSP | 双向 | 未知PDU |
| 0x08/09 | FEATURE_REQ/RSP | 双向 | 特性协商 |
| 0x0A/0B | PAUSE_ENC_REQ/RSP | 双向 | 暂停加密(5.1) |
| 0x0C | VERSION_IND | 双向 | 蓝牙版本 |
| 0x0D | REJECT_IND | 双向 | 拒绝 |
| 0x0E | SLAVE_FEATURE_REQ | S→M | 从设备特性请求 |
| 0x14/15 | PHY_REQ/RSP | 双向 | PHY切换(5.0) |
| 0x16/17 | LENGTH_REQ/RSP | 双向 | 长度扩展(4.2) |
| 0x19 | PERIODIC_SYNC_IND | — | 周期同步(5.0) |

### 10.2 SMP Code

| Code | PDU | 用途 |
|------|-----|------|
| 0x01/02 | Pairing Req/Rsp | IO Capabilities 交换 |
| 0x03/04 | Pairing Confirm/Random | Legacy 配对验证 |
| 0x05 | Pairing Failed | 配对失败通知 |
| 0x06 | Encryption Info | 分发 LTK |
| 0x07 | Master ID | 分发 EDIV+Rand |
| 0x08/09 | Identity Info/Addr | 分发 IRK+地址 |
| 0x0A | Signing Info | 分发 CSRK |
| 0x0B | Security Request | S请求M启动加密 |
| 0x0C | Public Key | SC: ECDH 公钥(64B) |
| 0x0D | DHKey Check | SC: DHKey 校验(16B) |
| 0x0E | Keypress Notification | Passkey 按键确认 |

### 10.3 ATT Opcode

| Opcode | PDU | 类别 |
|--------|-----|------|
| 0x01 | Error Response | 错误 |
| 0x02/03 | Exchange MTU Req/Rsp | MTU |
| 0x04/05 | Find Information Req/Rsp | 读(发现) |
| 0x06/07 | Find By Type Value Req/Rsp | 读(发现) |
| 0x08/09 | Read By Type Req/Rsp | 读(发现) |
| 0x0A/0B | Read Req/Rsp | 读 |
| 0x0C/0D | Read Blob Req/Rsp | 读(长) |
| 0x10/11 | Read By Group Type Req/Rsp | 读(发现) |
| 0x12/13 | Write Req/Rsp | 写(确认) |
| 0x16/17 | Prepare Write Req/Rsp | 写(事务) |
| 0x18/19 | Execute Write Req/Rsp | 写(提交) |
| **0x1B** | **Handle Value Notification** | **通知(无确认)** |
| 0x1D/1E | Handle Value Ind/Conf | 指示(有确认) |
| **0x52** | **Write Command** | **写(无确认)** |
| 0xD2 | Signed Write Command | 签名写 |

### 10.4 L2CAP CID

| CID | 协议 | 走向 |
|-----|------|------|
| **0x0004** | **ATT** | 数据——GATT 读写通知 |
| 0x0005 | L2CAP Signaling | 控制——参数更新请求/响应 |
| **0x0006** | **SMP** | 安全——配对/加密/密钥分发 |
| 0x0020~0x003F | LE Credit Based | 自定义信道 (4.2+) |

### 10.5 AD Type（AdvData LTV 常用）

| Type | 名称 | Data格式 |
|------|------|---------|
| **0x01** | Flags | 1B 位掩码（必须排第一个） |
| 0x03 | Complete 16-bit Service UUIDs | 每UUID 2B(小端) |
| 0x07 | Complete 128-bit Service UUIDs | 每UUID 16B |
| 0x08 | Shortened Local Name | UTF-8 |
| **0x09** | Complete Local Name | UTF-8 |
| **0x0A** | TX Power Level | 1B 有符号dBm |
| 0x16 | Service Data (16-bit) | UUID(2B) + Data |
| **0xFF** | Manufacturer Specific | Company ID(2B小端) + 自定义 |

---

## 附录：典型完整报文序列

以 OPPO Enco Air2 耳机为例，首次连接 + SC Numeric Comparison + AT T写 CCCD 的完整报文序列：

```
                                                                    层   信道
══════════════════════════════════════════════════════════════════════════════
① ADV_IND ──────────────────────────────────────→                     LL   37/38/39
   PDU Type=0000, AdvA=MAC_B, AdvData=[Flags][Name][UUIDs]

② (可选) SCAN_REQ ←────────────────────────────                      LL   37/38/39
   SCAN_RSP  ──────────────────────────────────→

③ CONNECT_IND ←────────────────────────────────                      LL   37/38/39
   InitA=MAC_A, AdvA=MAC_B, AA=0x????????, Interval=30ms, ...

══╪ Connection ════════════════════════════════════════════════════════════
④ LL_VERSION_IND ──────────────────────────────→                     LL   0~36
⑤ LL_FEATURE_REQ/RSP ←────────────────────────→                     LL   0~36

⑥ SMP Pairing Req ─────────────────────────────→                    SMP  (L2CAP CID=0x0006)
   Code=0x01, IO=KeyboardDisplay, AuthReq=SC+Bonding
⑦ SMP Pairing Rsp ←────────────────────────────                     SMP

⑧ SMP Public Key ──────────────────────────────→                    SMP
   Code=0x0C, Pka=P-256(64B)
⑨ SMP Public Key ←─────────────────────────────                     SMP
   Code=0x0C, Pkb=P-256(64B)

⑩ SMP: Na ─────────────────────────────────────→                    SMP
⑪ SMP: Nb ←────────────────────────────────────                     SMP
   双方屏幕显示 6 位数字，用户肉眼比对确认

⑫ SMP: Confirm ────────────────────────────────→                    SMP
   (用户确认后发送)

⑬ SMP DHKey Check ─────────────────────────────→                    SMP
   Code=0x0D, Check=16B
⑭ SMP DHKey Check ←────────────────────────────                     SMP

⑮ SMP: Encryption Info ────────────────────────→                    SMP
   LTK (16B)
⑯ SMP: Encryption Info ←───────────────────────                     SMP
   LTK + EDIV+Rand + IRK + CSRK + Addr

⑰ LL_ENC_REQ ──────────────────────────────────→                    LL   0~36
   Opcode=0x03, Rand+EDIV+SKDm+IVm
⑱ LL_ENC_RSP ←─────────────────────────────────                     LL
   Opcode=0x04, SKDs+IVs

⑲ LL_START_ENC_REQ ────────────────────────────→                    LL
   Opcode=0x05 (明文!)
⑳ LL_START_ENC_RSP ←───────────────────────────                     LL
   Opcode=0x06 (明文!)

══╪═════ AES-CCM 加密通信 ═══════════════════════════════════════════════════
㉑ ATT Exchange MTU Req/Rsp ←──────────────────→                    ATT  (L2CAP CID=0x0004)
㉒ ATT Read By Group Type (Service Discovery)  →                    ATT
㉓ ATT Read By Type (Characteristic Discovery) →                    ATT
㉔ ATT Find Information (Descriptor Discovery) →                    ATT
㉕ ATT Write Request → CCCD=0x0001 (开通知)    →                    ATT
㉖ ATT Notification ← 数据推送 ←───────────────                     ATT
...
㉗ LL_TERMINATE_IND ───────────────────────────→                    LL   0~36
   Opcode=0x02
══════════════════════════════════════════════════════════════════════════════
```

---

*整理时间：2026-07-19*
*关联：[[3.7-链路层PDU格式]] [[3.3-广播PDU类型]] [[3.4-广播参数]] [[3.5-连接建立全过程]] [[4.1-HCI主机控制器接口]] [[4.2-L2CAP逻辑链路控制与适配协议]] [[5.4-LE-Secure-Connections详解]] [[5.6-链路层加密]] [[6.2-ATT-PDU类型全解]] [[6.3-GATT数据组织]] [[附录-报文手册深度问答]]*
