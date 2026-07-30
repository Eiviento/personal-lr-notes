# Phase 3: USB 描述符体系 — 逐字节解剖

## 3.1 描述符层级关系

### 全貌

USB 设备靠一套"元数据"向 Host 自报家门——这套元数据就是**描述符（Descriptor）**。所有描述符组成一棵严格的树：

```
Device Descriptor（设备级，1 个）
  │  制造商是谁、产品是什么、USB 版本多少
  │
  └─ Configuration Descriptor（配置级，≥1 个）
        │  耗电多少、有几个接口、自供电还是总线供电
        │
        └─ Interface Descriptor（接口级，≥1 个）
              │  这是什么设备类(HID/CDC/UVC)、几个端点
              │
              └─ Endpoint Descriptor（端点级，0~N 个）
                    │  端点号、方向、传输类型、最大包大小、轮询间隔
                    │
                    └─ (可选) 类专用描述符
                          HID Descriptor / CDC Functional Descriptors / UVC VC&VS Descriptors
```

### 树的结构约束

这是一种 **1 → 1+ → 1+ → 1+** 的严格层次：

| 层级 | 数量 | 说明 |
|------|------|------|
| Device | **1 个** | 每个设备只有一个 Device Descriptor |
| Configuration | **≥1 个** | 大多数设备只有一个配置。少数设备有多个（如高功耗配置 vs 低功耗配置） |
| Interface | **≥1 个** | 每个配置下至少一个接口。复合设备（如键盘+触摸板）有多个接口 |
| Endpoint | **0~N 个** | 接口下可以有 0 到多个端点（至少 EP0，但 EP0 不属于任何接口） |

### 每个描述符的前 2 字节铁律

**不管你是什么描述符，前两个字节的语义是固定的：**

```
Byte 0: bLength        — 本描述符的长度（字节数）
Byte 1: bDescriptorType — 描述符类型码（1 字节枚举值）
```

Host 拿到描述符链后，先读 `bLength` 知道多大，再读 `bDescriptorType` 知道是什么类型，然后决定怎么解析剩余的字节。这就像解析 TLV（Type-Length-Value）——只是 USB 把 L 放前面，变成 Length-Type-Value。

常见类型码速查：

| bDescriptorType | 名称 |
|:---:|------|
| 0x01 | Device Descriptor |
| 0x02 | Configuration Descriptor |
| 0x03 | String Descriptor |
| 0x04 | Interface Descriptor |
| 0x05 | Endpoint Descriptor |
| 0x06 | Device Qualifier Descriptor |
| 0x07 | Other Speed Configuration |
| 0x0F | BOS Descriptor |

### 描述符链的内存布局

Host 在枚举阶段用 `Get_Descriptor(Configuration)` 请求读回的**不是单个描述符**，而是一条**描述符链**——把 Configuration + Interface + Endpoint + 类专用描述符全部串联成一个连续数据块：

```
┌─────────────────────────────────────────────────────┐
│ Config Descriptor (9B)                              │  ← wTotalLength 告诉总长度
├─────────────────────────────────────────────────────┤
│ Interface Descriptor (9B)                           │
├─────────────────────────────────────────────────────┤
│   Endpoint Descriptor (7B)                          │
│   Endpoint Descriptor (7B)                          │
├─────────────────────────────────────────────────────┤
│   CDC Header Descriptor (5B)     ← 类专用，夹在中间 │
│   CDC ACM Descriptor (4B)                           │
│   CDC Union Descriptor (5B)                         │
│   CDC Call Mgmt Descriptor (5B)                     │
├─────────────────────────────────────────────────────┤
│ Interface Descriptor (9B)    ← 第二个接口           │
│   Endpoint Descriptor (7B)                          │
│   Endpoint Descriptor (7B)                          │
└─────────────────────────────────────────────────────┘
```

Host 拿到整个链后，从头开始，遇到一个描述符读 `bLength`，跳过 `bLength` 字节就是下一个描述符，一直读到总长度（`wTotalLength`）结束。

### MQTT 类比

| USB 描述符 | MQTT 类比 |
|------------|-----------|
| Device Descriptor | 设备上线时的 CONNECT 报文（Client ID、协议版本、KeepAlive） |
| Configuration Descriptor | 设备宣告自己有哪些 Topic 权限（订阅/发布模式） |
| Interface Descriptor | 每个 Topic 的 QoS 定义（消息格式、最大长度） |
| Endpoint Descriptor | TCP 连接的参数（接收窗口大小、超时时间） |
| `bLength + bDescriptorType` 前 2 字节铁律 | MQTT Fixed Header 的第一个字节（Message Type + Flags），决定整体怎么解读 |

### 关键理解

描述符不是 Host 下发给设备的"配置命令"——Host 只是**读取**设备的描述符。设备在固件里静态定义好，Host 在枚举阶段一句一句读走。描述符是设备的**自述文件**，Host 读完后按照它说的方式跟设备通信。

---

## 补充问答：端点和接口的区别

### 类比

一个 U 盘：

```
Interface 0: Mass Storage（"我是存文件的"）
  ├── Endpoint 1 IN   ← 批量 IN，Host 从这里读数据
  └── Endpoint 2 OUT  ← 批量 OUT，Host 往这里写数据
```

端点是数据进出的大门，接口告诉 Host"这些大门组合在一起对应什么功能"。

### 对比

| 维度 | Endpoint（端点）| Interface（接口）|
|------|-----------------|-------------------|
| **本质** | 硬件 FIFO 缓冲区 | 逻辑功能分组 |
| **数量** | 每设备 0~16 个（不含 EP0）| 每配置 1~N 个 |
| **描述符** | Endpoint Descriptor（7 字节）| Interface Descriptor（9 字节）|
| **包含关系** | 属于某个 Interface | 包含多个 Endpoint |
| **标识** | `bEndpointAddress`（bit7=方向 + bit3~0=端点号）| `bInterfaceNumber`（0, 1, 2...）|
| **对应概念** | 管道 | 功能模块 |

### 复合设备示例

一个 USB 键盘+触摸板的设备：

```
Interface 0: 键盘（bInterfaceClass=HID）
  └── Endpoint 1 IN    ← 按键数据从这里上报

Interface 1: 触摸板（bInterfaceClass=HID）
  └── Endpoint 2 IN    ← 触摸坐标从这里上报
```

同一个物理设备，两个独立功能，各用各的端点。Host 把 Interface 0 交给键盘驱动、Interface 1 交给鼠标驱动——互不干扰。

### CDC 的例子

```
Interface 0: 通信控制（bInterfaceClass=CDC）
  └── Endpoint 2 IN    ← 中断传输，SerialState 通知（10 字节）

Interface 1: 数据（bInterfaceClass=CDC Data）
  ├── Endpoint 1 OUT   ← 批量 OUT，Host→设备 发串口数据
  └── Endpoint 1 IN    ← 批量 IN，设备→Host 收串口数据
```

两个接口配合完成一个"虚拟串口"——但它们在逻辑上是分开的，驱动栈也是分开加载的。

**一句话：Interface 回答"我能干什么"，Endpoint 回答"数据从哪走"。**

---

## 补充问答：怎么知道这个接口能干什么？

Interface Descriptor 用三个字段精确回答：

```
Interface Descriptor 中：
  bInterfaceClass      (1 byte) — "大类是什么"
  bInterfaceSubClass   (1 byte) — "大类下的哪个子类"
  bInterfaceProtocol   (1 byte) — "用什么协议变体"
```

