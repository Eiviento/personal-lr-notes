# USB 协议学习计划（逐字节精讲版）

> 目标：用 C/C++ 构建一个 USB SDK，覆盖 UVC 摄像头、CDC 串口、HID 设备
> 学习策略：自底向上 — 先把协议基础打牢，再谈开发
> 深度要求：每个 byte 的每个 bit 含义都要讲清楚（MQTT 报文头级别精度）

---

## 第一阶段：USB 概览与总线拓扑

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| 1.1 | USB 设计目标与历史 | 为什么诞生？解决什么问题？与 RS232/并口/PS2 的对比 | ⬜ |
| 1.2 | USB 版本演进全景 | USB 1.0→1.1→2.0→3.x→4.0，各版本速度、电压、编码差异 | ⬜ |
| 1.3 | 总线拓扑结构 | Host→Hub→Device 树形结构；7层深度限制的原因；每层最多接多少设备 | ⬜ |
| 1.4 | 主机控制器类型 | UHCI/OHCI/EHCI/xHCI 各自管哪个速度、寄存器级别差异 | ⬜ |
| 1.5 | 物理层与电气特性 | VBUS(5V)、D+/D-、SSTX+/SSTX-、线颜色定义 | ⬜ |

---

## 第二阶段：USB 通信模型 — 层层拆解到比特

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| 2.1 | 三层通信模型 | 功能层↔设备层↔总线接口层，每层处理什么数据、怎么封装 | ⬜ |
| 2.2 | 端点 (Endpoint) 深入 | 端点号(0-15)、方向(IN/OUT)、端点 0 为什么一定有；端点的硬件本质(FIFO) | ⬜ |
| 2.3 | 管道 (Pipe) 深入 | 消息管道(Message Pipe) vs 流管道(Stream Pipe) 的数据结构差异 | ⬜ |
| 2.4 | 四种传输类型全景 | 控制/中断/批量/等时 — 各自适用场景、带宽保证、延迟边界 | ⬜ |
| 2.5 | 传输/事务/包 三层映射 | 一次 Transfer = N 个 Transaction = 每个 Transaction 有 Token+Data+Handshake 三个包 | ⬜ |
| 2.6 | ⛁ PID 编码表 | 8 位 PID 的位结构（低 4 位类型码 + 高 4 位取反校验）；SPECIAL/TOKEN/DATA/HANDSHAKE 四大类 16 种 PID 全集 | ⬜ |
| 2.7 | ⛁ Token 包逐位解析 | SYNC(8bit)→PID(8bit)→ADDR(7bit)→ENDP(4bit)→CRC5(5bit)→EOP | ⬜ |
| 2.8 | ⛁ Data 包逐位解析 | SYNC→PID→DATA(0~1023 byte)→CRC16→EOP；DATA0/DATA1/DATA2/MDATA 翻转机制；CRC16 多项式 | ⬜ |
| 2.9 | ⛁ Handshake 包逐位解析 | SYNC→PID→EOP；ACK/NAK/STALL/NYET(仅HS)/ERR(仅HS) 各自触发条件 | ⬜ |
| 2.10 | 控制传输逐事务拆解 | SETUP 事务(8 字节 SETUP 包)→可选 DATA 阶段→STATUS 阶段(方向相反) | ⬜ |
| 2.11 | 中断传输逐事务拆解 | Host 周期性发 IN Token→设备回复 DATA/NAK/STALL | ⬜ |
| 2.12 | 批量传输逐事务拆解 | 利用总线空闲带宽；HS 下最大 512 字节/包；PING 流控机制(HS) | ⬜ |
| 2.13 | 等时传输逐事务拆解 | 无握手包；固定带宽；最大 1023 字节(FS)/1024 字节(HS)；无重传机制 | ⬜ |
| 2.14 | SOF 包与帧结构 | SYNC→PID(SOF)→Frame Number(11bit)→CRC5→EOP；FS 每 1ms 一帧、HS 每 125μs 微帧 | ⬜ |
| 2.15 | HS 高速模式补充 | 微帧结构(125μs×8=1ms)；split transaction(SSPLIT/CSPLIT) | ⬜ |
| 2.16 | USB 3.x SuperSpeed 概览 | 不再是广播式总线，改用路由式 + LTSSM 状态机；SS Packets 与 USB 2 包结构差异 | ⬜ |

