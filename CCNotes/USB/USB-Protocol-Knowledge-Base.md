# USB 协议知识库

> 整理日期：2026-08-02
> 覆盖范围：Phase 1-3 理论学习 + 真实设备描述符实战 + UVC XU 控制与取流实战
> 学习进度：44/67 知识点（66%），Phase 4 完成，下一阶段 Phase 5
> 学习策略：自底向上 — 先把协议基础打牢，再谈开发
> 深度要求：每个 byte 的每个 bit 含义都要讲清楚（MQTT 报文头级别精度）

---

## 前言：学习路线图

### 67 个知识点全景

本知识库基于以下学习计划构建，总计 8 个阶段、67 个知识点任务。\(\color{green}{\text{⛁}}\) = 逐字节/逐比特精讲。

| 阶段 | 内容 | 知识点数 | 状态 |
|------|------|:---:|:---:|
| Phase 1 | USB 概览与总线拓扑 | 5 | ✅ 完成 |
| Phase 2 | USB 通信模型 — 层层拆解到比特 | 16 | ✅ 完成 |
| Phase 3 | USB 描述符体系 — 逐字节解剖 | 11 | ✅ 完成 |
| Phase 4 | USB 枚举过程 — 逐包逐事务追踪 | 12 | ✅ 完成 12/12 |
| Phase 5 | 标准请求与 Setup 包深度解析 | 6 | ⬜ 待开始 |
| Phase 6 | 设备类协议逐字节解析（HID / CDC / UVC） | 26 | ⬜ 待开始 |
| Phase 7 | 协议分析工具与实操 | 7 | ⬜ 待开始 |
| Phase 8 | libusb 编程衔接 | 5 | ⬜ 待开始 |

### 阅读指南

- **从零开始**：按第一篇→第二篇→第三篇→第四篇→第五篇→第六篇顺序阅读
- **快速查阅**：跳转到附录的速查表
- **实战优先**：如果你已经有理论基础，直接跳到第五篇（真实设备）和第六篇（XU 取流）
- **MQTT 类比**：文中大量使用 MQTT/TCP/HTTP 做类比，帮助理解 USB 协议设计
- **方向视角**：IN = Device→Host（Host "收进来"），OUT = Host→Device（Host "发出去"）

---

# 第一篇：USB 概览与总线拓扑

---

## 1.1 USB 设计目标与历史

### USB 之前的七种接口和七种痛

| 接口 | 痛点 |
|------|------|
| RS-232 串口 | 速度慢(115.2kbps)、不能热插拔、一端口一设备、需手动设参数 |
| 并口(LPT) | 电缆粗贵、速度~150KB/s、只能接打印机 |
| PS/2 | 不能热插拔、键盘鼠标不通用 |
| SCSI | 贵、需专用卡、终端电阻/ID需跳线 |
| Game Port | 只能一个游戏杆、CPU占用极高 |
| VGA | 只传视频不传数据/供电 |
| 各类专用 | 每加设备可能要加卡，IRQ/DMA/IO冲突 |

### USB 七大设计目标

| # | 目标 | 对应设计决策 |
|---|------|-------------|
| 1 | 一根线接所有外设 | 统一物理层+协议层 |
| 2 | 热插拔 | Host主动检测总线电平变化+枚举协议 |
| 3 | 自动配置 | 描述符→自动识别→不需要手动设地址 |
| 4 | 支持多种速度 | 1.5M/12M/480M/5G+ 分级 |
| 5 | 总线供电 | VBUS 5V，低功耗设备不额外供电 |
| 6 | 可扩展 | Hub级联，最多127设备 |
| 7 | 低成本 | 低速简单设备+分层协议 |

### USB 核心设计哲学

**Host 中心化**：所有通信由 Host 发起，Device 只能被动应答。

跟 MQTT 的根本差异：MQTT Client 可以随时 PUBLISH，USB Device 连打招呼的权利都没有。

---

## 1.2 USB 版本演进全景

| 版本 | 发布年 | 速度 | 编码 | 供电 | 连接器 |
|------|--------|------|------|------|--------|
| USB 1.0 | 1996 | 1.5 Mbps | NRZI | 5V/100mA | Type-A/B |
| USB 1.1 | 1998 | 1.5/12 Mbps | NRZI | 5V/500mA | 同上 |
| USB 2.0 | 2000 | +480 Mbps | NRZI | 5V/500mA | +Mini/Micro |
| USB 3.0 | 2008 | +5 Gbps | 8b/10b | 5V/900mA | 新增5根差分线 |
| USB 3.1 | 2013 | +10 Gbps | 128b/132b | 可协商到20V/5A | Type-C引入 |
| USB 3.2 | 2017 | +20 Gbps | 128b/132b | 同上 | Type-C双通道 |
| USB4 | 2019 | 20/40 Gbps | 64b/66b | 同上 | 仅Type-C |

### 关键速度概念

- **Low Speed (LS)**: 1.5Mbps — 键盘、鼠标
- **Full Speed (FS)**: 12Mbps — 打印机、老摄像头
- **High Speed (HS)**: 480Mbps — U盘、移动硬盘、高清摄像头
- **SuperSpeed (SS)**: 5Gbps+ — 固态硬盘、4K摄像头

### 向后兼容矩阵

```
Host \ Device: 新Host永远可以挂老Device，老Host不能挂新Device
USB 3.x Host → LS/FS/HS/SS 全支持
USB 2.0 Host → LS/FS/HS
USB 1.1 Host → LS/FS
```

### 为什么基于 USB 2.0 学协议

1. 包结构可直接读(NRZI简单)
2. 广播总线(Wireshark一个口看所有通信)
3. 四种传输类型都有
4. HID/CDC/UVC在2.0上完整工作
5. 3.0只是加了速度和路由，概念基础一样

---

## 1.3 总线拓扑结构

### 树形拓扑规则

| 规则 | 数值 |
|------|------|
| 最多层数 | 7层(Tier)，Root Hub = Tier 1 |
| 最多设备 | 127个（ADDR字段7bit，0x00保留） |
| 最多非Root Hub | 5个 |
| 每段电缆最长 | 5米(FS/LS)，总长30米 |

### 7层限制原因

1. **信号延迟**：往返延迟 ≤ 700ns(FS)，每米电缆 ~5.2ns，5m×5 + Hub延迟 → 7层到物理上限
2. **电缆长度**：5个Hub×5m = 最大30米

### 地址范围

```
ADDR字段 7 bit → 0x00~0x7F (128个)
0x00 = 默认地址（Default Address），设备刚复位后使用
剩余 1~127 = 127个可分配地址 → 127设备上限
```

### 三种角色

- **Host**: 发起所有通信、提供VBUS(5V)、枚举、带宽调度、内置Root Hub
- **Hub**: 扩展端口、检测插拔、端口供电、HS↔FS/LS速度翻译(Split Transaction)、本身也是USB Device
- **Device (Function)**: 响应请求、提供描述符、实现功能逻辑、管理电源

### Compound vs Composite

- **Compound Device**: 一个壳子多个地址（内含Hub+多个独立Device）
- **Composite Device**: 一个地址多个Interface（一个芯片多功能，如摄像头+麦克风）

---

## 1.4 主机控制器类型

| 缩写 | 全称 | 管什么速度 | 存亡状态 |
|------|------|-----------|---------|
| UHCI | Universal HCI | LS+FS | 已死亡(Intel) |
| OHCI | Open HCI | LS+FS | 已死亡(Compaq等) |
| EHCI | Enhanced HCI | HS + 兼容LS/FS | 存量设备 |
| xHCI | eXtensible HCI | LS/FS/HS/SS全管 | 现代标准 |

### EHCI 双控器架构

EHCI只支持HS。LS/FS设备需要 Companion Controller (UHCI/OHCI) 来处理：

```
插LS/FS设备 → 路由给Companion Controller
插HS设备(Chirp协商成功) → 交给EHCI
```

### xHCI 统一架构

一个控制器管所有速度，不再需要Companion Controller。通过Transfer Ring (TRB环形链表) 统一管理所有传输。

### 软件栈层次

```
你的SDK (libusb API)
  → libusb 用户空间库
    → OS USB 驱动后端 (WinUSB/usbfs/IOKit)
      → OS USB 驱动栈
        → 主机控制器驱动 (HCD)
          → 主机控制器硬件 (HC)
            → USB 物理总线 (D+/D-)
```

---

## 1.5 物理层与电气特性

### USB 2.0 线缆 (4根线)

| 线色 | 信号 | 用途 |
|------|------|------|
| 红 | VBUS | 5V供电 |
| 白 | D- | 差分数据- |
| 绿 | D+ | 差分数据+ |
| 黑 | GND | 地线 |

USB 3.0 加5根（共9根）：SSTX+/SSTX-/SSRX+/SSRX-/GND_DRAIN

### VBUS 供电规范

| 状态 | 最大电流 |
|------|---------|
| 未配置(枚举前) | 100 mA |
| 配置后 USB 2.0 | 500 mA |
| 配置后 USB 3.0 | 900 mA |
| 挂起态 | 2.5 mA |

电压: 4.40V ~ 5.25V (标称5.0V)

### 差分信号原理

D+和D-传差分信号：接收方计算 D+减D- 的差值。外部共模噪声同时影响两根线 → 相减后噪声抵消。

### J/K 状态

| 状态 | D+ | D- | 含义(取决于速度) |
|------|----|----|-----|
| J (Diff 1) | 高 | 低 | LS=Idle, FS=Data 1 |
| K (Diff 0) | 低 | 高 | LS=Data 1, FS=Idle |

注意：LS和FS的J/K含义是反的！

### 速度识别（电阻决定）

```
Host/Hub侧: D+和D-各有15KΩ下拉到GND
设备侧:
  FS/HS设备: D+ → 1.5KΩ上拉到3.3V → 插入后D+变高
  LS设备:    D- → 1.5KΩ上拉到3.3V → 插入后D-变高
```

Host检测：D+高→FS/HS, D-高→LS

### HS Chirp 协商

HS设备先冒充FS(D+上拉) → Host复位 → 设备发Chirp K → Host回Chirp K/J交替 → 设备切换HS终端电阻 → 协商成功，后续以480Mbps通信。

如果Chirp协商失败(老Host)→设备留在FS模式(12Mbps)。

### NRZI 编码 + Bit Stuffing

- NRZI: 0=跳变, 1=保持
- Bit Stuffing: 连续6个1后强制插1个0(产生跳变维持时钟同步)
- 接收方: 看到连续6个1→删除后面的0→恢复原数据

### SE0 (Single Ended Zero)

D+和D-同时为低。用于：
- EOP (包结束信号): SE0持续2个bit时间 + J状态1个bit时间
- 总线复位: SE0持续 ≥10ms

---

# 第二篇：USB 通信模型 — 层层拆解到比特

---

## 2.1 三层通信模型

### 三层定义

```
功能层 (Function Layer) — "做什么"
  → 你的SDK和业务逻辑
  → 例: HID按键→按键码, CDC→串口字节流, UVC→视频帧

USB设备层 (USB Device Layer) — "怎么组织"
  → 端点/管道/传输类型/描述符
  → 把包的碎片组织成有意义的传输

总线接口层 (Bus Interface Layer) — "怎么传"
  → 包(Packet)、NRZI编码、D+/D-信号
  → 硬件层面
```

### MQTT 类比

| MQTT层 | USB层 |
|--------|------|
| 应用层 (Topic/Payload) | 功能层 (业务数据) |
| MQTT协议 (QoS/PacketID) | USB设备层 (端点/管道/传输) |
| 传输层 (TCP/IP) | 总线接口层 (包/D+/D-) |

### 核心差异：Host中心化

- MQTT: Client可随时PUBLISH，Broker转发
- USB: Host不发Token，Device不能说任何话。所有通信Host发起。

---

## 2.2 端点 (Endpoint)

### 定义

**端点 = 设备内部的一段 FIFO 缓冲区。** 硬件概念，芯片设计时就要决定数量/大小/类型。

### 端点地址编码

```
Token包中 ENDP 字段 = 4 bits → 端点号 0~15

完整端点地址:
  Bit7 = 方向 (1=IN, 0=OUT) — 在端点描述符中
  Bit3-0 = 端点号

  IN = Device → Host (Host "收进来")
  OUT = Host → Device (Host "发出去")

方向永远从Host视角看！
0x81 = IN, EP1    0x02 = OUT, EP2
```

### 端点0 (EP0)

每个USB设备必须有。天生存在，不需要描述符声明。

| 属性 | 值 |
|------|-----|
| 端点号 | 固定0 |
| 方向 | 双向 |
| 传输类型 | 只能是控制传输 |
| 职责 | 枚举、配置、类特定控制请求 |
| LS MaxPacketSize | 固定8B |
| FS MaxPacketSize | 8/16/32/64 |
| HS MaxPacketSize | 固定64B |

类比 MQTT `$SYS/` 系统主题——管理通道。

### 最大包大小 (MaxPacketSize)

| 速度 | 控制 | 中断 | 批量 | 等时 |
|------|------|------|------|------|
| LS | 8 | 1~8 | ❌ | ❌ |
| FS | 8/16/32/64 | 1~64 | 8/16/32/64 | 1~1023 |
| HS | 64 | 1~1024 | 512 | 1~1024 |

> MaxPacketSize ≠ FIFO实际大小。FIFO通常更大(双缓冲/多缓冲)。

### 典型设备端点布局

```
HID键盘(LS): EP0(控制8B), EP1 IN(中断8B)
CDC串口(FS): EP0(控制64B), EP1 IN(中断16B), EP2 IN(批量64B), EP3 OUT(批量64B)
UVC摄像头(HS): EP0(控制64B), EP1 IN(中断16B可选), EP2 IN(等时512B)
```

---

## 2.3 管道 (Pipe)

### 定义

**管道 = Host软件到端点之间的逻辑通信通道。** 端点 = 目的地(硬件FIFO)，管道 = 通往目的地的路(软件抽象)。

### 两种管道

**消息管道 (Message Pipe)**：
- 双向、结构化、请求→响应格式
- 只能连EP0
- 只能控制传输
- 类比MQTT CONNECT/CONNACK

**流管道 (Stream Pipe)**：
- 单向、无结构、原始字节流
- 连EP1~15
- 中断/批量/等时传输
- 类比MQTT PUBLISH body

### 映射关系

```
消息管道 = 控制传输 = EP0 = 双向
流管道 = 中断/批量/等时传输 = 非0端点 = 单向
```

### libusb中的体现

管道不需要显式创建。调用传输API时系统内部维护：

```c
libusb_control_transfer(dev, ...);    // 消息管道, 永远双向
libusb_bulk_transfer(dev, 0x03, ...);  // 流管道, EP3 OUT
libusb_interrupt_transfer(dev, 0x81, ...); // 流管道, EP1 IN
```

---

## 2.3a 接口 (Interface) 与端点 (Endpoint) 的归属关系

### 核心规则四条

**规则 1：端点有主——每个非 EP0 端点只属于一个 Interface**

```
Configuration 1
├── Interface 0 (Video Control)
│   └── EP 0x83 (IN, Interrupt)      ← 只属于 IF=0
│
├── Interface 1 (Video Streaming)
│   └── EP 0x81 (IN, Bulk)           ← 只属于 IF=1
│
└── IF=1 的代码不能往 EP 0x83 发数据，IF=0 的代码也不能往 EP 0x81 发数据。
```

**规则 2：EP0 是共用的——设备级资源，不属于任何一个 Interface**

所有 Interface 的控制传输都走 EP0。发 XU 命令时 bmRequestType 选 Interface，wIndex 指定 Interface 号——但数据物理上从同一个 EP0 流过。类比：EP0 是小区的唯一大门，Interface 是门牌号。

**规则 3：同一个 Interface 的不同 Alternate Setting 可以复用端点号**

```
Interface 1 (VS):
  Alternate 0:  EP 0x81 (Bulk)        ← 取流时激活
  Alternate 2:  EP 0x81 (Isochronous)  ← 也可以声明相同 EndpointID
  Alternate 3:  EP 0x81 (Isochronous)  ← 因为同时只有一个 Alt 生效
```

**规则 4：两个不同的 Interface 不能声明同一个 EndpointID**

USB 规范禁止此行为——每个端点地址在一个 Configuration 内必须唯一。

### 真实设备数据验证（HIK 2bdf:0101）

```
USB View 报告:
  Used Endpoints: 3              ← EP0 + EP 0x83 + EP 0x81
  Number of open Pipes: 2        ← 用户态看到 2 个数据管道
  Pipe[0]: EP3  IN  Interrupt    ← 属于 IF=0 (VC)
  Pipe[1]: EP1  IN  Bulk         ← 属于 IF=1 (VS)
```

### 描述符树中的接口-端点层级

```
Device Descriptor
 └── Configuration Descriptor
      ├── Interface Descriptor (IF=0, VC)
      │    ├── VC Header Descriptor
      │    ├── Input Terminal Descriptor
      │    ├── Processing Unit Descriptor
      │    ├── Extension Unit Descriptor          ← XU 在这里
      │    ├── Output Terminal Descriptor
      │    └── Endpoint Descriptor (EP 0x83, IN, Interrupt)
      │
      └── Interface Descriptor (IF=1, VS, Alternate 0)
           ├── VS Input Header Descriptor
           │    bEndpointAddress: 0x81            ← 指向数据端点
           ├── Format Descriptor ×3
           ├── Frame Descriptor ×N
           └── Endpoint Descriptor (EP 0x81, IN, Bulk)
```

> VS Input Header 里的 `bEndpointAddress=0x81` 只是一个"指针"，告诉 Host "数据会从 EP 0x81 过来"。真正的端点属性在 Endpoint Descriptor。

### libusb 中的体现

```c
// 通过 Interface 发控制命令 — 走 EP0
libusb_claim_interface(devh, 0);          // claim Video Control 接口
libusb_control_transfer(devh, ...);       // 走 EP0，wIndex=(XU_ID<<8)|0

// 通过 Endpoint 读数据 — 走具体端点
libusb_claim_interface(devh, 1);          // claim Video Streaming 接口
libusb_bulk_transfer(devh, 0x81, ...);    // 走 EP 0x81，不需要接口号
```

**claim 接口 → 获得接口下所有端点的使用权。** 传输时直接用端点地址——不需要重复指定接口号，因为端点地址已经是全局唯一的。

---

## 2.2a 补充：EP0 的 64 字节 vs Bus Hound 的 512 字节

> 核心问题：HS 下 EP0 最大包只有 64 字节，为什么 Bus Hound 抓包显示一包 512 字节？

### 两种可能

**可能一（最常见）：看到的是 VS 端点，不是 EP0**

```
VC Interface (bInterfaceNumber=0)
  └─ EP0 (控制端点)              ← XU 命令、枚举走这里，HS=固定 64B

VS Interface (bInterfaceNumber=1)
  └─ Bulk IN Endpoint (0x81)     ← 视频数据走这里，HS=max 512B
```

| 端点类型 | HS 最大包 | 你在哪看到 |
|----------|:--------:|-----------|
| EP0（控制） | **64（固定）** | XU 命令、枚举 |
| Bulk Endpoint | **512** | 取流视频数据 |
| ISOC Endpoint | **1024** | 等时视频流 |

**可能二：Bus Hound 把多个 64B 事务合并显示为一行**

控制传输 DATA 阶段 512 字节 = USB 总线上 8 个 64B 事务（512÷64=8），每个都有独立的 Token + DATA + ACK。但 Bus Hound 工作在 URB 层，把驱动的一次完整请求合并显示：

```
Bus Hound 看到的：              USB 总线真实发生的：
┌──────────────────────┐      ┌────────────────────────────┐
│ CTL   8 bytes        │ ←──→ │ SETUP Token + DATA0(8B)    │
│ IN    512 bytes      │ ←──→ │ IN Token + DATA0(64B)+ACK  │ ×1
│                      │      │ IN Token + DATA1(64B)+ACK  │ ×2
│                      │      │ ... (DATA0/DATA1 交替) ... │ ×3~7
│                      │      │ IN Token + DATA1(64B)+ACK  │ ×8
│                      │      │ OUT Token + DATA1(0B)      │ STATUS
└──────────────────────┘      └────────────────────────────┘
```

**Bus Hound 一行 `IN 512` = 总线上 9 个事务！**

### 核心认知

- **Bus Hound 是 URB 层抓包**，不是总线层——它显示驱动的一次完整请求，不暴露底层包拆分
- **EP0 固定 64B（HS）不变**
- **区分方法**：看 Bus Hound 行里标注的端点地址——端点 0x00 → EP0 合并显示；0x81/0x82… → 非 EP0，512 是真实单包大小
- 这是 HANDOFF §六 第 27 条的延伸——STATUS 阶段不显示，DATA 阶段的包拆分也给合并了

---

## 2.4 四种传输类型全景

| 维度 | 控制 | 中断 | 批量 | 等时 |
|------|:---:|:---:|:---:|:---:|
| 可靠性 | ✅ ACK+重试 | ✅ ACK+重试 | ✅ ACK+重试 | ❌ 无握手 |
| 延迟保证 | 不保证 | ✅ bInterval | ❌ | ✅ 带宽保留 |
| 带宽保证 | 10%保留 | 有限保留 | ❌ 吃剩饭 | ✅ 预约 |
| 方向 | 双向 | 单向 | 单向 | 单向 |
| 管道 | 消息管道 | 流管道 | 流管道 | 流管道 |
| LS支持 | ✅ | ✅ | ❌ | ❌ |
| HS最大包 | 64 | 1024 | 512 | 1024 |
| 典型设备 | 所有设备 | 键盘/鼠标 | U盘/串口 | 摄像头/音频 |

### 帧内带宽分配优先级

```
等时(最高) → 中断 → 控制(至少10%) → 批量(吃剩饭)
```

### 选型: 中断 vs 批量

| 维度 | 中断 | 批量 |
|------|------|------|
| 延迟 | 有保证 | 无保证 |
| 数据量 | 小 | 大 |
| CPU | 必须定期轮询 | 按需 |
| 用途 | 状态/按键/传感器 | 文件/串口流 |

---

## 2.5 传输/事务/包 三层映射

### 核心公式

```
1 Transfer (传输) = N 个 Transaction (事务)
1 Transaction (事务) = 最多 3 个 Packet (包)
```

### 每种传输的事务模式

| 传输类型 | 事务组成 | Token | Data | Handshake |
|----------|---------|-------|------|-----------|
| 控制 | SETUP + [DATA×N] + STATUS | SETUP/IN/OUT | ✅ | ✅ |
| 中断IN | 1个IN事务 | IN | ✅ | ✅ |
| 中断OUT | 1个OUT事务 | OUT | ✅ | ✅ |
| 批量IN | 1个IN事务 | IN | ✅ | ✅ |
| 批量OUT | 1个OUT事务 | OUT | ✅ | ✅ |
| 等时IN | 1个IN事务 | IN | ✅ | ❌ |
| 等时OUT | 1个OUT事务 | OUT | ✅ | ❌ |

### DATA0/DATA1翻转

- 端点初始化→Toggle=DATA0
- 每成功传输(收到ACK)→Toggle翻转
- 收到NAK→Toggle不翻转
- 接收方检测Toggle不匹配→知道是重传→回ACK但丢数据
- 目的：区分"Host重发"和"Host发了相同内容"

---

## 2.6 ⛁ PID 编码表

### PID 8位结构

```
Bit7~Bit4 = ~Bit3~Bit0 (按位取反)

例: ACK
  低4位(类型码) = 0010 (0x2)
  高4位(校验)   = 1101 (~0010)
  完整PID       = 1101 0010 = 0xD2
```

错误检测：高4位≠~低4位→PID损坏→忽略整个包

### PID 低2位分类

```
Bit1-0 = 00 → SPECIAL类
Bit1-0 = 01 → TOKEN类
Bit1-0 = 10 → HANDSHAKE类
Bit1-0 = 11 → DATA类
```

### 16种PID全集

**TOKEN类：**

| PID | 低4位 | 完整(hex) | 含义 |
|-----|-------|-----------|------|
| OUT | 0001 | 0xE1 | Host→Device数据 |
| IN | 1001 | 0x69 | Host←Device数据 |
| SOF | 0101 | 0xA5 | 帧起始 |
| SETUP | 1101 | 0x2D | 控制传输SETUP阶段 |

**DATA类：**

| PID | 低4位 | 完整(hex) | 含义 |
|-----|-------|-----------|------|
| DATA0 | 0011 | 0xC3 | 翻转位=0 |
| DATA1 | 1011 | 0x4B | 翻转位=1 |
| DATA2 | 0111 | 0x87 | HS等时微帧多包 |
| MDATA | 1111 | 0x0F | HS等时Split |

**HANDSHAKE类：**

| PID | 低4位 | 完整(hex) | 含义 |
|-----|-------|-----------|------|
| ACK | 0010 | 0xD2 | 正确接收 |
| NAK | 1010 | 0x5A | 暂时忙/无数据 |
| STALL | 1110 | 0x1E | 端点Halted/请求不支持 |
| NYET | 0110 | 0x96 | HS批量OUT: FIFO满了(PING协议) |

**SPECIAL类：**