### 三级分类体系

三者共同定位到驱动。就像快递地址：省（Class）→ 市（SubClass）→ 区（Protocol）：

| 设备 | bInterfaceClass | bInterfaceSubClass | bInterfaceProtocol |
|------|:---:|:---:|:---:|
| USB 鼠标 | 0x03 (HID) | 0x01 (Boot Interface) | 0x02 (Mouse) |
| USB 键盘 | 0x03 (HID) | 0x01 (Boot Interface) | 0x01 (Keyboard) |
| CDC 虚拟串口 | 0x02 (CDC) | 0x02 (ACM) | 0x01 (AT Commands) |
| U 盘 | 0x08 (Mass Storage) | 0x06 (SCSI) | 0x50 (Bulk-Only) |
| UVC 摄像头 | 0x0E (Video) | 0x01 (Video Control) | 0x00 |
| 音频耳机 | 0x01 (Audio) | 0x01 (Audio Control) | 0x00 |

### Host 端的加载链

```
bInterfaceClass=0x03 (HID)
  → 系统知道：加载 HID 类驱动 (hidusb.sys)
    → bInterfaceSubClass=0x01 (Boot) + bInterfaceProtocol=0x02 (Mouse)
      → 系统知道：创建鼠标设备节点，挂到输入子系统
```

这就是为什么 U 盘插上自动出现盘符、鼠标插上自动能动——**不需要你安装驱动**。三个字段就决定了一切。操作系统内置了这些标准类的驱动，匹配上就自动接管。

---

## 补充问答：端点能否被多个接口共享？UVC 摄像头的接口描述符长什么样？

### 端点独享原则

**不能。** 每个端点只属于一个接口，是独享的。Endpoint Descriptor 嵌套在 Interface Descriptor 之后——物理上就是谁的链里出现就是谁的。如果两个接口的链里都出现了 EP1 IN，Host 收到的描述符就是自相矛盾的，驱动无法判断"EP1 数据到底交给键盘驱动还是鼠标驱动"。**USB 规范明确禁止。**

唯一的例外是 EP0——它不属于任何接口，全局公有，靠 SETUP 包的 `bRequest` 区分上层意图。

### UVC 摄像头的接口描述符实例

一个典型的 UVC 摄像头（如罗技 C920）的接口布局：

```
Configuration Descriptor
│  wTotalLength = 全部链长
│  bNumInterfaces = 3~4
│
├── Interface #0（Video Control — VC）
│     bInterfaceNumber  = 0
│     bAlternateSetting = 0   ← VC 只有一个，无备选
│     bNumEndpoints     = 0 或 1
│     bInterfaceClass   = 0x0E (Video)
│     bInterfaceSubClass= 0x01 (Video Control)
│     bInterfaceProtocol= 0x00
│     │
│     ├── VC Header Descriptor         (12B)
│     ├── Input Terminal Descriptor     (8B)  ← 摄像头传感器
│     ├── Processing Unit Descriptor    (9B)  ← 亮度/对比度/白平衡
│     ├── Output Terminal Descriptor    (9B)  ← 输出到Host
│     └── (可选) Endpoint IN (中断)      ← 硬件状态通知
│
├── Interface #1（Video Streaming — VS，零带宽）
│     bInterfaceNumber  = 1
│     bAlternateSetting = 0   ← 默认激活这个，零带宽
│     bNumEndpoints     = 0   ← 没有等时端点，不占带宽
│     bInterfaceClass   = 0x0E (Video)
│     bInterfaceSubClass= 0x02 (Video Streaming)
│     bInterfaceProtocol= 0x00
│     │
│     └── VS Input Header Descriptor    (13B)
│          （只声明格式，不分配端点）
│
├── Interface #1 Alternate 1（VS — 640×480 MJPG）
│     bInterfaceNumber  = 1   ← 还是1号接口！
│     bAlternateSetting = 1
│     bNumEndpoints     = 1   ← 现在有端点了
│     bInterfaceClass   = 0x0E
│     bInterfaceSubClass= 0x02
│     │
│     ├── VS Input Header Descriptor
│     ├── Format Descriptor (MJPG)
│     ├── Frame Descriptor (640×480, 30fps)
│     ├── Frame Descriptor (640×480, 15fps)
│     │   ...
│     └── Endpoint IN (等时)
│           bEndpointAddress = 0x82 (EP2 IN)
│           bmAttributes      = 0x05 (等时, Async)
│           wMaxPacketSize    = 0x0300 (768B/微帧, HS)
│           bInterval         = 1 (每微帧)
│
└── Interface #1 Alternate 2（VS — 1280×720 MJPG）
      bInterfaceNumber  = 1   ← 还是1号接口
      bAlternateSetting = 2
      bNumEndpoints     = 1
      ...（不同分辨率，端点参数可能不同）
```

### Alternate Setting 的妙用

Interface #1 出现了 N 次——不是 N 个不同接口，而是**同一个接口的 N 种形态**。Host 同一时刻只激活其中一种：

```
摄像头关闭时：
  Interface #1, Alternate 0 激活 → 零带宽，0 个端点

用户打开 720p：
  Host 发 Set_Interface(#1, Alt=2) → Alternate 0 停掉，Alternate 2 激活
  → 等时端点 EP2 IN 开始传输视频帧

用户切换到 480p：
  Host 发 Set_Interface(#1, Alt=1) → 先切回 Alt 0（释放带宽）
  → 再切到 Alt 1
```

**为什么不用多个独立接口？** 因为 Alternate Setting 让 Host 知道"这些是互斥的"。切换 Alt Setting 时，Host 自动释放旧 Alt 的端点资源、申请新 Alt 的带宽。如果用多个独立接口，Host 会尝试同时激活它们——等时带宽冲突，Set_Configuration 直接失败。

---

## 3.2 ⛁ Device Descriptor — 18 字节逐位解剖

这是 Host 读到的**第一个描述符**。设备在枚举阶段被要求交出 18 字节的"身份证"。

### 逐字节拆解

```
Offset  Size  Field              示例值（U盘）    含义
──────────────────────────────────────────────────────────────────
  0      1     bLength            0x12 (18)        "我18字节长"
  1      1     bDescriptorType    0x01             "我是Device Descriptor"
  2-3    2     bcdUSB             0x0200           "我支持USB 2.0"
  4      1     bDeviceClass       0x00             "具体分类看Interface层"
  5      1     bDeviceSubClass    0x00
  6      1     bDeviceProtocol    0x00
  7      1     bMaxPacketSize0    0x40 (64)        "EP0最大包64字节"
  8-9    2     idVendor           0x0781           "SanDisk制造"
 10-11   2     idProduct          0x5591           "型号是Ultra Fit"
 12-13   2     bcdDevice          0x0100           "固件版本1.00"
 14      1     iManufacturer      0x01             "制造商名字→String#1"
 15      1     iProduct           0x02             "产品名字→String#2"
 16      1     iSerialNumber      0x03             "序列号→String#3"
 17      1     bNumConfigurations 0x01             "只有1个配置"
```

### 逐字段精讲

**Byte 0 — bLength（0x12）**

永远是 18。如果你读到的是别的值，要么固件写错了，要么 Host 只读了前 8 字节（枚举第一次 Get_Descriptor 时故意只读 8 字节，后面会讲）。

**Byte 1 — bDescriptorType（0x01）**

USB 规范定义的枚举值。Device = 0x01，Configuration = 0x02，以此类推。

**Byte 2-3 — bcdUSB（如 0x0200）**

