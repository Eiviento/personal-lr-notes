/**
 * uvc_stream_viewer.cpp — UVC 摄像头取流 + OpenCV 实时显示
 *
 * 依赖：libuvc, libusb-1.0, OpenCV 4
 * 安装：sudo apt install libuvc-dev libusb-1.0-0-dev libopencv-dev
 * 编译：g++ -o uvc_stream_viewer uvc_stream_viewer.cpp \
 *           -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)
 * 运行：sudo ./uvc_stream_viewer [VID:PID]
 *
 * ============================================================
 * 对比 SDL2 版本的优势：
 *   - cv::imshow 自带窗口管理、缩放、无撕裂
 *   - cv::cvtColor 内置 YUYV→BGR，无需手写转换
 *   - cv::imdecode 内置 MJPEG 解码
 *   - 稳定的主循环 cv::waitKey，不会卡死/撕裂
 * ============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>

#include <libuvc/libuvc.h>
#include <libusb-1.0/libusb.h>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>

/* ============================================================
 * 全局状态
 * ============================================================ */
static volatile sig_atomic_t g_running    = 1;
static volatile sig_atomic_t g_frame_ok   = 0;

static pthread_mutex_t       g_mutex      = PTHREAD_MUTEX_INITIALIZER;
static cv::Mat               g_bgr_frame;           // 主线程显示用
static uvc_frame_t          *g_raw_frame  = NULL;   // 回调内重用
static int                   g_fb_w       = 0;
static int                   g_fb_h       = 0;
static long                  g_frame_cnt  = 0;

/* ============================================================
 * XU 参数 — 不同设备需修改！
 * lsusb -v -d VID:PID → 搜 bUnitID (XU_ID) 和 bInterfaceNumber (VC_IF)
 * ============================================================ */
#define XU_UNIT_ID              0x0A  // Extension Unit ID
#define VC_IF_NUM               0     // VideoControl interface number
#define CS_ID_THERMAL           0x03  // 热成像管理
#define SUBFUNC_STREAM_TYPE     0x05  // 码流类型配置
#define STREAM_TYPE_YUV_ONLY    0x0A  // 仅 YUV 实时流（无测温头）

/* 存储设备 VID/PID（全局，XU 切换时需要） */
static int g_vid = 0, g_pid = 0;

/* ============================================================
 * 发 XU 命令切换码流类型 → YUV_ONLY
 *
 * 独立开一个 libusb 句柄（不依赖 uvc 内部句柄），
 * 控制传输走 EP0，不需要 claim 接口，不影响 uvc 的 VS 管道。
 * ============================================================ */
static int xu_switch_stream_type(void)
{
    printf("[XU] Opening libusb for %04x:%04x ...\n", g_vid, g_pid);

    libusb_context       *ctx = NULL;
    libusb_device_handle *h   = NULL;

    libusb_init(&ctx);
    h = libusb_open_device_with_vid_pid(ctx, (uint16_t)g_vid, (uint16_t)g_pid);
    if (!h) {
        printf("[XU] ERROR: cannot open %04x:%04x\n", g_vid, g_pid);
        libusb_exit(ctx);
        return -1;
    }

    uint16_t wIndex = (uint16_t)((XU_UNIT_ID << 8) | VC_IF_NUM);
    int      ret;

    /* ---- 阶段 1: FUNC_SWITCH ---- */
    uint8_t sw_data[2] = { CS_ID_THERMAL, SUBFUNC_STREAM_TYPE };
    ret = libusb_control_transfer(h,
            0x21,           /* bmRequestType: OUT, Class, Interface */
            0x01,           /* bRequest: SET_CUR                    */
            0x0500,         /* wValue: CS_ID=0x05 (FUNC_SWITCH)     */
            wIndex,         /* wIndex: (XU_ID << 8) | VC_IF         */
            sw_data, 2,     /* data + length                        */
            1000);          /* timeout                              */
    if (ret != 2) {
        printf("[XU] FUNC_SWITCH FAILED: %s (ret=%d)\n",
               libusb_error_name(ret), ret);
        libusb_close(h); libusb_exit(ctx);
        return -1;
    }
    printf("[XU] ① FUNC_SWITCH OK → CS_ID=0x%02X SubFunc=0x%02X\n",
           CS_ID_THERMAL, SUBFUNC_STREAM_TYPE);

    /* ---- 阶段 2: GET_LEN ---- */
    uint8_t len_buf[2] = {0};
    ret = libusb_control_transfer(h,
            0xA1,           /* bmRequestType: IN, Class, Interface  */
            0x85,           /* bRequest: GET_LEN                    */
            (uint16_t)(CS_ID_THERMAL << 8), /* wValue               */
            wIndex,
            len_buf, 2, 1000);
    if (ret == 2)
        printf("[XU] ② GET_LEN → %u bytes\n", len_buf[0] | (len_buf[1] << 8));
    else
        printf("[XU] ② GET_LEN: ret=%d (non-fatal)\n", ret);

    /* ---- 阶段 3: SET_CUR (通道1, YUV_ONLY=10) ---- */
    uint8_t set_data[2] = { 0x01, STREAM_TYPE_YUV_ONLY };
    ret = libusb_control_transfer(h,
            0x21,           /* bmRequestType: OUT, Class, Interface */
            0x01,           /* bRequest: SET_CUR                    */
            (uint16_t)(CS_ID_THERMAL << 8), /* wValue               */
            wIndex,
            set_data, 2, 1000);
    if (ret != 2) {
        printf("[XU] SET_CUR FAILED: %s (ret=%d)\n",
               libusb_error_name(ret), ret);
        libusb_close(h); libusb_exit(ctx);
        return -1;
    }
    printf("[XU] ③ SET_CUR OK → YUV_ONLY (type=10)\n");

    libusb_close(h);
    libusb_exit(ctx);
    return 0;
}

