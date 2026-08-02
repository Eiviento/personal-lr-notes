#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "libusb.h"
#include "debug.h"
#include "timestamp.h"
////////////////////////////////////////////////////////////
#define UVC_RT_OUT_CLASS    0x21
#define UVC_RT_IN_CLASS     0xA1
#define UVC_SET_CUR         0x01
#define UVC_GET_CUR         0x81
#define UVC_GET_LEN         0x85

#define XU_UNIT_ID          0x0A
#define VC_IF_NUM           (1)

// CS ID Definition
#define CS_ID_THERMAL       0x03    // 热成像测温管理
#define CS_ID_IMAGE         0x02    // 图像管理
#define CS_ID_PROTOCOL_VER  0x04    // 扩展协议版本探测
#define CS_ID_FUNC_SWITCH   0x05    // 功能切换
#define CS_ID_ERRCODE       0x06    // 错误码读取

// 子功能ID
#define SUBFUNC_IMG_ENHANCE     0x05    // 图像增强(PaletteMode)
#define SUBFUNC_STREAM_TYPE     0x05    // 实时上传码流类型配置

// 伪彩常量定义
#define PALETTE_WHITE_HEAT    1
#define PALETTE_BLACK_HEAT    2
#define PALETTE_FUSION1      10
#define PALETTE_RAINBOW      11
#define PALETTE_FUSION2      12
#define PALETTE_IRON_RED1    13
#define PALETTE_IRON_RED2    14
#define PALETTE_DARK_BROWN   15
#define PALETTE_COLOR1       16
#define PALETTE_COLOR2       17
#define PALETTE_ICE_FIRE     18
#define PALETTE_RAIN         19
#define PALETTE_RED_HEAT     20
#define PALETTE_GREEN_HEAT   21
#define PALETTE_DARK_BLUE    22

// 实时上传码流类型定义
#define STREAM_TYPE_TEMP_FULL                 2   // 全屏测温矩阵数据
#define STREAM_TYPE_NUC_NUCADD                3   //实时裸数据
#define STREAM_TYPE_YUV_HEADER                6   // YUV实时流(带测温头)
#define STREAM_TYPE_FULL_TEMP_YUV             8   // 全屏测温数据+YUV实时流(默认)
#define STREAM_TYPE_NUC_NUCADD_YUV_YUVADD     9   //实时裸数据+YUV
#define STREAM_TYPE_YUV_ONLY                  10  // 仅YUV实时流(无测温头)

// ===================== 【新增】视频流读取相关定义 =====================
#define VS_IF_NUM               0       // UVC Video Streaming 接口号
#define VS_EP_IN_ADDR           0x81    // 视频流批量IN端点地址
#define MAX_FRAME_BUF_SIZE      (640 * 512 * 2 * 2) // 单帧最大缓冲区
#define USB_STREAM_TIMEOUT      1000    // 单次USB传输超时(ms)
#define FRAME_MAGIC             0x70827773   // 帧头魔术字（小端）
// =====================================================================

// 设备VID/PID，替换为你实际设备的值
#define DEV_VID  0x2bdf
#define DEV_PID  0x0102

////////////////////////////////////////////////////////////
// ===================== 错误码描述函数 =====================
const char* tm5x_err_desc(uint8_t err)
{
    switch(err)
    {
        case 0x00: return "0x00 Normal, No Error";
        case 0x01: return "0x01 Previous Command Not Finished, Need Delay Poll";
        case 0x02: return "0x02 Current Device State Reject This Request";
        case 0x03: return "0x03 Device Power Supply Insufficient";
        case 0x04: return "0x04 Input Parameter Out Of Valid Range";
        case 0x05: return "0x05 Unsupported Unit ID";
        case 0x06: return "0x06 Unsupported CS ID";
        case 0x07: return "0x07 Unsupported bRequest Command";
        case 0x08: return "0x08 Parameter Legal But Invalid Value";
        case 0x09: return "0x09 Unsupported Sub-function";
        case 0x0A: return "0x0A Internal Device Exception";
        case 0x0C: return "0x0C Packet Length/Seq/Type Mismatch";
        case 0x0D: return "0x0D Invalid wLength In Control Transfer";
        case 0xFF: return "0xFF Unknown Device Error";
        default: return "Reserved Undefined Error Code";
    }
}

