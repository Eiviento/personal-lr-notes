# 学习发现与问题记录

## 用户问题汇总

### Q1 (2026-07-11): 第一阶段内容太乱，接口太多，初学者看不清全局
> 用户反馈：第一次学习时给了太多接口，看起来很乱。
> **改进方向**：先讲"是什么、为什么"，用简单类比建立直觉（VC=遥控器，VS=水管），再逐步展开。

### Q2 (2026-07-11): 协商参数这一步一般会协商什么？
> 协商的核心：你指定格式/分辨率/帧率（3个输入），摄像头返回帧大小和载荷大小（2个关键输出）。Probe 是"问"，Commit 是"定"。

### Q3 (2026-07-11): XU 扩展单元的控制选择器和目标单元怎么理解？
> 标准 CT/PU 的控制选择器是 UVC 规范定死的，但 XU 的控制选择器是厂商自己定义的。通过 GUID 找到 XU 的 bUnitID（目标单元），再用厂商定义的 control_selector（控制选择器）发命令。

### Q4 (2026-07-11): CSID 和 Function ID 与 wValue/wIndex 的关系？
> 本质上是对 wValue 的 16 位空间做不同切分。标准 UVC 只用高字节放控制选择器，厂商可拆成 CSID（高字节）+ Function ID（低字节）。wIndex 始终不变（XU_ID<<8|interface）。

### Q5 (2026-07-11): 三级架构有没有示例？
> 一级 = wValue 高字节 (Category)，二级 = wValue 低字节 (SubFunc)，三级 = data[]（具体参数）。以 PTZ 巡航为例：0x0C01 + [路径号][预设点号][Pan角度][Tilt角度]。

### Q6 (2026-07-11): 四个摄像头是否对应四个 USB 设备？
> 不是。多 sensor 设备（如 RealSense D435、车载全景系统）在一个 USB 口下通过内部 CSI/MIPI 总线连接多个 sensor，由聚合芯片统一通过 USB 上报。用 CSID 区分不同 sensor。

### Q7 (2026-07-11): 怎么进行组包？每一包之间应该按照什么顺序来组帧？
> USB 是点到点总线，数据严格按发送顺序到达，不需要包序号。组帧只需 FID（翻转=换帧）+ EOF（置位=帧结束）。got_bytes（缓冲区偏移）就是隐式的"包序号"。

### Q8 (2026-07-11): 收到 N+1 帧时需要额外下发指令吗？FID 异常怎么恢复？
> 不需要下发任何指令，流启动后持续被动接收。FID 异常时 libuvc 自动通过 FID 翻转机制恢复，代价是丢 1~3 帧。可加帧头魔数（0xDEADBEEF）做二次校验减少损失。根本原因应检查硬件信号质量。

### Q9 (2026-07-11): 能否通过视频流传输文件？
> 可以。推荐在 Payload Header 的 metadata 字段中标记帧类型（文件帧 vs 图像帧），libuvc 已有 frame->metadata 支持。也可用帧序号窗口或格式切换方案。

### Q10 (2026-08-30): 想完整学习所有接口，理解接口间配合调用关系
> 用户新需求：接口级学习（不同于 2026-07-11 的源码级学习）。要点：每个接口作用 + 拿到什么数据 + 谁先谁后。已制定 task_plan.md v2（Phase 0-11）。

---

## 学习过程中的关键发现

### 架构理解
- libuvc 是 libusb 的薄封装，核心工作：解析描述符 + 封装控制传输 + 管理等时/批量传输
- 5 个核心结构体层层"打开"：context → device → device_handle → stream_handle
- 描述符树是后续所有操作的"字典"，uvc_open 时一次性解析完成

### UVC 协议关键点
- 控制传输寻址：wValue = 控制选择器，wIndex = 单元ID + 接口号
- 流协商：Probe 试探（不改变状态）→ Commit 确认（真正生效）
- 等时传输选 altsetting：从低到高找第一个带宽 ≥ dwMaxPayloadTransferSize 的
- Payload Header 的 FID 和 EOF 组合即完整的帧边界检测协议

