# Phase 7 · 帧获取（uvc_frame_t 逐字段 + 轮询/回调两种吃法）

> 对应主干链第 ⑧ 步——全流程的最终目的。学完本 Phase 你会：用轮询模式一帧帧拿图像，读懂帧结构里每个字段。
> 演示程序：`../demos/phase7_frame_capture.c`（需先解决 D1 才能实跑）

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 |
|------|------|------|-------------|
| `uvc_stream_get_frame` | 轮询取一帧 | 流句柄 + `timeout_us` | `uvc_frame_t *`（可能 NULL） |
| `uvc_allocate_frame` | 分配一个帧结构（可带数据缓冲） | `data_bytes` | `uvc_frame_t *` |
| `uvc_free_frame` | 释放帧 | 帧 | 无 |
| `uvc_duplicate_frame` | 深拷贝一帧 | 入帧 + 出帧 | 无（修改出帧） |

---

## 2. uvc_frame_t 逐字段（拿到手的就是它）

```c
typedef struct uvc_frame {
  void *data;                 /* ★ 像素数据本体 */
  size_t data_bytes;          /* 数据字节数 */
  uint32_t width;             /* 宽（像素） */
  uint32_t height;            /* 高（像素） */
  enum uvc_frame_format frame_format;  /* 编码格式（YUYV/MJPEG/...） */
  size_t step;                /* 一行的字节数（压缩格式为 0） */
  uint32_t sequence;          /* 帧序号：严格单调递增，但可能跳号 */
  struct timeval capture_time;         /* 设备开始采集的估计时间 */
  struct timespec capture_time_finished; /* 本机收完该帧的时间（CLOCK_MONOTONIC） */
  uvc_device_handle_t *source;  /* 产生此帧的设备 */
  uint8_t library_owns_data;    /* 数据缓冲归库所有？ */
  void *metadata;               /* 帧头附加元数据（可能 NULL） */
  size_t metadata_bytes;        /* 元数据字节数 */
} uvc_frame_t;
```

| 字段 | 怎么用它 | 注意 |
|------|---------|------|
| `data` / `data_bytes` | 图像本体。YUYV 时 data_bytes = width*height*2 | 只在本帧有效；轮询模式下取下一帧前会复用同一缓冲 |
| `step` | 计算像素地址：`data + y*step + x*每像素字节` | YUYV=width*2；压缩格式（MJPEG/H264）=0，不可按行寻址 |
| `sequence` | 检测丢帧（跳号） | 从 1 开始；不是 0 |
| `capture_time` | 需要"这一帧是什么时候拍的"时（如多机同步） | 是估计值 |
| `capture_time_finished` | 测延迟（收完时间 - 采集时间） | 单调时钟，不能转墙钟 |
| `source` | 多设备场景判断帧来自哪台 | 回调期间别用 |
| `library_owns_data` | 告诉你缓冲归谁管 | 你自己造帧时置 0（Phase 10 演示） |
| `metadata` | 设备在帧头附加的自定义信息 | UVC 1.5 才有的概念，多数设备为 NULL |

**最重要的一条**：轮询模式下返回的 `uvc_frame_t*` 指向**流句柄内部的可复用帧**——拿到手就尽快处理（或 `uvc_duplicate_frame` 复制走），下次调用会覆盖。回调模式下同理：回调返回后帧即失效。

## 3. 轮询模式：uvc_stream_get_frame

```c
uvc_error_t uvc_stream_get_frame(uvc_stream_handle_t *strmh,
                                 uvc_frame_t **frame, int32_t timeout_us);
```

| `timeout_us` | 行为 |
|--------------|------|
| `0` | 无限等待，直到新帧 |
| `>0` | 最多等 N 微秒；超时返回 `UVC_ERROR_TIMEOUT (-7)` |
| `-1` | 不等待：有新帧立即给，没新帧 `*frame=NULL` |

**拿到什么**：`*frame` 是新帧；**没有新帧时返回 NULL（但返回值仍是 SUCCESS）**——注意区分"成功但无帧"与"出错"。