// ===================== 伪彩名称映射 =====================
const char* palette_name(uint8_t mode)
{
    switch(mode){
        case 1: return "White Heat";
        case 2: return "Black Heat";
        case 10: return "Fusion 1";
        case 11: return "Rainbow";
        case 12: return "Fusion 2";
        case 13: return "Iron Red 1";
        case 14: return "Iron Red 2";
        case 15: return "Dark Brown";
        case 16: return "Color 1";
        case 17: return "Color 2";
        case 18: return "Ice Fire";
        case 19: return "Rain";
        case 20: return "Red Heat";
        case 21: return "Green Heat";
        case 22: return "Dark Blue";
        default: return "Unknown Palette Mode";
    }
}

// ===================== 码流类型名称映射 =====================
const char* stream_type_name(uint8_t type)
{
    switch(type)
    {
        case 2:  return "STREAM_TYPE_TEMP_FULL";
        case 3:  return "STREAM_TYPE_NUC_NUCADD";
        case 6:  return "STREAM_TYPE_YUV_HEADER";
        case 8:  return "STREAM_TYPE_FULL_TEMP_YUV";
        case 9:  return "STREAM_TYPE_NUC_NUCADD_YUV_YUVADD";
        case 10: return "STREAM_TYPE_YUV_ONLY";
        default: return "STREAM_TYPE_Unknown";
    }
}

////////////////////////////////////////////////////////////
// ===================== 底层错误处理工具 =====================
// 读取设备自定义错误码
int tm5x_get_error_code(libusb_device_handle *devh, uint8_t *out_err)
{
	uint8_t buf[1] = {0};
    uint16_t wValue = (CS_ID_ERRCODE << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_CUR,
        wValue, wIndex, buf, 1, 1000
    );
    if (ret != 1)
    {
    	debug_printf("[ERR] Transfer Failed To Get Error Code, libusb_ret=%d | %s\n",
    			ret, libusb_error_name(ret));
        return -1;
    }
    *out_err = buf[0];
    return 0;
}

// 轮询等待设备空闲（解决0x01忙状态）
uint8_t tm5x_wait_cmd_finish(libusb_device_handle *devh, int interval_ms)
{
    uint8_t err = 0x01;
    while (err == 0x01)
    {
        int r = tm5x_get_error_code(devh, &err);
        if (r != 0) break;
        if (err == 0x01) usleep(interval_ms * 1000);
    }
    return err;
}

// 统一打印设备业务错误信息
void print_device_err(libusb_device_handle *devh, const char *op_name)
{
    uint8_t err_code = 0;
    int ret = tm5x_get_error_code(devh, &err_code);
    if(ret == 0)
    {
    	debug_printf("[%s] Device Error Code:0x%02X -> %s\n", op_name, err_code, tm5x_err_desc(err_code));
        if (err_code == 0x01)
        {
        	debug_printf("  Start polling for command complete...\n");
            uint8_t final_err = tm5x_wait_cmd_finish(devh, 10);
            debug_printf("  Polling Finished, Final Error Code:0x%02X -> %s\n", final_err, tm5x_err_desc(final_err));
        }
    }
    else
    {
    	debug_printf("[%s] Cannot read device error code, USB transfer failed\n", op_name);
    }
}

// ===================== UVC XU 基础传输封装 =====================
static int xu_get_len(libusb_device_handle *devh, uint8_t cs_id, uint16_t *out_len)
{
    uint8_t buf[2] = {0};
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_LEN,
        wValue, wIndex, buf, 2, 1000
    );
    if (ret != 2)
    {
        print_device_err(devh, "GET_LEN");
        return -1;
    }
    *out_len = (buf[1] << 8) | buf[0];
    return 0;
}

static int xu_switch_subfunc(libusb_device_handle *devh, uint8_t cs_id, uint8_t subfunc)
{
    uint8_t data[2] = {cs_id, subfunc};
    uint16_t wValue = (CS_ID_FUNC_SWITCH << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_OUT_CLASS, UVC_SET_CUR,
        wValue, wIndex, data, 2, 1000
    );
    if (ret < 0)
    {
        print_device_err(devh, "Function Switch");
        return -1;
    }
    return 0;
}

