/* ============================================================
 * 12_hid_report.c —— HID 中断报表读取
 *
 * 学什么:  6.7 的"中断管道 = 设备主动汇报"——interrupt_transfer
 *          周期轮询；报表字节原样打印（对照 6.6 的报表结构）
 * 对应知识点: KB 第六篇 §6.7（HID Report 协议）+ 第九篇 §9.4
 * 编译:    gcc -o hid_report 12_hid_report.c -lusb-1.0
 * 运行:    sudo ./hid_report 2bdf 028a    （TM5X 的厂商 HID 接口）
 * 预期:    每 100ms 读一次报表，打印前 32 字节 hex（1023B 报表的头部）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, r;
    int hid_if = -1, ep_in = -1, ep_interval = 0;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 按 bInterfaceClass=0x03 找 HID 接口 + 中断 IN 端点 */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    for (int i = 0; i < cfg->bNumInterfaces; i++) {
        if (cfg->interface[i].altsetting[0].bInterfaceClass == 0x03) {
            hid_if = i;
            for (int k = 0; k < cfg->interface[i].altsetting[0].bNumEndpoints; k++) {
                const struct libusb_endpoint_descriptor *ep =
                    &cfg->interface[i].altsetting[0].endpoint[k];
                if ((ep->bmAttributes & 0x03) == 3 && (ep->bEndpointAddress & 0x80)) {
                    ep_in = ep->bEndpointAddress;
                    ep_interval = ep->bInterval;
                }
            }
        }
    }
    libusb_free_config_descriptor(cfg);
    if (hid_if < 0) { fprintf(stderr, "没找到 HID 接口\n"); return 1; }
    printf("HID 接口 %d, 中断 IN EP 0x%02x, bInterval=%d\n", hid_if, ep_in, ep_interval);

    if (libusb_kernel_driver_active(devh, hid_if) == 1)
        libusb_detach_kernel_driver(devh, hid_if);
    libusb_claim_interface(devh, hid_if);

    /* 中断传输循环：Host 周期发 IN Token（bInterval 节奏），设备有数据就回 */
    unsigned char buf[1024];
    for (int n = 0; n < 10; n++) {
        int got = 0;
        r = libusb_interrupt_transfer(devh, ep_in, buf, sizeof(buf), &got, 1000);
        if (r == 0 && got > 0) {
            printf("报表 #%d (%d 字节):", n, got);
            for (int i = 0; i < got && i < 32; i++) printf(" %02x", buf[i]);
            printf("%s\n", got > 32 ? " ..." : "");
        } else if (r == LIBUSB_ERROR_TIMEOUT) {
            printf("报表 #%d: （无数据，设备 NAK）\n", n);
        } else {
            printf("报表 #%d: %s\n", n, libusb_error_name(r)); break;
        }
    }

    libusb_release_interface(devh, hid_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
