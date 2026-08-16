/* ============================================================
 * 04_claim_alt_setting.c —— claim 接口 + 切换 Alt Setting
 *
 * 学什么:  四层动作的后两层——claim（所有权登记，零总线流量）与
 *          set_interface_alt_setting（SET_INTERFACE 的代码版，设备
 *          固件执行"旧端点失效→新端点激活→toggle 归零"）
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流 / claim 与 detach）
 * 编译:    gcc -o claim_alt 04_claim_alt_setting.c -lusb-1.0
 * 运行:    sudo ./claim_alt 2bdf 0101
 * 预期:    detach+claim 成功 → VS 接口 Alt1 激活 → 打印端点 → 还原
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    int vs_if = 1, vs_alt1 = 1;   /* 2bdf:0101: VS 接口 1，Alt1 有流端点 */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 【内核层】detach 司机（video0 消失）+ claim 登记（零总线流量） */
    if ((r = libusb_kernel_driver_active(devh, vs_if)) == 1) {
        libusb_detach_kernel_driver(devh, vs_if);
        printf("[内核层] 已请内核司机下车（/dev/video0 消失）\n");
    }
    if ((r = libusb_claim_interface(devh, vs_if)) < 0) {
        fprintf(stderr, "claim 失败: %s\n", libusb_error_name(r)); return 1;
    }
    printf("[内核层] claim 接口 %d 成功（所有权登记，无总线流量）\n", vs_if);

    /* 【协议层】SET_INTERFACE = 开流开关 */
    r = libusb_set_interface_alt_setting(devh, vs_if, vs_alt1);
    if (r < 0) { fprintf(stderr, "切 Alt 失败: %s\n", libusb_error_name(r)); return 1; }
    printf("[协议层] SET_INTERFACE(Alt%d) 成功——流端点已激活，toggle 归零\n", vs_alt1);

    /* 查看 Alt1 的端点 */
    struct libusb_config_descriptor *cfg;
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    const struct libusb_interface_descriptor *alt = &cfg->interface[vs_if].altsetting[vs_alt1];
    printf("[查看]   Alt%d 有 %d 个端点:", vs_alt1, alt->bNumEndpoints);
    for (int i = 0; i < alt->bNumEndpoints; i++)
        printf(" 0x%02x", alt->endpoint[i].bEndpointAddress);
    printf("\n");
    libusb_free_config_descriptor(cfg);

    /* 还原：切回 Alt0（关流）+ 还车 + 司机复工 */
    libusb_set_interface_alt_setting(devh, vs_if, 0);
    libusb_release_interface(devh, vs_if);
    libusb_attach_kernel_driver(devh, vs_if);
    printf("[还原]  Alt0 + release + attach 完成（司机复工）\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