---

## 第三阶段：USB 描述符体系 — 逐字节解剖

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| 3.1 | 描述符层级关系 | Device→Config→Interface→Endpoint 的树；每个描述符的前 2 字节都是 bLength + bDescriptorType | ⬜ |
| 3.2 | ⛁ Device Descriptor 逐字节 | 18 字节逐位映射 | ⬜ |
| 3.3 | bcdUSB 的 BCD 编码细节 | 0x0200 表示 USB 2.0；0x0110 表示 USB 1.1 | ⬜ |
| 3.4 | ⛁ Configuration Descriptor 逐字节 | 9 字节逐位：wTotalLength/bNumInterfaces/bmAttributes/bMaxPower | ⬜ |
| 3.5 | ⛁ Interface Descriptor 逐字节 | 9 字节逐位：bInterfaceNumber/bAlternateSetting/bNumEndpoints/bInterfaceClass | ⬜ |
| 3.6 | ⛁ Endpoint Descriptor 逐字节 | 7 字节逐位：bEndpointAddress/bmAttributes/wMaxPacketSize/bInterval | ⬜ |
| 3.7 | bInterval 在不同速率下的含义 | LS/FS/HS 中断/HS 等时的不同计算公式 | ⬜ |
| 3.8 | ⛁ String Descriptor 逐字节 | bLength/bDescriptorType(03)/UNICODE 编码/LANGID 请求 | ⬜ |
| 3.9 | Qualifier Descriptor | Device_Qualifier/Other_Speed_Configuration | ⬜ |
| 3.10 | BOS Descriptor (USB 3.x) | LPM capability；SuperSpeed capability | ⬜ |
| 3.11 | 描述符类型码全集 | 所有 bDescriptorType 值速查 | ⬜ |

---

## 第四阶段：USB 枚举过程 — 逐包逐事务追踪

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| 4.1 | 枚举完整时间线 | 插入→检测→复位→Default→Address→Configured | ⬜ |
| 4.2 | 阶段 0：设备检测 | D+ 上拉(FS/HS) 或 D- 上拉(LS)→Host 检测到电平变化 | ⬜ |
| 4.3 | 阶段 0b：总线复位 | Host 将 D+/D- 都拉低 ≥10ms→设备复位 | ⬜ |
| 4.4 | 阶段 1：Get_Descriptor(Device) — 第1次 | SETUP 包逐字节 + 只读 8 字节的前因后果 | ⬜ |
| 4.5 | 阶段 1b：Set_Address | SETUP 包逐字节 + 设备地址分配 | ⬜ |
| 4.6 | 阶段 2：Get_Descriptor(Device) — 第2次 | wLength=18 读完整 18 字节 Device Descriptor | ⬜ |
| 4.7 | 阶段 3：Get_Descriptor(Config) — 先读头 | 先只读 9 字节→从 wTotalLength 知道完整链长度 | ⬜ |
| 4.8 | 阶段 4：Get_Descriptor(Config) — 完整链 | 一次读回全部描述符链 | ⬜ |
| 4.9 | 阶段 5：Get_Descriptor(String) | 读 String Descriptor — iManufacturer/iProduct/iSerialNumber | ⬜ |
| 4.10 | 阶段 6：Set_Configuration | wValue=配置编号→设备进入 Configured 状态 | ⬜ |
| 4.11 | 用 Wireshark/USBpcap 实战抓包 | 抓取真实设备枚举全过程，逐包匹配 | ⬜ |
| 4.12 | 枚举失败常见原因排查 | 最大包大小不对/地址分配后无响应/描述符 CRC 错误/Set_Config STALL | ⬜ |

---

## 第五阶段：标准请求与 Setup 包深度解析

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| 5.1 | ⛁ SETUP 包 8 字节逐位 | bmRequestType/bRequest/wValue/wIndex/wLength 逐位 | ⬜ |
| 5.2 | 11 种标准设备请求全集 | GET_STATUS/CLEAR_FEATURE/SET_FEATURE/SET_ADDRESS/GET_DESCRIPTOR/SET_DESCRIPTOR/GET_CONFIGURATION/SET_CONFIGURATION/GET_INTERFACE/SET_INTERFACE/SYNCH_FRAME | ⬜ |
| 5.3 | GET_STATUS 响应解析 | Device Status/Interface Status/Endpoint Status | ⬜ |
| 5.4 | SET_FEATURE / CLEAR_FEATURE | Feature Selector 全集 | ⬜ |
| 5.5 | SET_INTERFACE / GET_INTERFACE | Alternate Setting 切换机制 | ⬜ |
| 5.6 | wValue/wIndex/wLength 速查表 | 每个标准请求的参数组合速查 | ⬜ |