| PID | 低4位 | 完整(hex) | 含义 |
|-----|-------|-----------|------|
| PRE | 1100 | 0x3C | LS Preamble |
| ERR | 1100 | 0x3C | Split Transaction出错 |
| SPLIT | 1000 | 0x78 | HS Split开始 |
| PING | 0100 | 0xB4 | HS批量OUT流控探测 |
| EXT | 0000 | 0xF0 | 扩展PID(保留) |

---

## 2.7 ⛁ Token 包逐位解析

### IN/OUT/SETUP Token (24 bits)

```
SYNC(8b) | PID(8b) | ADDR(7b) | ENDP(4b) | CRC5(5b) | EOP(3b)
```

### SYNC字段 (8 bits)

`00000001` (0x80, LSB first)

7个0→NRZI连续7次跳变→接收方PLL锁定时钟
最后1→停止跳变→标志SYNC结束

### ADDR字段 (7 bits)

范围 0x00~0x7F (0~127)。0x00 = 默认地址(Default Address)，0x01~0x7F = 可分配地址。

### ENDP字段 (4 bits)

范围 0~15。方向由PID决定(IN PID=读, OUT PID=写)。EP3 IN和EP3 OUT是硬件上两个不同的FIFO。

### CRC5字段 (5 bits)

多项式: G(x) = x⁵ + x² + 1 (100101 = 0x25)。校验范围: ADDR(7b) + ENDP(4b) = 11 bits。

### SOF Token (结构不同)

```
SYNC(8b) | PID=SOF(0xA5) | Frame Number(11b) | CRC5(5b) | EOP
```

Frame Number: 0~2047。FS: 1帧=1ms→~2秒回卷。HS: 1微帧=125μs→256ms回卷。

---

## 2.8 ⛁ Data 包逐位解析

### 结构

```
SYNC(8b) | PID(8b) | DATA(0~1024B) | CRC16(16b) | EOP(3b)
```

### CRC16

多项式: G(x) = x¹⁶ + x¹⁵ + x² + 1，截断多项式: 0x8005。校验范围: DATA字段全部字节。

### 短包终止

数据长度 < MaxPacketSize → 短包 = 传输结束信号。如果恰好等于MaxPacketSize → 追加零长度DATA包标记结束。

---

## 2.9 ⛁ Handshake 包逐位解析

### 结构（USB最短的包）

```
SYNC(8b) | PID(8b) | EOP(3b)
```

没有DATA、没有CRC。PID自身的高4位=~低4位校验已足够。

### ACK (0xD2)

数据被正确接收(CRC正确、PID校验正确、Toggle匹配)。发送方翻转Toggle，事务完成。

### NAK (0x5A)

暂时忙/无数据: FIFO空(IN)或FIFO满(OUT)。Toggle不翻转，发送方稍后重试。**不是错误**，是正常流控。NAK总是Device给Host的。

### STALL (0x1E)

端点Halted或请求不支持。需要软件干预(CLEAR_FEATURE)。NAK="等等再来" vs STALL="别试了，需要人来修"。

### NYET (0x96, HS only)

HS批量OUT: 数据收了但FIFO满了。PING协议的一部分：Host先PING确认空间→再发OUT数据。

### ERR (0x3C, HS only)

Hub在Split Transaction中向Host报告错误。SDK一般不直接处理。

---

## 2.10 控制传输逐事务拆解

### 三阶段模型

```
必含: SETUP + STATUS
可选: DATA (wLength=0则跳过)
```

### SETUP阶段

```
固定结构，一个SETUP事务:
Host → SETUP Token (0x2D, ADDR, EP0)
Host → DATA0 (8B SETUP包)
Host ← ACK (设备必须ACK! 不能NAK)
```

### SETUP包8字节

| 偏移 | 字段 | 大小 | 示例(GET_DESCRIPTOR) |
|------|------|------|---------------------|
| +0 | bmRequestType | 1B | 0x80 (D2H, Standard, Device) |
| +1 | bRequest | 1B | 0x06 (GET_DESCRIPTOR) |
| +2 | wValue | 2B | 0x0100 (Device Desc, Index=0) |
| +4 | wIndex | 2B | 0x0000 |
| +6 | wLength | 2B | 0x0012 (18 bytes) |

### DATA阶段

方向由bmRequestType Bit7决定:
- Bit7=1(Device→Host): DATA=IN事务系列
- Bit7=0(Host→Device): DATA=OUT事务系列
- wLength=0: 跳过DATA阶段

### STATUS阶段

- 方向总是跟DATA阶段相反
- 无DATA阶段时默认IN
- STATUS数据包永远是DATA1 (跟在最后DATA事务Toggle后面)
- 接收STATUS的那方必须回ACK→控制传输才正式闭环

### 三种类型

1. 控制读(Read): SETUP→DATA(IN)×N→STATUS(OUT)
2. 控制写(Write): SETUP→DATA(OUT)×N→STATUS(IN)
3. 无数据(No Data): SETUP→STATUS(IN)

### 长度不匹配处理

- 设备回的数据 < wLength: 短包自动终止
- 设备回的数据 = wLength但可更多: Host按wLength截断
- 所以GET_DESCRIPTOR(Config)要先读9B头→知wTotalLength→再读完整

---

## 2.11 中断传输逐事务拆解

### 基本结构

```
Host发IN Token→Device回应:
  有数据: DATA(1~64B FS/1~1024B HS)→Host ACK
  无数据: NAK (Host下个周期再问)
  出错:   STALL
```

### bInterval 延迟保证

Host保证在bInterval内至少服务一次中断端点。

```
LS/FS: bInterval = N ms
HS: 实际间隔 = 2^(bInterval-1) × 125μs

最快延迟: HS bInterval=1 → 125μs
典型鼠标: FS bInterval=10 → 10ms
```

### 中断OUT

存在但少用: HID键盘LED控制、游戏手柄力反馈。

---

## 2.12 批量传输逐事务拆解

### 帧内优先级

等时 > 中断 > 控制(≥10%) > 批量(吃剩饭)

### HS PING流控

```
FS/LS: 直接OUT→可能被NAK(浪费带宽)
HS: 先PING探测空间→ACK→再OUT→避免浪费

PING流程:
Host→PING Token→Device回ACK(有空间)/NAK(满)
ACK→OUT Token+DATA→Device回ACK/NYET
NYET: 数据收了但满了，下次先PING再发
```

### 理论吞吐

HS: 13×512B/125μs ≈ 53.2 MB/s (理论)
实际: 20-35 MB/s (协议开销+其他传输占用)
USB 3.0 SS: 理论400+MB/s

### 结束条件

1. 客户端指定了传输长度
2. 短包终止 (< MaxPacketSize)
3. 零长度包 (设备不想NAK)

---

## 2.13 等时传输逐事务拆解

### 基本结构（无握手包！）

```
IN:  Host→IN Token ←DATA (结束!)
OUT: Host→OUT Token→DATA (结束!)
```

没有ACK, 没有NAK, 没有STALL。

### 为什么不要握手

实时>可靠性: 30fps视频(33ms/帧), 重传延迟比丢几帧更致命。人脑对5-10%帧丢失不敏感，但对>50ms延迟非常敏感。

### 带宽预约

枚举时Host检查是否有足够带宽。带宽不够→Set_Configuration失败→设备不可用。

### HS微帧多包

```
一个微帧最多3包:
IN+DATA2(1024B)→IN+DATA1(1024B)→IN+DATA0(1024B)
= 3072B/125μs ≈ 24.6 MB/s
```

### 同步类型

bmAttributes Bit2-3:
- 00=Asynchronous (异步, 各走各时钟, 如USB音箱)
- 01=Adaptive (自适应, 如USB话筒)
- 10=Synchronous (同步, 锁定SOF, 如UVC摄像头)

---

## 2.14 SOF 包与帧结构

### SOF包结构

```
SYNC(8b) | PID=SOF(0xA5) | Frame Number(11b) | CRC5(5b) | EOP(3b)
```

SOF是广播包(没有ADDR/ENDP)，总线上所有设备都收到。

### Frame Number = 0~2047

```
FS: 1帧=1ms→Frame Number每ms+1→~2.048秒回卷
HS: 1微帧=125μs→每125μs发SOF→但Frame Number每1ms才+1
    8个微帧=1ms=1个HS帧
    设备自己计微帧号(0~7)
```

### SOF时间精度

FS: 1ms ± 500ns；HS: 125μs ± 62.5ns。USB总线上最精确的时间参考。

### 帧内调度

```
SOF→等时→中断→控制→批量→SOF(下一帧)
```

### Suspend检测

连续3ms(FS)或3个微帧(HS)没看到SOF→设备进入Suspend→电流≤2.5mA

---

## 2.15 HS 高速模式补充

### 微帧结构

8个微帧=1ms HS帧。μF0~μF7，Frame Number相同，下一组μF0的Frame Number+1。

### Split Transaction

**问题**: HS Hub后挂FS/LS设备，Hub必须做速度翻译。

**解法**: Split Transaction (两阶段)

#### Phase 1: Start-Split (SSPLIT)

Host→SSPLIT Token→Hub翻译成FS/LS信号→跟FS/LS设备交互→数据暂存Hub缓冲区

#### Phase 2: Complete-Split (CSPLIT)

Host→CSPLIT Token→Hub返回之前暂存的数据

### 时间线示例（FS鼠标在HS Hub后）

```
μF0: SSPLIT → Hub翻译→FS鼠标NAK
μF1: CSPLIT → Hub报告NAK(没数据)
μF2: SSPLIT → Hub翻译→FS鼠标DATA(按键!)
μF3: CSPLIT → Hub→DATA→Host拿到按键数据
```

从按下到Host拿到 ≈ 4微帧 = 500μs

---

## 2.16 USB 3.x SuperSpeed 概览

### 双总线架构

USB 3.0端口 = USB 2.0总线 + SuperSpeed总线 (并行运行，互不抢占)

### 广播式 vs 路由式

```
USB 2.0: Host喊一嗓子，所有设备都听→功耗随设备数增加
USB 3.0: 路由式转发→只有目标设备接收→功耗常数
```

### LTSSM (Link Training and Status State Machine)

USB 3.0引入链路层状态机:
Rx.Detect→Polling→Training→U0(正常工作)
省电: U1(浅眠,~μs) / U2(深眠,~ms) / U3(Suspend)

### USB 2.0 vs 3.0 核心对比

| 维度 | USB 2.0 | USB 3.x |
|------|---------|---------|
| 拓扑 | 广播式 | 路由式 |
| 编码 | NRZI | 8b/10b→128b/132b |
| 流控 | NAK/NYET/PING | 链路层信用(Credit-based) |
| 链路管理 | SE0复位 | LTSSM状态机 |
| 中断 | 定期轮询 | 设备可主动发ERDY |
| EP0 | 64B | 512B |

---

## 补充问答一：传输方向深度辨析

### Q1: 控制传输的"双向"是全双工吗？另外三种是半双工吗？

**USB 总线物理层本身就是半双工的。** D+/D- 只有一对差分线，同一时刻只能有一个方向的数据在线上传输。

**控制传输的"双向"不是同时收发**，而是指 EP0 这个端点既能收也能发，收发分阶段串行执行：

```
控制读 (Host 读 Device 描述符):
  阶段1 SETUP: Host → Device  (OUT方向)
  阶段2 DATA:   Host ← Device  (IN方向，Device回数据)
  阶段3 STATUS: Host → Device  (OUT方向，Host确认)
```

STATUS 阶段的方向永远跟 DATA 阶段相反——这是协议规定，不是硬件能力。

**中断/批量/等时端点的"单向"是端点层面的：** 它们是两个物理上不同的 FIFO 缓冲区。即使端点号相同，EP3 IN 和 EP3 OUT 是两段独立的硬件 FIFO。

| 层面 | 全双工/半双工 | 说明 |
|------|:---:|------|
| USB 总线（物理层） | 半双工 | D+/D- 只有一对 |
| 控制传输 EP0 | 半双工，但双向 | 分阶段切换方向 |
| 中断/批量/等时端点 | 单向 | 硬件上方向固定，双向需两个端点 |

### Q2: 每个端点是做什么功能的，由谁决定？

决定权在**设备（Device）**这边，分两个层面：

**层面一：硬件设计时（芯片设计师决定）** — 端点的数量、类型、方向、FIFO 大小是芯片设计时硬件决定的。芯片流片之后这些就不能改了。

**层面二：枚举时（设备固件通过描述符告诉 Host）** — Host 读描述符 → 知道 EP1 是中断 IN → 以后按这个规矩发 Token。Host 不能"自作主张"给 EP1 发批量传输。

**最终话事权 = 设备（硬件+固件）。Host 只是被动接受者。**

### Q3: Token 在每种传输的事务中起什么作用？

Token 是 USB 总线上**每一笔事务的起始信号**，由 Host 发出。作用：

> "第 X 号设备，你的第 Y 号端点，接下来我们要收/发数据了。"

| 字段 | 作用 | 例 |
|------|------|-----|
| PID | 告诉设备**要干什么**：IN(发数据)、OUT(收数据)、SETUP(命令来了) | `0x69` = IN |
| ADDR | 总线上 127 个设备，**喊哪一个** | `0x03` = 设备 3 |
| ENDP | 那个设备的 16 个端点，**用哪个** | `0x1` = EP1 |

类比：Token = 课堂上老师点名。**"张三（ADDR），把你的作业交上来（IN，ENDP）。"** 没被点名的人不说话。

| Token 类型 | 含义 | 谁发 | 后面发生什么 |
|------------|------|------|-------------|
| **SETUP** | "我要发控制命令" | Host | DATA0(8B命令) → 设备 ACK |
| **IN** | "你发数据给我" | Host | 设备回 DATA / NAK / STALL |
| **OUT** | "我发数据给你" | Host | Host 发 DATA → 设备 ACK/NAK/STALL |
| **SOF** | "新一帧开始了" | Host | 广播，全总线都听，不回应 |

---

## 补充问答二：SOF Token 和 SETUP Token 的区别

| 维度 | SOF Token | SETUP Token |
|------|-----------|-------------|
| **目标** | **广播**（全体设备） | **点对点**（特定设备 + EP0） |
| **包含 ADDR/ENDP** | ❌ 不包含 | ✅ ADDR(7) + ENDP(4) |
| **特有字段** | Frame Number(11 bit) | 无（地址和端点替代） |
| **触发动作** | 设备据此同步帧计时 | 设备必须接受后续 DATA0（8 字节 Setup Packet） |
| **发送频率** | FS: 每 1ms 一次；HS: 每 125μs 一次 | 只在控制传输开始时发一次 |
| **PID 值** | `0xA5` | `0x2D` |

**SOF = 心跳 / 时钟信号。** 广播形式，不带地址，总线上的所有设备都收到。两个作用：(1)让设备知道帧边界，做时间同步；(2)防止设备进入 Suspend 状态。

**SETUP = 点名 + 命令开启。** 控制传输的"起手式"，必须指向特定设备的 EP0。

---

## 补充问答三：为什么 SETUP 事务必须 ACK，不能 NAK？

### 三个根因

**根因一：SETUP 是状态机清零信号。** SETUP Token 一到达设备，USB 硬件自动：(1)清空之前未完成的控制传输状态；(2)强制复位 Data Toggle（永远用 DATA0 包）。

**根因二：EP0 的硬件保证——SETUP 缓冲永远可用。** EP0 必须预留专用的 SETUP 缓冲区（通常 8 字节 FIFO），跟普通数据 FIFO 是分离的。

**根因三：USB 协议不允许 SETUP 重试的语义。** SETUP 上的很多请求不是幂等的（比如 SetConfiguration()），重试会制造歧义。

### SETUP 异常处理

| 情况 | 设备行为 | Host 处理 |
|------|---------|----------|
| SETUP 包 CRC 校验错 | **静默丢弃**（不响应任何东西） | 超时，判定总线错误，重发 SETUP 事务 |
| SETUP 包正确、但设备不支持该命令 | DATA 阶段正常走完，**STATUS 阶段返回 STALL** | Host 收到 STALL，知道"设备不支持这个命令" |
| SETUP 包正确、固件来不及处理 | 硬件自动 ACK（不依赖固件） | Host 继续发送下一个事务 |

> 即使设备不支持 SETUP 里的命令，SETUP 阶段本身也照样 ACK。拒绝发生在 STATUS 阶段用 STALL 表达。

---

## 补充问答四：127 个设备一帧照顾得过来吗？

### 理论极限

FS（12Mbps）下，一帧 = 1ms = 12,000 bit times。一个最小事务（IN Token → NAK）约 60 bit times。127 × 60 + SOF(35) ≈ 7,655 bit times。**理论上有余量。**

### 但纯 NAK 毫无意义

| 事务类型 | 典型大小 | 单次耗时 | 127 个设备总耗时 |
|---------|---------|---------|----------------|
| IN + NAK | 0 字节 | ~60 bit times | ~7,655 ✅ 勉强 OK |
| IN + DATA + ACK（鼠标 8B） | 8 字节 | ~200 bit times | ~25,400 ❌ 2 帧多 |
| 批量 OUT + 512B + ACK | 512 字节 | ~4,300 bit times | ~546,000 ❌ 45 帧 |

### 制约机制

1. **带宽分配机制**：等时/中断预留 ≤ 90%，Host 在枚举阶段就会算账——带宽不够直接拒绝 Set_Configuration
2. **供电**：一个 Root Hub 只出 500mA（5 个 unit load），127 个设备全 Bus-powered 需要 12.7A
3. **Hub 层级**：USB 最多 5 层 Hub
4. **实用场景**：大部分设备大部分时间在静默

**结论：127 是地址空间的上限，不是并发能力的承诺。**

---

# 第三篇：USB 描述符体系 — 逐字节解剖

---

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

### 每个描述符的前 2 字节铁律

```
Byte 0: bLength        — 本描述符的长度（字节数）
Byte 1: bDescriptorType — 描述符类型码（1 字节枚举值）
```

Host 拿到描述符链后，先读 `bLength` 知道多大，再读 `bDescriptorType` 知道是什么类型，然后决定怎么解析剩余的字节。

### 常见类型码速查

| bDescriptorType | 名称 |
|:---:|------|
| 0x01 | Device Descriptor |
| 0x02 | Configuration Descriptor |
| 0x03 | String Descriptor |
| 0x04 | Interface Descriptor |
| 0x05 | Endpoint Descriptor |
| 0x06 | Device Qualifier Descriptor |
| 0x07 | Other Speed Configuration |
| 0x0B | Interface Association Descriptor (IAD) |
| 0x0F | BOS Descriptor |

### 描述符链的内存布局

Host 用 `Get_Descriptor(Configuration)` 请求读回的不是单个描述符，而是一条**描述符链**——把 Configuration + Interface + Endpoint + 类专用描述符全部串联成一个连续数据块。Host 从头开始，遇到一个描述符读 `bLength`，跳过 `bLength` 字节就是下一个描述符。

### MQTT 类比

| USB 描述符 | MQTT 类比 |
|------------|-----------|
| Device Descriptor | CONNECT 报文 |
| Configuration Descriptor | 设备 Topic 权限声明 |
| Interface Descriptor | 每个 Topic 的 QoS 定义 |
| Endpoint Descriptor | TCP 连接参数 |
| `bLength + bDescriptorType` 前 2 字节铁律 | MQTT Fixed Header 第一个字节 |

---

## 补充问答一：端点和接口的区别

| 维度 | Endpoint（端点）| Interface（接口）|
|------|-----------------|-------------------|
| **本质** | 硬件 FIFO 缓冲区 | 逻辑功能分组 |
| **数量** | 每设备 0~16 个（不含 EP0）| 每配置 1~N 个 |
| **包含关系** | 属于某个 Interface | 包含多个 Endpoint |
| **标识** | `bEndpointAddress`（bit7=方向 + bit3~0=端点号）| `bInterfaceNumber`（0, 1, 2...）|

**一句话：Interface 回答"我能干什么"，Endpoint 回答"数据从哪走"。**

### 类码三级分类体系

```
bInterfaceClass      (1 byte) — "大类是什么"
bInterfaceSubClass   (1 byte) — "大类下的哪个子类"
bInterfaceProtocol   (1 byte) — "用什么协议变体"
```

| 设备 | bInterfaceClass | bInterfaceSubClass | bInterfaceProtocol |
|------|:---:|:---:|:---:|
| USB 鼠标 | 0x03 (HID) | 0x01 (Boot Interface) | 0x02 (Mouse) |
| USB 键盘 | 0x03 (HID) | 0x01 (Boot Interface) | 0x01 (Keyboard) |
| CDC 虚拟串口 | 0x02 (CDC) | 0x02 (ACM) | 0x01 (AT Commands) |
| U 盘 | 0x08 (Mass Storage) | 0x06 (SCSI) | 0x50 (Bulk-Only) |
| UVC 摄像头 | 0x0E (Video) | 0x01 (Video Control) | 0x00 |
| 音频耳机 | 0x01 (Audio) | 0x01 (Audio Control) | 0x00 |

---

## 3.2 ⛁ Device Descriptor — 18 字节逐位解剖

这是 Host 读到的**第一个描述符**。

### 逐字段表格

| 偏移 | 字段 | 大小 | 含义 | 示例值（SanDisk U盘） |
|------|------|------|------|------|
| 0 | bLength | 1 | 固定 0x12 (18) | 0x12 |
| 1 | bDescriptorType | 1 | 固定 0x01 | 0x01 |
| 2-3 | bcdUSB | 2 | USB 协议版本(BCD) | 0x0200 |
| 4 | bDeviceClass | 1 | 设备级类码(0x00=看Interface) | 0x00 |
| 5 | bDeviceSubClass | 1 | 设备级子类 | 0x00 |
| 6 | bDeviceProtocol | 1 | 设备级协议 | 0x00 |
| 7 | bMaxPacketSize0 | 1 | EP0最大包大小 | 0x40 (64) |
| 8-9 | idVendor | 2 | 厂商ID(USB-IF分配) | 0x0781 |
| 10-11 | idProduct | 2 | 产品ID(厂商自定) | 0x5591 |
| 12-13 | bcdDevice | 2 | 固件版本(BCD) | 0x0100 |
| 14 | iManufacturer | 1 | 制造商字符串索引 | 0x01 |
| 15 | iProduct | 1 | 产品字符串索引 | 0x02 |
| 16 | iSerialNumber | 1 | 序列号字符串索引(0=无) | 0x03 |
| 17 | bNumConfigurations | 1 | 配置数 | 0x01 |

### 关键字段深入

**bDeviceClass = 0x00**：分类权下放到 Interface 层——最常见。复合设备必须用 0x00。如果设备用 IAD，设备级必须写 0xEF（Miscellaneous）。

**bMaxPacketSize0**：LS=8, FS可选8/16/32/64, HS=固定64。Host 枚举时靠这个值知道后续怎么拆包。

**iManufacturer/iProduct/iSerialNumber**：不是字符串本身，是索引号。0x00 表示空。实际字符串是 UNICODE 编码，存在独立的 String Descriptor 里。

### 完整 HEX dump 示例（SanDisk U盘）

```
Offset: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11
  Hex: 12 01 00 02 00 00 00 40 81 07 91 55 00 01 01 02 03 01

逐字节对照：
  12       = bLength (18)
  01       = bDescriptorType (Device)
  00 02    = bcdUSB (2.0, LE)
  00       = bDeviceClass (0→看Interface)
  40       = bMaxPacketSize0 (64)
  81 07    = idVendor (0x0781 = SanDisk, LE)
  91 55    = idProduct (0x5591)
  01       = iManufacturer
  02       = iProduct
  03       = iSerialNumber
  01       = bNumConfigurations (1)
```

### ⚠️ Little-Endian 陷阱

2 字节字段在 USB 总线上是 Little-Endian：`81 07` 实际值是 `0x0781`，不是 `0x8107`。

---

## 3.3 bcdUSB 的 BCD 编码细节

BCD = Binary-Coded Decimal，每个 nibble（4 bit）表示一个十进制数字（0~9）。

```
bcdUSB = 0xJJMN（16 bit = 4 nibble）
          JJ = 主版本号, M = 次版本号, N = 子次版本号
```

| bcdUSB 值 | 含义 | nibble 拆开 |
|:---------:|------|:-----------:|
| `0x0100` | USB 1.0 | JJ=01, M=0, N=0 |
| `0x0110` | USB 1.1 | JJ=01, M=1, N=0 |
| `0x0200` | USB 2.0 | JJ=02, M=0, N=0 |
| `0x0300` | USB 3.0 | JJ=03, M=0, N=0 |
| `0x0310` | USB 3.1 | JJ=03, M=1, N=0 |

---

## 3.4 ⛁ Configuration Descriptor — 9 字节逐位解析

### 逐字段表格

| 偏移 | 字段 | 大小 | 含义 | 示例 |
|------|------|------|------|------|
| 0 | bLength | 1 | 固定 0x09 | 0x09 |
| 1 | bDescriptorType | 1 | 固定 0x02 | 0x02 |
| 2-3 | wTotalLength | 2 | **整条描述符链总长** | 0x002E (46) |
| 4 | bNumInterfaces | 1 | 接口总数 | 0x02 |
| 5 | bConfigurationValue | 1 | 配置编号(Set_Configuration用) | 0x01 |
| 6 | iConfiguration | 1 | 配置字符串索引(0=无) | 0x00 |
| 7 | bmAttributes | 1 | 属性位图 | 0x80 |
| 8 | bMaxPower | 1 | 总线最大电流，单位 2mA | 0xFA (500mA) |