BCD 码，不是简单的十六进制。`0x0200` = 十进制 2.00 = USB 2.0。`0x0110` = 1.10 = USB 1.1。

**Byte 4-6 — bDeviceClass / bDeviceSubClass / bDeviceProtocol**

这三兄弟跟 Interface 那三个字段长得一样，但位置不同——这是**设备级**分类。关键是：

| 值 | 含义 |
|----|------|
| **0x00** | 分类权下放到 Interface 层——**最常见**（复合设备必须用 0x00）|
| 0x02 | 整个设备都是 CDC 通信设备 |
| 0x03 | 整个设备都是 HID |
| 0xEF | 杂项（Miscellaneous）|

绝大多数设备都写 0x00，把真正的分类信息放在 Interface Descriptor 里。因为复合设备（一个设备多个功能）没法在设备级用一个 Class 概括。

**Byte 7 — bMaxPacketSize0**

EP0 的最大包大小。FS 设备合法值：8、16、32、**64**。HS 设备只能写 64。LS 设备只能写 8。

这个值极其关键——Host 在枚举刚开始时还不知道设备的速度，看到这个值就知道后续怎么拆包了。

**Byte 8-11 — idVendor + idProduct**

USB 世界的"身份证号"。VID 由 USB-IF 分配（花钱买），PID 由厂商自己定。操作系统用 VID+PID 查驱动匹配表：

```
VID=0x0781, PID=0x5591 → 查inf文件 → 匹配到USBSTOR.SYS → 加载大容量存储驱动
```

这就是为什么插入 U 盘不需要装驱动——系统内置了 VID/PID 到驱动的映射表。

**Byte 12-13 — bcdDevice**

设备固件版本号，BCD 编码。`0x0100` = 版本 1.00。厂商自己定，Host 一般不用，但 lsusb 和 Wireshark 会显示。

**Byte 14-16 — iManufacturer / iProduct / iSerialNumber**

这三个**不是字符串本身**，而是索引号：

```
iManufacturer=0x01 → "去看 String Descriptor #1，那是制造商名字"
iProduct=0x02      → "去看 String Descriptor #2，那是产品名字"
iSerialNumber=0x00 → "我没有序列号"（0x00 表示空）
```

实际字符串是 UNICODE 编码，存在独立的 String Descriptor 里。Host 要单独发请求去读。

**Byte 17 — bNumConfigurations**

有几个配置。绝大多数设备写 **0x01**（一个配置就够了）。

### 完整 HEX dump 示例

```
一个 SanDisk U 盘的 18 字节 Device Descriptor：

Offset: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11
  Hex: 12 01 00 02 00 00 00 40 81 07 91 55 00 01 01 02 03 01

逐字节对照：
  12       = bLength (18)
  01       = bDescriptorType (Device)
  00 02    = bcdUSB (2.0, LE: MSB在右→0x0200)
  00       = bDeviceClass (0→看Interface)
  00       = bDeviceSubClass
  00       = bDeviceProtocol
  40       = bMaxPacketSize0 (64)
  81 07    = idVendor (0x0781 = SanDisk, Little-Endian: 低字节在前)
  91 55    = idProduct (0x5591)
  00 01    = bcdDevice (1.00)
  01       = iManufacturer (String#1)
  02       = iProduct (String#2)
  03       = iSerialNumber (String#3)
  01       = bNumConfigurations (1)
```

### ⚠️ Little-Endian 陷阱

2 字节字段（bcdUSB / idVendor / idProduct / bcdDevice）在 USB 总线上是 **Little-Endian** 传输：

```
内存/描述符中:  81 07  →  实际值是 0x0781，不是 0x8107
LSB 先发、MSB 后发
```

---

## 3.3 bcdUSB 的 BCD 编码细节

### 什么是 BCD 码

BCD = Binary-Coded Decimal，用 **每个 nibble（4 bit）** 表示一个十进制数字（0~9）。禁止出现 A~F。

```
bcdUSB = 0xJJMN（16 bit = 4 nibble）
          ↑↑ ↑ ↑
          JJ = 主版本号（Major）
          M  = 次版本号（Minor）
          N  = 子次版本号（Sub-minor）
```

### 常见值对照

| bcdUSB 值 | 含义 | nibble 拆开 |
|:---------:|------|:-----------:|
| `0x0100` | USB 1.0 | JJ=01, M=0, N=0 |
| `0x0110` | USB 1.1 | JJ=01, M=1, N=0 |
| `0x0200` | USB 2.0 | JJ=02, M=0, N=0 |
| `0x0210` | USB 2.1（很少见） | JJ=02, M=1, N=0 |
| `0x0300` | USB 3.0 | JJ=03, M=0, N=0 |
| `0x0310` | USB 3.1 | JJ=03, M=1, N=0 |
| `0x0320` | USB 3.2 | JJ=03, M=2, N=0 |

### 最容易踩的坑

**坑 1：把 0x0110 当十进制 272**

```
0x0110 当成整数读 = 1×256 + 16 = 272 ❌ 毫无意义
正确解读: nibble 拆开 → 01.1.0 → USB 1.1 ✓
```

**坑 2：直接用十六进制比较**

```c
// 大部分人这样写，碰巧能工作：
if (desc->bcdUSB >= 0x0200) { /* 2.0 以上 */ }

// 正确的比较方式：
uint8_t major = (desc->bcdUSB >> 8) & 0xFF;  // 主版本
uint8_t minor = (desc->bcdUSB >> 4) & 0x0F;  // 次版本
uint8_t sub   =  desc->bcdUSB       & 0x0F;  // 子次版本
```

**坑 3：bcdUSB 和 bcdDevice 用同一种编码，但语义不同**

```
bcdUSB   = 描述符里的 USB 协议版本（USB-IF 定义，设备不能乱写）
bcdDevice = 固件版本（厂商随意定）
```

### BCD 编码在 USB 描述符中的分布

| 字段 | 位置 | BCD 格式 |
|------|------|----------|
| `bcdUSB` | Device Descriptor byte 2-3 | 协议版本 |
| `bcdDevice` | Device Descriptor byte 12-13 | 设备固件版本 |
| `bcdHID` | HID Descriptor | HID 协议版本（如 0x0111 = HID 1.11）|
| `bcdCDC` | CDC Header Descriptor | CDC 协议版本（如 0x0110 = CDC 1.10）|

---

## 3.4 ⛁ Configuration Descriptor — 9 字节逐位解析

Device Descriptor 说"我是谁"，Configuration Descriptor 说"我怎么运行"。

### 逐字节拆解

```
Offset  Size  Field              示例值            含义
──────────────────────────────────────────────────────────────────
  0      1     bLength            0x09 (9)          "我9字节长"
  1      1     bDescriptorType    0x02              "我是Configuration Descriptor"
  2-3    2     wTotalLength       0x002E (46)       "整个描述符链一共46字节"
  4      1     bNumInterfaces     0x02              "这个配置有2个接口"
  5      1     bConfigurationValue 0x01             "配置编号=1（Set_Configuration 时用）"
  6      1     iConfiguration     0x00              "没有配置名称字符串"
  7      1     bmAttributes       0x80              "总线供电、无Remote Wakeup"
  8      1     bMaxPower          0xFA (250)        "最多吃500mA电流"
```

### 逐字段精讲

**Byte 2-3 — wTotalLength**

**这个字段是整个描述符体系的关键枢纽。** 它不是 Configuration Descriptor 自身的长度，而是"从 Config 开始到整个描述符链结束"的总长度：

