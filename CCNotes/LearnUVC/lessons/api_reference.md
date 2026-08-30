# libuvc v0.0.7 全部接口速查表

> 日常开发查这张表。按用途分 9 组，每组内按调用顺序排列。
> 列含义：**签名**（简写）、**作用**、**拿到/设置什么数据**、**配合关系**（先谁后谁）、**讲解 Phase**。

---

## 0. 主干链十一步（先背这个）

```
 1 uvc_init                     领工作台 uvc_context_t
 2 uvc_find_device              拿名片 uvc_device_t
 3 uvc_open                     拿控制台 uvc_device_handle_t（内部读完全部描述符）
 4 uvc_get_format_descs         看菜单：格式/分辨率/帧率
 5 uvc_get_stream_ctrl_format_size  谈判出合同 uvc_stream_ctrl_t
 6 uvc_stream_open_ctrl         按合同建水管 uvc_stream_handle_t（合同在此 Commit）
 7 uvc_stream_start             开闸（回调模式传 cb，轮询模式传 NULL）
 8 uvc_stream_get_frame         拿帧 uvc_frame_t ★最终目的
 9 uvc_stream_stop / uvc_stream_close   关闸/拆管
10 uvc_close                    关设备
11 uvc_exit                     还工作台
```

---

## 1. 生命周期组（Phase 1）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_init(uvc_context_t **ctx, libusb_context *usb_ctx)` | 创建上下文 | `*ctx` = 工作台（内含 libusb 上下文） | 一切的第一步；usb_ctx 一般传 NULL |
| `uvc_exit(uvc_context_t *ctx)` | 释放上下文 | 无（自动关掉所有开着的设备） | 一切的最后一步；之后所有指针作废 |

## 2. 设备发现组（Phase 2）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_get_device_list(ctx, uvc_device_t ***list)` | 枚举全部 UVC 设备 | NULL 结尾的设备数组 | 靠系统花名册，无需打开 |
| `uvc_free_device_list(list, unref)` | 释放列表 | 无 | 与 get_device_list 配对；unref=1 |
| `uvc_get_device_descriptor(dev, uvc_device_descriptor_t **desc)` | 读名片 | VID/PID/序列号/厂家/产品名（后三者可能 NULL） | 无需打开；desc 用完要 free |
| `uvc_free_device_descriptor(desc)` | 释放名片 | 无 | 配对释放 |
| `uvc_get_bus_number(dev)` | 总线号 | `uint8_t` | 调试定位 |
| `uvc_get_device_address(dev)` | 设备地址 | `uint8_t` | 调试定位 |
| `uvc_find_device(ctx, &dev, vid, pid, sn)` | 按条件找一台（0/NULL=通配） | `*dev`；找不到返回 `NO_DEVICE(-4)` | 内部 = 枚举+过滤 |
| `uvc_find_devices(ctx, &devs, vid, pid, sn)` | 按条件找全部 | NULL 结尾数组（free + 逐个 unref） | 同上，多台版 |
| `uvc_ref_device(dev)` / `uvc_unref_device(dev)` | 引用计数 ±1 | 无 | unref 到 0 释放结构 |

## 3. 打开与关闭组（Phase 3）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_open(dev, uvc_device_handle_t **devh)` | 打开设备 | `*devh` = 控制台（描述符树在此解析） | 先于 4~9 组一切接口；Windows 内置摄像头报 NOT_SUPPORTED（D1） |
| `uvc_close(devh)` | 关闭设备 | 无（自动停流） | 之后 devh 及派生全作废 |
| `uvc_wrap(sys_dev, ctx, &devh)` | 系统句柄直接包装 | `*devh` | 替代 find+open；Linux 专用居多 |
| `uvc_get_device(devh)` | devh → dev（自动 ref） | `uvc_device_t *` | 用完 unref |
| `uvc_get_libusb_handle(devh)` | 拿 libusb 底层句柄 | `libusb_device_handle *` | 访问同设备其他接口（如麦克风） |
| `uvc_set_status_callback(devh, cb, ptr)` | 注册状态变化回调 | 回调收到 class/selector/attribute/新值 | 需设备有中断端点 |
| `uvc_set_button_callback(devh, cb, ptr)` | 注册按钮事件回调 | 回调收到 button/state | 同上 |

