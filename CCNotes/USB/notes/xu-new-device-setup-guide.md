# UVC XU 新设备上手实操指南

> 目的：拿到一台新 UVC 摄像头 → 找到 XU 参数 → 构造 SETUP 包 → 发出第一条 XU 命令
> 前置：已理解 SETUP 包 8 字节结构（bmRequestType + bRequest + wValue + wIndex + wLength）

---

## 一、三步找到所有参数

### 第 1 步：找到设备 VID/PID

```bash
lsusb
# Bus 003 Device 005: ID 2bdf:0101 HIK HikCamera
#                         ──── ────
#                          VID  PID
```

### 第 2 步：找到 Extension Unit 的 ID

```bash
sudo lsusb -v -d 2bdf:0101 > /tmp/cam.txt
grep -n "EXTENSION_UNIT\|bUnitID\|bInterfaceNumber\|Video Control" /tmp/cam.txt
```

你会看到类似：

```
37:    Interface Descriptor:
38:      bInterfaceNumber        0        ← VC_IF_NUM = 0
...
47:      VideoControl Interface Descriptor:
...
86:        bUnitID                10       ← XU_UNIT_ID = 0x0A
85:        bDescriptorSubtype      6 (EXTENSION_UNIT)
```

**四个参数齐了**：

| 参数 | 值 | 含义 | 在 SETUP 包里放哪 |
|------|-----|------|-------------------|
| VID:PID | `2bdf:0101` | 设备标识 | 不在 SETUP 包里，是 `libusb_open_device_with_vid_pid()` 用的 |
| XU Unit ID | `0x0A` | 扩展单元编号 | **wIndex 高字节** |
| VC IF number | `0` | Video Control 接口号 | **wIndex 低字节** |

> **关键**：XU Unit ID 是 `bUnitID` 的值，**不是** Extension Unit 块的序号。不管设备有几个 Unit，只管你要的那个 Extension Unit 的 `bUnitID`。

### 第 3 步：看 bmControls 位图，了解支持哪些 CS_ID

```bash
sed -n '85,100p' /tmp/cam.txt
```

你设备的真实数据（设备 1 和 2 完全一致）：

```
bLength                  : 0x1D (29 bytes)
bDescriptorType          : 0x24 (Video Control Interface)
bDescriptorSubtype       : 0x06 (Extension Unit)
bUnitID                  : 0x0A (ID 10)
guidExtensionCode        : {A29E7641-DE04-47E3-8B2B-F4341AFF003B}
bNumControls             : 0x0F (15 Controls)
bNrInPins                : 0x01 (1 Input Pin)
baSourceID[1]            : 0x02
bControlSize             : 0x04 (4 bytes)
bmControls               : 0xFF, 0x03, 0x00, 0x00
 D0                      : 1  yes  → CS_ID 0x01 支持
 D1                      : 1  yes  → CS_ID 0x02 支持
 D2                      : 1  yes  → CS_ID 0x03 支持
 D3                      : 1  yes  → CS_ID 0x04 支持  ← 协议版本
 D4                      : 1  yes  → CS_ID 0x05 支持  ← 功能切换
 D5                      : 1  yes  → CS_ID 0x06 支持  ← 错误码
 D6                      : 1  yes  → CS_ID 0x07 支持
 D7                      : 1  yes  → CS_ID 0x08 支持
 D8                      : 1  yes  → CS_ID 0x09 支持
 D9                      : 1  yes  → CS_ID 0x0A 支持
 D10~D14                 : 0  no   → CS_ID 0x0B~0x0F 不支持
```

**位图规则**：

```
bmControls 是 4 字节小端位图：0xFF, 0x03, 0x00, 0x00

LE 还原为 32-bit: 0x000003FF
                   ────────┬────────
                   高 16 位 │ 低 16 位
                           └─ bit 0~9 置位

bit N = 1  → CS_ID(N+1) 存在   (bit 0 → CS_ID 0x01)
bit N = 0  → CS_ID(N+1) 不存在

bNumControls = 15  → 只有前 15 个 bit 有意义
```

> **设备 3 没有 Extension Unit**——不是 UVC 设备或走其他控制通道。

---

## 二、从参数到 SETUP 包 8 字节

SETUP 包结构（固定格式，所有 USB 控制传输都一样）：

```
Byte 0:  bmRequestType     ← D7=方向, D6-5=字典, D4-0=接收者
Byte 1:  bRequest          ← 命令号
Byte 2-3: wValue (LE)      ← 含义由 bmRequestType 决定
Byte 4-5: wIndex (LE)      ← 含义由 bmRequestType 决定
Byte 6-7: wLength (LE)     ← DATA 阶段字节数
```