```
wTotalLength = Config(9) + Interface(9) + Endpoint(7) + Endpoint(7)
             + Interface(9) + Endpoint(7) + Endpoint(7)
             + 类专用描述符(...)
```

Host 枚举时先只读 Config 的 9 字节，看到 wTotalLength 后知道"还要再读多少"。

**Byte 7 — bmAttributes（位图，逐位解读）**

```
Bit  Layout
 D7     保留，必须写 1
 D6     0=总线供电(偷Host的电) / 1=自供电(自己有电源适配器)
 D5     0=不支持远程唤醒 / 1=支持Remote Wakeup
 D4-0   保留，写 0
```

常见组合：
- `0x80` = 1000 0000 — 总线供电、无远程唤醒（大多数设备）
- `0xC0` = 1100 0000 — 总线供电、有远程唤醒（键盘/鼠标）
- `0xA0` = 1010 0000 — 自供电、无远程唤醒

**Byte 8 — bMaxPower**

"我从 VBUS 上最多吃多少电"。单位是 **2mA**：

```
bMaxPower = 0xFA (250)  → 250 × 2mA = 500mA    ← USB 2.0 最大
bMaxPower = 0x32 (50)   → 50 × 2mA = 100mA     ← 普通键盘鼠标
bMaxPower = 0x00 (0)    → 0 × 2mA = 0mA        ← 自供电设备
```

**Host 会算账！** 如果 Hub 的剩余供电不够，Host 拒绝 `Set_Configuration`——设备就始终无法进入 Configured 状态。

---

## 3.5 ⛁ Interface Descriptor — 9 字节逐位解析

### 逐字节拆解

```
Offset  Size  Field                 示例值       含义
──────────────────────────────────────────────────────────────────
  0      1     bLength               0x09 (9)     "我9字节长"
  1      1     bDescriptorType       0x04         "我是Interface Descriptor"
  2      1     bInterfaceNumber      0x00         "我是第0号接口"
  3      1     bAlternateSetting     0x00         "我是默认配置（备选编号0）"
  4      1     bNumEndpoints         0x01         "我有1个端点（不含EP0）"
  5      1     bInterfaceClass       0x03         "HID类"
  6      1     bInterfaceSubClass    0x01         "Boot Interface子类"
  7      1     bInterfaceProtocol    0x02         "鼠标协议"
  8      1     iInterface            0x00         "无名"
```

### 逐字段精讲

**Byte 2 — bInterfaceNumber**

接口在配置内的编号，从 0 开始递增。这个编号跟驱动绑定直接相关：Host 用 `{bInterfaceClass, bInterfaceSubClass, bInterfaceProtocol}` 找到驱动后，通过 `bInterfaceNumber` 告诉驱动"你接管几号接口"。

**Byte 3 — bAlternateSetting**

一个接口可以有**多个备选配置**，用这个编号区分。最常见用途是 USB 摄像头：

```
Interface 1, Alternate 0: 无视频流（零带宽）
Interface 1, Alternate 1: 视频流 640×480@30fps
Interface 1, Alternate 2: 视频流 1280×720@15fps
Interface 1, Alternate 3: 视频流 1920×1080@5fps
```

枚举完成后，摄像头默认激活 Alternate 0（零带宽）。打开摄像头时 Host 切到 Alternate 1~3 之一；关闭时切回 Alternate 0 释放带宽。这就是 **Set_Interface** 请求干的活。

**Byte 4 — bNumEndpoints**

这个接口下面有几个端点，**不含 EP0**。EP0 属于设备级，不在任何接口的管辖范围。

**Byte 5-7 — 三级分类码**

```
bInterfaceClass → 系统决定用哪个大驱动框架
bInterfaceSubClass → 驱动框架下的哪个子类
bInterfaceProtocol → 子类下的哪个具体协议变体
```

### HEX 实例

```
一个 USB 鼠标的 Interface Descriptor：

Offset: 00 01 02 03 04 05 06 07 08
  Hex: 09 04 00 00 01 03 01 02 00

解读：
  09 = bLength (9)
  04 = bDescriptorType (Interface)
  00 = bInterfaceNumber (接口#0)
  00 = bAlternateSetting (默认)
  01 = bNumEndpoints (1个端点)
  03 = bInterfaceClass (HID)
  01 = bInterfaceSubClass (Boot Interface)
  02 = bInterfaceProtocol (Mouse)
  00 = iInterface (没有字符串名)
```

---

## 3.6 ⛁ Endpoint Descriptor — 7 字节逐位解析

描述符树的最底层。它回答：**数据从哪个门走、朝哪个方向、每次能搬多少字节、多久查一次这个门。**

### 逐字节拆解

```
Offset  Size  Field               示例值            含义
──────────────────────────────────────────────────────────────────
  0      1     bLength             0x07 (7)          "我7字节长"
  1      1     bDescriptorType     0x05              "我是Endpoint Descriptor"
  2      1     bEndpointAddress    0x82              "EP2, 方向=IN"
  3      1     bmAttributes        0x03              "中断传输"
  4-5    2     wMaxPacketSize      0x0008 (8)        "一次最多搬8字节"
  6      1     bInterval           0x0A (10)         "每10ms查一次"
```

### 逐字段精讲

**Byte 2 — bEndpointAddress（包含两个独立信息）**

```
Bit 7    : 方向 — 1=IN(Device→Host)  0=OUT(Host→Device)
Bit 6-4  : 保留，写 0
Bit 3-0  : 端点号 (0~15)
```

```
0x82 = 1000 0010
       ↑    ↑─── 端点号 = 2
       │──────── 方向 = IN (Device → Host)

0x01 = 0000 0001
       ↑    ↑─── 端点号 = 1
       │──────── 方向 = OUT (Host → Device)
```

**注意：** 描述符链中不会出现 EP0 的 Endpoint Descriptor。EP0 的 bMaxPacketSize 已经在 Device Descriptor 的 byte 7 中定义了。

**Byte 3 — bmAttributes（端点类型 + 等时同步模式）**

```
Bit 1-0: 传输类型
  00 = 控制
  01 = 等时
  10 = 批量
  11 = 中断

Bit 7-2: 保留（批量/中断）、或等时同步模式
```

对于等时端点（bit1-0=01），高两位有额外含义：

```
Bit 3-2: Synchronization Type
  00 = 无同步 (Async)
  01 = 异步 (Asynchronous)
  10 = 自适应 (Adaptive)
  11 = 同步 (Synchronous)

Bit 5-4: Usage Type
  00 = 数据端点
  01 = 反馈端点 (Feedback)
```

常见组合：
```
0x03 = 中断传输（HID 鼠标/键盘）
0x02 = 批量传输（U盘、CDC 数据）
0x05 = 等时传输, Async, Data Endpoint（UVC 视频流）
0x0D = 等时传输, Sync, Data Endpoint（USB 音频）
```

**Byte 4-5 — wMaxPacketSize**

端点一次事务中能收/发的最大数据字节数。Little-Endian。

```
FS 设备:
  批量:     8/16/32/64（最大 64）
  中断:     0~64
  等时:     0~1023

HS 设备:
  批量:     只能 512
  中断:     0~1024
  等时:     0~1024
```

**扩展位（HS 等时/中断才有）：**

```
Bit 12-11（即 wMaxPacketSize 的高 2 bit 被挪用）:
  00 = 1 transaction per microframe
  01 = 2 transactions per microframe
  10 = 3 transactions per microframe
```

**Byte 6 — bInterval**

