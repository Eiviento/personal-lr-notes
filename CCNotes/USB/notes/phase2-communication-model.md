# Phase 2: USB 通信模型笔记 — 层层拆解到比特

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

### 数据流转示例（读设备描述符）

```
功能层: "我要VID/PID"
  ↓
设备层: 组装 GET_DESCRIPTOR(Device), bmReqType=0x80, bReq=0x06
  ↓
总线接口层: SETUP Token + DATA0(8B) → IN Token×3 → DATA+ACK ×3
  ↓
设备层: 拼回18字节 Device Descriptor
  ↓
功能层: 拿到 VID=0x046D, PID=0xC077 → "罗技鼠标"
```

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

注意：MaxPacketSize ≠ FIFO实际大小。FIFO通常更大(双缓冲/多缓冲)。

### 典型设备端点布局

```
HID键盘(LS): EP0(控制8B), EP1 IN(中断8B)
CDC串口(FS): EP0(控制64B), EP1 IN(中断16B), EP2 IN(批量64B), EP3 OUT(批量64B)
UVC摄像头(HS): EP0(控制64B), EP1 IN(中断16B可选), EP2 IN(等时512B)
```

---

## 2.3 管道 (Pipe)

### 定义

**管道 = Host软件到端点之间的逻辑通信通道。** 
端点 = 目的地(硬件FIFO)，管道 = 通往目的地的路(软件抽象)。

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

### 控制传输
- EP0专用，三阶段(SETUP→DATA→STATUS)
- 所有配置、枚举、命令都走它

### 中断传输
- bInterval保证延迟上限
- 周期轮询：Host定期发IN Token
- 不是物理中断！只是像中断一样低延迟
- LS最大包8B，HS最大1024B

### 批量传输
- 无带宽保证、无延迟保证
- 数据正确(有ACK+重试)
- HS下最大512B/包
- 理想吞吐~53MB/s(HS)，实际20-35MB/s

### 等时传输
- 无握手包！无ACK/NAK/STALL
- 带宽有保留(枚举时预约)
- 错误发生时直接丢数据，不重试
- 实时>可靠性：UVC视频流、USB Audio

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

范围 0x00~0x7F (0~127)
0x00 = 默认地址(Default Address)，设备刚复位后使用
0x01~0x7F = 可分配地址(127个)

### ENDP字段 (4 bits)

范围 0~15 (0x0~0xF)
方向由PID决定(IN PID=读, OUT PID=写)
EP3 IN和EP3 OUT是硬件上两个不同的FIFO

### CRC5字段 (5 bits)

多项式: G(x) = x⁵ + x² + 1 (100101 = 0x25)
校验范围: ADDR(7b) + ENDP(4b) = 11 bits
如果CRC5不匹配→地址或端点号在传输中损坏→丢弃包

### SOF Token (结构不同)

```
SYNC(8b) | PID=SOF(0xA5) | Frame Number(11b) | CRC5(5b) | EOP
```

Frame Number: 0~2047
FS: 1帧=1ms→~2秒回卷
HS: 1微帧=125μs→256ms回卷

---

## 2.8 ⛁ Data 包逐位解析

### 结构

```
SYNC(8b) | PID(8b) | DATA(0~1024B) | CRC16(16b) | EOP(3b)
```

### CRC16

多项式: G(x) = x¹⁶ + x¹⁵ + x² + 1
截断多项式: 0x8005
校验范围: DATA字段全部字节

### 短包终止

如果数据长度 < MaxPacketSize → 短包 = 传输结束信号
如果恰好等于MaxPacketSize → 追加零长度DATA包标记结束

### DATA0/DATA1翻转机制

- 初始化: Toggle = DATA0
- 成功(收到ACK): Toggle翻转
- NAK: Toggle不变
- 接收方检测到Toggle与预期不一致→知道是重传→回ACK但丢弃数据

保护1: ACK被干扰丢失→Host重发同一DATAx→Device识别重传
保护2: 没有翻转时→Device分不清"Host重发"还是"Host真的又发了相同内容"

### HS等时微帧多包

HS等时一个微帧可发多包(最大3包):
第1包: DATA2 → 第2包: DATA1 → 第3包: DATA0