## 4. 能力查询组（Phase 4）——全部零 USB 通信，读 open 时的缓存

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_print_diag(devh, FILE*)` | 一键打印全部配置 | 直接输出到流 | 调试三板斧第一斧 |
| `uvc_get_format_descs(devh)` | 格式菜单链表头 | `uvc_format_desc_t`（格式→帧两级链表） | 谈判前看菜单 |
| `uvc_get_camera_terminal(devh)` | 找 Camera Terminal | `uvc_input_terminal_t`（bmControls 位图） | 可能 NULL |
| `uvc_get_input_terminals(devh)` | 全部输入端子 | 链表头 | 遍历用 ->next |
| `uvc_get_processing_units(devh)` | 全部 PU | `uvc_processing_unit_t`（bUnitID/bmControls） | Phase 8/9 寻址用 |
| `uvc_get_extension_units(devh)` | 全部 XU | `uvc_extension_unit_t`（bUnitID/GUID/bmControls） | 厂商自定义功能入口 |
| `uvc_get_selector_units(devh)` | 全部选择器单元 | `uvc_selector_unit_t` | 多输入设备 |
| `uvc_get_output_terminals(devh)` | 输出端子 | **恒 NULL（v0.0.7 未实现）** | 别依赖 |

## 5. 流协商组（Phase 5）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_get_stream_ctrl_format_size(devh, &ctrl, fmt, w, h, fps)` | 一步谈判 | `ctrl` = 合同（核心：dwMaxVideoFrameSize / dwMaxPayloadTransferSize） | 输入是 Phase 4 菜单；输出喂 open_ctrl；失败 INVALID_MODE |
| `uvc_probe_stream_ctrl(devh, &ctrl)` | 手工 Probe（问） | 设备回填后的 ctrl | 一般不直接用 |
| `uvc_stream_ctrl(strmh, &ctrl)` | Commit（定） | 无（写入流句柄） | 在 open_ctrl 内自动调用 |
| `uvc_get_still_ctrl_format_size(devh, &ctrl, &still, w, h)` | 静态图谈判 | `uvc_still_ctrl_t` | 仅 method-2 设备 |
| `uvc_probe_still_ctrl(devh, &still)` | 静态图 Probe（**内部直接 Commit**） | 回填的 still_ctrl | 同上 |
| `uvc_trigger_still(devh, &still)` | 触发静态拍照 | 无 | 需流已在跑 |
| `uvc_print_stream_ctrl(&ctrl, FILE*)` | 打印合同 | 输出到流 | 谈判后核对 |

## 6. 流管理组（Phase 6/7）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_stream_open_ctrl(devh, &strmh, &ctrl)` | 建流（claim VS 接口 + Commit + 分配双缓冲） | `*strmh` = 水管 | 输入 Phase 5 合同；同接口重复建流 BUSY |
| `uvc_stream_start(strmh, cb, ptr, flags)` | 开闸 | 无（数据开始流入） | cb 非 NULL=回调模式；NULL=轮询模式；flags 传 0 |
| `uvc_stream_start_iso(...)` | 同 start | — | **已废弃**，直接调 start |
| `uvc_stream_get_frame(strmh, &frame, timeout_us)` | 轮询取一帧 | `*frame` = 新帧（无新帧=NULL）；超时 TIMEOUT(-7) | 仅轮询模式；帧是复用缓冲 |
| `uvc_stream_stop(strmh)` | 关闸（cancel+等待+join，阻塞） | 无 | 在 close 前 |
| `uvc_stream_close(strmh)` | 拆管（释放接口与缓冲） | 无 | 之后 strmh 作废 |
| `uvc_start_streaming(devh, &ctrl, cb, ptr, flags)` | **快捷组合**：open_ctrl+start | 无 | 内部等价，start 失败自动 close |
| `uvc_start_iso_streaming(...)` | 同上 | — | **已废弃** |
| `uvc_stop_streaming(devh)` | 停该设备全部流 | 无 | 与 start_streaming 配对 |

## 7. 控制组——通用底层（Phase 8）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_get_ctrl_len(devh, unit, ctrl)` | 问控制数据长度 | `int` 长度（负数=不支持） | unit 来自 Phase 4 getter |
| `uvc_get_ctrl(devh, unit, ctrl, buf, len, req_code)` | 万能读 | 缓冲被填充，返回字节数 | req_code ∈ GET_CUR/MIN/MAX/RES/LEN/INFO/DEF |
| `uvc_set_ctrl(devh, unit, ctrl, buf, len)` | 万能写（SET_CUR） | 发送字节数 | XU 控制的唯一通道 |
| `uvc_get_power_mode(devh, &mode, req_code)` | 读电源模式 | FULL(0x0b) / DEVICE_DEPENDENT(0x1b) | 接口级控制（wIndex 无 unit） |
| `uvc_set_power_mode(devh, mode)` | 设电源模式 | 无 | 同上 |

## 8. 控制组——高层 35 对（Phase 9）

