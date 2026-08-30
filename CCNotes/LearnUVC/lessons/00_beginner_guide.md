# 00 · libuvc 接口全景入门（从零开始）

> 本文是第一课：不逐个讲接口，先建立全局地图。
> 学完本文你会知道：libuvc 是干什么的、一共哪几类接口、它们如何串成一条主干流程。

---

## 1. 为什么会有 libuvc？

### 1.1 背景：USB 摄像头为什么"插上就能用"

普通 U 盘、鼠标插上电脑需要装驱动，但 USB 摄像头插上就能用，原因是它遵循一个**公开的标准协议**：

> **UVC = USB Video Device Class（USB 视频设备类规范）**

规范规定：摄像头不需要厂商专属驱动，只要操作系统内置一个通用 UVC 驱动（Windows 上是 usbvideo.sys），就能让任何 UVC 摄像头工作。

但**系统驱动只做"能出图"这一件事**，不会给你：
- 直接控制曝光/对焦/白平衡的底层通道
- 拿到原始帧数据的自由（DirectShow/MediaFoundation 层层封装）
- 跨平台一致的访问方式

这时候就需要一个**给开发者用的库**直接跟摄像头说话，这就是 libuvc。

### 1.2 libuvc 与 libusb 的关系（类比）

| 层 | 类比 | 干什么 |
|----|------|--------|
| USB 总线 | 电话线 | 物理层，传递电信号 |
| libusb | 电话接线员 | 帮你在总线上找到设备、收发原始字节，但**不懂摄像头行话** |
| libuvc | 懂行话的业务员 | 站在 libusb 肩上，会解析摄像头的"自述文件"（描述符）、会按 UVC 协议谈判和收发视频 |

一句话：**libuvc 是 libusb 的薄封装 + UVC 协议翻译器**。它做的事只有三件：

1. **解析描述符** — 读懂摄像头自述"我支持什么格式、什么控制"
2. **封装控制传输** — 把"设置亮度"翻译成 USB 控制包发出去
3. **管理等时/批量传输** — 把视频流一帧一帧收回来

---

## 2. 最重要的一张图：主干调用链

libuvc 全部接口可以串成一条**主干**（生命周期流程）加两条**分线**（控制、数据）。

```
 ① uvc_init               领一张"工作台"（context）
 ② uvc_find_device         在总线上找到摄像头（拿"名片"）
 ③ uvc_open                打开设备，拿"控制台"（devh），内部读完自述文件
 ④ uvc_get_format_descs    问：支持哪些格式/分辨率/帧率（看菜单）
 ⑤ uvc_get_stream_ctrl_format_size  和摄像头"谈判"出一份合同（ctrl）
 ⑥ uvc_stream_open_ctrl    按合同建一根"水管"（strmh）
 ⑦ uvc_stream_start        开闸放水，视频数据开始流入
 ⑧ uvc_stream_get_frame    一帧一帧接图像（uvc_frame_t）
 ⑨ uvc_stream_stop / uvc_stream_close   关闸、拆水管
 ⑩ uvc_close               关闭设备，还"控制台"
 ⑪ uvc_exit                还"工作台"
```

这就是 libuvc 官方示例 example.c 的真实调用顺序，**任何 libuvc 程序都是这条链的变体**。

### 2.1 主干每步：做什么 / 拿到什么 / 为什么是这个顺序