---

## 2.9 ⛁ Handshake 包逐位解析

### 结构（USB最短的包）

```
SYNC(8b) | PID(8b) | EOP(3b)
```

没有DATA、没有CRC。PID自身的高4位=~低4位校验已足够。

### ACK (0xD2)

- `1101 0010`, 高4位=1101=~0010 ✓
- 数据被正确接收(Crc正确、PID校验正确、Toggle匹配)
- 发送方翻转Toggle，事务完成

### NAK (0x5A)

- `0101 1010`, 高4位=0101=~1010 ✓
- 暂时忙/无数据: FIFO空(IN)或FIFO满(OUT)
- Toggle不翻转，发送方稍后重试
- **不是错误**，是正常流控
- NAK总是Device给Host的

### STALL (0x1E)

- `0001 1110`, 高4位=0001=~1110 ✓
- 端点Halted或请求不支持
- 需要软件干预(CLEAR_FEATURE)
- NAK="等等再来" vs STALL="别试了，需要人来修"

### NYET (0x96, HS only)

- `1001 0110`, 高4位=1001=~0110 ✓
- HS批量OUT: 数据收了但FIFO满了
- PING协议的一部分：Host先PING确认空间→再发OUT数据
- 下一包前Host需要再PING

### ERR (0x3C, HS only)

- `0011 1100`, 高4位=0011=~1100 ✓
- Hub在Split Transaction中向Host报告错误
- SDK一般不直接处理

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

存在但少用: HID键盘LED控制、游戏手柄力反馈

### 选型: 中断 vs 批量

| 维度 | 中断 | 批量 |
|------|------|------|
| 延迟 | 有保证 | 无保证 |
| 数据量 | 小 | 大 |
| CPU | 必须定期轮询 | 按需 |
| 用途 | 状态/按键/传感器 | 文件/串口流 |

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

### NAK限制

协议层面没有重试上限，但Host驱动可以限制。
批量传输没有确定的延迟。

---

## 2.13 等时传输逐事务拆解

### 基本结构（无握手包！）

```
IN:  Host→IN Token ←DATA (结束!)
OUT: Host→OUT Token→DATA (结束!)
```

没有ACK, 没有NAK, 没有STALL。

### 为什么不要握手

实时>可靠性: 30fps视频(33ms/帧), 重传延迟比丢几帧更致命。
人脑对5-10%帧丢失不敏感，但对>50ms延迟非常敏感。

### 带宽预约

枚举时Host检查是否有足够带宽。
带宽不够→Set_Configuration失败→设备不可用。

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

### 错误处理

CRC16错了→丢弃, 不通知设备。
UVC: 一帧丢了一个包→整帧损坏→SDK应丢弃此帧。

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

FS: 1ms ± 500ns
HS: 125μs ± 62.5ns

USB总线上最精确的时间参考。音频/视频设备用SOF PLL锁定时钟。

### 帧内调度

```
SOF→等时→中断→控制→批量→SOF(下一帧)
```

### Suspend检测

连续3ms(FS)或3个微帧(HS)没看到SOF→设备进入Suspend→电流≤2.5mA

---

## 2.15 HS 高速模式补充

### 微帧结构

8个微帧=1ms HS帧
μF0~μF7，Frame Number相同，下一组μF0的Frame Number+1

### Split Transaction

**问题**: HS Hub后挂FS/LS设备，Hub必须做速度翻译。

**解法**: Split Transaction (两阶段)

#### Phase 1: Start-Split (SSPLIT)

Host→SSPLIT Token→Hub翻译成FS/LS信号→跟FS/LS设备交互→数据暂存Hub缓冲区

SSPLIT Token字段:
```
Hub Addr(7b) | SC=0 | Port(7b) | S(0=FS,1=LS) | E=0 | ET(2b) | CRC5
```

#### Phase 2: Complete-Split (CSPLIT)

Host→CSPLIT Token→Hub返回之前暂存的数据

CSPLIT Token字段:
```
Hub Addr(7b) | SC=1 | Port(7b) | S | U(0=未完,1=完成) | ET(2b)
```

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

USB 2.0没有链路层概念。

### USB 2.0 vs 3.0 核心对比

