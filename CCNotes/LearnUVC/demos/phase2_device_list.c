/* Phase 2 演示：设备发现（uvc_get_device_list / uvc_find_device / 描述符 / 总线地址）
 *
 * 本演示不需要打开设备——枚举靠系统花名册，不碰驱动，任何机器都能跑。
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase2_device_list.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase2_device_list.exe
 */
#include <stdio.h>
#include <stdlib.h>
#include "libuvc/libuvc.h"

static void print_device(uvc_device_t *dev, int index) {
  uvc_device_descriptor_t *desc = NULL;

  if (uvc_get_device_descriptor(dev, &desc) != UVC_SUCCESS) {
    printf("设备[%d]: 描述符读取失败\n", index);
    return;
  }

  /* 注意：如果字符串取不到（比如设备被系统驱动独占时），这三个字段是 NULL */
  printf("设备[%d]\n", index);
  printf("  VID:PID     = %04x:%04x\n", desc->idVendor, desc->idProduct);
  printf("  bcdUVC      = %04x\n", desc->bcdUVC);
  printf("  序列号      = %s\n", desc->serialNumber ? desc->serialNumber : "(无)");
  printf("  厂家        = %s\n", desc->manufacturer  ? desc->manufacturer  : "(无)");
  printf("  产品名      = %s\n", desc->product       ? desc->product       : "(无)");
  printf("  总线/地址   = %d/%d\n", uvc_get_bus_number(dev), uvc_get_device_address(dev));

  uvc_free_device_descriptor(desc);
}

int main(void) {
  uvc_context_t *ctx;
  uvc_device_t **list;
  uvc_device_t *dev;
  uvc_error_t res;

  res = uvc_init(&ctx, NULL);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_init");
    return 1;
  }

  /* 1. 枚举全部 UVC 设备：list 是 NULL 结尾的指针数组 */
  res = uvc_get_device_list(ctx, &list);
  if (res != UVC_SUCCESS) {
    uvc_perror(res, "uvc_get_device_list");
    uvc_exit(ctx);
    return 1;
  }

  int count = 0;
  while (list[count] != NULL) {
    print_device(list[count], count);
    count++;
  }
  printf("共发现 %d 台 UVC 设备\n\n", count);

  /* 2. uvc_find_device：通配符 (0,0,NULL) = 拿第一台 */
  res = uvc_find_device(ctx, &dev, 0, 0, NULL);
  printf("uvc_find_device(0,0,NULL)      -> %s\n", uvc_strerror(res));

  /* 3. uvc_find_device：不存在的 VID -> 找不到 */
  res = uvc_find_device(ctx, &dev, 0xffff, 0xffff, NULL);
  printf("uvc_find_device(0xffff,0xffff) -> %s (%d)\n", uvc_strerror(res), res);

  /* 4. uvc_find_devices：找全部（通配），逐个打印后释放 */
  uvc_device_t **devs;
  res = uvc_find_devices(ctx, &devs, 0, 0, NULL);
  if (res == UVC_SUCCESS) {
    int n = 0;
    while (devs[n] != NULL) {
      uvc_device_descriptor_t *d;
      if (uvc_get_device_descriptor(devs[n], &d) == UVC_SUCCESS) {
        printf("uvc_find_devices 命中[%d]: %04x:%04x\n", n, d->idVendor, d->idProduct);
        uvc_free_device_descriptor(d);
      }
      uvc_unref_device(devs[n]);
      n++;
    }
    free(devs);
  }

  /* 5. 释放列表（第二个参数 1 = 逐个解除引用计数） */
  uvc_free_device_list(list, 1);

  uvc_exit(ctx);
  return 0;
}
