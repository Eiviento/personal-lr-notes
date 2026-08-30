/* Phase 3 演示：打开与关闭（uvc_open / uvc_close / 事件回调 / 句柄互查）
 *
 * 注意（Windows）：内置摄像头被 usbvideo.sys 占用时，uvc_open 会返回
 * Access denied (-3)。解决办法见 lessons/phase3_open_close.md 的「检查点 D1」。
 * 换装 USBDK 驱动或插外置摄像头后，本程序无需修改即可完整运行。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase3_open_close.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase3_open_close.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

/* 状态变化回调：设备主动上报（比如别的程序改了亮度）时被调用 */
static void status_cb(enum uvc_status_class status_class, int event,
                      int selector, enum uvc_status_attribute status_attribute,
                      void *data, size_t data_len, void *user_ptr) {
  printf("[status_cb] class=%02x event=%d selector=%02x attr=%d len=%zu\n",
         status_class, event, selector, status_attribute, data_len);
}

/* 按键回调：设备带按钮（如拍照键）时，按下/松开会被调用 */
static void button_cb(int button, int state, void *user_ptr) {
  printf("[button_cb] button=%d state=%s\n", button, state ? "按下" : "松开");
}

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t *dev;
  uvc_device_handle_t *devh;
  uvc_error_t res;

  res = uvc_init(&ctx, NULL);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_init");
    return 1;
  }

  res = open_first_camera(ctx, &dev, &devh);
  if (res != UVC_SUCCESS) {
    /* 真实世界报错：设备被 usbvideo.sys 绑定时，libusb 的 WinUSB 后端打不开它。
     * 本机实测返回 Not supported (-12)；被独占时也可能是 Access denied (-3)。
     * 两种都说明：需要 USBDK 驱动或外置摄像头（见 lessons/phase3_open_close.md「检查点 D1」） */
    printf("\n打开失败（错误码见上面的 uvc_perror 输出）\n");
    printf("原因：设备被 Windows 系统驱动绑定，libusb 后端无法直接打开。\n");
    printf("解决：装 USBDK 驱动（推荐，与系统驱动共存）或插外置摄像头。\n");
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 1;
  }

  /* 1. 注册事件回调（devh 有效期内一直生效） */
  uvc_set_status_callback(devh, status_cb, NULL);
  uvc_set_button_callback(devh, button_cb, NULL);
  puts("已注册 status / button 回调");

  /* 2. 句柄互查：devh -> dev（自动 ref 计数 +1），devh -> libusb 句柄 */
  uvc_device_t *dev2 = uvc_get_device(devh);
  printf("uvc_get_device 拿回同一台设备: %s\n", dev2 == dev ? "是" : "否");
  uvc_unref_device(dev2); /* 用完要还 */

  printf("libusb 底层句柄: %p\n", (void *)uvc_get_libusb_handle(devh));

  /* 3. 关闭设备。之后 devh 及其派生物全部失效 */
  uvc_close(devh);
  puts("设备已关闭（devh 已失效）");

  /* 4. 释放"名片"的引用计数（find_device 时 +1 过） */
  uvc_unref_device(dev);

  uvc_exit(ctx);
  puts("上下文已释放，程序结束");
  return 0;
}
