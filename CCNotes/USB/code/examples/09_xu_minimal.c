/* ============================================================
 * 09_xu_minimal.c —— 最小 XU 扩展单元通信（读协议版本）
 *
 * 学什么:  XU 三把钥匙的填法——wValue 高字节=CS_ID（海康惯例）、
 *          wIndex 高字节=XU Unit ID（换设备只改这里）；GET_LEN 试通
 * 对应知识点: KB 第八篇 §8.1（XU 协议设计）+ 第六会话方法论
 * 编译:    gcc -o xu_minimal 09_xu_minimal.c -lusb-1.0
 * 运行:    sudo ./xu_minimal 2bdf 0101 <VC_IF> <XU_ID>
 *          （XU_ID 从 sudo lsusb -v -d 2bdf:0101 的 bUnitID 查）
 * 预期:    GET_LEN 返回 2 字节协议版本号
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define CS_PROTOCOL_VERSION 0x04   /* 本设备 CS_ID=0x04 是协议版本（第六会话验证） */

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    unsigned char len[2] = {0}, ver[8] = {0};
    int vid, pid, vc_if, xu_id, r;

    if (argc != 5) {
        printf("用法: %s VID PID VC_IF XU_ID\n", argv[0]);
        printf("  XU_ID 查法: sudo lsusb -v -d VID:PID | grep bUnitID\n");
        return 1;
    }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);
    vc_if = atoi(argv[3]);
    xu_id = atoi(argv[4]);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 三阶段: GET_LEN → GET_CUR（FUNC_SWITCH 对只读 CS 可省略） */
    /* bmRequestType=0xA1(IN Class IF), wValue=CS_ID<<8（海康惯例）,
     * wIndex=(XU_ID<<8)|VC_IF —— 换设备只改 XU_ID！ */
    r = libusb_control_transfer(devh, 0xA1, 0x85, CS_PROTOCOL_VERSION << 8,
                                (xu_id << 8) | vc_if, len, 2, 1000);
    if (r < 0) { fprintf(stderr, "GET_LEN: %s（XU_ID 填对了吗？）\n", libusb_error_name(r)); return 1; }
    int len_val = len[0] | (len[1] << 8);
    printf("GET_LEN(CS=0x%02x) → 应答长度 %d 字节\n", CS_PROTOCOL_VERSION, len_val);
    if (len_val == 0) { printf("（长度 0 = 该 CS 无参数或为触发型命令，正常）\n"); return 0; }
    if (len_val > (int)sizeof(ver)) len_val = sizeof(ver);

    r = libusb_control_transfer(devh, 0xA1, 0x81, CS_PROTOCOL_VERSION << 8,
                                (xu_id << 8) | vc_if, ver, len_val, 1000);
    if (r < 0) { fprintf(stderr, "GET_CUR: %s\n", libusb_error_name(r)); return 1; }
    printf("GET_CUR → %d 字节:", r);
    for (int i = 0; i < r; i++) printf(" %02x", ver[i]);
    printf("\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
