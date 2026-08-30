/* demos 公共工具：打开第一台摄像头 + BMP 保存
 * 所有 phaseX 演示程序均可 #include "uvc_demo_common.h" 使用。
 */
#ifndef UVC_DEMO_COMMON_H
#define UVC_DEMO_COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "libuvc/libuvc.h"

/* 打开第一台 UVC 摄像头：封装 find + open 两步，失败时打印诊断信息 */
static uvc_error_t open_first_camera(uvc_context_t *ctx,
                                     uvc_device_t **dev_out,
                                     uvc_device_handle_t **devh_out) {
  uvc_error_t res = uvc_find_device(ctx, dev_out, 0, 0, NULL);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_find_device");
    return res;
  }
  puts("找到摄像头");
  res = uvc_open(*dev_out, devh_out);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_open");
    return res;
  }
  puts("摄像头已打开");
  return UVC_SUCCESS;
}

/* 保存 24 位 BGR 数据为 BMP 文件（Windows 自带看图软件可直接打开）
 * 注意：BMP 的像素顺序正好是 BGR，与 uvc_any2bgr 的输出顺序一致。
 */
static int write_bmp24(const char *path, const uint8_t *bgr,
                       int width, int height, size_t step) {
  FILE *fp = fopen(path, "wb");
  if (!fp) return -1;

  int row_size = (width * 3 + 3) & ~3;   /* BMP 每行按 4 字节对齐 */
  int data_size = row_size * height;
  uint8_t hdr[54] = {0};
  hdr[0] = 'B'; hdr[1] = 'M';
  *(uint32_t *)(hdr + 2)  = 54 + data_size;  /* 文件总大小 */
  *(uint32_t *)(hdr + 10) = 54;              /* 像素数据偏移 */
  *(uint32_t *)(hdr + 14) = 40;              /* DIB 头大小 */
  *(int32_t *)(hdr + 18)  = width;
  *(int32_t *)(hdr + 22)  = height;          /* 正值 = 行序自下而上 */
  *(uint16_t *)(hdr + 26) = 1;               /* 色彩平面数 */
  *(uint16_t *)(hdr + 28) = 24;              /* 位深 */
  *(uint32_t *)(hdr + 34) = data_size;
  fwrite(hdr, 1, 54, fp);

  uint8_t pad[3] = {0, 0, 0};
  for (int y = height - 1; y >= 0; --y) {    /* BMP 行序：自下而上 */
    fwrite(bgr + (size_t)y * step, 1, (size_t)width * 3, fp);
    int padn = row_size - width * 3;
    if (padn) fwrite(pad, 1, padn, fp);
  }
  fclose(fp);
  return 0;
}

/* 帧格式枚举 -> 可读字符串 */
static const char *frame_format_name(enum uvc_frame_format f) {
  switch (f) {
  case UVC_FRAME_FORMAT_YUYV: return "YUYV";
  case UVC_FRAME_FORMAT_UYVY: return "UYVY";
  case UVC_FRAME_FORMAT_RGB:  return "RGB";
  case UVC_FRAME_FORMAT_BGR:  return "BGR";
  case UVC_FRAME_FORMAT_MJPEG:return "MJPEG";
  case UVC_FRAME_FORMAT_H264: return "H264";
  case UVC_FRAME_FORMAT_GRAY8:return "GRAY8";
  case UVC_FRAME_FORMAT_GRAY16:return "GRAY16";
  case UVC_FRAME_FORMAT_NV12: return "NV12";
  case UVC_FRAME_FORMAT_P010: return "P010";
  case UVC_FRAME_FORMAT_UNKNOWN: return "UNKNOWN";
  default: return "其他";
  }
}

#endif
