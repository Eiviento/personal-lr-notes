/* ============================================================
 * 10_frame_mailbox.c —— 信箱模式取流（libuvc 帧回调 + 主线程渲染）
 *
 * 学什么:  "两方 + 一个信箱"的协调——回调只做转换+投放（信箱满就丢
 *          新帧，绝不阻塞事件泵）；主线程有空才取走渲染
 * 对应知识点: KB 第九篇 §9.4 深挖（信箱模式简版）+ 第八会话踩坑 1/36
 * 编译:    g++ -o frame_mailbox 10_frame_mailbox.cpp -luvc -lusb-1.0 \
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

/* 信箱（共享缓冲 + 标志位 + 锁）——存的是"成品 BGR 帧"，不是原始字节 */
static pthread_mutex_t mbox_mutex = PTHREAD_MUTEX_INITIALIZER;
static unsigned char mbox_buf[640 * 480 * 3];
static int mbox_len = 0, mbox_w = 0, mbox_h = 0;
static int mbox_ready = 0;

/* 帧回调：跑在 libuvc 事件线程（与拼帧回调同一线程） */
static void frame_cb(uvc_frame_t *frame, void *ptr)
{
    (void)ptr;
    /* 快解码：本设备撒谎报 YUYV 实发 MJPEG（第八会话踩坑 3）——检测 FF D8 */
    /* uvc_frame_t::data 是 void*——C++ 必须先转指针再下标（第八会话踩坑 7） */
    const uint8_t *raw = (const uint8_t *)frame->data;
    cv::Mat img;
    if (raw[0] == 0xFF && raw[1] == 0xD8) {
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
        mbox_len = (int)(img.total() * img.elemSize());
        memcpy(mbox_buf, img.data, mbox_len);
        mbox_w = img.cols;
        mbox_h = img.rows;
        mbox_ready = 1;
    }
    pthread_mutex_unlock(&mbox_mutex);
}

/* ★ 真机勘误（第八会话踩坑 38）：本设备 VS 链含 VS_COLORFORMAT 描述符、
 * Probe 协商不可靠——直接调 uvc_get_stream_ctrl_format_size 会失败。
 * 解法与 code/tools/uvc_stream_viewer.cpp 相同：先试常见参数组合，
 * 再回退遍历原始格式描述符链，fps 传 0 表示"无所谓"。 */
static int negotiate(uvc_device_handle_t *devh, uvc_stream_ctrl_t *ctrl_out)
{
    struct trial { enum uvc_frame_format fmt; int w, h, fps; } trials[] = {
        { UVC_FRAME_FORMAT_YUYV,   0,   0,  0 },
        { UVC_FRAME_FORMAT_MJPEG,  0,   0,  0 },
        { UVC_FRAME_FORMAT_YUYV,   120, 160, 30 },
        { UVC_FRAME_FORMAT_MJPEG,  120, 160, 30 },
        { UVC_FRAME_FORMAT_UNCOMPRESSED, 0, 0, 0 },
    };
    for (size_t i = 0; i < sizeof(trials) / sizeof(trials[0]); i++) {
        if (uvc_get_stream_ctrl_format_size(devh, ctrl_out,
                trials[i].fmt, trials[i].w, trials[i].h, trials[i].fps)
                == UVC_SUCCESS)
            return 0;
    }

    /* 回退：遍历原始格式描述符链 */
    const uvc_format_desc_t *fmt_list = uvc_get_format_descs(devh);
    if (!fmt_list) return -1;
    for (const uvc_format_desc_t *fmt = fmt_list; fmt; fmt = fmt->next) {
        enum uvc_frame_format ffmt =
            (fmt->bDescriptorSubtype == UVC_VS_FORMAT_MJPEG)
                ? UVC_FRAME_FORMAT_MJPEG : UVC_FRAME_FORMAT_YUYV;
        for (const uvc_frame_desc_t *frm = fmt->frame_descs; frm; frm = frm->next) {
            int w = frm->wWidth, h = frm->wHeight;
            int fps = (frm->dwDefaultFrameInterval > 0)
                ? (int)(10000000UL / frm->dwDefaultFrameInterval) : 15;
            if (uvc_get_stream_ctrl_format_size(devh, ctrl_out, ffmt, w, h, fps)
                    == UVC_SUCCESS)
                return 0;
            if (uvc_get_stream_ctrl_format_size(devh, ctrl_out, ffmt, w, h, 0)
                    == UVC_SUCCESS)
                return 0;
        }
    }
    return -1;
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
    /* 标准取流流程由 libuvc 代劳（Probe/Commit 武装 + SET_INTERFACE 开闸）。
     * ★ 本设备协商不可靠，需两轮协商（见 negotiate，第八会话踩坑 38） */
    if (negotiate(devh, &ctrl) < 0) {
        fprintf(stderr, "协商失败\n"); return 1;
    }
    if (uvc_start_streaming(devh, &ctrl, frame_cb, NULL, 0) < 0) {
        fprintf(stderr, "开流失败\n"); return 1;
    }
    puts("取流中... 按 ESC 退出");

    /* 主线程：信箱里有帧才取（渲染在锁外）。
     * ★ 信箱里已是解码好的 BGR 成品——回调干了转换，主线程只负责显示，
     *   不要再解码第二遍（早期版本把 BGR 当 JPEG 再 imdecode，静默不显示） */
    while (1) {
        unsigned char local[640 * 480 * 3];
        int len = 0, w = 0, h = 0;
        pthread_mutex_lock(&mbox_mutex);
        if (mbox_ready) {
            len = mbox_len;
            memcpy(local, mbox_buf, len);
            w = mbox_w;
            h = mbox_h;
            mbox_ready = 0;
        }
        pthread_mutex_unlock(&mbox_mutex);

        if (len) {
            cv::Mat img(h, w, CV_8UC3, local);
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