/* ============================================================
 * SIGINT
 * ============================================================ */
static void sig_handler(int sig) { (void)sig; g_running = 0; }

/* ============================================================
 * 帧回调 — libuvc 线程，只转换不渲染
 *
 * 统一用 libuvc 的 uvc_any2rgb 做格式转换（它最懂 UVC 的各种 YUV 变体），
 * 然后 cv::cvtColor(RGB→BGR) 给 OpenCV 显示。
 * ============================================================ */
static void frame_cb(uvc_frame_t *frame, void *user_ptr)
{
    (void)user_ptr;

    if (!frame || !frame->data || frame->data_bytes == 0 ||
        frame->width == 0 || frame->height == 0)
        return;

    int w = frame->width;
    int h = frame->height;

    /* 首帧：打印信息 + 保存原始数据到磁盘 */
    if (g_frame_cnt == 0) {
        printf("[CB] First frame: %dx%d, fmt=%d, step=%zu, bytes=%zu\n",
               w, h, frame->frame_format,
               (size_t)frame->step, (size_t)frame->data_bytes);

        /* 保存前 3 帧原始数据，用 xxd 查看 */
        char fname[64];
        snprintf(fname, sizeof(fname),
                 "/tmp/raw_frame_%dx%d_fmt%d.bin", w, h, frame->frame_format);
        FILE *f = fopen(fname, "wb");
        if (f) {
            fwrite(frame->data, 1, frame->data_bytes, f);
            fclose(f);
            printf("[DEBUG] Saved: %s\n", fname);
        }
    }

    /* 前 3 帧也保存转换后的 BGR 图像 */
    if (g_frame_cnt < 3) {
        char fname[64];
        snprintf(fname, sizeof(fname), "/tmp/frame_%03ld.png", g_frame_cnt);
        /* 先转换再保存 */
    }

    cv::Mat bgr;

    /* ★ 关键修复：不少热成像摄像头描述符报 YUYV，实际送 MJPEG。
     * 检测帧数据是否以 JPEG SOI (FF D8) 开头来判断。 */
    const uint8_t *raw = (const uint8_t *)frame->data;
    int is_jpeg = (frame->data_bytes >= 2 &&
                   raw[0] == 0xFF && raw[1] == 0xD8);

    if (is_jpeg) {
        /* MJPEG → BGR：OpenCV 内置 JPEG 解码 */
        cv::Mat raw(1, (int)frame->data_bytes, CV_8UC1, frame->data);
        bgr = cv::imdecode(raw, cv::IMREAD_COLOR);
        if (bgr.empty() && g_frame_cnt == 0)
            fprintf(stderr, "[CB] JPEG imdecode failed\n");
    } else {
        /* 真·YUYV → RGB → BGR */
        size_t need = (size_t)w * h * 3;
        if (g_raw_frame == NULL || g_raw_frame->data_bytes < need) {
            if (g_raw_frame) uvc_free_frame(g_raw_frame);
            g_raw_frame = uvc_allocate_frame(need);
            if (!g_raw_frame) return;
        }

        uvc_error_t err = uvc_any2rgb(frame, g_raw_frame);
        if (err != UVC_SUCCESS) {
            if (g_frame_cnt == 0)
                fprintf(stderr, "[CB] uvc_any2rgb failed: %s\n", uvc_strerror(err));
            return;
        }
        cv::Mat rgb(h, w, CV_8UC3, g_raw_frame->data);
        cv::cvtColor(rgb, bgr, cv::COLOR_RGB2BGR);
    }

    if (bgr.empty()) return;

    /* 前 3 帧保存 PNG（诊断用） */
    if (g_frame_cnt < 3) {
        char fname[64];
        snprintf(fname, sizeof(fname), "/tmp/frame_%03ld.png", g_frame_cnt);
        cv::imwrite(fname, bgr);
        if (g_frame_cnt == 0)
            printf("[DEBUG] Saved first frames to /tmp/frame_*.png\n");
    }

    pthread_mutex_lock(&g_mutex);
    bgr.copyTo(g_bgr_frame);
    g_fb_w  = w;
    g_fb_h  = h;
    g_frame_cnt++;
    g_frame_ok = 1;
    pthread_mutex_unlock(&g_mutex);
}