### bmAttributes 位图

```
Bit 7: 保留，必须写 1
Bit 6: 0=总线供电 / 1=自供电
Bit 5: 0=不支持远程唤醒 / 1=支持Remote Wakeup
Bit 4-0: 保留，写 0

常见组合:
  0x80 = 总线供电、无远程唤醒
  0xC0 = 总线供电、有远程唤醒（键盘/鼠标）
  0xA0 = 自供电、无远程唤醒
```

### bMaxPower

单位是 2mA：`bMaxPower × 2mA = 实际最大总线电流`。Host 会算账——如果 Hub 的剩余供电不够，拒绝 `Set_Configuration`。

---

## 3.5 ⛁ Interface Descriptor — 9 字节逐位解析

| 偏移 | 字段 | 大小 | 含义 | 示例(HID鼠标) |
|------|------|------|------|------|
| 0 | bLength | 1 | 固定 0x09 | 0x09 |
| 1 | bDescriptorType | 1 | 固定 0x04 | 0x04 |
| 2 | bInterfaceNumber | 1 | 接口编号 | 0x00 |
| 3 | bAlternateSetting | 1 | 备选设置号 | 0x00 |
| 4 | bNumEndpoints | 1 | 端点个数（不含EP0） | 0x01 |
| 5 | bInterfaceClass | 1 | 接口类码 | 0x03 (HID) |
| 6 | bInterfaceSubClass | 1 | 接口子类码 | 0x01 (Boot) |
| 7 | bInterfaceProtocol | 1 | 协议码 | 0x02 (Mouse) |
| 8 | iInterface | 1 | 字符串索引 | 0x00 |

### Alternate Setting 全面解析

> Alternate Setting 允许同一个 Interface 在不同时刻以不同的"配置档"运行——切换端点数量、传输类型、带宽分配，但不改变功能类别。

**最熟悉的例子：你的热成像摄像头**

```
Interface 1 (Video Streaming, bInterfaceClass=0x0E Video)
│
├── Alternate Setting 0  ← 默认状态，"零带宽"
│   bNumEndpoints: 0       （没有数据端点）
│   用途：关流/待机
│
├── Alternate Setting 1  ← 等时传输，160x120
│   Endpoint: EP 0x81, Isochronous, 256B
│
├── ...Alternate 2~7...  ← 其他分辨率/帧率组合
│
└── Alternate Setting 8  ← 批量传输
    Endpoint: EP 0x81, Bulk, 512B
```

所有 Alternate 0~8 都属于 Interface 1（bInterfaceNumber 相同），功能都是"传视频"。但 Alt 0 关流省带宽，Alt 8 开 Bulk 传数据——同一个接口，完全不同端点配置。

**类比：同一扇门的不同开法**

```
Alt 0：门关着 — 不传数据，不占带宽
Alt 1：门开着，一次过 256B — ISOC 低分辨率
Alt 8：门开着，一次过 512B — Bulk 高吞吐
```

门还是那扇门（IF=1），开法不同。SET_INTERFACE 切换时总线不断开、描述符不用重读。

**和 Configuration 切换的区别**

| | Alternate Setting | Configuration |
|---|---|---|
| 切换范围 | 一个 Interface 内部 | 整个设备 |
| 切换方式 | **SET_INTERFACE** | Set_Configuration |
| 其他 Interface 受影响？ | **不影响** | 全部重置 |
| 典型用途 | 开关流、换分辨率 | 切换工作模式 |
| 切换速度 | 快（局部调整） | 慢（全局重构） |

**为什么需要 Alternate Setting？——带宽管理**

等时传输预约的带宽即使不用也占着。如果摄像头关流后还占着等时带宽，纯浪费。**UVC 规范强制 Alt 0 为零带宽**（bNumEndpoints=0）——关流时切 Alt 0 释放带宽给其他设备。

**在代码里的体现：SET_INTERFACE**

```c
// SET_INTERFACE 是 Standard 请求，不是 Class 请求！
libusb_control_transfer(devh,
    0x01,           // bmRequestType = Standard, OUT, Interface
    0x0B,           // bRequest = SET_INTERFACE
    0x08,           // wValue = Alternate Setting 8
    0x01,           // wIndex = Interface 1 (VS) — 不拼 Unit ID！
    NULL, 0, 5000);
```

**关键认知**

- Alternate Setting 不是新 Interface——bInterfaceNumber 不变
- 同时只有一个 Alternate 生效——切 Alt 8 后 Alt 0 自动失效
- 不同 Alternate 可复用端点号——同时只有一个激活，不冲突（规则 3）
- Alt 0 = 零带宽是 UVC 强制的——核心带宽管理机制

---

## 3.6 ⛁ Endpoint Descriptor — 7 字节逐位解析

| 偏移 | 字段 | 大小 | 含义 | 示例(HID鼠标) |
|------|------|------|------|------|
| 0 | bLength | 1 | 固定 0x07 | 0x07 |
| 1 | bDescriptorType | 1 | 固定 0x05 | 0x05 |
| 2 | bEndpointAddress | 1 | bit7=方向 + bit3-0=端点号 | 0x81 (EP1, IN) |
| 3 | bmAttributes | 1 | bit1-0: 传输类型 | 0x03 (中断) |
| 4-5 | wMaxPacketSize | 2 | 最大包长 | 0x0008 (8B) |
| 6 | bInterval | 1 | 轮询间隔 | 0x0A (10ms) |

### bEndpointAddress

```
Bit 7    : 方向 — 1=IN(Device→Host)  0=OUT(Host→Device)
Bit 6-4  : 保留，写 0
Bit 3-0  : 端点号 (0~15)

0x82 = 1000 0010 → IN, EP2
0x01 = 0000 0001 → OUT, EP1
```

### bmAttributes — 传输类型

```
Bit 1-0: 00=控制  01=等时  10=批量  11=中断

常见值:
  0x03 = 中断传输（HID 鼠标/键盘）
  0x02 = 批量传输（U盘、CDC 数据）
  0x05 = 等时传输（UVC 视频流）
```

---

## 3.7 bInterval 在不同速率下的含义

bInterval 是 USB 描述符中**最容易被误解**的字段——同一个值在不同速率/传输类型下含义完全不同。

| 速率 | 传输类型 | 公式 | 单位 | 范围 |
|------|---------|------|------|------|
| FS | 中断 | bInterval | **ms** | 1~255 ms |
| LS | 中断 | bInterval | **ms** | 10~255 ms |
| FS | 等时 | 2^(bInterval-1) | **帧数 (ms)** | 1~16 ms |
| HS | 中断 | 2^(bInterval-1) | **微帧 (125μs)** | 125μs~4s |
| HS | 等时 | bInterval-1 | **微帧 (125μs)** | 125μs~16ms |
| 所有 | 批量 | 忽略 | — | 有空就来 |

### 常见错误

```c
// ❌ 错误：把所有传输类型当线性
uint16_t polling_ms = desc->bInterval;

// ✅ 正确：根据速度和类型用不同公式
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

---

## 3.8 ⛁ String Descriptor

### 结构（无固定长度）

```
Offset  Size  Field          含义
──────────────────────────────────────────────
  0      1     bLength        本描述符总字节数
  1      1     bDescriptorType 0x03
  2~N   可变   bString         UNICODE 字符串 (UTF-16LE)
```

英文/数字每个字符就是 `0x00 + ASCII码`——Unicode 前 128 个码点等于 ASCII。

### String Descriptor #0 是特例

存的是**语言 ID 列表**（LANGID）。Host 必须先读它才知道设备支持什么语言：

```
Host → Get_Descriptor(String, index=0)    → 设备回: [0x0409, ...]
Host → Get_Descriptor(String, index=2, langid=0x0409) → 产品名英文版
```

---

## 3.9 Device Qualifier + Other Speed Configuration

### 为什么需要

HS 设备插入 USB 1.1 端口 → 被降级到 FS。两种速度下参数不同：批量端点 512B→64B，bInterval 语义变了。

- **Device Qualifier (0x06, 10字节)**：告诉 Host "如果我在另一速度运行，设备描述符会怎么变"。只有能跑双速的设备才有。
- **Other Speed Configuration (0x07)**：整条配置链的"另一速度版本"。结构完全一样，只有端点参数按另一速度重写。

Host 的典型用法：设备以 HS 枚举完成后读 Qualifier，如果后面被移到 FS 端口，直接用备胎链配置——**无需重新枚举**。

---

## 3.10 BOS Descriptor

BOS = Binary Device Object Store。USB 3.0 引入的**扩展容器**。

### 解决什么问题

USB 2.0 的 Device Descriptor 是固定 18 字节。USB 3.0 需要宣告新能力（LPM、SuperSpeed 特性等），但不敢改 Device Descriptor 结构——改了老 Host 就不认识了。解决思路：加一个指针指向**可变长的扩展区**。

### 关键 Capability

**USB 2.0 Extension (LPM)**：`bmAttributes[0]=1` 表示支持 LPM Link Power Management，可以在 10μs 级别进出低功耗状态。

---

## 3.11 描述符类型码全集

### 标准描述符

| 值 | 宏名 | 描述符 | 固定长度？ |
|:--:|------|--------|:--:|
| 0x01 | `USB_DT_DEVICE` | Device | ✅ 18 字节 |
| 0x02 | `USB_DT_CONFIG` | Configuration | ✅ 9 字节 |
| 0x03 | `USB_DT_STRING` | String | ❌ 可变 |
| 0x04 | `USB_DT_INTERFACE` | Interface | ✅ 9 字节 |
| 0x05 | `USB_DT_ENDPOINT` | Endpoint | ✅ 7 字节 |
| 0x06 | `USB_DT_DEVICE_QUALIFIER` | Device Qualifier | ✅ 10 字节 |
| 0x07 | `USB_DT_OTHER_SPEED_CONFIG` | Other Speed Config | ✅ 9 字节（头）|
| 0x0B | `USB_DT_INTERFACE_ASSOCIATION` | IAD | ✅ 8 字节 |
| 0x0F | `USB_DT_BOS` | BOS | ✅ 5 字节（头）|

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

---

## 补充问答二：控制传输只能在 EP0 吗？

**是的，所有 USB 设备的控制传输只能在端点 0（EP0）上。** 这是 USB 规范从第一天就写死的硬规定。

UVC 的 VC（Video Control）接口名字里带 "Control"，容易让人以为控制命令走它下面的端点。但实际上：

```
Interface #0 (VC):
  作用: 用描述符声明"我有哪些控制项"（亮度、对比度、白平衡……）
  控制命令的实际通道: EP0（永远是 EP0）
  可选端点: EP3 IN（中断）——不是用来传控制的，是用来做硬件事件通知的
```

**一句话：所有控制传输走 EP0，VC 接口定义的是"有哪些控制"，而不是"控制走哪个端点"。**

---

## 补充问答三：UVC 扩展单元传大数据怎么办？

假设 UVC 扩展单元要传输 64KB 校准数据：

```
FS: 64KB ÷ 64B = 1024 次事务 × ~125μs ≈ 128ms
HS: 64KB ÷ 512B = 128 次事务 × ~10μs ≈ 1.3ms
```

128ms（FS）或 1.3ms（HS）传输 64KB——对"设置一次，用一辈子"的控制数据来说够了。

对于真的很大的数据，USB 的解决方案是走 Bulk 端点（DFU 固件升级标准就是控制传输只发命令，固件字节走专用 Bulk 端点）。

---

## 补充问答四：控制传输排队会不会无限积累？

不会。USB 在三个层面做了保护：

1. **硬件层**：EP0 状态机天然串行——上一个 STATUS 没闭环就不会发下一个 SETUP
2. **Host 驱动层**：每个设备一个控制请求槽位——Linux `usb_control_msg()` 同步阻塞，Windows 只有一个 IRP 挂起
3. **软件应用层**：超时杀死——xHCI 默认 5 秒超时，超时 → 中止端点 → 返回错误

---

## 补充问答五：设备类家族全景（HID / CDC 分别是什么）

> Phase 6 预习。回答"CDC 设备是什么设备""HID 是不是就是鼠标键盘"。

### HID：不是"鼠标键盘类"，是"免驱动通用 I/O 通道"

HID = Human Interface Device（人机接口设备类，bInterfaceClass=0x03）。鼠标键盘是最著名成员，但成员远不止：

| 成员 | 例子 |
|------|------|
| 传统输入 | 鼠标、键盘 |
| 游戏外设 | 手柄、摇杆、方向盘 |
| 触摸类 | 触摸屏、触摸板、数位板 |
| 特殊输入 | 扫码枪（模拟键盘）、指纹识别、VR 手柄 |
| 传感器 | 加速度计、陀螺仪 |
| 厂商自定义 | TM5X 的 HID 接口（Usage Page 0x81、Report 1023 字节） |

**HID 的本质是"免驱动、小包、低延迟的通用 I/O 通道"**：三大 OS 内置 HID 驱动，设备用 Report Descriptor 自描述数据格式。所以大量厂商拿它当"免驱动通信管道"——海康 TM5X 用它传 1023 字节大报文，冲着"插上即用、无需安装"去的。

### CDC：通信设备类大家族，串口只是其中一员

CDC = Communications Device Class（bInterfaceClass=0x02）。规范定义范围：**在 USB 上重现"传统通信/网络设备"的一大类**——串口、modem、以太网卡全都算。

| 子类 | 名称 | 现实例子 |
|------|------|---------|
| 0x02 | ACM | **虚拟串口**（CH340/CP210x/STM32、TM5X 的 "CDC Serial"） |
| 0x01/0x03/0x04 | 电话/ISDN | 历史上的 USB Modem |
| 0x06 | ECM | 早期 USB 以太网卡 |
| 0x0C | EEM | 点对点简易以太网 |
| 0x0F | NCM | **手机 USB 网络共享**主力 |
| 0x0D | OBEX | 老式手机同步 |

**手机插线共享网络（CDC-NCM）跑的是以太网帧，跟串口毫无关系——但它也是 CDC。** 类比：CDC=运输行业，ACM=公路货运（串口字节流），NCM=铁路货运（以太网帧）。

**口语 vs 规范**：嵌入式圈里说"CDC 设备"90% 指 CDC-ACM 虚拟串口（CH340 太普及），但规范里 CDC 是大家族。

### 判断方法：Class + SubClass 两层锁定

```
bInterfaceClass = 0x03        → HID
bInterfaceClass = 0x02        → CDC 家族
   bInterfaceSubClass = 0x02  → ACM（虚拟串口）
   bInterfaceSubClass = 0x0F  → NCM（以太网）
bInterfaceClass = 0x0E        → UVC 视频
```

### 三大类对照（SDK 三大目标）

| 类 | 类比 | 说什么语言 |
|---|------|-----------|
| UVC (0x0E) | 视频信号线 | 视频流协议 |
| CDC (0x02) | 电话线/串口线 | 串口/modem 协议 |
| HID (0x03) | 人机对话 | Report 报文 |

---

## 补充问答六：USB 虚拟串口是怎么"变"出来的（CDC-ACM 机制）

### 物理插头 ≠ 设备扮演的角色

插的确实是 USB 口（物理层），但插上之后设备"假装"是什么是另一回事：同一条 USB 线插 U 盘="硬盘"、插摄像头="视频设备"、插 TM5X="视频+串口+HID"。**插头长什么样，和它是什么设备没有关系**——和"同一条网线既能跑 HTTP 也能跑 SSH"同理：物理介质是公路，协议是路上跑的车。

### USB 自己就是"串行总线"

USB = Universal **Serial** Bus——它自己就是串行的。"串口"这个词指的不是"串行传输"，而是 RS-232/UART 那套协议（波特率、起始位、DTR/RTS）。所以"USB 上的串口"不矛盾：协议还是那套串口协议，物理层从 9 针线换成了 USB 线。

### 双层协议栈：USB 层运输 + 串口层业务

| 层 | 谁负责 | 干什么 |
|---|--------|--------|
| USB 层 | 设备里的 USB 控制器（硬件） | 枚举、握手、拆包——必须会 USB 协议 |
| 串口层 | 固件应用逻辑 | 解析串口业务数据 |

类比：快递公司（USB 层）必须会开车送货，收件人（串口层）只关心箱子里装了什么。

### 数据通路（下发方向）

```
串口助手 WriteFile("COM5", "AT+CONFIG")
  ↓ 内核：CDC 驱动把字节塞进批量 OUT 传输
  ↓ 总线：OUT Token → DATA0[数据] → CRC16 → 设备硬件 ACK
  ↓ 设备：USB 控制器硬件自动拆包（剥 Token、验 CRC、拼数据、放 FIFO）
  ↓ 固件：从端点缓冲读到的已是干净字节流——和真 UART 收到的几乎一样
  ↓ 应用逻辑：串口解析（校验、分帧、执行命令）
```

上行方向完全对称（固件写批量 IN 端点 → 主机 IN Token 取走 → CDC 驱动 → 串口助手）。

### 没有"串口物理帧"：波特率是虚拟参数

USB 虚拟串口里没有起始位/停止位/校验位——那些是 RS-232 物理层的概念，USB 的 CRC16 替代了它们。**连波特率都成了虚拟参数**：SET_LINE_CODING 里的 115200 不是让 USB 线按 115200bps 传，只是告诉固件"把 UART 逻辑配置成 115200"（后端真挂 UART 外设才用得上，纯虚拟串口基本忽略）。

**"虚拟串口"的精确含义：串口协议的内容语义（数据流+波特率参数+DTR/RTS 信号）全部保留，串口的物理帧格式被 USB 替代。** 上层软件和下层业务逻辑都不用改，只有中间的公路换了。

### 为什么存在

物理 RS-232 从电脑上消失了，但串口协议生态庞大（嵌入式调试、工业配置、console 口）→ USB 虚拟串口成为标准答案：**协议不死，只换公路。** TM5X 机芯没给 RS-232 排针，但 USB 线里藏着一个虚拟串口做调试/配置通道。

抓包实拍（4.11a）：`a1 21` GET_LINE_CODING = 串口助手"读取波特率"在 USB 总线上的翻译。

---

## 综合示例：CDC 虚拟串口完整描述符链

以下以一个 STM32 虚拟串口为例，把 3.1~3.11 全部串起来。

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
  ③ Host → OUT Token → EP2 OUT → "Hello"

Device 回 "World":
  ④ Host → IN Token → EP1 IN → "World"

设备状态变化:
  ⑤ Host → IN Token → EP3 IN → SerialState(10B)
```

---

# 第四篇：USB 枚举过程 — 逐包逐事务追踪

> Phase 4 主线。枚举（Enumeration）= 设备插入后，Host 通过 EP0 控制传输一问一答给设备"登记造册"的过程。本篇章每一节对应枚举时间线上的一个阶段，压轴（4.11）用 Wireshark/USBpcap 抓真机逐包对照。

## 4.1 枚举完整时间线（插入 → 检测 → 复位 → Default → Address → Configured）

### 为什么要有"枚举"这一步

PCI 卡插上主板，资源地址是固定分配的（门牌号焊死）；USB 设备即插即拔，每次插入都可能是不同的口、不同的 Hub 下游。所以 USB 规定：**设备插入后不能自己说话，必须等 Host 来问，一问一答走完全套流程，设备才被"认识"**。

之前的问题"USB 标准请求主要做什么用的"——答案在这里揭晓：**标准请求的一大半工作就是枚举**。GET_DESCRIPTOR(0x06)、SET_ADDRESS(0x05)、SET_CONFIGURATION(0x09) 全部登场。

### 核心框架：设备的 6 个状态

USB 2.0 规范第 9 章定义的设备状态机，是理解整个 Phase 4 的骨架：

```
插入
 │
 ▼
[Attached 已连接] ──上电──► [Powered 已上电]
                                │ 总线复位（SE0，≥10ms）
                                ▼
                          [Default 默认]   地址=0，只有 EP0 可用
                                │ SET_ADDRESS(新地址)     ▲ Set_Address(0) 或复位打回
                                ▼                         │
                          [Address 已编址] 有唯一地址，仍只有 EP0
                                │ SET_CONFIGURATION(1)    ▲ Set_Configuration(0) 打回
                                ▼                         │
                          [Configured 已配置] 全部端点启用 ─┘
                                │ 总线 3ms 无活动
                                ▼
                          [Suspended 挂起] ──总线活动/唤醒──► 回到原状态
```

| 状态 | 含义 | 设备能干什么 |
|------|------|-------------|
| Attached | 物理插入，hub 检测到 | 啥也不能干，还没上电 |
| Powered | 已上电 | 还不能通信 |
| Default | 总线复位后 | **只响应 EP0，且地址是公共的 0** |
| Address | 领到唯一地址（1~127） | 仍然只有 EP0 能用 |
| Configured | 激活了配置 | **非 EP0 端点全部启用，接口功能可用** |
| Suspended | 总线 3ms 没动静 | 省电待机 |

三个记忆锚点：

- **Default = 无名氏**：所有刚复位的设备都叫"地址 0"，像没领工牌的新员工。
- **Address = 有名字了，但没上岗**：只有 EP0 能应答。
- **Configured = 上岗**：这之后才谈得上"开流"（SET_INTERFACE）、批量/等时传输——本知识库第六篇的所有实战（XU 命令、取流）都发生在 Configured 之后。

### 完整时间线（Host 视角，教科书主线 10 步）

```
① 插入           hub 检测到 D+/D- 上拉电平变化 → 状态 Attached
② 复位           Host 把总线拉低 ≥10ms（SE0）→ 状态 Default（地址=0）
③ 第 1 次读      GET_DESCRIPTOR(Device)，只读前 8 字节
   → 只为拿一个字段：bMaxPacketSize0（EP0 最大包，在 offset 7）
④ Set_Address    Host 分配唯一地址（比如 5）→ 状态 Address
⑤ 第 2 次读      GET_DESCRIPTOR(Device)，读完整 18 字节
   → 完整自报家门：VID/PID/版本/配置个数...
⑥ 读 Config 头   GET_DESCRIPTOR(Config)，先只读 9 字节
   → 只为拿 wTotalLength（整条描述符链总长，在 offset 2~3）
⑦ 读 Config 全链 GET_DESCRIPTOR(Config)，一次读完整条链
   → 全部 Interface/Endpoint 描述符（lsusb -v 里看到的那整棵树）
⑧ 读 String      GET_DESCRIPTOR(String) — 厂商名/产品名/序列号
   （可多次、可跳过，不是所有设备都有）
⑨ Set_Config     SET_CONFIGURATION(1) → 状态 Configured，非 EP0 端点全部启用
⑩ （总线之外）   OS 按 VID/PID/Class 匹配并加载驱动 → 设备就绪，可以开流了
```

`sudo lsusb -v -d 2bdf:0101` 里看到的整棵描述符树（Device → Configuration → 两个 Interface → Endpoint → XU 单元），就是在第 ⑤⑥⑦ 步被 Host 一段一段问出来的。

一个贯穿性的事实：**枚举全流程只走 EP0 控制传输**——数据端点全程没参与。这正是 EP0 被类比为"$SYS/ 系统主题"的原因：先谈系统的事，业务管道后面才开。

### 三个"为什么"（理解了才算真的懂）

**1. 为什么 Device Descriptor 要读两次？**

第一次读的时候，Host 连"设备 EP0 一次最多收多少字节"都不知道。规范保证任何设备的前 8 字节都能读（bMaxPacketSize0 恰好在前 8 字节的最后一个字节）。拿到这个数，第二次才敢读满 18 字节。类比：先问对方"你一次最多听我讲几个字"，再决定长句怎么断句。

**2. 为什么 Config 描述符要先读 9 字节头？**

Host 不知道整条配置链有多长（Interface/Endpoint 个数不定），wTotalLength 写在 Config Descriptor 头的 offset 2~3。类比：快递外箱先看"内件总长"，再决定开多大的车去装。

**3. 为什么设备全程不能主动说话？**

USB 是 Host 中心总线：令牌（Token）只有 Host 能发。枚举就是一场单方面发问的"审讯"——设备只有被 IN 令牌点到名，才允许回答。这呼应了第二篇学的：所有传输都是 Host 发起。

### 类比：新员工入职

| 枚举步骤 | 入职场景 |
|---------|---------|
| 插入（hub 检测上拉） | 推门进公司，前台感应到有人 |
| 总线复位 | 安检：一切归零，从头办手续 |
| 读 8 字节 | 先自报最基础信息（"我一次最多听几个字"） |
| Set_Address | 领工牌号（地址 5） |
| 读 18 字节 | 交完整简历（VID/PID/版本...） |
| 读 Config 链 | 交部门配置表（几个接口、每个接口几条管道） |
| 读 String | 补花名册（"USB Thermal Camera"、序列号） |
| Set_Configuration | 门禁卡激活、工位通电 |
| 驱动加载 | HR 系统录入完毕，正式开工 |

MQTT 视角：枚举 ≈ 客户端接入 broker 的握手——TCP 连上 → CONNECT 报能力 → CONNACK 确认 → 才能订阅/PUBLISH。没走完握手，什么 Topic 都别想动；没枚举完，什么端点都别想用。