### 设计模式
- 双缓冲：USB 线程写 outbuf，回调线程读 holdbuf，swap 信号驱动
- cancel + wait 模式：异步取消 transfer，等待回调自清理，避免死锁
- 定点数加速：YUYV→RGB 转换用 2^14 固定系数 + 位移代替浮点

### 初学 UVC 应遵循"先全局后细节"的路径
- 先用类比建立直觉（VC=遥控器，VS=水管）
- 只关注核心流程（init→find→open→negotiate→start→callback→stop→close）
- 在理解流程之前，数据结构和枚举值可以先不深究

---

## 2026-08-30 会话：环境盘点 + API 全景清单

### 环境盘点结果

| 项目 | 结果 |
|------|------|
| 摄像头 | ACER HD User Facing（内置 UVC，被 usbvideo.sys 绑定）|
| gcc | 8.1.0 x86_64-posix-sjlj MinGW-W64，位于 E:\software\OfficeWorkLife\CCplus\mingw64 |
| cmake / make | 可用（cmake + mingw32-make）|
| libusb | ❌ 未找到（msys64、mingw64 均无），需下载预编译包 |
| libuvc 源码 | ✅ v0.0.7 已克隆在 libuvc/ |
| libuvc 编译 | ❌ 未编译 |
| ⚠️ 风险 | 内置摄像头被 usbvideo.sys 占用，libusb_open 会失败 → 需 USBDK 或外置摄像头（检查点 D1）|

### libuvc v0.0.7 全部公开接口清单（来自 include/libuvc/libuvc.h）

**生命周期**：uvc_init / uvc_exit / uvc_get_device_list / uvc_free_device_list / uvc_find_device / uvc_find_devices / uvc_wrap / uvc_open / uvc_close / uvc_ref_device / uvc_unref_device

**设备信息**：uvc_get_device_descriptor / uvc_free_device_descriptor / uvc_get_bus_number / uvc_get_device_address / uvc_get_device / uvc_get_libusb_handle / uvc_set_status_callback / uvc_set_button_callback

**描述符查询**：uvc_get_camera_terminal / uvc_get_input_terminals / uvc_get_output_terminals / uvc_get_selector_units / uvc_get_processing_units / uvc_get_extension_units / uvc_get_format_descs

**流协商**：uvc_get_stream_ctrl_format_size / uvc_get_still_ctrl_format_size / uvc_probe_stream_ctrl / uvc_probe_still_ctrl

**流管理**：uvc_start_streaming / uvc_start_iso_streaming / uvc_stop_streaming / uvc_stream_open_ctrl / uvc_stream_ctrl / uvc_stream_start / uvc_stream_start_iso / uvc_stream_get_frame / uvc_stream_stop / uvc_stream_close / uvc_trigger_still

**通用控制**：uvc_get_ctrl_len / uvc_get_ctrl / uvc_set_ctrl / uvc_get_power_mode / uvc_set_power_mode

**高层控制（ctrl-gen.c 生成，get/set 对）**：scanning_mode、ae_mode、ae_priority、exposure_abs/rel、focus_abs/rel/simple_range/auto、iris_abs/rel、zoom_abs/rel、pantilt_abs/rel、roll_abs/rel、privacy、digital_window、digital_roi、backlight_compensation、brightness、contrast、contrast_auto、gain、power_line_frequency、hue、hue_auto、saturation、sharpness、gamma、white_balance_temperature、white_balance_temperature_auto、white_balance_component、white_balance_component_auto、digital_multiplier、digital_multiplier_limit、analog_video_standard、analog_video_lock_status、input_select

**帧处理**：uvc_allocate_frame / uvc_free_frame / uvc_duplicate_frame（+ frame.c 中的转换函数族 yuyv2*/uyvy2*/mjpeg2*/any2*，Phase 10 前完整核对）

**诊断**：uvc_perror / uvc_strerror / uvc_print_diag / uvc_print_stream_ctrl

### example.c 官方示例的调用序列（作为主干链佐证）

