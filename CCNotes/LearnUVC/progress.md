# 学习进度日志

## 会话 1（2026-07-11，已完成）：源码级系统学习

- **学习内容**: libuvc 源码系统学习（v0.0.7，commit 047920b）
- **产出**: [libuvc-knowledge-notes.md](libuvc-knowledge-notes.md)
- 完成 12 阶段 + 3 个扩展专题（XU 扩展单元、Payload 组帧、知识笔记整理），全部 ✅

## 会话 2（2026-08-30，进行中）：接口级学习

- **学习内容**: libuvc 全部公开接口——每个接口的作用、拿到什么数据、接口间配合关系
- **用户要求**: 从头带学，零基础可读，代码讲解带真实运行示例
- **环境**: ACER HD User Facing 内置摄像头；gcc 8.1.0 + cmake（E:\software\...）；libusb 待安装
- **产出目录**: `lessons/`（每 Phase 一份文档 + api_reference.md 速查表）
- **旧计划**: 源码级 12 阶段计划已归档进 task_plan.md v2

### 进度记录

| 日期 | 阶段 | 状态 | 备注 |
|------|------|------|------|
| 2026-08-30 | 计划制定 v2 | ✅ | 接口级 12 Phase 新路线，聚焦作用/数据/配合关系 |
| 2026-08-30 | Phase 0: 全景地图 | ✅ | lessons/00_beginner_guide.md：主干链+四件套+分组总览 |
| 2026-08-30 | 环境盘点 | ✅ | 摄像头 OK，gcc/cmake OK，libusb 缺失（待下载） |
| 2026-08-30 | 编译环境搭建 | ✅ | libusb 1.0.27（清华镜像预编译包）+ libuvc v0.0.7 静态库 + example.exe 编译通过 |
| 2026-08-30 | Phase 1: 初始化与退出 | ✅ | uvc_init/uvc_exit/strerror/perror + 真实运行（outputs/phase1_run.txt） |
| 2026-08-30 | Phase 2: 设备发现 | ✅ | 本机实跑：04f2:b76f 枚举 + find_device + 描述符（outputs/phase2_run.txt） |
| 2026-08-30 | Phase 3: 打开与关闭 | ✅ | 本机实跑失败路径：NOT_SUPPORTED(-12)（outputs/phase3_run.txt），D1 方案写入文档 |
| 2026-08-30 | Phase 4~9、11 | ✅ | 文档+演示代码全部完成（待 D1 解决后实跑） |
| 2026-08-30 | Phase 10: 帧格式转换 | ✅ | 本机实跑：8 色块验证 + BMP（outputs/phase10_run.txt + phase10_test.bmp） |
| 2026-08-30 | api_reference 速查表 | ✅ | ~110 接口全表定稿 |

## 完成状态（2026-08-30）

- **全部 12 份 lessons 文档完成**（00 总纲 + phase1~11 + api_reference）
- **11 个演示程序全部编译通过**；phase1/2/3/10 已实跑（含真实失败路径）
- **剩余待办**：D1 解决后运行 phase4~9、11（代码零改动）；可选：装 libjpeg-turbo 重编支持 MJPEG

## 待办检查点

- **D1**（Phase 2 演示前）：确认摄像头访问方案（USBDK / 外置摄像头 / 先理论）
- Phase 1 前：下载 libusb 预编译包 → 编译 libuvc（构建脚本 scripts/）