| 维度 | USB 2.0 | USB 3.x |
|------|---------|---------|
| 拓扑 | 广播式 | 路由式 |
| 编码 | NRZI | 8b/10b→128b/132b |
| 流控 | NAK/NYET/PING | 链路层信用(Credit-based) |
| 链路管理 | SE0复位 | LTSSM状态机 |
| 中断 | 定期轮询 | 设备可主动发ERDY |
| EP0 | 64B | 512B |

### 对SDK的影响

- libusb在xHCI上对USB 3.0透明支持
- 描述符体系基本一样
- 注意降速(3.0设备插2.0口→降到HS→等时带宽不够)
- 超时参数应该可配置

---

## 补充问答：传输方向深度辨析

### Q1: 控制传输的"双向"是全双工吗？另外三种是半双工吗？

**USB 总线物理层本身就是半双工的。** D+/D- 只有一对差分线，同一时刻只能有一个方向的数据在线上传输。所以所有传输从物理上都是半双工。

**控制传输的"双向"不是同时收发**，而是指 EP0 这个端点既能收也能发，收发分阶段串行执行：

```
控制读 (Host 读 Device 描述符):
  阶段1 SETUP: Host → Device  (OUT方向)
  阶段2 DATA:   Host ← Device  (IN方向，Device回数据)
  阶段3 STATUS: Host → Device  (OUT方向，Host确认)

控制写 (Host 发配置给 Device):
  阶段1 SETUP: Host → Device  (OUT方向)
  阶段2 DATA:   Host → Device  (OUT方向，Host发数据)
  阶段3 STATUS: Host ← Device  (IN方向，Device确认)
```

STATUS 阶段的方向永远跟 DATA 阶段相反——这是协议规定，不是硬件能力。

**中断/批量/等时端点的"单向"是端点层面的：**

- `EP1 IN`（地址 0x81）——这个端点**只能** Device→Host
- `EP2 OUT`（地址 0x02）——这个端点**只能** Host→Device

它们是两个**物理上不同的 FIFO 缓冲区**。即使端点号相同，EP3 IN 和 EP3 OUT 是两段独立的硬件 FIFO。

设备想双向通信？用两个端点：

```
CDC 串口端点布局:
  EP1 IN  (中断) — Device→Host，通知串口状态变化
  EP2 IN  (批量) — Device→Host，串口收到的数据
  EP3 OUT (批量) — Host→Device，要发往串口的数据
```

就像两条独立单向水管，一根进水一根出水。

| 层面 | 全双工/半双工 | 说明 |
|------|:---:|------|
| USB 总线（物理层） | 半双工 | D+/D- 只有一对 |
| 控制传输 EP0 | 半双工，但双向 | 分阶段切换方向 |
| 中断/批量/等时端点 | 单向 | 硬件上方向固定，双向需两个端点 |

---

### Q2: 每个端点是做什么功能的，由谁决定？

决定权在**设备（Device）**这边，分两个层面：

**层面一：硬件设计时（芯片设计师决定）**

端点的数量、类型、方向、FIFO 大小是芯片设计时硬件决定的：

```
USB 设备芯片内部:
┌──────────────────────────────────────┐
│  EP0 IN/OUT FIFO (64B)  ← 控制传输，必须有     │
│  EP1 IN FIFO     (8B)   ← 硬件固定为 IN，中断   │
│  EP2 IN FIFO     (64B)  ← 硬件固定为 IN，批量   │
│  EP3 OUT FIFO    (64B)  ← 硬件固定为 OUT，批量  │
└──────────────────────────────────────┘
```

芯片流片之后这些就不能改了。

**层面二：枚举时（设备固件通过描述符告诉 Host）**

```
Device Descriptor
 └── Configuration Descriptor
      ├── Interface Descriptor (bInterfaceClass=0x03 → HID)
      │    └── Endpoint Descriptor
      │         bEndpointAddress = 0x81  → EP1, IN
      │         bmAttributes      = 0x03 → 中断传输
      │         wMaxPacketSize    = 0x0008 → 8 字节
      │         bInterval         = 0x0A → 每 10ms 轮询
      │
      ├── Interface Descriptor (bInterfaceClass=0x0A → CDC)
      │    └── Endpoint Descriptor → EP2, IN, 批量
      │    └── Endpoint Descriptor → EP3, OUT, 批量
```