### 关键规则：UVC XU 约定

对于 UVC Extension Unit 的 Class 请求，**UVC 规范**规定了 wValue 和 wIndex 的填法：

| 字段 | UVC XU 约定 | 你的设备值 |
|------|------------|-----------|
| wValue 高字节 | **CS_ID**（你要操作的功能号） | 0x04（协议版本）/ 0x05（功能切换）/ 等 |
| wValue 低字节 | 0x00（不用） | 0x00 |
| wIndex 高字节 | **XU Unit ID**（lsusb 查的 bUnitID） | 0x0A |
| wIndex 低字节 | **接口号**（Video Control 接口的 bInterfaceNumber） | 0x00 |

所以不管你操作哪个 CS_ID，**wIndex 是不变的**：

```
wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM
       = (0x0A << 8) | 0x00
       = 0x0A00
```

### 三条 SETUP 包的逐字节构造

每种操作对应一个 bRequest：

| 操作 | bmRequestType | bRequest | wValue | wIndex | wLength |
|------|--------------|----------|--------|--------|---------|
| SET_CUR（写） | 0x21 | 0x01 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 数据长度 |
| GET_CUR（读） | 0xA1 | 0x81 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 参数长度 |
| GET_LEN（问长度） | 0xA1 | 0x85 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 2 |

以你的设备（XU_ID=0x0A, IF=0）读 CS_ID=0x04 为例：

```
        ┌──────────────┬──────┬───────────┬──────────┬──────────┐
        │ bmRequestType│ bReq │  wValue   │  wIndex  │ wLength  │
        ├──────────────┼──────┼───────────┼──────────┼──────────┤
GET_LEN │     A1       │  85  │  04 00    │  0A 00   │  02 00   │
GET_CUR │     A1       │  81  │  04 00    │  0A 00   │  04 00   │ ← len 来自上一步返回值
FUNC_SW │     21       │  01  │  05 00    │  0A 00   │  02 00   │ + data=[CS_ID,SubFunc]
        └──────────────┴──────┴───────────┴──────────┴──────────┘
```

> LE 字节序：wValue=0x0004 在 USB 线上是 `04 00`（低位在前）
> wIndex=0x000A 在 USB 线上是 `0A 00`

---

## 三、新设备上手的实际顺序

拿到一台新摄像头，按这个顺序来：

### ① 先试 CS_ID=0x04（协议版本）

0x04 不需要 FUNC_SWITCH，最简单：

```c
// GET_LEN
libusb_control_transfer(devh, 0xA1, 0x85, 0x0004, 0x0A00, len_buf, 2, 1000);
// → 返回 4，说明 param_len=4

// GET_CUR
libusb_control_transfer(devh, 0xA1, 0x81, 0x0004, 0x0A00, buf, 4, 1000);
// → 返回 "2.0" 或其他 ASCII 版本号
```

**如果 GET_LEN 回 STALL（`LIBUSB_ERROR_PIPE`）**：说明这个 CS_ID 不存在或 XU_ID 不对。再确认 `bUnitID`。

**如果 GET_LEN 成功**：说明你的 XU_ID 和 IF 号都对，通道通了。

### ② 再试带 SubFunc 的 CS_ID

找一个已知的 CS_ID（比如海康的 CS_ID=0x03 THERMAL, SubFunc=0x05），走三阶段：

```
FUNC_SWITCH(0x03, 0x05) → GET_LEN(0x03) → GET_CUR(0x03)
```

### ③ 未知设备怎么探索 CS_ID

如果没有任何文档，用 `bmControls` 位图找支持的 CS_ID，然后逐个试 `GET_LEN`：

```bash
# 看 Extension Unit 的 bmControls
grep -A 10 "bUnitID.*10" /tmp/cam.txt
```

bmControls 是位图（小端），bit N=1 表示 CS_ID(N+1) 存在。试每个置位的 CS_ID 发 GET_LEN，不 STALL 的就是可用功能。

---

## 四、SETUP 包 8 字节速查表

### bmRequestType 的三个字段

```
┌───────┬────────────────────────────────────────────┐
│  Bit  │  含义                                       │
├───────┼────────────────────────────────────────────┤
│  D7   │  方向：0=OUT(Host→Dev)  1=IN(Dev→Host)      │
│  D6-5 │  字典：00=Standard  01=Class  10=Vendor     │
│  D4-0 │  接收者：0=Device  1=Interface  2=Endpoint  │
└───────┴────────────────────────────────────────────┘
```

