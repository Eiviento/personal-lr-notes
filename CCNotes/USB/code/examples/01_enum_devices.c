/* ============================================================
 * 01_enum_devices.c —— 枚举设备（抄内核花名册）
 *
 * 学什么:  libusb_get_device_list 与协议枚举的区别——这是"抄花名册"，
 *          不是"入职面试"（面试是内核在设备插入时完成的）
 * 对应知识点: KB 第九篇 §9.2（设备列表 ≠ 协议枚举）
 * 编译:    gcc -o enum_devices 01_enum_devices.c -lusb-1.0
 * 运行:    sudo ./enum_devices [VID PID]   （不带参数 = 列出全部）
 * 预期:    列出全部设备；带 2bdf 0101 时高亮海康热成像
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device **devs;
    ssize_t cnt, i;
    int target_vid = -1, target_pid = -1;   /* -1 = 不过滤 */

    if (argc == 3) {
        target_vid = (int)strtol(argv[1], NULL, 16);
        target_pid = (int)strtol(argv[2], NULL, 16);
    } else if (argc != 1) {
        printf("用法: %s [VID PID]\n", argv[0]);
        return 1;
    }

    if (libusb_init(&ctx) < 0) { perror("libusb_init"); return 1; }

    cnt = libusb_get_device_list(ctx, &devs);   /* ★ 抄花名册（零总线流量） */
    if (cnt < 0) { fprintf(stderr, "get_device_list: %s\n", libusb_error_name((int)cnt)); return 1; }

    printf("共 %zd 台设备\n", cnt);
    for (i = 0; i < cnt; i++) {
        struct libusb_device_descriptor desc;
        if (libusb_get_device_descriptor(devs[i], &desc) < 0)   /* 内核缓存的副本 */
            continue;
        int match = (target_vid < 0) ||
                    (desc.idVendor == target_vid && desc.idProduct == target_pid);
        printf("%s%04x:%04x  bus %d  address %d  %s\n",
               match ? ">>> " : "    ",
               desc.idVendor, desc.idProduct,
               libusb_get_bus_number(devs[i]),
               libusb_get_device_address(devs[i]),   /* §4.5 领的工牌号 */
               match ? "← 目标设备" : "");
    }

    libusb_free_device_list(devs, 1);
    libusb_exit(ctx);
    return 0;
}
