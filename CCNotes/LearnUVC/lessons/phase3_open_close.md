# Phase 3 · 打开与关闭（uvc_open / uvc_close + 事件回调）

> 对应主干链第 ③⑩ 步。学完本 Phase 你会：把"名片"换成"控制台"，理解 uvc_open 内部到底做了什么，以及 Windows 上打开内置摄像头的驱动问题（检查点 D1）。
> 演示程序：`../demos/phase3_open_close.c`，真实运行输出：`../outputs/phase3_run.txt`

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 | 返回 |
|------|------|------|-------------|------|
| `uvc_open` | 打开设备，**一次性解析全部描述符** | `dev` | `uvc_device_handle_t *`（控制台） | 错误码 |
| `uvc_close` | 关闭设备 | `devh` | 无 | void |
| `uvc_get_device` | 由 devh 找回 dev（自动 ref） | `devh` | `uvc_device_t *` | — |
| `uvc_get_libusb_handle` | 拿底层 libusb 句柄 | `devh` | `libusb_device_handle *` | — |
| `uvc_wrap` | 已有系统句柄时直接包装成 devh | 系统句柄 + ctx | `uvc_device_handle_t *` | 错误码 |
| `uvc_set_status_callback` | 注册状态变化回调 | `devh` + 回调 + 自定义指针 | 无 | void |
| `uvc_set_button_callback` | 注册按钮事件回调 | 同上 | 无 | void |

---

## 2. 检查点 D1：Windows 上的驱动墙（先读这一段）

在本机上，`uvc_open` 内置摄像头**实测报错**（`outputs/phase3_run.txt`）：

```
找到摄像头
uvc_open: Not supported (-12)
```

**为什么**：Windows 把内置摄像头绑定给了系统驱动 usbvideo.sys。libusb 在 Windows 上靠 WinUSB 后端工作——打开设备时要求设备有 WinUSB 接口；usbvideo 绑定的设备没有，`libusb_open` 直接返回 `NOT_SUPPORTED`（还没轮到 claim 那一步）。

（如果你看到的是 `Access denied (-3)`：说明设备已绑 WinUSB 但被别的程序独占，比如相机 App 正开着。）

**三条出路，按推荐排序**：

