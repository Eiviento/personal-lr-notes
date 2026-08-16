# 真实设备描述符分析手册

> 基于三台真实 USB 摄像头，从字节级拆解 USB 描述符：标准描述符逐字节精读 + UVC 类专用描述符机制 + 综合实战追踪。
>
> - 设备 1：HikCamera（海康，VID 0x2BDF / PID 0x0101，序列号 G11376317），完整原始描述符 dump
> - 设备 2：HikCamera（同型号另一台，序列号 E83518457），完整原始描述符 dump（含 Device Qualifier + Other Speed Configuration）
> - 设备 3：2K USB Camera + Audio（VID 0x2BDF / PID 0x028A），无原始 USB 描述符，仅有 Windows Kernel Streaming（KS）层数据，用于反推练习
>
> 本手册是独立文档：不需要先读任何其他笔记。目标读者是**从零学 USB 的 C/C++ 应用工程师**。
> 所有原始数据来自 `captures/usb设备1的描述符.txt` / `captures/usb设备2的描述符.txt` / `captures/usb设备3的描述符.txt`
> （用 USB 描述符抓取工具如 USB Device Tree Viewer 导出）。

## 目录

- [第 1 章 描述符是什么](#第-1-章-描述符是什么)
- [第 2 章 标准描述符逐字节](#第-2-章-标准描述符逐字节)
- [第 3 章 类专用描述符机制（UVC）](#第-3-章-类专用描述符机制uvc)
- [第 4 章 综合实战](#第-4-章-综合实战)
- [第 5 章 FAQ](#第-5-章-faq)
- [附录 A 设备 1 完整原始 dump（精简）](#附录-a-设备-1-完整原始-dump精简)
- [附录 B 设备 2 完整原始 dump（精简）](#附录-b-设备-2-完整原始-dump精简)
- [附录 C 设备 3 KS 数据摘要](#附录-c-设备-3-ks-数据摘要)

---

## 0. 阅读约定

### 0.1 字节序与数值写法

- 所有多字节字段都是 **小端序（Little-Endian）**：低字节在前。例：`wTotalLength = 0x01B1` 在线上是字节 `B1 01`。
- 所有十六进制数值统一带 `0x` 前缀。
- `0b` 前缀表示二进制。

### 0.2 字节地图颜色图例

本手册用 ASCII 字符代替颜色（纯 markdown 无法着色；HTML 版会渲染为真彩色）。每个字节地图有三行：**偏移 / 分类字母 / 实际值**。

| 分类字母 | 颜色 | 含义 |
|:---:|:---:|---|
| `H` | 蓝 | 铁律头：bLength + bDescriptorType（每个描述符前两字节） |
| `S` | 青 | 规格/版本号：bcdUSB、bcdDevice、bcdUVC 等 |
| `C` | 紫 | 类别声明：class / subclass / protocol |
| `K` | 橙 | 能力值：bMaxPacketSize0、wMaxPacketSize 等 |
| `I` | 绿 | 身份：idVendor、idProduct |
| `N` | 灰 | 索引/数量/ID：bInterfaceNumber、bNumEndpoints、字符串索引等 |
| `P` | 黄 | 属性/电源：bmAttributes、MaxPower |
| `E` | 粉 | 端点：bEndpointAddress、bmAttributes、bInterval |

### 0.3 术语速查

| 术语 | 含义 |
|---|---|
| EP | Endpoint，端点。EP0 = 控制端点（每个设备必有） |
| IN / OUT | 设备→主机 为 IN；主机→设备 为 OUT（以设备视角命名） |
| VC | Video Control，UVC 视频控制接口（负责控制，不走视频数据） |
| VS | Video Streaming，UVC 视频流接口（负责传输视频数据） |
| IAD | Interface Association Descriptor，接口关联描述符（把多个接口绑成一个"功能"） |
| UVC | USB Video Class，USB 视频类规范（bcdUVC 1.10 = 本设备实现 UVC 1.1） |
| UAC | USB Audio Class，USB 音频类规范 |
| KS | Kernel Streaming，Windows 内核流媒体层（应用看到的其实是驱动解析后的数据） |
| 描述符链 | 一个配置下所有描述符按顺序拼接成的字节串 |

### 0.4 数据完整度说明

- **设备 1 / 设备 2**：有完整原始 USB 描述符 dump（Device / Config / IAD / Interface / Class-specific / Endpoint / String）。
- **设备 3**：**无原始 USB 描述符**。仅有 Windows 驱动解析后的 KS 数据（视频格式表、音频参数、设备路径中的 MI_00/MI_02 接口号）。所有"设备 3"的 USB 描述符字段标为 **无数据**；能从设备路径/HW ID 推出的值标注"推断"。

---

# 第 1 章 描述符是什么

## 1.1 描述符 = USB 设备递给 Host 的名片

USB 是 **Host 中心化** 总线：设备没有发言权，只有在 Host 点名（发请求）时才允许应答。那 Host 怎么知道插上来的是什么设备、有哪些功能、怎么跟它通信？

答案是**描述符（Descriptor）**：设备固件里写死的一组结构化字节，用"一问一答"的方式交给 Host。

MQTT 类比：MQTT Client 连上 Broker 后会收到 CONNACK，里面带着 Broker 的能力声明（最大包长、心跳间隔等）；USB 设备被枚举时做的事本质上一样——**把"我是谁、我能干什么、怎么跟我通信"通过描述符一次性讲清楚**。只不过 MQTT 是 JSON/二进制属性，USB 是全字节级的固定格式。

### TLV 铁律

所有 USB 描述符（无论标准还是类专用）都遵守同一条铁律——**前两个字节必须是**：

```
+----------+----------+--------------------------+
| bLength  | bDescTyp |     描述符内容           |
| 1 字节   | 1 字节   |     (长度不定)           |
+----------+----------+--------------------------+
  ↑ 长度     ↑ 类型
```

- `bLength`：本描述符总字节数。Host 靠它**跳过**一个描述符、找到下一个。
- `bDescriptorType`：类型码。Device=0x01，Config=0x02，String=0x03，Interface=0x04，Endpoint=0x05，Device Qualifier=0x06，Other Speed Config=0x07，IAD=0x0B；类专用描述符另有自己的类型码（如 UVC 的 0x24/0x25，见第 3 章）。

这就像 MQTT 报文固定头里的"报文类型 + Remaining Length"：解析器拿到前几字节就知道这是什么报文、后面还有多少字节。USB 的 Host 栈就是靠 TLV 铁律**顺序遍历整条描述符链**的——它不需要任何索引表，只需要从链头开始不断"读 2 字节头 + 跳过 bLength"。

## 1.2 描述符获取流程：枚举

设备插上后，Host 按下面这个流程把描述符"问"出来（这段过程叫**枚举 Enumeration**）：

```
 设备                       Host
  │                           │
  │  上电 + 复位 (Reset)       │
  ├───────────────────────────►│  设备在默认地址 0 上等待
  │◄───────────────────────────┤  GET_DESCRIPTOR(Device, 0, 18)  ① 读 18 字节设备描述符
  │  18 字节应答               │      （先读出 bMaxPacketSize0，确定 EP0 包大小）
  │◄───────────────────────────┤  SET_ADDRESS(7)                 ② 分配设备地址
  │  ACK                       │
  │◄───────────────────────────┤  GET_DESCRIPTOR(Device, 0, 18)  ③ 用新地址重读设备描述符
  │◄───────────────────────────┤  GET_DESCRIPTOR(Config, 0, 9)   ④ 只读配置描述符头 9 字节
  │  9 字节应答 (wTotalLength=433)                               → 知道整条链长
  │◄───────────────────────────┤  GET_DESCRIPTOR(Config, 0, 433) ⑤ 完整链一次性返回
  │  433 字节应答               │      （配置 + IAD + 接口 + 类专用 + 端点，全在这一个包里）
  │◄───────────────────────────┤  GET_DESCRIPTOR(String, ...)    ⑥ 按需取字符串描述符
  │◄───────────────────────────┤  SET_CONFIGURATION(1)           ⑦ 选定配置，开始工作
  │                           │
```

三个关键点：

1. **描述符是按需索取**：Host 先读 9 字节配置头拿到 `wTotalLength`，再按这个长度**一次**取回整条链。
2. **完整链一次性返回**：配置描述符链（433 字节）是配置描述符本身 + IAD + 所有接口描述符 + 所有类专用描述符 + 所有端点描述符**按顺序拼接**成的一个大字节串，一次 GET_DESCRIPTOR 传输返回。UVC 的 `wTotalLength`（VC 81 字节、VS 298 字节）同理，是各自的类专用子链总长。
3. **字符串是懒加载**：描述符里只放字符串**索引**（iManufacturer=0x01 等），Host 需要显示时才发 GET_DESCRIPTOR(String, index)。

MQTT 类比：这就像 Client 连接后先读 CONNACK 的固定属性，再根据属性决定要不要进一步订阅/拉取——USB 用 `wTotalLength` 做"后续报文有多长"的声明，和 MQTT 的 Remaining Length 思想同源。

## 1.3 描述符层级树

三台设备里，设备 1/2 是同一型号的两台 HikCamera，它们的描述符链结构完全一致（设备 3 只能从 KS 层推断，见 4.3）。以设备 1 为例，完整层级如下：

```
Device Descriptor (18 B)                     ← 整台设备的"身份证"
└── Configuration Descriptor (9 B, wTotalLength = 0x01B1 = 433 B)
    ├── IAD Descriptor (8 B)                 ← 声明"接口 0~1 是一个 Video Function"
    ├── Interface 0: VideoControl (VC) (9 B)
    │   ├── VC Header Descriptor (13 B)      ← 类专用子链起点 (0x24/0x01)
    │   ├── VC Input Terminal (18 B)         ← ITT_CAMERA 摄像头输入端子
    │   ├── VC Processing Unit (12 B)        ← 图像处理单元
    │   ├── VC Extension Unit (29 B)         ← 厂商扩展单元 (15 个私有控制)
    │   ├── VC Output Terminal (9 B)         ← TT_STREAMING 输出端子
    │   │                                    (以上 81 B = VC 类专用子链)
    │   ├── Endpoint EP3 IN Interrupt (7 B)  ← 控制状态通知通道
    │   └── Class-Specific VC EP (5 B, 0x25) ← 该端点的 UVC 类专用信息
    ├── Interface 1: VideoStreaming (VS) (9 B)
    │   ├── VS Input Header (16 B)           ← 类专用子链起点 (0x24/0x01)
    │   ├── VS Uncompressed Format + 3×Frame (27 + 90 B)  ← YUY2 格式
    │   ├── VS MJPEG Format + 3×Frame (11 + 90 B)         ← MJPEG 格式
    │   ├── VS Frame-Based Format + 1×Frame (28 + 30 B)   ← H.264 格式
    │   ├── VS Color Matching (6 B)
    │   │                                    (以上 298 B = VS 类专用子链)
    │   └── Endpoint EP1 IN Bulk (7 B)       ← 视频数据通道
    └── (字符串描述符 0~6：通过 iManufacturer/iProduct/... 索引引用)
```

注意层级：**设备 → 配置 → 接口 → 端点** 四层，类专用描述符挂在接口下面，字符串挂在索引上。Host 拿到的 433 字节就是上树"深度优先遍历"的扁平字节串。

## 1.4 三台设备速览

| 项目 | 设备 1 (HikCamera #1) | 设备 2 (HikCamera #2) | 设备 3 (2K USB Camera) |
|---|---|---|---|
| VID : PID | 0x2BDF : 0x0101 | 0x2BDF : 0x0101 | 0x2BDF : 0x028A（推断自 Device ID） |
| 序列号 | G11376317 | E83518457 | 无数据 |
| 产品字符串 | "HikCamera" | "HikCamera" | "2K USB Camera"（Friendly Name，非描述符） |
| 功能 | UVC 视频（VC + VS） | UVC 视频（VC + VS） | UVC 视频 + UAC 音频（推断 4 接口，见 4.3） |
| 接口数 | 2（IAD 绑定） | 2（IAD 绑定） | ≥4（推断） |
| 描述符链总长 | 0x01B1 = 433 B | 0x01B1 = 433 B | 无数据 |
| 视频格式 | YUY2 / MJPEG / H.264，最高 640×360@30 | 同左 | MJPG / NV12 / YUY2，最高 2560×1440@30 |
| 音频 | 无 | 无 | PCM 16 kHz / 16 bit / 单声道（麦克风） |
| 数据完整度 | 完整原始描述符 dump | 完整原始 dump（另含 Device Qualifier + Other Speed Config） | **无原始描述符**，仅 KS 层数据 |
| 抓取时状态 | 枚举成功，设备处于 D3 低功耗态 | 枚举成功，设备处于 D0 | 驱动已加载（usbvideo.sys + usbaudio.sys） |

设备 1 与设备 2 是**同一型号的两个个体**：描述符几乎全同，只有序列号和抓取时机不同（这正是第 4 章 4.2 的对比素材）。设备 3 是另一款更高分辨率的复合设备（视频 + 音频），但原始描述符缺失，只能从驱动层数据反推——这恰好演示了"没有抓包工具时怎么读描述符"。

## 1.5 如何自己抓一份描述符

Windows 下用 USB 描述符抓取工具（如 **USB Device Tree Viewer** 或微软 **UsbView**）即可看到与附录 A/B 相同格式的 dump。要点：

- 工具显示的是**驱动栈解析后的友好格式**，不是原始字节流——但它给出的每个十六进制值就是线缆上的原始字节。
- 原始字节流需要抓包工具（如 Wireshark + USBPcap）在 USB 2.0 总线层捕获 GET_DESCRIPTOR 应答。
- 注意工具的时间陷阱：设备在 D3 低功耗态时，某些请求（如设备 1 的 Device Qualifier）会失败——那是状态问题，不是描述符问题。

---

# 第 2 章 标准描述符逐字节

标准描述符定义在 USB 2.0 规范第 9 章，所有设备都必须实现。本章逐个拆解设备 1/2 中出现过的 5 种标准描述符；每种都有 4 个小节：**标准定义表 → 字节地图 → 三设备对照表 → 关键字段深入**。

## 2.1 Device Descriptor（18 字节）

### 2.1.1 标准定义表

| 偏移 | 字段 | 长度 | 含义 |
|---|---|---|---|
| 0 | bLength | 1 | 本描述符长度，固定 0x12 (18) |
| 1 | bDescriptorType | 1 | 类型码，固定 0x01 (Device) |
| 2 | bcdUSB | 2 | 设备实现的 USB 规范版本（BCD 码，0x0200 = USB 2.0） |
| 4 | bDeviceClass | 1 | 设备级类码（0x00 / 0xEF，见关键字段深入） |
| 5 | bDeviceSubClass | 1 | 设备级子类码 |
| 6 | bDeviceProtocol | 1 | 设备级协议码 |
| 7 | bMaxPacketSize0 | 1 | EP0 最大包长（HS 必须 0x40 = 64） |
| 8 | idVendor | 2 | 厂商 ID（USB-IF 分配，0x2BDF = 海康威视） |
| 10 | idProduct | 2 | 产品 ID（厂商自定） |
| 12 | bcdDevice | 2 | 设备版本号（BCD，厂商自定） |
| 14 | iManufacturer | 1 | 厂商字符串索引（0 = 无） |
| 15 | iProduct | 1 | 产品字符串索引 |
| 16 | iSerialNumber | 1 | 序列号字符串索引 |
| 17 | bNumConfigurations | 1 | 配置描述符个数（≥1） |

### 2.1.2 字节地图（设备 1 实际值）

```
+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  | 9  | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |  ← 偏移
+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
| H  | H  | S  | S  | C  | C  | C  | K  | I  | I  | I  | I  | S  | S  | N  | N  | N  | N  |  ← 颜色分类
+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
| 12 | 01 | 00 | 02 | EF | 02 | 01 | 40 | DF | 2B | 01 | 01 | 09 | 04 | 01 | 02 | 03 | 01 |  ← 设备 1 字节
+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
  bL  bDT   └─bcdUSB─┘  └bClass┘  └MPS┘   └─idVendor─┘  └idProduct┘ └bcdDevice┘ iM iP iS nC
```

对应关系逐字段核对（注意小端）：

| 字节 | 值 | 字段 | 说明 |
|---|---|---|---|
| 00-01 | 12 01 | bLength + 类型 | 18 字节，Device |
| 02-03 | 00 02 | bcdUSB = 0x0200 | USB 2.0 |
| 04-06 | EF 02 01 | 类/子类/协议 | Miscellaneous / 0x02 / IAD |
| 07 | 40 | bMaxPacketSize0 | 64 字节 |
| 08-09 | DF 2B | idVendor = 0x2BDF | 海康威视 |
| 10-11 | 01 01 | idProduct = 0x0101 | HikCamera |
| 12-13 | 09 04 | bcdDevice = 0x0409 | 固件版本 4.09（BCD 码，与 HW ID 的 REV_0409 一致） |
| 14 | 01 | iManufacturer | → 字符串 1 "HIK" |
| 15 | 02 | iProduct | → 字符串 2 "HikCamera" |
| 16 | 03 | iSerialNumber | → 字符串 3 "G11376317" |
| 17 | 01 | bNumConfigurations | 1 个配置 |

### 2.1.3 三设备对照表

| 字段 | 标准要求 | 设备 1 (HikCamera #1) | 设备 2 (HikCamera #2) | 设备 3 (2K USB Camera) | 解读 |
|---|---|---|---|---|---|
| bLength | 0x12 | 0x12 | 0x12 | 无数据 | 固定 |
| bDescriptorType | 0x01 | 0x01 | 0x01 | 无数据 | 固定 |
| bcdUSB | 0x0200 (2.0) | 0x0200 | 0x0200 | 无数据 | 三台都是 USB 2.0 设备 |
| bDeviceClass | 0x00 或 0xEF | 0xEF | 0xEF | 无数据 | 复合设备专用（见 2.1.4） |
| bDeviceSubClass | 0x02 (当 Class=0xEF) | 0x02 | 0x02 | 无数据 | Common subclass |
| bDeviceProtocol | 0x01 (用 IAD 时) | 0x01 | 0x01 | 无数据 | IAD 协议 |
| bMaxPacketSize0 | HS 必须 0x40 | 0x40 | 0x40 | 无数据 | 见 2.1.4 |
| idVendor | USB-IF 分配 | 0x2BDF | 0x2BDF | 0x2BDF（推断自 Device ID） | 海康 |
| idProduct | 厂商自定 | 0x0101 | 0x0101 | 0x028A（推断自 Device ID） | 产品型号 |
| bcdDevice | 厂商自定 | 0x0409 | 0x0409 | 0x3000（推断自 REV_3000） | 固件版本 |
| iManufacturer | 索引或 0 | 0x01 "HIK" | 0x01 "HIK" | 无数据 | |
| iProduct | 索引或 0 | 0x02 "HikCamera" | 0x02 "HikCamera" | 无数据 | |
| iSerialNumber | 索引或 0 | 0x03 "G11376317" | 0x03 "E83518457" | 无数据 | 两台唯一差异字段 |
| bNumConfigurations | ≥1 | 0x01 | 0x01 | 无数据 | |

### 2.1.4 关键字段深入

**（1）bDeviceClass = 0xEF，为什么不直接写 0x0E (Video)？**

设备 1/2 明明是摄像头，设备级类码却是 `0xEF (Miscellaneous)`，而不是 `0x0E (Video)`。原因：

- `bDeviceClass` 描述**整台设备**。它只有在"设备 = 单一功能"时才有意义（键盘写 0x03 HID，读卡器写 0x0B 等）。
- 但 UVC 摄像头天然是**复合设备**：一个 Video 功能至少由 **2 个接口**（VC 控制 + VS 流）组成；设备 3 更复杂（视频 + 音频 4 个接口）。接口的绑定关系接口描述符表达不了，需要 IAD 来描述。
- USB 规范规定：**使用 IAD 的复合设备，设备级类码必须声明为 0xEF**（子类 0x02，协议 0x01 = "使用 IAD"）。Host 看到 0xEF/0x02/0x01 就知道："这是一个由多个功能组成的复合设备，功能划分请看配置链里的 IAD"。
- 真正的功能分类（Video）写在 IAD 的 `bFunctionClass = 0x0E` 里（见 2.3）。

一句话：**设备级 class 管"整台机器是不是复合的"，IAD 的 function class 才管"每个功能是什么"**。这也是 FAQ Q1/Q5 的答案。

**（2）bMaxPacketSize0 = 0x40 = 64 字节**

EP0（控制端点）是设备与 Host 的第一条通道，枚举全靠它。它的最大包长：

- Low Speed：必须 8 字节
- Full Speed：8 / 16 / 32 / 64 可选
- **High Speed：必须 64 字节**（USB 2.0 §9.6.1 强制）

设备 1/2 运行在 HS（480 Mbps），所以 EP0 包长固定 0x40。Host 读设备描述符的第一个目的就是拿到这个值，从而知道"控制传输里每个事务最多能装多少字节"。详见 FAQ Q3。

---

## 2.2 Configuration Descriptor（9 字节）

### 2.2.1 标准定义表

| 偏移 | 字段 | 长度 | 含义 |
|---|---|---|---|
| 0 | bLength | 1 | 固定 0x09 (9) |
| 1 | bDescriptorType | 1 | 类型码 0x02 (Configuration) |
| 2 | wTotalLength | 2 | **整条配置描述符链总长**（配置头 + IAD + 接口 + 类专用 + 端点） |
| 4 | bNumInterfaces | 1 | 本配置下接口总数 |
| 5 | bConfigurationValue | 1 | 配置编号（SET_CONFIGURATION 用它选中本配置） |
| 6 | iConfiguration | 1 | 配置字符串索引（0 = 无） |
| 7 | bmAttributes | 1 | 属性位图（见下） |
| 8 | MaxPower | 1 | 总线最大电流，单位 2 mA |

### 2.2.2 字节地图（设备 1 实际值）

```
+----+----+----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  |  ← 偏移
+----+----+----+----+----+----+----+----+----+
| H  | H  | N  | N  | N  | N  | N  | P  | P  |  ← 颜色分类
+----+----+----+----+----+----+----+----+----+
| 09 | 02 | B1 | 01 | 02 | 01 | 04 | C0 | 01 |  ← 设备 1 字节
+----+----+----+----+----+----+----+----+----+
  bL  bDT  └─wTotalLength─┘ nI  bCV  iC  bmA MP
```

### 2.2.3 三设备对照表

| 字段 | 标准要求 | 设备 1 | 设备 2 | 设备 3 | 解读 |
|---|---|---|---|---|---|
| bLength | 0x09 | 0x09 | 0x09 | 无数据 | |
| bDescriptorType | 0x02 | 0x02 | 0x02 | 无数据 | |
| wTotalLength | 链总长 | 0x01B1 (433) | 0x01B1 (433) | 无数据 | 整条链 433 字节（4.1 会逐字节验证） |
| bNumInterfaces | ≥1 | 0x02 | 0x02 | 无数据（推断 ≥4） | 2 个接口 = VC + VS |
| bConfigurationValue | ≥1 | 0x01 | 0x01 | 无数据 | 唯一配置 |
| iConfiguration | 索引或 0 | 0x04 "Config 1" | 0x04 "Config 1" | 无数据 | |
| bmAttributes | bit7 恒 1 | 0xC0 | 0xC0 | 无数据 | 见下 |
| MaxPower | 单位 2 mA | 0x01 → 2 mA | 0x01 → 2 mA | 无数据 | 几乎不取总线电 |

### 2.2.4 关键字段深入

**（1）wTotalLength = 0x01B1 = 433 字节：整条链的"总账"**

`wTotalLength` 是配置链的总长度声明——Host 靠它决定 GET_DESCRIPTOR(Config) 要读多少字节。设备 1 的 433 字节构成（4.1 会逐项核对）：

```
9 (配置头) + 8 (IAD) + 9 (VC 接口) + 81 (VC 类专用) + 7 (中断 EP) + 5 (0x25 EP)
          + 9 (VS 接口) + 298 (VS 类专用) + 7 (Bulk EP) = 433 ✔
```

**（2）bmAttributes = 0xC0**

```
bit7  : 1  ← 保留位，USB 规范强制置 1（历史原因，不可清零）
bit6  : 1  ← Self Powered：设备自供电
bit5  : 0  ← Remote Wakeup：不支持远程唤醒
bit4..0: 0  ← 保留，必须为 0
```

设备是"自供电 + 不远程唤醒"，所以 `0b1100_0000 = 0xC0`。**bit7=1 是 spec 强制要求**——任何不置 bit7 的配置描述符都是违规范品，Host 会直接拒收。

**（3）MaxPower = 0x01 → 2 mA**

单位是 **2 mA**：`MaxPower × 2 mA = 实际最大总线电流`。0x01 → 2 mA，说明这台自供电摄像头从总线几乎不取电（只取 VBUS 做电平参考）。对比：总线供电设备常见 0x32 (100 mA) 或 0xFA (500 mA)。

---

## 2.3 IAD Descriptor（8 字节）

IAD（Interface Association Descriptor）不是 USB 1.x 就有的，是 USB 2.0 时代为了"复合设备的多接口功能绑定"新增的。**它必须紧跟在配置描述符之后、它所描述的第一个接口描述符之前**。

### 2.3.1 标准定义表

| 偏移 | 字段 | 长度 | 含义 |
|---|---|---|---|
| 0 | bLength | 1 | 固定 0x08 (8) |
| 1 | bDescriptorType | 1 | 类型码 0x0B (IAD) |
| 2 | bFirstInterface | 1 | 功能起始接口号 |
| 3 | bInterfaceCount | 1 | 功能包含的接口个数 |
| 4 | bFunctionClass | 1 | 功能的类码（0x0E = Video） |
| 5 | bFunctionSubClass | 1 | 功能的子类码 |
| 6 | bFunctionProtocol | 1 | 功能的协议码 |
| 7 | iFunction | 1 | 功能字符串索引（0 = 无） |

### 2.3.2 字节地图（设备 1 实际值）

```
+----+----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  |  ← 偏移
+----+----+----+----+----+----+----+----+
| H  | H  | N  | N  | C  | C  | C  | N  |  ← 颜色分类
+----+----+----+----+----+----+----+----+
| 08 | 0B | 00 | 02 | 0E | 03 | 00 | 05 |  ← 设备 1 字节
+----+----+----+----+----+----+----+----+
  bL  bDT  bFI  bIC  └─bFunction─┘   iF
```

### 2.3.3 三设备对照表

| 字段 | 标准要求 | 设备 1 | 设备 2 | 设备 3 | 解读 |
|---|---|---|---|---|---|
| bLength | 0x08 | 0x08 | 0x08 | 无数据 | |
| bDescriptorType | 0x0B | 0x0B | 0x0B | 无数据 | IAD |
| bFirstInterface | 起始接口 | 0x00 | 0x00 | 无数据（推断 0x00 视频 / 0x02 音频） | 接口 0 起 |
| bInterfaceCount | ≥1 | 0x02 | 0x02 | 无数据（推断每功能 2 个） | 绑定接口 0~1 |
| bFunctionClass | 0x0E = Video | 0x0E | 0x0E | 无数据（推断 0x0E 视频 / 0x01 音频） | **真正的功能分类** |
| bFunctionSubClass | 0x03 = Video Interface Collection | 0x03 | 0x03 | 无数据 | VC+VS 集合 |
| bFunctionProtocol | 0x00 | 0x00 | 0x00 | 无数据 | |
| iFunction | 索引或 0 | 0x05 "UVC Camera" | 0x05 "UVC Camera" | 无数据 | |

### 2.3.4 关键字段深入

**（1）bFirstInterface + bInterfaceCount 划定功能边界**

设备 1：`bFirstInterface=0`、`bInterfaceCount=2` → 接口 0 和接口 1 同属一个 Video 功能。Host 的驱动加载逻辑：

```
配置里有 IAD 吗？
 ├─ 没有 → 每个接口独立找驱动
 └─ 有 → 把 bFirstInterface..bFirstInterface+bInterfaceCount-1 的接口
         绑成一个功能，为整个功能加载一个驱动
```

设备 3（推断）会有两个 IAD：IAD1 绑接口 0~1（视频），IAD2 绑接口 2~3（音频）——Windows 设备树里就能看到 `MI_00`（视频节点）和 `MI_02`（音频节点）两个独立功能节点，这正是复合设备在设备管理器里的呈现。

**（2）bFunctionClass = 0x0E 才是"摄像头"的正式声明**

设备描述符里 class 是 0xEF（含糊的 Miscellaneous），真正的"这是视频功能"写在 IAD 里。Host 的 UVC 驱动（Windows 的 usbvideo.sys）就是看到 `bFunctionClass=0x0E, bFunctionSubClass=0x03 (Video Interface Collection)` 才决定加载自己的。

MQTT 类比：设备描述符的 0xEF 像 CONNACK 里的"连接标志"，IAD 像后续的具体主题声明（`topic: camera/video`）——前者只说"连接建立了"，后者才说"这个功能是什么"。

---

## 2.4 Interface Descriptor（9 字节）

设备 1/2 有**两个**接口描述符：接口 0（VC）与接口 1（VS）。两者字段布局完全相同，只有取值不同。UVC 规范要求 VC 的 subclass=0x01、VS 的 subclass=0x02——这是 Host 区分"控制接口"与"流接口"的依据。

### 2.4.1 标准定义表（一张表，两列值）

| 偏移 | 字段 | 长度 | 含义 | 设备 1 接口 0 (VC) | 设备 1 接口 1 (VS) |
|---|---|---|---|---|---|
| 0 | bLength | 1 | 固定 0x09 | 0x09 | 0x09 |
| 1 | bDescriptorType | 1 | 0x04 (Interface) | 0x04 | 0x04 |
| 2 | bInterfaceNumber | 1 | 接口号（同号接口共享同一逻辑接口） | 0x00 | 0x01 |
| 3 | bAlternateSetting | 1 | 备用设置号（0 = 默认） | 0x00 | 0x00 |
| 4 | bNumEndpoints | 1 | 端点个数（不含 EP0） | 0x01 | 0x01 |
| 5 | bInterfaceClass | 1 | 接口类码 | 0x0E (Video) | 0x0E (Video) |
| 6 | bInterfaceSubClass | 1 | 接口子类码 | **0x01 (Video Control)** | **0x02 (Video Streaming)** |
| 7 | bInterfaceProtocol | 1 | 协议码 | 0x00 | 0x00 |
| 8 | iInterface | 1 | 接口字符串索引 | 0x05 "UVC Camera" | 0x06 "Video Streaming" |

### 2.4.2 字节地图（两张并排）

```
接口 0 (VC):                            接口 1 (VS):
+----+----+----+----+----+----+----+----+----+   +----+----+----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  |   | 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  |
+----+----+----+----+----+----+----+----+----+   +----+----+----+----+----+----+----+----+----+
| H  | H  | N  | N  | N  | C  | C  | C  | N  |   | H  | H  | N  | N  | N  | C  | C  | C  | N  |
+----+----+----+----+----+----+----+----+----+   +----+----+----+----+----+----+----+----+----+
| 09 | 04 | 00 | 00 | 01 | 0E | 01 | 00 | 05 |   | 09 | 04 | 01 | 00 | 01 | 0E | 02 | 00 | 06 |
+----+----+----+----+----+----+----+----+----+   +----+----+----+----+----+----+----+----+----+
  bL  bDT  bIN  bAS  bNE  bIC bIS bIP  iI       bL  bDT  bIN  bAS  bNE  bIC bIS bIP  iI
```

### 2.4.3 三设备对照表

| 字段 | 标准要求 | 设备 1 | 设备 2 | 设备 3 | 解读 |
|---|---|---|---|---|---|
| bLength | 0x09 | 0x09 | 0x09 | 无数据 | |
| bDescriptorType | 0x04 | 0x04 | 0x04 | 无数据 | |
| bInterfaceNumber | ≥0 | 0x00 / 0x01 | 0x00 / 0x01 | 0x00 / 0x02（推断自 MI_00 / MI_02） | 设备 3 至少 4 个接口 |
| bAlternateSetting | 0 起 | 0x00 / 0x00 | 0x00 / 0x00 | 无数据 | 都只用默认设置（见 FAQ Q2） |
| bNumEndpoints | ≥0 | 0x01 / 0x01 | 0x01 / 0x01 | 无数据 | 不含 EP0 |
| bInterfaceClass | 0x0E | 0x0E | 0x0E | 无数据 | Video |
| bInterfaceSubClass | 0x01 VC / 0x02 VS | 0x01 / 0x02 | 0x01 / 0x02 | 无数据 | VC 与 VS 的判别字段 |
| bInterfaceProtocol | 0x00 | 0x00 | 0x00 | 无数据 | |
| iInterface | 索引或 0 | 0x05 / 0x06 | 0x05 / 0x06 | 无数据 | "UVC Camera" / "Video Streaming" |

### 2.4.4 关键字段深入

**（1）bInterfaceSubClass：VC = 0x01，VS = 0x02**

这是 UVC 描述符体系的第一道分叉口。Host 拿到接口描述符后：

```
bInterfaceClass == 0x0E (Video) ?
 ├─ subclass 0x01 → 这是 Video Control 接口：解析 0x24/0x25 类描述符，
 │                  加载控制逻辑（调焦、曝光等请求走 EP0 + 中断 EP）
 └─ subclass 0x02 → 这是 Video Streaming 接口：解析 0x24 流描述符，
                    协商格式（YUY2/MJPEG/H264）、打开数据端点传视频
```

**（2）bAlternateSetting = 0x00（默认）**

备用设置（Alternate Setting）是 USB 的带宽开关机制：同一接口号可以有多个接口描述符，bAlternateSetting 不同、端点配置不同。UVC 流接口的典型设计：alt 0 无数据端点（不占带宽），alt 1/2/3… 各有不同包长的等时端点（占递增带宽）。设备 1/2 只声明了 alt 0——因为它们的视频数据走 **Bulk** 端点，不需要带宽预留，一个档位就够。详见 FAQ Q2。

**（3）bNumEndpoints**

接口下端点个数，**不含 EP0**。VC 接口的 1 个端点 = 中断 IN 端点（EP3）；VS 接口的 1 个端点 = Bulk IN 端点（EP1）。注意：VC 接口本身的控制请求（UVC class request）走 EP0，不算在 bNumEndpoints 里。

---

## 2.5 Endpoint Descriptor（7 字节）

设备 1/2 各有 2 个端点：EP3 IN（Interrupt，VC 状态通知）与 EP1 IN（Bulk，视频数据）。端点描述符布局相同，重点看传输类型字段的取值差异。

### 2.5.1 标准定义表（一张表，两列值）

| 偏移 | 字段 | 长度 | 含义 | EP3 IN (Interrupt) | EP1 IN (Bulk) |
|---|---|---|---|---|---|
| 0 | bLength | 1 | 固定 0x07 | 0x07 | 0x07 |
| 1 | bDescriptorType | 1 | 0x05 (Endpoint) | 0x05 | 0x05 |
| 2 | bEndpointAddress | 1 | 端点地址（方向 + 号） | 0x83 | 0x81 |
| 3 | bmAttributes | 1 | 传输类型 + 属性 | 0x03 (Interrupt) | 0x02 (Bulk) |
| 4 | wMaxPacketSize | 2 | 最大包长 + 附加事务 | 0x0010 (16 B) | 0x0200 (512 B) |
| 6 | bInterval | 1 | 轮询间隔 | 0x08 | 0x00 |

### 2.5.2 字节地图（两张并排）

```
EP3 IN (Interrupt):                         EP1 IN (Bulk):
+----+----+----+----+----+----+----+        +----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  |        | 0  | 1  | 2  | 3  | 4  | 5  | 6  |
+----+----+----+----+----+----+----+        +----+----+----+----+----+----+----+
| H  | H  | E  | E  | K  | K  | E  |        | H  | H  | E  | E  | K  | K  | E  |
+----+----+----+----+----+----+----+        +----+----+----+----+----+----+----+
| 07 | 05 | 83 | 03 | 10 | 00 | 08 |        | 07 | 05 | 81 | 02 | 00 | 02 | 00 |
+----+----+----+----+----+----+----+        +----+----+----+----+----+----+----+
  bL  bDT  bEA  bmA  └─wMaxPacketSize─┘ bI   bL  bDT  bEA  bmA  └─wMaxPacketSize─┘ bI
```

### 2.5.3 三设备对照表

| 字段 | 标准要求 | 设备 1 | 设备 2 | 设备 3 | 解读 |
|---|---|---|---|---|---|
| bLength | 0x07 | 0x07 | 0x07 | 无数据 | 固定 |
| bDescriptorType | 0x05 | 0x05 | 0x05 | 无数据 | 固定 |
| bEndpointAddress | bit7=方向，bit3..0=号 | 0x83 / 0x81 | 0x83 / 0x81 | 无数据 | 两个都是 IN 端点 |
| bmAttributes | 低 2 位 = 类型 | 0x03 (Int) / 0x02 (Bulk) | 同左 | 无数据 | 中断 = 状态通道，Bulk = 数据通道 |
| wMaxPacketSize | 见下 | 0x0010 / 0x0200 | 0x0010 / 0x0200 | 无数据 | 16 B / 512 B (HS) |
| bInterval | 随类型/速度变化 | 0x08 / 0x00 | 0x08 / 0x00 | 无数据 | 中断 16 ms；Bulk 忽略 |

### 2.5.4 关键字段深入

**（1）bEndpointAddress：bit7 = 方向，bit3..0 = 端点号**

```
0x83 = 0b1000_0011   bit7=1 → IN（设备→主机）;  号 = 3  → EP3
0x81 = 0b1000_0001   bit7=1 → IN;               号 = 1  → EP1
```

设备 1/2 只有 IN 端点（摄像头只往外吐数据，不需要 OUT 数据端点；控制走 EP0）。

**（2）bmAttributes：低 2 位 = 传输类型**

```
00 = Control    01 = Isochronous (等时)    10 = Bulk (批量)    11 = Interrupt (中断)
```

- `0x03` → Interrupt：VC 接口的状态通知通道（UVC 事件如曝光变化等）。
- `0x02` → Bulk：视频数据通道。Bulk 有 CRC 重传保证，但带宽不预留；设备 1/2 分辨率不高（最高 640×360@30 MJPEG），Bulk 足够。等时端点见 4.3 的设备 3 分析。

**（3）wMaxPacketSize 的位域**

```
bits 15..13  : 保留，必须为 0
bits 12..11  : 每微帧附加事务数 (仅 HS，0~2；值 3 = 非法)
bits 10..0   : 最大包长
```

- 中断 EP：0x0010 → 包长 16 字节，无附加事务。
- Bulk EP：0x0200 → 包长 512 字节（HS Bulk 最大 512，FS 最大 64——这就是 4.2 里 Other Speed Config 中变成 0x0040 的原因）。

**（4）bInterval：HS 下的计算公式**

| 传输类型 | FS 间隔 | HS 间隔 |
|---|---|---|
| Interrupt | `bInterval` 毫秒 | **2^(bInterval-1) × 125 µs** |
| Isochronous | `bInterval` 毫秒 | **2^(bInterval-1) × 125 µs** |
| Bulk / Control | 忽略 | 忽略 |

设备 1 中断 EP：`bInterval=0x08` → HS 间隔 = 2^7 × 125 µs = **16 ms**（每 16 ms 轮询一次，每次最多 16 字节，带宽需求极小 ≈ 8 kbit/s）。设备 2 的 Other Speed Config 里同一个 `0x08` 在 FS 语义下 = **8 ms**——同一字节，两种速度两种含义，这是 4.2 的重点。设备 1 的抓取工具把 HS 下 0x08 换算为"128 microframes → 16 ms"，正确。

MQTT 类比：bInterval 像 MQTT 的 Keep Alive 心跳间隔——告诉 Host "你多久来问候我一次"。中断端点 = 低频心跳主题，Bulk 端点 = 大流量数据主题（不设心跳，全靠流量本身）。

---

# 第 3 章 类专用描述符机制（UVC）

标准描述符只解决"设备有几层、几接口、几端点"的骨架问题。摄像头该怎么控制、支持哪些视频格式，标准描述符一概不答——这是**类专用（Class-Specific）描述符**的领域。本章以 UVC 为例讲透它的机制，并用设备 1 的 VC Header 做逐字节示例。

## 3.1 0x24 / 0x25 的分发原理：同一个类型码，两种含义

UVC 的类专用描述符大量复用同一个 `bDescriptorType`：

```
bDescriptorType = 0x24 (Video Control Interface)
   └─ 由"所属接口的 bInterfaceSubClass"决定含义
        ├─ 接口 subclass = 0x01 (VideoControl)  →  VC 类描述符
        │     0x01 VC Header          0x02 Input Terminal
        │     0x03 Output Terminal    0x04 Selector Unit
        │     0x05 Processing Unit    0x06 Extension Unit
        └─ 接口 subclass = 0x02 (VideoStreaming) → VS 类描述符
              0x01 VS Input Header     0x04 Uncompressed Format
              0x05 Uncompressed Frame  0x06 MJPEG Format
              0x07 MJPEG Frame         0x0D Color Matching
              0x10 Frame-Based Format  0x11 Frame-Based Frame

bDescriptorType = 0x25 (Video Control Endpoint)  → 只出现在 VC 接口下
       0x03 Interrupt（VC 中断端点的类专用信息）

bDescriptorType = 0x26 (Video Streaming Endpoint) → 只出现在 VS 接口下（本设备未用）
```

**为什么可以复用同一个类型码？** 因为解析上下文不同：Host 遍历描述符链时，先读到接口描述符（0x04），知道当前处于哪个接口（subclass 是多少），之后遇到的 0x24 就按该接口的语义解析。这就像 MQTT 里同一个 topic 名在不同层级（`camera/ctl/` 与 `camera/data/`）承载不同类型报文——**靠上下文区分，不靠类型码本身**。

这也意味着：**类专用描述符必须紧跟所属接口描述符**（以及紧随其后的端点描述符），链的顺序不能乱。顺序乱了，0x24 就会解析到错误的含义。

## 3.2 逐字节拆解：VC Header Descriptor（13 字节）

VC Header 是整个 VC 类专用子链的第一个描述符，相当于"这条子链的目录"。设备 1 的原始字节：

```
偏移: 0  1  2  3  4  5  6  7  8  9  10 11 12
      0D 24 01 10 01 51 00 00 6C DC 02 01 01
```

| 偏移 | 字段 | 值 | 含义 |
|---|---|---|---|
| 0 | bLength | 0x0D (13) | 固定 |
| 1 | bDescriptorType | 0x24 | Video Control Interface |
| 2 | bDescriptorSubtype | 0x01 | **VC Header** |
| 3-4 | bcdUVC | 0x0110 | **UVC 版本 1.10**（BCD：0x01.0x10） |
| 5-6 | wTotalLength | 0x0051 (81) | **VC 类专用子链总长 81 字节** |
| 7-10 | dwClockFreq | 0x02DC6C00 (48,000,000) | 设备时钟频率 **48 MHz**（帧时间戳 PTS 的计时基准；小端字节 = `00 6C DC 02`） |
| 11 | bInCollection | 0x01 | 有 1 个 VS 接口与 VC 关联 |
| 12 | baInterfaceNr[1] | 0x01 | 关联的 VS 接口号 = 接口 1 |

字节地图：

```
+----+----+----+----+----+----+----+----+----+----+----+----+----+
| 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  | 9  | 10 | 11 | 12 |  ← 偏移
+----+----+----+----+----+----+----+----+----+----+----+----+----+
| H  | H  | C  | S  | S  | N  | N  | N  | N  | N  | N  | N  | N  |  ← 颜色分类
+----+----+----+----+----+----+----+----+----+----+----+----+----+
| 0D | 24 | 01 | 10 | 01 | 51 | 00 | 00 | 6C | DC | 02 | 01 | 01 |  ← 设备 1 字节
+----+----+----+----+----+----+----+----+----+----+----+----+----+
  bL  bDT  bDS  └─bcdUVC─┘  └─wTotalLength─┘  └───dwClockFreq────┘  bIC baIN
```

逐字段深入：

- **bcdUVC = 0x0110**：设备实现的 UVC 规范版本。1.10 = UVC 1.1（UVC 1.5 会写 0x0150）。版本决定 Host 按哪版规范解析后续描述符。
- **wTotalLength = 0x51 = 81**：VC 子链总长 = 13 (Header) + 18 (IT) + 12 (PU) + 29 (XU) + 9 (OT) = **81 ✔**（不含端点描述符与 0x25——0x25 属于"类专用端点描述符"，不算在接口描述符子链里）。Host 靠它知道 VC 子链到哪里结束，好接着找下一个描述符。
- **dwClockFreq = 48 MHz**：设备用于产生视频帧时间戳（PTS）的时钟。Host 端播放器靠它把 PTS 换算成真实时间轴。0x02DC6C00 = 48,000,000 ✔。
- **bInCollection = 1 + baInterfaceNr[1] = 0x01**：声明"我的数据流搭档是接口 1"。这是 UVC 1.0/1.1 把 VC 与 VS 关联起来的机制（UVC 1.5 改用 bcdUVC + VS 的 bTerminalLink 反查）。Host 据此知道"控制接口 0 管着流接口 1 的摄像头"。

## 3.3 UVC 拓扑图：Terminal / Unit 链

UVC 的 VC 描述符构建了一张**图像处理流水线图**：传感器 → 端子/单元 → 流接口。标准拓扑（UVC 规范 2.1 节）：

```
  物理相机传感器
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Input        │───▶│ Processing    │───▶│ Extension    │───▶│ Output       │
│ Terminal     │    │ Unit          │    │ Unit         │    │ Terminal     │
│ ITT_CAMERA   │    │ (亮度/对比度/ │    │ (厂商私有    │    │ TT_STREAMING │
│ (ID 2)       │    │  增益等处理)  │    │  扩展控制)   │    │ (ID 3)       │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                 │ bTerminalLink=3
                                                                 ▼
                                                          VS 流接口 (接口 1)
                                                          Format → Frame 描述符
                                                          → EP1 IN Bulk 传视频
```

- **Input Terminal (IT)**：数据的源头（ITT_CAMERA = 摄像头传感器）。
- **Processing Unit (PU)**：标准图像处理（亮度、对比度、增益等，bmControls 位图声明支持哪些）。
- **Extension Unit (XU)**：厂商扩展，UVC 标准没定义的控制都塞在这里（设备 1 的 XU 有 15 个 vendor-specific 控制）。
- **Output Terminal (OT)**：数据出口（TT_STREAMING = 送给流接口）。OT 的 ID 被 VS Input Header 的 `bTerminalLink` 引用（= 3），把控制面与数据面接起来。
- 单元之间用 **ID 号** 串联：PU 的 `bSourceID` 指向上游单元 ID，XU 的 `baSourceID`、OT 的 `bSourceID` 同理。

**设备 1 的实际接线（对照 dump 逐条核对）：**

| 描述符 | ID | 上游引用 | 核对结果 |
|---|---|---|---|
| Input Terminal | 2 | — | ITT_CAMERA |
| Processing Unit | 5 | bSourceID = 1 | **引用了 dump 中不存在的 IT(1)**——固件小瑕疵或 dump 截取问题（见下注） |
| Extension Unit | 10 | baSourceID[1] = 2 | 上游是 IT(2) |
| Output Terminal | 3 | bSourceID = 2 | 上游是 IT(2)，**绕过 PU/XU 直接连 IT** |

> 注（真实世界的粗糙）：按 dump 的字面数据，OT(3) 与 XU(10) 都直接引用 IT(2)，PU(5) 引用的 IT(1) 在 dump 里没有对应描述符（VC 子链 81 字节逐项相加正好等于 wTotalLength，不存在截断）。这可能是固件把"未启用的处理单元"也写进了描述符。Host 端驱动一般只关心"IT → OT 主链路"，不会因此报错——但作为工程师你应该知道：**描述符是人写的固件数据，允许有这种不一致，应用代码要能容忍**。

对应用工程师最重要的是这条链的**控制入口**：所有控制请求（调亮度、切格式）都通过 EP0 发往 **VC 接口**（接口 0），目标用 (Unit/Terminal ID, Control Selector) 寻址；视频数据从 **VS 接口**（接口 1）的数据端点流出。

## 3.4 UVC 描述符类型码速查表

下表覆盖本手册用到的全部 subtype（bDescriptorSubtype）。注意：**同一 subtype 数值在 VC 接口与 VS 接口下含义不同**（3.1 的分发原理），所以下表按"所在接口"分列。0x10/0x11（Frame-Based）就是 UVC 1.1 规范的正式编号（Linux 内核 include/linux/usb/video.h 中 UVC_VS_FORMAT_FRAME_BASED=0x10、UVC_VS_FRAME_FRAME_BASED=0x11 与之一致）；设备声明 bcdUVC=1.10 并使用 0x10/0x11，完全符合规范，不存在"编号不一致"的问题。

| 值 (十进制) | 值 (十六进制) | VC 接口 (subclass 0x01) 下含义 | VS 接口 (subclass 0x02) 下含义 | 设备 1 中出现 |
|---|---|---|---|---|
| 1 | 0x01 | VC Header | VS Input Header | ✔ 两处都有 |
| 2 | 0x02 | Input Terminal | VS Output Header | ✔ VC |
| 3 | 0x03 | Output Terminal | VS Still Image Frame | ✔ VC |
| 4 | 0x04 | Selector Unit | Format: Uncompressed | ✔ VS |
| 5 | 0x05 | Processing Unit | Frame: Uncompressed | ✔ VC + VS |
| 6 | 0x06 | Extension Unit | Format: MJPEG | ✔ VC + VS |
| 7 | 0x07 | Encoding Unit (UVC 1.5) | Frame: MJPEG | ✔ VS |
| 8 | 0x08 | 保留 | 保留 | 无 |
| 9 | 0x09 | 保留 | 保留 | 无 |
| 10 | 0x0A | 保留 | Format: MPEG-2 TS | 无 |
| 11 | 0x0B | 保留 | 保留 | 无 |
| 12 | 0x0C | 保留 | Format: DV | 无 |
| 13 | 0x0D | 保留 | **Color Matching**（颜色匹配） | ✔ VS |
| 16 | 0x10 | 保留 | Format: Frame-Based（现行编号） | ✔ VS (H.264) |
| 17 | 0x11 | 保留 | Frame: Frame-Based（现行编号） | ✔ VS (H.264) |

设备 1 用到的组合：VC = 1,2,3,5,6（Header/IT/OT/PU/XU）；VS = 1,4,5,6,7,0x0D,0x10,0x11。

**注意**：subtype 只是"这种描述符存在"的声明，具体格式靠 `bFormatIndex` / `guidFormat` 区分（设备 1 的 VS 有 3 个 Format：YUY2、MJPEG、H.264）。

## 3.5 USB Audio Class 简要提及（设备 3）

设备 3 是"视频 + 音频"复合设备，音频部分（`MI_02`）由 Windows 的 usbaudio.sys（UAC 驱动）接管，KS 层只暴露：

- 格式：PCM，16 kHz / 16 bit / 单声道（麦克风采集）
- Pin：CAPTURE（采集）+ MICROPHONE 节点

UAC 1.0 与 UVC 的骨架完全同构——这就是类描述符体系的统一设计：

```
UAC (USB Audio Class) 与 UVC 对照：
  bInterfaceClass = 0x01 (Audio)       ←→  UVC 的 0x0E (Video)
  AC 接口 (subclass 0x01 AudioControl) ←→  UVC 的 VC (0x01)
  AS 接口 (subclass 0x02 AudioStreaming) ←→ UVC 的 VS (0x02)
  bDescriptorType 0x24 (Audio Control) ←→  UVC 的 0x24（同名同值，靠接口 subclass 分义）
  描述符: Input Terminal → Feature Unit → Output Terminal
         (0x0201 麦克风 / 0x0301 扬声器)
```

所以虽然设备 3 的原始描述符抓不到，但按 UVC 学的"接口 subclass 分义 + Terminal/Unit 链 + 类型码速查"这套方法，换成 UAC 规范表（0x24/0x25 的 Audio 版本）就能解析它的音频部分。**类专用描述符 = 标准骨架 + 每类规范一套"方言"**。

## 3.6 控制请求是怎么发的（对应用工程师最有用的一节）

描述符只是"声明"，真正控制设备靠 **EP0 上的类请求**。UVC 控制请求的编码（与 UAC 同构）：

```
SET_CUR : bmRequestType = 0x21 (Host→Device, Class, Interface), bRequest = 0x01
GET_CUR : bmRequestType = 0xA1 (Device→Host, Class, Interface), bRequest = 0x81
GET_MIN : 0x82    GET_MAX : 0x83    GET_RES : 0x84
GET_LEN : 0x85    GET_INFO: 0x86    GET_DEF : 0x87

wValue : CS —— 本厂商固件惯例：CS_ID 在**高字节**、低字节=0（wValue = CS << 8）
         ⚠ 与 UVC 规范不同：规范的标准写法是 CS 在低字节（wValue = CS），
         海康固件是反的（第六会话真机验证，见 xu_minimal_get.c 的 `CS_ID << 8`）
wIndex : 高字节 = Unit/Terminal ID，低字节 = 接口号（VC 接口 = 0）
数据阶段 : 控制值（长度由描述符/GET_LEN 决定）
```

例子——读设备 1 XU（Unit 10）的 vendor control 5 当前值：

| 设置 | 值 | 含义 |
|---|---|---|
| bmRequestType | 0xA1 | Device→Host，类请求，目标接口 |
| bRequest | 0x81 | GET_CUR |
| wValue | 0x0500 | CS=5（控制 5，高字节，本厂商惯例） |
| wIndex | 0x0A00 | 高字节=UnitID 0x0A（10），低字节=接口 0（VC） |
| wLength | 控制值长度 | 由 GET_LEN 查询 |

流接口的"切格式/启停流"走 VS 接口（接口 1）上的两个特殊控制：**VS_PROBE_CONTROL (CS=1)** 试探格式，**VS_COMMIT_CONTROL (CS=2)** 提交生效（Q7 里说的"流控制"就是这两个）。用 WinUSB / libusb 实现时，只需组装上面的 SETUP 包发到目标接口即可——这就是描述符之外，类机制的另一半。

---

# 第 4 章 综合实战

## 4.1 设备 1 完整 433 字节描述符链追踪

把设备 1 的整条链从第一个字节追到最后，逐段标注偏移与长度（十六进制）。所有偏移用 0x 表示，从配置头 0x0000 起算：

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
                                         合计 = 433 B = 0x01B1 ✔ 与 wTotalLength 吻合
```

**逐段验算（这是理解整条链的最好练习）：**

```
配置头 9 + IAD 8 + 接口 9×2 = 35
VC 类子链:  13 + 18 + 12 + 29 + 9  = 81   (0x51)   ✔ = VC Header 的 wTotalLength
VS 类子链:  16 + 27 + 90 + 11 + 90 + 28 + 30 + 6 = 298 (0x12A) ✔ = VS Input Header 的 wTotalLength
端点:       7 + 5 + 7 = 19
35 + 81 + 298 + 19 = 433 ✔
```

**对应的原始字节（每段开头 1~2 字节核对）：**

| 段 | 原始字节 (节选) | 验证点 |
|---|---|---|
| 配置头 | `09 02 B1 01 ...` | 9 字节；wTotalLength 小端 = B1 01 = 0x01B1 |
| IAD | `08 0B 00 02 0E 03 00 05` | 8 字节；0x0B 类型；function class 0x0E |
| VC 接口 | `09 04 00 00 01 0E 01 00 05` | subclass 0x01 |
| VC Header | `0D 24 01 10 01 51 00 00 6C DC 02 01 01` | 13 字节；bcdUVC 0x0110；wTotalLength 0x0051；48 MHz |
| VC IT | `12 24 02 02 01 02 00 00 00 00 00 00 00 00 03 00 00 00` | 18 字节；ITT_CAMERA 0x0201 |
| VC PU | `0C 24 05 05 01 00 40 02 00 00 00 09` | 12 字节；bSourceID=1；乘数 0x4000；标准 0x09 |
| VC XU | `1D 24 06 0A ... 0F 01 02 04 FF 03 00 00 00` | 29 字节；15 控制；bmControls FF 03 00 00 |
| VC OT | `09 24 03 03 01 01 00 02 00` | 9 字节；TT_STREAMING 0x0101；源 = IT(2) |
| EP3 中断 | `07 05 83 03 10 00 08` | 7 字节；0x83 IN EP3；0x03 中断；16 B；间隔 16 ms |
| 0x25 EP | `05 25 03 10 00` | 5 字节；wMaxTransferSize 16 B |
| VS 接口 | `09 04 01 00 01 0E 02 00 06` | subclass 0x02 |
| VS Header | `10 24 01 03 2A 01 81 00 03 00 00 00 01 00 00 00` | 16 字节；3 格式；wTotalLength 0x012A；bTerminalLink=3 |
| VS YUY2 | `1B 24 04 01 03 59 55 59 32 ...` | 27 字节；guidFormat 首 4 字节 "YUY2" |
| VS MJPEG | `0B 24 06 02 03 00 01 00 00 00 00` | 11 字节；3 帧 |
| VS H.264 | `1C 24 10 03 01 48 32 36 34 ...` | 28 字节；guidFormat 首 4 字节 "H264" |
| Color Matching | `06 24 0D 01 01 04` | 6 字节；BT.709 / BT.709 / SMPTE 170M |
| EP1 Bulk | `07 05 81 02 00 02 00` | 7 字节；0x81 IN EP1；0x02 Bulk；512 B |

> 有趣的现象（工具解析 bug）：设备 1/2 的 Summary 里有一条 "240 x 320 @ 1410065.408 fps : Frame Based Payload"——141 万帧/秒显然是抓取工具把 H.264 帧描述符的字段错位解析（正确的 240×320@30 写在 Frame 描述符里）。读 dump 时遇到这种"离谱数字"要先怀疑工具，再怀疑设备。

## 4.2 设备 1 vs 设备 2 差异分析

两台设备同型号同固件，几乎所有字段一致。逐项对比：

| 对比项 | 设备 1 | 设备 2 | 说明 |
|---|---|---|---|
| 序列号 (iSerialNumber=3) | "G11376317" | "E83518457" | **唯一描述符差异**，产线个体标识 |
| 设备地址 (总线分配) | 0x07 | 0x08 | 不是描述符，是 Host 枚举时分配的总线地址 |
| 抓取时电源状态 | D3（低功耗） | D0（正常工作） | 造成下一条差异的直接原因 |
| Device Qualifier Descriptor | **请求失败**（ERROR_GEN_FAILURE，设备在 D3） | 完整返回 (10 字节) | 见 FAQ Q4 |
| Other Speed Configuration | 未抓到 | 完整返回 (433 字节) | HS→FS 降级备胎 |
| Other-Speed 中 Bulk EP wMaxPacketSize | — | 0x0040 (64 B) | HS 是 0x0200 (512 B) |
| Other-Speed 中中断 EP bInterval 语义 | — | 0x08 → **8 ms (FS)** | HS 语义下同一字节 = **16 ms** |
| 其余所有描述符字节 | 与设备 2 完全相同 | 与设备 1 完全相同 | 同一产线同一固件 |

### Device Qualifier + Other Speed Configuration：HS→FS 降级备胎机制

USB 2.0 设备可能被插到**不同速度**的端口上：插在 HS 口跑 480 Mbps，插在老 FS 口（或 Hub 不支持 HS）就只跑 12 Mbps。设备的大多数描述符（类码、字符串等）与速度无关，但**端点参数与速度强相关**：

- Bulk 端点最大包长：HS = 512 B，FS = 64 B；
- bInterval 的换算公式：HS = 2^(n-1)×125 µs，FS = n ms；
- 等时端点的每微帧附加事务数：HS 才有。

如果等速切换时让 Host 重新枚举（Reset + SET_ADDRESS + 重读全部描述符），既慢又浪费。于是 USB 2.0 设计了两个"备胎"：

1. **Device Qualifier (0x06, 10 字节)**：告诉 Host "如果我在另一速度运行，设备描述符会怎么变"。字段与设备描述符基本一致（bcdUSB / class / bMaxPacketSize0 / bNumConfigurations），其中 `bNumConfigurations` = 另一速度下的配置数（设备 2 = 1）。**只有能跑双速的设备才有资格应答；单速设备必须 STALL 该请求。**
2. **Other Speed Configuration (0x07, 433 字节)**：整条配置链的"另一速度版本"。结构、长度、接口、类描述符完全一样，只有**端点参数按另一速度重写**（设备 2：Bulk 512→64，中断间隔换算基准 125µs→1ms）。

Host 的典型用法：设备以 HS 枚举完成后，Host 发 GetDescriptor(Device_Qualifier) 拿到另一速度信息；如果后面设备被移到 FS 端口，Host 请求 Other_Speed_Configuration，直接按备胎链配置设备，**无需重新枚举**。

设备 1 的 Qualifier 抓取失败是**时机问题**：抓包时设备处于 D3 低功耗态，控制请求没有得到有效应答（ERROR_GEN_FAILURE），不是设备不支持。这也提醒你：**抓描述符要在设备唤醒状态下抓**。

MQTT 类比：Device Qualifier + Other Speed Config 像 MQTT 5 的协商降级（CONNACK 里的 Maximum Packet Size / 版本回退）——设备在不同网络条件下声明不同的能力参数，主协议骨架不变。

## 4.3 设备 3 从 KS 数据反推描述符结构

设备 3 没有原始描述符 dump，但从 Windows 驱动层的数据完全可以反推出它的 USB 结构。**KS（Kernel Streaming）是驱动解析描述符后的结果**——就像从 MQTT Broker 的日志反推 Client 的订阅关系。

### 已知事实（来自设备 3 的 txt）

| 线索 | 值 | 反推出什么 |
|---|---|---|
| Device ID | `USB\VID_2BDF&PID_028A&REV_3000&MI_00` | VID=0x2BDF、PID=0x028A、bcdDevice=0x3000（REV_3000） |
| 视频节点路径 | `...&MI_00...` + usbvideo.sys | 接口 0 = 视频功能的**控制接口（VC）**；usbvideo.sys 是 Windows 的 UVC 类驱动 |
| 音频节点路径 | `...&MI_02...` + usbaudio.sys | 接口 2 = 音频功能的**控制接口（AC）**；usbaudio.sys 是 UAC 类驱动 |
| 接口号跳跃 | 有 MI_00 和 MI_02，没有 MI_01 / MI_03 节点 | 中间接口（1、3）是被 IAD 并入同一功能、不单独建节点的 VS/AS 接口 |
| Friendly Name | "2K USB Camera" / "2K USB Camera-Audio" | 复合设备，两个功能各有一个名字 |
| 视频格式表 | MJPG 最高 2560×1440@30；NV12/YUY2 只有低分辨率低帧率 | 见下方带宽分析 |
| 音频格式 | PCM 16 kHz / 16 bit / 1 ch | 单声道麦克风，UAC 1.0 典型配置 |

### 推断出的描述符结构

```
Device Descriptor (推断)          bDeviceClass = 0xEF（复合设备，必须）
└── Configuration Descriptor      bNumInterfaces ≥ 4
    ├── IAD #1                    bFirstInterface=0, bInterfaceCount=2
    │                             bFunctionClass=0x0E (Video)
    │   ├── Interface 0: VC       (MI_00, usbvideo.sys 绑定)
    │   │   └── VC 类描述符 + 中断端点
    │   └── Interface 1: VS       (推断；无独立节点，被 IAD 并入功能)
    │       └── VS 类描述符 + 数据端点（推断为等时，见下）
    ├── IAD #2                    bFirstInterface=2, bInterfaceCount=2
    │                             bFunctionClass=0x01 (Audio)
    │   ├── Interface 2: AC       (MI_02, usbaudio.sys 绑定)
    │   │   └── 音频控制描述符 (0x24: IT 麦克风 → Feature Unit → OT)
    │   └── Interface 3: AS       (推断；音频流接口)
    │       └── 音频流描述符 + 等时端点 (16 kHz×2 B = 32 kB/s，带宽极小)
    └── (字符串：厂商/产品/序列号，无数据)
```

为什么接口号是 0 和 2？UVC 规范要求 VC 与 VS **相邻成对**（IAD 的 bFirstInterface..+count 连续），所以视频占用接口 0~1；音频功能接着从接口 2 开始（AC=2, AS=3）。Windows 只为"功能入口接口"（VC/AC）建节点，VS/AS 被 usbccgp 复合驱动并入，因此设备树里只见 MI_00 与 MI_02——这个"跳号"本身就是 IAD 存在的证据。

### 为什么 2560×1440@30 MJPEG 需要等时端点保证带宽

先算 HS 的带宽硬预算：

```
HS 等时端点理论上限：每微帧最多 3 个事务 × 1024 B = 3072 B
                    3072 B × 8000 微帧/秒 ≈ 24.6 MB/s ≈ 197 Mbps（含协议开销实际更低）
```

再看设备 3 的格式表与带宽需求（KS 的 Bit Rate = 分辨率 × bpp/8 × 帧率，可验证）：

| 格式 | 分辨率 @ 帧率 | 需要的带宽 | 结论 |
|---|---|---|---|
| YUY2 | 1920×1080 @ 5 | 20.7 MB/s | 勉强塞进等时预算（~85%）→ 只能给 5 fps |
| NV12 | 1280×960 @ 10 | 18.4 MB/s | 同样逼近预算 → 只能给 10 fps |
| MJPG | 2560×1440 @ 30 | 压缩后远小于原始 331.8 MB/s | **只有压缩格式能跑满 30 fps** |

- 原始 YUY2 的 2560×1440@30 = 221 MB/s，**远超 HS 总线能力**，所以无压缩模式只能低分辨率/低帧率；
- MJPEG 是逐帧压缩，2560×1440 单帧压缩后通常 0.5~2 MB（24 bpp 的 331.8 MB/s 只是 KS 工具按原始位深折算的名义值，不是真实总线流量），30 fps 大约 15~60 MB/s——仍在等时预算内；
- **等时端点保证带宽**：等时传输在每个微帧有固定的事务槽（wMaxPacketSize 位 12..11 的附加事务数就是用来声明要占几个槽），Host 据此做带宽调度，视频帧不会因为总线上别的事务而延迟——这是实时视频流的关键。设备 1/2 用 Bulk 是因为分辨率低（640×360 以下），Bulk 的重传机制反而更省心；设备 3 要做到 2K@30，**最可能的设计就是等时端点 + 多组 Alternate Setting**（每档一个包长，FAQ Q2 的机制）。

所以从 KS 层就能反推出：设备 3 的 VS 接口**推断有等时端点、多档 Alternate Setting、以及把 MJPEG 放到最大分辨率的设计**。这就是"没有原始描述符也能做结构推断"的完整方法。

---

# 第 5 章 FAQ

### Q1: 为什么 bDeviceClass 不直接写 0x0E (Video)？

因为摄像头是**复合设备**：一个 Video 功能 = VC + VS 两个接口。设备级 class 只能描述"整台设备"，描述不了接口分组。USB 规范规定：凡是用 IAD 做功能绑定的复合设备，设备级必须声明 `0xEF (Miscellaneous) / 0x02 / 0x01`，把真正的功能分类交给 IAD 的 bFunctionClass=0x0E。写了 0x0E 反而违反规范——Host 会以为整台设备只有一个接口，直接拒绝加载。见 2.1.4。

### Q2: Alternate Setting 在描述符里怎么体现？

同一接口号出现**多个接口描述符**，bInterfaceNumber 相同、bAlternateSetting 依次递增（0,1,2…），端点配置不同。Host 用 `SET_INTERFACE(接口号, 设置号)` 切换。典型 UVC VS 设计：

```
接口 1, alt 0 : 0 个数据端点（不占带宽）          ← 默认，枚举后先停在 0
接口 1, alt 1 : 等时端点 wMaxPacketSize=512 B     ← 低带宽档
接口 1, alt 2 : 等时端点 wMaxPacketSize=1024 B    ← 高带宽档
```

应用开视频时，驱动按所选格式挑一档 alt 设置并切换，用完再切回 alt 0 释放带宽。**设备 1/2 只有 alt 0**（Bulk 不需要带宽预留）；设备 3（推断）有多档 alt（见 4.3）。MQTT 类比：同一"主题"（接口）提供 QoS 0/1/2 三档服务，连接时声明用哪档。

### Q3: bMaxPacketSize0 对 HS 设备为什么固定 64 字节？

USB 2.0 规范 9.6.1 硬性规定：**HS 设备的 EP0 最大包长必须是 64 字节**。原因：EP0 是控制通道，控制传输（SETUP + DATA + STATUS）每个事务只能传一个包；64 字节是 HS 下控制事务的标准包长，所有 HS 设备统一，Host 栈的缓冲区与调度器就不用为不同设备准备不同尺寸。LS=8、FS 可选 8/16/32/64，HS 无选择——**统一 64 是规范强制的简化**。枚举早期 Host 就是靠这个字段决定后续控制传输怎么切包。

### Q4: Device Qualifier 什么情况下 Host 会请求？

USB 2.0 规范 9.6.2：**只有能跑双速（HS 与 FS）的设备才有 Device Qualifier**；单速设备必须对该请求回 STALL。Host 在设备**以 HS 运行**时会请求它（拿到"若在 FS 运行会是什么样"的信息）；若设备以 FS 运行而 Host 想知道它的 HS 能力，同样可以请求。配套的是 Other Speed Configuration（0x07）——另一速度下的整条配置链。典型场景：设备先在 HS 口枚举，之后被插到只支持 FS 的口（或经 FS Hub），Host 不必重新枚举，直接用备胎链配置。设备 1 的 Qualifier 抓取失败纯粹是**设备处于 D3 低功耗态**的抓取时机问题。

### Q5: IAD 和 Interface Descriptor 里的 Class 有什么不同？

两者是**两个层级**的声明：

| | IAD 的 bFunctionClass | 接口的 bInterfaceClass |
|---|---|---|
| 描述对象 | 一**组**接口（功能） | 单个接口 |
| 设备 1 的值 | 0x0E (Video) | 0x0E (Video)，但 subclass 分 VC(0x01)/VS(0x02) |
| 驱动加载作用 | 决定"这组接口归哪个类驱动管" | 驱动内部再按 subclass 分派角色 |
| 音频功能对照 | 0x01 (Audio) | AC 接口 0x01/0x01，AS 接口 0x01/0x02 |

IAD 是"功能级"的：usbvideo.sys 看到 Video Interface Collection（0x0E/0x03）就绑定整个功能；接口 class 是"接口级"的：VC/VS 的分工靠它。两者分工明确，缺一不可。

### Q6: UVC Extension Unit 的 15 个 vendor-specific controls 是干什么的？

设备 1/2 的 XU（Unit ID 10）声明 `bNumControls=15`、GUID `{A29E7641-DE04-47E3-8B2B-F4341AFF003B}`（海康私有扩展标识）。这 15 个控制是**标准 UVC 没定义的厂商私有控制**——通常是曝光模式、增益、白平衡、降噪、图像翻转等厂商标定参数。注意 `bmControls = FF 03 00 00` 只置位了低 10 位，即**实际启用 control 1~10**，其余 5 个未启用。

应用怎么用它们：向 VC 接口（接口 0）发 UVC 类请求 `SET_CUR/GET_CUR`，wValue 高位 = 控制号（1~10），低位 = Unit ID（10），wIndex = 接口号。含义只有厂商知道（对应海康 SDK 的私有控制项），第三方只能枚举 `GET_INFO` 试探可用性。这解释了 Q7——标准控制全关，私有控制是主通道。

### Q7: 设备 1 & 2 的 bmControls 全是 0，怎么控制摄像头？

对照 dump：

- Camera IT 的 bmControls = `00 00 00` → 标准摄像头控制（曝光、增益、对焦等）**全部未实现**；
- PU 的 bmControls = `00 00` → 标准处理控制（亮度、对比度等）**全部未实现**。

意味着对这些标准控制发 GET_CUR/SET_CUR，设备会回 STALL 或错误——**它们真的不存在**。实际控制通道是：

1. **XU 的 vendor-specific 控制**（见 Q6）：10 个已启用的私有控制承担了真实的图像调节，需用厂商 SDK 访问；
2. **VS 接口的流控制**：切格式、启停流走 VS 的 PROBE/COMMIT 类请求（VideoStreaming Interface Control），与 bmControls 无关；
3. 其余参数（如自动曝光）由固件自动管理，不开放。

结论：**bmControls=0 只代表"标准控制没实现"，不代表设备不可控**——看 XU 和 VS 控制才是这类摄像头应用的正确姿势。做应用时先枚举 XU（GET_INFO），别假设标准控制可用。

### Q8: 为什么 Bus Hound 抓包看不到 Token 包、Handshake 包和 PID 字段？

这是 USB 学习中一个经典分水岭——你抓到的数据**完全正确**，Bus Hound 本来就看不到这些东西。

**根本原因：Bus Hound 是软件层抓包工具，工作在 USB 驱动栈里。**

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

Bus Hound 插在操作系统驱动栈中间，截获的是 **URB（USB Request Block）和传输的数据负载**——这是驱动层看到的东西。Token 包、Handshake 包、PID 字节、SYNC 字段、CRC5/CRC16——这些全在**硬件层**由 USB 主机控制器（xHCI）自动生成和解析，软件连看都看不到。

**类比：这就像用 Wireshark 抓 HTTP 却看不到 TCP 的 SYN/ACK seq 号。**

| Wireshark 抓 HTTP | Bus Hound 抓 USB |
|---|---|
| HTTP 请求/响应（文本） | 你的数据（调色板、码流类型、YUV 帧） |
| TCP 段（seq/ack 号） | URB（传输状态、字节数、端点地址） |
| IP 帧 → 以太网帧 | **Token/Data/Handshake 包** ← 你学过的那些 |
| 电平信号 | **SYNC + PID + CRC + EOP** ← 硬件处理 |

TCP 栈剥掉了 IP/以太网帧头，应用层只看到数据流。同样，xHCI 硬件剥掉了 PID/CRC/SYNC/EOP，驱动层只看到"这个 URB 传了多少字节，状态是什么"。你代码里写 `libusb_bulk_transfer(devh, 0x81, buf, size, &recv_len, timeout)` 的时候，底层发生的是：

```
Host 控制器自动生成:
  IN Token  →  [SYNC][PID=0x69(IN)][ADDR][ENDP=1][CRC5][EOP]
Device 回应:
  DATA0/1   →  [SYNC][PID=0xC3(DATA0)][512 bytes YUV payload][CRC16][EOP]
Host 应答:
  ACK       →  [SYNC][PID=0xD2(ACK)][EOP]
```

Bus Hound 只告诉你 "这次 bulk transfer 收到了 512 字节"——那 512 字节就是 DATA 包里**去掉 PID 和 CRC 后的 payload**。Token 是谁发的、Device 回的 DATA 包 PID 是 DATA0 还是 DATA1、有没有 NAK 重试——这些在硬件层自动完成，软件完全感知不到。

**怎么才能看到 PID/Token/Handshake？需要硬件 USB 协议分析仪。**

| 工具 | 价格 | 用途 |
|---|---|---|
| Ellisys USB Explorer | $3000+ | 专业级，USB 3.0/2.0 |
| Total Phase Beagle 480 | ~$500 | USB 2.0 协议分析 |
| OpenVizsla（开源） | ~$150 | 入门级 USB 2.0 嗅探 |

这些设备直接串在 D+/D- 物理线上，能抓到最原始的包——SYNC、PID、Token、Data、Handshake、CRC、EOP 全部可见。

**那之前学的那些白学了吗？没有，完全不是。** 理解 Token→Data→Handshake 的事务模型、理解 PID 编码（高 4 位 = ~低 4 位）、理解 DATA0/1 翻转——这些东西在你看到 Bus Hound 里出现一连串超时或 STALL 的时候，是你做调试的唯一线索。USB 不像 TCP 有丰富的内核统计（`ss -i` / `netstat -s`），出问题了你只能靠协议模型推理。"Host 中心化"意味着 Device 绝不会主动发数据——如果你在 Bus Hound 上看到数据到了，那一定是 Host 先发了 IN Token。**你看见了数据，看不见谁请的客，但你知道一定有请客的那一下。**

### Q9: 为什么批量传输的 payload 前面 8 字节长得跟控制传输的 SETUP 包一模一样？

**这不是 USB 规范要求的——是厂商自己抄过去的。**

USB 规范层面：控制传输的 SETUP 包有固定 8 字节格式（bmRequestType + bRequest + wValue + wIndex + wLength），批量传输是纯数据管道，爱发什么发什么。

但实际设备中，你经常在 Bus Hound 里看到：

```
Bulk OUT  0x03  12B    A1 81 00 04 00 0A 04 00 [32 2E 30 00]
                       ↑── 跟 SETUP 包完全一样的 8 字节 ──↑ ↑ payload ↑
```

**为什么厂商要这么干？**

| | EP0 控制传输 | 批量端点模拟 |
|---|---|---|
| 并发 | 一次一个请求，等 STATUS 完 | 可以排多个命令，异步执行 |
| 数据量 | wLength 最大 64KB，HS 每包 64B | 512B/包，多大命令都行 |
| 排队 | 必须等上一笔 STATUS 闭环 | 可以 pipeline |
| 代码复用 | — | **直接复用 EP0 的命令解析代码** |

核心原因就一句话：**"我们在 EP0 上已经写了一套命令解析代码，再为批量端点重新设计一套格式太傻了。直接把 EP0 那 8 字节头搬过来，解析代码复用，唯一的区别是——不走 EP0 那个慢车道，走批量端点这条高速公路。"**

**这算违反 USB 规范吗？不算。** 规范只规定 EP0 必须是控制传输（有那 8 字节头），但没有禁止其他端点模仿。批量端点是"纯数据管道"——数据里面是什么格式，完全是厂商的自由。类比：TCP 定义了 SYN/ACK/FIN 握手，但没有禁止你在 payload 里传 HTTP 格式。HTTP、gRPC、MQTT——都是"用了 TCP 的传输能力，自己的协议格式塞 payload 里"。

**Bus Hound 怎么看穿？** Bus Hound 不管这些——控制传输的 `CTL` 行会帮你展开那 8 字节，批量传输的 `Bulk` 行就是一坨 hex。当你看到 `Bulk OUT, 12B, A1 81 00 04 00 0A...`，能认出来这是 UVC GET_CUR 的格式——说明你 USB 协议已经入门了。

### Q10: STATUS 阶段只是锦上添花的"收到了"吗？

**不是。STATUS 是不可或缺的协议硬需求——它是设备拒绝不支持的 SETUP 命令的唯一切入点。**

理解为什么，要先看三个约束：

1. **SETUP 阶段设备必须 ACK**（见 Q8 和 2.17）——SETUP Token 一到达，硬件自动清空状态机、强制 DATA0，设备**不能**在这里说"不支持"
2. **DATA 阶段不一定有**——如果 wLength=0（纯控制命令，不需要数据），DATA 阶段直接跳过
3. **Endpoint 0 是共享资源**——Host 需要明确知道"这笔交易完了，可以发下一个 SETUP 了"

三条加在一起：SETUP 拦不住拒绝，DATA 可能不存在，那拒绝在哪里表达？

```
SETUP:  "给我不存在的描述符 #99"
        Device → ACK  ← SETUP 必须 ACK，不能拒绝
DATA:   无数据（或回了也是错的）
STATUS: Device → STALL ← ❌ 拒绝唯一发生在这里！
        或
        Device → ACK  ← ✅ 交易成功

对比批量传输——没有 STATUS 阶段，每个包都可以直接回 STALL:
  OUT Token → DATA → STALL  ← 当场拒绝，不需要 STATUS
```

**STATUS 不是"锦上添花"——它是控制传输的"判决书"。** SETUP 是"请求"，DATA 是"证据"，STATUS 是"裁决"——成功（ACK）还是驳回（STALL）。去掉 STATUS，设备对不支持的 SETUP 命令连说"不"的权利都没有。

**所以三段式不是冗余设计——是权力分立：**
- SETUP = 提出请求（必须受理）
- DATA = 提供数据（可选）
- STATUS = 宣布判决（✅ 或 ❌，必须做出）

---

# 附录 A 设备 1 完整原始 dump（精简）

> 格式：字段 = 值（十六进制），去掉了抓取工具的行号与逐位展开，保留全部描述符字段。来源 `captures/usb设备1的描述符.txt`（序列号 G11376317）。

```
===== 设备信息 =====
VID = 0x2BDF (Hangzhou Hikvision Digital Technology Co., Ltd.)
PID = 0x0101    Serial = "G11376317"
USB 版本 = 2.0 (480 Mbit/s)    速度 = High-Speed
Self Powered = yes    Demanded Current = 2 mA    已用端点 = 3
Video = UVC Version 1.10
默认视频模式: 640x360@30 (MJPEG/Uncompressed); 240x320@30 (MJPEG); 120x160@25 (MJPEG)
(注: Summary 中 "240x320 @ 1410065.408 fps: Frame Based Payload" 为工具解析 bug)
设备地址 = 0x07    Current Config = 0x01    电源状态 = D3
Pipe[0]: EP3 IN Interrupt wMaxPacketSize=0x10 bInterval=8
Pipe[1]: EP1 IN Bulk       wMaxPacketSize=0x200 bInterval=0

===== Device Descriptor (18 B) =====
bLength = 0x12    bDescriptorType = 0x01 (Device)
bcdUSB = 0x0200    bDeviceClass = 0xEF (Miscellaneous)
bDeviceSubClass = 0x02    bDeviceProtocol = 0x01 (IAD)
bMaxPacketSize0 = 0x40 (64)    idVendor = 0x2BDF    idProduct = 0x0101
bcdDevice = 0x0409
iManufacturer = 0x01 "HIK"    iProduct = 0x02 "HikCamera"
iSerialNumber = 0x03 "G11376317"    bNumConfigurations = 0x01

===== Configuration Descriptor (9 B) =====
bLength = 0x09    bDescriptorType = 0x02 (Configuration)
wTotalLength = 0x01B1 (433)    bNumInterfaces = 0x02
bConfigurationValue = 0x01    iConfiguration = 0x04 "Config 1"
bmAttributes = 0xC0 (D7=1, D6=Self Powered, D5=no Remote Wakeup)
MaxPower = 0x01 (2 mA)

===== IAD Descriptor (8 B) =====
bLength = 0x08    bDescriptorType = 0x0B (IAD)
bFirstInterface = 0x00    bInterfaceCount = 0x02
bFunctionClass = 0x0E (Video)    bFunctionSubClass = 0x03 (Video Interface Collection)
bFunctionProtocol = 0x00    iFunction = 0x05 "UVC Camera"

===== Interface 0 (VC) Descriptor (9 B) =====
bLength = 0x09    bDescriptorType = 0x04
bInterfaceNumber = 0x00    bAlternateSetting = 0x00    bNumEndpoints = 0x01
bInterfaceClass = 0x0E (Video)    bInterfaceSubClass = 0x01 (Video Control)
bInterfaceProtocol = 0x00    iInterface = 0x05 "UVC Camera"

===== VC Header Descriptor (13 B) =====
bLength = 0x0D    bDescriptorType = 0x24    bDescriptorSubtype = 0x01 (Header)
bcdUVC = 0x0110 (1.10)    wTotalLength = 0x0051 (81)
dwClockFreq = 0x02DC6C00 (48 MHz)
bInCollection = 0x01    baInterfaceNr[1] = 0x01 (Interface 1)

===== VC Input Terminal Descriptor (18 B) =====
bLength = 0x12    bDescriptorType = 0x24    bDescriptorSubtype = 0x02 (Input Terminal)
bTerminalID = 0x02    wTerminalType = 0x0201 (ITT_CAMERA)
bAssocTerminal = 0x00    iTerminal = 0x00
wObjectiveFocalLengthMin = 0x0000    wObjectiveFocalLengthMax = 0x0000
wOcularFocalLength = 0x0000
bControlSize = 0x03    bmControls = 0x00, 0x00, 0x00 (无标准控制)

===== VC Processing Unit Descriptor (12 B) =====
bLength = 0x0C    bDescriptorType = 0x24    bDescriptorSubtype = 0x05 (Processing Unit)
bUnitID = 0x05    bSourceID = 0x01
wMaxMultiplier = 0x4000 (163.84x Zoom)
bControlSize = 0x02    bmControls = 0x00, 0x00 (无标准控制)
iProcessing = 0x00
bmVideoStandards = 0x09 (None + SECAM-625/50)

===== VC Extension Unit Descriptor (29 B) =====
bLength = 0x1D    bDescriptorType = 0x24    bDescriptorSubtype = 0x06 (Extension Unit)
bUnitID = 0x0A    guidExtensionCode = {A29E7641-DE04-47E3-8B2B-F4341AFF003B}
bNumControls = 0x0F (15)    bNrInPins = 0x01    baSourceID[1] = 0x02
bControlSize = 0x04    bmControls = 0xFF, 0x03, 0x00, 0x00 (control 1~10 启用)
iExtension = 0x00

===== VC Output Terminal Descriptor (9 B) =====
bLength = 0x09    bDescriptorType = 0x24    bDescriptorSubtype = 0x03 (Output Terminal)
bTerminalID = 0x03    wTerminalType = 0x0101 (TT_STREAMING)
bAssocTerminal = 0x00    bSourceID = 0x02    iTerminal = 0x00

===== Endpoint EP3 IN Interrupt (7 B) =====
bLength = 0x07    bDescriptorType = 0x05
bEndpointAddress = 0x83 (IN, EP3)    bmAttributes = 0x03 (Interrupt)
wMaxPacketSize = 0x0010 (16 B, 无附加事务)    bInterval = 0x08 (HS: 128 microframes = 16 ms)

===== Class-Specific VC EP Descriptor (5 B) =====
bLength = 0x05    bDescriptorType = 0x25    bDescriptorSubtype = 0x03 (Interrupt)
wMaxTransferSize = 0x0010 (16 B)

===== Interface 1 (VS) Descriptor (9 B) =====
bLength = 0x09    bDescriptorType = 0x04
bInterfaceNumber = 0x01    bAlternateSetting = 0x00    bNumEndpoints = 0x01
bInterfaceClass = 0x0E (Video)    bInterfaceSubClass = 0x02 (Video Streaming)
bInterfaceProtocol = 0x00    iInterface = 0x06 "Video Streaming"

===== VS Input Header Descriptor (16 B) =====
bLength = 0x10    bDescriptorType = 0x24    bDescriptorSubtype = 0x01 (Input Header)
bNumFormats = 0x03    wTotalLength = 0x012A (298)
bEndpointAddress = 0x81 (IN, EP1)    bmInfo = 0x00
bTerminalLink = 0x03    bStillCaptureMethod = 0x00    nbTriggerSupport = 0x00
bTriggerUsage = 0x00    bControlSize = 0x01    bmaControls(3) = 0x00, 0x00, 0x00

===== VS Uncompressed Format (27 B, index 1) =====
bLength = 0x1B    bDescriptorType = 0x24    bDescriptorSubtype = 0x04 (Format Uncompressed)
bFormatIndex = 0x01    bNumFrameDescriptors = 0x03
guidFormat = {32595559-0000-0010-8000-00AA00389B71} (YUY2)
bBitsPerPixel = 0x10 (16)    bDefaultFrameIndex = 0x01
bAspectRatioX = 0x00    bAspectRatioY = 0x00    bmInterlaceFlags = 0x00
bCopyProtect = 0x00
(注: 工具报 "no Color Matching Descriptor for this format" —— 该格式未带颜色描述符)

===== VS Uncompressed Frame ×3 (30 B each) =====
Frame 1: 120x160  位率 0x00753000 (7.68 Mbps)  缓冲 0x00009600 (38400 B)
         默认间隔 0x00061A80 (40 ms = 25 fps)  离散间隔 1 个
Frame 2: 240x320  位率 0x02328000 (36.864 Mbps)  缓冲 0x00025800 (153600 B)
         默认间隔 0x00051615 (33.3333 ms = 30 fps)  离散间隔 1 个
Frame 3: 640x360  位率 0x06978000 (110.592 Mbps)  缓冲 0x00070800 (460800 B)
         默认间隔 0x00051615 (33.3333 ms = 30 fps)  离散间隔 1 个

===== VS MJPEG Format (11 B, index 2) =====
bLength = 0x0B    bDescriptorType = 0x24    bDescriptorSubtype = 0x06 (Format MJPEG)
bFormatIndex = 0x02    bNumFrameDescriptors = 0x03
bmFlags = 0x00 (样本大小不固定)    bDefaultFrameIndex = 0x01
bAspectRatioX = 0x00    bAspectRatioY = 0x00    bmInterlaceFlags = 0x00
bCopyProtect = 0x00

===== VS MJPEG Frame ×3 (30 B each) =====
Frame 1: 120x160  位率 0x00753000 (7.68 Mbps)  缓冲 38400 B  25 fps
Frame 2: 240x320  位率 0x009C4000 (10.24 Mbps)  缓冲 153600 B  30 fps
Frame 3: 640x360  位率 0x009C4000 (10.24 Mbps)  缓冲 460800 B  30 fps

===== VS Frame-Based Format (28 B, index 3, H.264) =====
bLength = 0x1C    bDescriptorType = 0x24    bDescriptorSubtype = 0x10 (Format Frame Based)
bFormatIndex = 0x03    bNumFrameDescriptors = 0x01
guidFormat = {34363248-0000-0010-8000-00AA00389B71} (H264)
bBitsPerPixel = 0x10 (16)    bDefaultFrameIndex = 0x01
bAspectRatioX = 0x00    bAspectRatioY = 0x00    bmInterlaceFlags = 0x00
bCopyProtect = 0x00    bVariableSize = 0x01 (变长)

===== VS Frame-Based Frame (30 B) =====
Frame 1: 240x320  位率 0x007D0000 (8.192 Mbps)  缓冲 153600 B  30 fps
dwBytesPerLine = 0x0000
(注: 工具按 UVC 1.5 字段表展开此描述符需要 32 字节，而 bLength 声明 30 字节——
 与 VS 子链 wTotalLength=298 的验算一致。属固件长度声明与字段表之间的轻微
 不一致，Host 驱动按 bLength 解析即可，不影响使用)

===== VS Color Matching (6 B) =====
bLength = 0x06    bDescriptorType = 0x24    bDescriptorSubtype = 0x0D (Color Matching)
bColorPrimaries = 0x01 (BT.709, sRGB)
bTransferCharacteristics = 0x01 (BT.709)
bMatrixCoefficients = 0x04 (SMPTE 170M)

===== Endpoint EP1 IN Bulk (7 B) =====
bLength = 0x07    bDescriptorType = 0x05
bEndpointAddress = 0x81 (IN, EP1)    bmAttributes = 0x02 (Bulk)
wMaxPacketSize = 0x0200 (512 B)    bInterval = 0x00 (忽略)

===== Device Qualifier =====
请求失败: ERROR_GEN_FAILURE (设备处于 D3 低功耗状态)

===== String Descriptors =====
String 0: 语言 ID [0] = 0x0409 (English-US)
String 1 (0x01): "HIK" (8 B)
String 2 (0x02): "HikCamera" (20 B)
String 3 (0x03): "G11376317" (20 B)
String 4 (0x04): "Config 1" (18 B)
String 5 (0x05): "UVC Camera" (22 B)
String 6 (0x06): "Video Streaming" (32 B)
```

---

# 附录 B 设备 2 完整原始 dump（精简）

> 来源 `captures/usb设备2的描述符.txt`（序列号 E83518457）。与设备 1 完全相同的部分用「同设备 1」省略，仅列出差异与新增段。

```
===== 设备信息 =====
VID = 0x2BDF    PID = 0x0101    Serial = "E83518457"
USB 版本 = 2.0 (480 Mbit/s)    速度 = High-Speed
Self Powered = yes    电流 = 2 mA    已用端点 = 3    UVC Version 1.10
设备地址 = 0x08    Current Config = 0x01    电源状态 = D0 (工作态)
Pipe[0]: EP3 IN Interrupt wMaxPacketSize=0x10 bInterval=8
Pipe[1]: EP1 IN Bulk       wMaxPacketSize=0x200 bInterval=0

===== Device Descriptor (18 B) =====
与设备 1 完全相同，唯一差异: iSerialNumber = 0x03 "E83518457"

===== Configuration / IAD / Interface / VC 类描述符 / VS 类描述符 / 端点 / 字符串 =====
与设备 1 完全相同 (wTotalLength = 0x01B1 = 433)

===== Device Qualifier Descriptor (10 B) =====
bLength = 0x0A    bDescriptorType = 0x06 (Device_qualifier)
bcdUSB = 0x0200    bDeviceClass = 0xEF    bDeviceSubClass = 0x02
bDeviceProtocol = 0x01 (IAD)    bMaxPacketSize0 = 0x40 (64)
bNumConfigurations = 0x01 (1 other-speed configuration)    bReserved = 0x00

===== Other Speed Configuration Descriptor (433 B) =====
bLength = 0x09    bDescriptorType = 0x07 (Other_speed_configuration)
wTotalLength = 0x01B1 (433)    bNumInterfaces = 0x02
bConfigurationValue = 0x01    iConfiguration = 0x04 "Config 1"
bmAttributes = 0xC0    MaxPower = 0x01 (2 mA)
(后续 IAD / 接口 / 类专用描述符与设备 1 的配置链完全一致)

──── 与 HS 配置的端点差异（其余全同）────
EP3 IN Interrupt: bInterval = 0x08 → FS 语义 = 8 ms (HS 语义 = 16 ms)
EP1 IN Bulk:      wMaxPacketSize = 0x0040 (64 B)  ← FS 下 Bulk 最大包长
                  bInterval = 0x00 (忽略)
```

---

# 附录 C 设备 3 KS 数据摘要

> 来源 `captures/usb设备3的描述符.txt`。设备 3 没有原始 USB 描述符，以下为 Windows 驱动解析后的 KS 层数据。

```
===== 设备信息 =====
Friendly Name  : "2K USB Camera" (视频) / "2K USB Camera-Audio" (音频)
Device ID      : USB\VID_2BDF&PID_028A&REV_3000&MI_00  (视频, usbvideo.sys)
                 USB\VID_2BDF&PID_028A&REV_3000&MI_02  (音频, usbaudio.sys)
推断: VID=0x2BDF, PID=0x028A, bcdDevice=0x3000, 复合设备(视频+音频), 接口 0~3

===== 视频格式表 (Pin 0: CAPTURE) =====
32 个 Data Range (每种格式每个分辨率 ×2 种 Specifier: VIDEOINFO / VIDEOINFO2)

| 格式 | 分辨率 @ 帧率 | KS Bit Rate (bps) | 推断带宽需求 |
|---|---|---|---|
| MJPG (24 bpp 名义) | 2560×1440 @ 30 | 2,654,208,000 (名义) | 压缩后实际 << 预算 |
| MJPG | 1920×1080 @ 30 | 1,492,992,000 (名义) | 压缩后实际 << 预算 |
| MJPG | 1280×960 @ 30 | 884,736,000 (名义) | 压缩后实际 << 预算 |
| MJPG | 1280×720 @ 30 | 663,552,000 (名义) | 压缩后实际 << 预算 |
| MJPG | 640×480 @ 30 | 221,184,000 (名义) | 压缩后实际 << 预算 |
| MJPG | 640×360 @ 30 | 165,888,000 (名义) | 压缩后实际 << 预算 |
| NV12 (12 bpp) | 1920×1080 @ 5 | 124,416,000 (15.55 MB/s) | 等时预算内 |
| NV12 | 1280×960 @ 10 | 147,456,000 (18.43 MB/s) | 接近等时预算上限 |
| NV12 | 1280×720 @ 15 | 165,888,000 (20.74 MB/s) | 接近等时预算上限 |
| NV12 | 640×480 @ 30 | 110,592,000 (13.82 MB/s) | 等时预算内 |
| NV12 | 640×360 @ 30 | 82,944,000 (10.37 MB/s) | 等时预算内 |
| YUY2 (16 bpp) | 1920×1080 @ 5 | 165,888,000 (20.74 MB/s) | 接近等时预算上限 |
| YUY2 | 1280×960 @ 5 | 98,304,000 (12.29 MB/s) | 等时预算内 |
| YUY2 | 1280×720 @ 10 | 147,456,000 (18.43 MB/s) | 接近等时预算上限 |
| YUY2 | 640×480 @ 30 | 147,456,000 (18.43 MB/s) | 接近等时预算上限 |
| YUY2 | 640×360 @ 30 | 110,592,000 (13.82 MB/s) | 等时预算内 |

(注: MJPG 的 KS Bit Rate 是"24 bpp 名义原始速率"= W×H×3×fps，不代表真实总线流量;
 NV12/YUY2 的 Bit Rate = W×H×bpp/8×fps，与真实流量一致)

===== 音频 (Pin 0: CAPTURE + Pin 1: MICROPHONE) =====
格式: PCM, 16 kHz / 16 bit / 单声道 (1 ch)
数据流: 麦克风模拟 → 采集 (KSNODETYPE_MICROPHONE)
推断 USB 结构: UAC 1.0, AC 接口 (MI_02) + AS 接口 (MI_03), 等时端点
带宽: 16000 × 2 B = 32 kB/s，极低
```
