# Phase 11 · 综合实战（完整调用链 + 常见问题）

> 收官。把 00~10 全部串起来：一个真实抓图程序 + 调试方法 + 常见错误码对照。
> 演示程序：`../demos/phase11_full_demo.c`（需先解决 D1 才能实跑）

---

## 1. 完整程序：打开摄像头 → 抓图存 BMP

`demos/phase11_full_demo.c` 干的事：

```
① uvc_init                    工作台
② uvc_find_device(0,0,NULL)   名片
③ uvc_open                    控制台
④ uvc_print_diag              自述文件
⑤ uvc_get_stream_ctrl_format_size(640x480@30 YUYV，失败用菜单第一项兜底)  合同
⑥ uvc_start_streaming(cb)     建流+开闸（快捷组合）
⑦ 流中 uvc_get_ae_mode        证明控制线与数据线并行
⑧ 回调每 30 帧 uvc_any2bgr → write_bmp24 存 outputs/phase11_frame_XXXX.bmp
⑨ uvc_stop_streaming          关闸
⑩ uvc_close → uvc_unref_device → uvc_exit   逐级归还
```

跑 5 秒 @30fps 约存 5 张 BMP。**这个程序的骨架就是一切 libuvc 程序的骨架**——以后写任何新程序，从它改起。

**回调里的纪律提醒**（Phase 6 的坑，实战版）：回调里用了 `uvc_any2bgr`（转换函数，安全）但**没有**调用任何 uvc 控制/流函数——那些会死锁。BMP 写入是文件 IO，在回调里做 5 张还行；高频存储要移出回调。

## 2. 常见错误码速查（真机调试用）

| 现象 | 错误 | 原因 | 排查方向 |
|------|------|------|---------|
| open 报 `Not supported (-12)` | UVC_ERROR_NOT_SUPPORTED | Windows：设备没绑 WinUSB（usbvideo 占用） | D1：装 USBDK / 外置摄像头（本机实测，见 outputs/phase3_run.txt） |
| open 报 `Access denied (-3)` | UVC_ERROR_ACCESS | 设备被独占（相机 App 开着） | 关掉用摄像头的程序再试 |
| find 报 `No such device (-4)` | UVC_ERROR_NO_DEVICE | 总线上没有 UVC 设备 | 检查 USB 连接/换口；用 Phase 2 枚举确认 |
| 协商报 `Invalid mode (-14)` | UVC_ERROR_INVALID_MODE | 菜单里没有该 格式×分辨率×帧率 | Phase 4 打印菜单，用兜底策略 |
| get_frame 报 `Callback exists (-52)` | UVC_ERROR_CALLBACK_EXISTS | 回调模式下又去轮询 | 二选一：start 时 cb 传 NULL 才能轮询 |
| 控制类接口报 `Pipe (-9)` | UVC_ERROR_PIPE | 设备不支持该控制 | 正常！用 Phase 9 的容错写法，或先查 bmControls 位图 |
| get_frame 报 `Timeout (-7)` | UVC_ERROR_TIMEOUT | 超时窗口内没有新帧 | 检查流是否真在跑；摄像头可能被系统电源管理暂停 |
| `Busy (-6)` | UVC_ERROR_BUSY | 资源已被占用 | 同一接口重复建流、或设备已被本上下文打开 |

## 3. 调试三板斧

1. **`uvc_print_diag` 先行**：任何设备接进来，第一步打印自述文件。大多数"协商失败"看一眼菜单就有答案。
2. **`uvc_perror` 每个调用**：错误码 + 上下文前缀，照着上表定位。
3. **分步替换**：`uvc_start_streaming` 跑不通时，拆成 open_ctrl → start → get_frame 分步，缩小故障点。启编译 `-DENABLE_UVC_DEBUGGING=ON`（libuvc 编译选项）能看到内部 UVC_DEBUG 日志。

## 4. 与你的两个环境的衔接

- **Ubuntu VM（已验证路径）**：demos 全是标准 C，编译一行 `gcc -o x x.c -luvc -lusb-1.0 -lpthread`，`sudo` 运行，接 HIKVISION 2bdf:028a。Phase 3 的 D1 问题在 Linux 上不存在（内核驱动会被 libuvc 自动 detach）。
- **Windows 本机**：装 USBDK 后全部 demos 零改动运行。需要时告诉我，我帮你找 USBDK 的国内可下载源。

## 5. 全部接口速查表

配套文档 [api_reference.md](api_reference.md)：v0.0.7 全部公开接口的签名、作用、拿到什么数据、配合关系、所在 Phase 的一页式速查。**日常开发主要查它**。

---

## 6. 总结：从零到抓图，你走过的路

```
工作台 uvc_init
  └─ 名片 uvc_find_device / uvc_get_device_list
      └─ 控制台 uvc_open（读自述文件 + 占接口）
          ├─ 菜单 uvc_get_format_descs / uvc_print_diag        ── 能力查询
          ├─ 合同 uvc_get_stream_ctrl_format_size             ── 流协商
          │    └─ 水管 uvc_stream_open_ctrl ── 开闸 uvc_stream_start
          │         └─ 帧 uvc_stream_get_frame / 回调          ── 数据到手
          │              └─ uvc_any2rgb/any2bgr               ── 转格式
          ├─ 遥控器 uvc_get_ctrl/set_ctrl + 35 对 get/set      ── 控制线
          └─ 归还：stop → close → unref → exit
```

学完全部 Phase，你对 libuvc 应该建立起三层认识：
1. **接口层**（本系列）：哪个函数拿什么数据、什么顺序调、怎么配合——api_reference.md 速查
2. **原理层**：描述符树、Probe/Commit、双缓冲、Payload 组帧——旧笔记 libuvc-knowledge-notes.md
3. **代码层**：demo 全部可编译可运行——demos/ + outputs/ 真机输出

祝玩得开心，有问题随时来问。