---

## 第六阶段：设备类协议逐字节解析（HID / CDC / UVC）

> **2026-08-16 裁剪决策**：用户是应用层开发者（SDK 消费设备，不写设备固件），本篇按**应用层裁剪版**执行——描述符逐字节学到"认字"级别（能看懂 dump/工具解析结果），描述符链用全景图带过，**类请求与数据流精讲**（SDK 直接要用）。以 byte 表 + 结构图为主，减少通篇文字。26/26 全部完成。

| # | 知识点 | 要讲清楚什么 | 状态 |
|---|--------|-------------|------|
| **HID 类** | | | |
| 6.1 | ⛁ HID Descriptor 逐字节 | bLength/bDescriptorType(0x21)/bcdHID/bCountryCode/bNumDescriptors | ✅ |
| 6.2 | ⛁ Report Descriptor Item 编码规则 | Item 前缀字节的位布局：bSize/bType/bTag | ✅（认字级） |
| 6.3 | Main Item 全集 | Input/Output/Feature/Collection/End Collection — 8 个标志位 | ✅（认字级） |
| 6.4 | Global Item 全集 | Usage Page/Logical Min&Max/Report Size&Count/Report ID | ✅（压缩为速查） |
| 6.5 | Local Item 全集 | Usage/Usage Min&Max | ✅（压缩为速查） |
| 6.6 | 键盘 Report Descriptor 完整范例 | 8 字节 Boot Keyboard Report 一步一步写出 | ✅（成品解剖图） |
| 6.7 | HID Report 协议 | Get_Report/Set_Report/Get_Idle/Set_Idle/Get_Protocol/Set_Protocol | ✅（精讲） |
| **CDC 类** | | | |
| 6.8 | ⛁ CDC 功能描述符链完整布局 | Interface↔Header↔ACM↔Union↔Call Mgmt↔Interface↔Endpoint×2 | ✅ |
| 6.9 | CDC Header Descriptor 逐字节 | bFunctionLength/bDescriptorType(0x24 CS)/bDescriptorSubType(0x00)/bcdCDC | ✅（认字级） |
| 6.10 | CDC ACM Descriptor 逐字节 | bDescriptorSubType(0x02)/bmCapabilities 逐位 | ✅（认字级） |
| 6.11 | CDC Union Descriptor 逐字节 | 主控制接口号 + 从属接口号列表 | ✅（认字级） |
| 6.12 | CDC Call Management Descriptor 逐字节 | bmCapabilities/bDataInterface | ✅（认字级） |
| 6.13 | CDC 类请求逐字节 | SET_LINE_CODING(7 字节)/GET_LINE_CODING/SET_CONTROL_LINE_STATE/SEND_BREAK | ✅（精讲） |
| 6.14 | CDC 数据流 | 中断端点(SerialState 10 字节) + 批量端点(收发数据) | ✅（精讲） |
| **UVC 类** | | | |
| 6.15 | ⛁ UVC 接口组织 | VC 接口(Video Control) + VS 接口(Video Streaming) | ✅ |
| 6.16 | ⛁ UVC VC Descriptor 链完整布局 | Interface↔VC Header↔Input Terminal↔Processing Unit↔Output Terminal↔Endpoint(可选) | ✅ |
| 6.17 | ⛁ UVC VC Header Descriptor 逐字节 | bLength/bDescriptorType/bDescriptorSubType/bcdUVC/wTotalLength/dwClockFrequency/bInCollection/baInterfaceNr | ✅（认字级） |
| 6.18 | ⛁ UVC Input Terminal Descriptor 逐字节 | bTerminalID/wTerminalType/bAssocTerminal/bmControls 位图 | ✅（认字级） |
| 6.19 | ⛁ UVC Processing Unit Descriptor 逐字节 | bUnitID/bSourceID/bmControls + bmVideoStandards | ✅（认字级） |
| 6.20 | UVC 控制位图 (bmControls) 详解 | PU/CT 两套全集 + 2bdf:0101 真机（PU 空壳，控制全走 XU） | ✅ |
| 6.21 | ⛁ UVC VS Descriptor 链完整布局 | Interface↔Input Header↔Format↔Frame↔Color Matching(可选)↔Endpoint | ✅ |
| 6.22 | ⛁ UVC VS Input Header Descriptor 逐字节 | bNumFormats/wTotalLength/bEndpointAddress/bmInfo/bTerminalLink/bmaControls | ✅（认字级） |
| 6.23 | ⛁ UVC Format Descriptor (MJPEG) 逐字节 | 26 字节布局（guidFormat 前 4 字节 ASCII 认格式；bDefaultFrameIndex 不在 Format 而在 Still Image 帧描述符） | ✅（认字级） |
| 6.24 | ⛁ UVC Frame Descriptor (MJPEG) 逐字节 | wWidth/wHeight/dwMinBitRate/dwMaxBitRate/dwMaxVideoFrameBufSize/dwDefaultFrameInterval/bFrameIntervalType | ✅（认字级） |
| 6.25 | UVC Probe/Commit 协商机制 | SET_CUR/GET_CUR/GET_MIN/GET_MAX/GET_DEF 协商格式/分辨率/帧率 | ✅ |
| 6.26 | ⛁ UVC Payload Header 逐字节 | HLEN/Bit Field Header(FID/EOF/PTS/SCR/STI)/PTS/SCR；FID 翻转判断帧边界 | ✅ |