Host 读描述符 → 知道 EP1 是中断 IN → 以后按这个规矩发 Token。Host 不能"自作主张"给 EP1 发批量传输。

| 层面 | 谁决定 | 决定什么 |
|------|--------|---------|
| 硬件层 | 芯片设计师 | 有几个端点、FIFO 多大、什么类型 |
| 固件层 | 设备固件 | 填描述符，告诉 Host 每个端点属性 |
| Host 层 | 操作系统 | 读描述符，遵守规则，照章办事 |

**最终话事权 = 设备（硬件+固件）。Host 只是被动接受者。**

MQTT 类比：Broker 读 CONNECT 报文知道 Client ID，读 SUBSCRIBE 知道路由——但 Broker 不能强行给没订阅的 Topic 发消息。Host 读描述符知道端点布局——但 Host 不能强行给中断端点发批量传输。

---

### Q3: Token 在每种传输的事务中起什么作用？

Token 是 USB 总线上**每一笔事务的起始信号**，由 Host 发出。作用：

> "第 X 号设备，你的第 Y 号端点，接下来我们要收/发数据了。"

**Token 包里装了什么：**

```
SYNC(8b) | PID(8b) | ADDR(7b) | ENDP(4b) | CRC5(5b) | EOP(3b)
          ↑           ↑           ↑
       干嘛用      找谁        找他的哪个端点
```

| 字段 | 作用 | 例 |
|------|------|-----|
| PID | 告诉设备**要干什么**：IN(发数据)、OUT(收数据)、SETUP(命令来了) | `0x69` = IN |
| ADDR | 总线上 127 个设备，**喊哪一个** | `0x03` = 设备 3 |
| ENDP | 那个设备的 16 个端点，**用哪个** | `0x1` = EP1 |

类比：Token = 课堂上老师点名。**"张三（ADDR），把你的作业交上来（IN，ENDP）。"** 没被点名的人不说话。

**四种传输中 Token 的角色：**

**控制传输 — 三种 Token 都用：**

```
SETUP Token: "设备3，EP0，我要发一个命令"    → 后跟 DATA0(8B SETUP包)
IN Token:    "设备3，EP0，把数据返回给我"    → 后跟 DATA1(设备回描述符)
OUT Token:   "设备3，EP0，我发确认信息给你"  → 后跟 DATA1(零长度STATUS)
```

**中断传输 — 通常只有 IN：**

```
IN Token: "鼠标，EP1，有新按键吗？"  → Host 周期性地问
  设备回: DATA(按键) 或 NAK(没新按键)
```

**批量传输 — IN 或 OUT：**

```
OUT Token: "U盘，EP2，数据来了接好"       → Host 先打招呼再发数据
IN Token:  "U盘，EP1，文件内容给我"       → Host 要读数据
```

**等时传输 — IN 或 OUT，无握手：**

```
IN Token:  "摄像头，EP2，给一帧视频"      → 设备回 DATA，不等 ACK
OUT Token: "音箱，EP1，音频拿去"          → Host 发 DATA，不等 ACK
```

**为什么 Token 是 USB 核心设计——Host 中心化的物理实现：**

没有 Token → 设备不能说话，一个字都不能。即使鼠标有紧急按键，也只能等 Host 下一个 IN Token 到来时附在 DATA 包里回过去。USB 总线上没有"中断信号线"，没有"设备主动请求"——只有 Token → 回应。

| Token 类型 | 含义 | 谁发 | 后面发生什么 |
|------------|------|------|-------------|
| **SETUP** | "我要发控制命令" | Host | DATA0(8B命令) → 设备 ACK |
| **IN** | "你发数据给我" | Host | 设备回 DATA / NAK / STALL |
| **OUT** | "我发数据给你" | Host | Host 发 DATA → 设备 ACK/NAK/STALL |
| **SOF** | "新一帧开始了" | Host | 广播，全总线都听，不回应 |

**Token = 老师点名 = 一切通信的起手式。没 Token，设备连呼吸的权利都没有。**
