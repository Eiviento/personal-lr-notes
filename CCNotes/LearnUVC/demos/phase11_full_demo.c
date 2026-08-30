/* Phase 11 演示：综合实战——完整调用链 + 定时存 BMP
 *
 * 主干链全流程：init -> find -> open -> print_diag -> 协商 -> start_streaming(回调)
 *              -> 流中改控制 -> stop_streaming -> close -> unref -> exit
 * 回调里每 30 帧转 BGR 存一张 BMP，运行 5 秒大约能存 5 张。
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase11_full_demo.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase11_full_demo.exe
 */
#include <stdio.h>
#ifdef _WIN32
#include <windows.h>
#define SLEEP_MS(ms) Sleep(ms)
#else
#include <unistd.h>
#define SLEEP_MS(ms) usleep((ms) * 1000)
#endif
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

static int saved = 0;

/* 帧回调：每 30 帧转 BGR 存 BMP。
 * 注意：回调里不能调用 uvc_* 函数——转换函数(u_any2bgr)可以，控制/流函数不行。 */
static void frame_cb(uvc_frame_t *frame, void *user_ptr) {
  if (frame->sequence % 30 != 0)
    return;

  uvc_frame_t *bgr = uvc_allocate_frame(0);
  if (uvc_any2bgr(frame, bgr) == UVC_SUCCESS) {
    char path[64];
    snprintf(path, sizeof(path), "../outputs/phase11_frame_%04u.bmp", frame->sequence);
    if (write_bmp24(path, bgr->data, bgr->width, bgr->height, bgr->step) == 0) {
      saved++;
      printf("已保存 %s (%ux%u)\n", path, bgr->width, bgr->height);
    }
  }
  uvc_free_frame(bgr);
}

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t *dev;
  uvc_device_handle_t *devh;
  uvc_stream_ctrl_t ctrl;
  uvc_error_t res;

  /* ① 工作台 */
  res = uvc_init(&ctx, NULL);
  if (res < 0) { uvc_perror(res, "uvc_init"); return res; }
  puts("UVC initialized");

  /* ②③ 名片 + 控制台 */
  res = uvc_find_device(ctx, &dev, 0, 0, NULL);
  if (res < 0) { uvc_perror(res, "uvc_find_device"); uvc_exit(ctx); return res; }
  puts("Device found");

  res = uvc_open(dev, &devh);
  if (res < 0) { uvc_perror(res, "uvc_open"); uvc_unref_device(dev); uvc_exit(ctx); return res; }
  puts("Device opened");

  /* ④ 自述文件 */
  uvc_print_diag(devh, stderr);

  /* ⑤ 谈判 */
  res = uvc_get_stream_ctrl_format_size(devh, &ctrl,
                                        UVC_FRAME_FORMAT_YUYV, 640, 480, 30);
  if (res != UVC_SUCCESS) {
    const uvc_format_desc_t *format = uvc_get_format_descs(devh);
    const uvc_frame_desc_t *frame = format->frame_descs;
    printf("640x480@30 不可用，改用 %ux%u@%u\n",
           frame->wWidth, frame->wHeight,
           10000000 / frame->dwDefaultFrameInterval);
    res = uvc_get_stream_ctrl_format_size(devh, &ctrl, UVC_FRAME_FORMAT_YUYV,
                                          frame->wWidth, frame->wHeight,
                                          10000000 / frame->dwDefaultFrameInterval);
  }
  if (res < 0) { uvc_perror(res, "协商失败"); goto cleanup; }
  uvc_print_stream_ctrl(&ctrl, stderr);

  /* ⑥⑦ 快捷组合：建流 + 开闸（内部 = open_ctrl + start） */
  res = uvc_start_streaming(devh, &ctrl, frame_cb, NULL, 0);
  if (res < 0) { uvc_perror(res, "uvc_start_streaming"); goto cleanup; }
  puts("Streaming...（每 30 帧存一张 BMP，共 5 秒）");

  /* ⑧（变体）流中改控制：证明控制线与数据线可以并行 */
  uint8_t ae_mode;
  if (uvc_get_ae_mode(devh, &ae_mode, UVC_GET_CUR) == UVC_SUCCESS)
    printf("流中读取 AE 模式: %d\n", ae_mode);

  SLEEP_MS(5000);

  /* ⑨⑩⑪ */
  uvc_stop_streaming(devh);
  printf("Done streaming，共保存 %d 张 BMP（见 outputs/）\n", saved);

cleanup:
  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  puts("UVC exited");
  return 0;
}
