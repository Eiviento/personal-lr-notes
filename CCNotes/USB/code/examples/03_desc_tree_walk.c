/* ============================================================
 * 03_desc_tree_walk.c —— 遍历描述符树
 *
 * 学什么:  描述符结构体 = §3.1 层级树的 C 版——
 *          cfg.interface[i].altsetting[j].endpoint[k] 递归打印，
 *          就是 lsusb -v 的 libusb 版
 * 对应知识点: KB 第九篇 §9.2（描述符结构体层级）+ 第六篇（Alt Setting 数组形态）
 * 编译:    gcc -o desc_tree 03_desc_tree_walk.c -lusb-1.0
 * 运行:    sudo ./desc_tree 2bdf 0101
 * 预期:    打印 433 字节链的树形结构（接口/Alt/端点/传输类型/包大小）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

static void indent(int n) { while (n--) printf("  "); }

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, i, j, k;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    if (libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg) < 0) {
        fprintf(stderr, "读配置链失败\n"); return 1;
    }

    printf("设备 %04x:%04x — 配置链（wTotalLength=%d）\n",
           vid, pid, cfg->wTotalLength);
    for (i = 0; i < cfg->bNumInterfaces; i++) {              /* 接口 */
        const struct libusb_interface *iface = &cfg->interface[i];
        indent(1); printf("Interface %d (class 0x%02x)\n",
                          i, iface->altsetting[0].bInterfaceClass);
        for (j = 0; j < iface->num_altsetting; j++) {        /* Alt Setting */
            const struct libusb_interface_descriptor *alt = &iface->altsetting[j];
            indent(2); printf("Alt %d: %d 个端点%s\n", alt->bAlternateSetting,
                              alt->bNumEndpoints,
                              alt->bNumEndpoints == 0 ? "（零带宽）" : "");
            for (k = 0; k < alt->bNumEndpoints; k++) {       /* 端点 */
                const struct libusb_endpoint_descriptor *ep = &alt->endpoint[k];
                const char *type =
                    (ep->bmAttributes & 0x03) == 0 ? "控制" :
                    (ep->bmAttributes & 0x03) == 1 ? "等时" :
                    (ep->bmAttributes & 0x03) == 2 ? "批量" : "中断";
                indent(3);
                printf("EP 0x%02x (%s) %s wMaxPacketSize=%d bInterval=%d\n",
                       ep->bEndpointAddress,
                       ep->bEndpointAddress & 0x80 ? "IN" : "OUT",
                       type, ep->wMaxPacketSize, ep->bInterval);
            }
        }
    }

    libusb_free_config_descriptor(cfg);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
