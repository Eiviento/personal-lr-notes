/* ============================================================
 * 05_clear_halt.c —— 端点 Halt 恢复闭环
 *
 * 学什么:  5.3 的故障闭环写成代码——STALL 现形为 PIPE →
 *          GET_STATUS 确认 → libusb_clear_halt 解冻 → 重试
 * 对应知识点: KB 第五篇 §5.3（两种 STALL 生命周期）+ 第九篇 §9.4
 * 编译:    gcc -o clear_halt 05_clear_halt.c -lusb-1.0
 * 运行:    sudo ./clear_halt 2bdf 0101
 * 预期:    故意发错 wIndex 高字节 → PIPE（STATUS 回 STALL 现形）→
 *          演示闭环三步（GET_STATUS → clear_halt → 重试恢复）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    unsigned char buf[16];

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* ① 故意发错 wIndex 高字节（XU ID=0xFF 不存在）→ 设备 STATUS 回 STALL */
    r = libusb_control_transfer(devh, 0xA1, 0x85, 0x0400, 0xFF00, buf, 2, 1000);
    if (r == LIBUSB_ERROR_PIPE)
        printf("① 故意错发: PIPE —— 这就是 STATUS 阶段的 STALL（§5.1 拒绝唯一入口）\n");
    else
        printf("① 意外: %s\n", libusb_error_name(r));

    /* ② 闭环演示：GET_STATUS 确认 → clear_halt 解冻 → 重试 */
    /*    （注：EP0 的 STALL 是一次性的——下个 SETUP 自动清除；数据端点才需要本闭环。
     *     这里演示的是数据端点故障时的标准处理路径。） */
    int ep = 0x81;   /* VS 批量 IN 端点 */
    unsigned char status[2];
    r = libusb_control_transfer(devh, 0x82, 0x00, 0, ep, status, 2, 1000);
    if (r < 0) { printf("② GET_STATUS 失败: %s\n", libusb_error_name(r)); return 1; }
    printf("② GET_STATUS(EP 0x%02x) = %02x %02x（D0=Halt:%d）\n",
           ep, status[0], status[1], status[0] & 1);

    r = libusb_clear_halt(devh, ep);   /* = CLEAR_FEATURE(ENDPOINT_HALT) 的封装 */
    printf("③ libusb_clear_halt(0x%02x): %s（解冻，管道恢复可重试）\n",
           ep, r < 0 ? libusb_error_name(r) : "成功");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
