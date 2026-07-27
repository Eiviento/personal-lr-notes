# Phase 1: USB 概览与总线拓扑笔记

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

### 名字含义

- **U**niversal — 通用
- **S**erial — 串行
- **B**us — 总线

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

### 关键概念

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

D+和D-传差分信号：接收方计算 D+减D- 的差值。
外部共模噪声同时影响两根线 → 相减后噪声抵消。

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