> get 版本统一多一个 `req_code` 参数；set 版本固定 SET_CUR。CT 系寻址 camera terminal，PU 系寻址第一个 PU。全部返回 `UVC_SUCCESS` 或错误（不支持=PIPE）。

| 接口对 | 数据（get 输出 / set 输入） | 单位/取值 |
|--------|--------------------------|-----------|
| `uvc_get/set_scanning_mode` | `uint8_t` | 0=隔行 1=逐行 |
| `uvc_get/set_ae_mode` | `uint8_t` | 1=手动 2=自动 4=快门优先 8=光圈优先 |
| `uvc_get/set_ae_priority` | `uint8_t` | 0=帧率恒定 1=帧率可变 |
| `uvc_get/set_exposure_abs` | `uint32_t` | **0.1ms** |
| `uvc_get/set_exposure_rel` | `int8_t` | EV 步 |
| `uvc_get/set_focus_abs` | `uint16_t` | 0~65535 |
| `uvc_get/set_focus_rel` | `int8_t, uint8_t` | 方向, 速度 |
| `uvc_get/set_focus_simple_range` | `uint8_t` | 0=全 1=近 2=远 3=微距 |
| `uvc_get/set_focus_auto` | `uint8_t` | 0=关 1=开 |
| `uvc_get/set_iris_abs` | `uint16_t` | F×100 |
| `uvc_get/set_iris_rel` | `uint8_t` | 开合方向 |
| `uvc_get/set_zoom_abs` | `uint16_t` | 焦距 mm |
| `uvc_get/set_zoom_rel` | `int8_t, uint8_t, uint8_t` | 方向, 数字变焦, 速度 |
| `uvc_get/set_pantilt_abs` | `int32_t, int32_t` | **0.0001°**（pan, tilt） |
| `uvc_get/set_pantilt_rel` | `int8_t,uint8_t,int8_t,uint8_t` | 方向×2, 速度×2 |
| `uvc_get/set_roll_abs` | `int16_t` | 0.01° |
| `uvc_get/set_roll_rel` | `int8_t, uint8_t` | 方向, 速度 |
| `uvc_get/set_privacy` | `uint8_t` | 0=关 1=开 |
| `uvc_get/set_digital_window` | `uint16_t`×6 | 上/左/下/右/步数/步进单位 |
| `uvc_get/set_digital_roi` | `uint16_t`×5 | 上/左/下/右/自动标志 |
| `uvc_get/set_backlight_compensation` | `uint16_t` | 背光补偿 |
| `uvc_get/set_brightness` | `int16_t` | **有符号**，先问 MIN/MAX |
| `uvc_get/set_contrast` | `uint16_t` | |
| `uvc_get/set_contrast_auto` | `uint8_t` | 0/1 |
| `uvc_get/set_gain` | `uint16_t` | |
| `uvc_get/set_power_line_frequency` | `uint8_t` | 0=关 1=50Hz 2=60Hz |
| `uvc_get/set_hue` | `int16_t` | 度（有符号） |
| `uvc_get/set_hue_auto` | `uint8_t` | 0/1 |
| `uvc_get/set_saturation` | `uint16_t` | |
| `uvc_get/set_sharpness` | `uint16_t` | |
| `uvc_get/set_gamma` | `uint16_t` | |
| `uvc_get/set_white_balance_temperature` | `uint16_t` | K |
| `uvc_get/set_white_balance_temperature_auto` | `uint8_t` | 0/1 |
| `uvc_get/set_white_balance_component` | `uint16_t, uint16_t` | 蓝, 红 |
| `uvc_get/set_white_balance_component_auto` | `uint8_t` | 0/1 |
| `uvc_get/set_digital_multiplier` | `uint16_t` | 步进值 |
| `uvc_get/set_digital_multiplier_limit` | `uint16_t` | 步进值 |
| `uvc_get/set_analog_video_standard` | `uint8_t` | PAL/NTSC/… |
| `uvc_get/set_analog_video_lock_status` | `uint8_t` | 锁定状态 |
| `uvc_get/set_input_select` | `uint8_t` | 输入通道 |