static int xu_get_cur(libusb_device_handle *devh, uint8_t cs_id, uint8_t *buf, uint16_t buf_len)
{
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_CUR,
        wValue, wIndex, buf, buf_len, 1000
    );
    if (ret <= 0)
    {
        print_device_err(devh, "GET_CUR Read Param");
        return -1;
    }
    return ret;
}

static int xu_set_cur(libusb_device_handle *devh, uint8_t cs_id, uint8_t *buf, uint16_t buf_len)
{
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_OUT_CLASS, UVC_SET_CUR,
        wValue, wIndex, buf, buf_len, 1000
    );
    if (ret < 0)
    {
        print_device_err(devh, "SET_CUR Write Param");
        return -1;
    }
    return 0;
}

// ===================== 【新增】小端字节序解析工具 =====================
static uint32_t le32_to_cpu(const uint8_t *buf)
{
    return (uint32_t)buf[0]
         | ((uint32_t)buf[1] << 8)
         | ((uint32_t)buf[2] << 16)
         | ((uint32_t)buf[3] << 24);
}
// ==================================================================

////////////////////////////////////////////////////////////
// ===================== 业务接口：查询协议版本 =====================
int tm5x_get_protocol_version(libusb_device_handle *devh, char *ver_buf, int buf_len)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t ver_raw[8] = {0};

    if (ver_buf == NULL || buf_len < 4)
    {
        debug_printf("[Protocol Ver] Invalid output buffer\n");
        return -1;
    }

    ret = xu_get_len(devh, CS_ID_PROTOCOL_VER, &param_len);
    if (ret != 0)
    {
        debug_printf("[Protocol Ver] GET_LEN failed\n");
        return -2;
    }
    if (param_len > sizeof(ver_raw))
    {
        debug_printf("[Protocol Ver] Param length %u exceeds buffer limit\n", param_len);
        return -3;
    }

    ret = xu_get_cur(devh, CS_ID_PROTOCOL_VER, ver_raw, param_len);
    if (ret <= 0)
    {
        debug_printf("[Protocol Ver] GET_CUR failed\n");
        return -4;
    }

    int copy_len = (param_len < buf_len - 1) ? param_len : (buf_len - 1);
    memcpy(ver_buf, ver_raw, copy_len);
    ver_buf[copy_len] = '\0';

    return 0;
}

// ===================== 业务接口：读取伪彩 =====================
int palette_mode_get(libusb_device_handle *devh, uint8_t *palette_out)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t img_enh_buf[128] = {0};

    ret = xu_switch_subfunc(devh, CS_ID_IMAGE, SUBFUNC_IMG_ENHANCE);
    if (ret != 0) return -1;

    ret = xu_get_len(devh, CS_ID_IMAGE, &param_len);
    if (ret != 0) return -2;
    if (param_len > sizeof(img_enh_buf))
    {
    	debug_printf("[Read Palette] Param Length Exceed Buffer Size\n");
        return -3;
    }

    ret = xu_get_cur(devh, CS_ID_IMAGE, img_enh_buf, param_len);
    if (ret <= 0) return -4;

    *palette_out = img_enh_buf[5];
    return 0;
}

// ===================== 业务接口：设置伪彩 =====================
int palette_mode_set(libusb_device_handle *devh, uint8_t new_palette)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t img_enh_buf[128] = {0};

    ret = xu_switch_subfunc(devh, CS_ID_IMAGE, SUBFUNC_IMG_ENHANCE);
    if (ret != 0) return -1;

    ret = xu_get_len(devh, CS_ID_IMAGE, &param_len);
    if (ret != 0) return -2;
    ret = xu_get_cur(devh, CS_ID_IMAGE, img_enh_buf, param_len);
    if (ret <= 0) return -3;

    img_enh_buf[5] = new_palette;

    ret = xu_set_cur(devh, CS_ID_IMAGE, img_enh_buf, param_len);
    if (ret != 0) return -4;

    uint8_t err;
    tm5x_get_error_code(devh, &err);
    if (err != 0x00)
    {
    	debug_printf("[Set Palette] Device Exception After Write:0x%02X -> %s\n", err, tm5x_err_desc(err));
        if (err == 0x01) tm5x_wait_cmd_finish(devh, 10);
        return -5;
    }
    return 0;
}

