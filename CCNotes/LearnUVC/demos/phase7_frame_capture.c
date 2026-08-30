/* Phase 7 演示：帧获取（uvc_stream_get_frame 轮询模式 + uvc_frame_t 逐字段）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 * 与 phase6 的区别：stream_start 时回调传 NULL -> 轮询模式，由本程序主循环取帧。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase7_frame_capture.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase7_frame_capture.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t *dev;
  uvc_device_handle_t *devh;
  uvc_stream_handle_t *strmh = NULL;
  uvc_stream_ctrl_t ctrl;
  uvc_error_t res;

  res = uvc_init(&ctx, NULL);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_init"); return 1; }

  res = open_first_camera(ctx, &dev, &devh);
  if (res != UVC_SUCCESS) {
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 1;
  }

  res = uvc_get_stream_ctrl_format_size(devh, &ctrl,
                                        UVC_FRAME_FORMAT_YUYV, 640, 480, 30);
  if (res != UVC_SUCCESS) {
    const uvc_format_desc_t *format = uvc_get_format_descs(devh);
    const uvc_frame_desc_t *frame = format->frame_descs;
    res = uvc_get_stream_ctrl_format_size(devh, &ctrl, UVC_FRAME_FORMAT_YUYV,
                                          frame->wWidth, frame->wHeight,
                                          10000000 / frame->dwDefaultFrameInterval);
  }
  if (res != UVC_SUCCESS) { uvc_perror(res, "协商失败"); goto cleanup; }

  res = uvc_stream_open_ctrl(devh, &strmh, &ctrl);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_stream_open_ctrl"); goto cleanup; }

  /* 关键：cb 传 NULL -> 轮询模式（不能用回调模式同时轮询，否则 CALLBACK_EXISTS） */
  res = uvc_stream_start(strmh, NULL, NULL, 0);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_stream_start"); goto cleanup; }
  puts("轮询模式已启动，开始取 5 帧……");

  for (int i = 0; i < 5; i++) {
    uvc_frame_t *frame = NULL;

    /* timeout_us = 5000000：最多等 5 秒；0 = 无限等；-1 = 不等待立即返回 */
    res = uvc_stream_get_frame(strmh, &frame, 5000000);
    if (res == UVC_ERROR_TIMEOUT) {
      printf("第 %d 帧: 超时（5 秒内没有新帧）\n", i + 1);
      continue;
    }
    if (res != UVC_SUCCESS || frame == NULL) {
      uvc_perror(res, "uvc_stream_get_frame");
      break;
    }

    printf("第 %d 帧 uvc_frame_t 逐字段:\n", i + 1);
    printf("  data          = %p（像素数据本体）\n", frame->data);
    printf("  data_bytes    = %zu\n", frame->data_bytes);
    printf("  width/height  = %ux%u\n", frame->width, frame->height);
    printf("  frame_format  = %s\n", frame_format_name(frame->frame_format));
    printf("  step          = %zu（一行多少字节）\n", frame->step);
    printf("  sequence      = %u（帧序号，单调递增）\n", frame->sequence);
    printf("  capture_time  = %ld.%06ld（设备开始采集的估计时间）\n",
           (long)frame->capture_time.tv_sec, (long)frame->capture_time.tv_usec);
    printf("  source        = %p（产生此帧的设备句柄）\n", (void *)frame->source);
    printf("  library_owns_data = %u（数据缓冲归库所有）\n", frame->library_owns_data);
    printf("  metadata      = %p / %zu 字节\n", frame->metadata, frame->metadata_bytes);

    if (i == 0) {
      FILE *fp = fopen("../outputs/phase7_first_frame.yuyv", "wb");
      if (fp) {
        fwrite(frame->data, 1, frame->data_bytes, fp);
        fclose(fp);
        printf("  第一帧原始数据已存: outputs/phase7_first_frame.yuyv\n");
      }
    }
    printf("\n");
  }

  uvc_stream_stop(strmh);
  uvc_stream_close(strmh);
  puts("流已停止并关闭");

cleanup:
  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
