# libuvc 系统学习计划

## 学习目标
1. 理解 libuvc 与 UVC 设备交互的完整流程及原理
2. 掌握 UVC 报文协议（控制传输 + 视频流传输）
3. 熟悉 libuvc API 的调用方式

## 学习阶段

### 第一阶段：背景知识 — UVC 规范基础
- [ ] 1.1 USB Video Class (UVC) 规范概述 — 什么是 UVC，规范版本 (1.0/1.1/1.5)
- [ ] 1.2 UVC 设备拓扑结构 — VC 接口 (VideoControl) + VS 接口 (VideoStreaming)
- [ ] 1.3 UVC 中的单元模型：Camera Terminal → Processing Unit → Extension Unit → Output Terminal
- [ ] 1.4 USB 描述符体系回顾（Device/Configuration/Interface/Endpoint Descriptor）

### 第二阶段：libuvc 架构总览
- [ ] 2.1 源码文件结构与职责划分
- [ ] 2.2 核心数据结构全景图
  - uvc_context_t → uvc_device_t → uvc_device_handle_t → uvc_stream_handle_t
  - uvc_device_info_t → uvc_control_interface_t + uvc_streaming_interface_t
  - uvc_format_desc_t → uvc_frame_desc_t
  - uvc_stream_ctrl_t（流控制块）
  - uvc_frame_t（帧数据）
- [ ] 2.3 libuvc 依赖关系（libusb 的作用）

### 第三阶段：设备发现与打开流程
- [ ] 3.1 初始化：uvc_init() 创建上下文
- [ ] 3.2 设备枚举：uvc_get_device_list() 如何发现 UVC 设备
  - 遍历 USB 设备 → 检查 Interface Class=14 (Video), Subclass=1/2
- [ ] 3.3 查找特定设备：uvc_find_device() / uvc_find_devices()
- [ ] 3.4 打开设备：uvc_open() 的完整流程
  - libusb_open → 获取设备描述符 → 解析 VC/VS 描述符
  - 声明接口 (claim interface) → 注册状态回调 → 启动事件处理线程
- [ ] 3.5 获取设备描述符：uvc_get_device_descriptor()
- [ ] 3.6 关闭设备：uvc_close() 的资源清理流程

### 第四阶段：UVC 描述符解析（device.c 深入）
- [ ] 4.1 VideoControl 接口描述符解析
  - VC Header：UVC 版本号、时钟频率
  - Input Terminal (Camera)：支持的控制位图
  - Processing Unit：支持的图像处理控制位图
  - Extension Unit：厂商扩展
- [ ] 4.2 VideoStreaming 接口描述符解析
  - VS Input Header：端点地址、Terminal Link
  - Format Descriptor (Uncompressed/MJPEG/Frame-based)
  - Frame Descriptor：分辨率、帧率、最大帧大小
- [ ] 4.3 描述符解析状态机：uvc_parse_vc() / uvc_parse_vs() 的分发逻辑

### 第五阶段：UVC 控制传输协议
- [ ] 5.1 USB 控制传输基础（bmRequestType, bRequest, wValue, wIndex, wLength）
- [ ] 5.2 UVC 请求码：SET_CUR / GET_CUR / GET_MIN / GET_MAX / GET_RES / GET_LEN / GET_INFO / GET_DEF
- [ ] 5.3 底层控制 API：uvc_get_ctrl() / uvc_set_ctrl() / uvc_get_ctrl_len()
  - 请求类型：0xA1 (Get) / 0x21 (Set)
  - wValue = Control Selector << 8
  - wIndex = Unit ID << 8 | Interface Number
- [ ] 5.4 高层控制 API（ctrl-gen.c 自动生成）
  - Camera Terminal 控制：曝光、聚焦、变焦、云台、隐私...
  - Processing Unit 控制：亮度、对比度、增益、白平衡、锐度...
- [ ] 5.5 电源管理：uvc_get_power_mode() / uvc_set_power_mode()

### 第六阶段：流协商机制（Probe/Commit）
- [ ] 6.1 Probe/Commit 协议原理：为何需要协商
- [ ] 6.2 uvc_query_stream_ctrl() 详解
  - UVC 1.0: 26 字节控制块
  - UVC 1.1+: 34 字节控制块（增加时钟频率、framing info、版本信息）
  - SET_CUR 设置期望参数 → GET_CUR 获取设备确认的参数