## 4.2 阶段 0：设备检测（插入瞬间，纯硬件零字节）

### 在时间线的位置

10 步时间线的第 ① 步：hub 检测到 D+/D- 上拉电平变化 → 状态 Attached。

> **这是整个 USB 世界里设备唯一一次"主动"——而且不是靠发任何数据，是靠一个电阻。**

协议栈还没醒来，没有 Token、没有包、没有 PID，纯电气行为。

### 插入瞬间的电路：一个分压器

```
设备侧                          线缆                Host/Hub 侧
┌─────────┐                                        ┌──────────────┐
│         │  3.3V (VTERM 3.0~3.6V)                 │              │
│         │   │                                    │              │
│         │  1.5kΩ ±5%（上拉）                      │              │
│  FS/HS  │   │                                    │              │
│  设备   ├───┴────────── D+ ────────────┬─────────┤  端口检测电路  │
│         │                              │         │              │
│         │  1.5kΩ ±5%（LS 设备接 D-）    │         │              │
│         │                              │         │              │
│         │                   空闲时 D+/D- 各接    │              │
│         │                   15kΩ ±5% 下拉到 GND   │              │
└─────────┘                                        └──────────────┘
```

- **没插设备时**：D+ 和 D- 被 Host 端的 15kΩ 下拉钉在低电平——这就是 SE0（两根线同时为低）
- **插入瞬间**：设备端 1.5kΩ 上拉一接通，D+ 电压变为：

```
V(D+) = 3.3V × 15kΩ / (15kΩ + 1.5kΩ) ≈ 3.0V
```

**为什么设计成 1.5k : 15k 的 1:10 比例？**

1. 分压出来 ≈3.0V，远高于差分接收器 200mV 的判定阈值 → 稳判"高"
2. 不接近 VTERM 上限，不伤 3.3V 逻辑电平
3. 1:10 让两根线的电平差足够大，任何一端都能清楚分辨"谁在上拉"

**USB 规范里第一个"信息编码"，不是 0 和 1 的比特流，而是电阻的位置。**

### D+ 还是 D-？——零字节的速度宣告

| 上拉位置 | 宣告的速度 | 为什么 |
|---------|-----------|--------|
| **D+** 上拉 | FS（12 Mbps）或 HS（480 Mbps） | 全速/高速一族 |
| **D-** 上拉 | LS（1.5 Mbps） | 低速一族 |

速度信息不需要任何协议报文——**上拉接在哪根线上，就是设备说的第一句话**，而且是"零字节"的一句话。

D+ 从低变高的**边沿**被 Host 端口的连接检测电路捕捉 → 端口状态变化 → 中断一路报到 hub → 主机控制器 → OS。这就是 4.1 状态机的第一跳：

```
[未连接] ──D+ 出现上拉电平──► [Attached 已连接]
                               │（总线供电设备）VBUS 稳定供电
                               ▼
                             [Powered 已上电]
```

注意：Attached 只是"检测到上拉"，**还没上电、不能通信**——只是前台感应到有人推门进来了。

### 重要伏笔：HS 设备也拉 D+，它在"冒充"FS

> **检测阶段只能区分 LS 和"非 LS"。FS 与 HS 在插入这一刻是分不开的。**

HS 设备插入时同样 D+ 上拉，先以 FS 身份出现，真实身份要等到 ② 复位之后的 **Chirp 握手**（§1.5：设备发 Chirp K → Host 回 K/J 交替 → 设备切 HS 终端电阻）才揭晓。

两段式速度判定：

```
插入瞬间（纯电阻）:  D+ 上拉 → "非 LS"（先当 FS 对待）
                     D- 上拉 → LS
复位后（Chirp 协议）: 是 HS 就升级 480Mbps，不是就留在 FS 12Mbps
```

Chirp 协商失败时设备退级到 FS 是安全的——它本来插进来时就按 FS 在跑。

### 三条硬件时序铁律（USB 2.0 规范 §7.1.5 / §7.1.7）

1. **VBUS 先来，上拉后到。** 设备绝不允许在 VBUS 有效之前给上拉电阻供电。上拉可以接 VBUS 本身，也可以接独立 3.3V——但逻辑上必须等 VBUS。原因：Hub 只在端口供电的情况下才监视 D+/D-；在无电端口上拉，等于对空气按门铃。
2. **Host 检测到上拉后，至少等 100ms 才动手。** 这 100ms 是规范留给设备上电稳定的缓冲期。插上 U 盘后系统总要愣一下才有反应，就是这 100ms 在起作用。
3. **设备要有能力"断开上拉"。** 断开 D+ 上拉 = 从电气上模拟一次拔出（Host 看到 D+ 掉回低电平）→ 触发重新枚举。这是设备的**软件重置后门**——出故障了不用物理拔插，协议栈断开上拉再拉上，就"假装重新插了一次"。

   注意：廉价设备常把上拉直接焊死在 VBUS 上，省一个 GPIO——后果就是失去这条后门，只能物理拔插。

### 类比：按门铃

把 4.1 的"新员工入职"类比往前延伸一格：

| 硬件行为 | 入职场景 | MQTT 场景 |
|---------|---------|----------|
| 插入瞬间，上拉接通，D+ 变高 | 按门铃 | 网线插上，物理层 **link up**（链路灯亮） |
| D+ 还是 D- 上拉 | 门铃的不同音色（听出来是快递还是同事） | —— |
| Host 检测到电平边沿 | 前台感应门开了 | 网卡 PHY 检测到载波 |
| 断开上拉再拉上 | 出门再按一次门铃 | 拔网线重插 |

门铃响，传递的信息只有一条："**有东西来了。**" 至于是谁、来干什么、有什么能力——一句话都还没说，全要等开门后（② 复位 → ③~⑨ 枚举）一问一答慢慢聊。

### 一句话总结

**设备检测 = 一个 1.5kΩ 电阻接上数据线，让 D+/D- 从"双低"变成"一高一低"。电阻的位置宣告速度，电平的边沿宣告存在。零字节、零包、纯硬件——这是枚举的起跑枪。**

## 4.3 阶段 0b：总线复位（SE0 ≥10ms，一切归零）

### 在时间线的位置

10 步时间线的第 ② 步：检测到设备之后、第一次读描述符之前。

为什么检测到设备后不能直接开问？因为此刻设备状态是"脏"的：可能残留上一个 Host 分配的地址/配置，刚上电内部时钟还没锁稳，Host 对它的 EP0 能力一无所知。所以 Host 的第一步动作不是"问"，而是**"清零"**。

### 电气定义：还是 SE0，但这次是"按着不放"

复位信号 = **D+ 和 D- 同时拉低（SE0），持续 ≥10ms**（USB 2.0 规范 §7.1.7.5）。

SE0 也是 EOP（包结束信号）的一部分——同一个电气状态，靠**持续时间**区分语义：

| 信号 | SE0 持续时间 | 含义 |
|------|-------------|------|
| EOP（包结束） | 2 个 bit 时间（FS 下 ≈167ns） | 正常的"这一包说完了" |
| 总线复位 | **≥10ms** | 全场清零，一切从头来 |

**时间长度本身就是信息。** 不引入新电平、新线缆，就用"低电平按多久"区分语义。类比：敲门和按住门铃不放——同样的动作，时长不同，含义完全不同。

设备侧：规范要求设备检测到 SE0 持续 **≥2.5μs** 就必须当作复位开始响应。余量设计：

```
EOP 的 SE0（FS）  ≈ 167ns     ← 正常包结尾，绝不误判
设备的响应门槛    = 2.5μs     ← 约 15 倍于 EOP，足够保险
Host 实际驱动     = 10ms      ← 又 4000 倍于门槛，杜绝漏判
```

### 复位期间设备必须"立即停手"

设备看到 SE0 ≥2.5μs 的瞬间，必须放弃手头的一切传输——正在发的数据包掐断、进行到一半的控制传输作废。复位就是 Host 的"全场静默"信号。类比：裁判吹哨，场上所有人立即放下球。

### 复位让设备进入 Default 状态

复位结束（SE0 撤除）后，设备进入 Default 状态（4.1），四件事同时发生：

| 被清零的东西 | 清成什么 |
|-------------|---------|
| 设备地址 | **0**（公用地址，回到"无名氏"） |
| 配置 | 无（未配置） |
| 可用端点 | 只剩 **EP0** |
| 数据切换位 | DATA0/DATA1 翻转归零 |

设备还是那个设备（描述符、VID/PID 都没变），但协议层面的身份全部抹除。类比游戏：角色没删，装备、等级、状态全部清零，回到出生点。

### 为什么必须复位？三个理由

1. **状态未知，必须归一。** Host 不知道设备从哪来、带着什么旧状态。与其猜测，不如强制清零到一个双方都知道的起点："地址 0、只有 EP0"——这是唯一确定的共同事实。
2. **同步起点。** 之后的所有对话（③~⑨）都默认从"地址 0 开始"这一点出发。没有复位，Host 连该用哪个地址喊它都不知道。
3. **给设备内部初始化的时间。** 复位期间设备完成内部时钟锁定、上电复位电路稳定——10ms 对数字电路来说是相当充裕的"深呼吸"。

MQTT 类比：复位 ≈ 客户端 clean session=1 的重连——旧订阅、旧会话状态全部作废，一切从 CONNECT 重新来过。

两种"重来"的区别（呼应 4.2）：**断开上拉 = 模拟拔出**（回到 Attached 之前，连"我插着"都重新宣告），**复位 = 模拟"重新开始"**（回到 Default，只清零协议状态）。

### HS 的伏笔在此接上

HS 设备插入时"冒充"FS（4.2），揭晓真实身份的时机就是复位撤除之后：

```
插入（D+ 上拉，冒充 FS）→ 复位 ≥10ms → 复位撤除 → HS 设备发 Chirp K
                                            → Host 回 Chirp K/J 交替
                                            → 设备切 HS 终端电阻 → 480Mbps 模式
```

**先复位，后 Chirp。** 复位是 Chirp 协商的"发令枪"——设备一直在等这一声枪响，才敢喊出"我其实是高速的"。

### 复位不只发生在枚举时

Host 任何时刻都能发复位，不只枚举开头。设备在任何状态（哪怕 Configured 正在干活）收到复位，一律打回 Default。这是 Host 手里的"强制重置"大招——设备行为异常时，Host 直接复位重来，不用拔插。

**断开上拉是设备侧的后门，复位是 Host 侧的开关。** 两侧各有一个"重新开始"的手段。

### 一句话总结

**复位 = Host 把两根数据线同时按低 ≥10ms——用"SE0 的持续时间"这个唯一的变量，把设备从任何状态强制打回 Default（地址 0、仅 EP0、数据翻转归零）。设备从这一刻起，才进入"可以被提问"的状态。**

## 4.4 阶段 1：Get_Descriptor(Device) 第 1 次（Host 的第一个包）

### 在时间线的位置

10 步时间线的第 ③ 步。前两格（4.2 检测、4.3 复位）都是纯电气行为——没有包、没有 PID。从这一刻起，Token、SETUP 包、DATA0/DATA1 全部登场。

这个包的构造方法和第六篇 XU 命令完全相同（8 字节 SETUP 骨架），只是"三把钥匙"取值不同。

### SETUP 包逐字节：80 06 00 01 00 00 08 00

```
80 06 00 01 00 00 08 00
│  │  └──┴──┘ └──┴──┘ └──┴──┘
│  │    │       │       └─ wLength  = 0x0008 = 8   ★ 只读 8 字节
│  │    │       └─ wIndex   = 0x0000 = 0（Device 描述符用不到语言 ID，规范定死为 0）
│  │    └─ wValue  = 0x0100：高字节 0x01 = 描述符类型 Device
│  │                         低字节 0x00 = 描述符索引 0（Device 描述符只有一个）
│  └─ bRequest = 0x06 = GET_DESCRIPTOR
└─ bmRequestType = 0x80
```

第一字节"三把钥匙"（第五会话的肌肉记忆）：

```
0x80 = 1 00 00000
       │ │  └───── D4-0 = 0     → 接收者 = Device（整个设备）
       │ └──────── D6-5 = 00    → 字典 = Standard（OS USB 核心，枚举专用）
       └────────── D7  = 1      → 方向 = IN（Host 要"收"数据）
```

对比 XU 命令 `0x21 = 0 01 00001`：骨架一模一样，D6-5 从 Class 换成 Standard、D4-0 从 Interface 换成 Device。

wValue 字节序（第十会话踩过坑）：`0x0100` 在线上是小端 `00 01`——高字节是描述符类型码（Device=0x01，与 §3.2 的 bDescriptorType 同一张表）。

### 总线上的完整对话（设备还没地址，ADDR 全是 0）

```
事务 1 — SETUP 阶段：
  Host 发: SETUP Token(ADDR=0, ENDP=0) → DATA0 [80 06 00 01 00 00 08 00] → 设备回 ACK

事务 2 — DATA 阶段（IN）：
  Host 发: IN Token(ADDR=0, ENDP=0)
  设备回:  DATA1 [12 01 00 02 00 00 00 40] → Host 回 ACK

事务 3 — STATUS 阶段（OUT）：
  Host 发: OUT Token(ADDR=0, ENDP=0) → DATA1 [空，0 字节] → 设备回 ACK
```

两个现场应用（§2.5/2.10 学过的第一次登场）：

1. **DATA0/DATA1 翻转**：SETUP 固定用 DATA0，紧跟的第一个数据包必是 DATA1，STATUS 阶段继续翻转。翻转从枚举第一问就开始严格执行。
2. **STATUS 方向与 DATA 相反**：DATA 是 IN（设备→Host），STATUS 就是 OUT（Host→设备），零长度包表示"收讫"。

### 设备回的 8 字节

对照 §3.2 的 18 字节全表，这 8 字节是前段：

```
12 01 00 02 00 00 00 40
│  │  └──┴──┘ └──┴──┘ └─┘
│  │    │     │       └─ offset 7: bMaxPacketSize0 = 0x40 = 64 ★★★ 本次读的终极目标
│  │    │     └─ offset 4~6: bDeviceClass/SubClass/Protocol = 00 00 00
│  │    └─ offset 2~3: bcdUSB = 0x0200 = USB 2.0
│  └─ offset 1: bDescriptorType = 0x01
└─ offset 0: bLength = 0x12 = 18（完整长度）
```

Host 真正认真看的只有 2 个字段：**bLength=18**（知道第二次读该要多少，4.6 节）和 **bMaxPacketSize0=64**（知道 EP0 每次最多传多少——本次核心收获）。

### 为什么 wLength=8？——前因后果完整版

**前因**：Host 连设备 EP0 最大包都不知道。bMaxPacketSize0 有 8/16/32/64 四种可能（FS；LS 固定 8，HS 固定 64）。第一次狮子大开口要 18 字节，设备 EP0 只有 8 就会错位，而且 Host 连分片单位都不知道。

**规范的设计**：bMaxPacketSize0 恰好在 offset 7——**前 8 字节的最后一个字节**。而 8 是所有可能值的最小值。于是规范给出铁保证：

> **任何 USB 设备的 Device Descriptor，前 8 字节一定可读。**

**后果**：最小 8 字节探测必然成功 → 拿到 offset 7 的 bMaxPacketSize0 → 从此知道分片单位 → 第二次才敢要完整 18 字节（4.6 节）。

**保底规则**：控制传输里设备回"短包"（不足 wLength）即代表传输结束——即使设备描述符短于 wLength 也不会卡死，短包自然终止。

**类比**：打电话给陌生人，不知道对方是座机还是老人机——先只说 8 个字试试水，判断"语速该多快"，再决定长句怎么讲。

### 地址 0 为什么不会撞车

Default 状态的设备全叫"地址 0"，靠 **Hub 逐端口复位**（4.3）保证同一时刻只有一个设备处于"地址 0 待提问"状态。类比：医院叫号，第 0 号窗口每次只放一个人。

### 与 §2.2a 的交叉：64 vs 512 vs 65535

这里只读 8 字节，是因为"不知道上限"；而 bMaxPacketSize0 本身是 EP0 单笔事务的上限（HS 固定 64）。"控制传输最大多少"有三层答案：总线事务 64B（§2.2a）、TM5X 协议帧 512B（§6.9）、wLength 字段 65535——三个数管三层，一层套一层。

### 一句话总结

**Host 用地址 0 发出枚举的第一个请求——GET_DESCRIPTOR(Device)，wLength=8。8 是 bMaxPacketSize0 的位置（offset 7）和所有设备最小 EP0 包的交集。用最小代价探出"对方一次能听多少"，这 8 字节是整场枚举的第一个锚点。**

## 4.5 阶段 1b：Set_Address（设备领到专属地址）

### 在时间线的位置

10 步时间线的第 ④ 步。为什么读完 8 字节后不接着读完整描述符，而是先插一个 Set_Address？因为地址 0 的"独享"是脆弱的（4.4：靠 Hub 逐端口复位才没撞车）。Host 往往同时挂着多个设备，当务之急是给这台设备一个唯一身份，让后续所有 Token 都有明确的喊话对象。

### SETUP 包逐字节：00 05 05 00 00 00 00 00

（以分配地址 5 为例）

```
00 05 05 00 00 00 00 00
│  │  └──┴──┘ └──┴──┘ └──┴──┘
│  │    │       │       └─ wLength  = 0x0000 = 0   ★ 没有 DATA 阶段！
│  │    │       └─ wIndex   = 0x0000 = 0（用不到）
│  │    └─ wValue  = 0x0005 = 5   ★ 新地址装在这里（小端 05 00）
│  └─ bRequest = 0x05 = SET_ADDRESS
└─ bmRequestType = 0x00
```

三把钥匙与上一个包对比：GET_DESCRIPTOR 的 `0x80` 与 SET_ADDRESS 的 `0x00` 只有 D7 不同——方向 OUT（Host"告诉"设备一件事，没有数据要收回）。字典 Standard、接收者 Device 完全一致。

### 为什么地址装在 wValue 里

**wValue/wIndex/wLength 是"通用盒子"，bRequest 决定盒子里装什么：**

| bRequest | wValue 装什么 |
|----------|--------------|
| GET_DESCRIPTOR (0x06) | 描述符类型 + 索引 |
| SET_ADDRESS (0x05) | **新地址** |
| SET_INTERFACE (0x0B) | Alternate Setting 号 |

同一个 wValue，换个 bRequest 就换一层语义——8 字节骨架永远不变，这是 libusb_control_transfer 一个函数通吃所有标准请求的原因。地址 1~127 只需 7 bit，wValue 有 16 bit，绰绰有余。

### wLength=0：没有 DATA 阶段的两阶段传输

GET_DESCRIPTOR 是三阶段（SETUP+DATA+STATUS），SET_ADDRESS 只有两阶段：

```
事务 1 — SETUP 阶段：
  Host 发: SETUP Token(ADDR=0, ENDP=0) → DATA0 [00 05 05 00 00 00 00 00] → 设备 ACK

（没有 DATA 阶段——地址 7 bit，SETUP 包里装得下）

事务 2 — STATUS 阶段（IN）：
  Host 发: IN Token(ADDR=0, ENDP=0)          ← 注意！还是地址 0
  设备回:  DATA1 [空，0 字节] → 完成签收
```

DATA 阶段本来就是可选的（§2.10）——装得下就不开数据车。

### ★ 经典细节：设备什么时候"改听"新地址

**设备在 STATUS 阶段仍用旧地址（0）完成握手，STATUS 成功之后才切换到新地址。**

反证：如果设备收到 SETUP 就立刻切到地址 5，Host 发 STATUS 的 IN Token 用地址 0 喊它——没人应答，Host 以为传输失败。

```
① SETUP(ADDR=0) ──► 设备记下"我将成为地址 5"，但不切换
② STATUS IN(ADDR=0) ──► 设备以旧身份完成签收
③ STATUS 完成 ──► 设备正式切换，从此只认地址 5
④ 规范要求：切换后 2ms 内必须能响应新地址的请求（§9.2.6.3）
```

类比：离职交接——旧工牌交还、签完交接单（STATUS），新工牌才生效。交接单没签就换工牌，门卫（Host）就找不到人了。

### 地址是"会话级"的——应用层永远不碰它

- 地址由 Host（USB 核心栈）统一分配，1~127 挑一个，0 永远保留给 Default
- 拔掉重插 → 重新枚举 → 地址可能变（哪怕插同一个口）
- 应用层代码（xu_interactive.c / uvc_stream_viewer.cpp）从不写地址——libusb 句柄把地址封装掉了，只认 VID:PID 和句柄

地址是总线的内部事务。类比：TCP 连接的内核临时源端口——会话级、内核管理、应用层无感知。USB 地址 = USB 世界的"临时端口号"。

### 一句话总结

**Set_Address 用一次两阶段控制传输（无 DATA 阶段），把 1~127 里的一个数字装进 wValue 发给地址 0 的设备。设备以旧身份签完 STATUS 才切换新身份——"先交接、后换牌"。从此设备有了本次会话的唯一地址，后续所有枚举对话都用这个地址点名。**

## 4.6 阶段 2：Get_Descriptor(Device) 第 2 次（自报家门全家福）

### 在时间线的位置

10 步时间线的第 ⑤ 步。设备已有专属地址（比如 5），Host 用新地址读完整 18 字节 Device Descriptor。

### SETUP 包逐字节：80 06 00 01 00 00 12 00

```
第 1 次: 80 06 00 01 00 00 08 00     wLength = 0x0008 = 8
第 2 次: 80 06 00 01 00 00 12 00     wLength = 0x0012 = 18
                          ▲
                    SETUP 包内容一模一样，只改了 wLength！
```

真正的区别不在包内容里，而在**总线 Token 的地址字段**：第 1 次三个 Token 全是 ADDR=0（喊"无名氏"），第 2 次全是 ADDR=5（点名道姓）。这就是 Set_Address 立竿见影的效果。

### 为什么这次敢要 18 了

两道保险同时生效：

**保险一：分片单位已知。** 第一次拿到 bMaxPacketSize0（比如 64），18 字节 < 64，一笔事务装得下。

**保险二：短包规则兜底。** 即使 bMaxPacketSize0=8 的最小设备（18 字节装不下），规范也保证能读完：

```
bMaxPacketSize0=8 的设备回 18 字节：
  事务1: DATA1 [8 字节]   ← 满包
  事务2: DATA1 [8 字节]   ← 满包
  事务3: DATA1 [2 字节]   ← 短包！短包 = 传输结束信号
  Host 收到短包，知道 18 字节收齐
```

第二次读**无论设备 EP0 多大都必然成功**——这是规范设计上的闭环。

### 18 字节全家福（2bdf:0101 为例）

| 偏移 | 字段 | 值（示例） | Host 拿来干什么 |
|------|------|-----------|----------------|
| 0 | bLength | 0x12 = 18 | 确认长度（交叉验证） |
| 1 | bDescriptorType | 0x01 | 确认类型 |
| 2-3 | bcdUSB | 0x0200 | 协议版本 |
| 4 | bDeviceClass | 0xEF | 类信息（§5.3：Misc，IAD 场景） |
| 5 | bDeviceSubClass | 0x02 | 通用类 |
| 6 | bDeviceProtocol | 0x01 | 配合 IAD 使用 |
| 7 | bMaxPacketSize0 | 0x40 = 64 | 又见一次——交叉确认 |
| 8-9 | idVendor | 0x2BDF | **★ 驱动匹配钥匙之一** |
| 10-11 | idProduct | 0x0101 | **★ 驱动匹配钥匙之二** |
| 12-13 | bcdDevice | 设备版本 | 版本管理 |
| 14 | iManufacturer | 字符串索引 | "HIK"（指向 String Descriptor） |
| 15 | iProduct | 字符串索引 | "HikCamera" |
| 16 | iSerialNumber | 字符串索引 | 序列号（可能为 0=没有） |
| 17 | bNumConfigurations | 0x01 | **★ 下一步路线图：要读几个配置** |

Host 重点收走三个信息：**VID:PID**（驱动匹配唯一依据）、**bNumConfigurations**（下面有几个 Config 要读）、**字符串索引**（iManufacturer/iProduct 不是字符串本身，是指针，指向第 ⑧ 步要读的 String Descriptor）。

### "为什么分两次读"的最终闭环

```
问题：Host 想读完整 18 字节
  ↓
障碍：分片单位（EP0 最大包）未知，读 18 字节可能错位
  ↓
死循环？：要知道分片单位 → 必须先读描述符 → 读描述符又要先知道分片单位
  ↓
规范的破环一刀：★ 前 8 字节无条件可读 ★
  （8 = 所有设备 EP0 最小值，bMaxPacketSize0 恰好卡在 offset 7）
  ↓
第一次读 8 字节 → 拿到分片单位 + 总长
  ↓
第二次读 18 字节 → 拿到完整身份
```

**"读两次"不是效率低下，是破解信息依赖死循环的唯一优雅解法。** 用最小承诺（8 字节）撬动完整信息（18 字节）——和 MQTT 固定报头如出一辙：先读第 1 字节拿"剩余长度"，再按长度读完整报文。

### 一句话总结

