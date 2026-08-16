/* ============================================================
 * 06_uvc_brightness.c —— 标准 UVC 亮度控制（PU GET_CUR/SET_CUR）
 *
 * 学什么:  标准 UVC 类请求的形状（0x21/0xA1 + wValue 高字节=CS_ID）
 *          与"专业设备 PU 是空壳"的现实——2bdf:0101 的 PU
 *          bmControls=00 00，GET_CUR 必然 STALL（预期失败=教学点）
 * 对应知识点: KB 第六篇 §6.20（bmControls 位图）+ 第八篇 §8.8
 * 编译:    gcc -o uvc_brightness 06_uvc_brightness.c -lusb-1.0
 * 运行:    sudo ./uvc_brightness 2bdf 0101
 * 预期:    GET_CUR(Brightness) → PIPE；程序打印解释并退出
 *          （换罗技等标准摄像头，同一份代码会返回亮度值并成功 SET_CUR）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define CS_BRIGHTNESS  0x01   /* PU 控制选择子（§6.20 位图表） */

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    unsigned char val[2];
    int vc_if = 0;   /* 2bdf:0101 的 VC 接口号（lsusb -v 确认） */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }
    libusb_claim_interface(devh, vc_if);   /* PU 控制走 EP0，其实不 claim 也行 */

    /* 读亮度: IN Class Interface, GET_CUR, wValue 高字节=CS_BRIGHTNESS,
     * wIndex=VC 接口号（PU 没有 Unit ID——那是 XU 的专利） */
    r = libusb_control_transfer(devh, 0xA1, 0x81, CS_BRIGHTNESS << 8,
                                vc_if, val, 2, 1000);
    if (r == LIBUSB_ERROR_PIPE) {
        printf("GET_CUR(Brightness) → PIPE（STATUS 回 STALL）\n");
        printf("★ 预期内：本设备 PU bmControls=00 00，标准控制是空壳\n");
        printf("  （第六篇 §6.20 的专业设备常态——亮度/对比度全塞进 XU，\n");
        printf("   见示例 09。换标准摄像头则本代码直接返回亮度值。）\n");
    } else if (r >= 0) {
        int brightness = val[0] | (val[1] << 8);
        printf("当前亮度 = %d（小端 %02x %02x）\n", brightness, val[0], val[1]);

        /* 设亮度 = 当前值（标准设备上可改任意 0~100 试试） */
        r = libusb_control_transfer(devh, 0x21, 0x01, CS_BRIGHTNESS << 8,
                                    vc_if, val, 2, 1000);
        printf("SET_CUR(Brightness=%d): %s\n", brightness,
               r < 0 ? libusb_error_name(r) : "成功");
    } else {
        printf("意外: %s\n", libusb_error_name(r));
    }

    libusb_release_interface(devh, vc_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