/* ============================================================
 * 格式协商（和之前一样）
 * ============================================================ */
static uvc_error_t find_stream_params(uvc_device_handle_t *devh,
                                      uvc_stream_ctrl_t *ctrl_out)
{
    uvc_error_t ret;

    struct trial {
        enum uvc_frame_format fmt;
        int w, h, fps;
        const char *label;
    } trials[] = {
        { UVC_FRAME_FORMAT_YUYV, 0, 0, 0, "YUYV auto"        },
        { UVC_FRAME_FORMAT_MJPEG,0, 0, 0, "MJPEG auto"       },
        { UVC_FRAME_FORMAT_YUYV, 640, 480, 30, "YUYV 640x480@30" },
        { UVC_FRAME_FORMAT_MJPEG,640, 480, 30, "MJPEG 640x480@30" },
        { UVC_FRAME_FORMAT_YUYV, 320, 240, 30, "YUYV 320x240@30" },
        { UVC_FRAME_FORMAT_UNCOMPRESSED, 0, 0, 0, "UNCOMPRESSED auto" },
    };

    for (size_t i = 0; i < sizeof(trials)/sizeof(trials[0]); i++) {
        printf("[Stream] Try #%zu: %s\n", i+1, trials[i].label);
        ret = uvc_get_stream_ctrl_format_size(
            devh, ctrl_out, trials[i].fmt,
            trials[i].w, trials[i].h, trials[i].fps);
        if (ret == UVC_SUCCESS) {
            printf("[Stream] ✓ OK: fmt=%d, %dx%d@%d\n",
                   trials[i].fmt, trials[i].w, trials[i].h, trials[i].fps);
            return UVC_SUCCESS;
        }
    }

    /* 遍历描述符链 */
    printf("[Stream] Round 1 failed — raw descriptor walk...\n");
    const uvc_format_desc_t *fmt_list = uvc_get_format_descs(devh);
    if (!fmt_list) return ret;

    for (const uvc_format_desc_t *fmt = fmt_list; fmt; fmt = fmt->next) {
        enum uvc_frame_format ffmt =
            (fmt->bDescriptorSubtype == UVC_VS_FORMAT_MJPEG)
                ? UVC_FRAME_FORMAT_MJPEG : UVC_FRAME_FORMAT_YUYV;

        for (const uvc_frame_desc_t *frm = fmt->frame_descs; frm; frm = frm->next) {
            int w = frm->wWidth, h = frm->wHeight;
            int fps = (frm->dwDefaultFrameInterval > 0)
                ? (int)(10000000UL / frm->dwDefaultFrameInterval) : 15;

            printf("[Stream] Raw: 0x%02x %dx%d@%d\n",
                   fmt->bDescriptorSubtype, w, h, fps);
            ret = uvc_get_stream_ctrl_format_size(
                devh, ctrl_out, ffmt, w, h, fps);
            if (ret == UVC_SUCCESS)
                return UVC_SUCCESS;
            ret = uvc_get_stream_ctrl_format_size(
                devh, ctrl_out, ffmt, w, h, 0);
            if (ret == UVC_SUCCESS)
                return UVC_SUCCESS;
        }
    }

    return ret;
}

