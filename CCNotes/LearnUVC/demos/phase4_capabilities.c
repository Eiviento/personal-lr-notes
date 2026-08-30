/* Phase 4 演示：能力查询（uvc_print_diag / 描述符遍历 / units / format_descs）
 *
 * 需要先 uvc_open 成功（见 phase3 的 D1 说明）。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase4_capabilities.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase4_capabilities.exe
 */
#include <stdio.h>
#include "libuvc/libuvc.h"
#include "uvc_demo_common.h"

static void print_guid(const uint8_t guid[16]) {
  for (int i = 0; i < 16; i++)
    printf("%02x", guid[i]);
}

static void print_format_descs(const uvc_format_desc_t *format) {
  while (format != NULL) {
    printf("  格式 %d: fourcc=%.4s bpp=%d 默认帧=%d\n",
           format->bFormatIndex, (char *)format->fourccFormat,
           format->bBitsPerPixel, format->bDefaultFrameIndex);
    printf("    GUID: ");
    print_guid(format->guidFormat);
    printf("\n");

    const uvc_frame_desc_t *frame = format->frame_descs;
    while (frame != NULL) {
      printf("    帧 %d: %ux%u 默认帧率 1/%u s",
             frame->bFrameIndex, frame->wWidth, frame->wHeight,
             10000000 / frame->dwDefaultFrameInterval);
      if (frame->intervals) {
        printf(" 可选帧率:");
        for (uint32_t *iv = frame->intervals; *iv; iv++)
          printf(" %ufps", 10000000 / *iv);
      } else {
        printf(" 帧率范围: %u~%u fps",
               10000000 / frame->dwMaxFrameInterval,
               10000000 / frame->dwMinFrameInterval);
      }
      printf("\n");
      frame = frame->next;
    }
    format = format->next;
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

  /* 1. 一键打印设备全部配置（官方诊断函数，输出到 stderr） */
  puts("\n===== uvc_print_diag 输出（stderr）=====");
  uvc_print_diag(devh, stderr);
  puts("===== uvc_print_diag 结束 =====\n");

  /* 2. 手动遍历格式/帧描述符（uvc_get_format_descs 返回链表头） */
  puts("===== 手动遍历 uvc_get_format_descs =====");
  print_format_descs(uvc_get_format_descs(devh));

  /* 3. Camera Terminal：传感器控制能力位图 */
  const uvc_input_terminal_t *cam = uvc_get_camera_terminal(devh);
  if (cam) {
    printf("\nCamera Terminal: ID=%d 类型=0x%04x\n", cam->bTerminalID, cam->wTerminalType);
    printf("  焦距范围: %u~%u mm\n", cam->wObjectiveFocalLengthMin, cam->wObjectiveFocalLengthMax);
    printf("  bmControls 位图: %016llx（bit 位 = CT 控制选择器编号）\n",
           (unsigned long long)cam->bmControls);
  } else {
    printf("\n无 Camera Terminal\n");
  }

  /* 4. Processing Unit：图像处理能力位图 */
  const uvc_processing_unit_t *pu = uvc_get_processing_units(devh);
  while (pu) {
    printf("Processing Unit: ID=%d 上游源ID=%d bmControls=%016llx\n",
           pu->bUnitID, pu->bSourceID, (unsigned long long)pu->bmControls);
    pu = pu->next;
  }

  /* 5. Extension Unit：厂商自定义（GUID 标识） */
  const uvc_extension_unit_t *xu = uvc_get_extension_units(devh);
  while (xu) {
    printf("Extension Unit: ID=%d GUID=", xu->bUnitID);
    print_guid(xu->guidExtensionCode);
    printf(" bmControls=%016llx\n", (unsigned long long)xu->bmControls);
    xu = xu->next;
  }

  uvc_close(devh);
  uvc_unref_device(dev);
  uvc_exit(ctx);
  return 0;
}
