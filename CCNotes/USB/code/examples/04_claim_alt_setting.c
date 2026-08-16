/* ============================================================
 * 04_claim_alt_setting.c —— claim 接口 + 切换 Alt Setting
 *
 * 学什么:  四层动作的后两层——claim（所有权登记，零总线流量）与
 *          set_interface_alt_setting（SET_INTERFACE 的代码版，设备
 *          固件执行"旧端点失效→新端点激活→toggle 归零"）
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流 / claim 与 detach）
 * 编译:    gcc -o claim_alt 04_claim_alt_setting.c -lusb-1.0
 * 运行:    sudo ./claim_alt 2bdf 0101
 * 预期:    detach+claim 成功 → 自动发现流 Alt（本机为 Alt0）→
 *          打印端点 → 还原（★ 真机勘误：原硬编码 Alt1 不存在——
 *          2bdf:0101 是批量视频设备，VS 只有 Alt0，无零带宽 Alt）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg = NULL;
    int vid, pid, r;
    int vs_if = 1;   /* 2bdf:0101: VS 接口 1（接口号从 lsusb -v 确认） */
    int vs_alt = -1; /* 流 Alt 自动发现，不硬编码 */

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
        fprintf(stderr, "claim 失败: %s\n", libusb_error_name(r));
        goto cleanup;   /* ★ 失败也要还车：司机被 detach 后必须 attach 回去 */
    }
    printf("[内核层] claim 接口 %d 成功（所有权登记，无总线流量）\n", vs_if);

    /* 【协议层】自动发现流 Alt：找第一个有端点的 Alt Setting
     * ★ 真机勘误（2026-08-16）：原硬编码 Alt1 → NOT_FOUND。
     * 2bdf:0101 是批量视频设备，VS 只有 Alt0（批量流端点直接挂在
     * Alt0 上）——"Alt0 零带宽/Alt1 流端点"是等时设备的带宽闸门，
     * 批量不预留带宽，零带宽 Alt 无意义 */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    for (int j = 0; j < cfg->interface[vs_if].num_altsetting; j++) {
        if (cfg->interface[vs_if].altsetting[j].bNumEndpoints > 0) {
            vs_alt = j;
            break;
        }
    }
    if (vs_alt < 0) { fprintf(stderr, "没找到带端点的 Alt\n"); goto cleanup; }

    r = libusb_set_interface_alt_setting(devh, vs_if, vs_alt);
    if (r < 0) {
        fprintf(stderr, "切 Alt 失败: %s\n", libusb_error_name(r));
        goto cleanup;
    }
    printf("[协议层] SET_INTERFACE(Alt%d) 成功——流端点已激活，toggle 归零\n", vs_alt);

    /* 查看流 Alt 的端点 */
    const struct libusb_interface_descriptor *alt = &cfg->interface[vs_if].altsetting[vs_alt];
    printf("[查看]   Alt%d 有 %d 个端点:", vs_alt, alt->bNumEndpoints);
    for (int i = 0; i < alt->bNumEndpoints; i++)
        printf(" 0x%02x", alt->endpoint[i].bEndpointAddress);
    printf("\n");

    printf("[还原]  release + attach 完成（司机复工）\n");

cleanup:
    libusb_free_config_descriptor(cfg);
    libusb_release_interface(devh, vs_if);
    libusb_attach_kernel_driver(devh, vs_if);   /* 已 detach 过才 attach；未 detach 返回 NOT_SUPPORTED，无害 */
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