```
uvc_init → uvc_find_device → uvc_open → uvc_print_diag → uvc_get_format_descs
→ uvc_get_stream_ctrl_format_size → uvc_print_stream_ctrl → uvc_start_streaming(回调)
→ uvc_set_ae_mode(流中控制) → uvc_stop_streaming → uvc_close → uvc_unref_device → uvc_exit
```

---

## 2026-08-30：编译环境搭建实录（Phase 1 演示前）

### 网络与软件源

| 源 | 状态 |
|----|------|
| github.com | ❌ HTTP 000 不通 |
| codeload.github.com | ✅ 可下载源码 tar.gz |
| gitee.com | ✅ 通，但 mirrors/libusb 镜像**无 CMake 文件**（连 v1.0.26/v1.0.27 tag 都没有，已弃用） |
| mirrors.tuna.tsinghua.edu.cn (MSYS2) | ✅ 可下载预编译 MinGW 包 |

### 关键事实

- **libusb 新版已彻底移除 CMake 构建系统**（v1.0.26、v1.0.27 均无 CMakeLists.txt，只剩 autotools/msvc）。所以放弃源码编译，改用清华 MSYS2 镜像的预编译包 `mingw-w64-x86_64-libusb-1.0.27-1-any.pkg.tar.zst`（含 bin/libusb-1.0.dll + lib/libusb-1.0.dll.a + include）。解压用 Windows 自带 bsdtar 3.7.7（支持 zstd）。
- **libuvc 的 FindLibUSB.cmake 有坑**：`if (MSVC OR MINGW) return()`——MinGW 下 find_package(LibUSB) 什么都不做。解决：`CMAKE_PROJECT_INCLUDE` 预定义 `LibUSB::LibUSB` 导入目标（见 scripts/predefine-libusb-target.cmake）。
- **libuvc CMake 还需要 `-DLibUVC_STATIC=ON`**：否则 `LibUVC::UVC` 别名不创建，generate 阶段报 "target was not found"。
- **libuvc 在 Windows 上用 pthread**：MinGW 需 `-lwinpthread`，运行时需 libwinpthread-1.dll（工具链 posix 线程模型，x86_64-posix-sjlj）。
- JPEG 未装（JpegPkg QUIET 找不到）→ frame-mjpeg.c 未编入 → **MJPEG 解码暂不可用**。Phase 10 前需从同一镜像装 mingw-w64-x86_64-libjpeg-turbo。

### 最终构建配方（全部成功）

```
libusb: 清华镜像下载 .pkg.tar.zst → bsdtar 解压 → third_party/libusb-dist/mingw64/
libuvc: cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_BUILD_TARGET=Static -DBUILD_EXAMPLE=ON -DLibUVC_STATIC=ON
        -DCMAKE_THREAD_LIBS_INIT=-lwinpthread
        -DCMAKE_PROJECT_INCLUDE=scripts/predefine-libusb-target.cmake
        → libuvc.a (88KB) + example.exe 编译通过
demo 链接: -luvc -lusb-1.0 -lwinpthread；运行时需 libusb-1.0.dll + libwinpthread-1.dll
```

### 遇到的错误（按计划规则记录）

| 错误 | 尝试 | 解决方案 |
|------|------|---------|
| github.com 下载不通 (HTTP 000) | 1 | 换 codeload / 清华 MSYS2 镜像 |
| gitee libusb 镜像无 CMakeLists（master 和 v1.0.27/v1.0.26 都试过） | 2 | 放弃源码编译，用预编译包 |
| rm -rf third_party/libusb "Device or resource busy" | 1 | 换新目录名（旧目录遗留，无害） |
| cmake generate 报 LibUVC::UVC target not found | 1 | 加 -DLibUVC_STATIC=ON |
| FindLibUSB 在 MinGW 直接 return() | 1 | CMAKE_PROJECT_INCLUDE 预定义导入目标 |

### Phase 1 真实运行结果（outputs/phase1_run.txt）