// ===================== 业务接口：获取当前码流类型 =====================
int get_stream_type(libusb_device_handle *devh, uint8_t *stream_type_out)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t buf[16] = {0};

    ret = xu_switch_subfunc(devh, CS_ID_THERMAL, SUBFUNC_STREAM_TYPE);
    if (ret != 0) return -1;

    ret = xu_get_len(devh, CS_ID_THERMAL, &param_len);
    if (ret != 0) return -2;
    if (param_len > sizeof(buf))
    {
        debug_printf("[Get Stream Type] Param Length Exceed Buffer Size\n");
        return -3;
    }

    ret = xu_get_cur(devh, CS_ID_THERMAL, buf, param_len);
    if (ret <= 0) return -4;

    debug_printf("");
    debug_array_print_x8(buf, param_len);

    // Offset 1 为 streamType 字段
    *stream_type_out = buf[1];
    return 0;
}

// ===================== 业务接口：设置码流类型 =====================
int set_stream_type(libusb_device_handle *devh, uint8_t new_stream_type)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t buf[16] = {0};

    ret = xu_switch_subfunc(devh, CS_ID_THERMAL, SUBFUNC_STREAM_TYPE);
    if (ret != 0) return -1;

    ret = xu_get_len(devh, CS_ID_THERMAL, &param_len);
    if (ret != 0) return -2;
    ret = xu_get_cur(devh, CS_ID_THERMAL, buf, param_len);
    if (ret <= 0) return -3;

    // 修改码流类型字段，保留channelID等原有字段
    buf[1] = new_stream_type;


    debug_printf("");
    debug_array_print_x8(buf, param_len);

    ret = xu_set_cur(devh, CS_ID_THERMAL, buf, param_len);
    if (ret != 0) return -4;

    // 写入后校验设备错误码
    uint8_t err;
    tm5x_get_error_code(devh, &err);
    if (err != 0x00)
    {
        debug_printf("[Set Stream Type] Device Exception After Write:0x%02X -> %s\n", err, tm5x_err_desc(err));
        if (err == 0x01) tm5x_wait_cmd_finish(devh, 10);
        return -5;
    }
    return 0;
}
int set_stream_type_2(libusb_device_handle *devh, uint8_t new_stream_type)
{
    int ret;
    uint16_t param_len = 0;
    uint8_t buf[16] = {0};
    uint8_t err;

    ret = xu_switch_subfunc(devh, CS_ID_THERMAL, SUBFUNC_STREAM_TYPE);
    if (ret != 0) return -1;

    ret = xu_get_len(devh, CS_ID_THERMAL, &param_len);
    if (ret != 0) return -2;
    ret = xu_get_cur(devh, CS_ID_THERMAL, buf, param_len);
    if (ret <= 0) return -3;

    // 强制通道号为1，符合协议“通道号限定为1”的要求
    buf[0] = 0x01;
    // 修改码流类型字段
    buf[1] = new_stream_type;

    debug_printf("");
    debug_array_print_x8(buf, param_len);

    ret = xu_set_cur(devh, CS_ID_THERMAL, buf, param_len);
    if (ret != 0) return -4;

    // ========== 修正：正确处理0x01忙状态 ==========
    // 1. 先读取一次错误码
    ret = tm5x_get_error_code(devh, &err);
    if (ret != 0)
    {
        debug_printf("[Set Stream Type] Failed to read error code after write\n");
        return -5;
    }

    // 2. 如果是忙状态，轮询等待执行完成
    if (err == 0x01)
    {
        debug_printf("[Set Stream Type] Device is processing switch, waiting...\n");
        // 等待函数会持续轮询，直到不是0x01，返回最终错误码
        err = tm5x_wait_cmd_finish(devh, 20); // 码流切换建议20ms间隔
    }

    // 3. 用最终错误码判断结果
    if (err != 0x00)
    {
        debug_printf("[Set Stream Type] Device Execute Failed, Final Error:0x%02X -> %s\n",
                     err, tm5x_err_desc(err));
        return -6;
    }

    // 码流切换完成后，增加少量延时再进行后续读取，确保状态完全稳定
    usleep(100 * 1000); // 100ms
    return 0;
}