### UVC XU 常用的三个 bmRequestType

```
0x21 = 0010 0001  → OUT, Class, Interface   (SET_CUR / FUNC_SWITCH)
0xA1 = 1010 0001  → IN,  Class, Interface   (GET_CUR / GET_LEN)
```

### bRequest 三个值

```
0x01 = SET_CUR    写当前值
0x81 = GET_CUR    读当前值
0x85 = GET_LEN    读参数长度
```

### wValue 填法

```
高字节 = CS_ID
低字节 = 0x00
```

### wIndex 填法

```
高字节 = XU Unit ID (来自 lsusb -v 的 bUnitID)
低字节 = VC 接口号   (来自 lsusb -v 的 bInterfaceNumber)
```

---

## 五、libusb 调用和 SETUP 包的对应关系

每次调用 `libusb_control_transfer()`，libusb 自动把参数组装成 8 字节 SETUP 包发出去：

```c
libusb_control_transfer(
    devh,
    0xA1,           // → SETUP[0] = bmRequestType
    0x85,           // → SETUP[1] = bRequest
    0x0004,         // → SETUP[2-3] = wValue LE (线序: 04 00)
    0x0A00,         // → SETUP[4-5] = wIndex LE  (线序: 00 0A)
    buf,            // → DATA 阶段的数据
    2,              // → SETUP[6-7] = wLength LE (线序: 02 00)
    1000            // → 超时，不影响 SETUP 包
);
// 对应 SETUP 包 8 字节: A1 85 04 00 00 0A 02 00
//                       ── ── ────── ────── ──────
//                       RT BR wValue wIndex wLength
```

> **换 XU Unit ID 只改一个地方**：wIndex 的高字节。比如 XU_ID 从 0x0A 换到 0x07，wIndex 就从 `0x0A00` 变成 `0x0700`。

---

## 六、Transaction vs Control Transfer（事务 vs 控制传输）

这是一个容易混淆的概念。"事务"和"控制传输"是两层不同的东西：

```
USB 协议层级：

  Control Transfer（控制传输）= libusb_control_transfer() 一次调用
  │
  ├── SETUP 阶段 ─── 1 个 Transaction: SETUP Token → DATA0{8B} → Device ACK
  ├── DATA 阶段  ─── 1 个 Transaction: IN/OUT Token → DATA1{data} → ACK
  └── STATUS 阶段 ── 1 个 Transaction: 方向相反的 Token → DATA1{ZLP} → ACK

  一个 Transaction = 一次 Token + Data + Handshake 交换
```

**libusb_control_transfer() = 1 次完整的控制传输 = 2~3 个总线事务。**

以你刚才读协议版本为例：

```
调用: libusb_control_transfer(devh, 0xA1, 0x85, 0x0004, 0x0A00, buf, 2, 1000);

SETUP 包 8 字节: A1 85 04 00 00 0A 02 00

BUS 上实际发生:
  ┌─ 事务 1 (SETUP) ───────────────────────
  │ Host → SETUP Token (ADDR, EP0)
  │ Host → DATA0 {A1 85 04 00 00 0A 02 00}
  │ Host ← ACK
  ├─ 事务 2 (DATA) ────────────────────────
  │ Host → IN Token (ADDR, EP0)
  │ Host ← DATA1 {04 00}                  ← 2 字节参数长度
  │ Host → ACK
  ├─ 事务 3 (STATUS) ─────────────────────
  │ Host → OUT Token (ADDR, EP0)
  │ Host → DATA1 (ZLP, 0 字节)            ← 交易关账
  │ Host ← ACK
  └────────────────────────────────────────

Bus Hound 只显示一行: CTL A1 85 04 00 00 0A 02 00
                       IN  04 00
→ STATUS 阶段驱动层已合并，Bus Hound 不显示
```

**一句话总结**：`libusb_control_transfer` 一次调用 = 一次完整的控制传输 = Bus Hound 里的一行 `CTL` + 一行 `IN`/`OUT` = USB 总线上的 2~3 个事务。用户态代码只需要关心控制传输层，事务层由 USB 主控和 libusb 自动处理。

---

## 七、Interface 和 Endpoint 怎么区分

这两个概念容易混淆，关键是：**它们不是一个层面的东西**。

