# Phase 10 · 帧格式转换（YUYV → RGB/BGR/灰度）

> 把摄像头吐出的原始编码变成能显示、能存盘的格式。本 Phase 的演示**不需要摄像头**（手工构造测试帧），已在本机真实运行验证。
> 演示程序：`../demos/phase10_convert.c`，真实运行输出：`../outputs/phase10_run.txt`，产物：`../outputs/phase10_test.bmp`

---

## 1. 为什么需要转换

摄像头几乎不发 RGB。家用摄像头最常见的输出是 **YUYV**（未压缩）或 **MJPEG**（压缩）。前者的原始字节直接存盘没人能看，必须先转成 RGB/BGR。libuvc 把这活内置了（frame.c）。

## 2. 接口一览

| 接口 | 作用 | 输入格式 | 输出 |
|------|------|---------|------|
| `uvc_any2rgb` | 一键转 RGB | YUYV/UYVY/RGB（+MJPEG 若有 jpeg） | RGB 帧（每像素 3 字节，step=w*3） |
| `uvc_any2bgr` | 一键转 BGR | YUYV/UYVY/BGR | BGR 帧 |
| `uvc_yuyv2rgb` / `uvc_uyvy2rgb` | 定向转换 | 各自格式 | RGB 帧 |
| `uvc_yuyv2bgr` / `uvc_uyvy2bgr` | 定向转换 | 各自格式 | BGR 帧 |
| `uvc_yuyv2y` | 提亮度 | YUYV | GRAY8（每像素 1 字节，step=w） |
| `uvc_yuyv2uv` | 提色度 | YUYV | GRAY8（**实际只取 U 字节**，见坑 3） |
| `uvc_mjpeg2rgb` / `uvc_mjpeg2gray` | MJPEG 解码 | MJPEG | RGB / GRAY8（**需编译时带 libjpeg**） |

调用形态高度统一：

```c
uvc_frame_t *out = uvc_allocate_frame(0);  /* 库会自己 realloc 出够大的缓冲 */
uvc_any2rgb(in, out);
/* 用 out->data / out->data_bytes / out->step ... */
uvc_free_frame(out);
```

- 输出帧的 `library_owns_data` 必须是 1（allocate_frame 已设置）——转换函数内部 `uvc_ensure_frame_size` 据此决定能否 realloc。
- 输出帧的 width/height/sequence/capture_time 等元数据会被原样带上（frame.c 每个转换函数都复制一遍）。

## 3. 原理：BT.601 与定点数加速

转换公式（ITU-R BT.601）：

```
R = Y + 1.402*(V-128)
G = Y - 0.344*(U-128) - 0.714*(V-128)
B = Y + 1.772*(U-128)
```

但浮点太慢（一帧 30 万像素 × 每个 5 次浮点运算）。libuvc 用**定点数**：系数 ×2^14 取整，乘法后右移 14 位：

```c
#define IYUYV2RGB_2(pyuv, prgb) { \
    int r = (22987 * ((pyuv)[3] - 128)) >> 14; \       /* 1.402 * 2^14 = 22987 */
    ...
```

误差 ≤1/16384，肉眼不可见，速度快一个数量级。（详细剖析见旧笔记 11.1 节。）

## 4. 坑

**坑 1（本演示亲身踩过）：YUYV 字节序是 [Y0, U, Y1, V]，不是 [Y0, U, V, Y1]。**
每 4 字节编码**两个**像素，共享 U、V（4:2:2 色度抽样）——即"每对水平相邻像素共用一组色度"。我第一次构造测试帧写错了顺序，8 个色块的 RGB 全乱。这也意味着：**红和绿不能在 YUYV 里相邻成对**（它们需要不同的 U/V）。正确的测试帧必须同 UV 成对（黑|白、红|粉…）。

**坑 2：any2rgb 认的格式有限。** 分发表只有 YUYV/UYVY/RGB（+MJPEG 若有 jpeg）。传 NV12、GRAY8 等 → `UVC_ERROR_NOT_SUPPORTED (-12)`。NV12 需要自己写转换或用 OpenCV。

**坑 3：uvc_yuyv2uv 其实只取 U。** 看宏定义：`(puv)[0] = (pyuv)[1]`——pyuv[1] 是 U 字节，V（pyuv[3]）被扔了。名字叫"uv"，实际输出的是 U 平面。用它做色度分析时要心里有数。

**坑 4：MJPEG 需要 libjpeg。** libuvc 编译时找不到 libjpeg 就不编 frame-mjpeg.c，`uvc_mjpeg2rgb` 直接不存在（头文件里 `#ifdef LIBUVC_HAS_JPEG` 包着）。本机构建就是这种情况——`any2rgb(MJPEG)` 返回 NOT_SUPPORTED（见真实输出）。需要的话从 MSYS2 镜像装 libjpeg-turbo 重编（findings.md 有记录）。

**坑 5：转换是 CPU 活，不在回调里做重活。** 一帧 640x480 转 RGB 约几毫秒，可行但别在回调里转 4K。

## 5. 真实运行示例（本机已实跑）

`demos/phase10_convert.c` 构造 4x2 YUYV 测试图（黑|白、红|粉、蓝|浅蓝、绿|浅绿，8 个 BT.601 标准色），然后 any2rgb / any2bgr 存 BMP / yuyv2y / 错误路径，全程不需要摄像头。

**真实输出**（`outputs/phase10_run.txt`，节选）：

```
YUYV(4x2, 16 字节) --uvc_any2rgb--> RGB(4x2, 24 字节, step=12)

  (0,0) 黑: R= 16 G= 16 B= 16
  (1,0) 白: R=235 G=235 B=235
  (2,0) 红: R=238 G= 14 B= 13
  (3,0) 粉: R=255 G=113 B=112
  (0,1) 蓝: R= 15 G= 15 B=239
  ...
uvc_yuyv2y -> GRAY8 4x2: 亮度序列 = 16 235 81 180 41 160 145 190
  （应等于每个像素的 Y 值：16 235 81 180 41 160 145 190）
对 MJPEG 帧调 uvc_any2rgb -> Not supported（本机 libuvc 未编入 JPEG 支持）
```

**验证点**：
- 黑=(16,16,16)、白=(235,235,235)：无彩色时 R=G=B=Y ✓
- 红=(238,14,13)：套 BT.601 公式手算一致 ✓
- 亮度序列与输入 Y 值逐一吻合 ✓
- `outputs/phase10_test.bmp`（78 字节 = 54 头 + 4×2×3 数据）用看图软件打开可见 8 个色块

**顺带学到的**：BMP 的像素顺序恰好是 BGR——所以 `uvc_any2bgr` 的输出可以直接写 BMP（Phase 11 就是这么存图的）。

---

## 6. 本 Phase 小结

```
原始帧(YUYV/UYVY/MJPEG) ──uvc_any2rgb/any2bgr──> 可显示/可存盘帧
         └──uvc_yuyv2y──> GRAY8（机器视觉常用）
调用形态：allocate_frame(0) → 转换 → 用 → free_frame
```

自检清单：
- [ ] 能默写 YUYV 字节序 [Y0,U,Y1,V] 和"每对像素共享 UV"的含义
- [ ] 知道 any2rgb 支持的格式清单，NV12 要自己转
- [ ] 知道 yuyv2uv 实际只取 U
- [ ] 知道 MJPEG 依赖 libjpeg 编译选项
- [ ] 知道 BMP=BGR 顺序这个便利

下一步：Phase 11 综合实战——完整程序 + 全部接口速查表定稿。
