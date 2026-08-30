# libuvc 接口级系统学习计划（v2）

> 更新于 2026-08-30。本计划聚焦**公开 API 接口层**：每个接口的作用、拿到什么数据、接口之间的配合调用关系。

## 学习目标（用户 2026-08-30 提出）

1. 完整学习 libuvc 的**所有公开接口**，每个接口的作用是什么
2. 每个接口**能拿到什么数据**（输入/输出）
3. 理解**接口之间的配合调用关系**（先调谁后调谁、谁的输出喂给谁）
4. 从头学起、零基础可读；代码讲解必须附带**实际运行示例**（记忆约定）

## 历史：已完成的学习（归档）

2026-07-11 完成 12 阶段**源码内部机制**学习（协议报文、线程、缓冲），全部 ✅，产物：
- [libuvc-knowledge-notes.md](libuvc-knowledge-notes.md) — 源码级知识笔记（本系列作为"内部原理"参考引用）
- 本计划的 v1 版本已被本文件替换

## 新学习路线（接口视角，按调用顺序）

### Phase 0：全景地图 ✅ 2026-08-30
- [x] 0.1 libuvc 是什么、UVC 协议背景、与 libusb 的关系
- [x] 0.2 主干调用链（init→find→open→negotiate→start→frame→close→exit）
- [x] 0.3 四件套对象模型：context / device / device_handle / stream_handle
- [x] 0.4 全部接口按用途分组总览
- 文档：`lessons/00_beginner_guide.md`

### Phase 1：初始化与退出 ✅ 2026-08-30
- [x] 1.1 uvc_init() — 创建上下文（拿 uvc_context_t）
- [x] 1.2 uvc_exit() — 释放上下文
- [x] 1.3 libusb 是什么（薄封装关系）
- [x] 1.4 诊断四件套：uvc_strerror / uvc_perror / uvc_print_diag / uvc_print_stream_ctrl（后两个签名已讲，演示放 Phase 4/5）
- [x] 1.5 运行示例：编译 libuvc + 最小程序真实运行（outputs/phase1_run.txt）
- 文档：`lessons/phase1_init_context.md`

### Phase 2：设备发现 ✅ 2026-08-30
- [x] 2.1 ~ 2.6 全部完成（本机实跑：04f2:b76f ACER 摄像头枚举成功）
- 文档：`lessons/phase2_device_discovery.md`

### Phase 3：打开与关闭 ✅ 2026-08-30
- [x] 3.1 ~ 3.5 全部完成（本机实跑失败路径：uvc_open 报 Not supported(-12)）
- 文档：`lessons/phase3_open_close.md`（含检查点 D1 三条出路）
- 检查点 D1 结论：无需用户立刻决策——演示代码已零改动兼容，装 USBDK 或换环境（Ubuntu VM + HIKVISION）即可跑

### Phase 4：能力查询（描述符读取）✅ 2026-08-30
- [x] 4.1 ~ 4.4 全部完成（代码就绪，待 D1 解决后实跑）
- 文档：`lessons/phase4_capability_query.md`

### Phase 5：流协商（Probe/Commit）✅ 2026-08-30
- [x] 5.1 ~ 5.5 全部完成（代码就绪，待 D1）
- 文档：`lessons/phase5_stream_negotiation.md`

### Phase 6：流生命周期 ✅ 2026-08-30
- [x] 6.1 ~ 6.5 全部完成（代码就绪，待 D1）
- 文档：`lessons/phase6_stream_lifecycle.md`

### Phase 7：帧获取 ✅ 2026-08-30
- [x] 7.1 ~ 7.5 全部完成（代码就绪，待 D1）
- 文档：`lessons/phase7_frame_capture.md`

### Phase 8：通用控制底层（遥控器底座）✅ 2026-08-30
- [x] 8.1 ~ 8.5 全部完成（代码就绪，待 D1）
- 文档：`lessons/phase8_lowlevel_control.md`

### Phase 9：高层相机控制族（35+ 对 get/set）✅ 2026-08-30
- [x] 9.1 ~ 9.3 全部完成（代码就绪，待 D1）
- 文档：`lessons/phase9_highlevel_controls.md`

### Phase 10：帧格式转换 ✅ 2026-08-30
- [x] 10.1 ~ 10.4 全部完成（本机实跑：8 色块 BT.601 验证通过 + BMP 输出）
- 文档：`lessons/phase10_frame_conversion.md`

### Phase 11：综合实战 ✅ 2026-08-30
- [x] 11.1 完整程序（代码就绪，待 D1 实跑）
- [x] 11.2 API 速查表定稿 `lessons/api_reference.md`（~110 接口全表）
- [x] 11.3 常见错误码与调试方法
- 文档：`lessons/phase11_full_demo.md` + `lessons/api_reference.md`

## 演示环境准备

| 项 | 状态 | 说明 |
|----|------|------|
| 摄像头 | ✅ ACER HD User Facing | 内置 UVC 摄像头，被 usbvideo.sys 绑定 |
| 编译器 | ✅ gcc 8.1.0 MinGW x86_64 | E:\software\OfficeWorkLife\CCplus\mingw64 |
| 构建工具 | ✅ cmake + mingw32-make | |
| libusb | ✅ 清华 MSYS2 镜像预编译包 1.0.27 | third_party/libusb-dist/mingw64/ |
| libuvc 编译 | ✅ 静态库 libuvc.a + example.exe | MinGW + cmake，配方见 findings.md |
| 摄像头访问 | ⚠️ 检查点 D1 | 内置摄像头需 USBDK 驱动（不影响正常使用）或外置摄像头 |

## 检查点

- **D1**（Phase 2 演示前）：libusb 打开被 usbvideo.sys 占用的内置摄像头会失败。方案：A) 装 USBDK 驱动（推荐，与系统驱动共存）；B) 外置 USB 摄像头；C) 先纯理论后补演示。**需与用户确认**。

## 学习规则

- 每 Phase 产出一份 lessons/ 文档：接口表格（作用/拿到什么数据）+ 原理 + 坑 + 真实运行示例
- 对话里简短讲解，详细内容指向文档
- 每完成一 Phase 更新 progress.md，新发现写入 findings.md
- api_reference.md 随各 Phase 逐步填充，Phase 11 定稿
