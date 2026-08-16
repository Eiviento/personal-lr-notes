/**
 * xu_minimal_get.c — UVC XU 读参数最小示例
 *
 * 流程：GET_LEN → GET_CUR（无 FUNC_SWITCH，CS_ID=0x04 无需子功能切换）
 * 目标：CS_ID=0x04（协议版本）
 *
 * 编译：gcc -o xu_minimal_get xu_minimal_get.c -lusb-1.0
 * 运行：./xu_minimal_get
 *
 * 使用前请修改：
 *   1. DEV_VID / DEV_PID → 你的热成像摄像头 VID/PID（lsusb 查看）
 *   2. XU_UNIT_ID         → Extension Unit ID（lsusb -v 查看 bUnitID）
 *   3. VC_IF_NUM          → Video Control 接口号（通常 0 或 1）
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libusb-1.0/libusb.h>

/* ========== 请修改为你的实际设备参数 ========== */
#define DEV_VID         0x2bdf   // 你的摄像头 VID
#define DEV_PID         0x0102   // 你的摄像头 PID
#define XU_UNIT_ID      0x0A     // Extension Unit ID（lsusb -v 查 bUnitID）
#define VC_IF_NUM       1        // Video Control 接口号（通常 0 或 1）
/* ============================================= */

/* UVC Class 请求常量 */
#define UVC_RT_OUT_CLASS    0x21    // Host→Device, Class, Interface
#define UVC_RT_IN_CLASS     0xA1    // Device→Host, Class, Interface
#define UVC_SET_CUR         0x01
#define UVC_GET_CUR         0x81
#define UVC_GET_LEN         0x85

/* CS_ID 定义 */
#define TARGET_CS_ID        0x04    // 协议版本，无需 SubFunc

int main(void)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int ret;

    /* 1. 初始化 libusb */
    ret = libusb_init(&ctx);
    if (ret < 0) {
        fprintf(stderr, "libusb_init failed: %s\n", libusb_error_name(ret));
        return 1;
    }

    /* 2. 打开设备 */
    devh = libusb_open_device_with_vid_pid(ctx, DEV_VID, DEV_PID);
    if (!devh) {
        fprintf(stderr, "Cannot open device %04x:%04x\n", DEV_VID, DEV_PID);
        fprintf(stderr, "Check VID/PID and permissions (see udev rules).\n");
        libusb_exit(ctx);
        return 1;
    }
    printf("[OK] Device opened: %04x:%04x\n", DEV_VID, DEV_PID);

    /* 3. 解绑内核 uvcvideo 驱动 + claim 接口（Linux 必须） */
    if (libusb_kernel_driver_active(devh, VC_IF_NUM)) {
        printf("Detaching kernel driver from interface %d...\n", VC_IF_NUM);
        ret = libusb_detach_kernel_driver(devh, VC_IF_NUM);
        if (ret < 0) {
            fprintf(stderr, "detach_kernel_driver failed: %s\n", libusb_error_name(ret));
            libusb_close(devh);
            libusb_exit(ctx);
            return 1;
        }
        printf("[OK] Kernel driver detached\n");
    }

    ret = libusb_claim_interface(devh, VC_IF_NUM);
    if (ret < 0) {
        fprintf(stderr, "claim_interface failed: %s\n", libusb_error_name(ret));
        libusb_close(devh);
        libusb_exit(ctx);
        return 1;
    }
    printf("[OK] Interface %d claimed\n", VC_IF_NUM);

    /* ============================================================
     * 两阶段读流程（CS_ID=0x04 无需 FUNC_SWITCH）
     * ============================================================ */

    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;

    /* ---- 阶段 1：GET_LEN — 获取参数长度 ---- */
    uint16_t param_len = 0;
    {
        uint8_t len_buf[2] = {0};
        uint16_t wValue = (TARGET_CS_ID << 8);

        ret = libusb_control_transfer(
            devh,
            UVC_RT_IN_CLASS,             // bmRequestType: IN, Class, Interface
            UVC_GET_LEN,                  // bRequest
            wValue,                       // wValue: CS_ID=0x04
            wIndex,
            len_buf, 2,
            1000);

        if (ret != 2) {
            fprintf(stderr, "[GET_LEN] CS_ID=0x%02X failed: %s (ret=%d)\n",
                    TARGET_CS_ID, libusb_error_name(ret), ret);
            if (ret == LIBUSB_ERROR_PIPE)
                fprintf(stderr, "  → Device STALL: CS_ID not supported by firmware\n");
            goto cleanup;
        }

        param_len = len_buf[0] | (len_buf[1] << 8);  // LE → host
        printf("[GET_LEN] param_len = %u bytes\n", param_len);
    }

    /* ---- 阶段 2：GET_CUR — 按长度读取数据 ---- */
    if (param_len == 0) {
        printf("[GET_CUR] param_len=0, nothing to read\n");
    } else {
        uint8_t *buf = malloc(param_len);
        if (!buf) {
            fprintf(stderr, "malloc(%u) failed\n", param_len);
            goto cleanup;
        }

        uint16_t wValue = (TARGET_CS_ID << 8);

        ret = libusb_control_transfer(
            devh,
            UVC_RT_IN_CLASS,             // bmRequestType: IN, Class, Interface
            UVC_GET_CUR,                  // bRequest
            wValue,                       // wValue: CS_ID=0x04
            wIndex,
            buf, param_len,
            1000);

        if (ret < 0) {
            fprintf(stderr, "[GET_CUR] failed: %s (ret=%d)\n",
                    libusb_error_name(ret), ret);
            free(buf);
            goto cleanup;
        }

        int actual_len = ret;
        printf("[GET_CUR] read %d bytes:\n", actual_len);
        printf("  HEX: ");
        for (int i = 0; i < actual_len; i++)
            printf("%02X ", buf[i]);
        printf("\n");

        /* 协议版本通常是 ASCII 字符串 */
        printf("  ASCII: ");
        for (int i = 0; i < actual_len; i++)
            putchar((buf[i] >= 0x20 && buf[i] < 0x7F) ? buf[i] : '.');
        printf("\n");

        free(buf);
    }

    printf("\nDone.\n");

    /* ============================================================
     * 清理
     * ============================================================ */
cleanup:
    libusb_release_interface(devh, VC_IF_NUM);
    libusb_attach_kernel_driver(devh, VC_IF_NUM);  // 归还给 uvcvideo
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
