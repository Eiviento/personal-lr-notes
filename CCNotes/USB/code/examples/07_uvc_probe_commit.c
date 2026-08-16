/* ============================================================
 * 07_uvc_probe_commit.c —— Probe/Commit 协商（不取流只看对话）
 *
 * 学什么:  6.25 的协商机制——GET_MIN/MAX/DEF 问范围 → SET_CUR Probe
 *          试问 → GET_CUR 看设备敲定的参数；26 字节负载的字段解析
 * 对应知识点: KB 第六篇 §6.25 + 第十会话（UVC 请求码全家桶）
 * 编译:    gcc -o uvc_probe 07_uvc_probe_commit.c -lusb-1.0
 * 运行:    sudo ./uvc_probe 2bdf 0101
 * 预期:    打印设备自报的格式索引/帧索引/帧率/单帧最大字节数
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libusb-1.0/libusb.h>

/* VS Probe 26 字节负载的字段偏移（UVC 1.1） */
#define OFF_FORMAT_IDX     1
#define OFF_FRAME_IDX      2
#define OFF_FRAME_INTERVAL 3
#define OFF_MAX_FRAME_SIZE 17
#define OFF_MAX_PAYLOAD    21
#define PROBE_LEN          26

static void print_probe(const char *tag, unsigned char *p)
{
    printf("%s: Format=%d Frame=%d interval=%.1fms MaxFrameSize=%d Payload=%d\n",
           tag, p[OFF_FORMAT_IDX], p[OFF_FRAME_IDX],
           (p[OFF_FRAME_INTERVAL] | p[OFF_FRAME_INTERVAL+1]<<8 |
            p[OFF_FRAME_INTERVAL+2]<<16 | p[OFF_FRAME_INTERVAL+3]<<24) / 10000.0,
           p[OFF_MAX_FRAME_SIZE] | p[OFF_MAX_FRAME_SIZE+1]<<8 |
           p[OFF_MAX_FRAME_SIZE+2]<<16 | p[OFF_MAX_FRAME_SIZE+3]<<24,
           p[OFF_MAX_PAYLOAD] | p[OFF_MAX_PAYLOAD+1]<<8 |
           p[OFF_MAX_PAYLOAD+2]<<16 | p[OFF_MAX_PAYLOAD+3]<<24);
}

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    unsigned char buf[PROBE_LEN];
    int vid, pid, r;
    int vs_if = 1;   /* 2bdf:0101 的 VS 接口号 */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* ★ 真机勘误（2026-08-16）：uvcvideo 绑定时，接口寻址类请求被拒（报 IO）
     * ——发类请求前先请司机下车，结束再请回来 */
    int if_was = 0;
    if (libusb_kernel_driver_active(devh, vs_if) == 1) {
        libusb_detach_kernel_driver(devh, vs_if);
        if_was = 1;
    }
    libusb_claim_interface(devh, vs_if);

    /* 问范围: VS Probe 的 CS_ID=0x01，wIndex=VS 接口号（没有 Unit ID！） */
    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x82, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_MIN", buf); else printf("GET_MIN: %s\n", libusb_error_name(r));

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x83, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_MAX", buf); else printf("GET_MAX: %s\n", libusb_error_name(r));

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x87, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_DEF", buf); else printf("GET_DEF: %s\n", libusb_error_name(r));

    /* 试问: 用默认值 Probe（SET_CUR 是 OUT 传输，设备不会回写缓冲——
     * 先打印"请求"再发送；设备是否敲定看下面的 GET_CUR） */
    memset(buf, 0, sizeof(buf));
    buf[OFF_FORMAT_IDX] = 1;
    buf[OFF_FRAME_IDX]  = 1;
    print_probe("SET_CUR Probe 请求", buf);
    r = libusb_control_transfer(devh, 0x21, 0x01, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    printf("  发送结果: %s\n", r < 0 ? libusb_error_name(r) : "成功");

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x81, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_CUR 设备敲定", buf); else printf("GET_CUR: %s\n", libusb_error_name(r));
    printf("（未发 Commit、未开流——纯协商对话到此为止）\n");

    libusb_release_interface(devh, vs_if);
    if (if_was) libusb_attach_kernel_driver(devh, vs_if);
    printf("[还原] 司机复工\n");
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