// ===================== 【新增】业务接口：读取带头部的完整一帧 =====================
// 适配码流2/6/8，自动通过魔术字定位帧边界
int uvc_read_one_frame(libusb_device_handle *devh, uint8_t *frame_buf, int buf_size, int *out_frame_len)
{
    int ret;
    int total_recv = 0;
    int header_found = 0;
    uint8_t tmp_buf[512];

    if (frame_buf == NULL || out_frame_len == NULL || buf_size < 64)
    {
        debug_printf("[UVC Read] Invalid input parameter\n");
        return -1;
    }
    *out_frame_len = 0;

    // 查找帧头魔术字，对齐帧边界
    while (total_recv < buf_size)
    {
        int recv_len = 0;
        ret = libusb_bulk_transfer(devh, VS_EP_IN_ADDR, tmp_buf, sizeof(tmp_buf),
                                   &recv_len, USB_STREAM_TIMEOUT);
        if (ret != 0)
        {
            debug_printf("[UVC Read] Bulk transfer failed: %s\n", libusb_error_name(ret));
            return -2;
        }

        for (int i = 0; i <= recv_len - 4; i++)
        {
            uint32_t magic = le32_to_cpu(&tmp_buf[i]);
            if (magic == FRAME_MAGIC)
            {
                int copy_len = recv_len - i;
                if (copy_len > buf_size) copy_len = buf_size;
                memcpy(frame_buf, &tmp_buf[i], copy_len);
                total_recv = copy_len;
                header_found = 1;
                break;
            }
        }
        if (header_found) break;
    }

    if (!header_found)
    {
        debug_printf("[UVC Read] Cannot find frame magic word in stream\n");
        return -3;
    }

    // 读取完整帧头，获取总帧长
    while (total_recv < 16)
    {
        int recv_len = 0;
        ret = libusb_bulk_transfer(devh, VS_EP_IN_ADDR, frame_buf + total_recv,
                                   buf_size - total_recv, &recv_len, USB_STREAM_TIMEOUT);
        if (ret != 0) return -4;
        total_recv += recv_len;
    }

    uint32_t header_size = le32_to_cpu(frame_buf + 4);
    uint32_t stream_len = le32_to_cpu(frame_buf + 12);
    uint32_t total_frame_len = header_size + stream_len;

    if (total_frame_len > (uint32_t)buf_size)
    {
        debug_printf("[UVC Read] Frame size %u exceeds buffer limit\n", total_frame_len);
        return -5;
    }

    // 读取剩余帧数据
    while (total_recv < (int)total_frame_len)
    {
        int recv_len = 0;
        int remain = (int)total_frame_len - total_recv;
        int read_size = (remain > (int)sizeof(tmp_buf)) ? (int)sizeof(tmp_buf) : remain;

        ret = libusb_bulk_transfer(devh, VS_EP_IN_ADDR, frame_buf + total_recv,
                                   read_size, &recv_len, USB_STREAM_TIMEOUT);
        if (ret != 0) return -6;
        total_recv += recv_len;
    }

    *out_frame_len = total_recv;
    return 0;
}

// ===================== 【新增】业务接口：读取纯YUV帧（码流10专用） =====================
int uvc_read_yuv_only_frame_0(libusb_device_handle *devh, uint8_t *yuv_buf, int buf_size,
                            int width, int height, int *out_yuv_len)
{
    int ret;
    int total_recv = 0;
    int frame_size = width * height * 2; // YUV422 每像素占2字节

    if (yuv_buf == NULL || buf_size < frame_size)
    {
        debug_printf("[YUV Read] Buffer too small or invalid param\n");
        return -1;
    }

    while (total_recv < frame_size)
    {
        int recv_len = 0;
        int remain = frame_size - total_recv;
        int read_size = (remain > 512) ? 512 : remain;

        ret = libusb_bulk_transfer(devh, VS_EP_IN_ADDR, yuv_buf + total_recv,
                                   read_size, &recv_len, USB_STREAM_TIMEOUT);
        debug_printf("recv_len = %d", recv_len);
        if (ret != 0)
        {
            debug_printf("[YUV Read] Bulk transfer failed: %s\n", libusb_error_name(ret));
            return -2;
        }
        debug_printf("");
        total_recv += recv_len;
    }

    *out_yuv_len = total_recv;
    return 0;
}
int uvc_read_yuv_only_frame(libusb_device_handle *devh, uint8_t *yuv_buf, int buf_size,
                            int width, int height, int *out_yuv_len)
{
    int ret;
    int total_recv = 0;
    int frame_size = 640 * 512 * 2; // YUV422 每像素占2字节
    int recv_len = 0;

    if (yuv_buf == NULL || buf_size < frame_size)
    {
        debug_printf("[YUV Read] Buffer too small or invalid param\n");
        return -1;
    }

    while (total_recv < frame_size)
    {
        ret = libusb_bulk_transfer(
        		devh,
				0x81,//VS_EP_IN_ADDR,
				yuv_buf,
        		frame_size,
				&recv_len,
				1000000);
        debug_printf("%ld, recv_len = %d", timestamp_get_ms(), recv_len);
        if (ret != 0)
        {
            debug_printf("[YUV Read] Bulk transfer failed: %s\n", libusb_error_name(ret));
            return -2;
        }
        //debug_printf("");
    }

    *out_yuv_len = total_recv;
    return 0;
}