| 方案 | 做法 | 代价 |
|------|------|------|
| A. USBDK 驱动（推荐） | 装 [USBDK](https://github.com/daynix/usbdk)（一个开源内核驱动），libusb 自动改用 usbdk 后端 | 与 usbvideo **共存**，摄像头日常使用完全不受影响；一次安装永久生效 |
| B. 外置 USB 摄像头 | 插一个普通 UVC 外置摄像头 | 外置摄像头默认绑 usbvideo，**同样需要 USBDK**……除非设备绑了 WinUSB。所以此方案实际是配合 A 用（或买有 WinUSB 驱动授权的工业相机，如你的 HIKVISION 2bdf:028a） |
| C. 你现成的 Ubuntu VM | 在 VM 里编译运行 demos（`gcc -o x x.c -luvc -lusb-1.0 -lpthread`，需 sudo），接 HIKVISION 相机 | 你 USB 学习项目里已验证过这条路（`10_frame_mailbox.cpp`） |

> 说明：本机网络不通 GitHub（findings.md 有记录）。装 USBDK 需要能访问其下载源，或之后告诉我帮你找国内镜像。装好后 Phase 3~9、11 的演示**零改动**直接跑。

---

## 3. uvc_open：敲门之后发生了什么

`uvc_open(dev, &devh)` 只有两步，但第二步很重：

```c
/* device.c 源码 */
ret = libusb_open(dev->usb_dev, &usb_devh);   /* ① 打开底层 USB 句柄 */
...
ret = uvc_open_internal(dev, usb_devh, devh); /* ② 读自述文件 + 占接口 + 挂状态侦听 */
```

`uvc_open_internal` 的完整流程（值得逐行读 device.c:337-414）：

1. **ref 设备**（名片的计数 +1）
2. **`uvc_get_device_info`：一次性解析全部描述符**——读配置描述符 → 扫 VideoControl（UVC 版本、Input Terminal 支持哪些控制、PU 支持哪些处理、XU 厂商扩展）→ 按 VC 头里列出的接口扫 VideoStreaming（支持哪些格式/分辨率/帧率）。这就是第 00 课说的"自述文件"，Phase 4 的所有查询函数读的就是这份解析结果。
3. **claim VideoControl 接口**（`uvc_claim_if`）：先 `libusb_detach_kernel_driver`（Linux 上把内核驱动让出来；Windows 上此调用返回 NOT_SUPPORTED 但被容忍），再 `libusb_claim_interface`。
4. 若设备有**状态中断端点**：挂一个中断传输，持续侦听设备主动上报（这就是 status/button 回调的来源）。
5. 若是本上下文**第一台**打开的设备：启动 libusb 事件处理线程（Phase 1 埋的伏笔 `uvc_start_handler_thread` 在这里兑现）。
6. 挂进 `ctx->open_devices` 链表，返回 devh。

**拿到什么**：`uvc_device_handle_t *devh`——"控制台"。从这一刻起，Phase 4~9 的所有控制/流接口都要拿它当通行证。

**不做的后果**：不开门就喊话（跳过 open 直接调控制接口）→ 崩；重复 open 同一台 → `UVC_ERROR_BUSY`（同一上下文内）。

## 4. uvc_close：关门的顺序

```c
void uvc_close(uvc_device_handle_t *devh);   /* device.c:1722 */
```

按序做 5 件事：**停掉所有还在跑的流** → 释放 VC 接口（并尝试把内核驱动挂回去）→ 若是最后一台设备：停掉事件处理线程 → 关 libusb 句柄 → unref + free。

**注意**：即使你忘了 `uvc_stream_stop`，`uvc_close` 也会帮你停流（内部调用 `uvc_stop_streaming`）——但**不推荐依赖它**，显式 stop 才能控制时序。

**坑**：close 之后 devh、以及从这个 devh 派生的一切（流、帧）全部作废。任何持有旧指针的代码都是野指针。

## 5. 句柄互查与 uvc_wrap

```c
uvc_device_t *uvc_get_device(uvc_device_handle_t *devh);  /* 找回名片（自动 ref，用完要 unref） */
libusb_device_handle *uvc_get_libusb_handle(uvc_device_handle_t *devh); /* 底层句柄 */
```

- `uvc_get_libusb_handle` 的官方注释点名了它的用途：**访问同一设备上的其他接口**，比如摄像头自带的麦克风（UVC 只管视频，音频是另一个接口）。
- `uvc_wrap(sys_dev, ctx, &devh)`：你已经有一个平台级的系统句柄（如 Linux 上自己 open 的设备文件描述符）时，绕过查找直接包装。Windows 上极少用；注意系统句柄要等 uvc_close 之后才能关。

## 6. 事件回调：设备主动说话时

```c
void uvc_set_status_callback(uvc_device_handle_t *devh,
                             uvc_status_callback_t cb, void *user_ptr);
void uvc_set_button_callback(uvc_device_handle_t *devh,
                             uvc_button_callback_t cb, void *user_ptr);
```

| 回调 | 触发场景 | 参数拿到的数据 |
|------|---------|---------------|
| status_callback | 设备控制状态变化（如别的程序改了亮度，设备上报） | `status_class`（相机/处理单元）、`selector`（哪个控制变了）、`attribute`（值变/信息变/失败）、`data`+`data_len`（新值） |
| button_callback | 设备带物理按键（拍照键、变焦键）按下/松开 | `button`（哪个键）、`state`（按下/松开） |

两个细节：
1. **需要设备有状态中断端点**——open 时第 4 步挂的中断传输就是干这个的。没有该端点的设备（多数廉价摄像头）注册了也收不到。
2. `user_ptr` 会原样传回你的回调，用来把 C++ 对象 `this` 之类带进去。
3. 回调运行在 libusb 事件线程里，**不能调用任何 uvc_* 函数**（会死锁），只许做轻量记录。

## 7. 真实运行示例

本机演示（`demos/phase3_open_close.c`）：find → open（撞墙，打印真实错误 + 出路）→ 若成功则注册回调、演示句柄互查 → close → unref → exit。完整输出 `outputs/phase3_run.txt`。待 D1 解决后，成功路径会打印：

```
找到摄像头
摄像头已打开
已注册 status / button 回调
uvc_get_device 拿回同一台设备: 是
libusb 底层句柄: 0x...
设备已关闭（devh 已失效）
上下文已释放，程序结束
```

---

## 8. 本 Phase 小结

```
uvc_open(dev, &devh)  = 开门 + 读自述文件 + 占VC接口 + 挂状态侦听 + 开事件线程
devh = 控制台：Phase 4~9 所有接口的通行证
uvc_close(devh)       = 停流 → 还接口 → 关线程 → 关句柄 → 释放
```

自检清单：
- [ ] 能说出 uvc_open 内部 6 步流程（至少：解析描述符、claim、事件线程）
- [ ] 知道 Windows 内置摄像头报 NOT_SUPPORTED(-12) 的原因和三条出路（D1）
- [ ] 知道 uvc_close 会帮你停流，但 close 后一切指针作废
- [ ] 知道 status/button 回调依赖中断端点，回调里不能调 uvc_* 函数

下一步：Phase 4 能力查询——读那份"自述文件"：支持什么格式、什么控制。