Host 多久访问一次这个端点。但不同速率下含义不同，详见 3.7。

### HEX 实例

```
一个 USB 鼠标的 HID 中断 IN 端点：

Offset: 00 01 02 03 04 05 06
  Hex: 07 05 81 03 08 00 0A

解读：
  07    = bLength (7)
  05    = bDescriptorType (Endpoint)
  81    = bEndpointAddress → EP1, IN (Device→Host)
  03    = bmAttributes → 中断传输
  08 00 = wMaxPacketSize → 8 字节 (够放按键+位移)
  0A    = bInterval → 每 10ms 查询一次 (100Hz)
```

---

## 3.7 bInterval 在不同速率下的含义

bInterval 是 Endpoint Descriptor 的最后一个字节，但它是 USB 描述符中**最容易被误解**的字段——同一个值在不同速率/传输类型下含义完全不同。

### 总览

| 速率 | 传输类型 | 公式 | 单位 | 范围 |
|------|---------|------|------|------|
| FS | 中断 | bInterval | **ms** | 1~255 ms |
| LS | 中断 | bInterval | **ms** | 10~255 ms |
| FS | 等时 | 2^(bInterval-1) | **帧数 (ms)** | 1~16 ms |
| HS | 中断 | 2^(bInterval-1) | **微帧 (125μs)** | 125μs~4s |
| HS | 等时 | bInterval-1 | **微帧 (125μs)** | 125μs~16ms |
| 所有 | 批量 | 忽略 | — | 有空就来 |

### 逐类说明

**FS 中断 — 最直白**

bInterval 就是毫秒数：
```
bInterval=1  → 每 1ms 查一次
bInterval=10 → 每 10ms 查一次（普通鼠标/键盘：100Hz）
bInterval=32 → 每 32ms 查一次
```

**FS 等时 — 指数关系**

```
bInterval=1 → 2^0 = 1   → 每 1 帧 (每 1ms)
bInterval=2 → 2^1 = 2   → 每 2 帧 (每 2ms)
bInterval=3 → 2^2 = 4   → 每 4 帧 (每 4ms)
```

**HS 中断 — 微帧底数 + 指数**

```
bInterval=1 → 2^0 = 1 微帧 → 每 125μs
bInterval=4 → 2^3 = 8 微帧 → 每 1ms（=FS 的 bInterval=1）
```

注意：bInterval=4 在 HS 中断下 = 1ms，跟 FS 的 bInterval=1 相同效果——但数值是 4 不是 1。

**HS 等时 — 微帧线性**

```
bInterval=1 → 每 125μs（每微帧）
bInterval=2 → 每 2 微帧 (250μs)
bInterval=4 → 每 4 微帧 (500μs)
```

### 常见错误

**BUG 1：把所有传输类型当线性**

```c
// ❌ 错误
uint16_t polling_ms = desc->bInterval;  // FS 中断碰巧对，其他全错

// ✅ 正确
switch (speed) {
case USB_SPEED_FULL:
    if (type == USB_ENDPOINT_XFER_INT)  polling_us = desc->bInterval * 1000;
    if (type == USB_ENDPOINT_XFER_ISOC) polling_us = (1 << (desc->bInterval - 1)) * 1000;
    break;
case USB_SPEED_HIGH:
    if (type == USB_ENDPOINT_XFER_INT)  polling_us = (1 << (desc->bInterval - 1)) * 125;
    if (type == USB_ENDPOINT_XFER_ISOC) polling_us = (desc->bInterval - 1) * 125;
    break;
}
```

**BUG 2：HS 中断公式跟 HS 等时弄反**

HS 中断是 `2^(bInterval-1)`（指数），HS 等时是 `bInterval-1`（线性）。搞反了会导致帧间隔暴涨到秒级。

---

## 3.8 ⛁ String Descriptor

### 结构

```
Offset  Size  Field          含义
──────────────────────────────────────────────
  0      1     bLength        本描述符总字节数
  1      1     bDescriptorType 0x03
  2~N   可变   bString         UNICODE 字符串 (UTF-16LE)
```

没有固定长度——bLength 是多少就是多少。

### 实例

```
一个 SanDisk U 盘的产品名 (iProduct=0x02):

Offset: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13
  Hex: 16 03 55 00 6C 00 74 00 72 00 61 00 20 00 46 00 69 00 74 00

解读:
  16       = bLength (22 字节)
  03       = bDescriptorType (String)
  55 00    = 'U'  (U+0055, LE)
  6C 00    = 'l'  (U+006C)
  ...      → "Ultra Fit"
```

英文/数字每个字符就是 `0x00 + ASCII码`——因为 Unicode 前 128 个码点等于 ASCII。

### String Descriptor #0 是特例

Host 不能直接问"给我 String #2"——它必须先知道设备支持什么语言。String Descriptor #0 存的就是**语言 ID 列表**（LANGID）：

```
Offset: 00 01 02 03 04 05 06 07
  Hex: 08 03 09 04

解读:
  08       = bLength (8 字节)
  03       = bDescriptorType (String)
  09 04    = 0x0409 = English (United States)
```

Host 的请求流程：

```
① Host → Get_Descriptor(String, index=0)         → 设备回: [0x0409, ...]
② Host 挑一个语言: "English 0x0409"
③ Host → Get_Descriptor(String, index=2, langid=0x0409) → 产品名英文版
```

### Unicode 编码细节

bString 是 **UTF-16LE**（小端序），不是 ASCII，不是 UTF-8。

```
字符 'A' (U+0041):  41 00  ← 低字节在前
字符 '中'(U+4E2D):  2D 4E  ← LE: LSB 在先

"USB 视频设备" 的部分 hex:
  55 00  = 'U'
  53 00  = 'S'
  42 00  = 'B'
  20 00  = ' '
  C6 89  = '视' (U+89C6, LE → 89 C6)
  91 98  = '频' (U+9891)
```

---

## 3.9 Device Qualifier Descriptor + Other Speed Configuration

### 为什么需要

HS 设备插入 USB 2.0 端口 → 480Mbps。但如果这根线插到了 USB 1.1 口，设备会被降级到 FS。两种速度下参数不同：

| 参数 | HS 模式 | FS 模式 |
|------|---------|---------|
| EP0 MaxPacketSize | 64 | 可能是 8/16/32/64 |
| 批量端点的 wMaxPacketSize | 512 | ≤64 |
| bInterval 语义 | HS 版本公式 | FS 版本公式 |

### Device Qualifier Descriptor — 逐字节

```
Offset  Size  Field                含义
──────────────────────────────────────────────────────────────
  0      1     bLength              0x0A (10)
  1      1     bDescriptorType      0x06
  2-3    2     bcdUSB               另一个速度下遵循的USB版本
  4      1     bDeviceClass         设备级分类（另一个速度下）
  5      1     bDeviceSubClass
  6      1     bDeviceProtocol
  7      1     bMaxPacketSize0      EP0最大包（另一个速度下）
  8      1     bNumConfigurations   另一个速度下有几个配置
  9      1     bReserved            保留=0
```

跟 Device Descriptor 比——少了 VID/PID/BCD/字符串索引，多了保留字节。Host 假设这些不变（同一个物理设备）。

### HEX 示例

```
一个 HS U 盘在 HS 模式时的 FS 备选配置：

Device Descriptor (HS):           Device_Qualifier (FS 备用):
  12 01 00 02 ... 40 ... 01         0A 06 00 02 00 00 00 08 01 00
                                     ↑     ↑           ↑     ↑
                                    bcdUSB bDeviceClass  EP0=8 1个Config
```