```
USB 设备
├── Configuration
│   ├── Interface 0: VideoControl（视频控制功能）
│   │   └── Endpoint 0x83 (IN, Interrupt)           ← 可选：中断端点，设备推送状态
│   │   └── Endpoint 0x00 (EP0)                      ← 隐含：所有 Interface 共用 EP0
│   └── Interface 1: VideoStreaming（视频流功能）
│       ├── Alternate 0: 零带宽（= 关流）
│       └── Alternate 1: 批量传输
│           └── Endpoint 0x81 (IN, Bulk)             ← 数据端点
│       └── Alternate 2: 等时传输
│           └── Endpoint 0x81 (IN, Isochronous)      ← 数据端点
```

**Interface = 功能分类，Endpoint = 数据管道。**

### 什么时候用 Interface（控制传输的目标）

发 XU 命令时，控制传输的接收者是 **Interface**：

```c
libusb_control_transfer(devh,
    0xA1,                       // bmRequestType D4-0 = 00001 → Interface
    0x85,                       // bRequest = GET_LEN
    0x0004,                     // wValue = CS_ID << 8
    0x0A00,                     // wIndex = (XU_ID<<8) | 接口号
    buf, 2, 1000);
```

- 走的是 **EP0**（控制端点，出厂自带，不声明）
- bmRequestType 里指定接收者是 **Interface**（D4-0=00001）
- wIndex 低字节指定是第几个 Interface

### 什么时候用 Endpoint（批量/中断传输）

读视频帧、读中断状态时，传输的目标是 **Endpoint**：

```c
// 批量传输读视频帧 — 不需要控制传输那套 SETUP 包
libusb_bulk_transfer(devh,
    0x81,                       // 端点地址（bit7=IN, EndpointID=1）
    buf, frame_size, &recv_len, 5000);

// 中断传输读状态 — 也不走控制传输
libusb_interrupt_transfer(devh,
    0x83,                       // 中断端点地址
    status_buf, 16, &recv_len, 1000);
```

- 走的是 **具体端点**（0x81 = EndpointID 1, IN）
- 没有 SETUP 包，没有 wValue/wIndex/wLength
- 纯粹的数据管道：发 Token → 收/发数据 → ACK

### 对比表

| | 控制传输 (EP0) | 批量传输 | 中断传输 |
|---|---|---|---|
| libusb 函数 | `control_transfer` | `bulk_transfer` | `interrupt_transfer` |
| 走哪个端点 | EP0 | VS 端点 (如 0x81) | VC 中断端点 (如 0x83) |
| 参数指定方式 | bmRequestType+wValue+wIndex | 端点地址 | 端点地址 |
| 有 SETUP 包？ | 有（8 字节） | 无 | 无 |
| 做什么用 | XU 命令、开/关流 | 搬运视频帧 | 设备推送状态 |
| 接收者语义 | Device/Interface/Endpoint | — | — |

### 端点归属规则（用你的设备真实数据）

```
你的设备 (HIK 2bdf:0101) USB View 报告:

Used Endpoints: 3                          ← EP0 + EP 0x83 + EP 0x81
Number of open Pipes: 2                    ← 用户态看到 2 个数据管道

Pipe[0]: EndpointID=3  Type=Interrupt  ← IF=0 拥有的中断端点
Pipe[1]: EndpointID=1  Type=Bulk       ← IF=1 拥有的批量端点
```

```bash
sudo lsusb -v -d 2bdf:0101 输出:

Interface 0 (VC):
  bNumEndpoints: 1
  Endpoint 0x83 (IN, Interrupt)           ← 这个端点属于 Interface 0

Interface 1 (VS):
  Alternate 0:  bNumEndpoints = 1
    Endpoint 0x81 (IN, Bulk)              ← 这个端点属于 Interface 1
  Alternate 1~8: bNumEndpoints = 0        ← 等时模式下无额外端点声明
```

**核心规则**：

```
规则 1: 每个端点（EP0 除外）只属于一个 Interface
        EP 0x83 只属于 IF=0，IF=1 不能用它
        EP 0x81 只属于 IF=1，IF=0 不能用它

规则 2: EP0 是共用的——所有 Interface 的控制传输都走 EP0

规则 3: 同一个 Interface 的不同 Alternate Setting
        可以复用端点号（EndpointID），但不能同时存在
        因为只有 1 个 Alternate Setting 处于激活状态

规则 4: 两个 Interface 不能声明同一个 EndpointID
        IF=0 用了 EndpointID=3，IF=1 就不能再声明 EP 0x83
```

**图示**：

