# 附录：BLE 协议交互报文完整手册

> 涵盖设备 A（Central/Phone）与设备 B（Peripheral/流量计）从广播发现到链路加密的全过程，包含所有交互路径和完整报文格式。
>
> 本手册统一使用"设备A = Central（手机）"和"设备B = Peripheral（设备）"。

---

## 一、总体状态流转

```
设备B                             设备A
  │                                 │
  │ ←──────── 广告阶段 ────────────→│  (37/38/39 信道)
  │                                 │
  │ ←──────── 连接建立 ────────────→│  (CONNECT_IND)
  │                                 │
══╪══════ Connection State ═══════╪══ (0~36 数据信道，跳频)
  │                                 │
  │ ←──── LL Control: 参数协商 ────→│  (连接参数/PHY/信道/长度)
  │                                 │
  │ ←──── SMP: 配对加密 ───────────→│  (L2CAP CID=0x0006)
  │                                 │
  │ ←──── LL Control: 启动加密 ────→│  (LL_ENC_REQ/RSP)
  │                                 │
══╪══════ 加密通信 ═══════════════╪══ (AES-CCM)
  │                                 │
  │ ←──── LL Control: 终止 ────────→│  (LL_TERMINATE_IND)
```

---

## 二、广告阶段（Advertising）

### 空中帧通用格式

```
所有 BLE 空中包的完整结构：

┌────────┬──────────────┬──────────────────────────────────┬───────┬─────┐
│Preamble│Access Address│           PDU                    │  MIC  │ CRC │
│ 1 字节  │   4 字节      │ ┌──────────┬──────────────────┐ │ 4 字节 │3 字节│
│ 0xAA   │              │ │ LL Header│    Payload        │ │       │     │
│        │              │ │  2 字节   │                  │ │       │     │
└────────┴──────────────┴─┴──────────┴──────────────────┴─┴───────┴─────┘

广告包: Access Address = 0x8E89BED6 (固定值)
数据包: Access Address = 随机值 (CONNECT_IND 下发)
MIC: 仅加密数据包有，广告包无 MIC
```

### 广告 PDU 类型速查

| PDU 类型 | PDU Type 值 | 可扫描？ | 可连接？ | 用途 |
|----------|-----------|---------|---------|------|
| ADV_IND | 0000 | ✅ | ✅ | 通用广播 |
| ADV_DIRECT_IND | 0001 | ❌ | ✅ (仅指定设备) | 定向广播 |
| ADV_NONCONN_IND | 0010 | ❌ | ❌ | 纯信标 |
| ADV_SCAN_IND | 0110 | ✅ | ❌ | 可扫描不可连 |
| SCAN_REQ | 0011 | — | — | 扫描请求 |
| SCAN_RSP | 0100 | — | — | 扫描响应 |
| CONNECT_IND | 0101 | — | — | 连接请求 |

> **注意**：广告信道 PDU Header 中 PDU Type 是 **4 bit**，数据信道 PDU Header 中用 **LLID（2 bit）** 区分 Data/Control。两者都在 16-bit PDU Header 内，但字段结构完全不同。

---

### PDU Header 通用格式

**广告信道 PDU Header (16 bit) — 广告包/扫描包/连接包**

```
 bit: [15:8]    [7]   [6]    [5]    [4]   [3:0]
     ┌────────┬──────┬──────┬──────┬─────┬──────────┐
     │ Length │RxAdd │TxAdd │ChSel │ RFU │ PDU Type │
     │ 8 bit  │ 1b   │ 1b   │ 1b   │ 1b  │  4 bit   │
     └────────┴──────┴──────┴──────┴─────┴──────────┘
```

| 字段 | 位宽 | 说明 |
|------|------|------|
| PDU Type | 4 bit [3:0] | 0000=ADV_IND, 0001=ADV_DIRECT_IND, 0010=ADV_NONCONN_IND, 0011=SCAN_REQ, 0100=SCAN_RSP, 0101=CONNECT_IND, 0110=ADV_SCAN_IND |
| RFU | 1 bit [4] | Reserved |
| ChSel | 1 bit [5] | Channel Selection Algorithm (0=Algorithm1, 1=Algorithm2) |
| TxAdd | 1 bit [6] | AdvA 地址类型 (0=Public, 1=Random) |
| RxAdd | 1 bit [7] | 目标地址类型 (0=Public, 1=Random)，仅 ADV_DIRECT_IND 和 CONNECT_IND 使用 |
| Length | 8 bit [15:8] | Payload 长度 (6~37 字节) |

**数据信道 PDU Header (16 bit) — LL Data / LL Control**

