/* ============================================================
 * 13_sdk_skeleton.c —— 综合骨架（热插拔 + 枚举 + 打开 + 开流串联）
 *
 * 学什么:  一个最小 SDK 外壳——热插拔回调 + 事件泵线程 + ARRIVED 自动
 *          打开 + LEFT 自动收尾；全部第九篇知识的汇合点
 * 对应知识点: KB 第九篇 §9.5（全 Phase 8 汇成 SDK 骨架）
 * 编译:    gcc -o sdk_skeleton 13_sdk_skeleton.c -lusb-1.0 -pthread
 * 运行:    sudo ./sdk_skeleton 2bdf 0101
 * 预期:    启动打印现有设备 → 拔插摄像头自动响应 → 回车退出
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <libusb-1.0/libusb.h>

static libusb_context *ctx = NULL;
static libusb_device_handle *devh = NULL;
static int g_vid, g_pid;

static int hotplug_cb(libusb_context *c, libusb_device *dev,
                      libusb_hotplug_event event, void *user_data)
{
    (void)c; (void)user_data;
    if (event == LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED) {
        printf("＋ 设备插入 → 自动打开...\n");
        if (!devh) {
            if (libusb_open(dev, &devh) == 0)
                printf("  打开成功（此处可接 claim + 开流 + 取流）\n");
        }
    } else if (event == LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT) {
        printf("－ 设备拔出 → 自动收尾\n");
        if (devh) { libusb_close(devh); devh = NULL; }
    }
    fflush(stdout);
    return 0;
}

static void *event_thread(void *arg)
{
    (void)arg;
    while (1) libusb_handle_events(ctx);   /* ★ 事件泵：传输完成 + 热插拔都靠它 */
    return NULL;
}

int main(int argc, char **argv)
{
    libusb_hotplug_callback_handle handle;
    pthread_t tid;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    g_vid = (int)strtol(argv[1], NULL, 16);
    g_pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    libusb_hotplug_register_callback(ctx,
        LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED | LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT,
        LIBUSB_HOTPLUG_ENUMERATE,      /* 启动时已插着的设备也回调一遍 */
        g_vid, g_pid, LIBUSB_HOTPLUG_MATCH_ANY,
        hotplug_cb, NULL, &handle);

    pthread_create(&tid, NULL, event_thread, NULL);
    printf("SDK 骨架运行中（插拔 %04x:%04x 试试，回车退出）\n", g_vid, g_pid);
    getchar();

    libusb_hotplug_deregister_callback(ctx, handle);
    if (devh) libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