## 9. 帧处理组（Phase 7/10）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_allocate_frame(data_bytes)` | 分配帧（可带缓冲） | `uvc_frame_t *`（library_owns_data=1） | 转出帧/复制目标 |
| `uvc_free_frame(frame)` | 释放帧 | 无 | 配对 |
| `uvc_duplicate_frame(in, out)` | 深拷贝帧（含 metadata） | out 被完整填充 | 抢救复用帧的标准姿势 |
| `uvc_any2rgb(in, out)` | 一键转 RGB | RGB 帧（YUYV/UYVY/RGB/MJPEG* 输入） | *MJPEG 需 LIBUVC_HAS_JPEG |
| `uvc_any2bgr(in, out)` | 一键转 BGR | BGR 帧（YUYV/UYVY/BGR） | BMP 直接用 |
| `uvc_yuyv2rgb / uvc_uyvy2rgb` | 定向转 RGB | RGB 帧 | |
| `uvc_yuyv2bgr / uvc_uyvy2bgr` | 定向转 BGR | BGR 帧 | |
| `uvc_yuyv2y(in, out)` | 提亮度 | GRAY8（w*h 字节） | 机器视觉常用 |
| `uvc_yuyv2uv(in, out)` | 提色度 | GRAY8（**实际只取 U**） | 注意坑 |
| `uvc_mjpeg2rgb / uvc_mjpeg2gray` | MJPEG 解码 | RGB / GRAY8 | 仅编译带 libjpeg 时存在 |

## 10. 诊断组（Phase 1）

| 签名 | 作用 | 拿到/设置什么数据 | 配合关系 |
|------|------|------------------|---------|
| `uvc_strerror(uvc_error_t)` | 错误码 → 字符串 | `const char *`（未知返回 "Unknown error"） | 任何错误处理 |
| `uvc_perror(uvc_error_t, msg)` | 错误打到 stderr | 格式 `msg: 文字 (码)` | 每个调用失败时 |
| `uvc_print_diag(devh, FILE*)` | 打印设备全景 | 输出到流 | open 后 |
| `uvc_print_stream_ctrl(&ctrl, FILE*)` | 打印合同 | 输出到流 | 谈判后 |

## 11. 关键枚举与结构（速查）

- **uvc_error_t**：SUCCESS=0；IO=-1 …NOT_SUPPORTED=-12；INVALID_DEVICE=-50；INVALID_MODE=-51；CALLBACK_EXISTS=-52；OTHER=-99
- **uvc_req_code**：SET_CUR=0x01，GET_CUR=0x81，GET_MIN=0x82，GET_MAX=0x83，GET_RES=0x84，GET_LEN=0x85，GET_INFO=0x86，GET_DEF=0x87
- **uvc_frame_format**：UNKNOWN=0, ANY=0, UNCOMPRESSED=1, COMPRESSED=2, YUYV=3, UYVY=4, RGB=5, BGR=6, MJPEG=7, H264=8, GRAY8=9, GRAY16=10, BY8=11, BA81=12, SGRBG8=13, SGBRG8=14, SRGGB8=15, SBGGR8=16, NV12=17, P010=18
- **uvc_frame_t**：data, data_bytes, width, height, frame_format, step, sequence, capture_time, capture_time_finished, source, library_owns_data, metadata, metadata_bytes
- **uvc_stream_ctrl_t**：bFormatIndex, bFrameIndex, dwFrameInterval(100ns), dwMaxVideoFrameSize, dwMaxPayloadTransferSize, bInterfaceNumber, …（全文见 Phase 5）
- **uvc_device_descriptor_t**：idVendor, idProduct, bcdUVC（v0.0.7 恒 0）, serialNumber, manufacturer, product
- **uvc_input_terminal_t**：bTerminalID, wTerminalType, bmControls（CT 控制位图）
- **uvc_processing_unit_t**：bUnitID, bSourceID, bmControls（PU 控制位图）
- **uvc_extension_unit_t**：bUnitID, guidExtensionCode[16], bmControls
- **CT 选择器**：0x01 scanning_mode, 0x02 ae_mode, 0x03 ae_priority, 0x04 exposure_abs, 0x05 exposure_rel, 0x06 focus_abs, 0x07 focus_rel, 0x08 focus_auto, 0x09 iris_abs, 0x0a iris_rel, 0x0b zoom_abs, 0x0c zoom_rel, 0x0d pantilt_abs, 0x0e pantilt_rel, 0x0f roll_abs, 0x10 roll_rel, 0x11 privacy, 0x12 focus_simple, 0x13 digital_window, 0x14 roi
- **PU 选择器**：0x01 backlight, 0x02 brightness, 0x03 contrast, 0x04 gain, 0x05 power_line_frequency, 0x06 hue, 0x07 saturation, 0x08 sharpness, 0x09 gamma, 0x0a wb_temperature, 0x0b wb_temperature_auto, 0x0c wb_component, 0x0d wb_component_auto, 0x0e digital_multiplier, 0x0f digital_multiplier_limit, 0x10 hue_auto, 0x11 analog_video_standard, 0x12 analog_lock_status, 0x13 contrast_auto