降级到 FS 时，EP0 从 64 退到 8 字节，批量端点从 512 退到 64 字节。

### Other_Speed_Configuration Descriptor

结构跟 Configuration Descriptor **完全一样**（0x07 类型码），后面同样跟着 Interface → Endpoint 完整链。唯一的区别是 bDescriptorType=0x07（不是 0x02）。

---

## 3.10 BOS Descriptor

BOS = Binary Device Object Store。USB 3.0 引入的**扩展容器**。

### 解决什么问题

USB 2.0 的 Device Descriptor 是固定 18 字节。USB 3.0 需要宣告新能力（LPM、SuperSpeed 特性等），但不敢改 Device Descriptor 结构——改了老 Host 就不认识了。解决思路：加一个指针指向**可变长的扩展区**。

### 结构

**BOS Header（5 字节）：**

```
Offset  Size  Field              示例            含义
────────────────────────────────────────────────────────────
  0      1     bLength            0x05 (5)        "Header本身5字节"
  1      1     bDescriptorType    0x0F            "我是BOS"
  2-3    2     wTotalLength       0x0016 (22)     "Header+所有Capability 22字节"
  4      1     bNumDeviceCaps     0x03            "下面有3个能力描述符"
```

**每个 Capability 的通用头部（3 字节）：**

```
Offset  Size  Field              含义
────────────────────────────────────────────────────────────
  0      1     bLength            本 Capability 的字节数
  1      1     bDevCapabilityType 能力类型码
  2~N   可变   Capability 数据    类型决定内容
```

### USB 2.0 Extension Descriptor（最重要）

```
Offset  Size  Field                 含义
────────────────────────────────────────────────────────────
  0      1     bLength               0x07 (7字节)
  1      1     bDevCapabilityType    0x02
  2-5    4     bmAttributes          位图 — 支持的特性
  6      1     bLPMDevBESLAttr       设备建议的 BESL 值
```

**bmAttributes 的 key bit：**

```
Bit 0 (LPM):  1 = 支持 LPM Link Power Management
              设备可以通过 LPM 事务进入更低功耗（比 Suspend 高效）
              LPM 可以在 10μs 级别进出低功耗状态
```

### 标准 Capability 类型

| bDevCapabilityType | 名称 |
|:---:|------|
| 0x01 | Wireless USB |
| 0x02 | USB 2.0 Extension (LPM) |
| 0x03 | SuperSpeed USB |
| 0x04 | Container ID (128-bit UUID) |
| 0x05 | Platform |
| 0x0A | SuperSpeedPlus USB (USB 3.1+) |
| 0x0D | Precision Time Measurement |

---

## 3.11 描述符类型码全集

### 标准描述符类型码

| 值 | 宏名 | 描述符 | 固定长度？ |
|:--:|------|--------|:--:|
| 0x01 | `USB_DT_DEVICE` | Device | ✅ 18 字节 |
| 0x02 | `USB_DT_CONFIG` | Configuration | ✅ 9 字节 |
| 0x03 | `USB_DT_STRING` | String | ❌ 可变 |
| 0x04 | `USB_DT_INTERFACE` | Interface | ✅ 9 字节 |
| 0x05 | `USB_DT_ENDPOINT` | Endpoint | ✅ 7 字节（USB 2.0）|
| 0x06 | `USB_DT_DEVICE_QUALIFIER` | Device Qualifier | ✅ 10 字节 |
| 0x07 | `USB_DT_OTHER_SPEED_CONFIG` | Other Speed Config | ✅ 9 字节（头）|
| 0x0B | `USB_DT_INTERFACE_ASSOCIATION` | IAD | ✅ 8 字节 |
| 0x0F | `USB_DT_BOS` | BOS | ✅ 5 字节（头）|

### BOS Capability 类型码

| 值 | 名称 |
|:--:|------|
| 0x02 | USB 2.0 Extension (LPM) |
| 0x03 | SuperSpeed USB |
| 0x04 | Container ID |
| 0x0A | SuperSpeedPlus USB |
| 0x0D | Precision Time Measurement |

### 类专用描述符类型码

| 类 | 值 | 描述符 |
|------|:--:|------|
| HID | 0x21 | HID Descriptor |
| HID | 0x22 | Report Descriptor |
| CDC | 0x24 | CDC 类专用（用 `bDescriptorSubType` 进一步区分）|
| UVC | 0x24 | UVC 类专用 |
| Audio | 0x24 | Audio Control 类专用 |
| Hub | 0x29 | Hub Descriptor |

**0x24 的复用机制：** CDC、UVC、Audio 都把 0x24 用作类专用描述符——不冲突，因为 Host 先读了 Interface Descriptor 的 `bInterfaceClass`，再遇到 0x24 时就知道按哪个类解析。

### IAD（Interface Association Descriptor）— 0x0B

```
Interface Association Descriptor (8B):
  bLength              = 8
  bDescriptorType      = 0x0B
  bFirstInterface      = 0  ← "从Interface#0开始"
  bInterfaceCount      = 2  ← "一共2个接口绑在一起"
  bFunctionClass       = 0x0E (Video)
  bFunctionSubClass    = 0x03 (Video Interface Collection)
  bFunctionProtocol    = 0x00
  iFunction            = 0x00
```

Windows 需要 IAD 才能把 VC+VS 两个接口绑定到同一个摄像头驱动堆栈。

### 描述符识别流程

```
while (offset < wTotalLength) {
    desc = (uint8_t*)buf + offset;
    len = desc[0];       // bLength → 就是链表的 next 指针
    type = desc[1];      // bDescriptorType
    
    if (type == 0x04) {
        current_interface = desc[2];
        current_class = desc[5];
    }
    
    if (type == 0x24 && current_class == 0x0E) {
        subtype = desc[2];
        parse_uvc_class_specific(subtype, desc);
    }
    
    offset += len;
}
```

---

## 综合示例：CDC 虚拟串口完整描述符链

以一个 STM32 虚拟串口为例，把 3.1~3.11 串起来。设备在 HS 模式下，自供电。

### 完整 RAW HEX

