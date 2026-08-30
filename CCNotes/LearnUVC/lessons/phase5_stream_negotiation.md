# Phase 5 · 流协商（Probe / Commit——签"合同"）

> 对应主干链第 ⑤ 步。学完本 Phase 你会：按格式+分辨率+帧率与摄像头谈判出一份流参数"合同"，并读懂合同上的每一项。
> 演示程序：`../demos/phase5_negotiate.c`（需先解决 D1 才能实跑）

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 |
|------|------|------|-------------|
| `uvc_get_stream_ctrl_format_size` | 一步到位：按 格式+宽高+fps 谈判 | devh + format + w + h + fps | `uvc_stream_ctrl_t` 合同 |
| `uvc_probe_stream_ctrl` | 手工 Probe（问，不生效） | devh + 合同 | 设备回填后的合同 |
| `uvc_stream_ctrl` | Commit（定，生效） | 流句柄 + 合同 | 无（更新流参数） |
| `uvc_get_still_ctrl_format_size` | 静态图像谈判（method-2 设备专用） | devh + 合同 + still 合同 + w + h | `uvc_still_ctrl_t` |
| `uvc_probe_still_ctrl` / `uvc_trigger_still` | 静态图 Probe / 触发拍摄 | — | — |
| `uvc_print_stream_ctrl` | 打印合同内容 | 合同 | 打到 FILE* |

---

## 2. 为什么需要"协商"？

你说"我要 640x480@30 的 YUYV"，摄像头未必恰好支持；就算支持，**一帧多大、每包多大**只有摄像头知道（取决于它的固件和端点配置）。所以 UVC 规范设计了两个控制（VS 接口上的"虚拟控制"）：

| 控制 | 类比 | 行为 |
|------|------|------|
| **Probe**（问） | 试穿 | 你把期望参数写进去，设备回答"实际会是什么样"，**不改变设备状态** |
| **Commit**（定） | 付款 | 把谈好的参数正式生效，流按此启动 |

一次典型协商 = 你出 3 个输入（格式/分辨率/帧率），设备回填 2 个关键输出：**dwMaxVideoFrameSize**（一帧最大字节数，分配缓冲的依据）和 **dwMaxPayloadTransferSize**（每包最大字节数，选 altsetting 的依据）。

## 3. 合同逐字段：uvc_stream_ctrl_t

```c
typedef struct uvc_stream_ctrl {
  uint16_t bmHint;            /* 协商提示位图：bit0=1 表示"帧间隔别给我改" */
  uint8_t  bFormatIndex;      /* 格式编号（来自菜单） */
  uint8_t  bFrameIndex;       /* 帧编号（来自菜单） */
  uint32_t dwFrameInterval;   /* 帧间隔，100ns 单位 */
  uint16_t wKeyFrameRate;     /* 关键帧率（压缩格式用） */
  uint16_t wPFrameRate;       /* P 帧率（压缩格式用） */
  uint16_t wCompQuality;      /* 压缩质量 1~10000 */
  uint16_t wCompWindowSize;   /* 压缩窗口 */
  uint16_t wDelay;            /* 采集延迟 */
  uint32_t dwMaxVideoFrameSize;     /* ★ 一帧最大字节数 */
  uint32_t dwMaxPayloadTransferSize;/* ★ 每包最大字节数 */
  uint32_t dwClockFrequency;  /* 设备时钟（UVC1.1+ 才有，否则取 VC 头值） */
  uint8_t  bmFramingInfo;     /* 组帧信息（UVC1.1+） */
  uint8_t  bPreferredVersion; /* 首选 UVC 版本（UVC1.1+） */
  uint8_t  bMinVersion;       /* 最低版本 */
  uint8_t  bMaxVersion;       /* 最高版本 */
  uint8_t  bInterfaceNumber;  /* 流接口号（libuvc 自己填） */
} uvc_stream_ctrl_t;
```

协议细节（stream.c `uvc_query_stream_ctrl`）：UVC 1.0/1.1 用 26 字节控制块，UVC 1.5 用 34 字节（多出时钟/组帧/版本 8 字节）。**你不用管字节序**——libuvc 负责打包拆包，你只读写上面的字段。

## 4. uvc_get_stream_ctrl_format_size：一步到位的谈判

```c
uvc_error_t uvc_get_stream_ctrl_format_size(uvc_device_handle_t *devh,
                                            uvc_stream_ctrl_t *ctrl,
                                            enum uvc_frame_format format,
                                            int width, int height, int fps);
```

**内部流程**（stream.c:470-538，建议对着源码读一遍）：

