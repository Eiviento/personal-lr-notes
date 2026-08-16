# USB SDK 最小代码示例集

13 份最小可独立运行的 libusb 示例，每份聚焦一个功能。配套讲解页：`../usb-sdk-examples.html`（双击打开）。

**编译运行环境**：Ubuntu VM（`~/桌面/hikusb/`），需 `sudo`。

| # | 文件 | 学什么 | 编译 | 真机预期 |
|---|------|--------|------|---------|
| 01 | 01_enum_devices.c | 枚举：抄内核花名册 | `gcc -o enum_devices 01_enum_devices.c -lusb-1.0` | 列出设备，高亮目标 VID:PID |
| 02 | 02_hotplug_detect.c | 热插拔：ARRIVED/LEFT 回调 | 同上模式 | ENUMERATE 刷屏 + 实时打印 |
| 03 | 03_desc_tree_walk.c | 描述符树：3.1 树的 C 版 | 同上模式 | 打印 433 字节链树形结构 |
| 04 | 04_claim_alt_setting.c | claim + 切 Alt：四层动作 | 同上模式 | claim 成功 → 自动发现流 Alt（本机 Alt0）→ 还原 |
| 05 | 05_clear_halt.c | Halt 恢复闭环 | 同上模式 | 设备拒绝（教科书 PIPE / 本机 IO）→ GET_STATUS → clear_halt |
| 06 | 06_uvc_brightness.c | 标准 UVC 亮度（PU） | 同上模式 | ★ STALL（本设备 PU 空壳，预期失败=教学点） |
| 07 | 07_uvc_probe_commit.c | Probe/Commit 协商 | 同上模式 | 打印设备自报格式/帧率范围 |
| 08 | 08_uvc_open_stream.c | 开流：SET_INTERFACE + 收 1 秒 | 同上模式 | 打印字节速率（管道已通） |
| 09 | 09_xu_minimal.c | XU：GET_LEN 读版本 | 同上模式 | 返回协议版本号 |
| 10 | 10_frame_mailbox.cpp | 信箱模式取流（libuvc） | `g++ -o frame_mailbox 10_frame_mailbox.cpp -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)` | 窗口显示画面 |
| 11 | 11_cdc_serial.c | CDC 串口收发 | 同上模式 | 行编码 + 控制线 + 批量统计（需 2bdf:028a） |
| 12 | 12_hid_report.c | HID 中断报表 | 同上模式 | 每 100ms 打印报表 hex（需 2bdf:028a） |
| 13 | 13_sdk_skeleton.c | 综合骨架 | `gcc -o sdk_skeleton 13_sdk_skeleton.c -lusb-1.0 -pthread` | 插拔自动响应 |

**学习路径建议**：01 设备层 → 06~10 UVC 主战场 → 11/12 其他类 → 13 综合。

**同步纪律**：本目录 .c 文件是唯一可编译真相源；`../usb-sdk-examples.html` 内嵌同一份代码，改动时两边同步。
