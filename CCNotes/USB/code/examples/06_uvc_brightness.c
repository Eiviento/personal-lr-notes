/* ============================================================
 * 06_uvc_brightness.c —— 标准 UVC 亮度控制（PU GET_CUR/SET_CUR）
 *
 * 学什么:  标准 UVC 类请求的形状（0x21/0xA1 + wValue 高字节=CS_ID）
 *          与 PU 的寻址——wIndex = (PU_ID << 8) | VC_IF（与 XU 同构，
 *          第八篇 §8.8 惯例：Unit ID 填高字节）
 * 对应知识点: KB 第八篇 §8.8（PU 教程）+ 第六篇 §6.20（bmControls 位图）
 * 编译:    gcc -o uvc_brightness 06_uvc_brightness.c -lusb-1.0
 * 运行:    sudo ./uvc_brightness 2bdf 028a 0 2 [亮度值]
 *          （PU_ID 查法: sudo lsusb -v -d VID:PID | grep -B2 -A6 PROCESSING_UNIT；
 *           不带亮度值 = 读回当前值后原样写回；带 = 设为自定义值 0~100）
 * 预期:    两台真机对照——028a (PU_ID=2, bmControls=0x13df) 返回真实亮度
 *          并可 SET_CUR；0101 (PU_ID=5, bmControls=00 00) STALL（真·空壳）
 * ★ 真机勘误（2026-08-16）：初版 wIndex 漏了 PU_ID 高字节，两台设备都
 *   STALL，误判为"空壳"——PU 寻址与 XU 同构（第八篇 §8.8 早有此惯例）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define CS_BRIGHTNESS  0x01   /* PU 控制选择子（§6.20 位图表） */

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    unsigned char val[2];
    int vid, pid, vc_if, pu_id, r;

    if (argc != 5 && argc != 6) {
        printf("用法: %s VID PID VC_IF PU_ID [亮度值]\n", argv[0]);
        printf("  PU_ID 查法: sudo lsusb -v -d VID:PID | grep -B2 -A6 PROCESSING_UNIT\n");
        return 1;
    }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);
    vc_if = atoi(argv[3]);
    pu_id = atoi(argv[4]);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* ★ 真机勘误（2026-08-16）：uvcvideo 绑定时，接口寻址类请求被拒（报 IO）
     * ——发类请求前先请司机下车，结束再请回来（第六会话老规矩） */
    int if_was = 0;
    if (libusb_kernel_driver_active(devh, vc_if) == 1) {
        libusb_detach_kernel_driver(devh, vc_if);
        if_was = 1;
        printf("[准备] 已请内核司机下车（/dev/video0 消失）\n");
    }
    libusb_claim_interface(devh, vc_if);   /* PU 控制走 EP0，其实不 claim 也行 */

    /* 读亮度: IN Class Interface, GET_CUR, wValue 高字节=CS_BRIGHTNESS,
     * wIndex = (PU_ID << 8) | VC_IF —— ★ PU 寻址与 XU 同构（第八篇 §8.8） */
    r = libusb_control_transfer(devh, 0xA1, 0x81, CS_BRIGHTNESS << 8,
                                (pu_id << 8) | vc_if, val, 2, 1000);
    if (r == LIBUSB_ERROR_PIPE) {
        printf("GET_CUR(Brightness) → PIPE（STATUS 回 STALL）\n");
        printf("★ 设备拒绝了亮度控制——用 lsusb -v 查它的 PU bmControls：\n");
        printf("  bmControls=00 00 → 标准控制是空壳（如 2bdf:0101，第六篇 §6.20\n");
        printf("    的专业设备常态——亮度全塞进 XU，见示例 09）\n");
        printf("  bmControls 非零   → 检查 PU_ID 参数（本例 %d）和 CS_ID 字节序\n", pu_id);
    } else if (r >= 0) {
        int brightness = val[0] | (val[1] << 8);
        printf("当前亮度 = %d（小端 %02x %02x）\n", brightness, val[0], val[1]);

        /* 设亮度：带第 5 参数 = 自定义值；不带 = 原样写回当前值。
         * 小端打包：低位字节在前（线上顺序 32 00 = 50） */
        int target = (argc == 6) ? atoi(argv[5]) : brightness;
        unsigned char set_val[2] = { target & 0xFF, (target >> 8) & 0xFF };
        r = libusb_control_transfer(devh, 0x21, 0x01, CS_BRIGHTNESS << 8,
                                    (pu_id << 8) | vc_if, set_val, 2, 1000);
        printf("SET_CUR(Brightness=%d): %s\n", target,
               r < 0 ? libusb_error_name(r) : "成功");

        /* 写后立即读回验证（§5.3 闭环思路：改完先读回来确认） */
        unsigned char back[2] = {0};
        r = libusb_control_transfer(devh, 0xA1, 0x81, CS_BRIGHTNESS << 8,
                                    (pu_id << 8) | vc_if, back, 2, 1000);
        if (r >= 0)
            printf("写后读回 = %d %s\n", back[0] | (back[1] << 8),
                   back[0] == set_val[0] && back[1] == set_val[1]
                       ? "（与写入一致 ✓）" : "（与写入不一致——固件表面成功未应用？）");
    } else {
        printf("意外: %s\n", libusb_error_name(r));
    }

    libusb_release_interface(devh, vc_if);
    if (if_was) libusb_attach_kernel_driver(devh, vc_if);
    printf("[还原] 司机复工\n");
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