---

## 第七阶段：协议分析工具与实操 — ⏭ 跳过（2026-08-16 用户决定，暂缓）

> 理由：应用层开发暂不需要；真机抓包实战已在 4.11/4.11a 完成（枚举全过程 + TM5X 逐包分析）。若将来调试需要再回补。

| # | 知识点 | 要做什么 | 状态 |
|---|--------|---------|------|
| 7.1 | lsusb -v 完整输出解读 | 逐段对照描述符知识点，完全读懂输出信息的每一位 | ⏭ 跳过 |
| 7.2 | Wireshark + USBpcap 安装配置 | Windows 上抓 USB 流量的环境搭建 | ✅（已在 4.11 实操） |
| 7.3 | 抓取真实设备枚举过程 | HID 键盘 / CDC 串口 / UVC 摄像头 各抓一遍枚举过程 | ⏭ 跳过 |
| 7.4 | 抓取 HID 数据流 | 按键上报的中断 IN 传输，Report Descriptor 对应报文字段 | ⏭ 跳过 |
| 7.5 | 抓取 CDC 数据流 | 打开串口→Set_Line_Coding→收发测试→观察批量传输 | ⏭ 跳过 |
| 7.6 | 抓取 UVC 数据流 | Probe/Commit 协商→VS 启动→等时传输视频帧→Payload Header 分析 | ⏭ 跳过 |
| 7.7 | USB Tree Viewer 等工具 | 图形化查看描述符树 | ⏭ 跳过 |

---

## 第八阶段：libusb 编程衔接

| # | 知识点 | 要做什么 | 状态 |
|---|--------|---------|------|
| 8.1 | libusb 架构概览 | 同步/异步模型、context、传输 completion callback | ✅（含 libuvc 关系、两层回调、★帧回调规则深挖） |
| 8.2 | 设备发现与枚举 | libusb_get_device_list→遍历→获取描述符→跟协议阶段对应 | ✅（含 ★open≠开流、★claim/detach、两扇门深挖） |
| 8.3 | 控制传输编程 | libusb_control_transfer — SETUP 包 8 字节与位定义完全对应 | ✅（含 ★错误翻译表、★Windows↔Linux 对照深挖） |
| 8.4 | 批量/中断/等时传输编程 | 三种传输的 API 与回调模型 | ✅（含 ★信箱模式简版深挖） |
| 8.5 | 热插拔检测 | 注册回调→设备插入/拔出通知 | ✅（02_hotplug_detect.c 已真机验证） |

---

> ⛁ = 逐字节/逐比特精讲
> 总计：8 个阶段，88 个知识点任务（原"67"为统计笔误，2026-08-16 修正）
> 状态：★ 主线全部完成（81/88，92%；Phase 7 跳过暂缓）——2026-08-16 第十二会话收官。下一步：SDK 动工
> 创建日期：2026-07-25