```
Device Descriptor (18B):
  Offset: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11
    Hex: 12 01 00 02 02 00 00 40 83 04 4A 57 00 02 01 02 03 01
         │    │     │  │  │  │  │        │     │     │  │  │  └─ bNumConfigurations=1
         │    │     │  │  │  │  │        │     │     │  │  └─── iSerialNumber=3
         │    │     │  │  │  │  │        │     │     │  └────── iProduct=2
         │    │     │  │  │  │  │        │     │     └───────── iManufacturer=1
         │    │     │  │  │  │  │        │     └─────────────── bcdDevice=0x0200 (2.00)
         │    │     │  │  │  │  │        └───────────────────── idProduct=0x574A
         │    │     │  │  │  │  └────────────────────────────── idVendor=0x0483 (STMicro)
         │    │     │  │  │  └───────────────────────────────── bMaxPacketSize0=64
         │    │     │  │  └──────────────────────────────────── bDeviceProtocol=0x00
         │    │     │  └─────────────────────────────────────── bDeviceSubClass=0x02?
         │    │     └────────────────────────────────────────── bDeviceClass=0x02 (CDC)
         │    └──────────────────────────────────────────────── bcdUSB=0x0200 (USB 2.0)
         └───────────────────────────────────────────────────── bLength=18, bDescType=0x01

Configuration Descriptor (9B):
  Offset: 00 01 02 03 04 05 06 07 08
    Hex: 09 02 43 00 02 01 00 A0 32
         │    │     │  │  │  │     └─ bMaxPower=50×2=100mA (自供电+少量总线补充)
         │    │     │  │  │  └──────── bmAttributes=0xA0=1010 0000 (自供电, 无RemoteWake)
         │    │     │  │  └─────────── iConfiguration=0 (无名字)
         │    │     │  └────────────── bConfigurationValue=1
         │    │     └───────────────── bNumInterfaces=2 (CDC控制接口 + CDC数据接口)
         │    └─────────────────────── wTotalLength=0x0043=67B 完整链
         └──────────────────────────── bLength=9, bDescType=0x02

Interface #0 — CDC 通信控制接口 (9B):
  Offset: 00 01 02 03 04 05 06 07 08
    Hex: 09 04 00 00 01 02 02 01 00
         │    │  │  │  │  │  │  └─ iInterface=0
         │    │  │  │  │  │  └──── bInterfaceProtocol=0x01 (AT Commands V.250)
         │    │  │  │  │  └─────── bInterfaceSubClass=0x02 (Abstract Control Model)
         │    │  │  │  └────────── bInterfaceClass=0x02 (CDC)
         │    │  │  └───────────── bNumEndpoints=1 (中断IN, 用于SerialState通知)
         │    │  └──────────────── bAlternateSetting=0
         │    └─────────────────── bInterfaceNumber=0
         └──────────────────────── bLength=9, bDescType=0x04

  CDC Header Descriptor (5B):
    Hex: 05 24 00 10 01
         │  │  │  └─── bcdCDC=0x0110 (CDC 1.10)
         │  │  └────── bDescriptorSubType=0x00 (Header)
         │  └───────── bDescriptorType=0x24 (CS Interface)
         └──────────── bLength=5

  CDC ACM Descriptor (4B):
    Hex: 04 24 02 02
         │  │  │  └── bmCapabilities=0x02 (支持Set_Line_Coding, Set_Control_Line_State)
         │  │  └───── bDescriptorSubType=0x02 (ACM)
         │  └──────── bDescriptorType=0x24 (CS Interface)
         └─────────── bLength=4

  CDC Union Descriptor (5B):
    Hex: 05 24 06 00 01
         │  │  │  │  └── bSlaveInterface=1 (数据接口是Interface#1)
         │  │  │  └───── bMasterInterface=0 (控制接口是Interface#0)
         │  │  └──────── bDescriptorSubType=0x06 (Union)
         │  └─────────── bDescriptorType=0x24 (CS Interface)
         └────────────── bLength=5

  CDC Call Mgmt Descriptor (5B):
    Hex: 05 24 01 00 01
         │  │  │  │  └── bDataInterface=1 (数据走Interface#1)
         │  │  │  └───── bmCapabilities=0x00 (设备自己不处理Call Mgmt)
         │  │  └──────── bDescriptorSubType=0x01 (Call Management)
         │  └─────────── bDescriptorType=0x24 (CS Interface)
         └────────────── bLength=5

  Endpoint IN — 中断通知 (7B):
    Hex: 07 05 83 03 08 00 0A
         │    │     │     │  └─ bInterval=10ms (FS中断)
         │    │     │     └──── wMaxPacketSize=8
         │    │     └────────── bmAttributes=0x03 (中断传输)
         │    └──────────────── bEndpointAddress=0x83 → EP3, IN
         └───────────────────── bLength=7, bDescType=0x05

Interface #1 — CDC 数据接口 (9B):
  Offset: 00 01 02 03 04 05 06 07 08
    Hex: 09 04 01 00 02 0A 00 00 00
         │    │  │  │  │  │        └─ iInterface=0
         │    │  │  │  │  └────────── bInterfaceProtocol=0x00
         │    │  │  │  └───────────── bInterfaceSubClass=0x00
         │    │  │  └──────────────── bInterfaceClass=0x0A (CDC Data)
         │    │  └─────────────────── bNumEndpoints=2 (批量IN + 批量OUT)
         │    └────────────────────── bAlternateSetting=0
         └─────────────────────────── bInterfaceNumber=1

  Endpoint OUT — 批量发送 (7B):
    Hex: 07 05 02 02 40 00 00
         │    │     │     │  └─ bInterval=0 (批量忽略)
         │    │     │     └──── wMaxPacketSize=64 (FS)
         │    │     └────────── bmAttributes=0x02 (批量传输)
         │    └──────────────── bEndpointAddress=0x02 → EP2, OUT
         └───────────────────── bLength=7, bDescType=0x05

  Endpoint IN — 批量接收 (7B):
    Hex: 07 05 81 02 40 00 00
         │    │     │     │  └─ bInterval=0 (批量忽略)
         │    │     │     └──── wMaxPacketSize=64 (FS)
         │    │     └────────── bmAttributes=0x02 (批量传输)
         │    └──────────────── bEndpointAddress=0x81 → EP1, IN
         └───────────────────── bLength=7, bDescType=0x05
```

### 总字节数核对

```
Device Descriptor:               18
Configuration Descriptor:         9
Interface #0:                     9
  CDC Header:                     5
  CDC ACM:                        4
  CDC Union:                      5
  CDC Call Mgmt:                  5
  Endpoint IN (中断):             7
Interface #1:                     9
  Endpoint OUT (批量):            7
  Endpoint IN (批量):             7
────────────────────────────────────
  wTotalLength = 18+9+9+5+4+5+5+7+9+7+7 = 85?

不对——wTotalLength不包含Device Descriptor！
Config开始的总链长:
  9+9+5+4+5+5+7+9+7+7 = 67 = 0x0043 ✓
```

### 结构树

```
Device (VID=0x0483 STM, USB 2.0, CDC类, FS, EP0=64B)
  └── Config #1 (自供电, 100mA)
        ├── Interface #0: CDC Control (bInterfaceClass=0x02)
        │   ├── CDC Header (CDC 1.10)
        │   ├── CDC ACM (支持 Line_Coding + Control_Line_State)
        │   ├── CDC Union (Master=#0, Slave=#1)
        │   ├── CDC Call Mgmt (Data走Interface#1)
        │   └── EP3 IN (中断, 8B, 10ms) ← SerialState通知
        │
        └── Interface #1: CDC Data (bInterfaceClass=0x0A)
            ├── EP2 OUT (批量, 64B) ← Host→Device 发串口数据
            └── EP1 IN  (批量, 64B) ← Device→Host 收串口数据
```

### 数据流

```
Host 打开串口:
  ① Host → SETUP(Set_Line_Coding, 115200-8-N-1) → Interface #0, EP0
  ② Host → SETUP(Set_Control_Line_State, DTR=1, RTS=1) → Interface #0, EP0

Host 发 "Hello":
  ③ Host → OUT Token (Addr=N, EP2) → DATA0("Hello") → Device ACK
     ↑ EP2 OUT, 批量, Interface #1

Device 回 "World":
  ④ Host → IN Token (Addr=N, EP1) → Device DATA1("World") → Host ACK
     ↑ EP1 IN, 批量, Interface #1

设备状态变化 (如 DCD 信号断):
  ⑤ Host → IN Token (Addr=N, EP3) → Device DATA0(SerialState=10B) → Host ACK
     ↑ EP3 IN, 中断, Interface #0
```

这就是从描述符到总线通信的完整映射：描述符定义了"有哪些接口、各有什么端点"，Host 根据这些信息发的每一笔 Token 都精确命中对应端点和方向。

