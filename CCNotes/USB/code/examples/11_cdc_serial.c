/* ============================================================
 * 11_cdc_serial.c —— CDC 虚拟串口收发（SET_LINE_CODING + 批量）
 *
 * 学什么:  6.13 的 SET_LINE_CODING 7 字节在代码里的完整形态；
 *          "打开串口"= 行编码 + 控制线状态 + 批量传输三件事
 * 对应知识点: KB 第六篇 §6.13/§6.14（CDC 类请求与数据流）
 * 编译:    gcc -o cdc_serial 11_cdc_serial.c -lusb-1.0
 * 运行:    sudo ./cdc_serial 2bdf 028a    （TM5X 的 CDC 接口）
 * 预期:    打印 line coding 设置 → 收 1 秒数据统计字节数
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, r;
    int ctrl_if = -1, data_if = -1, ep_in = -1;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 按 bInterfaceClass 找 CDC 控制接口(0x02)与数据接口(0x0A) */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    for (int i = 0; i < cfg->bNumInterfaces; i++) {
        int cls = cfg->interface[i].altsetting[0].bInterfaceClass;
        if (cls == 0x02) ctrl_if = i;
        if (cls == 0x0A) {
            data_if = i;
            for (int k = 0; k < cfg->interface[i].altsetting[0].bNumEndpoints; k++)
                if (cfg->interface[i].altsetting[0].endpoint[k].bEndpointAddress & 0x80)
                    ep_in = cfg->interface[i].altsetting[0].endpoint[k].bEndpointAddress;
        }
    }
    libusb_free_config_descriptor(cfg);
    if (ctrl_if < 0 || data_if < 0) { fprintf(stderr, "没找到 CDC 接口\n"); return 1; }
    printf("CDC: 控制接口 %d, 数据接口 %d (EP IN 0x%02x)\n", ctrl_if, data_if, ep_in);

    /* 打开串口 = SET_LINE_CODING（7 字节）+ SET_CONTROL_LINE_STATE */
    uint8_t line_coding[7] = {0x00, 0xC2, 0x01, 0x00, 0x00, 0x00, 0x08};
    /*                       115200 LE        停止位  校验  数据位 */
    r = libusb_control_transfer(devh, 0x21, 0x20, 0, ctrl_if, line_coding, 7, 1000);
    if (r < 0) { fprintf(stderr, "SET_LINE_CODING: %s\n", libusb_error_name(r)); return 1; }
    printf("SET_LINE_CODING: 115200 8N1 已发送\n");

    r = libusb_control_transfer(devh, 0x21, 0x22, 0x0003, ctrl_if, NULL, 0, 1000);
    if (r < 0) { fprintf(stderr, "SET_CONTROL_LINE_STATE: %s\n", libusb_error_name(r)); return 1; }
    printf("SET_CONTROL_LINE_STATE: DTR|RTS 已拉起\n");

    /* 数据层：claim 数据接口，批量收 1 秒 */
    if (libusb_kernel_driver_active(devh, data_if) == 1)
        libusb_detach_kernel_driver(devh, data_if);
    libusb_claim_interface(devh, data_if);

    unsigned char buf[4096];
    long long total = 0;
    time_t t0 = time(NULL);
    while (time(NULL) - t0 < 1) {
        int got = 0;
        r = libusb_bulk_transfer(devh, ep_in, buf, sizeof(buf), &got, 100);
        if (r == 0) total += got;
        else if (r != LIBUSB_ERROR_TIMEOUT) { printf("传输: %s\n", libusb_error_name(r)); break; }
    }
    printf("1 秒收到 %lld 字节（串口无数据时通常为 0——发数据才有流）\n", total);

    libusb_release_interface(devh, data_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