1. 遍历格式菜单，把 `format` 参数翻译成 GUID 去比对（YUYV/UYVY/MJPEG/GRAY8…都认得；`UVC_FRAME_FORMAT_ANY` = 随便）
2. 找到**宽高完全相等**的帧描述符（**严格相等**，不近似、不缩放）
3. 帧率匹配：离散表里找 `10000000/interval == fps`；连续范围里验证落在 min~max 且对齐步长；**fps 传 0 = 第一个可用帧率**
4. claim 流接口，`GET_MAX` 问出最大帧大小/包大小
5. 填好 `bmHint=bit0`（告诉设备"帧间隔别改"）、格式/帧索引、帧间隔
6. **Probe 一轮**（SET_CUR 写入 → GET_CUR 读回），校验设备没改格式/帧索引、包大小没超 → 成功

**拿到什么**：填好的 `uvc_stream_ctrl_t`——包含设备确认过的 `dwMaxVideoFrameSize` 和 `dwMaxPayloadTransferSize`。这张合同直接喂给 Phase 6 的建流接口。

**失败返回 `UVC_ERROR_INVALID_MODE (-14)`**：菜单里没有你要的组合。常见于"问设备要它没有的分辨率"。演示程序的兜底策略（用第一个格式的第一个帧）就是应对这个。

## 5. Probe / Commit 分步操作

快捷接口把两步包了，但拆开看更有教育意义：

```c
/* 手工构造一个"期望" */
ctrl.bFormatIndex = ...; ctrl.bFrameIndex = ...; ctrl.dwFrameInterval = ...;
/* ① Probe：问设备"你会给我什么" */
uvc_probe_stream_ctrl(devh, &ctrl);   /* ctrl 被设备回填 */
/* ② Commit：让参数生效（在 stream_open_ctrl 内部自动做） */
```

`uvc_probe_stream_ctrl` 内部（stream.c:609）：SET_CUR 写入你的期望 → GET_CUR 读回设备确认值 → 校验（格式/帧索引没变、包大小 ≤ 你的要求）→ 不通过返回 INVALID_MODE。

`uvc_stream_ctrl(strmh, ctrl)`（stream.c:392）就是 Commit：向设备发 SET_CUR，然后存进流句柄。它在 `uvc_stream_open_ctrl` 内部被自动调用，所以**日常代码里你几乎不用手写 Commit**。

## 6. 静态图像（大多数摄像头不支持）

method-2（流内静态图）设备的专用接口：`uvc_get_still_ctrl_format_size`（按宽高找 still 分辨率模式并 Probe）→ `uvc_probe_still_ctrl`（注意它内部**直接 Commit 了**，和流版 probe 语义不同，见 stream.c:631）→ `uvc_trigger_still`（流运行中发触发命令）。要求：设备声明 `bStillCaptureMethod == 2` 且流已在跑，否则 `UVC_ERROR_NOT_SUPPORTED`。

**结论**：普通网络摄像头基本用不上这条线；工业相机（如你的 HIKVISION）可能支持，届时按 phase5 演示里的调用试即可。

## 7. 真实运行示例

`demos/phase5_negotiate.c`（需 D1 解决后运行）逻辑：先谈 640x480@30 YUYV → 失败则用菜单第一项兜底 → `uvc_print_stream_ctrl` 打印合同 → 手工 probe 一轮 → 试静态图（预期 NOT_SUPPORTED）。

预期输出形态（数值以真机为准）：

```
协商成功，合同内容如下：
bmHint: 0001
bFormatIndex: 1
bFrameIndex: 3
dwFrameInterval: 333333        <- 30fps = 10000000/333333
...
dwMaxVideoFrameSize: 614400    <- 640*480*2（YUYV 每像素 2 字节）
dwMaxPayloadTransferSize: 3072 <- 每包 3KB
bInterfaceNumber: 1
```

**读合同的要领**：`dwMaxVideoFrameSize` ≈ 宽×高×每像素字节数（YUYV=2）就是佐证——640×480×2 = 614400。

---

## 8. 本 Phase 小结

```
菜单（Phase 4）──> uvc_get_stream_ctrl_format_size(格式,宽,高,fps)
                        │  内部 = 找匹配帧 + GET_MAX + Probe 一轮
                        ▼
                  合同 uvc_stream_ctrl_t
                        │  dwMaxVideoFrameSize / dwMaxPayloadTransferSize 是核心输出
                        ▼
                  喂给 uvc_stream_open_ctrl（Phase 6，内部自动 Commit）
```

自检清单：
- [ ] 能说出 Probe（问）与 Commit（定）的区别
- [ ] 能解释合同里 dwMaxVideoFrameSize / dwMaxPayloadTransferSize 的用途
- [ ] 知道宽高匹配是严格相等，失败返回 INVALID_MODE
- [ ] 知道帧间隔 100ns 单位，fps=0 表示"随便第一个"

下一步：Phase 6 流生命周期——按合同铺水管、开闸、关闸、拆管。
