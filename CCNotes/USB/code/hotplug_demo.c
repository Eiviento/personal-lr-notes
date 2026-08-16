/* hotplug_demo.c —— 最小热插拔演示：设备插入/拔出时打印消息
 *
 * 编译: gcc -o hotplug_demo hotplug_demo.c -lusb-1.0
 * 运行: sudo ./hotplug_demo              ← 监听所有设备（推荐先这么试）
 *       sudo ./hotplug_demo 2bdf 0101    ← 只监听海康热成像
 */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

static int hotplug_cb(libusb_context *ctx, libusb_device *dev,
                      libusb_hotplug_event event, void *user_data)
{
    (void)ctx;
    (void)user_data;

    if (event == LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED) {
        struct libusb_device_descriptor desc;
        if (libusb_get_device_descriptor(dev, &desc) == 0) {
            printf("+ 设备插入: %04x:%04x  (bus %d, address %d)\n",
                   desc.idVendor, desc.idProduct,
                   libusb_get_bus_number(dev),
                   libusb_get_device_address(dev));
        }
    } else if (event == LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT) {
        printf("- 设备拔出\n");   /* 设备已离线，读不到任何信息 */
    }
    fflush(stdout);
    return 0;
}

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_hotplug_callback_handle handle;
    int vid = LIBUSB_HOTPLUG_MATCH_ANY;   /* 默认不过滤 */
    int pid = LIBUSB_HOTPLUG_MATCH_ANY;

    if (argc == 3) {
        vid = (int)strtol(argv[1], NULL, 16);
        pid = (int)strtol(argv[2], NULL, 16);
    }

    libusb_init(&ctx);
    libusb_hotplug_register_callback(ctx,
        LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED | LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT,
        LIBUSB_HOTPLUG_ENUMERATE,   /* 启动时已插着的设备也报一遍 */
        vid, pid, LIBUSB_HOTPLUG_MATCH_ANY,
        hotplug_cb, NULL, &handle);

    printf("等待设备插拔...（Ctrl+C 退出）\n");
    while (1)
        libusb_handle_events(ctx);  /* 事件泵：回调在这里被触发 */

    /* 不会走到这里；正式代码中应 deregister + exit */
    libusb_hotplug_deregister_callback(ctx, handle);
    libusb_exit(ctx);
    return 0;
}
