/* ============================================================
 * 10_frame_mailbox.c —— 信箱模式取流（libuvc 帧回调 + 主线程渲染）
 *
 * 学什么:  "两方 + 一个信箱"的协调——回调只做转换+投放（信箱满就丢
 *          新帧，绝不阻塞事件泵）；主线程有空才取走渲染
 * 对应知识点: KB 第九篇 §9.4 深挖（信箱模式简版）+ 第八会话踩坑 1/36
 * 编译:    gcc -o frame_mailbox 10_frame_mailbox.c -luvc -lusb-1.0 \
 *              $(pkg-config --cflags --libs opencv4)
 * 运行:    sudo ./frame_mailbox 2bdf 0101
 * 预期:    窗口显示画面；主线程跟不上时丢帧变慢动作但绝不卡死
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <libuvc/libuvc.h>
#include <opencv2/opencv.hpp>

/* 信箱（共享缓冲 + 标志位 + 锁） */
static pthread_mutex_t mbox_mutex = PTHREAD_MUTEX_INITIALIZER;
static unsigned char mbox_buf[640 * 480 * 3];
static int mbox_len = 0;
static int mbox_ready = 0;

/* 帧回调：跑在 libuvc 事件线程（与拼帧回调同一线程） */
static void frame_cb(uvc_frame_t *frame, void *ptr)
{
    (void)ptr;
    /* 快解码：本设备撒谎报 YUYV 实发 MJPEG（第八会话踩坑 3）——检测 FF D8 */
    cv::Mat img;
    if (frame->data[0] == 0xFF && frame->data[1] == 0xD8) {
        img = cv::imdecode(cv::Mat(1, frame->data_bytes, CV_8UC1, frame->data),
                           cv::IMREAD_COLOR);
    } else {
        img = cv::Mat(frame->height, frame->width, CV_8UC2, frame->data);
        cv::cvtColor(img, img, cv::COLOR_YUV2BGR_YUYV);
    }
    if (img.empty()) return;

    /* 信箱规则：满就丢新帧，绝不等待（不阻塞事件泵） */
    pthread_mutex_lock(&mbox_mutex);
    if (!mbox_ready) {
        memcpy(mbox_buf, img.data, img.total() * img.elemSize());
        mbox_len = (int)(img.total() * img.elemSize());
        mbox_ready = 1;
    }
    pthread_mutex_unlock(&mbox_mutex);
}

int main(int argc, char **argv)
{
    uvc_context_t *ctx; uvc_device_t *dev; uvc_device_handle_t *devh;
    uvc_stream_ctrl_t ctrl;
    int vid, pid;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    if (uvc_init(&ctx, NULL) < 0) { fprintf(stderr, "uvc_init 失败\n"); return 1; }
    if (uvc_find_device(ctx, &dev, vid, pid, NULL) < 0) { fprintf(stderr, "找不到设备\n"); return 1; }
    if (uvc_open(dev, &devh) < 0) { fprintf(stderr, "uvc_open 失败\n"); return 1; }
    /* 标准取流流程: Probe/Commit 协商 + SET_INTERFACE 开流由 libuvc 代劳 */
    if (uvc_get_stream_ctrl_format_size(devh, &ctrl, UVC_FRAME_FORMAT_ANY,
                                        120, 160, 30) < 0) {
        fprintf(stderr, "协商失败\n"); return 1;
    }
    if (uvc_start_streaming(devh, &ctrl, frame_cb, NULL, 0) < 0) {
        fprintf(stderr, "开流失败\n"); return 1;
    }
    puts("取流中... 按 ESC 退出");

    /* 主线程：信箱里有帧才取（渲染在锁外） */
    while (1) {
        unsigned char local[640 * 480 * 3];
        int len = 0;
        pthread_mutex_lock(&mbox_mutex);
        if (mbox_ready) {
            memcpy(local, mbox_buf, mbox_len);
            len = mbox_len;
            mbox_ready = 0;
        }
        pthread_mutex_unlock(&mbox_mutex);

        if (len) {
            cv::Mat img = cv::imdecode(cv::Mat(1, len, CV_8UC1, local), cv::IMREAD_COLOR);
            if (!img.empty()) { cv::imshow("frame_mailbox", img); }
        }
        if (cv::waitKey(10) == 27) break;   /* ESC */
    }

    uvc_stop_streaming(devh);
    uvc_close(devh);
    uvc_unref_device(dev);
    uvc_exit(ctx);
    return 0;
}
