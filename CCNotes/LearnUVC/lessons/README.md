# libuvc 接口级学习 · lessons 索引

> 本目录是 libuvc **公开接口**的系统教程：每个接口的作用、能拿到什么数据、接口之间怎么配合。
> 源码内部机制请查仓库根目录的 [libuvc-knowledge-notes.md](../libuvc-knowledge-notes.md)。

## 学习顺序

| 文档 | 内容 | 状态 |
|------|------|------|
| [00_beginner_guide.md](00_beginner_guide.md) | 全景地图：主干调用链 + 四件套对象模型 + 接口分组总览 | ✅ 2026-08-30 |
| [phase1_init_context.md](phase1_init_context.md) | 初始化与退出：uvc_init/uvc_exit + 诊断函数 | ✅ 2026-08-30（实跑） |
| [phase2_device_discovery.md](phase2_device_discovery.md) | 设备发现：枚举/查找/设备信息 | ✅ 2026-08-30（实跑） |
| [phase3_open_close.md](phase3_open_close.md) | 打开与关闭：uvc_open/uvc_close + 事件回调 + **检查点 D1（Windows 驱动墙）** | ✅ 2026-08-30（实跑失败路径） |
| [phase4_capability_query.md](phase4_capability_query.md) | 能力查询：terminals/units/format_descs | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase5_stream_negotiation.md](phase5_stream_negotiation.md) | 流协商：Probe/Commit、stream_ctrl 合同逐字段 | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase6_stream_lifecycle.md](phase6_stream_lifecycle.md) | 流生命周期：建流/启动/停止/关闭 | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase7_frame_capture.md](phase7_frame_capture.md) | 帧获取：uvc_frame_t 逐字段、回调 vs 轮询 | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase8_lowlevel_control.md](phase8_lowlevel_control.md) | 通用控制底层：get_ctrl/set_ctrl 万能通道 | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase9_highlevel_controls.md](phase9_highlevel_controls.md) | 高层相机控制族：曝光/对焦/白平衡/图像质量等 35+ 对全表 | ✅ 2026-08-30（代码就绪，待 D1） |
| [phase10_frame_conversion.md](phase10_frame_conversion.md) | 帧格式转换：any2rgb 等 + YUYV 字节序 | ✅ 2026-08-30（实跑验证） |
| [phase11_full_demo.md](phase11_full_demo.md) | 综合实战：完整程序 + 错误码对照 + 调试三板斧 | ✅ 2026-08-30（代码就绪，待 D1） |
| [api_reference.md](api_reference.md) | **全部接口速查表**（~110 个接口 + 关键枚举） | ✅ 2026-08-30 定稿 |

## 配套目录

- `../demos/` — 11 个演示程序（C 源码，全部编译通过；phase1/2/10 已实跑）
- `../scripts/` — 构建脚本（build_libuvc.sh 搭环境、build_demos.sh 编译全部演示）
- `../outputs/` — 真实运行日志与图像（phase1/2/3/10 有真机输出）

## 运行演示前的准备（检查点 D1）

phase4~9、11 的演示需要真正打开摄像头。本机内置摄像头被 Windows 驱动绑定（实测 `uvc_open` 报 `Not supported (-12)`）。三条路：

1. **装 USBDK 驱动**（推荐，与系统驱动共存）——装好后全部演示零改动直接跑
2. **外置 USB 摄像头**（需同样解决驱动绑定问题）
3. **Ubuntu VM + HIKVISION 相机**（你已验证过的路径：`gcc -o x x.c -luvc -lusb-1.0 -lpthread` + sudo，Linux 无 D1 问题）

详见 [phase3_open_close.md](phase3_open_close.md) 的「检查点 D1」。

## 教学约定

1. 零基础可读：每一步写清"做什么 / 为什么 / 不做会怎样"
2. 每个 Phase 包含：接口表格（作用/拿到什么数据）→ 原理 → 坑 → 真实运行示例
3. 对话只做简短讲解，详细内容以本文档为准