```
 bit: [15:8]    [7:6]  [5]   [4]   [3]   [2]   [1:0]
     ┌────────┬──────┬─────┬─────┬─────┬─────┬────────┐
     │ Length │ RFU  │ CP  │ MD  │ SN  │NESN │  LLID  │
     │ 8 bit  │ 2b   │ 1b  │ 1b  │ 1b  │ 1b  │ 2 bit  │
     └────────┴──────┴─────┴─────┴─────┴─────┴────────┘
```

| 字段 | 位宽 | 说明 |
|------|------|------|
| LLID | 2 bit [1:0] | 10=Data起始片段, 01=空包/续传, 11=Control PDU |
| NESN | 1 bit [2] | Next Expected SN — 确认对方上一包已收，期望下一个 SN |
| SN | 1 bit [3] | Sequence Number — 本包序列号 (0/1 翻转，相同=重传) |
| MD | 1 bit [4] | More Data — 本连接事件内是否还有更多数据 |
| CP | 1 bit [5] | Coded PHY 指示 (BLE 5.0: 0=非Coded, 1=Coded) |
| RFU | 2 bit [7:6] | Reserved |
| Length | 8 bit [15:8] | Payload 长度 (0~251 字节，0=空包) |

---

### 情况 1：通用可连接广播 → 连接

**何时发生**：最常见场景。设备 B 上电后广播，允许任何设备扫描和连接。

```text
设备B (Peripheral)                    设备A (Central)
  │                                       │
  │ ADV_IND ─────────────────────────────→│  37/38/39 信道轮发
  │                                       │  扫描到设备
  │                              (可选)    │
  │←──────── SCAN_REQ ────────────        │  请求更多信息
  │ SCAN_RSP ─────────────────────→       │  额外 31 字节
  │                                       │
  │←──────── CONNECT_IND ──────────       │  发起连接
  │                                       │
══╪═══════ Connection ════════════╪═══════╪══
```

**ADV_IND 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0000 (ADV_IND) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 (0=Public MAC, 1=Random MAC) |
| RxAdd | 1 bit [7] | 0 |
| Length | 8 bit [15:8] | 6 + AdvData 长度 |

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | 设备 B 的 MAC 地址 |
| AdvData | 0~31 字节 | AD Structure LTV 格式 |

**CONNECT_IND 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0101 (CONNECT_IND) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 (InitA 地址类型) |
| RxAdd | 1 bit [7] | 0/1 (AdvA 地址类型) |
| Length | 8 bit [15:8] | 34 |