```
Configuration 1
│
├── Interface 0 (VC) ─ 当前激活 Alternate 0
│   ├── EP0   ← 共用（控制传输）
│   └── EP83  ← 私有（中断传输，收设备状态）
│
├── Interface 1 (VS) ─ 当前激活 Alternate 1 (取流)
│   ├── EP0   ← 共用（同一个 EP0）
│   └── EP81  ← 私有（批量传输，读视频帧）
│
│   Interface 1 的其他 Alternate Settings:
│   ├── Alt 0 (零带宽):  无数据端点 → 关流用
│   ├── Alt 1 (Bulk):    EP81 批量
│   └── Alt 2~8 (Isoch): EP81 等时（复用同一个 EndpointID）
│                          └── Alt 不同 = 同端点号但传输模式变了
│
└── EP0 不属于任何 Interface — 设备级资源，所有 Interface 都用它
```

### 一句话

**控制传输 = 发命令（"请把分辨率调到 640x480"），走 EP0。**
**批量传输 = 搬数据（"把这一帧像素数据传过来"），走数据端点。**
**两条通道互不阻塞——流开着的时候你照样可以用 EP0 调参数。**
**端点有主——IF=0 的端点 IF=1 不能碰，反之亦然。**

---

## 八、标准 UVC 取流完整流程

和 XU 控制的区别：XS 命令的 wIndex **不带 Unit ID**，视频流不需要 XU 那套三阶段协议。

### 两个 wIndex 体系对比

```
VideoControl (XU):     wIndex = (XU Unit ID << 8) | VC_IF
                          例: (0x0A << 8) | 0 = 0x0A00

VideoStreaming:        wIndex = VS_IF  （没有 Unit ID！）
                          例: 0x00 或 0x01
```

### 取流步骤

```
┌─ 阶段 1：协商参数 ──────────────────────（控制传输，EP0，wIndex=VS_IF）
│
│ ① Probe SET_CUR:  Host 提出想要的参数（格式/分辨率/帧率）
│    CTL  21 01  01 00  00 00  1A 00      ← wValue=0x0001(Probe), wIndex=VS_IF
│    OUT  01 00 80 02 E0 01 00 00 ...26B  ← 26 字节 Probe 结构体
│
│ ② Probe GET_CUR:  读回设备实际接受的参数
│    CTL  A1 81  01 00  00 00  1A 00      ← 可能修改了某些字段
│    IN   01 00 80 02 E0 01 0F 00 ...26B
│                        ↑dwMaxVideoFrameBufSize 等
│
│ ③ Commit SET_CUR: 锁定参数
│    CTL  21 01  01 00  00 00  1A 00      ← wValue=0x0001, wIndex=VS_IF
│    OUT  ...（跟②读回的值一样）
│
├─ 阶段 2：开启流 ────────────────────────（控制传输，EP0，bmRT=Standard）
│
│ ④ SET_INTERFACE: 切换到非 0 的 alternate setting
│    CTL  01 0B  01 00  01 00  00 00      ← bmRT=0x01(Standard,不是Class!)
│                                            bReq=0x0B(SET_INTERFACE)
│                                            wValue=altsetting, wIndex=VS_IF
│    (无数据)
│
├─ 阶段 3：读视频数据 ────────────────────（批量传输，EP 0x81）
│
│ ⑤ 循环读帧:
│    libusb_bulk_transfer(devh, 0x81, buf, buf_size, &recv_len, timeout);
│    → 每帧带帧头（magic + 长度 + 时间戳 + payload）
│
└─ 关闭流:
    SET_INTERFACE → Alternate 0（零带宽，关流）
```

### Probe 结构体 26 字节核心字段

```c
// UVC 1.1 Probe 结构体，小端
struct uvc_probe {
    uint16_t bmHint;              // offset 0:  哪些字段 Host 在意
    uint8_t  bFormatIndex;        // offset 2:  格式号（YUYV=1, MJPEG=2, H264=3）
    uint8_t  bFrameIndex;         // offset 3:  帧描述符索引号（分辨率+帧率组合）
    uint32_t dwFrameInterval;     // offset 4:  帧间隔（100ns 单位）
    uint16_t wKeyFrameRate;       // offset 8:  关键帧率
    uint16_t wPFrameRate;         // offset 10: P 帧率
    uint16_t wCompQuality;        // offset 12: 压缩质量（1~10000）
    uint16_t wCompWindowSize;     // offset 14: 压缩窗口大小
    uint16_t wDelay;              // offset 16: 内部延迟（ms）
    uint32_t dwMaxVideoFrameSize; // offset 18: 最大帧缓冲（重要！从这里拿 buffer 大小）
    uint32_t dwMaxPayloadTransferSize; // offset 22: 单次传输最大载荷
    // ... 后有 bmHint 之外的更多字段
};
```