/* ============================================================
 * main
 * ============================================================ */
int main(int argc, char **argv)
{
    uvc_context_t       *ctx  = NULL;
    uvc_device_t        *dev  = NULL;
    uvc_device_handle_t *devh = NULL;
    uvc_stream_ctrl_t    ctrl;
    uvc_error_t          uvcret;

    /* ---- 命令行 ---- */
    int vid = 0, pid = 0;
    if (argc >= 2) {
        if (sscanf(argv[1], "%x:%x", &vid, &pid) != 2) {
            fprintf(stderr, "Usage: %s [VID:PID]  e.g. %s 2bdf:0102\n",
                    argv[0], argv[0]);
            return 1;
        }
    }

    /* ---- 1. libuvc ---- */
    uvcret = uvc_init(&ctx, NULL);
    if (uvcret != UVC_SUCCESS) {
        fprintf(stderr, "uvc_init: %s\n", uvc_strerror(uvcret));
        return 1;
    }

    /* ---- 2. 找设备 ---- */
    uvc_device_t **dev_list = NULL;
    uvc_get_device_list(ctx, &dev_list);
    if (!dev_list || !dev_list[0]) {
        fprintf(stderr, "No UVC devices\n");
        uvc_exit(ctx); return 1;
    }

    if (vid) {
        uvcret = uvc_find_device(ctx, &dev, vid, pid, NULL);
        if (uvcret != UVC_SUCCESS) {
            fprintf(stderr, "%04x:%04x not found\n", vid, pid);
            uvc_free_device_list(dev_list, 1);
            uvc_exit(ctx); return 1;
        }
    } else {
        dev = dev_list[0];
        uvc_ref_device(dev);
    }

    uvc_device_descriptor_t *desc;
    if (uvc_get_device_descriptor(dev, &desc) == UVC_SUCCESS) {
        printf("[Device] %s  %04x:%04x  S/N:%s\n",
               desc->product ? desc->product : "?",
               desc->idVendor, desc->idProduct,
               desc->serialNumber ? desc->serialNumber : "N/A");
        /* 记下实际 VID/PID，后续 XU 切换要用 */
        g_vid = desc->idVendor;
        g_pid = desc->idProduct;
        uvc_free_device_descriptor(desc);
    }

    /* ---- 2.5 Detach 内核驱动 + XU 切换码流类型 ---- */
    /* 必须在 uvc_open 之前做：设备"干净"时发 XU 命令最可靠 */
    {
        uint16_t dv = vid, dp = pid;
        if (dv == 0) {
            uvc_device_descriptor_t *dd;
            if (uvc_get_device_descriptor(dev, &dd) == UVC_SUCCESS) {
                dv = dd->idVendor; dp = dd->idProduct;
                uvc_free_device_descriptor(dd);
            }
        }
        libusb_context *usb_ctx = NULL;
        libusb_init(&usb_ctx);
        libusb_device_handle *usb_h =
            libusb_open_device_with_vid_pid(usb_ctx, dv, dp);
        if (!usb_h) {
            fprintf(stderr, "Cannot open %04x:%04x for setup\n", dv, dp);
            libusb_exit(usb_ctx);
        } else {
            /* ---- detach 内核驱动 ---- */
            for (int i = 0; i < 8; i++) {
                if (libusb_kernel_driver_active(usb_h, i) == 1) {
                    libusb_detach_kernel_driver(usb_h, i);
                    printf("[Detach] IF %d released\n", i);
                }
            }

            /* ---- XU: 切码流类型 → YUV_ONLY ---- */
            uint16_t wIdx = (uint16_t)((XU_UNIT_ID << 8) | VC_IF_NUM);
            int      r;

            /* ① FUNC_SWITCH: SET_CUR to CS_ID=0x05 */
            uint8_t sw[2] = { CS_ID_THERMAL, SUBFUNC_STREAM_TYPE };
            r = libusb_control_transfer(usb_h,
                    0x21, 0x01, 0x0500, wIdx, sw, 2, 1000);
            if (r == 2) {
                printf("[XU] ① FUNC_SWITCH OK\n");

                /* ② GET_LEN */
                uint8_t lb[2] = {0};
                r = libusb_control_transfer(usb_h,
                        0xA1, 0x85, (uint16_t)(CS_ID_THERMAL << 8),
                        wIdx, lb, 2, 1000);
                if (r == 2)
                    printf("[XU] ② GET_LEN → %u bytes\n",
                           lb[0] | (lb[1] << 8));

                /* ③ SET_CUR: [通道1, YUV_ONLY] */
                uint8_t sd[2] = { 0x01, STREAM_TYPE_YUV_ONLY };
                r = libusb_control_transfer(usb_h,
                        0x21, 0x01, (uint16_t)(CS_ID_THERMAL << 8),
                        wIdx, sd, 2, 1000);
                if (r == 2)
                    printf("[XU] ③ SET_CUR OK → YUV_ONLY\n");
                else
                    printf("[XU] ③ SET_CUR FAILED: %s\n",
                           libusb_error_name(r));
            } else {
                printf("[XU] ① FUNC_SWITCH FAILED: %s\n",
                       libusb_error_name(r));
            }

            libusb_close(usb_h);
            libusb_exit(usb_ctx);
            usleep(100000);
        }
    }

    uvcret = uvc_open(dev, &devh);
    if (uvcret != UVC_SUCCESS) {
        fprintf(stderr, "uvc_open: %s\n", uvc_strerror(uvcret));
        uvc_unref_device(dev);
        uvc_free_device_list(dev_list, 1);
        uvc_exit(ctx); return 1;
    }
    uvc_free_device_list(dev_list, 1);
    printf("[Open] OK\n");

    /* ---- 3. 协商格式 ---- */
    uvcret = find_stream_params(devh, &ctrl);
    if (uvcret != UVC_SUCCESS) {
        fprintf(stderr, "Stream negotiation failed\n");
        uvc_close(devh); uvc_unref_device(dev); uvc_exit(ctx);
        return 1;
    }

    /* ---- 4. OpenCV 窗口 ---- */
    cv::namedWindow("UVC Stream", cv::WINDOW_NORMAL);
    cv::resizeWindow("UVC Stream", 640, 480);
    printf("[OpenCV] Window ready\n");

    /* ---- 5. 开始取流 ---- */
    uvcret = uvc_start_streaming(devh, &ctrl, frame_cb, NULL, 0);
    if (uvcret != UVC_SUCCESS) {
        fprintf(stderr, "Stream start: %s\n", uvc_strerror(uvcret));
        cv::destroyAllWindows();
        uvc_close(devh); uvc_unref_device(dev); uvc_exit(ctx);
        return 1;
    }
    signal(SIGINT, sig_handler);

    printf("\n========================================\n");
    printf("  Streaming... ESC / q to quit\n");
    printf("========================================\n\n");

    /* ---- 6. 主循环 ---- */
    int    first_frame   = 1;
    time_t last_fps_tick = time(NULL);
    int    frame_count   = 0;

    while (g_running) {
        if (g_frame_ok) {
            pthread_mutex_lock(&g_mutex);

            if (!g_bgr_frame.empty()) {
                cv::imshow("UVC Stream", g_bgr_frame);

                if (first_frame) {
                    printf("[OpenCV] First frame: %dx%d (#%ld)\n",
                           g_bgr_frame.cols, g_bgr_frame.rows, g_frame_cnt);
                    first_frame = 0;
                }
                frame_count++;
            }

            g_frame_ok = 0;
            pthread_mutex_unlock(&g_mutex);

            time_t now = time(NULL);
            if (now - last_fps_tick >= 5) {
                double fps = frame_count / (double)(now - last_fps_tick);
                printf("[FPS] %.1f  %dx%d  total=%ld\n",
                       fps, g_fb_w, g_fb_h, g_frame_cnt);
                frame_count   = 0;
                last_fps_tick = now;
            }
        }

        int key = cv::waitKey(10);  // 10ms = 100Hz 轮询
        if (key == 27 || key == 'q' || key == 'Q')  // ESC 或 q
            g_running = 0;
        if (key == 'f' || key == 'F') {  // F 键全屏切换
            /* 简易全屏切换 */
        }
    }

    /* ---- 7. 清理 ---- */
    printf("\nShutting down...\n");
    uvc_stop_streaming(devh);
    uvc_close(devh);
    uvc_unref_device(dev);
    uvc_exit(ctx);
    if (g_raw_frame) uvc_free_frame(g_raw_frame);

    cv::destroyAllWindows();
    printf("Done.\n");
    return 0;
}