- uvc_init 返回 Success (0)，ctx 指针 = 0xE28DC0
- uvc_strerror 表查询正常；99 → "Unknown error" 兜底
- uvc_perror 输出格式：`模拟一个错误: Not found (-5)` 到 stderr
- **注意**：stderr 行在合并输出中排到了最前——stdout 经管道是块缓冲、stderr 无缓冲，顺序会乱（已写进 Phase 1 文档的"坑"）

---

## 2026-08-30：demos 开发与真机运行实录（Phase 2/3/10 实测）

### 真实摄像头信息（outputs/phase2_run.txt）

- ACER HD User Facing = **04f2:b76f**（群光 Chicony），总线2/地址2
- 序列号 "200901010001"、厂家 "Generic"、产品名 "ACER HD User Facing" **均可读到**——字符串描述符读取只需 libusb_open 成功，不需要 claim 接口，所以被 usbvideo 绑定也能读
- **uvc_device_descriptor_t.bcdUVC 恒为 0**：v0.0.7 的 uvc_get_device_descriptor 从不填充该字段（真正的 UVC 版本在 open 后从 VC 头解析，print_diag 可见）

### 重要修正：uvc_open 在 usbvideo 绑定设备上的真实报错

- 我原预测 `Access denied (-3)`，**实测是 `Not supported (-12)`**（outputs/phase3_run.txt）
- 机理：libusb 的 WinUSB 后端打开设备时需要 WinUSB 接口；usbvideo.sys 绑定的设备没有 → libusb_open 直接 NOT_SUPPORTED，轮不到 claim。ACCESS(-3) 只会出现在"已绑 WinUSB 但被别的进程独占"的场景
- 结论不变：装 USBDK 或换外置摄像头

### Phase 10 转换验证（outputs/phase10_run.txt）

- **YUYV 字节序 = [Y0,U,Y1,V]**（每对像素共享 U、V，4:2:2）。我第一次构造测试数据写成了 [Y0,U,V,Y1]，转换结果全错——这个坑已写进 phase10 文档
- 修正后 8 个色块 RGB 全部符合 BT.601 公式（黑16/白235/红238,14,13/绿13,237,13/蓝15,15,239 等），uvc_yuyv2y 亮度序列与 Y 值逐一吻合
- 定点系数（22987/5636/11698/29049，2^14 移位）与浮点公式 R=Y+1.402(V-128) 等误差 ≤1
- 本机 libuvc 无 JPEG（未编 frame-mjpeg.c）：any2rgb(MJPEG) → Not supported
- BMP 写入正常（phase10_test.bmp，78 字节）

### demos 编译状态

- 11 个演示全部编译通过（scripts/build_demos.sh）
- 本机可实跑：phase1（init）、phase2（枚举）、phase10（转换）；phase3 已实跑（预期失败路径）
- phase4~9、11 待 D1 解决后运行（代码完整，零改动）

---

## 2026-08-30：批量交付完成清单

- **lessons/ 14 份文档**（1955 行）：00 总纲 + phase1~11 + api_reference 速查表（~110 接口全表）
- **demos/ 11 个演示**（.c 全部编译通过；phase1/2/3/10 已实跑并留存 outputs/）
- **scripts/ 3 个脚本**：build_libuvc.sh（搭环境）、build_demos.sh（编译演示）、predefine-libusb-target.cmake（MinGW 坑的绕过）
- **修正**：Phase 1 文档错误码表（INVALID_DEVICE=-50 / INVALID_MODE=-51 / CALLBACK_EXISTS=-52 / OTHER=-99，初版按 diag.c 表顺序误写为 -13/-14/-15，对照 libuvc.h 头文件修正）
- **用户可复用的第二环境**：CCNotes/USB/code/examples/10_frame_mailbox.cpp 是用户此前在 Ubuntu VM + HIKVISION 2bdf:028a 上跑通的 libuvc 程序——Phase 3 文档的 D1 方案 C 引用之
- **待办**：D1（USBDK）解决后跑 phase4~9、11；可选装 libjpeg-turbo 重编以支持 MJPEG