**流开后，dwMaxVideoFrameSize 是你的 malloc 参考值。**

### VS 端点确认

```bash
sudo lsusb -v -d 2bdf:0101 2>&1 | grep -A 5 "bInterfaceNumber.*1\|Bulk\|Isochronous"
```

VS 接口（通常是 IF=1）的 Alternate 1+ 下面会声明批量或等时端点，`bEndpointAddress=0x81` 就是数据端点地址。

### SETUP 包三对比

```c
/* VideoControl XU:     */ wIndex = (XU_ID << 8) | VC_IF;   // 0x0A00
/* VideoStreaming:      */ wIndex = VS_IF;                   // 0x0000
/* SET_INTERFACE 开流:  */ bmRT = 0x01(Standard), bReq = 0x0B, wValue = alt
```

### 取流 + XU 同时工作

```
EP0 (控制传输)        →  发 XU 命令（调伪彩/云台） + 开流/关流
EP 0x81 (批量传输)    →  读视频帧
EP 0x83 (中断传输)    →  收设备状态通知（可选）

三条通道互不阻塞，可以同时工作。
```

> 参考：`HIKVISION_TM76_libusb_3.c` — 先用 VC 接口发 XU 设码流类型，再 claim VS 接口读帧，最后释放时先还 VS 再还 VC。

---

## 九、新设备参数检查清单

拿到一台新 UVC 摄像头，按这个清单走：

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU Unit ID)
□                                       bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 IF 填对              → SETUP wIndex 高/低字节
□ 用 CS_ID=0x04 GET_LEN 试通         → 验证通道 + 拿到协议版本
□ 看 bmControls 位图                 → 了解支持哪些 CS_ID
□ 选一个已知 CS_ID 走三阶段          → FUNC_SWITCH → GET_LEN → GET_CUR
```

---

## 十、和已有代码的对应

| 代码文件 | 作用 |
|---------|------|
| `xu_minimal_get.c` | 最简示例，直接读 CS_ID=0x04（无 SubFunc） |
| `xu_interactive.c` | 交互式工具，手动选 CS_ID/SubFunc，每步展示 SETUP 包 |
| `uvc_xu_subfunc_framework.c` | 完整封装库，三阶段流程 + 错误码处理 |
| `HIKVISION_TM76_libusb_3.c` | 海康 TM76 完整参考，含伪彩/码流/视频流 |

> 新设备调试：先用 `xu_interactive` 探索 → 搞清楚 CS_ID/SubFunc 定义 → 写进 `xu_minimal_get` 验证 → 最终集成到自己的业务代码。

---

## ★ 九、码流类型切换：为什么、什么时候、怎么切

> 本章是 `uvc_stream_viewer.cpp` 开发过程中踩坑的总结——热成像摄像头不是普通 webcam，**数据内容**和**传输格式**是两层独立控制。

### 9.1 热成像摄像头的数据分层模型

```
┌──────────────────────────────────────────────────────────────┐
│                      热成像摄像头                              │
│                                                              │
│  探测器（FPA）                                                │
│    ↓                                                         │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              原始数据（Raw/NUC）                       │    │
│  │   每个像素 = 14~16bit 温度值（非可见光！）               │    │
│  │   分辨率通常 256×192 或 640×512                         │    │
│  └──────────┬───────────────────────────────────────────┘    │
│             │                                                 │
│    ┌────────┴────────┐                                        │
│    ↓                 ↓                                        │
│  ┌──────────┐  ┌──────────────┐                               │
│  │ 测温矩阵  │  │ 伪彩映射     │                               │
│  │ 16bit×   │  │ 温度→RGB/YUV │                               │
│  │ W×H      │  │ （调色板）    │                               │
│  └────┬─────┘  └──────┬───────┘                               │
│       │               │                                       │
│       └───┬───────────┘                                       │
│           ↓                                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │          ★ 码流类型多路复用器（XU CS_ID=0x03）★        │    │
│  │                                                      │    │
│  │  类型 2:  全屏测温矩阵（纯温度数据，16bit float）       │    │
│  │  类型 3:  实时裸数据（NUC 校正前的原始探测器输出）      │    │
│  │  类型 6:  YUV 实时流 + 测温头（画面混温度采样点）      │    │
│  │  类型 8:  全屏测温数据 + YUV 实时流（两套数据拼接）     │    │
│  │  ★ 类型 10: 仅 YUV 实时流（无测温头，纯画面）★         │    │
│  │  类型 9:  实时裸数据 + YUV                             │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         ↓                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              UVC 传输层（Probe/Commit/ISOC）           │    │
│  │   管"怎么传"——分辨率、帧率、YUYV/MJPEG 编码            │    │
│  └──────────────────────────────────────────────────────┘    │
│                         ↓                                     │
│                   USB 总线 → 主机                              │
└──────────────────────────────────────────────────────────────┘
```

**关键理解**：摄像头探测器只有一个，但不同应用场景需要不同类型的数据：

| 应用场景 | 需要的码流类型 | 说明 |
|---------|--------------|------|
| 看热成像画面 | 类型 10（YUV_ONLY） | 纯 YUV 画面，无温度数据 |
| 工业测温（要温度值） | 类型 2（TEMP_FULL） | 全屏 16bit 温度矩阵，自己算温度 |
| 画面+测温点叠加 | 类型 6（YUV_HEADER） | YUV 画面里带测温头，可以画测温光标 |
| 自己做算法（原始数据） | 类型 3（NUC） | 未经伪彩映射的探测器原始输出 |

### 9.2 为什么需要 XU 切换码流类型

标准 UVC（Probe/Commit/SET_INTERFACE）只管**传输格式**：

```
UVC 管的事：                    UVC 不管的事：
  分辨率 (120x160/640x360)      数据内容（纯画面 vs 画面+温度）
  帧率 (25fps/30fps)            数据排列（YUV 开头 vs 温度矩阵开头）
  编码格式 (YUYV/MJPEG)         帧头结构（纯UVC头 vs 自定义测温头）
  带宽分配 (dwMaxPayloadSize)