**第二次 GET_DESCRIPTOR 只改了 wLength（8→18）和 Token 里的地址（0→5），换来设备的完整身份——VID/PID（驱动匹配）、bNumConfigurations（下一步路线图）、字符串索引（花名册指针）。"分两次读"是破解"先有鸡还是先有蛋"的规范级设计：用无条件可读的 8 字节，撬动 18 字节的完整档案。**

## 4.7 阶段 3：Get_Descriptor(Config) 先读 9 字节头（总长未知，先看"目录"）

### 在时间线的位置

10 步时间线的第 ⑥ 步。身份已明（VID/PID/bNumConfigurations），下一步看"能力清单"——Config 描述符链。

### Config 和 Device 的本质区别：长度不定

Device Descriptor 固定 18 字节，4.6 的"两次读"解决的是"分片单位未知"。Config 是**一条链**，长度完全不定：

```
Config Descriptor (9B)
  ├─ Interface Descriptor (9B)      ← 有几个接口就接几个
  │    ├─ Endpoint Descriptor (7B)  ← 每个接口下挂 N 个端点
  │    └─ 类专用描述符 (不定长)      ← UVC 的 VC/VS 链、CDC 的 CS 链…
  └─ ...（2bdf:0101 整条链 433 字节，§5.8 逐段验算）
```

规范把链的总长 `wTotalLength` 写在 Config Descriptor 头部的 offset 2~3——**"先读固定长度的头，头里写着总长，再按总长读全部"，与 Device Descriptor 的两次读同构，换了一层楼。**

但两个"未知"不一样：

| | Device Descriptor | Config 描述符链 |
|---|---|---|
| 第 1 次的未知 | 分片单位（EP0 最大包）未知 | **总长**未知 |
| 第 1 次读多少 | 8 字节（规范保底） | 9 字节（Config 头固定长度） |
| 头里的关键字段 | bMaxPacketSize0 (offset 7) | wTotalLength (offset 2~3) |
| 第 2 次读 | 18 字节 | 整条链 |

分片单位已在 4.4 拿到，所以 Config 的两次读只剩一个问题：总长。

### SETUP 包逐字节：80 06 00 02 00 00 09 00

```
80 06 00 02 00 00 09 00
│  │  └──┴──┘ └──┴──┘ └──┴──┘
│  │    │       │       └─ wLength = 0x0009 = 9   ★ Config 头固定 9 字节
│  │    │       └─ wIndex  = 0（Config 用不到语言 ID）
│  │    └─ wValue = 0x0200：高字节 0x02 = 描述符类型 Configuration
│  │                        低字节 0x00 = 配置索引 0（第一个配置）
│  └─ bRequest = 0x06
└─ bmRequestType = 0x80
```

与 Device 版对比，**唯一变化是 wValue 高字节：0x01（Device）→ 0x02（Configuration）**——描述符类型码变一位，请求语义就从"要身份"变成"要能力清单"。wLength=9 不是拍脑袋：Config Descriptor 本身固定 9 字节（§3.4），第一次读正好一个头。

### 9 字节头里有什么

```
09 02 31 02 02 00 01 00 32        （格式示例，LE）
│  │  └──┴──┘ │  │  │  │  └─┘
│  │    │     │  │  │  │   └─ offset 8: bMaxPower（2mA 单位）
│  │    │     │  │  │  └─ offset 7: bmAttributes（供电属性位图）
│  │    │     │  │  └─ offset 6: iConfiguration（字符串索引，可为 0）
│  │    │     │  └─ offset 5: bConfigurationValue ← 第 ⑨ 步 Set_Config 的 wValue 来源！
│  │    │     └─ offset 4: bNumInterfaces（链里有几个接口）
│  │    └─ offset 2~3: wTotalLength ★★★ 本次读的终极目标
│  └─ offset 1: bDescriptorType = 0x02
└─ offset 0: bLength = 0x09
```

Host 真正拿走的是 **wTotalLength**，顺手白捡两个伏笔：**bNumInterfaces**（几个接口的心理预期）、**bConfigurationValue**（第 ⑨ 步 SET_CONFIGURATION 的 wValue 就是填它）。

### 为什么 9 字节一定读得成功

9 < 64（分片单位已知），一笔事务装下。Config 头本身固定 9 字节——**这次连短包兜底都用不上**，精确命中：

```
事务1: SETUP Token(ADDR=5) → DATA0 [80 06 00 02 00 00 09 00] → ACK
事务2: IN Token(ADDR=5) → DATA1 [09 02 … 9 字节] → Host ACK
事务3: OUT Token(ADDR=5) → DATA1 [空] → 设备 ACK
```

三个 Token 的 ADDR 全是 5——设备有身份了，全程点名。

### 类比

Device Descriptor 的两次读像**试通话**（先测语速），Config 的两次读像**看目录**（先查总页数）。两次"先读头再读全"解决同一个元问题——**"在不知道对方有多少信息之前，如何安全地知道"**——Device 的未知是"传输能力"，Config 的未知是"内容体量"。

### 一句话总结

**Config 描述符链长度不定，规范把总长 wTotalLength 写在 9 字节固定头部的 offset 2~3。Host 先精确读 9 字节拿总长，下一次按总长读完整条链。与 Device Descriptor 的两次读同构，但这次解决的是"内容多大"，不是"传输多快"。**

## 4.8 阶段 4：Get_Descriptor(Config) 完整链（能力清单一次拉回）

### 在时间线的位置

10 步时间线的第 ⑦ 步。手里有 wTotalLength（比如 433），这一次读回整条链。

### SETUP 包逐字节：只有 wLength 变了

```
第 1 次: 80 06 00 02 00 00 09 00      wLength = 0x0009 = 9（头）
第 2 次: 80 06 00 02 00 00 B1 01      wLength = 0x01B1 = 433（整链）
                          └──┴──┘
                    只改 wLength——433 的小端形式 B1 01
```

**wLength 直接填上一步拿到的 wTotalLength**——上一个请求的答案变成下一个请求的参数，信息像接力棒一样传递。

### ★ 枚举里第一次出现"一个传输拆多笔事务"

4.7 之前所有枚举对话数据量都 ≤64 字节，一笔事务装下。这次 433 字节 > 64，§2.2a/§6.9 反复琢磨的"拆分"现象第一次在总线上真实上演：

```
DATA 阶段：433 字节 = 6 × 64 + 49
  事务1: IN Token(ADDR=5) → DATA1 [64B] → Host ACK
  事务2: IN Token(ADDR=5) → DATA0 [64B] → Host ACK
  事务3: IN Token(ADDR=5) → DATA1 [64B] → Host ACK
  ...（DATA0/DATA1 交替翻转，全程贯穿）
  事务6: IN Token(ADDR=5) → DATA1 [64B] → Host ACK
  事务7: IN Token(ADDR=5) → DATA0 [49B] → Host ACK   ← 短包！
```

- **7 笔事务，每笔一个完整的 Token + Data + ACK**，DATA0/DATA1 翻转贯穿（§2.5 实战）
- 最后一笔 49 字节是**短包**——短包 = 传输结束信号（4.6 的兜底规则这次是主角）
- **Bus Hound 视角**：7 笔事务合并为一行 `IN 433`（URB 层，§2.2a）。"一行 512 = 总线 8 笔事务"不只是 XU 大数据才有——枚举阶段就发生了，433 字节 Config 链是设备上就能抓到的最小例子

### 这次拿到的：设备的能力清单（完整树）

```
Device Descriptor (已读)
└─ Config Descriptor (wTotalLength=433)
    ├─ IAD                                  ← VC+VS 归组
    ├─ Interface 0: Video Control (VC)
    │    ├─ VC Header / Input Terminal / Processing Unit…
    │    └─ Extension Unit (bUnitID=0x0A)   ← XU 命令发到这儿
    └─ Interface 1: Video Streaming (VS)（含 Alt Setting）
         └─ Endpoint 0x81: Bulk IN, wMaxPacketSize=512  ← 视频数据管道
```

Host 从链里知道三件事：**每个接口是干什么的**（bInterfaceClass 驱动匹配依据）、**每个端点的地址和能力**（将来开流的数据管道施工图）、**Alt Setting 结构**（SET_INTERFACE 切档依据，§6.3）。

### ★ 关键认知：读回来 ≠ 激活

**Host 此刻只是"读"到了能力清单，什么端点都没启用。设备仍处于 Address 状态——非 EP0 端点全部关闭。**

类比：HR 把部门配置表调档查看了，但工位没通电、门禁没激活。"知道你能干什么"和"让你开始干"是两件事——后者要等第 ⑨ 步 SET_CONFIGURATION。刚插上的摄像头不 Set_Config 就发数据传输，设备根本不响应——管道还不存在。

### 为什么敢一次读完 433

三道保险：**分片单位已知**（64，切不坏）、**短包规则**（49 字节自然收尾）、**wTotalLength 兜底**（设备保证发满；万一少发，短包结束 + Host 报错）。

### 一句话总结

**第二次 GET_DESCRIPTOR(Config) 把 wLength 填成上一步的 wTotalLength，一次拉回完整描述符链。433 字节在总线上拆成 7 笔 ≤64B 事务（短包收尾）——"64 字节事务上限"在枚举阶段就登台。但读回来只是"知道"，端点激活要等 SET_CONFIGURATION。**

## 4.9 阶段 5：Get_Descriptor(String)（花名册兑现，最不重要的环节）

### 在时间线的位置

10 步时间线的第 ⑧ 步。兑现 4.6 的伏笔：Device Descriptor 里的 `iManufacturer=1`、`iProduct=2` 不是字符串，是**索引（指针）**，指向 String Descriptor。

### String Descriptor 的特殊结构

1. **长度不定**：字符串多长它多长
2. **内容不是 ASCII，是 UTF-16LE（UNICODE）**——每个字符 2 字节，低字节在前
3. **String #0 是特例**——装的不是字符串，是语言 ID（LANGID）列表：

```
String #0（特例）: 04 03 09 04
                   │  │  └──┴──┘
                   │  │     └─ LANGID = 0x0409 = English (US)（小端 09 04）
                   │  └─ bDescriptorType = 0x03
                   └─ bLength = 4（多个 LANGID 则长度翻倍）
```

读字符串两步：先读 String #0 问"你会说哪几种语言"→ 拿到 LANGID → 带 LANGID 读真正的字符串（§3.8 的 LANGID 机制上台）。

### SETUP 包逐字节：wIndex 终于有用了

前几节 GET_DESCRIPTOR 的 wIndex 一直是 0，这次第一次派上用场：

```
第 1 问 — String #0（LANGID 列表）:
  80 06 00 03 00 00 FF 00
  │  │  └──┴──┘ └──┴──┘ └──┴──┘
  │  │    │       │       └─ wLength = 0x00FF = 255（"有多少说多少"）
  │  │    │       └─ wIndex = 0x0000（LANGID 还没定，只能给 0）
  │  │    └─ wValue = 0x0300：高字节 03 = String 类型，低字节 00 = 索引 0
  │  └─ bRequest = 0x06
  └─ bmRequestType = 0x80

第 2 问 — String #1（iManufacturer，带 LANGID）:
  80 06 01 03 09 04 FF 00
  │  │  └──┴──┘ └──┴──┘ └──┴──┘
  │  │    │       │       └─ wLength = 255
  │  │    │       └─ wIndex = 0x0409  ★ 刚拿到的 LANGID 装这里！
  │  │    └─ wValue = 0x0301：索引 1（iManufacturer 指的那个）
  │  └─ bRequest = 0x06
  └─ bmRequestType = 0x80
```

**wIndex 语义此刻完整**：对 Device/Config 是"用不到的语言参数"（填 0），对 String 是"请用这个语言回答我"。4.4/4.7 里 wIndex=0 的谜底——不是"没用"，是"轮到它用的时候还没到"。

设备回答 String #1（iManufacturer="HIK"）：

```
08 03 48 00 49 00 4B 00
│  │  └──┴──┘ └──┴──┘ └──┴──┘
│  │    │       │       └─ 'K' = 0x004B
│  │    │       └─ 'I' = 0x0049
│  │    └─ 'H' = 0x0048（UTF-16LE：低字节在前）
│  └─ bDescriptorType = 0x03
└─ bLength = 8 = 2 + 3字符×2
```

### 一个实用细节：读 String 不用"两次读"

规范允许两种策略：**学院派**（先读 2 字节拿 bLength 再读全，与 Device/Config 同套路）、**实用派**（wLength=255 一次读，设备回完整字符串后短包结束）。**主流 OS 全用实用派**——字符串短，短包规则（4.6/4.8 的老朋友）第三次兜底。字符串是枚举里唯一"懒得先读头"的描述符——信息价值低，不值得折腾。

### 为什么是"最不重要的环节"

1. **可以跳过**：字符串索引为 0（"没名字"）就不读；读了失败也不影响后续
2. **不影响功能**：驱动匹配靠 VID/PID（4.6），配置激活靠描述符链（4.8）——字符串从头到尾只是"给人看的标签"
3. **纯展示用途**：设备管理器/`lsusb` 里显示的"USB Thermal Camera"就是它

类比：工号（地址）、简历（描述符）、部门配置表（Config 链）都是硬信息；花名册上的花名写错一个字（字符串乱码）不影响开工。

### 一句话总结

**String Descriptor 是 Device Descriptor 字符串索引的"兑现"——先读 String #0 拿 LANGID，再带 LANGID 读真正的字符串。wIndex 在这里第一次派上用场（装 LANGID），字符串是 UTF-16LE、长度不定、短包收尾。枚举里最"佛系"的一步：可跳过、可失败、纯展示。**

## 4.10 阶段 6：Set_Configuration（枚举的最后一问：上岗）

### 在时间线的位置

10 步时间线的第 ⑨ 步——总线层面枚举的收尾。

### SETUP 包逐字节：00 09 01 00 00 00 00 00

```
00 09 01 00 00 00 00 00
│  │  └──┴──┘ └──┴──┘ └──┴──┘
│  │    │       │       └─ wLength = 0（无 DATA 阶段）
│  │    │       └─ wIndex  = 0
│  │    └─ wValue  = 0x0001 = 1   ★ 填 4.7 的伏笔：bConfigurationValue
│  └─ bRequest = 0x09 = SET_CONFIGURATION
└─ bmRequestType = 0x00（OUT, Standard, Device）
```

和 SET_ADDRESS（4.5）几乎同构——两阶段传输、wValue 装数字。但语义不同：

| | SET_ADDRESS (4.5) | SET_CONFIGURATION (4.10) |
|---|---|---|
| wValue 装 | 新地址（1~127） | 配置编号（bConfigurationValue，通常是 1） |
| 为什么填这个 | Host 自己分配的数字 | **4.7 读 Config 头时设备自报的数字** |
| 效果 | 有名字了 | **上岗了** |

`bConfigurationValue=1` 是设备在 Config 头里告诉 Host 的"我的配置叫 1 号"——设备自我介绍的数字，Host 原样喊回去。填 1 而不是 433：配置用"编号"命名，不用"长度"命名（433 是 wTotalLength，是说明书厚度，不是名字）。

### 状态机最后一次跃迁：Address → Configured

```
[Address 已编址] ──SET_CONFIGURATION(1)──► [Configured 已配置]
 只有 EP0 可用                                ★ 非 EP0 端点全部启用
```

| 变化 | 之前 | 之后 |
|------|------|------|
| 非 EP0 端点（如 Bulk 0x81） | 不存在（管道关闭） | **全部启用** |
| 接口功能 | 未激活 | **激活**（正式"是摄像头"） |
| 供电限额 | 100mA | bMaxPower 声明的值（§1.5） |
| 你能做什么 | 只有 EP0 控制传输 | XU 命令 + SET_INTERFACE 开流 + Bulk 取流 |

**第六篇的所有实战（XU 命令、取流、码流切换）全部发生在 Configured 之后。** 前八步是"面试"，这步是"签合同上岗"。

### ★ 设计哲学：为什么默认不启用

1. **先面试、后上岗。** Host 读完描述符链（4.4~4.8），完全了解设备能力，才决定是否激活——"知情同意"。
2. **省电与安全。** 插入后默认零功能、供电限制 100mA。激活是显式动作——没有任何设备能"插上就全速运转"。总线级安全闸门。
3. **可撤销。** `SET_CONFIGURATION(0)`（wValue=0）卸载配置、端点全关、退回 Address——"下岗"。**双向开关**，不是单向发令枪。

类比：门禁激活——入职最后 HR 刷一下卡：工位通电、门禁生效。这张卡也能随时反刷把人请出去。

### 总线上的最后一笔对话

```
事务1: SETUP Token(ADDR=5) → DATA0 [00 09 01 00 00 00 00 00] → 设备 ACK
事务2: IN Token(ADDR=5) → 设备回 DATA1 [空] → STATUS 签收
       └─ 签收完成瞬间，设备跃迁 Configured，端点全部挂上总线
```

从 ① 插入到 ⑨ 签收，全程只用 EP0 和一个标准请求家族——没有第二个端点参与。这就是 EP0 被类比为"$SYS/ 系统主题"的全部含义。

### 第 ⑩ 步（简提）：驱动加载，总线之外的事

SET_CONFIGURATION 之后总线枚举结束，剩下 OS 的活：按 VID:PID（4.6）+ Class 匹配驱动 → 2bdf:0101 匹配 UVC 驱动 → 设备就绪。这就是 `lsusb` 立刻能列出设备（枚举已完成），但摄像头灯要等一两秒才亮（驱动加载）的原因。

### 一句话总结

**SET_CONFIGURATION 用两阶段控制传输把 bConfigurationValue（4.7 伏笔）填进 wValue，让设备完成状态机最后一次跃迁——非 EP0 端点全部启用，功能激活。"先面试、后上岗"的签字动作，也是双向开关（wValue=0 下岗）。总线上的枚举到此收官，剩下的是 OS 的驱动匹配。**

## 4.11 阶段 7：Wireshark + USBpcap 实战抓包（纸上推演对照真实总线）

### 工具与环境（Windows）

**USBPcap**：Windows 上抓 USB 流量的驱动层抓包器（Wireshark 安装向导里可勾选）。装完后系统多出几个 USBPcap 接口，**每个 USB 控制器一个**——设备插在哪个控制器，就抓哪个接口。

- 抓包需要管理员权限
- **★ 重要认知：USBPcap 抓的也是 URB 层**——和 Bus Hound 同一个高度。Token/PID/CRC/64B 事务拆分照样看不到（§2.2a 的局限，换工具也成立）。想验证 Token/64B 拆分需要硬件分析仪（Beagle USB 480 之类，万元级），URB 层对学协议已足够

### 抓包流程

```
① 打开 Wireshark → 选 USBPcap 接口（设备插在哪个控制器就选哪个）
② 开始抓包 → 拔下设备 → 等 2 秒 → 插回 → 等设备灯亮 → 停止
③ 过滤：usb.transfer_type == 0x02   （0x02 = URB_CONTROL，只看控制传输）
```

| 过滤表达式 | 含义 |
|-----------|------|
| `usb.transfer_type == 0x02` | 只看控制传输 |
| `usb.device_address == 5` | 只看地址 5 的设备 |
| `usb.setup.bmRequestType == 0x80` | 只看 IN 方向 Standard 请求 |
| `usb.setup.bRequest == 0x06` | 只看 GET_DESCRIPTOR |

### 逐包匹配 10 步时间线

| 包 | URB 内容 | 对应节 | 验证要点 |
|---|---------|--------|---------|
| 1 | CTL: `80 06 00 01 00 00 08 00` | 4.4 | wLength=8（或现代 Windows 直接 18，见 4.11a） |
| 2 | IN: `12 01 ... 00 40` | 4.4 | bMaxPacketSize0 在 offset 7 |
| 3 | CTL: `00 05 05 00 00 00 00 00` | 4.5 | SET_ADDRESS=5（设备级抓包看不到，见 4.11a） |
| 4 | CTL: `80 06 00 01 00 00 12 00` | 4.6 | wLength=18 |
| 5 | IN: 18 字节（含 VID/PID） | 4.6 | 自报家门 |
| 6 | CTL: `80 06 00 02 00 00 09 00` | 4.7 | Config 头 9 字节 |
| 7 | IN: 9 字节（含 wTotalLength） | 4.7 | 总长 |
| 8 | CTL: `80 06 00 02 00 00 <总长>` | 4.8 | wLength=wTotalLength |
| 9 | IN: **一行读回整链** | 4.8 | ★ 总线多笔 64B 事务被合并显示 |
| 10 | CTL: `80 06 00 03 00 00 FF 00` | 4.9 | String #0（LANGID） |
| 11 | CTL: `80 06 01 03 09 04 FF 00` | 4.9 | wIndex=0x0409 登场 |
| 12 | IN: UNICODE 字符串 | 4.9 | UTF-16LE |
| 13 | CTL: `00 09 01 00 00 00 00 00` | 4.10 | SET_CONFIGURATION(1) |

**两个"抓不到"**：
1. **① 插入、② 复位抓不到**——纯电气行为，没有 URB，抓包从第 ③ 步（第一个 SETUP）开始
2. 长链（如 433/911 字节）在总线上是 7/15 笔 64B 事务——USBPcap 像 Bus Hound 一样合并为一行（4.8 推演过拆分，抓包看不到但你知道它发生了）

### 为什么这步重要

1. **眼见为实**：纸上推演的每一个字节都能在抓包里对上号
2. **调试硬技能**：设备不识别时看抓包卡在第几包——没有包 1~2=电气问题；卡在包 3 后=Set_Address 后失联；包 8 的 wLength 与包 7 的 wTotalLength 对不上=固件 bug
3. **换设备通吃**：U 盘、键盘、摄像头枚举骨架都一样

### 一句话总结

**USBPcap+Wireshark 把枚举的 10 步时间线变成 13 行可核对的 URB 记录。抓包是 URB 层（看不到电气层 ① ② 和 64B 拆分），但 SETUP 字节流完整可验——纸上推演的每一个字节都能在抓包里对上号，枚举调试从此有据可查。**

## 4.11a 真机抓包实战分析（2026-08-15，TM5X 2bdf:028a）

> 抓包文件：`capture-tm5x-2bdf028a.pcapng`（206 包，从 174,032 包的全量抓包 `capture.pcapng` 中按设备地址切出）。设备：海康 TM5X 测温机芯，PID 028a（不是之前实战的 0101）。

### 抓包全景

| 地址 | VID:PID | 身份 |
|------|---------|------|
| 1 | 8087:0026 | Intel 主板内置（root hub） |
| 2 | 04f2:b76f | Chicony 笔记本内置摄像头 |
| 3 | 12d1:3a07 | 华为设备 |
| 4 | 372e:103e | HID 外设（4B 小包） |
| 5 | 24ae:4415 | Rapoo 无线鼠标（17.3 万包，流量主角） |
| **7** | **2bdf:028a** | **★ TM5X 机芯** |

设备字符串："2 K USB Camera"、"CDC Serial"、"HID Interface"——**UVC + CDC + HID 三合一复合设备，正是 SDK 三大目标的合体**。

### ★ TM5X 枚举逐包对照（三处真机勘误）

| 抓包实况 | 对应课程 | 对照结果 |
|---------|---------|---------|
| GET_DESC(Device) **wLen=18 一次读完** | 4.4/4.6 | ⚠️ 现代 Windows 不做 8 字节探测，直接要 18 |
| 响应：`df 2b 8a 02` = 2bdf:028a，bcdDevice=0x3000 | 4.6 | ✓ 完全对上 |
| GET_DESC(Config) wLen=9 → wTotalLength=**911** | 4.7 | ✓✓ 先读 9 字节头 |
| GET_DESC(Config) wLen=911 → 整链 | 4.8 | ✓✓（911=14×64+15，拆多笔事务） |
| SET_CONFIGURATION(1) | 4.10 | ✓ |
| String：**先读 4 字节拿 bLength 再读全** | 4.9 | ⚠️ Windows 用"学院派"两步读，不是 wLen=255 一次读 |
| SET_ADDRESS | 4.5 | ⚠️ **设备级抓包看不到**（SET_ADDRESS 是 hub 层 URB，发往 hub 端口而非设备） |

**三处勘误的实质**：教材讲的是"规范经典做法"（8 字节探测、255 一次读），真机是现代 Windows 的行为（18 一次读、4 字节两步读）。两者都成立——8 字节保底依然有效（bMaxPacketSize0 在 offset 7，18 字节内一定读得到；短包规则兜底）。**抓包是最终裁判。**

### TM5X 设备结构（911 字节链）

- **UVC**：VC 接口 + 中断状态端点 EP 0x81（16B）；VS 接口 alt0=零带宽 / alt1=**等时** EP 0x88（高带宽 5120B/微帧）
- **CDC**：串口接口（IF 4 起）
- **HID**：厂商自定义（Report ID=1，Report Count=1023 字节大报文）
- 视频走**等时**——对比 2bdf:0101 的 Bulk：同一厂商不同产品，完整性 vs 实时性选择不同（第十会话权衡的实例）

### SDK 活动拆解（+7.94s 起）

**1. 三合一初始化**：SET_INTERFACE(IF=1/3/5, alt=0)

**2. UVC"发现五件套"轮询（§6.8 的实战版）**，5ms 周期，wVal=CS_ID<<8 高字节（海康惯例再验证）：

