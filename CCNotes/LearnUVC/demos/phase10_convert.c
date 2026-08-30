/* Phase 10 演示：帧格式转换（uvc_any2rgb / uvc_any2bgr / uvc_yuyv2y）
 *
 * 本演示不需要摄像头！用一段手工构造的 YUYV 数据验证转换正确性，
 * 并输出 BMP 供肉眼检查。这是转换接口的"单元测试"式演示。
 *
 * YUYV 内存布局（关键）：每 2 像素 4 字节 [Y0, U, Y1, V]，
 * 即两个水平相邻像素共享同一个 U、V（4:2:2 色度抽样）。
 * 所以测试色块必须成对共享 UV：
 *   行0: [黑|白] (U=V=128)     [红|粉] (U=90,V=240)
 *   行1: [蓝|浅蓝] (U=240,V=110)  [绿|浅绿] (U=54,V=34)
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase10_convert.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase10_convert.exe
 */
#include <stdio.h>
#include <string.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

#define W 4
#define H 2

int main(void) {
  /* 1. 手工构造 4x2 YUYV 帧（library_owns_data = 0：数据缓冲我们自己提供）
   *    内存顺序：Y0 U Y1 V | Y0 U Y1 V | ... 行内从左到右、行间从上到下 */
  uint8_t img[2 * W * H] = {
    /* 行0: [黑|白] [红|粉] */
    16, 128, 235, 128,   81,  90, 180, 240,
    /* 行1: [蓝|浅蓝] [绿|浅绿] */
    41, 240, 160, 110,  145,  54, 190,  34,
  };

  uvc_frame_t in;
  memset(&in, 0, sizeof(in));
  in.data = img;
  in.data_bytes = sizeof(img);
  in.width = W;
  in.height = H;
  in.frame_format = UVC_FRAME_FORMAT_YUYV;
  in.library_owns_data = 0;    /* 告诉库：这个缓冲别动它 */

  /* 2. 转换到 RGB（库分配输出缓冲：library_owns_data=1） */
  uvc_frame_t *rgb = uvc_allocate_frame(0);
  uvc_error_t res = uvc_any2rgb(&in, rgb);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_any2rgb");
    uvc_free_frame(rgb);
    return 1;
  }

  printf("YUYV(%dx%d, %zu 字节) --uvc_any2rgb--> RGB(%dx%d, %zu 字节, step=%zu)\n\n",
         in.width, in.height, in.data_bytes,
         rgb->width, rgb->height, rgb->data_bytes, rgb->step);

  /* 3. 打印每个像素的 RGB 值。
   *    期望值 = BT.601 公式: R=Y+1.402*(V-128), G=Y-0.344*(U-128)-0.714*(V-128),
   *                          B=Y+1.772*(U-128)（超界截断到 0..255）
   *    无彩色 (U=V=128) 时 R=G=B=Y，即 黑=16、白=235 */
  const char *names[2][4] = {{"黑", "白", "红", "粉"}, {"蓝", "浅蓝", "绿", "浅绿"}};
  for (int y = 0; y < H; y++)
    for (int x = 0; x < W; x++) {
      uint8_t *px = (uint8_t *)rgb->data + y * rgb->step + x * 3;
      printf("  (%d,%d) %s: R=%3u G=%3u B=%3u\n", x, y, names[y][x],
             px[0], px[1], px[2]);
    }

  /* 4. 转换到 BGR 并保存 BMP（BMP 像素顺序正是 BGR） */
  uvc_frame_t *bgr = uvc_allocate_frame(0);
  if (uvc_any2bgr(&in, bgr) == UVC_SUCCESS) {
    write_bmp24("../outputs/phase10_test.bmp", bgr->data, bgr->width, bgr->height, bgr->step);
    printf("\nBGR 版已保存: outputs/phase10_test.bmp（用看图软件打开应看到 8 个色块）\n");
  }

  /* 5. 亮度提取：yuyv2y -> GRAY8（每像素取 Y 字节） */
  uvc_frame_t *gray = uvc_allocate_frame(0);
  if (uvc_yuyv2y(&in, gray) == UVC_SUCCESS) {
    printf("\nuvc_yuyv2y -> GRAY8 %ux%u: 亮度序列 = ", gray->width, gray->height);
    for (size_t i = 0; i < gray->data_bytes; i++)
      printf("%u ", ((uint8_t *)gray->data)[i]);
    printf("（应等于每个像素的 Y 值：16 235 81 180 41 160 145 190）\n");
  }

  /* 6. 错误路径：格式不匹配会怎样 */
  uvc_frame_t in_bad = in;
  in_bad.frame_format = UVC_FRAME_FORMAT_MJPEG;
  res = uvc_any2rgb(&in_bad, rgb);
  printf("\n对 MJPEG 帧调 uvc_any2rgb -> %s（本机 libuvc 未编入 JPEG 支持）\n",
         uvc_strerror(res));

  uvc_free_frame(rgb);
  uvc_free_frame(bgr);
  uvc_free_frame(gray);
  return 0;
}