```

**类比**：UVC 是快递公司（管包裹大小、送达速度），XU 是"包裹里装什么"——你必须在寄出之前告诉厂家。如果不发 XU 切换命令，摄像头就按默认类型（通常是类型 8：测温+YUV 混合）输出。主机收到混合数据后，解码器（libuvc/OpenCV）按纯 YUYV 去解析，看到的就是花屏。

**★ 另一个坑：YUYV vs MJPEG 描述符欺诈**

此设备（2bdf:0101）还有一个额外问题：UVC 描述符声称 UncompressedFormat 送的是 YUY2（YUYV），但**实际帧数据以 `FF D8`（JPEG SOI 标记）开头**。设备通过 YUYV 管道送 MJPEG 数据。

```
UVC 描述符          →  libuvc 信了          →  实际帧数据
UncompressedFormat      按 YUYV 协商成功       FF D8 FF E0 ...（JPEG！）
bits per pixel: 16      fmt=YUYV 标记          bytes=~10000（压缩后）
GUID: YUY2              期望 38400 字节         不是 38400 字节
```

**教训**：不能完全信任 UVC 描述符。在回调里检测 `data[0]==0xFF && data[1]==0xD8`，如果是 JPEG 就强制走 `cv::imdecode`。

### 9.3 XU 切换 vs UVC 取流：先后顺序（★重点）

```
正确顺序：先配置内容，再开传输

  ① uvc_open              → 拿到设备句柄
  ② XU: 切换码流类型       → 告诉摄像头"我要什么内容"   ← 先！
  ③ UVC: Probe/Commit     → 协商传输参数
  ④ uvc_start_streaming   → 打开管道，开始收帧           ← 后！

类比：先调好水龙头旋钮（选纯净水），再拧开水龙头。
```

**★ 为什么不能先开流再发 XU？**

```
错误顺序：
  ① uvc_open
  ② UVC: 开流 → 管道已建立，帧数据持续传输中
  ③ XU: 切换码流 → 摄像头收到命令，内部切换数据源
     ↑
     切换瞬间 UVC 管道还在跑！
     新数据格式变了（YUV变成测温矩阵），libuvc 仍按老的解码 → 花屏/崩溃
```

**★ 取流中能不能发 XU？能，但要看命令类型：**

```
切换码流类型 (CS_ID=0x03 SubFunc=0x05)：
  → 会导致管道中数据格式突变 → ★ 必须先停流再切换，切换完再开流

切换伪彩 (CS_ID=0x02 SubFunc=0x05, palette 参数)：
  → 只改颜色映射表，YUV 数据格式不变 → 取流中可以热切换，立即生效

读取协议版本 (CS_ID=0x04)：
  → 纯读操作，不影响管道 → 随时可以读