```
a1 86 wVal=0400 → GET_INFO  响应 1B: 03        （CS 0x04=协议版本）
a1 82 wVal=0400 → GET_MIN   响应 4B: 05 00 00 00
a1 83 wVal=0400 → GET_MAX   响应 4B: c4 09 00 00（2500）
a1 84 wVal=0400 → GET_RES   响应 4B: 01 00 00 00
a1 87 wVal=0400 → GET_DEF   响应 4B: c4 09 00 00
然后轮询 CS 0x02（图像：0/255/128/100/200/300/600...）、CS 0x06（错误码）
```

**3. CDC 串口初始化（学习计划 6.13 活样本）**：

```
a1 21 wIdx=0004 wLen=7 → GET_LINE_CODING  → 7B 全 0（波特率默认 0）
21 22 wIdx=0004 wLen=0 → SET_CONTROL_LINE_STATE
21 20 wIdx=0004 wLen=7 → SET_LINE_CODING
a1 21 wIdx=0004 wLen=7 → GET_LINE_CODING（回读确认）
```

**4. HID Report Descriptor 读取**（35B）：`05 81 09 82 a1 01 85 01 09 82 15 80 25 7f 75 08 96 ff 03 81 02...`（学习计划 6.2 活样本）

### 异常实例（活教材）

| 现象 | 解释 |
|------|------|
| 3× STALL（STALL_PID） | SDK 试探了设备不支持的请求（如 GET_RES 发到不支持的 CS）——**第五会话"STALL=硬件拒绝"的活例子**，SDK 靠 STALL 试探能力 |
| EP 0x81 读失败（XACT_ERROR/C0010000） | VS 还在 alt=0，流端点不存在就去读——**"没开流就读流"的典型错误** |
| 全程 0 字节视频数据 | 本次只做了初始化，没开流取流 |

### 教学价值

Phase 4 纸上推演全部落到真机：枚举 10 步在 206 个包里全部找到对应，还收获 3 处真机勘误 + 三合一设备结构 + 三类协议（UVC/CDC/HID）初始化的活样本。**下次抓取流流量（等时 EP 0x88）可对照 §2.13 等时传输。**

## 4.12 枚举失败常见原因排查（Phase 4 收官）

### 排查总纲：卡点定位法

枚举是 10 步线性流水线（4.2~4.10）。**每一步失败，症状都不同，卡住的位置就是故障所在的层。** 排查不是瞎猜，是定位卡点：

> **先确定设备走到了哪一步，再查那一步的嫌疑犯。**

两个定位工具：**抓包看卡在第几包（4.11），设备管理器看报错文案**。两者对照，故障层基本锁定。

### 完整排查树

```
插入设备没反应 / 黄叹号
│
├─ ① 电气层（无 URB 流量，设备管理器完全没动静）
│    ├─ 线缆断 / 端口坏 / VBUS 无 5V        → 换线、换口、换电脑三连
│    ├─ 设备上拉电阻故障（D+/D- 无电平变化）→ Host 根本不知道有设备（4.2）
│    └─ 供电过流（大功耗设备插无源 hub）     → 端口报"电涌"被强制关闭
│
├─ ② 复位层（罕见）
│    └─ 复位失败 / 设备对 SE0 无响应         → 抓包无任何 URB
│
├─ ③⑤ 描述符层（★ 最常见）
│    ├─ bMaxPacketSize0 填错（FS 设备报 512）→ 分片错位，描述符读回来全乱
│    ├─ 描述符 CRC16 校验错（固件 bug）      → Host 重试 3 次放弃
│    └─ bLength 与实际长度不符               → 传输错位
│    └─ 症状：★"未知 USB 设备（设备描述符请求失败）"= 错误代码 43
│
├─ ④ 地址层
│    └─ Set_Address 后设备不响应新地址       → 后续全部超时
│    └─ 症状：★"未知 USB 设备（设定地址失败）"——直指 4.5 的换牌动作
│
├─ ⑥⑧ 配置层
│    ├─ wTotalLength 填错 → 链读回来是坏的（4.7 的总长对不上）
│    └─ Config 链内部拼错（Interface/Endpoint 描述符结构错）→ 驱动解析失败
│
├─ ⑨ 配置激活层
│    ├─ ★ Set_Config STALL → 设备拒绝这个配置号（4.10 的签字被拒）
│    ├─ 供电超限：bMaxPower 声明的电流 Host 供不起 → 激活失败
│    └─ 带宽不足：等时端点申请超帧带宽预算（§2.13）→ SET_INTERFACE 失败
│
└─ ⑩ 驱动层（总线之外）
     ├─ VID:PID 无驱动匹配（4.6 的钥匙没用上）→ 黄叹号"未安装驱动程序"= 代码 28
     └─ 驱动加载失败（签名/崩溃）            → 代码 10"设备无法启动"
```

### Windows 错误码速查

| 报错文案 | 代码 | 卡在哪一步 | 嫌疑犯 |
|---------|:---:|-----------|--------|
| 设备描述符请求失败 | **43** | ③⑤ 描述符 | bMaxPacketSize0 错 / CRC 错 / 固件没响应 |
| 设定地址失败 | — | ④ 地址 | 固件换牌逻辑错（4.5） |
| 未安装驱动程序 | **28** | ⑩ 驱动 | 无 INF 匹配 / VID:PID 不在驱动库里 |
| 设备无法启动 | **10** | ⑩ 驱动 | 驱动加载崩溃 |
| 端口上的电涌 | — | ① 电气 | 供电过流，端口被关 |

Ubuntu 对应物：`dmesg` 里的 `device descriptor read/64, error -71`（描述符层）、`device not accepting address X, error -71`（地址层）——和 Windows 的 43/设定地址失败一一对应。

### 三个高频坑的"为什么"

**坑 1：bMaxPacketSize0 填错（③⑤）**：4.4 的 8 字节保底建立在"设备自报的 maxpacket 是对的"之上。FS 设备填 512（只有 HS 合法），Host 按 512 分片、设备只吐 64 → 事务错位 → 描述符全乱 → 重试 3 次放弃报 43。**自报家门报错了，后面的对话全部建立在这个错误数字上。**

**坑 2：Set_Address 后失联（④）**：4.5 的规则是 STATUS 签完才换牌。固件偷懒"收到 SETUP 就切地址"——Host 发 STATUS 用地址 0 喊，没人应答 → 传输失败 → 重试同样结果 → 报"设定地址失败"。**一个 2ms 的时序细节，写错就是永远枚举不成功。**

**坑 3：Set_Config STALL（⑨）**：wValue 填的是 bConfigurationValue（设备自报的编号）。固件声明配置号 2、Host 发 1 → 不认识 → STALL（第五会话：STALL=硬件拒绝）。或者配置链里有固件实际不支持的资源。**"签字阶段被拒"意味着设备自己描述的东西自己做不到。** 4.11a 抓包里的 3 次 STALL 是业务层试探；枚举失败时的 STALL 会出现在 Set_Config 位置——抓包一看便知。

### 排查武器清单

```
① 换线/换口/换电脑三连            → 区分设备坏还是主机坏
② 设备管理器报错文案              → 直接指向卡点（43/28/设定地址失败）
③ Wireshark + USBPcap（4.11）    → 抓包看卡在第几包，卡点即故障层
④ sudo lsusb -v                  → 描述符树是否完整
⑤ sudo dmesg | grep usb          → Ubuntu 侧枚举日志
⑥ 禁用→启用设备                   → 强制软件重新枚举
```

### Phase 4 收官

4.1~4.12 走完三段闭环：纸上推演（4.2~4.10）→ 真机验证（4.11/4.11a）→ 故障排查（4.12）。**枚举是整个 USB 协议的主干**——之后写的每一行 libusb 代码、每一个新设备调试，都跑在这条流水线上。

### 一句话总结

**枚举失败排查 = 卡点定位——症状（设备管理器文案/抓包断点）指向 10 步里的某一步，那一步就是故障层。三大高频坑各有原理课：bMaxPacketSize0 错（4.4 的分片基础被破坏）、Set_Address 失联（4.5 的换牌时序）、Set_Config STALL（4.10 的签字被拒）。**

---

# 第五篇：真实设备描述符实战

> 基于三台真实海康 USB 摄像头，从字节级拆解 USB 描述符。

## 5.1 三台设备速览