| 步骤 | 接口 | 这一步做什么 | 拿到什么数据 | 为什么必须按这个顺序 |
|------|------|-------------|-------------|---------------------|
| ① | `uvc_init` | 创建全局上下文 | `uvc_context_t*` 工作台 | 一切的总管家；没有它后面所有函数都无处登记 |
| ② | `uvc_find_device` | 按 VID/PID/序列号在总线上找设备 | `uvc_device_t*` 设备名片 | 不开门先认门；名片只是"地址"，还没接触设备 |
| ③ | `uvc_open` | 打开设备，**一次性解析全部描述符** | `uvc_device_handle_t*` 控制台 | 只有读懂了自述文件，才知道能谈什么、能要什么 |
| ④ | `uvc_get_format_descs` | 读出设备支持的格式列表 | `uvc_format_desc_t*` 链表（格式/分辨率/帧率"菜单"） | 谈判之前先看菜单，否则可能提出设备不支持的格式 |
| ⑤ | `uvc_get_stream_ctrl_format_size` | 按你选的格式+分辨率+帧率去谈判 | `uvc_stream_ctrl_t` 合同 | 水管口径必须双方确认，不能单方面拍板 |
| ⑥ | `uvc_stream_open_ctrl` | 按合同创建流 | `uvc_stream_handle_t*` 水管 | 水管按合同口径铺设 |
| ⑦ | `uvc_stream_start` | 启动数据传输 | 无（数据开始持续流入） | 不开闸没水；开了闸设备才真正开始发视频包 |
| ⑧ | `uvc_stream_get_frame` | 从水管取出一帧 | `uvc_frame_t*` 图像数据（像素指针+宽高+格式+时间戳） | 核心目的：拿到图像本体 |
| ⑨ | `uvc_stream_stop/close` | 停止并拆除流 | 无 | 不关闸会一直占带宽；拆了水管才能安全关设备 |
| ⑩ | `uvc_close` | 关闭设备 | 无 | 释放设备占用，别人（别的程序）才能用 |
| ⑪ | `uvc_exit` | 释放全局上下文 | 无 | 退出程序前清理全局资源 |

> **坑**：③ 必须在 ④⑤ 之前，因为描述符在 `uvc_open` 时才解析；⑨ 必须在 ⑩ 之前，流开着就关设备会出问题。顺序不能跳。

---

## 3. 四件套对象模型：接口之间的"血缘关系"

主干链上每个接口的输出，都是下一个接口的输入。把它们抽象成四个对象，全部接口就都挂在它们下面：

```
uvc_init ────────────▶ uvc_context_t          （工作台）
uvc_find_device ─────▶ uvc_device_t           （设备名片）
uvc_open ────────────▶ uvc_device_handle_t    （控制台）
uvc_stream_open_ctrl─▶ uvc_stream_handle_t    （水管）
uvc_stream_get_frame─▶ uvc_frame_t            （一帧图像数据）
```

| 对象 | 类比 | 由谁创建 | 传给谁用 | 生命周期 |
|------|------|---------|---------|---------|
| `uvc_context_t` | 工作台 | `uvc_init` | 整个程序 | init 到 exit |
| `uvc_device_t` | 设备名片 | `uvc_get_device_list` / `uvc_find_device` | `uvc_open` | 打开前；有引用计数 |
| `uvc_device_handle_t` | 控制台（已开门） | `uvc_open` | 一切控制和流接口 | open 到 close |
| `uvc_stream_handle_t` | 水管 | `uvc_stream_open_ctrl` | `uvc_stream_start/get_frame/stop/close` | 建流到拆流 |
| `uvc_frame_t` | 一帧图像 | `uvc_stream_get_frame` | 你的处理代码 | 单帧；用完要释放 |

**规律**：指针类型就是接口的"接线图"——看一个接口的参数里出现哪个对象指针，就知道它属于哪个阶段、该在何时调用。

---

## 4. 两条分线：控制线（遥控器）与数据线（水管）

主干之外，所有接口分成两大类，对应 UVC 设备的两个接口：

| 分线 | UVC 接口 | 类比 | 典型接口 | 特点 |
|------|----------|------|---------|------|
| **控制线** | VC 接口（VideoControl） | 遥控器 | `uvc_get_ctrl` / `uvc_set_ctrl` / `uvc_set_brightness` / `uvc_set_ae_mode`… | 请求-应答式；随时可用（③打开后即可，流开着时也能用） |
| **数据线** | VS 接口（VideoStreaming） | 水管 | `uvc_stream_*` 全家 | 持续单向流动；必须按 ⑤协商→⑥建流→⑦启动 的顺序 |

**配合关系要点**：
- 控制线**不依赖**数据线：没开流也能调曝光、问能力。
- 数据线**依赖**控制线打前站：协商（⑤）本身走的就是控制传输。
- 两条线在 ③ `uvc_open` 之后都可用，互不阻塞——这就是"流中调亮度"能成立的原因。

---

## 5. 全部接口分组总览（先混个脸熟，不深究）

libuvc v0.0.7 约 110 个公开接口，按用途分 8 组：

