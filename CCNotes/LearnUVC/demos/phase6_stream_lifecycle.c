/* Phase 6 演示：流生命周期（stream_open_ctrl / stream_start / stream_stop / stream_close）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 * 采用回调模式：uvc_stream_start 传回调函数，libuvc 开一个内部线程逐个喂帧。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase6_stream_lifecycle.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase6_stream_lifecycle.exe
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

static int frame_count = 0;

/* 帧回调：运行在 libuvc 的内部线程里。
 * 警告（官方头文件）：回调期间不能调用任何 uvc_* 函数（会死锁）！ */
static void frame_cb(uvc_frame_t *frame, void *user_ptr) {
  frame_count++;
  if (frame_count <= 3) {
    printf("  收到帧 %u: %s %ux%u, %zu 字节\n",
           frame->sequence, frame_format_name(frame->frame_format),
           frame->width, frame->height, frame->data_bytes);
  }
}

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

  /* 1. 协商（先试 640x480@30 YUYV，不行就用第一个格式） */
  res = uvc_get_stream_ctrl_format_size(devh, &ctrl,
                                        UVC_FRAME_FORMAT_YUYV, 640, 480, 30);
  if (res != UVC_SUCCESS) {
    const uvc_format_desc_t *format = uvc_get_format_descs(devh);
    const uvc_frame_desc_t *frame = format->frame_descs;
    res = uvc_get_stream_ctrl_format_size(devh, &ctrl, UVC_FRAME_FORMAT_YUYV,
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

  /* 2. 建流：拿到水管 strmh（内部 commit 合同 + 分配双缓冲） */
  res = uvc_stream_open_ctrl(devh, &strmh, &ctrl);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_stream_open_ctrl"); goto cleanup; }
  puts("流已建立（合同已 commit）");

  /* 3. 开闸：注册回调，开始收帧 */
  res = uvc_stream_start(strmh, frame_cb, NULL, 0);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_stream_start"); goto cleanup; }
  puts("流已启动，收帧 3 秒……");

  SLEEP_MS(3000);
  printf("3 秒共收到 %d 帧（约 %.1f fps）\n", frame_count, frame_count / 3.0);

  /* 4. 关闸：取消传输、等回调线程退出 */
  res = uvc_stream_stop(strmh);
  printf("uvc_stream_stop -> %s\n", uvc_strerror(res));

  /* 5. 拆管：释放接口与全部缓冲 */
  uvc_stream_close(strmh);
  puts("流已关闭");

cleanup:
  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