读取错误码 (CS_ID=0x06)：
  → 纯读操作 → 随时可以读
```

**★ 设备收到 XU 命令后多久生效？**

```
CS_ID=0x03 (码流类型) → SET_CUR 完成后 ∩ 下一帧开始生效
                         实际设备可能隔 1~3 帧才稳定
                         建议：发完 XU → usleep(200ms) → 再开流

CS_ID=0x02 (伪彩切换) → SET_CUR 完成后隔约 100~200ms 生效
                         取流中画面颜色会跳变（这是正常的）
```

**★ 标准取流+私有切换的建议流程：**

```
步骤                    传输介质           说明
────────────────────    ─────────         ───────────────────
① uvc_open              libuvc            拿到设备
② XU: 码流→YUV_ONLY     libusb→EP0        控制传输，不走UVC管道
   (usleep 200ms)                         等设备内部切换完成
③ uvc_stream_ctrl       libuvc            协商分辨率/帧率
④ uvc_start_streaming   libuvc            开管道（Probe+Commit+SET_INTERFACE）
⑤ 帧回调                libuvc            解码+显示
```

### 9.4 测温头是什么（类型 6 的结构）

类型 6（YUV_HEADER）：在标准 YUV 帧的**末尾**或**每隔 N 行**嵌入测温数据：

```
类型 10（纯 YUV，你要的）：           类型 6（YUV + 测温头）：
┌────────────────────┐               ┌────────────────────┐
│                    │               │                    │
│   YUV 图像数据      │               │   YUV 图像数据      │
│   120×160×2        │               │   120×160×2        │
│   = 38400 字节      │               │   ≈ 38400 字节     │
│                    │               │                    │
│   ← 帧尾            │               ├────────────────────┤
│                    │               │ ★ 测温头数据 ★      │
│                    │               │   温度值 + 坐标      │
│                    │               │   ～200~500 字节    │
└────────────────────┘               └────────────────────┘

解码器按纯 YUV 读：               解码器按纯 YUV 读：
  一行一行正常解析 ✓                读到测温头数据 →
                                    像素错位 → 花屏 ✗
```

测温头通常包含：
- 中心点温度（2 字节）
- 最高温/最低温 + 坐标（各 4 字节）
- ROI 区域平均温度（自定义）

如果你只是看画面（不需要测温功能），用类型 10 就够了——省带宽、不需要自己解析测温头、标准 UVC 播放器直接能放。

### 9.5 实战踩坑记录（uvc_stream_viewer 开发）

| # | 症状 | 根因 | 修复 |
|---|------|------|------|
| 1 | SDL2 播放数秒后 segfault | 回调线程和主线程同时访问帧缓冲区，无锁 | 换 OpenCV + `pthread_mutex_t` |
| 2 | 花屏（雪花状噪点） | 默认码流含测温数据混在 YUV 里 | XU 命令切到类型 10 (YUV_ONLY) |
| 3 | 花屏仍在，帧只有 10000 字节 | 描述符说 YUYV 实际送 MJPEG | 检测 `FF D8` 头，强制 `cv::imdecode` |
| 4 | XU 命令不执行 | `libusb_control_transfer` 漏了 `bRequest` 参数 | 补全 8 参数 (bmRT + bReq + wVal + wIdx + data + len + timeout) |
| 5 | XU 返回 `LIBUSB_ERROR_IO` | XU 在 `uvc_open` 之后发，设备状态不一致 | XU 移到 `uvc_open` 之前，复用 detach 时的 libusb 句柄 |
| 6 | `cv::cvtColor(YUV2BGR)` 花屏 | OpenCV 的 YUYV 字节序与设备不匹配 | 统一用 libuvc 的 `uvc_any2rgb` + `cv::cvtColor(RGB2BGR)` |
| 7 | `frame->data[0]` 编译报错 | `uvc_frame_t::data` 是 `void*`，不能下标 | 先转 `(const uint8_t *)frame->data` |

### 9.6 代码参考

| 文件 | 关键代码 |
|------|---------|
| `xu_interactive.c` | `read_cs_direct()` / `read_cs_with_subfunc()` — XU 三阶段交互 |
| `uvc_stream_viewer.cpp` | `frame_cb()` — JPEG 头检测 + MJPEG/YUYV 双路径解码 |
| `uvc_stream_viewer.cpp` | `main()` 2.5 段 — 在 `uvc_open` 之前发 XU 切换码流 |
| `HIKVISION_TM76_libusb_3.c` | `STREAM_TYPE_*` 定义 — 码流类型的完整枚举 |