| 项目 | 设备 1 (HikCamera #1) | 设备 2 (HikCamera #2) | 设备 3 (2K USB Camera) |
|---|---|---|---|
| VID : PID | 0x2BDF : 0x0101 | 0x2BDF : 0x0101 | 0x2BDF : 0x028A |
| 序列号 | G11376317 | E83518457 | 无数据 |
| 功能 | UVC 视频 | UVC 视频 | UVC 视频 + UAC 音频 |
| 接口数 | 2（IAD 绑定） | 2（IAD 绑定） | ≥4（推断） |
| 描述符链总长 | 433 B | 433 B | 无数据 |
| 视频格式 | YUY2/MJPEG/H.264, 最高640×360@30 | 同左 | MJPG/NV12/YUY2, 最高2560×1440@30 |
| 音频 | 无 | 无 | PCM 16kHz/16bit/单声道 |

## 5.2 描述符获取流程：枚举

```
 设备                       Host
  │  上电 + 复位 (Reset)       │
  ├───────────────────────────►│  设备在默认地址 0 上等待
  │◄───────────────────────────┤  GET_DESCRIPTOR(Device, 0, 18)  ① 读设备描述符
  │◄───────────────────────────┤  SET_ADDRESS(7)                 ② 分配地址
  │◄───────────────────────────┤  GET_DESCRIPTOR(Device, 0, 18)  ③ 新地址重读
  │◄───────────────────────────┤  GET_DESCRIPTOR(Config, 0, 9)   ④ 只读9B头
  │  9 字节应答 (wTotalLength=433)                               → 知道链长
  │◄───────────────────────────┤  GET_DESCRIPTOR(Config, 0, 433) ⑤ 完整链一次性返回
  │◄───────────────────────────┤  GET_DESCRIPTOR(String, ...)    ⑥ 按需取字符串
  │◄───────────────────────────┤  SET_CONFIGURATION(1)           ⑦ 进入Configured
```

三个关键点：
1. 描述符是按需索取——Host 先拿 wTotalLength，再按这个长度一次取回整条链
2. 完整链一次性返回——配置+IAD+接口+类专用+端点，全在一个包里
3. 字符串是懒加载——描述符里只放索引（iManufacturer=0x01），Host 需要显示时才单独请求

## 5.3 Device Descriptor 关键字段

### bDeviceClass = 0xEF，为什么不直接写 0x0E (Video)？

设备 1/2 明明是摄像头，设备级类码却是 `0xEF (Miscellaneous)`：

- USB 规范规定：**使用 IAD 的复合设备，设备级类码必须声明为 0xEF**（子类 0x02，协议 0x01 = "使用 IAD"）
- Host 看到 0xEF/0x02/0x01 就知道："这是一个由多个功能组成的复合设备，功能划分请看配置链里的 IAD"
- 真正的功能分类（Video = 0x0E）写在 IAD 的 `bFunctionClass` 里

**一句话：设备级 class 管"整台机器是不是复合的"，IAD 的 function class 才管"每个功能是什么"。**

## 5.4 IAD（Interface Association Descriptor）

设备 1 的 IAD：

```
bFirstInterface = 0x00    ← 接口 0 起
bInterfaceCount = 0x02    ← 绑定接口 0~1
bFunctionClass  = 0x0E    ← ★ 真正的功能分类：Video
bFunctionSubClass = 0x03  ← Video Interface Collection
```

Host 的 UVC 驱动（Windows 的 usbvideo.sys）就是看到 `bFunctionClass=0x0E, bFunctionSubClass=0x03` 才决定加载自己的。

## 5.5 Interface Descriptor — VC vs VS

| 字段 | 接口 0 (VC) | 接口 1 (VS) |
|------|-------------|-------------|
| bInterfaceNumber | 0x00 | 0x01 |
| bInterfaceClass | 0x0E (Video) | 0x0E (Video) |
| **bInterfaceSubClass** | **0x01 (Video Control)** | **0x02 (Video Streaming)** |

bInterfaceSubClass 是 UVC 描述符体系的第一道分叉口——Host 据此区分控制接口和流接口。

## 5.6 Endpoint Descriptor

设备 1 的两个端点：

| 字段 | EP3 IN (Interrupt) | EP1 IN (Bulk) |
|------|-------------------|---------------|
| bEndpointAddress | 0x83 (IN, EP3) | 0x81 (IN, EP1) |
| bmAttributes | 0x03 (Interrupt) | 0x02 (Bulk) |
| wMaxPacketSize | 0x0010 (16 B) | 0x0200 (512 B, HS) |
| bInterval | 0x08 (HS: 16 ms) | 0x00 (忽略) |

设备 1/2 用 Bulk 传视频是因为分辨率低（最高 640×360），Bulk 的重传机制反而更省心。设备 3 做 2K@30 则推断使用等时端点。

### 为什么视频用 Bulk 而不是等时？（完整性 vs 实时性）

"视频 = 等时"是典型，不是规定——传输类型由设备在端点描述符里声明（bmAttributes），Host 照单执行。

| | 等时传输 | 批量传输 |
|---|---|---|
| 带宽 | **保证**（帧内预留） | 吃剩余带宽，不保证 |
| 延迟 | **固定节拍** | 不保证（拥堵时可能延迟） |
| 出错 | **不重传**，错了就丢 | **CRC 错了自动重传**，保证完整 |

厂商的选择是"完整性 vs 实时性"的权衡：
- **罗技摄像头（等时）**：视频会议场景，花一帧无所谓、卡顿才难受 → 实时性优先
- **热成像（Bulk）**：低分辨率带宽需求小，测温数据错一个像素可能比慢一点更糟 → 完整性优先

海康的算盘：分辨率低（120×160 / 640×360）→ 带宽完全够 → 用 Bulk 白赚"重传保证完整"，代价（延迟不保证）在慢变化画面上无所谓。同一个厂商的 2K@30 设备（设备 3）就必须上等时——那个带宽和实时性 Bulk 扛不住。

规范演变：UVC 1.0/1.1 只定义等时，UVC 1.5 才把 Bulk 写进规范——业界先出现"低带宽、要完整"的设备，规范才追认。海康属于提前这么干的厂商实现。

类比：等时 = 直播（按时播放，信号不好就花屏不重放）；Bulk = 文件下载（慢点可以，一个字节都不能错）。

## 5.7 UVC 类专用描述符机制（0x24 / 0x25）

UVC 的类专用描述符大量复用同一个 `bDescriptorType`：

```
bDescriptorType = 0x24 (Video Control Interface)
   └─ 由"所属接口的 bInterfaceSubClass"决定含义
        ├─ 接口 subclass = 0x01 (VideoControl) → VC 类描述符
        │     0x01 VC Header          0x02 Input Terminal
        │     0x03 Output Terminal    0x05 Processing Unit
        │     0x06 Extension Unit
        └─ 接口 subclass = 0x02 (VideoStreaming) → VS 类描述符
              0x01 VS Input Header     0x04 Uncompressed Format
              0x06 MJPEG Format        0x10 Frame-Based Format (H.264)
              0x0D Color Matching
```

**为什么可以复用同一个类型码？** 因为解析上下文不同——Host 遍历描述符链时，先读到接口描述符，知道当前处于哪个接口（subclass 是多少），之后遇到的 0x24 就按该接口的语义解析。

### UVC 拓扑图：Terminal / Unit 链

```
  物理相机传感器
       ↓
  Input Terminal (IT, ID=2, ITT_CAMERA)
       ↓
  Processing Unit (PU, ID=5, 亮度/对比度/增益)
       ↓
  Extension Unit (XU, ID=10, 厂商私有扩展, 15 controls)
       ↓
  Output Terminal (OT, ID=3, TT_STREAMING)
       ↓
  VS 流接口 (接口 1) → EP1 IN Bulk 传视频
```

### VC Header Descriptor 逐字节（设备 1）

```
偏移: 0  1  2  3  4  5  6  7  8  9  10 11 12
      0D 24 01 10 01 51 00 00 6C DC 02 01 01
```

| 偏移 | 字段 | 值 | 含义 |
|------|------|------|------|
| 0 | bLength | 0x0D (13) | 固定 |
| 1 | bDescriptorType | 0x24 | Video Control Interface |
| 2 | bDescriptorSubtype | 0x01 | VC Header |
| 3-4 | bcdUVC | 0x0110 | UVC 1.10 |
| 5-6 | wTotalLength | 0x0051 (81) | VC 类专用子链总长 |
| 7-10 | dwClockFreq | 0x02DC6C00 | 48 MHz |
| 11 | bInCollection | 0x01 | 1 个 VS 接口关联 |
| 12 | baInterfaceNr[1] | 0x01 | VS 接口号 = 1 |

## 5.8 设备 1 完整 433 字节描述符链追踪

### 逐段验算

```
配置头 9 + IAD 8 + 接口 9×2 = 35
VC 类子链:  13 + 18 + 12 + 29 + 9  = 81   (0x51) ✔
VS 类子链:  16 + 27 + 90 + 11 + 90 + 28 + 30 + 6 = 298 (0x12A) ✔
端点:       7 + 5 + 7 = 19
35 + 81 + 298 + 19 = 433 ✔
```

### 逐段偏移追踪

```
偏移          描述符                               长度      累计
0x0000  ┌─ Configuration Descriptor               9 B       0x0009
0x0009  ├─ IAD Descriptor                         8 B       0x0011
0x0011  ├─ Interface 0 (VC) Descriptor             9 B       0x001A
0x001A  │   ├─ VC Header Descriptor               13 B       0x0027
0x0027  │   ├─ VC Input Terminal Descriptor       18 B       0x0039
0x0039  │   ├─ VC Processing Unit Descriptor      12 B       0x0045
0x0045  │   ├─ VC Extension Unit Descriptor       29 B       0x0062
0x0062  │   ├─ VC Output Terminal Descriptor       9 B  ──▶  81 B (0x51)
0x006B  │   ├─ Endpoint EP3 IN Interrupt           7 B       0x0072
0x0072  │   └─ Class-Specific VC EP (0x25)         5 B       0x0077
0x0077  ├─ Interface 1 (VS) Descriptor             9 B       0x0080
0x0080  │   ├─ VS Input Header Descriptor         16 B       0x0090
0x0090  │   ├─ VS Uncompressed Format             27 B       0x00AB
0x00AB  │   ├─ VS Uncompressed Frame ×3           90 B       0x0105
0x0105  │   ├─ VS MJPEG Format                    11 B       0x0110
0x0110  │   ├─ VS MJPEG Frame ×3                  90 B       0x016A
0x016A  │   ├─ VS Frame-Based Format (H.264)      28 B       0x0186
0x0186  │   ├─ VS Frame-Based Frame               30 B       0x01A4
0x01A4  │   └─ VS Color Matching                   6 B  ──▶ 298 B (0x12A)
0x01AA  └─ Endpoint EP1 IN Bulk                    7 B       0x01B1
                                                           ────────
                                         合计 = 433 B = 0x01B1 ✔
```

## 5.9 设备 1 vs 设备 2 差异分析

| 对比项 | 设备 1 | 设备 2 | 说明 |
|---|---|---|---|
| 序列号 | "G11376317" | "E83518457" | **唯一描述符差异** |
| 设备地址 | 0x07 | 0x08 | Host 枚举时分配，不是描述符 |
| 抓取时电源状态 | D3（低功耗） | D0（工作态） | 造成 Qualifier 抓取成败 |
| Device Qualifier | **请求失败** | 完整返回 (10 字节) | 设备在 D3 无法应答 |
| Other Speed Configuration | 未抓到 | 完整返回 (433 字节) | Bulk 512B→64B, bInterval HS→FS语义 |

### Device Qualifier + Other Speed Config：HS→FS 降级备胎

设备 2 的 Other Speed Config 里：
- EP1 IN Bulk: `wMaxPacketSize = 0x0040 (64 B)` —— HS 是 `0x0200 (512 B)`
- EP3 IN Interrupt: `bInterval = 0x08` —— FS 语义下 = **8 ms**，HS 语义下同一字节 = **16 ms**

同一字节，两种速度两种含义。

## 5.10 设备 3 从 KS 数据反推描述符结构

设备 3 没有原始描述符 dump，但从 Windows 驱动层数据反推：

### 已知事实

| 线索 | 值 | 反推出什么 |
|---|---|---|
| Device ID | `USB\VID_2BDF&PID_028A&REV_3000&MI_00` | VID/PID/bcdDevice, 复合设备 |
| 视频节点 | `MI_00` + usbvideo.sys | 接口 0 = VC |
| 音频节点 | `MI_02` + usbaudio.sys | 接口 2 = AC |
| 接口号跳跃 | 有 MI_00 和 MI_02，没有 MI_01/03 | VS/AS 被 IAD 并入功能 |

### 推断结构

```
Device Descriptor          bDeviceClass = 0xEF（复合设备）
└── Configuration          bNumInterfaces ≥ 4
    ├── IAD #1             bFunctionClass=0x0E (Video)
    │   ├── Interface 0: VC     (MI_00)
    │   └── Interface 1: VS     推断为等时端点，多档 Alternate Setting
    ├── IAD #2             bFunctionClass=0x01 (Audio)
    │   ├── Interface 2: AC     (MI_02)
    │   └── Interface 3: AS     等时端点 (32 kB/s)
    └── (字符串)
```

### 为什么 2560×1440@30 MJPEG 需要等时端点

- HS 等时理论上限：~24.6 MB/s
- 原始 YUY2 2560×1440@30 = 221 MB/s，远超 HS 总线能力
- MJPEG 压缩后通常 0.5~2 MB/帧，30fps ≈ 15~60 MB/s——仍在等时预算内
- 设备 1/2 用 Bulk 因为分辨率低；设备 3 做 2K@30 必须用等时 + MJPEG 压缩

---

## 第五篇 FAQ

### Q1: 为什么 bDeviceClass 不直接写 0x0E (Video)？

因为摄像头是复合设备（一个 Video 功能 = VC + VS 两个接口），必须用 IAD。USB 规范规定：使用 IAD 的复合设备，设备级必须声明 0xEF。真正的功能分类在 IAD 的 bFunctionClass。

### Q2: Alternate Setting 在描述符里怎么体现？

同一接口号出现多个接口描述符，bInterfaceNumber 相同、bAlternateSetting 依次递增。Host 用 `SET_INTERFACE` 切换。应用开视频时驱动按所选格式挑一档 alt 并切换，用完切回 alt 0 释放带宽。

### Q3: bMaxPacketSize0 对 HS 设备为什么固定 64 字节？

USB 2.0 规范 §9.6.1 硬性规定：HS 设备的 EP0 最大包长必须是 64 字节。HS 设备统一 64，Host 栈的缓冲区与调度器不用为不同设备准备不同尺寸。

### Q4: Device Qualifier 什么情况下 Host 会请求？

只有能跑双速（HS 与 FS）的设备才有 Device Qualifier；单速设备必须对该请求回 STALL。Host 在设备以 HS 运行时请求它，拿到"若在 FS 运行会是什么样"的信息。

### Q5: IAD 和 Interface Descriptor 里的 Class 有什么不同？

两者是两个层级：IAD 的 bFunctionClass 描述一组接口（功能级），决定归哪个类驱动管；接口的 bInterfaceClass 描述单个接口（接口级），驱动内部再按 subclass 分派角色。

### Q6: UVC Extension Unit 的 15 个 vendor-specific controls 是干什么的？

设备 1/2 的 XU（Unit ID 10）声明 `bNumControls=15`，但 bmControls 只置位低 10 位（实际启用 control 1~10）。这些是标准 UVC 没定义的厂商私有控制——通常是曝光模式、增益、图像翻转等厂商标定参数。

### Q7: 设备 1 & 2 的 bmControls 全是 0，怎么控制摄像头？

Camera IT 和 PU 的 bmControls 全是 0——标准控制真的不存在。实际控制通道是：(1)XU 的 vendor-specific 控制（10 个私有控制，需厂商 SDK）；(2)VS 接口的流控制（PROBE/COMMIT）；(3)其余参数固件自动管理。**bmControls=0 只代表"标准控制没实现"，不代表设备不可控。**

### Q8: 为什么 Bus Hound 抓包看不到 Token 包、Handshake 包和 PID 字段？

Bus Hound 是软件层抓包工具，工作在 USB 驱动栈的 URB 层。Token 包、Handshake 包、PID 字节、SYNC 字段、CRC5/CRC16——这些全在硬件层由 USB 主机控制器（xHCI）自动生成和解析，软件连看都看不到。

```
你的应用
   ↓
WinUSB / 设备驱动         ← Bus Hound 在这里抓包（URB 层）
   ↓
USB 主机控制器驱动 (xHCI)
   ↓
USB 主机控制器硬件         ← PID/SYNC/CRC 在这里被硬件处理掉了
   ↓
物理总线 (D+/D-)
```

要看到 PID/Token/Handshake？需要硬件 USB 协议分析仪（Ellisys、Total Phase Beagle 等，$500+）。

### Q9: 为什么批量传输的 payload 前面 8 字节长得跟控制传输的 SETUP 包一模一样？

**这不是 USB 规范要求的——是厂商自己抄过去的。** 核心原因：在 EP0 上已经写了一套命令解析代码，再为批量端点重新设计一套格式太傻了。直接把 EP0 那 8 字节头搬过来，解析代码复用。这不算违反 USB 规范——批量端点是"纯数据管道"，数据里面是什么格式完全是厂商的自由。

### Q10: STATUS 阶段只是锦上添花的"收到了"吗？

**不是。STATUS 是不可或缺的协议硬需求——它是设备拒绝不支持的 SETUP 命令的唯一切入点。**

SETUP 必须 ACK（不能在这里拒绝），DATA 可能不存在。那拒绝在哪里表达？STATUS：

```
SETUP:  "给我不存在的描述符 #99"  → Device → ACK (必须受理)
DATA:   无数据
STATUS: Device → STALL ← ❌ 拒绝唯一发生在这里！
```

**三段式不是冗余设计——是权力分立：** SETUP=提出请求，DATA=提供数据，STATUS=宣布判决。

---

# 第六篇：UVC XU 控制与取流实战

---

## 6.1 UVC XU 扩展协议设计

### CS_ID + SubFunc 二级命名空间

```
CS_ID = 0x05  功能切换（FUNC_SWITCH）
CS_ID = 0x17  云台控制（PTZ_CONTROL）
CS_ID = 0x18  图像参数（IMAGE_CONFIG）
CS_ID = 0x19  系统信息（SYS_INFO）
CS_ID = 0xF0  错误码（ERRCODE）

每个 CS_ID 下可挂 0x01~0xFF 个 SubFunc
总命令空间：~200 × 255 ≈ 51,000 个独立控制项
```

### CS_ID 分配策略

| 范围 | 用途 | 示例 |
|------|------|------|
| 0x01~0x04 | 保留（兼容 UVC 标准） | — |
| 0x05 | 功能切换（FUNC_SWITCH） | 协议基础设施 |
| 0x06 | 错误码读取（ERRCODE） | 0x00=成功，0x01=忙 |
| 0x10~0x1F | 设备控制类 | 0x17=云台，0x18=图像 |
| 0x20~0x2F | 数据流类 | 0x20=码流类型，0x21=帧率 |
| 0x30~0x3F | 系统信息类 | 0x30=固件版本，0x31=温度 |
| 0x80~0xEF | 厂商私有 | 扩展自定义功能 |
| 0xF0~0xFF | 诊断/调试 | 0xF0=错误码，0xF1=日志 |

### 核心流程（三阶段）

```
┌─────────────────────┐
│ 1. FUNC_SWITCH      │  SET_CUR, CS_ID=0x05
│ Data: [CS_ID, Sub]  │  选择目标功能
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│ 2. GET_LEN          │  GET_LEN, CS_ID=目标
│ 返回 2 字节 LE      │  获取参数长度
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│ 3. GET_CUR / SET_CUR│  读写参数数据
│ 长度 = GET_LEN 值   │  SET_CUR 后读错误码确认
└─────────────────────┘
```

### STALL vs 错误码：两层拒绝

| | STALL（硬件层） | 错误码（应用层） |
|---|---|---|
| 含义 | "我不认识这个请求" | "上次那个命令参数不对" |
| libusb 返回 | `LIBUSB_ERROR_PIPE` | 成功，但 err≠0 |
| 适用场景 | CS_ID 完全不存在 | SubFunc 不支持、参数非法等 |

推荐的分层拒绝策略：
```
CS_ID 不在白名单内    → STALL（硬件拒绝，最快）
CS_ID 在白名单内，但:
  SubFunc 不支持       → ACK → 错误码 0x09
  参数值非法           → ACK → 错误码 0x04 或 0x08
```

---

## 6.2 新设备上手实操指南

### 三步找到所有参数

**第 1 步：找到设备 VID/PID**

```bash
lsusb
# Bus 003 Device 005: ID 2bdf:0101 HIK HikCamera
```

**第 2 步：找到 Extension Unit 的 ID**

```bash
sudo lsusb -v -d 2bdf:0101 > /tmp/cam.txt
grep -n "EXTENSION_UNIT\|bUnitID\|bInterfaceNumber\|Video Control" /tmp/cam.txt
```

你会得到三个参数：

| 参数 | 值 | 在 SETUP 包里的位置 |
|------|-----|-------------------|
| VID:PID | `2bdf:0101` | 不在 SETUP 包里，是 `libusb_open_device_with_vid_pid()` 用的 |
| XU Unit ID | `0x0A` | **wIndex 高字节** |
| VC IF number | `0` | **wIndex 低字节** |

**第 3 步：看 bmControls 位图**

```
bmControls = 0xFF, 0x03, 0x00, 0x00
LE 还原为 32-bit: 0x000003FF
bit 0~9 置位 → CS_ID 0x01~0x0A 存在
```

> 位图规则：bit N = 1 → CS_ID(N+1) 存在。bNumControls 声明有 N 个，但实际启用以 bmControls 位图为准。

### SETUP 包 8 字节构造

对于 UVC Extension Unit 的 Class 请求：

| 字段 | UVC XU 约定 | 你的设备值 |
|------|------------|-----------|
| wValue 高字节 | **CS_ID**（你要操作的功能号）—— 海康固件惯例；UVC 规范标准写法是 CS 在低字节 | 0x04 / 0x05 / 等 |
| wValue 低字节 | 0x00 | 0x00 |
| wIndex 高字节 | **XU Unit ID**（lsusb 查的 bUnitID） | 0x0A |
| wIndex 低字节 | **接口号**（Video Control 的 bInterfaceNumber） | 0x00 |

**wIndex 是不变的**：不管你操作哪个 CS_ID，`wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM`。

### 三条 SETUP 包的逐字节构造

| 操作 | bmRequestType | bRequest | wValue | wIndex | wLength |
|------|--------------|----------|--------|--------|---------|
| SET_CUR（写） | 0x21 | 0x01 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 数据长度 |
| GET_CUR（读） | 0xA1 | 0x81 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 参数长度 |
| GET_LEN（问长度） | 0xA1 | 0x85 | `(CS_ID << 8)` | `(XU_ID << 8) \| IF` | 2 |

### 新设备上手的实际顺序

**① 先试 CS_ID=0x04（协议版本）** — 不需要 FUNC_SWITCH，最简单：

```c
// GET_LEN
libusb_control_transfer(devh, 0xA1, 0x85, 0x0004, 0x0A00, len_buf, 2, 1000);
// GET_CUR
libusb_control_transfer(devh, 0xA1, 0x81, 0x0004, 0x0A00, buf, 4, 1000);
```

**如果 GET_LEN 回 STALL**：CS_ID 不存在或 XU_ID 不对。**如果 GET_LEN 成功**：通道通了。

**② 再试带 SubFunc 的 CS_ID** — 走三阶段：FUNC_SWITCH → GET_LEN → GET_CUR。

**③ 未知设备探索** — 用 bmControls 位图找支持的 CS_ID，逐个试 GET_LEN。

### libusb 调用和 SETUP 包的对应关系

```c
libusb_control_transfer(
    devh,
    0xA1,           // → SETUP[0] = bmRequestType
    0x85,           // → SETUP[1] = bRequest
    0x0004,         // → SETUP[2-3] = wValue LE
    0x0A00,         // → SETUP[4-5] = wIndex LE
    buf,            // → DATA 阶段的数据
    2,              // → SETUP[6-7] = wLength LE
    1000            // → 超时，不影响 SETUP 包
);
// 对应 SETUP 包 8 字节: A1 85 04 00 00 0A 02 00
```

> **换 XU Unit ID 只改一个地方**：wIndex 的高字节。

### Transaction vs Control Transfer

```
1 Control Transfer = libusb_control_transfer() 一次调用
  ├── SETUP 阶段 — 1 个 Transaction
  ├── DATA 阶段  — 1 个 Transaction
  └── STATUS 阶段 — 1 个 Transaction

1 Transaction = 一次 Token + Data + Handshake 交换
```

**libusb_control_transfer() = 1 次完整的控制传输 = 2~3 个总线事务。** Bus Hound 显示为一行 CTL + 一行 IN/OUT。STATUS 阶段驱动层已合并，Bus Hound 不显示。

---

## 6.3 标准 UVC 取流完整流程

### 两个 wIndex 体系对比

```
VideoControl (XU):     wIndex = (XU Unit ID << 8) | VC_IF
                           例: (0x0A << 8) | 0 = 0x0A00

VideoStreaming:        wIndex = VS_IF  （没有 Unit ID！）
                           例: 0x00 或 0x01
```

### 取流步骤

```
┌─ 阶段 1：协商参数 ──────────（控制传输，EP0，wIndex=VS_IF）
│
│ ① Probe SET_CUR:  Host 提出想要的参数
│    CTL  21 01  01 00  00 00  1A 00
│    OUT  01 00 80 02 E0 01 00 00 ...26B
│
│ ② Probe GET_CUR:  读回设备实际接受的参数
│    CTL  A1 81  01 00  00 00  1A 00
│
│ ③ Commit SET_CUR: 锁定参数
│    CTL  21 01  01 00  00 00  1A 00
│
├─ 阶段 2：开启流 ────────────（控制传输，EP0，bmRT=Standard）
│
│ ④ SET_INTERFACE: 切换到非 0 的 alternate setting
│    CTL  01 0B  01 00  01 00  00 00    ← bmRT=0x01(Standard!)
│
├─ 阶段 3：读视频数据 ────────（批量传输，EP 0x81）
│
│ ⑤ 循环读帧: libusb_bulk_transfer(devh, 0x81, buf, size, &recv_len, timeout);
│
└─ 关闭流: SET_INTERFACE → Alternate 0（零带宽）
```

### Probe 结构体 26 字节核心字段

```c
struct uvc_probe {
    uint16_t bmHint;              // offset 0:  哪些字段 Host 在意
    uint8_t  bFormatIndex;        // offset 2:  格式号
    uint8_t  bFrameIndex;         // offset 3:  帧描述符索引号
    uint32_t dwFrameInterval;     // offset 4:  帧间隔（100ns 单位）
    uint32_t dwMaxVideoFrameSize; // offset 18: 最大帧缓冲（malloc 参考值！）
    uint32_t dwMaxPayloadTransferSize; // offset 22: 单次传输最大载荷
};
```

### SETUP 包三对比

```c
/* VideoControl XU:     */ wIndex = (XU_ID << 8) | VC_IF;   // 0x0A00
/* VideoStreaming:      */ wIndex = VS_IF;                   // 0x0000
/* SET_INTERFACE 开流:  */ bmRT = 0x01(Standard), bReq = 0x0B, wValue = alt
```

### 开流 = SET_INTERFACE 切通道：三层视图

"开流"不是 SET_INTERFACE 之外的另一个动作——UVC 把"开流"设计成了"切通道"本身。同一个动作的三个观察面：

| 层 | SET_INTERFACE 是什么 | 备注 |
|---|---|---|
| USB 标准层 | 接口换档位——Alt Setting 0 切到 Alt 1，端点描述符换掉 | USB 核心不关心你是什么类 |
| UVC 设备固件层 | **流的开关**——UVC 规范 4.3.1.1：设备看到 Host 选中带流端点的 Alt Setting，就开始产出视频数据 | 固件把 SET_INTERFACE 当"开始流"信号 |
| Host 应用层 | 最后一公里——应用必须真的去读端点，数据才流起来 | bulk 与等时行为不同（见下） |

**Alternate Setting 两档**：Alt 0 = 零带宽（无数据端点，"静默"状态）；Alt 1+ = 带流端点（等时/批量），管道存在、带宽被分配。切档位 = 开/关阀门。

**为什么借 Standard 请求而不是 Class 请求？** 因为开流 = 带宽分配。等时端点一激活，Host 控制器必须按 bInterval 预留总线带宽（FS 最多 90%、HS 每微帧 80%）。让"流开没开"直接体现在"端点存在与否"上，USB 核心统一管带宽账本——带宽不够 SET_INTERFACE 直接失败，流自然开不起来。

**最后一公里：bulk vs 等时**
- **Bulk**：切到 Alt 1 后管道通，但没人发 IN token 就没有数据流——必须应用调 `libusb_bulk_transfer` 发起读，数据才动（本设备 2bdf:0101 属此类）
- **等时**：Host 控制器自动按 bInterval 发 IN token，设备主动放数据——但应用不提交 transfer 接住，帧就丢

`uvc_start_streaming()` 内部 = ① SET_INTERFACE 开阀门 + ② 启动读线程不停发 IN token 接数据。

**类比**：SET_INTERFACE = 拧开水龙头阀门（管道接通、水压就绪）；bulk 设备的水要有人拿桶接（IN token）；等时设备是管道自带泵（控制器按节拍抽），没人摆桶就白流（丢帧）。

---

## 6.4 码流类型切换实战

> 本节是 `uvc_stream_viewer.cpp` 开发过程中踩坑的总结。

### 热成像摄像头的数据分层模型

```
探测器（FPA）
  ↓
原始数据（14~16bit 温度值）
  ↓
┌─测温矩阵（16bit）  ───┐
└─伪彩映射（温度→RGB）──┘
  ↓
★ 码流类型多路复用器（XU CS_ID=0x03）★
  类型 2:  全屏测温矩阵（纯温度数据）
  类型 6:  YUV 实时流 + 测温头
  类型 8:  全屏测温数据 + YUV 实时流
  ★ 类型 10: 仅 YUV 实时流（无测温头，纯画面）★
  ↓
UVC 传输层（Probe/Commit/ISOC）
  ↓
USB 总线 → 主机
```

### 为什么需要 XU 切换码流类型

标准 UVC（Probe/Commit/SET_INTERFACE）只管**传输格式**，不管数据内容。如果不发 XU 切换命令，摄像头按默认类型（通常是类型 8：测温+YUV 混合）输出，解码器按纯 YUYV 解析 → 花屏。

**UVC 管的事**：分辨率、帧率、编码格式、带宽分配
**UVC 不管的事**：数据内容（纯画面 vs 画面+温度）、数据排列、帧头结构

### ★ XU 切换 vs UVC 取流：先后顺序（极其重要）

```
正确顺序：先配置内容，再开传输

  ① XU: 切换码流类型       → 告诉摄像头"我要什么内容"   ← 先！
  ② UVC: Probe/Commit     → 协商传输参数
  ③ uvc_start_streaming   → 打开管道，开始收帧           ← 后！

错误顺序：
  ① UVC: 开流 → 管道已建立
  ② XU: 切换码流 → 数据格式突变 → 花屏/崩溃
```

### ★ 取流中能不能发 XU？能，但要分类讨论

```
切换码流类型 (CS_ID=0x03)：
  → 数据格式突变 → ★ 必须先停流再切换

切换伪彩 (CS_ID=0x02)：
  → 只改颜色映射表，数据格式不变 → 取流中可以热切换

读取协议版本/错误码 (CS_ID=0x04/0x06)：
  → 纯读操作 → 随时可以读
```

### ★ YUYV vs MJPEG 描述符欺诈

此设备（2bdf:0101）的 UVC 描述符声称 UncompressedFormat 送的是 YUY2，但**实际帧数据以 `FF D8`（JPEG SOI 标记）开头**：

```
UVC 描述符          →  libuvc 信了          →  实际帧数据
UncompressedFormat      按 YUYV 协商成功       FF D8 FF E0 ...（JPEG！）
bits per pixel: 16      fmt=YUYV 标记          bytes=~10000（压缩后）
GUID: YUY2              期望 38400 字节         不是 38400 字节
```

**教训**：不能完全信任 UVC 描述符。在回调里检测 `data[0]==0xFF && data[1]==0xD8`，如果是 JPEG 就强制走 `cv::imdecode`。

### ★ MJPEG 省 74% 带宽

120x160 YUYV = 38400 字节，MJPEG 压缩后 ~10000 字节。摄像头说谎是为了兼容性（YUYV 描述符更容易被 OS 匹配）但实际送 MJPEG 省带宽。

---

## 6.5 uvc_stream_viewer 完整流程

```
① libusb 打开 → detach 内核驱动
② XU FUNC_SWITCH → XU SET_CUR [01 0A] (YUV_ONLY)  ← ★ 必须在 uvc_open 之前
③ usleep(200ms)  ← 等设备内部切换完成
④ uvc_open → uvc_get_stream_ctrl_format_size → uvc_start_streaming
⑤ 帧回调：检测 FF D8 → cv::imdecode(MJPEG) 或 uvc_any2rgb(YUYV) → cv::cvtColor(RGB2BGR)
⑥ cv::imshow → cv::waitKey(10) → ESC 退出
```

### 编译命令

```bash
g++ -o uvc_stream_viewer uvc_stream_viewer.cpp -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)
```

### 为什么同一份代码 bulk/等时设备都能跑（libuvc 抽象层）

`uvc_start_streaming()` 内部开工流程：

```
① 自己解析设备描述符（不是你的代码去解析）
② 看视频端点 bmAttributes：
     ├─ 0x02 Bulk → 内部开 bulk 读循环（libusb_bulk_transfer）
     └─ 0x05 Isoc → 内部开等时队列（alloc/fill_iso/submit）
③ 无论哪种，内部用 UVC 载荷头（12 字节，bmHeaderInfo 的 FID/EOF 位标记帧起止）
   把 USB 包拼装成【完整帧】
④ 把完整帧交给你的回调：uvc_frame_t
```

**你的代码依赖的接口是"帧"，不是"包"**——回调里拿到的永远是拼好的完整一帧（`frame->data` + `frame->data_bytes`）。用哪种管道运帧是 libuvc 内部的事：2bdf:0101 走 bulk 分支，罗技自动切等时分支，回调签名和流程不变。

分层抽象的意义就是"上面一层不用改"——正如调 `libusb_control_transfer` 不用管 Host 控制器是 xHCI 还是 EHCI。

---

## 6.6 实战踩坑全记录（★★★★★ 最重要）

| # | 症状 | 根因 | 修复 | 重要度 |
|---|------|------|------|--------|
| 1 | SDL2 播放数秒后 segfault | 回调线程和主线程同时写/读帧缓冲区，无锁 | 换 OpenCV + `pthread_mutex_t` 保护所有帧访问 | ★★ |
| 2 | 花屏（雪花状噪点） | 默认码流类型含测温数据混在 YUV 里 | XU 命令切到类型 10 (YUV_ONLY)：FUNC_SWITCH → GET_LEN → SET_CUR [01 0A] | ★★ |
| 3 | 花屏仍在，帧只有 ~10000 字节（应该是 38400） | **描述符声称 YUYV，实际送 MJPEG**（帧数据以 `FF D8` JPEG SOI 开头） | 帧回调检测 `FF D8` 头 → 强制 `cv::imdecode` | ★★★ |
| 4 | XU 命令不执行（编译报错参数数量不对） | `libusb_control_transfer` 8 个参数漏了 `bRequest` | 补全：bmRT + bReq + wVal + wIdx + data + wLen + timeout | ★★★ |
| 5 | XU 返回 `LIBUSB_ERROR_IO` | XU 在 `uvc_open` 之后发，设备已被 uvc 占用状态不一致 | **XU 必须在 `uvc_open` 之前发**，复用 detach 时的 libusb 句柄 | ★★★ |
| 6 | OpenCV `cvtColor(YUV2BGR)` 花屏 | OpenCV YUYV 字节序与该设备不匹配 | 统一用 libuvc 的 `uvc_any2rgb` + `cvtColor(RGB2BGR)` | ★ |
| 7 | `frame->data[0]` 编译报错 | `uvc_frame_t::data` 是 `void*`，C++ 不允许 void* 下标 | 先转 `(const uint8_t *)frame->data` | ★ |

### 对应的深层理解

1. **UVC 管传输、XU 管内容** — 两层独立。UVC 管分辨率/帧率/编码，XU 管帧里装什么数据
2. **先 XU 后 UVC** — 顺序不可逆。必须先配置内容再开传输
3. **取流中能发 XU，但要分类讨论** — 判断标准不是物理冲突，而是语义影响
4. **不能信任 UVC 描述符** — 必须在回调里检测实际数据头
5. **MJPEG 省带宽** — 摄像头说谎是为了兼容性
6. **`libusb_control_transfer` 签名** — 8 个参数，极易漏 `bRequest`
7. **XU 控制传输走 EP0，不需要 claim 接口** — 可以独立开 libusb 句柄
8. **帧回调不能做渲染** — 回调只转换数据，主线程渲染，用 `pthread_mutex_t` 保护

---

## 6.7 Interface 和 Endpoint 区分

**一句话总结：**
- **控制传输 = 发命令**（"请把分辨率调到 640x480"），走 EP0
- **批量传输 = 搬数据**（"把这一帧像素数据传过来"），走数据端点
- 两条通道互不阻塞——流开着的时候你照样可以用 EP0 调参数
- 端点有主——IF=0 的端点 IF=1 不能碰

| | 控制传输 (EP0) | 批量传输 | 中断传输 |
|---|---|---|---|
| libusb 函数 | `control_transfer` | `bulk_transfer` | `interrupt_transfer` |
| 走哪个端点 | EP0 | VS 端点 (如 0x81) | VC 中断端点 (如 0x83) |
| 参数指定方式 | bmRequestType+wValue+wIndex | 端点地址 | 端点地址 |
| 有 SETUP 包？ | 有（8 字节） | 无 | 无 |

## 6.8 标准 UVC 控制：亮度/对比度/白平衡（PU）

### 定位：标准控制住在 Processing Unit

亮度、对比度、饱和度、锐度、增益、白平衡是 UVC 规范的**标准图像处理控制**，住在描述符链里的 **Processing Unit (PU)**——拓扑链 `IT → PU → XU → OT` 中的"标准窗口"。XU 是"厂商私人窗口"（语义厂商定义，CS_ID+SubFunc 二级命名空间），PU 是"标准窗口"（语义规范写死，一个字节的 Control Selector 就够了）。

沿用第八会话的类比（UVC=快递公司，XU=包裹内容单）：
- **PU 标准控制 = 快递单上的公开字段**（收件人、重量）——全国表格都一样，不用问就知道格式
- **XU = 包裹里的私密附言**——只有收发双方约定才知道含义
- **控制传输 = 同一辆快递车**——EP0 + Class 请求，传送机制没有任何区别

### PU 的值从哪来：bUnitID 实操

PU 的值 = PU 描述符里的 `bUnitID`，是设备固件在描述符中声明的，**每台设备自己定，不是规范常数**。设备 2 的真实 dump：

```
===== VC Processing Unit Descriptor (12 B) =====
bLength=0x0C  bDescriptorType=0x24  bDescriptorSubtype=0x05 (Processing Unit)
bUnitID = 0x05    ← PU 的值，就是它
bSourceID = 0x01  ← 上游模块 ID（拓扑链靠它串起来）
wMaxMultiplier = 0x4000    bmControls = 00 00（无标准控制）
```

- 原始字节里 `bUnitID` 是 PU 描述符的**第 4 个字节**（偏移 3）：`bLength, bType(0x24), bSubtype(0x05), bUnitID, ...`
- 拿到后填 `wIndex = (5 << 8) | VC_IF = 0x0500`——与 XU 同构（XU 的 bUnitID=10 → `0x0A00`），同一个寻址机制
- 新设备的 PU 编号可能不是 5，**每次接新设备必须重读**，不能照抄旧值

```bash
sudo lsusb -v -d 2bdf:0101 | grep -B2 -A12 "Processing Unit"
# 找 bUnitID 字段 → 填进 wIndex 高字节
```

拓扑链 `IT → PU → XU → OT` 里每个模块都有门牌号（Unit/Terminal ID），wIndex 高字节就是控制命令的邮寄地址。

### 与 XU 的寻址对照

| 要素 | XU（海康设备已验证） | 标准 PU |
|---|---|---|
| bmRequestType | 0x21 / 0xA1 | 一样 |
| bRequest | 0x01 / 0x81 / 0x85 | 一样，另多 4 个探测码：0x82/0x83/0x84/0x86/0x87 |
| wValue | 本厂商惯例：CS_ID 在**高字节**（`CS_ID << 8`） | **规范规定 CS 在低字节**（亮度=0x0002），高字节=0 |
| wIndex | `(XU_ID << 8) \| VC_IF` | 一样：`(PU_ID << 8) \| VC_IF` |
| 前置流程 | FUNC_SWITCH → GET_LEN → GET_CUR 三阶段 | **没有前置**，直接寻址 |

> ⚠️ **厂商惯例 vs 规范（重要）**：UVC 规范的标准写法是 wValue 低字节 = CS；海康热成像固件（2bdf:0101）是反的（CS 在高字节），所以 `xu_minimal_get.c` / `uvc_stream_viewer.cpp` 里都写 `(CS_ID << 8)`。接新设备先用一个已知控制试通，确定字节序再批量操作——不要假设新设备也走海康惯例。

### D6-5 三层字典：Standard / Class / Vendor 谁发谁定

**不是设备决定的，是"发请求的那层软件"决定的**——寄件人决定用哪张快递单。

| D6-5 | 字典 | 谁来发 | 什么时候出现 | 例子 |
|---|---|---|---|---|
| 00 | Standard | 操作系统 USB 核心（usbcore/xHCI） | 枚举 + 基本管理 | GET_DESCRIPTOR(0x06)、SET_ADDRESS(0x05)、SET_CONFIGURATION(0x09)、SET_INTERFACE(0x0B) |
| 01 | Class | 类驱动 / 按类规范写的应用（libusb 代码就是这层） | 正常运行期调参数 | UVC SET_CUR(0x01)、GET_CUR(0x81)、GET_LEN(0x85)、Probe/Commit |
| 10 | Vendor | 厂商 SDK | 厂商私有功能 | 海康私有控制 |

时间线：`插入 → 枚举（全 Standard）→ 正常工作（调参数走 Class）→ 厂商黑科技（Vendor）`。设备还没被"认识"（连地址都没有）时谈不上类和厂商，只有核心规范可用。

两个判断技巧：
1. **查字典**：00 → 《USB 2.0 规范第 9 章》（所有设备都必须懂，与类无关）；01 → 《类规范》（UVC 表 4-1 等，声明哪个类就懂哪本）；10 → 无公开字典，只有厂商文档
2. **看高 nibble 速判**：`0x0_`/`0x8_` = Standard，`0x2_`/`0xA_` = Class，`0x4_`/`0xC_` = Vendor（`0x21` → Class OUT ✓，`0xA1` → Class IN ✓）

**接收者和类型强相关**：Class 请求几乎总是发给 Interface——"类"以接口为单位组织，`bInterfaceClass=0x0E` 就是"接口 0 懂 UVC 字典"的合同；Standard 请求三个接收者都用；Vendor 随便。

### XU：Class 信封 + Vendor 内容

XU 请求本身是**标准 UVC 类请求**（D6-5=01），只有信封里的"内容"是厂商自定义的：

| 层 | 归谁管 | 证据 |
|---|---|---|
| 信封（传输机制） | UVC 规范 | bmRequestType=0x21/0xA1，bRequest 用 SET_CUR/GET_CUR/GET_LEN/GET_INFO——与 PU 完全同一套 |
| 地址（寻址） | UVC 规范 | wIndex=(XU_ID<<8)\|IF、wValue=控制号 1..bNumControls（规范 4.2.1 定义） |
| 内容（控制含义） | 厂商 | 控制 1 是曝光还是降噪、数据怎么解释——只有厂商 SDK 知道 |

- **GUID = 信封上的厂商署名**：XU 描述符的 `guidExtensionCode`（海康 `{A29E7641-...}`）告诉 Host 这套暗语是哪家的
- **为什么这样设计**：信封标准化 → 通用工具（uvcvideo/usbvideo）能**不理解内容**就枚举 XU、GET_INFO 试探、读写字节块。第六会话能对海康 XU 跑通三阶段，正因为信封是标准的——要逆向的只有信的内容
- **四种组合**：Standard=公文（格式含义全国统一）；PU=快递单公开字段；**XU=快递单备注栏（栏位标准、暗语私密）**；Vendor(D6-5=10)=连单据都是私制
- CS_ID+SubFunc 二级命名空间是**在厂商信封里再套一层自己的协议**（学习项目设计），海康固件只认控制号 1..N

### 逐字节：SET_CUR 设亮度 +20（标准写法）

```
CTL  21 01  02 00  05 00  02 00        ← 8 字节 SETUP
OUT  14 00                             ← DATA：+20（int16 小端）
```

| 字节 | 字段 | 值 | 含义 |
|---|---|---|---|
| 0 | bmRequestType | 0x21 | OUT + Class + Interface（和发 XU 一模一样） |
| 1 | bRequest | 0x01 | SET_CUR |
| 2-3 | wValue | 0x0002 | **CS = PU_BRIGHTNESS_CONTROL = 0x02** |
| 4-5 | wIndex | 0x0005 | 高字节 = **PU 的 bUnitID = 5**，低字节 = VC 接口号 0 |
| 6-7 | wLength | 0x0002 | DATA 阶段 2 字节 |
| DATA | 数据 | `14 00` | int16 小端 = +20，**0 = 默认**，负 = 变暗，正 = 变亮 |

读回来是镜像：`CTL A1 81 02 00 05 00 02 00` + IN 2 字节。"换设备只改 wIndex 高字节"（第六会话结论）对 PU 同样成立：`lsusb -v` 找 Processing Unit 的 `bUnitID` 填进去。

### 请求码全家桶

| bRequest | 名字 | 问什么 |
|---|---|---|
| 0x81 | GET_CUR | 当前值 |
| 0x01 | SET_CUR | 设值 |
| 0x82 | GET_MIN | 最小值 |
| 0x83 | GET_MAX | 最大值 |
| 0x84 | GET_RES | 步进分辨率 |
| 0x85 | GET_LEN | 数据长度（返回 2 字节） |
| 0x86 | GET_INFO | 1 字节能力位图 |
| 0x87 | GET_DEF | 默认值 |

**GET_INFO 返回的 1 字节位图**（和 bmControls 位图一个思路）：

```
D0 = 1  支持 GET（可读）
D1 = 1  支持 SET（可写）
D2 = 1  当前被自动模式禁用 ← 关键！很多相机开自动曝光时亮度就是 D2=1
D3~D7  保留
```

两层"能力声明"，呼应"不能信任描述符"：
1. **描述符层**：PU 的 `bmControls` 位图——bit N=1 → CS(N+1) 存在（硬件有没有这个寄存器）
2. **运行时层**：GET_INFO——此刻能不能读/写（自动模式可能临时接管）

### 完整报文速查表（示例：PU_ID=5, VC_IF=0，规范字节序）

> 换设备只改 wIndex 高字节（PU 的 bUnitID）；海康设备注意 wValue 要按高字节惯例改写（CS<<8）。

| CS | 控制 | 数据 | GET_INFO（读能力，返 1B） | GET_CUR（读当前值） |
|---|---|---|---|---|
| 0x01 | 背光补偿 Backlight | u16 ×2B | `A1 86 01 00 05 00 01 00` | `A1 81 01 00 05 00 02 00` |
| 0x02 | 亮度 Brightness | **i16 有符号** ×2B，0=默认 | `A1 86 02 00 05 00 01 00` | `A1 81 02 00 05 00 02 00` |
| 0x03 | 对比度 Contrast | u16 ×2B，0=默认 | `A1 86 03 00 05 00 01 00` | `A1 81 03 00 05 00 02 00` |
| 0x04 | 增益 Gain | u16 ×2B | `A1 86 04 00 05 00 01 00` | `A1 81 04 00 05 00 02 00` |
| 0x05 | 工频抑制 PowerLineFreq | u16 ×2B（0=关, 1=50Hz, 2=60Hz） | `A1 86 05 00 05 00 01 00` | `A1 81 05 00 05 00 02 00` |
| 0x06 | 色相 Hue | i16 有符号 ×2B | `A1 86 06 00 05 00 01 00` | `A1 81 06 00 05 00 02 00` |
| 0x07 | 色相自动 HueAuto | u8 ×1B（0=关, 1=开） | `A1 86 07 00 05 00 01 00` | `A1 81 07 00 05 00 01 00` |
| 0x08 | 饱和度 Saturation | u16 ×2B | `A1 86 08 00 05 00 01 00` | `A1 81 08 00 05 00 02 00` |
| 0x09 | 锐度 Sharpness | u16 ×2B | `A1 86 09 00 05 00 01 00` | `A1 81 09 00 05 00 02 00` |
| 0x0A | 伽马 Gamma | u16 ×2B（×100，100=γ1.0） | `A1 86 0A 00 05 00 01 00` | `A1 81 0A 00 05 00 02 00` |
| 0x0B | 白平衡温度 WBT | u16 ×2B（单位 K，如 6500=6500K） | `A1 86 0B 00 05 00 01 00` | `A1 81 0B 00 05 00 02 00` |
| 0x0C | 白平衡温度自动 WBTAuto | u8 ×1B（0/1） | `A1 86 0C 00 05 00 01 00` | `A1 81 0C 00 05 00 01 00` |
| 0x0D | 白平衡分量 WBComponent | **4B**（u16 蓝 + u16 红） | `A1 86 0D 00 05 00 01 00` | `A1 81 0D 00 05 00 04 00` |
| 0x0E | 白平衡分量自动 | u8 ×1B（0/1） | `A1 86 0E 00 05 00 01 00` | `A1 81 0E 00 05 00 01 00` |
| 0x0F | 数字倍率 DigitalMult | u16 ×2B（1/16 定点） | `A1 86 0F 00 05 00 01 00` | `A1 81 0F 00 05 00 02 00` |
| 0x10 | 数字倍率上限 | u16 ×2B | `A1 86 10 00 05 00 01 00` | `A1 81 10 00 05 00 02 00` |

（0x11~0x14 为 UVC 1.5 新增：HueAuto 重复定义、模拟视频制式、模拟锁定状态、对比度自动——常见摄像头少见实现。）

**其余报文的变换规则**（不用背，三条规则覆盖全部）：
- **GET_MIN/GET_MAX/GET_RES/GET_DEF**：报文与 GET_CUR 完全相同，只把第 2 字节 bRequest 换成 0x82/0x83/0x84/0x87
- **SET_CUR**：把 GET_CUR 的 `A1 81` 换成 `21 01`，DATA 阶段方向变 OUT（例：设亮度 +20 = `21 01 02 00 05 00 02 00` + OUT `14 00`）
- **GET_LEN**：`A1 85 CS 00 05 00 02 00`，返回 2 字节数据长度

### 数据格式要点（MQTT 级精度）

- **亮度、色相是 int16 有符号**（0=默认，可负可正）；**对比度/增益/饱和度/锐度/伽马是 uint16 无符号**
- **白平衡温度单位 K**；**白平衡分量 4 字节**（u16 蓝分量 + u16 红分量，两个通道各 2 字节）
- **自动类控制（0x07/0x0C/0x0E）只有 1 字节**：0=手动模式，1=自动模式——开自动后对应手动控制通常 GET_INFO D2=1（被禁用）

### 标准控制的发现五件套

```
① 描述符 bmControls bit1 = 1?        → 亮度控制存在吗
② GET_INFO(0x02) 返回 D2=0?          → 没被自动模式禁用吗
③ GET_MIN / GET_MAX / GET_DEF        → 值域和默认值
④ GET_CUR                           → 当前值
⑤ SET_CUR                           → 设新值
```

对比 XU 的三阶段（FUNC_SWITCH → GET_LEN → GET_CUR）：XU 的复杂度来自"语义未知、要厂商定义"；标准的复杂度来自"值域未知、要运行时探测"。**一个在猜协议，一个在读手册。**

### libusb 完整示例（规范字节序）

```c
#define PU_ID   5       // lsusb -v 里 Processing Unit 的 bUnitID
#define VC_IF   0       // Video Control 接口的 bInterfaceNumber
// 注意：这是 UVC 规范写法（wValue 低字节=CS）。
// 海康热成像固件是反的（wValue = CS << 8），先试通再定字节序。

// 设亮度 +20
unsigned char data[2] = {0x14, 0x00};              // int16 LE = +20
libusb_control_transfer(devh,
    0x21,                  // OUT, Class, Interface
    0x01,                  // SET_CUR
    0x0002,                // wValue = PU_BRIGHTNESS_CONTROL
    (PU_ID << 8) | VC_IF,  // wIndex — 换设备只改这里
    data, 2, 1000);

// 读值域/能力/当前值
unsigned char buf[2], info;
libusb_control_transfer(devh, 0xA1, 0x82, 0x0002, (PU_ID<<8)|VC_IF, buf, 2, 1000);   // GET_MIN
libusb_control_transfer(devh, 0xA1, 0x83, 0x0002, (PU_ID<<8)|VC_IF, buf, 2, 1000);   // GET_MAX
libusb_control_transfer(devh, 0xA1, 0x86, 0x0002, (PU_ID<<8)|VC_IF, &info, 1, 1000); // GET_INFO
libusb_control_transfer(devh, 0xA1, 0x81, 0x0002, (PU_ID<<8)|VC_IF, buf, 2, 1000);   // GET_CUR
```

### 为什么海康设备没走这条标准通道

设备 1/2 的 PU `bmControls = 00 00`——标准处理控制一个都没实现，对这些 CS 发 SET_CUR 会直接 STALL（硬件拒绝）。这是产品策略：厂商把亮度/对比度/增益全塞进 XU 私有控制（第五篇 Q6 的 10 个启用 control），配合厂商 SDK 卖。标准桌面摄像头（罗技等）才会实现 PU。

**但标准通道值得学**：它是 UVC 规范的"正文"，XU 是"附录"。接第三方摄像头第一步查 PU bmControls——这条是通用的，不依赖任何厂商文档。

## 6.9 TM5X 大数据交互流程（EP0 上的分包传输）

> 来源：海康《TM5X 工业测温机芯 UVC 功能开发指南 V2.0》（2024-02-20，文档号 UD36878B）。解答"EP0 控制传输怎么搬大文件"（§4.4 的延伸问题）。

### 核心概念：单帧报文与分包

当 Data 字段长度超过**单帧报文所能容纳的最大长度**时，对数据分包传输。接收方为 Device → 用 SET_CUR；接收方为 Host → 用 GET_CUR。

**"单帧最大长度"是设备固件定的**（TM5X 实际为 512 字节/帧，抓包中由 GET_LEN 响应逐次宣告）。它不在 USB 规范里——是厂商扩展协议的参数。

### 三层上限模型（64 / 512 / 65535 各归各层）

```
业务层    文件（如 TM56 抓热图 655,364 字节）
   │ 海康协议切：N 个分包帧，每帧 ≤512B + 5B 帧头
   ▼
XU 协议帧层   ★ 512 在这一层 ★  一帧 = 一次控制传输 = 一个新 SETUP
   │ （Bus Hound 里"一行 OUT/IN 512 + 下一行 CTL"就是这层）
   ▼
USB 传输层   一次控制传输，wLength ≤65535（字段宽度上限，实际没人填满）
   │ 硬件自动切：512 ÷ 64 = 8
   ▼
总线事务层   ★ 64 在这一层 ★  8 笔事务，每笔 ≤64B（HS EP0 钉死）
   │ Bus Hound 工作在 URB 层，这层被合并显示（§2.2a）
   ▼
物理层      D+/D- 上的比特
```

| | 64 字节 | 512 字节 | 65535 字节 |
|---|---|---|---|
| 谁定的 | USB 2.0 规范 | 海康机芯固件 | USB 规范（字段宽度） |
| 管什么 | 一笔事务的 Data 上限 | 一帧报文的 Data 上限 | 一次传输的理论上限 |
| 谁执行切分 | USB 硬件自动 | 上层软件按 GET_LEN 切 | —— |
| Bus Hound | 不可见（被合并） | 可见（一行 512） | 可见（一行） |

**65535 是 USB 给的字段上限，512 是海康机芯给的胃容量。协议永远按胃容量切，不按字段上限塞。**

### 两步流程

**步骤 1：交换数据总长**（总长不计算每帧的 5 字节帧头）

| 方向 | 载体 | Data 格式 |
|------|------|----------|
| Host→Device（SET 类） | SET_CUR | [ 0x01(数据类型) \| Total Length(4B) ] |
| Device→Host（GET 类） | GET_LEN 响应 | [ 0x01 \| Total Length(4B) ] |

**步骤 2：逐帧传分包数据**

每帧格式：`[ 0x02 | Packet Sequence Number(4B, 从 1 递增) | Packet Data ]`

时序：

```
功能切换(SET_CUR subFunID)
    │
GET_LEN ──► 响应（数据总长）          ← 步骤1：先知道总共多大
    │
┌─ 循环：每帧重复 ─────────────────┐
│ GET_LEN ──► 响应（下一帧大小）     │  ← 逐帧协商：设备告知本帧 wLength
│ SET_CUR/GET_CUR ──► 分包数据帧   │  ← 每帧 = 一次独立控制传输
└─────────────────────────────────┘
```

**GET_LEN 的双重作用**：① 告知下一帧 wLength（逐帧流控，最后一帧是余数）；② 存活探针——设备正常应答才继续。

### 谁定 512？——设备是强势方

文档 §1.2 步骤 2：Host 每次发送请求前，先 GET_LEN 获取 wLength。**wLength 填多少是设备说的，不是 Host 选的。** 512 = 机芯固件 XU 命令处理路径的缓冲区大小（与 flash 页大小可能有关，文档未明说原因）。

### 确认机制：两层确认

**帧级——USB 协议自带（"发到缓冲区"的确认，也是发下一帧的条件）**：

- 每笔事务 ACK = 64B 到达设备 USB 硬件（快递每车扫码）
- STATUS 阶段 = 整单 512B 签收（合同盖章）
- `libusb_control_transfer()` 返回成功 = 帧已进设备缓冲区
- 再配合 GET_LEN 正常应答 → 可以发下一帧

**业务级——海康协议自定义（"处理过"的确认）**：

- 设备"**先收齐、再解析**"——收 ≠ 处理
- SET 类请求 Host 无法直接感知异常 → 主动轮询错误码
- 错误码 `0x01` = 执行中（继续轮询），`0x00` = 成功，其他 = 失败
- 轮询间隔：恢复默认/设置专家测温校正参数按 1s；其他功能 ≥10ms
- 升级场景专用：GET_CUR 查 `updateStatus`(1 升级中/2 成功/3 失败) + `percent`(0~100) + `errMsg`，间隔 ≥1s；升级成功后需重启机芯模组才完成切换

**两层拒绝模型**（第五会话的 STALL vs 错误码）：

| 层 | 拒绝方式 | 含义 | 表现 |
|---|---------|------|------|
| USB 层 | STALL | 设备没收下（协议层拒收） | libusb 返回 LIBUSB_ERROR_PIPE |
| 业务层 | 错误码非 0 | 收下了，但执行失败 | GET_CUR 查错误码 |

### 适用功能与量级

| 功能 | 方向 | 量级 |
|------|------|------|
| 固件升级 | SET_CUR | 整个升级包 |
| 抓热图（附全屏测温数据） | GET_CUR | TM56：640×512×2+4 = 655,364B ≈ 1293 帧 ≈ 2500+ 个 SETUP |
| 获取 ROI 最高温信息 | SET_CUR + GET_CUR | 小 |
| 导出诊断文件 | GET_CUR | 最大 100KB |
| 导出/导入标定文件 | GET_CUR / SET_CUR | — |
| 获取/设置专家测温规则 | GET_CUR / SET_CUR | — |

### 传输中的约束（坑）

1. **大数据传输过程中不允许功能切换**——中途切换会破坏会话状态
2. SET 类请求设备收完才解析校验；慢功能（恢复默认/写标定/设专家规则/设校正参数）先置错误码 0x01 再执行
3. 分包过程可主动取错误码提前终止，但频率不宜高（升级过程会拖慢速度）
4. 升级状态查询间隔 ≥1s
5. 包序号从 1 递增——接收方靠它检测丢帧/乱序（5 字节帧头的作用）

---

# 附录：快速参考手册

---

## A.1 SETUP 包 8 字节速查

```
Byte 0: bmRequestType    0x21=OUT Class IF   0xA1=IN Class IF   0x01=Standard
Byte 1: bRequest         0x01=SET_CUR        0x81=GET_CUR       0x85=GET_LEN
Byte 2-3: wValue (LE)   高字节=CS_ID, 低字节=0   ← 海康固件惯例；UVC 规范标准写法是低字节=CS
Byte 4-5: wIndex  (LE)  高字节=XU Unit ID, 低字节=接口号  — 换设备只改这里！
Byte 6-7: wLength (LE)  DATA 阶段字节数
```

### bmRequestType 三个字段

```
Bit 7:   方向 — 0=OUT(Host→Dev)  1=IN(Dev→Host)
Bit 6-5: 字典 — 00=Standard  01=Class  10=Vendor
Bit 4-0: 接收者 — 0=Device  1=Interface  2=Endpoint

速判（看高 nibble）：0x0_/0x8_=Standard  0x2_/0xA_=Class  0x4_/0xC_=Vendor
```

## A.2 三种 wIndex 填法

| 场景 | wIndex | bmRequestType |
|------|--------|--------------|
| VC XU 命令 | `(XU_ID<<8) \| VC_IF` | 0x21/0xA1 (Class) |
| VS Probe/Commit | `VS_IF` | 0x21/0xA1 (Class) |
| SET_INTERFACE 开流 | `VS_IF` | 0x01 (Standard), bReq=0x0B |

## A.3 控制传输核心

- **三阶段模型**：SETUP(必须ACK) + DATA(可选) + STATUS(方向与DATA相反，零长度包)
- **SETUP 包 8 字节**：bmRequestType(1) + bRequest(1) + wValue(2 LE) + wIndex(2 LE) + wLength(2 LE)
- **bmRequestType 三把钥匙**：D7=方向, D6-5=字典, D4-0=接收者
- **ACK vs STATUS**：ACK=包级"CRC对了"，STATUS=传输级"交易关闭/拒绝"
- **STATUS 是拒绝唯一入口**：SETUP 必须 ACK → 不支持的请求只能在 STATUS 回 STALL
- **批量传输无 STATUS**：ACK 就是事务终点

## A.4 新设备上线检查清单

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU Unit ID)
□                                       bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 IF 填对              → SETUP wIndex 高/低字节
□ 用 CS_ID=0x04 GET_LEN 试通         → 验证通道 + 拿到协议版本
□ 看 bmControls 位图                 → 了解支持哪些 CS_ID
□ 选一个已知 CS_ID 走三阶段          → FUNC_SWITCH → GET_LEN → GET_CUR
```

## A.5 新设备码流切换检查清单

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU), bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 VC_IF                → wIndex = (XU_ID<<8) | VC_IF
□ ★ 先发 XU 切码流类型                → FUNC_SWITCH → GET_LEN → SET_CUR [01 0A]
  □ 用独立 libusb 句柄，EP0 不需要 claim
  □ 在 uvc_open 之前！不要之后！
  □ usleep(200ms) 等设备就绪
□ uvc_open → uvc_get_stream_ctrl_format_size（可能需要 raw descriptor walk）
□ 帧回调检测 FF D8 头 → 如果是 JPEG 走 cv::imdecode，否则走 uvc_any2rgb
□ 帧回调只做转换，不渲染。渲染在主线程，加 pthread_mutex_t 保护
```

