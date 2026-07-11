# libuvc 系统学习知识笔记

> 源码版本：v0.0.7 | 学习日期：2026-07-11  
> 基于 libuvc 源码 + UVC 规范的系统学习记录

---

## 目录

1. [UVC 规范基础](#1-uvc-规范基础)
2. [libuvc 架构总览](#2-libuvc-架构总览)
3. [设备发现与打开流程](#3-设备发现与打开流程)
4. [UVC 描述符解析](#4-uvc-描述符解析)
5. [UVC 控制传输协议](#5-uvc-控制传输协议)
6. [流协商机制（Probe/Commit）](#6-流协商机制probecommit)
7. [视频流传输核心流程](#7-视频流传输核心流程)
8. [视频流报文协议（Payload Header）](#8-视频流报文协议payload-header)
9. [帧获取与回调机制](#9-帧获取与回调机制)
10. [流停止与资源清理](#10-流停止与资源清理)
11. [帧格式转换](#11-帧格式转换)
12. [完整调用序列](#12-完整调用序列)
13. [XU 扩展单元与厂商自定义控制](#13-xu-扩展单元与厂商自定义控制)
14. [Payload 组帧与异常恢复](#14-payload-组帧与异常恢复)
15. [附录：源码文件速查](#15-附录源码文件速查)

---

## 1. UVC 规范基础

### 1.1 什么是 UVC

UVC = USB Video Device Class，USB 标准视频设备类规范。作用：让操作系统不需要厂商驱动即可使用 USB 摄像头。

### 1.2 规范版本

| 版本 | bcdUVC | 特点 |
|------|--------|------|
| UVC 1.0 | 0x0100 | 最广泛，26 字节流控制块 |
| UVC 1.1 | 0x010a | 增加时钟频率字段 |
| UVC 1.5 | 0x0110 | 34 字节控制块，H.264，Frame-based 格式 |

### 1.3 两大接口

```
UVC 设备
├── VC 接口 (VideoControl, Subclass=1)  — "遥控器"：控制传输
└── VS 接口 (VideoStreaming, Subclass=2) — "水管"：视频流传输
```

- **VC**：控制传输（Control Transfer），设置曝光/亮度/对焦等；中断传输（Interrupt Transfer），设备状态通知
- **VS**：等时传输（Isochronous）或批量传输（Bulk），承载视频帧数据

### 1.4 单元模型（Unit Model）

```
镜头 → Camera Terminal → Processing Unit → Extension Unit → Output Terminal → USB 主机
         (CT/传感器)      (PU/图像处理)      (EU/厂商扩展)
```

- **Camera Terminal**：传感器控制（曝光/聚焦/变焦/云台/隐私）
- **Processing Unit**：图像处理（亮度/对比度/饱和度/锐度/白平衡/增益/伽马）
- **Extension Unit**：厂商自定义，由 GUID 标识
- **Selector Unit**：多路输入选择

### 1.5 UVC 设备识别

USB 接口描述符中 `bInterfaceClass=14 (Video)` 且 `bInterfaceSubClass=2 (Streaming)` 即被识别为 UVC 设备。

---

## 2. libuvc 架构总览

### 2.1 源码文件职责

```
include/libuvc/
├── libuvc.h            公共 API 头文件
└── libuvc_internal.h   内部结构与常量

src/
├── init.c              初始化/销毁 (uvc_init/uvc_exit)
├── device.c            设备发现/打开/描述符解析
├── ctrl.c              底层控制传输 (get/set_ctrl)
├── ctrl-gen.c          自动生成的高层控制函数
├── stream.c            视频流核心 (打开/启动/收帧/组装)
├── frame.c             帧内存管理 + 颜色格式转换
├── frame-mjpeg.c        MJPEG → RGB 转换 (需 libjpeg)
├── diag.c              错误信息与调试打印
├── misc.c              杂项工具
├── example.c           示例程序
└── test.c              测试程序
```

### 2.2 五个核心结构体

```
uvc_context_t          — "大管家"，管理 libusb 上下文 + 所有打开的设备
  └─ uvc_device_t      — "摄像头身份证"，指向 libusb_device，引用计数
       └─ uvc_device_handle_t — "遥控器"，libusb 句柄 + 描述符树 + 流列表
            └─ uvc_stream_handle_t — "一条视频流"，双缓冲 + transfer 数组 + 回调线程
```

### 2.3 描述符数据树

```
uvc_device_info_t
├── ctrl_if (VC 接口)
│     ├── bcdUVC              版本号
│     ├── dwClockFrequency    时钟频率
│     ├── input_term_descs →  Camera Terminal 链表
│     ├── processing_unit_descs → PU 链表
│     ├── selector_unit_descs → Selector Unit 链表
│     └── extension_unit_descs → EU 链表
└── stream_ifs (VS 接口链表)
      └── format_descs → 格式链表
            ├── guidFormat / fourccFormat
            ├── bBitsPerPixel
            └── frame_descs → 帧配置链表
                  ├── wWidth, wHeight
                  ├── dwDefaultFrameInterval (100ns 单位)
                  ├── dwMaxVideoFrameBufferSize
                  └── intervals[] (可选帧率列表)
```

### 2.4 两条数据通道

```
通道一：控制（同步，一问一答）
  程序 → ctrl-gen.c → libusb_control_transfer → USB 总线 → 设备

通道二：视频流（异步，持续不断）
  设备 → USB 等时/批量传输 → _uvc_stream_callback → 解析 → 组帧 → 用户回调
```

---

## 3. 设备发现与打开流程

### 3.1 完整调用链

```c
uvc_context_t *ctx;
uvc_device_t *dev;
uvc_device_handle_t *devh;

uvc_init(&ctx, NULL);                         // ① 创建上下文
uvc_find_device(ctx, &dev, 0, 0, NULL);       // ② 找第一个 UVC 设备
uvc_open(dev, &devh);                         // ③ 打开设备
// ... 使用 ...
uvc_close(devh);                              // ④ 关闭设备
uvc_unref_device(dev);                        // ⑤ 释放设备引用
uvc_exit(ctx);                                // ⑥ 销毁上下文
```

### 3.2 uvc_init() — 创建上下文

```c
// init.c:104-124
uvc_init(&ctx, usb_ctx=NULL)
  ├── calloc 分配 uvc_context_t
  ├── usb_ctx==NULL → libusb_init() 创建新上下文 + own_usb_ctx=1
  └── usb_ctx!=NULL → 使用已有上下文 + own_usb_ctx=0
```

### 3.3 uvc_get_device_list() — 发现 UVC 设备

遍历所有 USB 设备，检查每个接口的每个 altsetting：
- `bInterfaceClass==14 && bInterfaceSubClass==2` → UVC 设备
- 特殊处理：Imaging Source 相机（vendor=0x199e, bInterfaceClass=255, bInterfaceSubClass=2）

### 3.4 uvc_find_device() — 查找特定设备

```c
uvc_find_device(ctx, &dev, vid, pid, sn)
  ├── uvc_get_device_list() → 全部设备
  └── 遍历匹配: (!vid || vid==desc->idVendor) && (!pid || pid==desc->idProduct) && (!sn || 序列号匹配)
```

### 3.5 uvc_open() — 打开设备（6 个步骤）

```
① libusb_open()               — USB 层面打开设备
② uvc_get_device_info()       — 解析 UVC 描述符 → 构建描述符树
③ uvc_claim_if(VC)            — 声明 VC 接口（先 detach 内核驱动）
④ 注册中断传输               — 监听设备状态通知
⑤ 启动事件处理线程           — 如果是第一个打开的设备
⑥ DL_APPEND → open_devices   — 加入全局设备列表
```

### 3.6 uvc_close() — 关闭设备

```
① 停掉所有流 (uvc_stop_streaming)
② uvc_release_if → libusb_release_interface → attach_kernel_driver
③ 最后一个设备 → 杀死事件线程 → pthread_join
④ libusb_close → 释放内存
```

---

## 4. UVC 描述符解析

### 4.1 数据来源

UVC Class-Specific 描述符存储在 USB 接口描述符的 `extra` 字段中。每个描述符块格式：

```
[bLength(1B)] [bDescriptorType=36(1B)] [bDescriptorSubtype(1B)] [payload(变长)]
```

### 4.2 解析主循环

```c
// device.c:1096-1107
buffer = if_desc->extra;
buffer_left = if_desc->extra_length;
while (buffer_left >= 3) {
    block_size = buffer[0];     // 读长度
    uvc_parse_vc(buffer);       // 分发给具体解析器
    buffer += block_size;
    buffer_left -= block_size;
}
```

### 4.3 VC 描述符分发 (uvc_parse_vc)

| Subtype | 解析函数 | 产生的结果 |
|---------|----------|-----------|
| 0x01 VC_HEADER | uvc_parse_vc_header | bcdUVC, dwClockFrequency, 触发 stream_if 扫描 |
| 0x02 INPUT_TERMINAL | uvc_parse_vc_input_terminal | bTerminalID, wTerminalType, bmControls |
| 0x03 OUTPUT_TERMINAL | — | 暂未实现 |
| 0x04 SELECTOR_UNIT | uvc_parse_vc_selector_unit | bUnitID |
| 0x05 PROCESSING_UNIT | uvc_parse_vc_processing_unit | bUnitID, bSourceID, bmControls |
| 0x06 EXTENSION_UNIT | uvc_parse_vc_extension_unit | bUnitID, GUID(16B), bmControls |

### 4.4 VS 描述符分发 (uvc_parse_vs)

| Subtype | 解析函数 | 产生的结果 |
|---------|----------|-----------|
| 0x01 INPUT_HEADER | uvc_parse_vs_input_header | bEndpointAddress, bTerminalLink |
| 0x04 FORMAT_UNCOMPRESSED | uvc_parse_vs_format_uncompressed | format_desc (YUYV 等) |
| 0x05 FRAME_UNCOMPRESSED | uvc_parse_vs_frame_uncompressed | frame_desc (分辨率/帧率) |
| 0x06 FORMAT_MJPEG | uvc_parse_vs_format_mjpeg | format_desc (MJPEG) |
| 0x07 FRAME_MJPEG | uvc_parse_vs_frame_uncompressed | frame_desc |
| 0x10 FORMAT_FRAME_BASED | uvc_parse_vs_frame_format | format_desc (H.264 等) |
| 0x11 FRAME_FRAME_BASED | uvc_parse_vs_frame_frame | frame_desc |

**帧描述符始终属于它前面最近的格式描述符**，解析时取 `stream_if->format_descs->prev`。

### 4.5 帧率编码

```c
// bFrameIntervalType == 0: 连续范围
frame->dwMinFrameInterval = DW_TO_INT(&block[26]);
frame->dwMaxFrameInterval = DW_TO_INT(&block[30]);
frame->dwFrameIntervalStep = DW_TO_INT(&block[34]);

// bFrameIntervalType > 0: 离散列表
frame->intervals = calloc(n + 1, sizeof(uint32_t));
for (i = 0; i < n; ++i)
    frame->intervals[i] = DW_TO_INT(p);
// 帧率(fps) = 10000000 / interval
```

---

## 5. UVC 控制传输协议

### 5.1 USB 控制传输参数

每个控制命令由 5 个部分构成，对应 libusb_control_transfer 的参数：

| 字段 | 含义 | 控制传输编码规则 |
|------|------|-----------------|
| bmRequestType | 方向+类型 | GET=0xA1, SET=0x21 |
| bRequest | 操作 | SET_CUR=0x01, GET_CUR=0x81, GET_MIN=0x82, GET_MAX=0x83, GET_RES=0x84, GET_LEN=0x85, GET_INFO=0x86, GET_DEF=0x87 |
| wValue | 控制选择器 | `Control_Selector << 8` |
| wIndex | 目标单元 | `Unit_ID << 8 \| Interface_Number` |
| data | 数据 | 变长，由具体控制决定 |

### 5.2 请求码

```c
UVC_SET_CUR = 0x01   // 写：设置当前值
UVC_GET_CUR = 0x81   // 读：获取当前值
UVC_GET_MIN = 0x82   // 读：最小值
UVC_GET_MAX = 0x83   // 读：最大值
UVC_GET_RES = 0x84   // 读：分辨率/步长
UVC_GET_LEN = 0x85   // 读：数据长度
UVC_GET_INFO = 0x86  // 读：能力信息（可读/可写/是否禁用）
UVC_GET_DEF = 0x87   // 读：默认值
```

GET 类请求最高位 (bit7=1) 表示方向为 Device→Host。

### 5.3 控制两大"家族"

#### Camera Terminal 控制（寻址目标 = Camera Terminal 的 bTerminalID）

```
uvc_set_ae_mode()           自动曝光模式 (1=手动,2=自动,4=快门优先,8=光圈优先)
uvc_set_exposure_abs()      绝对曝光时间 (0.0001秒单位)
uvc_set_focus_abs()         绝对聚焦距离 (mm)
uvc_set_focus_auto()        自动对焦开关
uvc_set_zoom_abs()          变焦焦距
uvc_set_pantilt_abs()       云台控制 (pan + tilt)
uvc_set_privacy()           隐私快门
```

#### Processing Unit 控制（寻址目标 = Processing Unit 的 bUnitID）

```
uvc_set_brightness()        亮度
uvc_set_contrast()          对比度
uvc_set_gain()              增益
uvc_set_hue()               色调
uvc_set_saturation()        饱和度
uvc_set_sharpness()         锐度
uvc_set_gamma()             伽马
uvc_set_white_balance_temperature()      白平衡色温
uvc_set_white_balance_component()        白平衡分量 (blue/red)
uvc_set_power_line_frequency()           电源频率（防闪烁）
uvc_set_backlight_compensation()        背光补偿
```

### 5.4 通用底层 API

```c
// 读取任意终端/单元的任意控制
int uvc_get_ctrl(devh, unit_id, ctrl_selector, data, len, UVC_GET_CUR);
// 写入
int uvc_set_ctrl(devh, unit_id, ctrl_selector, data, len);
// 查询控制长度
int uvc_get_ctrl_len(devh, unit_id, ctrl_selector);
```

所有高层 API 均由 `ctrl-gen.py` 自动生成，结构完全一样。

---

## 6. 流协商机制（Probe/Commit）

### 6.1 核心概念

- **Probe**（试探）：发送你的要求，设备返回它能做到的最接近参数。不改变设备状态。
- **Commit**（确认）：确认使用 Probe 阶段协商的参数，设备真正切换。

### 6.2 uvc_stream_ctrl_t 结构

```
UVC 1.0 (26字节)                UVC 1.1+ (34字节，多8字节)
┌──────────────────────┐        ┌──────────────────────────────┐
│ bmHint         (2B)  │        │ bmHint                 (2B)  │
│ bFormatIndex   (1B)  │        │ bFormatIndex           (1B)  │
│ bFrameIndex    (1B)  │        │ bFrameIndex            (1B)  │
│ dwFrameInterval(4B)  │        │ dwFrameInterval        (4B)  │
│ wKeyFrameRate  (2B)  │        │ wKeyFrameRate          (2B)  │
│ wPFrameRate    (2B)  │        │ wPFrameRate            (2B)  │
│ wCompQuality   (2B)  │        │ wCompQuality           (2B)  │
│ wCompWindowSize(2B)  │        │ wCompWindowSize        (2B)  │
│ wDelay         (2B)  │        │ wDelay                 (2B)  │
│ dwMaxVideoFrame(4B)  │        │ dwMaxVideoFrameSize    (4B)  │
│ dwMaxPayload   (4B)  │        │ dwMaxPayloadTransfer   (4B)  │
└──────────────────────┘        │ dwClockFrequency       (4B)  │     ← 新增
                                │ bmFramingInfo          (1B)  │     ← 新增
                                │ bPreferredVersion      (1B)  │     ← 新增
                                │ bMinVersion            (1B)  │     ← 新增
                                │ bMaxVersion            (1B)  │     ← 新增
                                └──────────────────────────────┘
```

### 6.3 协商流程

```
① uvc_get_stream_ctrl_format_size(devh, &ctrl, YUYV, 640, 480, 30)
     └── 查描述符树 → 找匹配的 format/frame → 填 ctrl 初始值

② uvc_probe_stream_ctrl(devh, &ctrl)
     ├── Probe + SET_CUR → "我想要这组参数"
     ├── Probe + GET_CUR → 设备回填实际值
     └── 验证: 格式/帧率匹配 && dwMaxPayloadTransferSize OK?

③ uvc_stream_ctrl(strmh, &ctrl)  // 在 stream_open 时调用
     └── Commit + SET_CUR → "确认！设备真正切换"
```

### 6.4 uvc_query_stream_ctrl() — 底层发动机

```c
uvc_query_stream_ctrl(devh, ctrl, probe, req)
// probe=1 → UVC_VS_PROBE_CONTROL; probe=0 → UVC_VS_COMMIT_CONTROL
// req → SET_CUR 写入 / GET_CUR 读取
```

内部通过 `SHORT_TO_SW` / `INT_TO_DW` 将 C 结构体序列化为字节数组，通过 USB 控制传输发送。

### 6.5 协商验证

```c
static int _uvc_stream_params_negotiated(required, actual) {
    return required->bFormatIndex == actual->bFormatIndex
        && required->bFrameIndex == actual->bFrameIndex
        && required->dwMaxPayloadTransferSize >= actual->dwMaxPayloadTransferSize;
}
```

两个关键输出值：
- **dwMaxVideoFrameSize** — 用于分配帧缓冲区大小
- **dwMaxPayloadTransferSize** — 用于选择等时传输 altsetting

---

## 7. 视频流传输核心流程

### 7.1 三步启动

```c
// 一步完成（简单场景）:
uvc_start_streaming(devh, &ctrl, callback, user_ptr, 0)
  ├── uvc_stream_open_ctrl()   // 创建流
  └── uvc_stream_start()       // 启动传输

// 分步完成（需要轮询模式或多流控制）:
uvc_stream_open_ctrl(devh, &strmh, &ctrl)
uvc_stream_start(strmh, callback, user_ptr, flags)
```

### 7.2 uvc_stream_open_ctrl() — 创建流

```
① 分配 uvc_stream_handle_t
② uvc_claim_if(VS) 声明 VS 接口
③ uvc_stream_ctrl() → COMMIT + SET_CUR → 设备切换模式
④ 分配双缓冲区: outbuf + holdbuf (每个 dwMaxVideoFrameSize 字节)
⑤ 分配元数据缓冲区: meta_outbuf + meta_holdbuf (各 4KB)
⑥ 初始化 pthread_mutex + pthread_cond
⑦ DL_APPEND 加入设备流链表
```

### 7.3 uvc_stream_start() — 启动传输

#### 判断传输类型

```c
isochronous = (interface->num_altsetting > 1);
// 等时 VS 接口有多个 altsetting（不同带宽级别）
// 批量 VS 接口只有一个默认 altsetting
```

#### 等时传输：选择 altsetting

```c
config_bytes_per_packet = ctrl->dwMaxPayloadTransferSize;

// 从低到高遍历 altsetting
for (alt_idx = 0; alt_idx < interface->num_altsetting; alt_idx++) {
    endpoint_bytes_per_packet = 计算端点最大 packet 大小;
    // wMaxPacketSize 编码: [unused:2][multiplier-1:3][size:11]
    // 实际大小 = (size & 0x07ff) * (((size >> 11) & 3) + 1)

    if (endpoint_bytes_per_packet >= config_bytes_per_packet) {
        // 找到了！
        packets_per_transfer = (max_frame + ep - 1) / ep;
        if (packets_per_transfer > 32) packets_per_transfer = 32;
        total_transfer_size = packets * ep;
        break;
    }
}

// 设置选中的 altsetting
libusb_set_interface_alt_setting(usb_devh, bInterfaceNumber, altsetting);
```

#### 分配 USB 传输

- **等时**：`libusb_fill_iso_transfer(transfer, devh, ep, buf, total_size, num_packets, callback, strmh, 5000)`
- **批量**：`libusb_fill_bulk_transfer(transfer, devh, ep, buf, dwMaxPayloadTransferSize, callback, strmh, 5000)`
- 传输数量：`LIBUVC_NUM_TRANSFER_BUFS`（Mac=20, Linux/Win=100）

#### 启动回调线程 + 提交全部传输

```c
if (cb) pthread_create(&strmh->cb_thread, NULL, _uvc_user_caller, strmh);

for (i = 0; i < LIBUVC_NUM_TRANSFER_BUFS; i++)
    libusb_submit_transfer(strmh->transfers[i]);
```

### 7.4 等时 vs 批量对比

| | 等时 (Isochronous) | 批量 (Bulk) |
|------|------|------|
| 带宽保障 | ✅ 保证 | ❌ 不保证（有空余才传） |
| 数据送达 | ❌ 不保证（丢了不重传） | ✅ 保证（丢了重传） |
| 延迟 | 低且可预测 | 不确定 |
| altsetting | 多个（不同带宽级别） | 1 个 |
| 典型用途 | 视频流 | 科学摄像头/特殊设备 |
| 接口特征 | num_altsetting > 1 | num_altsetting ≤ 1 |

---

## 8. 视频流报文协议（Payload Header）

### 8.1 Payload 结构

```
每次 USB 传输的有效载荷:
┌────────────┬─────────────┬──────────┬──────────────┐
│ bHeaderLen │ bmHeaderInfo│ 可选字段  │   图像数据    │
│   (1B)     │   (1B)      │  (变长)   │   (剩余的)    │
└────────────┴─────────────┴──────────┴──────────────┘
```

### 8.2 bmHeaderInfo 标志位

```c
#define UVC_STREAM_EOH (1 << 7)  // bit 7: End Of Header — 头部结束
#define UVC_STREAM_ERR (1 << 6)  // bit 6: Error — 数据损坏，整帧丢弃！
#define UVC_STREAM_STI (1 << 5)  // bit 5: Still Image — 静态图像触发
#define UVC_STREAM_RES (1 << 4)  // bit 4: Reserved — 保留
#define UVC_STREAM_SCR (1 << 3)  // bit 3: SCR 字段存在（6 字节）
#define UVC_STREAM_PTS (1 << 2)  // bit 2: PTS 字段存在（4 字节）
#define UVC_STREAM_EOF (1 << 1)  // bit 1: End Of Frame — 帧结束！
#define UVC_STREAM_FID (1 << 0)  // bit 0: Frame Identifier — 帧切换！
```

**三个最重要位**：FID（换帧）、EOF（帧结束）、ERR（丢弃）。

### 8.3 常见 bmHeaderInfo 组合

| hex | 含义 |
|-----|------|
| 0x82 | 帧开始包，FID=1，无 PTS/SCR |
| 0x83 | 帧开始包，FID=1，有 PTS+SCR |
| 0x81 | 中间包，FID=1 |
| 0x80 | 中间包，FID=0（另一帧） |
| 0x83 | 最后一包，FID=1，EOF=1 |
| 0xC1 | 错误包，ERR=1 → 丢弃 |

### 8.4 帧组装逻辑 (_uvc_process_payload)

```c
void _uvc_process_payload(strmh, payload, payload_len) {
    header_len = payload[0];                  // ① 读头部长度
    header_info = payload[1];                 // ② 读标志位
    data_len = payload_len - header_len;

    if (header_info & ERR) return;            // ③ 错误包 → 丢弃

    // ④ FID 翻转检测 → 帧边界
    if (fid != (header_info & 1) && got_bytes != 0) {
        _uvc_swap_buffers(strmh);            // 强制完成上一帧
    }
    strmh->fid = header_info & 1;

    // ⑤ 读可选字段 PTS / SCR
    if (header_info & PTS) pts = DW_TO_INT(payload + 2);
    if (header_info & SCR) scr = DW_TO_INT(payload + ...);

    // ⑥ 拼接数据
    memcpy(outbuf + got_bytes, payload + header_len, data_len);
    got_bytes += data_len;

    // ⑦ EOF？→ 帧完成！
    if (header_info & EOF || got_bytes == max_frame_size)
        _uvc_swap_buffers(strmh);
}
```

### 8.5 双缓冲机制 (_uvc_swap_buffers)

```c
// 原子交换两个缓冲区指针
swap(outbuf, holdbuf);
// 记录完成时间
clock_gettime(CLOCK_MONOTONIC, &capture_time_finished);
// 传递帧序号
hold_seq = seq;
// 唤醒等待者
pthread_cond_broadcast(&cb_cond);
// 准备下一帧
seq++;
got_bytes = 0;
```

### 8.6 帧边界检测的两个机制

| 机制 | 触发条件 | 用途 |
|------|----------|------|
| **FID 翻转** | `fid != new_fid && got_bytes > 0` | 检测换帧 + 容错（上帧丢 EOF） |
| **EOF 置位** | `header_info & EOF` | 正常帧结束 |

---

## 9. 帧获取与回调机制

### 9.1 两种模式

| | 回调模式 | 轮询模式 |
|------|---------|---------|
| 触发 | 有帧自动调你的函数 | 你主动查询 |
| 线程 | 独立线程 | 你的线程 |
| API | cb ≠ NULL | `uvc_stream_get_frame()` |
| 互斥 | 用了回调不能轮询 (UVC_ERROR_CALLBACK_EXISTS) | |

### 9.2 回调模式

```c
// 回调线程主循环
void *_uvc_user_caller(void *arg) {
    do {
        pthread_mutex_lock(&cb_mutex);
        while (running && last_seq == hold_seq)
            pthread_cond_wait(&cb_cond, &cb_mutex);    // 等待新帧

        if (!running) break;

        last_seq = hold_seq;
        _uvc_populate_frame(strmh);                    // 填充 frame
        pthread_mutex_unlock(&cb_mutex);

        user_cb(&strmh->frame, user_ptr);              // 调用你的回调
    } while(1);
}
```

### 9.3 轮询模式

```c
uvc_error_t uvc_stream_get_frame(strmh, &frame, timeout_us);
// timeout_us == -1: 立即返回，无帧则 NULL
// timeout_us == 0:  阻塞等待新帧
// timeout_us > 0:   最多等 N 微秒，超时返回 UVC_ERROR_TIMEOUT
```

用 `last_polled_seq` 防止同一帧被重复获取。

### 9.4 uvc_frame_t 结构

```c
typedef struct uvc_frame {
    void *data;                             // 图像数据指针
    size_t data_bytes;                      // 数据大小
    uint32_t width, height;                 // 图像尺寸
    enum uvc_frame_format frame_format;     // 像素格式
    size_t step;                            // 每行字节数（非压缩格式）
    uint32_t sequence;                      // 帧序号（递增，可能跳号）
    struct timeval capture_time;            // 开始捕获时间
    struct timespec capture_time_finished;  // 接收完成时间
    uvc_device_handle_t *source;            // 来源设备
    uint8_t library_owns_data;              // 是否由库分配内存
    void *metadata;                         // 帧附带元数据
    size_t metadata_bytes;                  // 元数据大小
} uvc_frame_t;
```

### 9.5 _uvc_populate_frame() — 从 holdbuf 到 frame

```
① 从描述符获取 width, height, frame_format
② 计算 step (YUYV=width*2, RGB=width*3, MJPEG=0)
③ 传递 sequence, capture_time
④ memcpy(holdbuf → frame->data) — 多一次拷贝，尽快释放 holdbuf 给 USB 线程
⑤ 拷贝 metadata
```

---

## 10. 流停止与资源清理

### 10.1 uvc_stream_stop() — 三步关闭

```
① running = 0   → USB 回调不再重新提交 transfer

② libusb_cancel_transfer(transfers[i]) × N
   → 每个 transfer 被取消后，回调收到 CANCELLED 状态
   → 自动 free buffer + libusb_free_transfer
   → transfer[i] = NULL
   → broadcast(cb_cond) 通知等待者

③ 等待所有 transfer 都被清理 (全为 NULL)
   → broadcast(cb_cond) 唤醒回调线程
   → 回调线程看到 running=0 → 退出循环
   → pthread_join(cb_thread) 等待线程结束
```

### 10.2 uvc_stream_close()

```c
if (running) uvc_stream_stop();     // ① 先停流
uvc_release_if(VS);                 // ② 归还 VS 接口
free(frame.data);                   // ③ 释放所有缓冲区
free(outbuf); free(holdbuf);
free(meta_outbuf); free(meta_holdbuf);
pthread_cond_destroy();             // ④ 销毁同步对象
pthread_mutex_destroy();
DL_DELETE(devh->streams, strmh);   // ⑤ 从链表移除
free(strmh);                        // ⑥ 释放句柄
```

### 10.3 完整关闭链

```
uvc_stop_streaming(devh) → 遍历关闭所有流
uvc_close(devh) → 归还VC接口 → libusb_close → 释放内存
uvc_unref_device(dev) → ref-- → 若0则free
uvc_exit(ctx) → libusb_exit → free(ctx)
```

---

## 11. 帧格式转换

### 11.1 支持的转换

| 函数 | 输入 | 输出 | 备注 |
|------|------|------|------|
| `uvc_yuyv2rgb` | YUYV | RGB | 定点数加速 |
| `uvc_yuyv2bgr` | YUYV | BGR | OpenCV 默认格式 |
| `uvc_uyvy2rgb` | UYVY | RGB | |
| `uvc_uyvy2bgr` | UYVY | BGR | |
| `uvc_yuyv2y` | YUYV | GRAY8 | 只提取亮度 |
| `uvc_yuyv2uv` | YUYV | GRAY8 | 只提取色度 |
| `uvc_mjpeg2rgb` | MJPEG | RGB | 需要 libjpeg |
| `uvc_mjpeg2gray` | MJPEG | GRAY8 | 需要 libjpeg |
| `uvc_any2rgb` | 任意 | RGB | 自动判断格式 ⭐ |
| `uvc_any2bgr` | 任意 | BGR | 自动判断格式 |
| `uvc_duplicate_frame` | 任意 | 同格式 | 帧复制 |

### 11.2 YUYV → RGB 转换原理

**YUYV 格式**：每 2 个像素共享一对 UV 色度值，4 字节描述 2 个像素。

```
[Y0][U0][Y1][V0] → 像素0: (Y0,U0,V0), 像素1: (Y1,U0,V0)
```

**转换公式**（定点数加速，乘以 2^14 后用位移代替除法和浮点乘法）：

```c
#define IYUYV2RGB_2(pyuv, prgb) {
    int r = (22987 * ((pyuv)[3] - 128)) >> 14;   // ≈ 1.402
    int g = (-5636 * ((pyuv)[1] - 128) - 11698 * ((pyuv)[3] - 128)) >> 14;
    int b = (29049 * ((pyuv)[1] - 128)) >> 14;   // ≈ 1.772
    (prgb)[0] = sat(*(pyuv) + r);
    (prgb)[1] = sat(*(pyuv) + g);
    (prgb)[2] = sat(*(pyuv) + b);
}
// 通过宏展开：2→4→8→16 → 流水线批量处理
```

### 11.3 典型用法

```c
void cb(uvc_frame_t *frame, void *ptr) {
    uvc_frame_t *bgr = uvc_allocate_frame(frame->width * frame->height * 3);
    uvc_any2bgr(frame, bgr);        // 一键转换
    // bgr->data 可直接喂给 OpenCV
    uvc_free_frame(bgr);
}
```

---

## 12. 完整调用序列

### 12.1 example.c 完整流程

```c
int main() {
    uvc_context_t *ctx;
    uvc_device_t *dev;
    uvc_device_handle_t *devh;
    uvc_stream_ctrl_t ctrl;

    // ========== 阶段1: 初始化 ==========
    uvc_init(&ctx, NULL);

    // ========== 阶段2: 发现并打开 ==========
    uvc_find_device(ctx, &dev, 0, 0, NULL);
    uvc_open(dev, &devh);

    // ========== 阶段3: 打印设备信息 ==========
    uvc_print_diag(devh, stderr);

    // ========== 阶段4: 协商流参数 ==========
    uvc_get_stream_ctrl_format_size(
        devh, &ctrl, UVC_FRAME_FORMAT_YUYV, 640, 480, 30);

    // ========== 阶段5: 启动视频流 ==========
    uvc_start_streaming(devh, &ctrl, cb, (void*)12345, 0);

    // ========== 阶段6: 运行时控制 ==========
    uvc_set_ae_mode(devh, UVC_AUTO_EXPOSURE_MODE_AUTO);

    sleep(10);  // 这期间 cb() 被反复调用

    // ========== 阶段7: 停止并清理 ==========
    uvc_stop_streaming(devh);
    uvc_close(devh);
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 0;
}

// ========== 回调: 每帧调用 ==========
void cb(uvc_frame_t *frame, void *ptr) {
    uvc_frame_t *bgr = uvc_allocate_frame(frame->width * frame->height * 3);
    uvc_any2bgr(frame, bgr);
    // 处理 bgr->data...
    uvc_free_frame(bgr);
}
```

### 12.2 完整架构图

```
main()
 ├─ uvc_init()                          上下文创建
 ├─ uvc_find_device()                   设备发现
 ├─ uvc_open()                          设备打开 + 描述符解析
 │    └─ uvc_get_device_info() → 解析描述符树
 │
 ├─ uvc_get_stream_ctrl_format_size()   格式选择 + 流协商
 │    └─ uvc_probe_stream_ctrl() → Probe SET → Probe GET
 │
 ├─ uvc_start_streaming()              启动视频流
 │    ├─ uvc_stream_open_ctrl() → Commit 流参数
 │    └─ uvc_stream_start()
 │         ├─ 选 altsetting
 │         ├─ 分配 20~100 个 USB transfer
 │         ├─ libusb_submit_transfer × N
 │         └─ 启动回调线程
 │
 ├─ uvc_set_ae_mode()                   运行时控制
 │
 │    ╔══════════════════════════════════╗
 │    ║  USB 数据到达 → callback         ║
 │    ║    _uvc_stream_callback()        ║
 │    ║      └─ _uvc_process_payload()  ║
 │    ║           ├─ 解析 Header          ║
 │    ║           ├─ memcpy → outbuf    ║
 │    ║           └─ EOF → swap_buf()   ║
 │    ║                └─ signal         ║
 │    ║                                  ║
 │    ║    _uvc_user_caller() 线程      ║
 │    ║      └─ _uvc_populate_frame()   ║
 │    ║           └─ cb(frame, ptr)     ║
 │    ║                └─ uvc_any2bgr() ║
 │    ╚══════════════════════════════════╝
 │
 ├─ uvc_stop_streaming()               停止流
 │    └─ cancel transfer → join thread → free
 │
 ├─ uvc_close()                         关闭设备
 ├─ uvc_unref_device()
 └─ uvc_exit()
```

---

## 13. XU 扩展单元与厂商自定义控制

### 13.1 标准控制 vs XU 对比

| | CT / PU 标准控制 | XU 扩展控制 |
|------|------|------|
| 控制选择器 | UVC 规范定死 | 厂商自定 (1~255) |
| 目标单元 | CT 的 bTerminalID 或 PU 的 bUnitID | XU 的 bUnitID（通过 GUID 查找） |
| API | 高层封装 (uvc_set_brightness...) | 底层 API (uvc_set_ctrl...) |
| 可移植性 | 任何 UVC 摄像头 | 仅特定厂商型号 |

### 13.2 XU 寻址方式

```c
// 步骤1：按 GUID 找到 XU 的 bUnitID
const uvc_extension_unit_t *eu;
DL_FOREACH(devh->info->ctrl_if.extension_unit_descs, eu) {
    if (memcmp(eu->guidExtensionCode, target_guid, 16) == 0) {
        xu_id = eu->bUnitID;  // ← 目标单元
        break;
    }
}

// 步骤2：发控制命令
uvc_set_ctrl(devh, xu_id, control_selector, data, len);
//               ↑        ↑
//          目标单元   控制选择器（厂商定义）
```

### 13.3 wValue 的三种编码方式

```
方案 A：标准 UVC
  wValue = Control_Selector << 8 | 0x00
  例: 0x0200 → 亮度控制

方案 B：二级结构 (Sensor + Function)
  wValue = CSID << 8 | Function_ID
  例: 0x0001 → Sensor0 的曝光, 0x0101 → Sensor1 的曝光

方案 C：三级结构 (Category + SubFunc + data[])
  一级 wValue 高字节 = Category（功能大类）
  二级 wValue 低字节 = SubFunc（子功能）
  三级 data 区      = 具体参数（坐标/速度/颜色/字符串...）
  例: 0x0901 + data[速度][角度] → 云台横向移动
```

### 13.4 三级封装示例

```c
// 车载全景摄像头 XU 巡航控制
#define CAT_PANTILT    0x09
#define SUB_PAN_LEFT   0x01
#define SUB_TILT_UP    0x03
#define SUB_HOME       0x05

uvc_error_t pantilt_move(devh, xu_id, uint8_t direction, uint8_t speed) {
    uint16_t wValue = (CAT_PANTILT << 8) | direction;  // 一级+二级
    uint8_t data[1] = {speed};                          // 三级参数
    return libusb_control_transfer(
        devh->usb_devh, 0x21, UVC_SET_CUR, wValue,
        xu_id << 8 | interface, data, 1, 0);
}
```

---

## 14. Payload 组帧与异常恢复

### 14.1 为什么不需要包序号

USB 是主从架构总线，点到点直连，不经过路由交换。数据严格按设备发送顺序到达主机。组帧只需两个标记：

| 标记 | 作用 |
|------|------|
| **FID** | 翻转表示换帧 → "新帧从这里开始" |
| **EOF** | 置位表示帧结束 → "这一帧到此结束" |

**`got_bytes`（outbuf 写入偏移）就是隐式的"包序号"**——它记录了当前帧已经拼接了多少字节。

### 14.2 正常组帧过程

```
收到包1: FID=1, EOF=0 → memcpy(outbuf+0, data, 49140)    got_bytes=49140
收到包2: FID=1, EOF=0 → memcpy(outbuf+49140, data, 49150) got_bytes=98290
...
收到包N: FID=1, EOF=1 → memcpy(outbuf+..., data, ...)     EOF→swap_buffers! got_bytes归零
收到包M: FID=0        → 翻转+got_bytes=0 → 新帧正常开始
```

### 14.3 异常恢复

#### 情况1：EOF 包丢失

```
FID=1, FID=1, [EOF包丢了!] → FID=0 来了 → 翻转+got_bytes>0 → 强制swap → 不完整帧
→ got_bytes=0 → 帧N+1开始 → 自动恢复
代价：丢 1 帧
```

#### 情况2：FID 毛刺（线路干扰）

```
FID=1, FID=1, FID=0(!毛刺), FID=1(EOF) → 
  毛刺触发强制swap（不完整）→ 之后正常包触发强制swap（乱数据）→ 再之后恢复
代价：丢 2~3 帧，自动恢复
```

#### 情况3：ERR 包

```
收到 ERR=1 → 直接丢弃该包 → 继续等待后续包
结果：该帧有数据空洞，整帧损坏
```

### 14.4 增强：帧头魔数

设备端在每帧数据前加魔数做二次校验：

```c
// 设备端：每帧前 4 字节写 0xDEADBEEF
// 客户端：
void cb(uvc_frame_t *frame, void *ptr) {
    if (frame->data_bytes < 4 || *(uint32_t*)frame->data != 0xDEADBEEF) {
        return;  // 对齐错误，丢帧
    }
    uint8_t *image = frame->data + 4;   // 跳过魔数
    size_t image_size = frame->data_bytes - 4;
}
```

### 14.5 码流传输文件的设计模式

利用 UVC 视频流通道传输配置文件，利用 metadata 或帧序号区分"文件帧"和"图像帧"：

```
方案一（推荐）：metadata 标记帧类型
  设备: header 中 metadata = [0xFF=文件帧, 文件ID, 偏移, is_last]
  客户端: 检查 frame->metadata → 分流处理

方案二：帧序号窗口
  协议约定前 N 帧 = 文件数据

方案三：格式切换
  文件帧用自定义 GUID 格式 → 传完切回 YUYV
```

---

## 15. 附录：源码文件速查

### 15.1 关键函数索引

| 函数 | 文件 | 功能 |
|------|------|------|
| `uvc_init` | init.c:104 | 创建 UVC 上下文 |
| `uvc_exit` | init.c:138 | 销毁 UVC 上下文 |
| `uvc_get_device_list` | device.c:679 | 枚举所有 UVC 设备 |
| `uvc_find_device` | device.c:128 | 按 VID/PID/SN 查找设备 |
| `uvc_open` | device.c:316 | 打开设备 |
| `uvc_close` | device.c:1722 | 关闭设备 |
| `uvc_scan_control` | device.c:1049 | 解析 VC 描述符 |
| `uvc_scan_streaming` | device.c:1319 | 解析 VS 描述符 |
| `uvc_parse_vc` | device.c:1273 | VC 描述符分发 |
| `uvc_parse_vs` | device.c:1635 | VS 描述符分发 |
| `uvc_get_ctrl` | ctrl.c:90 | 通用读控制 |
| `uvc_set_ctrl` | ctrl.c:113 | 通用写控制 |
| `uvc_get_ctrl_len` | ctrl.c:59 | 查询控制长度 |
| `uvc_query_stream_ctrl` | stream.c:194 | Probe/Commit 底层 |
| `uvc_probe_stream_ctrl` | stream.c:609 | 流参数协商 |
| `uvc_get_stream_ctrl_format_size` | stream.c:470 | 按格式/分辨率/帧率协商 |
| `uvc_stream_open_ctrl` | stream.c:1005 | 创建视频流 |
| `uvc_stream_start` | stream.c:1075 | 启动视频流 |
| `uvc_stream_stop` | stream.c:1492 | 停止视频流 |
| `uvc_stream_close` | stream.c:1542 | 关闭视频流 |
| `uvc_stream_get_frame` | stream.c:1397 | 轮询获取帧 |
| `_uvc_stream_callback` | stream.c:805 | USB 传输回调 |
| `_uvc_process_payload` | stream.c:699 | Payload 解析与组帧 |
| `_uvc_swap_buffers` | stream.c:657 | 双缓冲交换 |
| `_uvc_user_caller` | stream.c:1296 | 回调线程主循环 |
| `_uvc_populate_frame` | stream.c:1328 | 填充 uvc_frame_t |
| `uvc_allocate_frame` | frame.c:64 | 分配帧结构 |
| `uvc_free_frame` | frame.c:92 | 释放帧结构 |
| `uvc_any2rgb` | frame.c:441 | 任意格式→RGB |
| `uvc_any2bgr` | frame.c:464 | 任意格式→BGR |
| `uvc_yuyv2rgb` | frame.c:174 | YUYV→RGB |
| `uvc_yuyv2bgr` | frame.c:225 | YUYV→BGR |
| `uvc_perror` | diag.c | 打印错误信息 |
| `uvc_print_diag` | diag.c | 打印设备诊断信息 |

### 15.2 关键常量

| 常量 | 位置 | 值 | 含义 |
|------|------|-----|------|
| `USB_CLASS_VIDEO` | — | 14 | UVC 设备类 |
| `UVC_SC_VIDEOCONTROL` | libuvc_internal.h:80 | 1 | VC 子类 |
| `UVC_SC_VIDEOSTREAMING` | libuvc_internal.h:81 | 2 | VS 子类 |
| `REQ_TYPE_SET` | ctrl.c:45 | 0x21 | Host→Device, Class, Interface |
| `REQ_TYPE_GET` | ctrl.c:46 | 0xA1 | Device→Host, Class, Interface |
| `UVC_VS_PROBE_CONTROL` | libuvc_internal.h:135 | 1 | Probe 控制选择器 |
| `UVC_VS_COMMIT_CONTROL` | libuvc_internal.h:136 | 2 | Commit 控制选择器 |
| `LIBUVC_NUM_TRANSFER_BUFS` | libuvc_internal.h:228-231 | 20(Mac) / 100(Linux) | 传输缓冲区数量 |
| `LIBUVC_XFER_META_BUF_SIZE` | libuvc_internal.h:234 | 4096 | 元数据缓冲区大小 |

### 15.3 关键宏

| 宏 | 作用 |
|-----|------|
| `SW_TO_SHORT(p)` | 2 字节小端序列化：`(p)[0]\|((p)[1]<<8)` |
| `SHORT_TO_SW(s, p)` | 逆序列化 |
| `DW_TO_INT(p)` | 4 字节小端序列化 |
| `INT_TO_DW(i, p)` | 逆序列化 |
| `DL_APPEND` | 双向链表追加 |
| `DL_FOREACH` | 双向链表遍历 |
| `DL_FOREACH_SAFE` | 双向链表安全遍历（可删除） |
| `DL_DELETE` | 从双向链表删除 |

---

> 📝 本笔记基于 libuvc v0.0.7 源码 + UVC 1.0/1.1/1.5 规范，覆盖 12 个学习阶段及扩展专题。
