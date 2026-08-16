/* ============================================================
 * 08_uvc_open_stream.c —— 标准 UVC 开流（SET_INTERFACE + 收 1 秒统计）
 *
 * 学什么:  开流全流程——找 Alt（自动选第一个有端点的）→ SET_INTERFACE
 *          → 批量收 1 秒裸数据统计字节数（不拼帧，证明管道通即可）
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流）+ 第十会话（开流=切通道）
 * 编译:    gcc -o uvc_open_stream 08_uvc_open_stream.c -lusb-1.0
 * 运行:    sudo ./uvc_open_stream 2bdf 0101
 * 预期:    打印选中的 Alt 与端点 → Probe/Commit 协商 → 收 1 秒 → 字节数
 * ★ 真机勘误（2026-08-16）：只 SET_INTERFACE 收 0 字节——本设备固件
 *   把 Probe/Commit 当管线武装命令，必须补上完整协商序列
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
    int vs_if = 1, alt_num = -1, ep_in = -1, ep_pkt = 0;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 自动找第一个"有端点的 Alt"（跳过 Alt0 零带宽） */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    const struct libusb_interface *iface = &cfg->interface[vs_if];
    for (int j = 0; j < iface->num_altsetting; j++) {
        const struct libusb_interface_descriptor *alt = &iface->altsetting[j];
        for (int k = 0; k < alt->bNumEndpoints; k++) {
            if (alt->endpoint[k].bEndpointAddress & 0x80) {  /* IN 端点 */
                alt_num = alt->bAlternateSetting;
                ep_in = alt->endpoint[k].bEndpointAddress;
                ep_pkt = alt->endpoint[k].wMaxPacketSize;
                break;
            }
        }
        if (ep_in >= 0) break;
    }
    libusb_free_config_descriptor(cfg);
    if (ep_in < 0) { fprintf(stderr, "没找到流端点\n"); return 1; }
    printf("选中的流管道: Alt%d, EP 0x%02x, wMaxPacketSize=%d（带宽配额）\n",
           alt_num, ep_in, ep_pkt);

    /* 接管 + 开流（SET_INTERFACE 的代码版） */
    if (libusb_kernel_driver_active(devh, vs_if) == 1)
        libusb_detach_kernel_driver(devh, vs_if);
    libusb_claim_interface(devh, vs_if);

    /* ★ 真机勘误（2026-08-16）：只 SET_INTERFACE 不收数据——本设备固件把
     * Probe/Commit 当"管线武装命令"，不发协商内部视频管线不启动。
     * 补上规范顺序：GET_DEF → SET_CUR(Probe, CS=0x01) → SET_CUR(Commit, CS=0x02) */
    unsigned char probe[26] = {0};
    r = libusb_control_transfer(devh, 0xA1, 0x87, 0x0100, vs_if, probe, 26, 1000);
    if (r >= 0) {
        probe[1] = 1; probe[2] = 1;    /* 若 GET_DEF 无默认，指定 Format1/Frame1 */
        r = libusb_control_transfer(devh, 0x21, 0x01, 0x0100, vs_if, probe, 26, 1000);  /* Probe */
        printf("[协商] Probe: %s\n", r < 0 ? libusb_error_name(r) : "成功");
        r = libusb_control_transfer(devh, 0x21, 0x01, 0x0200, vs_if, probe, 26, 1000);  /* Commit */
        printf("[协商] Commit: %s\n", r < 0 ? libusb_error_name(r) : "成功");
    } else {
        printf("[协商] GET_DEF: %s（继续尝试开流）\n", libusb_error_name(r));
    }

    r = libusb_set_interface_alt_setting(devh, vs_if, alt_num);
    if (r < 0) { fprintf(stderr, "开流失败: %s\n", libusb_error_name(r)); return 1; }
    printf("★ 开流成功——设备已激活流端点；数据要等 Host 的 IN Token（现在开始收 1 秒）\n");

    /* 收 1 秒裸数据（不拼帧，只统计——拼帧见示例 10 由 libuvc 代劳） */
    unsigned char buf[512 * 64];
    long long total = 0;
    time_t t0 = time(NULL);
    while (time(NULL) - t0 < 1) {
        int got = 0;
        r = libusb_bulk_transfer(devh, ep_in, buf, sizeof(buf), &got, 100);
        if (r == 0) total += got;
        else if (r != LIBUSB_ERROR_TIMEOUT) { printf("传输: %s\n", libusb_error_name(r)); break; }
    }
    printf("1 秒收到 %lld 字节（约 %lld KB/s）——管道已通\n", total, total / 1024);

    /* 关流 + 还车 + 司机复工 */
    libusb_set_interface_alt_setting(devh, vs_if, 0);
    libusb_release_interface(devh, vs_if);
    libusb_attach_kernel_driver(devh, vs_if);
    printf("已关流（Alt0）+ release + attach\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
