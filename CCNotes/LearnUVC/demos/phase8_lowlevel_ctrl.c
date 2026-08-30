/* Phase 8 演示：通用控制底层（uvc_get_ctrl_len / uvc_get_ctrl / uvc_set_ctrl + 电源）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 * 用万能通道直接读"曝光时间绝对值"的 长度/当前值/最小值/最大值/分辨率/默认值。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase8_lowlevel_ctrl.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase8_lowlevel_ctrl.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

/* 万能读：GET_CUR/MIN/MAX/RES/DEF 一次打包演示 */
static void demo_ctrl(uvc_device_handle_t *devh, uint8_t unit_id,
                      uint8_t selector, const char *name) {
  uint8_t buf[16];
  int n, len;

  len = uvc_get_ctrl_len(devh, unit_id, selector);
  if (len <= 0) {
    printf("[%s] 设备不支持 (get_ctrl_len -> %s)\n", name, uvc_strerror(len));
    return;
  }

  struct { enum uvc_req_code code; const char *label; } reqs[] = {
    {UVC_GET_CUR, "GET_CUR 当前值"},
    {UVC_GET_MIN, "GET_MIN 最小值"},
    {UVC_GET_MAX, "GET_MAX 最大值"},
    {UVC_GET_RES, "GET_RES 分辨率"},
    {UVC_GET_DEF, "GET_DEF 默认值"},
  };

  printf("[%s] 数据长度 %d 字节:\n", name, len);
  for (size_t i = 0; i < sizeof(reqs) / sizeof(reqs[0]); i++) {
    n = uvc_get_ctrl(devh, unit_id, selector, buf, len, reqs[i].code);
    if (n < 0) {
      printf("  %-20s -> %s\n", reqs[i].label, uvc_strerror(n));
      continue;
    }
    uint32_t value = 0;
    for (int b = 0; b < n && b < 4; b++)
      value |= (uint32_t)buf[b] << (8 * b);   /* 小端解码 */
    printf("  %-20s -> %u（原始字节:", reqs[i].label, value);
    for (int b = 0; b < n; b++) printf(" %02x", buf[b]);
    printf("）\n");
  }
}

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t *dev;
  uvc_device_handle_t *devh;
  uvc_error_t res;

  res = uvc_init(&ctx, NULL);
  if (res != UVC_SUCCESS) { uvc_perror(res, "uvc_init"); return 1; }

  res = open_first_camera(ctx, &dev, &devh);
  if (res != UVC_SUCCESS) {
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 1;
  }

  /* 寻址三要素：unit ID（camera terminal）+ 控制选择器 + 请求码 */
  const uvc_input_terminal_t *cam = uvc_get_camera_terminal(devh);
  if (!cam) {
    printf("无 Camera Terminal，无法演示\n");
    uvc_close(devh);
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 1;
  }
  printf("Camera Terminal ID = %d\n\n", cam->bTerminalID);

  /* 1. 曝光时间绝对值（CT 选择器 0x04） */
  demo_ctrl(devh, cam->bTerminalID, UVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL, "曝光时间(绝对值)");

  /* 2. 缩放绝对值（CT 选择器 0x0b，多数定焦摄像头不支持） */
  demo_ctrl(devh, cam->bTerminalID, UVC_CT_ZOOM_ABSOLUTE_CONTROL, "焦距(变焦)");

  /* 3. 万能 set：把曝光当前值原样写回（无副作用的安全演示） */
  uint8_t buf[4];
  int len = uvc_get_ctrl_len(devh, cam->bTerminalID, UVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL);
  if (len > 0) {
    int n = uvc_get_ctrl(devh, cam->bTerminalID, UVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL,
                         buf, len, UVC_GET_CUR);
    if (n > 0) {
      int s = uvc_set_ctrl(devh, cam->bTerminalID, UVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL,
                           buf, len);
      printf("\nuvc_set_ctrl(曝光, 写回当前值) -> %s\n", s >= 0 ? "成功" : uvc_strerror(s));
    }
  }

  /* 4. 电源模式：VC 接口级控制（注意 wIndex 不带 unit ID） */
  enum uvc_device_power_mode mode;
  res = uvc_get_power_mode(devh, &mode, UVC_GET_CUR);
  if (res == UVC_SUCCESS) {
    printf("电源模式: %s\n", mode == UVC_VC_VIDEO_POWER_MODE_FULL ? "FULL" : "DEVICE_DEPENDENT");
    res = uvc_set_power_mode(devh, mode);
    printf("uvc_set_power_mode(写回) -> %s\n", uvc_strerror(res));
  } else {
    printf("电源模式: 设备不支持 (%s)\n", uvc_strerror(res));
  }

  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