---

## 补充问答一：控制传输只能在 EP0 吗？

**是的，所有 USB 设备的控制传输只能在端点 0（EP0）上。** 这是 USB 规范从第一天就写死的硬规定，不管你是 UVC 摄像头、U 盘、HID 键盘还是 CDC 串口。

### 为什么

EP0 是每个 USB 设备的"管理通道"——出厂自带，不需要在描述符里声明，无条件存在。控制传输走 EP0 不需要 Interface 下面的 Endpoint Descriptor 来定义，这就是为什么 bNumEndpoints 不含 EP0。

### UVC 摄像头的实际操作

```
设置亮度:
  Host → SETUP Token (ADDR=3, ENDP=0) → DATA0(8B Setup Packet) → 设备 ACK
  这个 Setup Packet 里 bRequest=SET_CUR, wValue=亮度值
  ↓
  这些都在 EP0 上跑，跟 VC Interface 下的 EP3 IN（中断，硬件通知）没有关系

视频流数据:
  Host → IN Token (ADDR=3, ENDP=2) → 设备 DATA0(一帧视频) → 不等 ACK
  ↓
  这才走 VS Interface 下的等时端点 EP2
```

### "Video Control" 接口的命名陷阱

UVC 的 VC（Video Control）接口名字里带 "Control"，容易让人以为控制命令走它下面的端点。但实际上：

```
Interface #0 (VC):
  作用: 用描述符声明"我有哪些控制项"（亮度、对比度、白平衡……）
        bmControls 位图列出: 亮度✓ 对比度✓ 缩放✓ ...
  
  控制命令的实际通道: EP0（永远是 EP0）
  
  可选端点: EP3 IN（中断）——不是用来传控制的，是用来做硬件事件通知的
           比如"摄像头被物理按键关闭了"这种 Host 意料之外的状态变化
```

**一句话：所有控制传输走 EP0，VC 接口定义的是"有哪些控制"，而不是"控制走哪个端点"。**

---

## 补充问答二：只有一个 EP0 走控制传输会不会不够？

不会不够。原因很直观：**控制传输是"控制面板"，不是"数据管道"。**

### 控制传输 vs 数据端点的工作量对比

```
一个 UVC 摄像头在 1 秒内的总线活动：

EP0（控制）:
  Set_Interface(Alt=1)  ← 打开视频流，1 次控制传输，~100 字节
  设置亮度 90%           ← 1 次控制传输，~50 字节
  查询当前帧率           ← 1 次控制传输，~50 字节
  ─────────────────────────
  合计：3 次控制传输，~200 字节，总线占比 < 1%

EP2 IN（等时，视频流）:
  每 125μs 一发，一发 3072 字节
  ─────────────────────────
  合计：8000 次等时事务，~24 MB，总线占比 ~80%
```

控制传输只占零头。而且控制请求的语义是**一问一答、做完一个再做下一个**——Host 不会同时下两条控制命令，因为总线本身就是半双工的，就算再多一个控制端点也得排队。

### 类比

路由器只有一个管理页面（192.168.1.1），但它同时服务 50 台设备上网——管理流量跟数据流量走的不是一条路。路由器不需要开 50 个管理页面，同理 USB 设备不需要多个控制端点。

**什么情况 EP0 会忙不过来？** 几乎不存在。EP0 有硬件级缓冲保证 SETUP 永远能接收，控制传输之间有自然地隔断（枚举只在启动时密集），Host 会逐个排队。真正要担心的是固件在 EP0 中断服务例程里干了太多事——但那是固件实现问题，不是协议设计问题。

---

## 补充问答三：UVC 扩展单元传大数据怎么办？

UVC 扩展单元（XU）确实可以通过控制传输传递任意大小的数据块——固件升级、校准表、配置文件，wLength 最大 65535 字节。这时候 EP0 会不会成为瓶颈？

### 算一笔账

假设一个 UVC 扩展单元要传输 64KB 的校准数据（这在工业相机里很常见）：

```
FS (12Mbps): EP0 每次事务最多 64 字节
  64KB ÷ 64B = 1024 次 IN/OUT 事务
  每事务 ≈ 125μs → 1024 × 125μs ≈ 128ms

HS (480Mbps): EP0 每次事务最多 512 字节
  64KB ÷ 512B = 128 次事务 × ~10μs ≈ 1.3ms
```

128ms（FS）或 1.3ms（HS）传输 64KB——跟等时传输每秒 24MB 比当然慢，但对"设置一次，用一辈子"的控制数据来说够了。

### 串行阻塞问题

控制传输期间，Host 不能对同一个 EP0 发其他控制请求。如果扩展单元数据量大 + 其他控制请求频繁，EP0 就会成为串行瓶颈。

### USB 的解决方案

**出路 1：固件升级走 Bulk 端点。** USB 设备固件升级标准（DFU）故意不用控制传输传固件数据——控制传输只发命令（开始升级 / 传送完成 / 验证），实际固件字节走专用的 Bulk 端点。

**出路 2：HS 微帧下 EP0 能获得更多带宽。** 每个微帧 (125μs) 里 Host 可以安排给 EP0 的事务次数；8 个微帧 = 1ms，EP0 在一帧内最多跑 8 次事务，比 FS 宽裕 8 倍。

**结论：EP0 不够的场景确实存在，但不是"走不下"——是"排队等太久"。** 当 UVC 扩展单元要传大块配置数据时，EP0 的 64/512 字节单次事务大小会在 FS 下产生明显延迟。但这种情况用 Bulk 端点替代——USB 协议本身也推荐这个模式。

---

## 补充问答四：控制传输排队会不会无限积累？

不会无限排。USB 在三个层面做了保护：

### 硬件层：EP0 状态机天然串行

EP0 的控制传输是一个严格的硬件状态机，不允许并发：

```
SETUP → DATA(可选) → STATUS = 一次完整的控制传输
   ↑                                          ↓
   └─────────── 完成后才能接收下一个 SETUP ────┘
```

Host 控制器硬件本身就不会对同一个设备的 EP0 同时发起两个 SETUP 事务——总线按 Transaction 逐个走，上一个 STATUS 阶段的 ACK 没收到之前，下一个 SETUP Token 根本不会出现在总线上。**所以总线层没有"积压"——因为压根没地方给它压。**

### Host 驱动层：每个设备一个控制请求槽位

```
Windows (USB 2.0 栈):
  每个设备 → 一个 IRP 挂起 → 完成后才能投递下一个
  上层同时调用 DeviceIoControl() 三次 → 驱动栈只接受一个，其余返回 STATUS_DEVICE_BUSY

Linux (usbcore):
  每个设备 → 一个控制 URB 在处理
  usb_control_msg() 是同步阻塞的 —— 函数不返回，直到控制传输完成
  多线程同时调 → 一个拿到 EP0 锁，其余线程在 mutex_lock_interruptible() 上睡觉排队
```

实际上没有堆积——软件层要么**阻塞**（等着），要么**立即失败返回**（忙），不存在无限增长的有界队列。

### 软件应用层：超时杀死

```
xHCI:  默认 5 秒控制传输超时
        超时 → 中止端点 → 返回错误给上层
        下一个排队的请求拿到 EP0 锁

软件:   请求超时 → 返回 -ETIMEDOUT
        调用方释放 USBD_STATUS_CANCELED
        后续请求正常通过
```

**所以不会永久卡住。** 要么完成（下一个上路），要么超时（被杀死），要么立即拒绝（软件不排队）。
