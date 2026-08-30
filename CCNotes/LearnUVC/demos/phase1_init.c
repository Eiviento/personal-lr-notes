/* Phase 1 演示：uvc_init / uvc_exit / uvc_strerror / uvc_perror
 *
 * 编译（在 demos/ 目录下）：
 *   gcc -I../libuvc/include -I../libuvc/build/include phase1_init.c \
 *       -L../libuvc/build -luvc \
 *       -L../third_party/libusb-dist/mingw64/lib -lusb-1.0 \
 *       -lwinpthread -o phase1_init.exe
 * 运行前把 libusb-1.0.dll、libwinpthread-1.dll 拷到 exe 同目录。
 */
#include <stdio.h>
#include "libuvc/libuvc.h"

int main(void) {
    uvc_context_t *ctx = NULL; /* 工作台指针，先置 NULL 表示"还没有" */
    uvc_error_t ret;

    /* 1. 创建上下文。
     *    第 1 个参数是输出参数（uvc_init 会把工作台指针写进 *ctx）；
     *    第 2 个参数传 NULL = 让 libuvc 自己创建并管理一个 libusb 上下文。 */
    ret = uvc_init(&ctx, NULL);
    printf("uvc_init 返回: %s (%d)\n", uvc_strerror(ret), ret);
    if (ret != UVC_SUCCESS) {
        uvc_perror(ret, "uvc_init 失败");
        return 1;
    }
    printf("ctx 指针: %p（非 NULL 表示工作台创建成功）\n", (void *)ctx);

    /* 2. 演示 uvc_strerror：错误码 -> 人类可读文字 */
    printf("\n-- uvc_strerror 对照表（挑几个）--\n");
    printf("UVC_SUCCESS        =  %d -> \"%s\"\n", UVC_SUCCESS, uvc_strerror(UVC_SUCCESS));
    printf("UVC_ERROR_ACCESS   =  %d -> \"%s\"\n", UVC_ERROR_ACCESS, uvc_strerror(UVC_ERROR_ACCESS));
    printf("UVC_ERROR_TIMEOUT  =  %d -> \"%s\"\n", UVC_ERROR_TIMEOUT, uvc_strerror(UVC_ERROR_TIMEOUT));
    printf("不存在的码 99      ->  \"%s\"（查无此码时的兜底文字）\n", uvc_strerror(99));

    /* 3. 演示 uvc_perror：错误码 + 自定义前缀，直接打到 stderr */
    printf("\n-- uvc_perror 输出格式（打到 stderr）--\n");
    uvc_perror(UVC_ERROR_NOT_FOUND, "模拟一个错误");
    fflush(stderr);

    /* 4. 释放上下文 */
    uvc_exit(ctx);
    printf("\nuvc_exit 执行完毕（工作台已归还）\n");
    return 0;
}
