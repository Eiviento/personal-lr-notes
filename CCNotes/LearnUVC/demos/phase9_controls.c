/* Phase 9 演示：高层相机控制族（ctrl-gen.c 生成的 get/set 对）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 * 覆盖最常用的几组：曝光 / 白平衡 / 图像质量。每组独立容错：
 * 设备不支持的控制会返回 PIPE 或 NOT_SUPPORTED，打印后继续。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase9_controls.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase9_controls.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

static void show(const char *label, uvc_error_t res) {
  printf("  %-28s -> %s\n", label, res == UVC_SUCCESS ? "成功" : uvc_strerror(res));
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

  /* ---- 曝光 ---- */
  printf("\n== 曝光 ==\n");
  uint8_t ae;
  res = uvc_get_ae_mode(devh, &ae, UVC_GET_CUR);
  if (res == UVC_SUCCESS)
    printf("  当前 AE 模式: %d (1=手动 2=自动 4=快门优先 8=光圈优先)\n", ae);

  uint32_t expo;
  res = uvc_get_exposure_abs(devh, &expo, UVC_GET_CUR);
  if (res == UVC_SUCCESS) printf("  曝光时间: %u (%u ms)\n", expo, expo / 10);

  /* 手动模式下调曝光，再读回验证 */
  if (uvc_set_ae_mode(devh, 1) == UVC_SUCCESS && uvc_get_exposure_abs(devh, &expo, UVC_GET_MAX) == UVC_SUCCESS) {
    uint32_t half = expo / 2;
    show("set_exposure_abs(一半)", uvc_set_exposure_abs(devh, half));
    uvc_get_exposure_abs(devh, &expo, UVC_GET_CUR);
    printf("  读回曝光: %u\n", expo);
  } else {
    printf("  (设备不支持手动曝光控制，跳过写入演示)\n");
  }

  /* ---- 白平衡 ---- */
  printf("\n== 白平衡 ==\n");
  uint16_t wb;
  if (uvc_get_white_balance_temperature(devh, &wb, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  色温当前值: %u K\n", wb);
  if (uvc_get_white_balance_temperature(devh, &wb, UVC_GET_MIN) == UVC_SUCCESS)
    printf("  色温最小值: %u K\n", wb);
  if (uvc_get_white_balance_temperature(devh, &wb, UVC_GET_MAX) == UVC_SUCCESS)
    printf("  色温最大值: %u K\n", wb);

  uint8_t auto_wb;
  if (uvc_get_white_balance_temperature_auto(devh, &auto_wb, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  自动白平衡: %s\n", auto_wb ? "开" : "关");

  uint16_t blue, red;
  if (uvc_get_white_balance_component(devh, &blue, &red, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  分量白平衡: 蓝=%u 红=%u\n", blue, red);

  /* ---- 图像质量（PU 组，每个都容错）---- */
  printf("\n== 图像质量 (Processing Unit) ==\n");
  int16_t brightness;
  if (uvc_get_brightness(devh, &brightness, UVC_GET_CUR) == UVC_SUCCESS) {
    printf("  亮度: %d（最小/最大见 GET_MIN/GET_MAX）\n", brightness);
    show("set_brightness(+10)", uvc_set_brightness(devh, brightness + 10));
    uvc_get_brightness(devh, &brightness, UVC_GET_CUR);
    printf("  写后读回: %d\n", brightness);
    uvc_set_brightness(devh, brightness - 10);  /* 恢复 */
  }

  uint16_t contrast;
  if (uvc_get_contrast(devh, &contrast, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  对比度: %u\n", contrast);

  uint16_t gain;
  if (uvc_get_gain(devh, &gain, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  增益: %u\n", gain);

  uint16_t saturation;
  if (uvc_get_saturation(devh, &saturation, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  饱和度: %u\n", saturation);

  uint16_t sharpness;
  if (uvc_get_sharpness(devh, &sharpness, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  锐度: %u\n", sharpness);

  uint16_t gamma;
  if (uvc_get_gamma(devh, &gamma, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  伽马: %u\n", gamma);

  int16_t hue;
  if (uvc_get_hue(devh, &hue, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  色相: %d\n", hue);

  uint16_t backlight;
  if (uvc_get_backlight_compensation(devh, &backlight, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  背光补偿: %u\n", backlight);

  /* ---- 其他 ---- */
  printf("\n== 其他 ==\n");
  uint8_t plf;
  if (uvc_get_power_line_frequency(devh, &plf, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  电源频率(防闪烁): %d (0=关闭 1=50Hz 2=60Hz)\n", plf);

  uint16_t zoom;
  if (uvc_get_zoom_abs(devh, &zoom, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  焦距(变焦): %u\n", zoom);
  else
    printf("  焦距(变焦): 不支持（定焦摄像头）\n");

  uint8_t privacy;
  if (uvc_get_privacy(devh, &privacy, UVC_GET_CUR) == UVC_SUCCESS)
    printf("  隐私(镜头盖): %s\n", privacy ? "开" : "关");

  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