| 组 | 数量 | 代表接口 | 一句话作用 |
|----|------|---------|-----------|
| ① 生命周期 | ~11 | `uvc_init` / `uvc_open` / `uvc_close` / `uvc_exit` | 创建和销毁上面四件套 |
| ② 设备信息 | ~8 | `uvc_get_device_descriptor` / `uvc_get_bus_number` / `uvc_ref_device` | 问设备"你是谁、在哪" |
| ③ 事件回调 | 2 | `uvc_set_status_callback` / `uvc_set_button_callback` | 设备状态变化时通知你 |
| ④ 描述符查询 | 7 | `uvc_get_camera_terminal` / `uvc_get_processing_units` / `uvc_get_format_descs` | 查自述文件：支持什么功能、什么格式 |
| ⑤ 流协商 | 4 | `uvc_get_stream_ctrl_format_size` / `uvc_probe_stream_ctrl` | 和摄像头谈判出合同 |
| ⑥ 流管理 | 11 | `uvc_stream_open_ctrl` / `uvc_stream_start` / `uvc_stream_get_frame` / `uvc_stream_stop` | 水管的全套操作 |
| ⑦ 控制接口 | ~40 | `uvc_get_ctrl` / `uvc_set_ctrl` + 35 对 get/set（亮度/曝光/对焦/白平衡…） | 遥控器：读参数、改参数 |
| ⑧ 帧处理 | ~15 | `uvc_any2rgb` / `uvc_duplicate_frame` / `uvc_allocate_frame` | 对拿到的图像数据做转换和复制 |
| ⑨ 诊断 | 4 | `uvc_strerror` / `uvc_perror` / `uvc_print_diag` / `uvc_print_stream_ctrl` | 错误转文字、打印设备和流信息 |

**控制接口那一组占了大头**（40 个），但它们全是同一个模板生成的 get/set 对——学会一对就全会了（Phase 8/9 会讲）。

---

## 6. 两个绕不开的核心数据类型（提前认识）

| 类型 | 类比 | 关键字段 | 在哪个阶段出现 |
|------|------|---------|---------------|
| `uvc_stream_ctrl_t` | 流合同 | 格式编号、帧索引、帧间隔、**dwMaxVideoFrameSize**（一帧多大）、**dwMaxPayloadTransferSize**（每包多大） | ⑤ 协商产出，⑥ 建流输入 |
| `uvc_frame_t` | 一帧图像 | **data**（像素数据指针）、data_bytes、width、height、frame_format、step、sequence、capture_time、metadata | ⑧ 输出，⑧ 帧处理输入 |

记住两个直觉：
- **合同（ctrl）决定水管怎么铺**——帧大小、每包大小都是谈判出来的，不是猜的。
- **帧（frame）就是最终目的**——前面 7 步全部是为了让 ⑧ 能持续吐出一帧帧 `uvc_frame_t`。

---

## 7. 学习路线

按主干顺序学，控制线和数据线穿插：

```
Phase 1  初始化与退出        （① + 诊断函数）
Phase 2  设备发现            （② + 设备信息组）
Phase 3  打开与关闭          （③ + 事件回调组）
Phase 4  能力查询            （④ 描述符查询组）
Phase 5  流协商              （⑤ + 合同逐字段）
Phase 6  流生命周期          （⑥⑦⑨ 水管操作）
Phase 7  帧获取              （⑧ + 帧逐字段）
Phase 8  通用控制底层        （控制线底座：get_ctrl/set_ctrl）
Phase 9  高层相机控制族      （35+ 对 get/set 全览）
Phase 10 帧格式转换          （⑧ 帧处理组）
Phase 11 综合实战            （完整程序真实运行 + API 速查表定稿）
```

每个 Phase 都是一份文档：**接口表格（作用/拿到什么数据）→ 原理 → 坑 → 真实运行示例**（用你机器上的 ACER 内置摄像头实测）。

---

## 8. 与旧笔记的关系

本仓库根目录的 `libuvc-knowledge-notes.md` 是 2026-07-11 完成的**源码内部机制**笔记（12 阶段：描述符解析状态机、Payload Header 组帧、双缓冲线程模型等）。

- **本系列** = 接口使用层：怎么调用、拿到什么、怎么配合
- **旧笔记** = 内部原理层：接口背后发生了什么

本系列各 Phase 会在"原理"小节引用旧笔记对应章节，供想深入时查阅。
