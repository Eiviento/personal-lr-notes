/* Phase 5 演示：流协商（uvc_get_stream_ctrl_format_size / uvc_probe_stream_ctrl）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase5_negotiate.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase5_negotiate.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t *dev;
  uvc_device_handle_t *devh;
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

  /* 1. 首选：YUYV 640x480@30 */
  res = uvc_get_stream_ctrl_format_size(devh, &ctrl,
                                        UVC_FRAME_FORMAT_YUYV, 640, 480, 30);
  if (res != UVC_SUCCESS) {
    printf("640x480@30 YUYV 不可用 (%s)，退而求其次：用第一个格式的第一个帧\n",
           uvc_strerror(res));

    /* 兜底：读描述符菜单，取第一项 */
    const uvc_format_desc_t *format = uvc_get_format_descs(devh);
    const uvc_frame_desc_t *frame = format->frame_descs;
    enum uvc_frame_format fmt =
        format->fourccFormat[0] == 'M' ? UVC_FRAME_FORMAT_MJPEG : UVC_FRAME_FORMAT_YUYV;
    res = uvc_get_stream_ctrl_format_size(devh, &ctrl, fmt,
                                          frame->wWidth, frame->wHeight,
                                          10000000 / frame->dwDefaultFrameInterval);
  }

  if (res != UVC_SUCCESS) {
    uvc_perror(res, "协商失败");
    uvc_close(devh);
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 1;
  }

  /* 2. 看合同内容：uvc_print_stream_ctrl 打印全部字段 */
  printf("协商成功，合同内容如下：\n");
  uvc_print_stream_ctrl(&ctrl, stdout);

  /* 3. 手工 Probe 一遍：probe = "问"（不生效），合同字段会被设备回填 */
  printf("\n手工 uvc_probe_stream_ctrl 再问一次 -> %s\n",
         uvc_strerror(uvc_probe_stream_ctrl(devh, &ctrl)));
  uvc_print_stream_ctrl(&ctrl, stdout);

  /* 4. 静态图像协商（只有支持 method-2 的设备才有；大多数摄像头不支持） */
  uvc_stream_ctrl_t stream_ctrl2 = ctrl;
  uvc_still_ctrl_t still_ctrl;
  res = uvc_get_still_ctrl_format_size(devh, &stream_ctrl2, &still_ctrl, 640, 480);
  printf("\nuvc_get_still_ctrl_format_size(640x480) -> %s（多数摄像头不支持）\n",
         uvc_strerror(res));

  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