**PDU Payload (34 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| InitA | 6 字节 | 设备 A 的 MAC 地址 |
| AdvA | 6 字节 | 设备 B 的 MAC 地址 |
| AA | **4 字节** | **32 位随机 Access Address，后续所有数据包用这个标识连接** |
| CRCInit | 3 字节 | CRC 初始值 |
| WinSize | 1 字节 | 传输窗口大小 = 1.25ms × WinSize |
| WinOffset | 2 字节 | 传输窗口偏移 = 1.25ms × WinOffset |
| Interval | 2 字节 | 连接间隔 = 1.25ms × Interval，范围 7.5ms~4s |
| Latency | 2 字节 | 从设备延迟次数，0~499 |
| Timeout | 2 字节 | 监督超时 = 10ms × Timeout，范围 100ms~32s |
| ChM | 5 字节 | 37 位信道图（bit=1 表示可用） |
| Hop | 1 字节 | 跳频增量（必须与 37 互质，典型值 5~16） |
| SCA | 1 字节 | 睡眠时钟精度（0~7），决定 WinOffset 的安全裕度 |

**连接参数约束**：

```text
约束 1: Interval 范围 6~3200 (即 7.5ms ~ 4s)
约束 2: (1 + Latency) × Interval × 2 ≤ Timeout
       否则可能因等待过久被误判为断连
约束 3: Timeout 范围 10~3200 (即 100ms ~ 32s)
```

---

### 情况 2：定向可连接广播 → 连接

```text
设备B                                设备A(地址在 InitA 中指定)
  │                                       │
  │ ADV_DIRECT_IND ──────────────────────→│  仅指定设备能响应
  │                                       │
  │←──────── CONNECT_IND ──────────       │  (必须在 1.28s 内发起)
  │                                       │
══╪═══════ Connection ════════════╪═══════╪══
```

**ADV_DIRECT_IND 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0001 (ADV_DIRECT_IND) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 |
| RxAdd | 1 bit [7] | 0/1 |
| Length | 8 bit [15:8] | 12 |

**PDU Payload (12 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | 设备 B 的 MAC |
| InitA | 6 字节 | 允许连接的设备 A 的 MAC（白名单） |

**特点**：无 AdvData。持续仅 1.28 秒，超时自动停止。

---

### 情况 3：只广播不连接（Beacon）

```text
设备B
  │
  │ ADV_NONCONN_IND ──────────────→  37/38/39 信道
  │                                  最多 31 字节数据
  │                                  不可扫描，不可连接
```

**ADV_NONCONN_IND 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0010 (ADV_NONCONN_IND) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 |
| RxAdd | 1 bit [7] | 0 |
| Length | 8 bit [15:8] | 6 + AdvData 长度 |

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | |
| AdvData | 0~31 字节 | 如 iBeacon 格式 |

---

### 情况 4：可扫描不可连接广播

```text
设备B                                设备A
  │                                       │
  │ ADV_SCAN_IND ────────────────────────→│
  │←──────── SCAN_REQ ────────────        │
  │ SCAN_RSP ─────────────────────→       │ 额外 31 字节
  │ (不能发 CONNECT_IND)                   │
```

**ADV_SCAN_IND 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0110 (ADV_SCAN_IND) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 |
| RxAdd | 1 bit [7] | 0 |
| Length | 8 bit [15:8] | 6 + AdvData 长度 |

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | |
| AdvData | 0~31 字节 | |

**SCAN_REQ 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0011 (SCAN_REQ) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 (ScanA 地址类型) |
| RxAdd | 1 bit [7] | 0/1 (AdvA 地址类型) |
| Length | 8 bit [15:8] | 12 |

**PDU Payload (12 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| ScanA | 6 字节 | 设备 A 的 MAC |
| AdvA | 6 字节 | 设备 B 的 MAC（确认是发给我的） |

**SCAN_RSP 报文**：

**PDU Header (16 bit，广告信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| PDU Type | 4 bit [3:0] | 0100 (SCAN_RSP) |
| RFU | 1 bit [4] | 0 |
| ChSel | 1 bit [5] | 0 |
| TxAdd | 1 bit [6] | 0/1 |
| RxAdd | 1 bit [7] | 0 |
| Length | 8 bit [15:8] | 6 + ScanRspData 长度 |

**PDU Payload**：

| 字段 | 大小 | 说明 |
|------|------|------|
| AdvA | 6 字节 | |
| ScanRspData | 0~31 字节 | 额外信息 |

**状态变化**：设备 B 发送 ADV_SCAN_IND → 收到 SCAN_REQ → 回复 SCAN_RSP → 继续发 ADV_SCAN_IND。**状态不变，始终是 Advertising。**

---

### 情况 5：BLE 5.0 扩展广播

```text
设备B
  │
  │ ADV_EXT_IND (主信道 37/38/39) ───→  仅含 AuxPtr 指针
  │ AUX_ADV_IND (辅助信道 0~36)  ───→  实际数据，最多 254 字节
  │
  │ (如果可扫描)
  │←──────── AUX_SCAN_REQ ────────
  │ AUX_SCAN_RSP ────────────────→
  │
  │ (如果可连接)
  │←──────── AUX_CONNECT_REQ ─────
  │
══╪═══════ Connection ════════════╪══
```

新增 PDU 类型：ADV_EXT_IND(0x07)、AUX_ADV_IND(0x09)、AUX_SCAN_REQ(0x0B)、AUX_SCAN_RSP(0x0C)、AUX_CONNECT_REQ(0x0D)、AUX_CONNECT_RSP(0x0E)

---

## 三、连接阶段（Connection State）

### 情况 6：正常连接事件（数据 + 空包确认）

**何时发生**：每一个连接事件，按 Connection Interval 周期发生。

```text
连接事件 n (信道 = hop(n)):

设备A (Master)                              设备B (Slave)
  │                                           │
  │ LL Data PDU ────────────────────────────→│  150μs 后必须回复
  │   [LLID=10, SN=0, NESN=0, MD=0, Len=7]  │
  │   Payload: L2CAP → ATT Write Request     │
  │                                           │
  │←──────── LL Data PDU (空包) ────────      │  LLID=01, 确认收到
  │           [LLID=01, SN=0, NESN=1]         │
  │                                           │
══╪═══════ 双方睡眠 ══════════════════════╪══════ 等待下一个连接事件
```

**LL Data PDU — 携带 ATT 数据**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 10 (Data PDU, 起始片段) |
| NESN | 1 bit [2] | 0/1 (期望对方下个 SN) |
| SN | 1 bit [3] | 0/1 (本包 SN, 翻转=新包, 相同=重传) |
| MD | 1 bit [4] | 0/1 (本事件内是否还有更多数据) |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | Payload 长度 (最大 251, 4.2+) |

**PDU Payload (L2CAP 包)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| L2CAP Length | 2 字节 | |
| L2CAP CID | 2 字节 | 0x0004=ATT, 0x0006=SM, 0x0005=L2CAP Signaling |
| ATT Data | 可变 | 如 Opcode(1B) + Handle(2B) + Value(可变) |

**LL Data PDU — 空包（确认/心跳）**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 01 (Data PDU, 空包/续传) |
| NESN | 1 bit [2] | 确认收到的 SN |
| SN | 1 bit [3] | 本包 SN |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 0 (无 Payload) |

**加密后的 LL Data PDU**：

```text
加密范围：
  ✅ 加密: Payload (L2CAP → ATT 全部) + MIC (4 字节)
  ❌ 明文: Preamble + Access Address + PDU Header(LLID/SN/NESN/MD/Length) + CRC
```

---

### 情况 7：从设备延迟（Slave Latency）

```text
Latency = 3 (允许跳过最多 3 个连接事件)

事件1: M ──→ S (正常)
事件2: M ──→ S (正常)
事件3: M ──→  (S 没醒来)
事件4: M ──→  (S 又没醒来)
事件5: M ──→ S (S 必须在此醒来)

约束: (1 + Latency) × Interval × 2 ≤ Timeout
```

---

### 情况 8：连接参数更新 — LL_CONNECTION_UPDATE_REQ

```text
设备A                                    设备B
  │                                         │
  │ LL_CONNECTION_UPDATE_REQ ──────────────→│ LL Control, Opcode=0x00
  │←──────── LL Data PDU (空包) ───────────┤ 确认收到
  │                                         │
══╪══ 新参数在 Instant 时刻生效 ════════════╪══
```

**LL_CONNECTION_UPDATE_REQ**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0/1 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 11 |

**Control Payload (11 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x00 |
| WinSize | 1 字节 | |
| WinOffset | 2 字节 | = 1.25ms × WinOffset |
| Interval | 2 字节 | 新连接间隔 |
| Latency | 2 字节 | 新从设备延迟 |
| Timeout | 2 字节 | 新监督超时 |
| Instant | 2 字节 | 生效时刻（连接事件序号） |

**注意**：LL_CONNECTION_UPDATE_REQ 是 Control PDU，没有 Response。接受则在 Instant 时刻自动切换。拒绝则回 LL_REJECT_IND。

---

### 情况 9：信道图更新 — LL_CHANNEL_MAP_REQ

```text
设备A                                    设备B
  │                                         │
  │ LL_CHANNEL_MAP_REQ ────────────────────→│ Opcode=0x01
  │←──────── LL Data PDU (空包) ───────────┤
══╪══ 使用新信道图 ═════════════════════════╪══
```

**LL_CHANNEL_MAP_REQ**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 8 |

**Control Payload (8 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x01 |
| ChM | 5 字节 | 37 位信道图（bit=1 表示可用） |
| Instant | 2 字节 | 生效时刻 |

---

### 情况 10：PHY 更新（BLE 5.0+） — LL_PHY_REQ/RSP

```text
设备A                                    设备B
  │                                         │
  │ LL_PHY_REQ ────────────────────────────→│ Opcode=0x14
  │←──────── LL_PHY_RSP ───────────────────┤ Opcode=0x15
```

**LL_PHY_REQ/RSP**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 3 |

**Control Payload (3 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x14(Req) / 0x15(Rsp) |
| TX_PHYS | 1 字节 | bit0=1M, bit1=2M, bit2=Coded(S8), bit3=Coded(S2) |
| RX_PHYS | 1 字节 | 同上 |

---

### 情况 11：版本交换 — LL_VERSION_IND

```text
设备A ←─────→ 设备B (双方都可能主动发)
  LL_VERSION_IND, Opcode=0x0C
```

**LL_VERSION_IND**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 6 |

**Control Payload (6 字节)**：

---

### 情况 12：特性交换 — LL_FEATURE_REQ/RSP

```text
设备A                                    设备B
  │                                         │
  │ LL_FEATURE_REQ ────────────────────────→│ Opcode=0x08
  │←──────── LL_FEATURE_RSP ───────────────┤ Opcode=0x09
```

**LL_FEATURE_REQ/RSP**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 9 |

**Control Payload (9 字节)**：

FeatureSet 关键位：

```
bit 0:  LE Encryption
bit 1:  Connection Parameters Request
bit 3:  Slave-initiated Features Exchange
bit 5:  LE Data Packet Length Extension (BLE 4.2)
bit 8:  LE 2M PHY (BLE 5.0)
bit 9:  LE Coded PHY (BLE 5.0)
bit 10: LE Extended Advertising (BLE 5.0)
```

---

### 情况 13：数据长度扩展 — LL_LENGTH_REQ/RSP（4.2+）

```text
设备A                                    设备B
  │                                         │
  │ LL_LENGTH_REQ ─────────────────────────→│ Opcode=0x16
  │←──────── LL_LENGTH_RSP ────────────────┤ Opcode=0x17
```

**LL_LENGTH_REQ/RSP**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 9 |

**Control Payload (9 字节)**：
| MaxTxOctets | 2 字节 | 最大发送 Payload 字节数 |
| MaxTxTime | 2 字节 | 最大发送时间（μs） |

---

### 情况 14：断开连接 — LL_TERMINATE_IND

```text
设备A                                    设备B
  │                                         │
  │ LL_TERMINATE_IND ──────────────────────→│ Opcode=0x02
  │                                         │
══╪═══════ Standby ════════════════════════╪══
  (CCCD 自动归零，绑定信息保留)
```

**LL_TERMINATE_IND**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 2 |

**Control Payload (2 字节)**：

---

### 情况 15：拒绝 Control PDU — LL_REJECT_IND

```text
设备A                                    设备B
  │                                         │
  │ (发送不支持的 Control PDU)                │
  │←──────── LL_REJECT_IND ────────────────┤ Opcode=0x0D
```

**LL_REJECT_IND**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 3 |

**Control Payload (3 字节)**：

---

## 四、安全管理器配对（SMP）

> 所有 SMP PDU 封装在 L2CAP CID=0x0006 中，再由 LL Data PDU 承载。
>
> **承载格式**：
>
> ```
> LL Data PDU (LLID=10):
>   PDU Header (16 bit, 数据信道格式): LLID=10, NESN/SN/MD/CP/RFU, Length
>   Payload = L2CAP 包:
>     ┌──────────┬──────────┬──────────────────────────────┐
>     │ L2CAP Len│ CID=0x0006│      SMP PDU                 │
>     │  2 字节   │  2 字节    │ (Code + Data)               │
>     └──────────┴──────────┴──────────────────────────────┘
> ```
>
> **SMP PDU 通用格式**：`[Code(1B)] [Data(可变)]`，Code 标识 SMP 操作类型。

### 情况 16：配对特征交换（Phase 1）

```text
设备A                                    设备B
  │                                         │
  │ SMP Pairing Request ───────────────────→│
  │←──────── SMP Pairing Response ──────────┤
  │                                         │
  │ 双方根据 IO Capabilities 决定配对方式：    │
  │ 任一方 NoInputNoOutput → Just Works      │
  │ 双方都有显示+确认 → Numeric Comparison    │
  │ 一方显示一方键盘 → Passkey Entry          │
```

**SMP Pairing Request/Response**：

**SMP PDU 格式**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x01(Req) / 0x02(Rsp) |
| IO Cap | 1 字节 | 0x00=DisplayOnly, 0x01=DisplayYesNo, 0x02=KeyboardOnly, 0x03=NoInputNoOutput, 0x04=KeyboardDisplay |
| OOB Flag | 1 字节 | 0x00=不使用OOB |
| AuthReq | 1 字节 | bit0=Bonding, bit2=MITM, bit3=SC, bit4=Keypress |
| Max Key Sz | 1 字节 | 最大密钥长度(7~16) |
| Init Key | 1 字节 | 发起方要分发的密钥类型位图 |
| Resp Key | 1 字节 | 响应方要分发的密钥类型位图 |

---

### 情况 17：LE Legacy Pairing（Phase 2 → Phase 3）

**何时发生**：BLE 4.0/4.1 设备或不支持 SC。

```text
Phase 2: TK 生成 STK
  Just Works: TK = 0
  Passkey:    6 位 PIN (20 bit 安全强度)

  Mconfirm = AES-CMAC(TK, Mrand || 配对信息)
  Sconfirm = AES-CMAC(TK, Srand || 配对信息)

  │ SMP: Mconfirm ──────────────────────→│
  │←──────── SMP: Sconfirm ──────────────┤
  │ SMP: Mrand ─────────────────────────→│
  │←──────── SMP: Srand ─────────────────┤
  │ 双方各自验证 Confirm 值                 │
  │                                     │
  │ STK = AES-CMAC(TK, Mrand || Srand) │

Phase 3: STK 加密 → 分发 LTK
  │ SMP (STK加密): LTK ─────────────────→│
  │← SMP (STK加密): EDIV+Rand ───────────┤
  │← SMP (STK加密): IRK ─────────────────┤
  │← SMP (STK加密): CSRK ────────────────┤
```

**SMP Pairing Confirm**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x03 |
| Confirm | 16 字节 | AES-CMAC(TK, Mrand/Srand \|\| 配对信息)，128-bit |

**SMP Pairing Random**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x04 |
| Random | 16 字节 | Mrand 或 Srand，128-bit 随机数 |

**关键弱点**：Legacy Just Works 时 TK=0，旁听者抓到 Mconfirm+Mrand 即可算出 STK。

---

### 情况 18：LE Secure Connections — Numeric Comparison（Phase 2~3）

**何时发生**：BLE 4.2+，双方都有显示能力。

```text
Phase 2: ECDH 公钥交换 ← 公私钥在这里交换！
  双方各生成 256-bit 私钥 (sk_a, sk_b)
  计算公钥: Pka = sk_a × G,  Pkb = sk_b × G

  │ SMP Public Key: Pka (64 字节) ────────→│
  │←──────── SMP Public Key: Pkb (64 字节) ─┤
  │                                      │
  │ DHKey = ECDH(自己私钥, 对方公钥)        │

Phase 3: Numeric Comparison (用户替代 CA)
  Na = 随机数(128 bit),  Nb = 随机数(128 bit)

  │ SMP: Na ─────────────────────────────→│
  │←──────── SMP: Nb ─────────────────────┤
  │                                      │
  │ C = f4(Pka, Pkb, Na, 0)              │
  │ → 取前 6 位十进制                     │
  │ 手机显示 "837265"                    │
  │                                      │
  │ 用户: 数字一样 → 按确认                 │
  │ SMP: Confirm ────────────────────────→│

Phase 4: DHKey 校验
  │ SMP DHKey Check ─────────────────────→│
  │←──────── SMP DHKey Check ────────────┤
  │ AES-CMAC验证 → 一致 = 密钥交换未被篡改  │
```

**SMP Public Key**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x0C |
| P-256 X | 32 字节 | 椭圆曲线点 X 坐标 |
| P-256 Y | 32 字节 | 椭圆曲线点 Y 坐标 |

**SMP DHKey Check**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Code | 1 字节 | 0x0D |
| DHKey_Check | 16 字节 | AES-CMAC(MacKey, DHKey \|\| Na/Nb \|\| IO Caps \|\| 地址A \|\| 地址B) |

**密钥派生链**：

```text
DHKey ──f5(DHKey, Na, Nb, 地址a, 地址b)──→ LTK (128-bit)
      ──f5──→ MacKey (128-bit)
      ──f6(MacKey, Na, Nb, IO, 地址)──→ 校验值 (128-bit)

后续每条连接：
LTK ──AES-CMAC(LTK, SKDm||SKDs)──→ SessionKey (128-bit, 每条连接新建)
```

---

### 情况 19：LE Secure Connections — Just Works

```text
Phase 2: ECDH 公钥交换 (同上)
Phase 3: 跳过！不验证身份
Phase 4: DHKey → f5 → LTK (密钥仍 128-bit 强)

加密了，但不知道在跟谁加密。
MITM 攻击者可在 Phase 2 拦截公钥并用自己的替换：
  Phone ←→ 攻击者(SessionKey₁) ←→ 耳机(SessionKey₂)
  攻击者完全透明地读、改、转发一切数据。
```

---

### 情况 20：LE Secure Connections — Passkey Entry

```text
Phase 2: ECDH 公钥交换
Phase 3: 一方显示 6 位 PIN → 用户输入到另一方
  PIN 通过 SMP Keypress Notification 逐位确认
  PIN 作为 Na/Nb 种子参与 f4
  → 只有相同 PIN 的双方才能生成相同确认码
```

---

### 情况 21：密钥分发（Phase 4）

```text
加密隧道建立后，分发长期密钥：

  │ SMP (加密): LTK ─────────────────────→│
  │←──────── SMP (加密): EDIV+Rand ───────┤
  │←──────── SMP (加密): IRK ─────────────┤
  │←──────── SMP (加密): CSRK ────────────┤
  │←──────── SMP (加密): 地址信息 ─────────┤
```

SMP 密钥分发 PDU：

| Code | PDU 名称 | 大小 | 内容 |
|------|---------|------|------|
| 0x06 | Encryption Info | 16B | LTK |
| 0x07 | Master ID | 10B | EDIV(2B)+Rand(8B) ← 下次找 LTK 的索引 |
| 0x08 | Identity Info | 16B | IRK ← 解析私有地址 |
| 0x09 | Identity Address | 7B | AddrType(1B)+Addr(6B) |
| 0x0A | Signing Info | 16B | CSRK ← 数据签名 |

---

## 五、链路层加密阶段

### 情况 22：启动加密（三次握手） — LL_ENC_REQ/RSP

```text
设备A                                    设备B
  │                                         │
  │ LL_ENC_REQ ───────────────────────────→│ LL Control, Opcode=0x03
  │←──────── LL_ENC_RSP ───────────────────│ LL Control, Opcode=0x04
  │                                         │
  │ SessionKey = AES-CMAC(LTK, SKDm||SKDs) │
  │                                         │
  │ LL_START_ENC_REQ ──────────────────────→│ LL Control, Opcode=0x05
  │←──────── LL_START_ENC_RSP ──────────────│ LL Control, Opcode=0x06
  │                                         │
══╪══════ 此后所有包 AES-CCM 加密 ═══════════╪══
```

**LL_ENC_REQ**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 23 |

**Control Payload (23 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x03 |
| Rand | 8 字节 | 64-bit 随机数（配合 EDIV 索引 LTK） |
| EDIV | 2 字节 | 加密分集（LTK 索引号） |
| SKDm | 8 字节 | Master Session Key Diversifier |
| IVm | 4 字节 | Master Initial Vector |

**LL_ENC_RSP**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 13 |

**Control Payload (13 字节)**：

**LL_START_ENC_REQ/RSP**：

**PDU Header (16 bit，数据信道格式)**：

| 字段 | 位宽 | 值 |
|------|------|-----|
| LLID | 2 bit [1:0] | 11 (Control PDU) |
| NESN | 1 bit [2] | 0/1 |
| SN | 1 bit [3] | 0/1 |
| MD | 1 bit [4] | 0 |
| CP | 1 bit [5] | 0 |
| RFU | 2 bit [7:6] | 00 |
| Length | 8 bit [15:8] | 1 |

**Control Payload (1 字节)**：

| 字段 | 大小 | 说明 |
|------|------|------|
| Opcode | 1 字节 | 0x05(REQ) / 0x06(RSP) |

**这两个包本身是明文**——对方必须先读到"开始加密"才能切换解密引擎。

**Session Key 派生**：

```text
SessionKey = AES-CMAC(
    Key  = LTK (128 bit),
    Data = SKDm (64 bit) || SKDs (64 bit)
)

每次连接全新 SKDm/SKDs → SessionKey 每次都不同 → 防重放
```

---

### 情况 23：绑定设备重连 — 跳过配对直接加密

```text
设备A                                    设备B
  │                                         │
══╪═══════ 连接建立 ═══════════════════════╪══
  │                                         │
  │ LL_ENC_REQ (EDIV+Rand → 查LTK) ───────→│  ← 跳过全部 SMP 配对！
  │←──────── LL_ENC_RSP ───────────────────┤
  │ LL_START_ENC_REQ ──────────────────────→│
  │←──────── LL_START_ENC_RSP ──────────────┤
  │                                         │
══╪══════ 加密通信 ════════════════════════╪══

EDIV+Rand 作为"钥匙串编号"，设备 B 从中找到对应的 LTK。
```

---

### 情况 24：加密拒绝

```text
设备A                                    设备B
  │                                         │
  │ LL_ENC_REQ ───────────────────────────→│
  │←──────── LL_REJECT_IND ────────────────┤
  │ RejectOpcode=0x03, ErrorCode=...      │
  │                                         │
══╪══ 连接继续(明文)或断开 ══════════════════╪══
```

常见 ErrorCode：0x05=Authentication Failure, 0x06=PIN/Key Missing, 0x2F=Insufficient Authentication

---

### 情况 25：加密暂停/重启（BLE 5.1+）

```text
══╪══════ 加密通信中 ═══════════════════════╪══
  │                                         │
  │ LL_PAUSE_ENC_REQ ──────────────────────→│ Opcode=0x19
  │←──────── LL_PAUSE_ENC_RSP ──────────────┤
══╪══════ 明文通信(分发新LTK) ════════════╪══
  │                                         │
  │ LL_ENC_REQ (新 LTK) ──────────────────→│
```

---

### 情况 26：MIC 校验失败

```text
设备收到加密包 → 解密 Payload → 重新算 MIC
  → 算出的 MIC ≠ 收到的 MIC → 丢弃此包
  → 连续多次失败 → LL_TERMINATE_IND (ErrorCode=0x05)

开发排查：最常见原因是双方 LTK 不一致 → removeBond() 后重新配对
```

---

## 六、综合速查表

| 场景 | 触发条件 | 主要 PDU | 信道 |
|------|---------|---------|------|
| 广播+连接 | 设备上电，任何人可连 | ADV_IND → CONNECT_IND | 37/38/39 |
| 定向广播+连接 | 仅指定 MAC 可连 | ADV_DIRECT_IND → CONNECT_IND | 37/38/39 |
| 纯信标 | 只广播不连接 | ADV_NONCONN_IND | 37/38/39 |
| 广播+额外信息 | 可扫描不可连 | ADV_SCAN_IND + SCAN_REQ/RSP | 37/38/39 |
| 连接事件 | 每次连接间隔 | LL Data PDU + 空包 | 0~36 |
| 从设备跳过 | 无数据省电 | 空包 + Latency | 0~36 |
| 参数更新 | 改间隔/延迟/超时 | LL_CONNECTION_UPDATE_REQ | 0~36 |
| 信道更新 | 检测干扰 | LL_CHANNEL_MAP_REQ | 0~36 |
| PHY 切换 | 1M/2M/Coded | LL_PHY_REQ/RSP | 0~36 |
| 版本交换 | 协商能力 | LL_VERSION_IND | 0~36 |
| 特性交换 | 协商功能 | LL_FEATURE_REQ/RSP | 0~36 |
| 数据长度扩展 | 更大 Payload | LL_LENGTH_REQ/RSP | 0~36 |
| 断开连接 | 任一方主动断开 | LL_TERMINATE_IND | 0~36 |
| 拒绝 Control | 不支持的操作 | LL_REJECT_IND | 0~36 |
| ─ | | | |
| 配对特征交换 | Phase 1 | SMP Pairing Req/Rsp | 0~36 (L2CAP) |
| Legacy 配对 | BLE 4.0/4.1 | SMP Confirm+Random | 0~36 (L2CAP) |
| SC 公钥交换 | Phase 2 | SMP Public Key (64B) | 0~36 (L2CAP) |
| SC NumComp | Phase 3 | SMP Na/Nb + 用户比对 6 位数字 | 0~36 (L2CAP) |
| SC Just Works | Phase 3 跳过 | 无确认，直接 Phase 4 | 0~36 (L2CAP) |
| 密钥分发 | Phase 4 | SMP Encryption/Master/Identity/Signing Info | 0~36 (L2CAP) |
| ─ | | | |
| 首次加密 | 配对后立即 | LL_ENC_REQ/RSP → START_ENC | 0~36 |
| 重连加密 | 绑定设备重连 | 直接 ENC_REQ/RSP，跳过 SMP | 0~36 |
| 加密拒绝 | 不支持/密钥缺失 | LL_REJECT_IND | 0~36 |
| 加密暂停 | 更新密钥 | LL_PAUSE_ENC_REQ/RSP | 0~36 |
| MIC 失败 | 密钥不一致 | 包丢弃 + 连接断开 | 0~36 |

---

## 七、完整 LL Control PDU Opcode 索引

| Opcode | PDU | 方向 | 说明 |
|--------|-----|------|------|
| 0x00 | LL_CONNECTION_UPDATE_REQ | M→S | 更新连接参数 |
| 0x01 | LL_CHANNEL_MAP_REQ | M→S | 更新信道图 |
| 0x02 | LL_TERMINATE_IND | 双向 | 断开连接 |
| 0x03 | LL_ENC_REQ | M→S | 加密请求 |
| 0x04 | LL_ENC_RSP | S→M | 加密响应 |
| 0x05 | LL_START_ENC_REQ | M→S | 开始加密（明文） |
| 0x06 | LL_START_ENC_RSP | S→M | 开始加密确认（明文） |
| 0x07 | LL_UNKNOWN_RSP | 双向 | 收到未知 Control PDU |
| 0x08 | LL_FEATURE_REQ | 双向 | 特性请求 |
| 0x09 | LL_FEATURE_RSP | 双向 | 特性响应 |
| 0x0A | LL_PAUSE_ENC_REQ | 双向 | 暂停加密 (5.1+) |
| 0x0B | LL_PAUSE_ENC_RSP | 双向 | 暂停加密确认 |
| 0x0C | LL_VERSION_IND | 双向 | 版本通知 |
| 0x0D | LL_REJECT_IND | 双向 | 拒绝 Control PDU |
| 0x0E | LL_SLAVE_FEATURE_REQ | S→M | 从设备特性请求 (4.2+) |
| 0x14 | LL_PHY_REQ | 双向 | PHY 更新请求 (5.0) |
| 0x15 | LL_PHY_RSP | 双向 | PHY 更新响应 |
| 0x16 | LL_LENGTH_REQ | 双向 | 数据长度请求 (4.2) |
| 0x17 | LL_LENGTH_RSP | 双向 | 数据长度响应 |
| 0x19 | LL_PERIODIC_SYNC_IND | — | 周期同步(5.0) |

---

*记录时间：2026-07-14*
*关联：[[3.7-链路层PDU格式]] [[3.5-连接建立全过程]] [[5.4-LE-Secure-Connections详解]] [[5.6-链路层加密]] [[5.1-安全流程全景]] [[4.1-HCI主机控制器接口]] [[附录-报文手册深度问答]]*