- [ ] 6.3 uvc_probe_stream_ctrl()：协商并确认参数
- [ ] 6.4 uvc_get_stream_ctrl_format_size()：根据格式/分辨率/帧率自动查找并协商
- [ ] 6.5 Still Image Capture（静态图像捕获）

### 第七阶段：视频流传输 — 核心流程
- [ ] 7.1 创建流：uvc_stream_open_ctrl()
  - 分配双缓冲区（outbuf / holdbuf）
  - Commit 流控制参数
  - 初始化互斥锁和条件变量
- [ ] 7.2 启动流：uvc_stream_start()
  - 等时传输 (Isochronous) vs 批量传输 (Bulk)
  - altsetting 选择策略
  - 分配传输缓冲区 (LIBUVC_NUM_TRANSFER_BUFS)
  - libusb_fill_iso_transfer / libusb_fill_bulk_transfer
  - 启动回调线程 (cb_thread)
- [ ] 7.3 数据传输回调：_uvc_stream_callback()
  - 传输完成/错误/取消的处理
  - 等时传输的多包处理

### 第八阶段：视频流报文协议分析（Payload Header）
- [ ] 8.1 UVC Payload Header 格式（UVC 1.5 §2.4.3.3）
  - bHeaderLength（头部长度）
  - bmHeaderInfo 标志位详解：
    - FID (bit 0): Frame Identifier — 帧切换检测
    - EOF (bit 1): End of Frame — 帧结束标志
    - PTS (bit 2): Presentation Time Stamp — 显示时间戳
    - SCR (bit 3): Source Clock Reference — 源时钟参考
    - RES (bit 4): Reserved
    - STI (bit 5): Still Image — 静态图像触发
    - ERR (bit 6): Error — 错误标志
    - EOH (bit 7): End of Header — 头部结束
  - PTS 时间戳
  - SCR (Source Clock Reference)
- [ ] 8.2 _uvc_process_payload() 逐帧组装过程
  - FID 位翻转检测 → 帧边界检测
  - EOF 位检测 → 帧完成
  - 数据拷贝到 outbuf
- [ ] 8.3 _uvc_swap_buffers() — 双缓冲区切换机制
- [ ] 8.4 iSight 摄像头的特殊处理

### 第九阶段：帧获取与回调机制
- [ ] 9.1 回调模式：_uvc_user_caller() 线程
  - pthread_cond_wait 等待新帧
  - _uvc_populate_frame() 填充帧信息
  - 调用用户回调函数
- [ ] 9.2 轮询模式：uvc_stream_get_frame()
  - 超时处理（-1=立即返回, 0=无限等待, >0=超时微秒数）
  - last_polled_seq 防止重复返回
- [ ] 9.3 帧结构 uvc_frame_t 各字段含义
  - data, data_bytes, width, height, frame_format
  - step, sequence, capture_time
  - library_owns_data, metadata

### 第十阶段：流停止与资源清理
- [ ] 10.1 uvc_stream_stop() 的关闭序列
  - 取消所有传输 → 等待传输完成 → 唤醒回调线程 → join 线程
- [ ] 10.2 uvc_stream_close() 的资源释放
- [ ] 10.3 uvc_stop_streaming() / uvc_close() 的级联清理

### 第十一阶段：帧格式转换
- [ ] 11.1 YUYV → RGB/BGR 转换（定点数加速）
- [ ] 11.2 UYVY → RGB/BGR 转换
- [ ] 11.3 MJPEG → RGB/Gray 转换（需 libjpeg）
- [ ] 11.4 YUYV → Y (Gray) / UV 分量提取
- [ ] 11.5 帧复制：uvc_duplicate_frame()

### 第十二阶段：综合实战
- [ ] 12.1 example.c 完整走读
- [ ] 12.2 典型调用序列总结
- [ ] 12.3 常见问题与调试方法

---

## 学习规则
- 每个知识点学习完成后在 progress.md 中记录
- 用户提出的问题记录在 findings.md 中
- 每完成一个阶段，回顾并总结