## A.6 编译运行速查

```bash
# XU 交互工具
gcc -o xu_interactive xu_interactive.c -lusb-1.0
sudo ./xu_interactive

# UVC 取流
g++ -o uvc_stream_viewer uvc_stream_viewer.cpp -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)

# 查描述符
sudo lsusb -v -d 2bdf:0101 > /tmp/cam.txt
grep -n "EXTENSION_UNIT\|bUnitID\|bInterfaceNumber" /tmp/cam.txt
```

## A.7 PID 编码全表

| 类别 | PID | 值(hex) | 含义 |
|------|-----|---------|------|
| TOKEN | OUT | 0xE1 | Host→Device数据 |
| TOKEN | IN | 0x69 | Host←Device数据 |
| TOKEN | SOF | 0xA5 | 帧起始 |
| TOKEN | SETUP | 0x2D | 控制传输SETUP |
| DATA | DATA0 | 0xC3 | 翻转位=0 |
| DATA | DATA1 | 0x4B | 翻转位=1 |
| HANDSHAKE | ACK | 0xD2 | 正确接收 |
| HANDSHAKE | NAK | 0x5A | 暂时忙 |
| HANDSHAKE | STALL | 0x1E | 端点Halted |
| HANDSHAKE | NYET | 0x96 | HS批量FIFO满 |
| SPECIAL | PING | 0xB4 | HS批量流控探测 |

## A.8 描述符类型码全表

| 值 | 描述符 | 固定长度？ |
|:--:|--------|:--:|
| 0x01 | Device | ✅ 18 字节 |
| 0x02 | Configuration | ✅ 9 字节 |
| 0x03 | String | ❌ 可变 |
| 0x04 | Interface | ✅ 9 字节 |
| 0x05 | Endpoint | ✅ 7 字节 |
| 0x06 | Device Qualifier | ✅ 10 字节 |
| 0x07 | Other Speed Config | ✅ 9 字节（头）|
| 0x0B | IAD | ✅ 8 字节 |
| 0x0F | BOS | ✅ 5 字节（头）|

## A.9 MQTT 类比速查表

| MQTT | USB |
|------|-----|
| CONNECT 报文 | Device Descriptor |
| Topic 权限声明 | Configuration Descriptor |
| Topic QoS 定义 | Interface Descriptor |
| TCP 连接参数 | Endpoint Descriptor |
| `$SYS/` 系统主题 | EP0（控制端点） |
| PUBLISH body | 流管道（中断/批量/等时） |
| QoS | ACK/NAK/STALL 握手机制 |
| Topic 下挂子 Topic | Interface 下挂 Endpoint |
| 多个 Topic 共用一个 TCP 连接 | 多个 Interface 共用 EP0 |
| Fixed Header 第一个字节 | `bLength + bDescriptorType` 前 2 字节铁律 |
| Keep Alive 心跳 | bInterval 轮询间隔 |

---

> **创建日期**：2026-08-02
> **覆盖范围**：Phase 1-3（32/67 知识点）+ 真实设备实战 + UVC XU 控制与取流
> **代码参考**：`code/xu_minimal_get.c` / `code/xu_interactive.c` / `code/uvc_stream_viewer.cpp` / `code/HIKVISION_TM76_libusb_3.c`