**前提条件**（stream.c 源码）：
- 流必须已 start（否则 `UVC_ERROR_INVALID_PARAM`）
- **start 时 cb 必须传过 NULL**——回调模式下调 get_frame 返回 `UVC_ERROR_CALLBACK_EXISTS (-52)`。两条路二选一。

内部机制：内部有个"已派发序号"（last_polled_seq），同一帧不会重复给你；双缓冲 swap 时唤醒等待者（Phase 6 铺垫的锁/条件变量在这里派上用场）。

## 4. 回调模式 vs 轮询模式怎么选

| | 回调模式 | 轮询模式 |
|--|---------|---------|
| 代码形态 | 事件驱动：start 传 cb | 主循环：反复 get_frame |
| 适合 | 实时显示、需要与帧节奏同步 | 自己的处理循环节奏、保存 N 帧后退出 |
| 代价 | 回调必须快、不能调 uvc_* | 处理慢时帧在内部覆盖丢失 |

两条路**互斥**（CALLBACK_EXISTS 保护），选一条。

## 5. 帧的管理三件套

```c
uvc_frame_t *uvc_allocate_frame(size_t data_bytes); /* data_bytes=0 只建结构 */
void uvc_free_frame(uvc_frame_t *frame);
uvc_error_t uvc_duplicate_frame(uvc_frame_t *in, uvc_frame_t *out);
```

- allocate 出来的帧 `library_owns_data=1`，free 时连数据一起释放。
- **duplicate 是把库内部帧"抢救"出来的标准姿势**：深拷贝数据+全部元数据字段（含 metadata）。轮询/回调拿到帧后若想保存处理，复制一份最安全。
- duplicate 的 out 需要先 allocate（或自己 memset 一个 `library_owns_data=1` 的帧，库会帮你 realloc）。

## 6. 真实运行示例

`demos/phase7_frame_capture.c`（需 D1 解决后运行）：协商 → open_ctrl → **start(strmh, NULL, ...) 轮询模式** → 连取 5 帧逐字段打印 → 第一帧原始数据存 `outputs/phase7_first_frame.yuyv`。

预期输出形态（数值以真机为准）：

```
轮询模式已启动，开始取 5 帧……
第 1 帧 uvc_frame_t 逐字段:
  data          = 0000000000A7A0C0（像素数据本体）
  data_bytes    = 614400
  width/height  = 640x480
  frame_format  = YUYV
  step          = 1280（一行多少字节）
  sequence      = 1（帧序号，单调递增）
  capture_time  = 1725000000.123456（设备开始采集的估计时间）
  source        = ...（产生此帧的设备句柄）
  library_owns_data = 1（数据缓冲归库所有）
  metadata      = (nil) / 0 字节
  第一帧原始数据已存: outputs/phase7_first_frame.yuyv
```

**验证点**：data_bytes = 614400 = 640×480×2（YUYV），step = 1280 = 640×2，sequence 1→5 递增。用 hexdump 看 yuyv 文件头部应能看到有规律的数据（不是全 0）。

---

## 7. 本 Phase 小结

```
uvc_stream_get_frame(strmh, &f, timeout_us)
   ├─ -1 立即 / 0 无限 / >0 定时（超时返回 TIMEOUT）
   ├─ 无新帧 -> *f = NULL（返回仍是 SUCCESS）
   └─ 有新帧 -> *f 指向库内部复用帧，尽快用或 duplicate
uvc_frame_t 核心五件：data / data_bytes / width / height / frame_format
```

自检清单：
- [ ] 逐字段说得清 uvc_frame_t（至少：data、step、sequence、library_owns_data、metadata）
- [ ] 知道轮询/回调二选一（CALLBACK_EXISTS 保护）
- [ ] 知道帧是复用缓冲，保存要 duplicate
- [ ] 知道 timeout_us 三种取值语义、超时返回 TIMEOUT

下一步：Phase 8 通用控制底层——"遥控器"的万能通道 get_ctrl/set_ctrl。