// ==================================================================

// ===================== 主测试函数 =====================
int TM76_libusb_main_3(void)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int r;
    uint8_t palette = 0;
    debug_printf("");

    // libusb初始化
    r = libusb_init(&ctx);
    if (r < 0)
    {
    	debug_printf("libusb Init Failed: %s\n", libusb_error_name(r));
        goto exit;
    }
    debug_printf("");

    // 打开测温设备
    devh = libusb_open_device_with_vid_pid(ctx, DEV_VID, DEV_PID);
    if (!devh)
    {
    	debug_printf("Cannot Open Device %04x:%04x, Check VID/PID And Permission\n", DEV_VID, DEV_PID);
        goto exit;
    }
    debug_printf("");

    // Linux系统解绑内核uvc驱动 Windows请注释这两段
    int detach_ret = -1;
    if (libusb_kernel_driver_active(devh, VC_IF_NUM))
    {
    	debug_printf("");
        detach_ret = libusb_detach_kernel_driver(devh, VC_IF_NUM);
        if (detach_ret < 0)
        {
        	debug_printf("Detach Kernel Driver Failed, ret=%d | %s\n", detach_ret, libusb_error_name(detach_ret));
            goto close_dev;
        }
        debug_printf("Detach kernel driver success\n");
    }

    // 申请接口
    r = libusb_claim_interface(devh, VC_IF_NUM);
    if (r < 0)
    {
    	debug_printf("");
    	debug_printf("libusb_claim_interface Failed, ret=%d | %s\n", r, libusb_error_name(r));
        debug_printf("");
        debug_printf("Try to read device error code after claim fail:\n");
        debug_printf("");
        print_device_err(devh, "Claim Interface Fail Check");
        debug_printf("");
        goto reattach;
    }
    debug_printf("Claim VC interface success\n");
    debug_printf("");

    // ========== 0. 查询UVC扩展协议版本 ==========
    debug_printf("========== 0. Query UVC Extension Protocol Version ==========\n");
    char protocol_ver[16] = {0};
    r = tm5x_get_protocol_version(devh, protocol_ver, sizeof(protocol_ver));
    if (r == 0)
    {
        debug_printf("UVC Extension Protocol Version: %s\n", protocol_ver);
        if (strcmp(protocol_ver, "2.0") != 0)
        {
            debug_printf("[WARN] Protocol version mismatch, expected 2.0, some features may be incompatible\n");
        }
    }
    else
    {
        debug_printf("Get protocol version failed, ret code: %d\n", r);
    }
    debug_printf("");

    debug_printf("========== 1. Read Current Palette Mode ==========\n");
    r = palette_mode_get(devh, &palette);
    if (r == 0)
    {
    	debug_printf("Current Palette ID: %d | Name: %s\n", palette, palette_name(palette));
    }
    else
    {
    	debug_printf("Read Palette Failed, Ret Code:%d\n", r);
    }

    debug_printf("========== 2. Set Palette To PALETTE_IRON_RED1(13) ==========\n");
    r = palette_mode_set(devh, PALETTE_IRON_RED1);
    if (r == 0)
    {
    	debug_printf("Set Rainbow Palette Success\n");
        uint8_t new_pal;
        palette_mode_get(devh, &new_pal);
        debug_printf("Verify Current Palette: %d | %s\n", new_pal, palette_name(new_pal));
    }
    else
    {
    	debug_printf("Set Rainbow Palette Failed, Ret Code:%d\n", r);
    }

    debug_printf("========== 3. Read Current Palette Mode ==========\n");
    r = palette_mode_get(devh, &palette);
    if (r == 0)
    {
    	debug_printf("Current Palette ID: %d | Name: %s\n", palette, palette_name(palette));
    }
    else
    {
    	debug_printf("Read Palette Failed, Ret Code:%d\n", r);
    }

    // ========== 新增：码流类型配置测试 ==========
    debug_printf("========== 4. Get Current Stream Type ==========\n");
    uint8_t stream_type = 0;
    r = get_stream_type(devh, &stream_type);
    if (r == 0)
    {
        debug_printf("Current Stream Type: %d | %s\n", stream_type, stream_type_name(stream_type));
    }
    else
    {
        debug_printf("Get Stream Type Failed, Ret Code:%d\n", r);
    }

    debug_printf("========== 5. Set Stream Type To YUV Only (Type 10) ==========\n");
    r = set_stream_type_2(devh, STREAM_TYPE_YUV_ONLY);
    if (r == 0)
    {
        debug_printf("Set YUV Only Stream Success\n");
        uint8_t verify_type;
        get_stream_type(devh, &verify_type);
        debug_printf("Verify Current Stream Type: %d | %s\n", verify_type, stream_type_name(verify_type));
    }
    else
    {
        debug_printf("Set Stream Type Failed, Ret Code:%d\n", r);
        goto reattach_vs;
    }

    debug_printf("sleep_start");
    sleep(1);
    debug_printf("sleep_end__");

    // ===================== 【新增】视频流读取测试 =====================
    debug_printf("========== 6. Claim VS Streaming Interface ==========\n");
    int vs_detach_ret = -1;
    if (libusb_kernel_driver_active(devh, VS_IF_NUM))
    {
        vs_detach_ret = libusb_detach_kernel_driver(devh, VS_IF_NUM);
        if (vs_detach_ret < 0)
        {
            debug_printf("Detach VS kernel driver failed: %s\n", libusb_error_name(vs_detach_ret));
            goto reattach_vs;
        }
        debug_printf("Detach VS kernel driver success\n");
    }

    r = libusb_claim_interface(devh, VS_IF_NUM);
    if (r < 0)
    {
        debug_printf("Claim VS interface failed: %s\n", libusb_error_name(r));
        goto reattach_vs;
    }
    debug_printf("Claim VS interface success\n");
    debug_printf("");

    debug_printf("sleep_start");
    sleep(1);
    debug_printf("sleep_end__");

    debug_printf("========== 7. Read YUV Only Frame ==========\n");
    uint8_t *yuv_buf = (uint8_t *)malloc(MAX_FRAME_BUF_SIZE);
    if (yuv_buf)
    {
        int yuv_len = 0;
        // 根据设备型号修改分辨率：TM52=256x192, TM53=384x288, TM56=640x512
        r = uvc_read_yuv_only_frame(devh, yuv_buf, MAX_FRAME_BUF_SIZE, 640, 512, &yuv_len);
        if (r == 0)
        {
            debug_printf("Read YUV frame success, size: %d bytes\n", yuv_len);
        }
        else
        {
            debug_printf("Read YUV frame failed, ret: %d\n", r);
        }
        free(yuv_buf);
    }
    else
    {
        debug_printf("Malloc YUV buffer failed\n");
    }
    debug_printf("");

    // 释放VS接口
    libusb_release_interface(devh, VS_IF_NUM);
    debug_printf("Release VS interface done\n");
    // ==================================================================

    // 释放资源
reattach_vs:
    if(vs_detach_ret == 0)
    {
        libusb_attach_kernel_driver(devh, VS_IF_NUM);
        debug_printf("Reattach VS kernel driver done\n");
    }

reattach:
    if(detach_ret == 0)
    {
        libusb_attach_kernel_driver(devh, VC_IF_NUM);
        debug_printf("Reattach kernel driver done\n");
    }
close_dev:
    libusb_close(devh);
exit:
    libusb_exit(ctx);
    return 0;
}
