/**
 * uvc_xu_subfunc_framework.c
 * UVC Extension Unit 扩展协议框架 — CS_ID + SubFunc 二级命名空间
 *
 * 设计思路：
 *   CS_ID 只有 1 字节（最多 255 个功能号），每个功能下可能有多个子功能。
 *   引入 SubFunc ID 实现分层命名空间，通过 FUNC_SWITCH（CS_ID=0x05）锁定目标。
 *   总控制能力从 255 扩展到 255×255 ≈ 65,000。
 *
 * 三阶段流程：
 *   1. FUNC_SWITCH  → 选择 CS_ID + SubFunc
 *   2. GET_LEN      → 获取参数长度
 *   3. GET_CUR/SET_CUR → 读写参数数据
 *
 * 依赖：libusb-1.0, debug.h, timestamp.h
 * 参考：HIKVISION_TM76_libusb_3.c（海康 TM76 热成像仪控制）
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "libusb.h"
#include "debug.h"

/* ============================================================
 * UVC 标准定义
 * ============================================================ */
#define UVC_RT_OUT_CLASS    0x21    // Host→Device, Class, Interface
#define UVC_RT_IN_CLASS     0xA1    // Device→Host, Class, Interface
#define UVC_SET_CUR         0x01    // 写当前参数值
#define UVC_GET_CUR         0x81    // 读当前参数值
#define UVC_GET_LEN         0x85    // 读参数长度

/* XU 地址 */
#define XU_UNIT_ID          0x0A    // Extension Unit ID
#define VC_IF_NUM           1       // Video Control 接口号

/* ============================================================
 * CS_ID 定义（功能大类）
 * ============================================================ */
#define CS_ID_FUNC_SWITCH   0x05    // 功能切换（协议基础设施）
#define CS_ID_ERRCODE       0x06    // 错误码读取
#define CS_ID_PTZ_CONTROL   0x17    // 云台相机控制
#define CS_ID_IMAGE_CONFIG  0x18    // 图像参数
#define CS_ID_SYS_INFO      0x19    // 系统信息

/* ============================================================
 * SubFunc ID — CS_ID=0x17 云台控制
 * ============================================================ */
#define SUBFUNC_PAN         0x01    // 水平角度 (uint32 LE, 0.1°)
#define SUBFUNC_TILT        0x02    // 垂直角度 (int32 LE, 0.1°)
#define SUBFUNC_ZOOM        0x03    // 变倍 (uint16 LE, 1x)
#define SUBFUNC_FOCUS       0x04    // 对焦 (uint16 LE)
#define SUBFUNC_PRESET      0x05    // 预置位 (6B struct)

/* ============================================================
 * SubFunc ID — CS_ID=0x18 图像参数
 * ============================================================ */
#define SUBFUNC_BRIGHTNESS  0x01    // 亮度 (int16 LE)
#define SUBFUNC_CONTRAST    0x02    // 对比度 (int16 LE)
#define SUBFUNC_SATURATION  0x03    // 饱和度 (int16 LE)
#define SUBFUNC_SHARPNESS   0x04    // 锐度 (int16 LE)
#define SUBFUNC_PALETTE     0x05    // 伪彩模式 (uint8)

/* ============================================================
 * 错误码（兼容海康 TM5x 协议）
 * ============================================================ */
const char* xu_err_desc(uint8_t err)
{
    switch(err) {
        case 0x00: return "Normal, No Error";
        case 0x01: return "Previous Command Not Finished, Need Delay Poll";
        case 0x02: return "Current Device State Reject This Request";
        case 0x03: return "Device Power Supply Insufficient";
        case 0x04: return "Input Parameter Out Of Valid Range";
        case 0x05: return "Unsupported Unit ID";
        case 0x06: return "Unsupported CS ID";
        case 0x07: return "Unsupported bRequest Command";
        case 0x08: return "Parameter Legal But Invalid Value";
        case 0x09: return "Unsupported Sub-function";
        case 0x0A: return "Internal Device Exception";
        case 0xFF: return "Unknown Device Error";
        default:   return "Reserved Undefined Error Code";
    }
}

/* ============================================================
 * 底层工具：读设备错误码
 * ============================================================ */
int xu_get_error_code(libusb_device_handle *devh, uint8_t *out_err)
{
    uint8_t buf[1] = {0};
    uint16_t wValue = (CS_ID_ERRCODE << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_CUR,
        wValue, wIndex, buf, 1, 1000);
    if (ret != 1) return -1;
    *out_err = buf[0];
    return 0;
}

/* ============================================================
 * 第 1 步：FUNC_SWITCH — 选择 CS_ID + SubFunc
 *
 * Bus Hound:
 *   CTL  21 01  05 00  00 0A  02 00    ← SET_CUR, CS_ID=0x05(FUNC_SWITCH)
 *   OUT  17 01                         ← data = [CS_ID=0x17, SubFunc=0x01]
 *
 * USB 总线事务:
 *   SETUP:  SETUP Token → DATA0{8B} → Device ACK
 *   DATA:   OUT Token → DATA1{17 01} → Device ACK
 *   STATUS: IN Token → DATA0(ZLP) → Host ACK  (Device确认切换)
 * ============================================================ */
int xu_switch_subfunc(libusb_device_handle *devh,
                      uint8_t cs_id, uint8_t subfunc)
{
    uint8_t data[2] = {cs_id, subfunc};
    uint16_t wValue = (CS_ID_FUNC_SWITCH << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_OUT_CLASS, UVC_SET_CUR,
        wValue, wIndex, data, 2, 1000);
    if (ret < 0) {
        debug_printf("[FUNC_SWITCH] CS=0x%02X Sub=0x%02X failed: %s\n",
                     cs_id, subfunc, libusb_error_name(ret));
        return -1;
    }
    return 0;
}

/* ============================================================
 * 第 2 步：GET_LEN — 获取参数长度（统一返回 2 字节 LE）
 *
 * Bus Hound:
 *   CTL  A1 85  00 17  00 0A  02 00    ← GET_LEN, CS_ID=0x17
 *   IN   04 00                         ← param_len = 4
 *
 * USB 总线事务:
 *   SETUP:  SETUP Token → DATA0{8B} → Device ACK
 *   DATA:   IN Token → DATA1{04 00} → Host ACK
 *   STATUS: OUT Token → DATA1(ZLP) → Device ACK
 * ============================================================ */
static int xu_get_len(libusb_device_handle *devh, uint8_t cs_id,
                      uint16_t *out_len)
{
    uint8_t buf[2] = {0};
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_LEN,
        wValue, wIndex, buf, 2, 1000);
    if (ret != 2) {
        debug_printf("[GET_LEN] CS=0x%02X failed: %s\n",
                     cs_id, libusb_error_name(ret));
        return -1;
    }
    *out_len = (buf[1] << 8) | buf[0];  // LE → CPU
    return 0;
}

/* ============================================================
 * 第 3 步（读）：GET_CUR — 读取当前 SubFunc 的参数
 *
 * Bus Hound:
 *   CTL  A1 81  00 17  00 0A  04 00    ← GET_CUR, CS_ID=0x17, wLength=4
 *   IN   2C 01 00 00                   ← pan_value = 0x012C = 300
 * ============================================================ */
static int xu_get_cur(libusb_device_handle *devh, uint8_t cs_id,
                      uint8_t *buf, uint16_t buf_len)
{
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_IN_CLASS, UVC_GET_CUR,
        wValue, wIndex, buf, buf_len, 1000);
    if (ret <= 0) {
        debug_printf("[GET_CUR] CS=0x%02X failed: %s\n",
                     cs_id, libusb_error_name(ret));
        return -1;
    }
    return ret;  // 返回实际读取字节数
}

/* ============================================================
 * 第 3 步（写）：SET_CUR — 写入参数到当前 SubFunc
 *
 * Bus Hound:
 *   CTL  21 01  17 00  00 0A  04 00    ← SET_CUR, CS_ID=0x17, wLength=4
 *   OUT  C2 01 00 00                   ← 目标值 0x01C2 = 450
 *
 * USB 总线事务:
 *   SETUP:  SETUP Token → DATA0{8B} → Device ACK
 *   DATA:   OUT Token → DATA1{4B data} → Device ACK
 *   STATUS: IN Token → DATA0(ZLP) → Host ACK  (Device确认接收)
 * ============================================================ */
static int xu_set_cur(libusb_device_handle *devh, uint8_t cs_id,
                      uint8_t *buf, uint16_t buf_len)
{
    uint16_t wValue = (cs_id << 8);
    uint16_t wIndex = (XU_UNIT_ID << 8) | VC_IF_NUM;
    int ret = libusb_control_transfer(
        devh, UVC_RT_OUT_CLASS, UVC_SET_CUR,
        wValue, wIndex, buf, buf_len, 1000);
    if (ret < 0) {
        debug_printf("[SET_CUR] CS=0x%02X failed: %s\n",
                     cs_id, libusb_error_name(ret));
        return -1;
    }
    return 0;
}

/* ============================================================
 * 高层封装：读 SubFunc 参数（三合一）
 *
 * 调用示例：
 *   uint8_t buf[8];
 *   int ret = xu_subfunc_get(devh, CS_ID_PTZ_CONTROL, SUBFUNC_PAN, buf, 8);
 *   // buf = {0x2C, 0x01, 0x00, 0x00} → Pan = 30.0°
 * ============================================================ */
int xu_subfunc_get(libusb_device_handle *devh,
                   uint8_t cs_id, uint8_t subfunc,
                   uint8_t *buf, uint16_t buf_size)
{
    uint16_t param_len = 0;
    int ret;

    // 1. 切换子功能
    ret = xu_switch_subfunc(devh, cs_id, subfunc);
    if (ret < 0) return -1;

    // 2. 获取参数长度
    ret = xu_get_len(devh, cs_id, &param_len);
    if (ret < 0) return -2;

    if (param_len == 0) return 0;   // 无参数
    if (param_len > buf_size) {
        debug_printf("[SubFunc GET] Param length %u exceeds buffer %u\n",
                     param_len, buf_size);
        return -3;
    }

    // 3. 读参数
    ret = xu_get_cur(devh, cs_id, buf, param_len);
    if (ret < 0) return -4;
    return ret;  // 返回实际读取字节数
}

/* ============================================================
 * 高层封装：写 SubFunc 参数（三合一 + 错误校验）
 *
 * 调用示例：
 *   uint32_t target = 450;  // 45.0°
 *   int ret = xu_subfunc_set(devh, CS_ID_PTZ_CONTROL, SUBFUNC_PAN,
 *                            (uint8_t*)&target, 4);
 * ============================================================ */
int xu_subfunc_set(libusb_device_handle *devh,
                   uint8_t cs_id, uint8_t subfunc,
                   uint8_t *buf, uint16_t data_len)
{
    int ret;

    // 1. 切换子功能
    ret = xu_switch_subfunc(devh, cs_id, subfunc);
    if (ret < 0) return -1;

    // 2. 写参数
    ret = xu_set_cur(devh, cs_id, buf, data_len);
    if (ret < 0) return -2;

    // 3. 读错误码确认
    uint8_t err = 0;
    ret = xu_get_error_code(devh, &err);
    if (ret < 0) {
        debug_printf("[SubFunc SET] Cannot read error code after write\n");
        return -3;
    }

    if (err != 0x00) {
        debug_printf("[SubFunc SET] Device error: 0x%02X — %s\n",
                     err, xu_err_desc(err));
        return -(100 + err);  // 负错误码便于调用方 switch
    }

    return 0;  // 成功
}

/* ============================================================
 * 使用示例（放在 main 或测试函数中）
 * ============================================================ */
#if 0
int example_usage(libusb_device_handle *devh)
{
    int ret;

    // ==== 示例 1：读云台水平角度 ====
    uint8_t pan_buf[4] = {0};
    ret = xu_subfunc_get(devh, CS_ID_PTZ_CONTROL, SUBFUNC_PAN,
                         pan_buf, sizeof(pan_buf));
    if (ret > 0) {
        uint32_t pan_val = pan_buf[0]
                         | (pan_buf[1] << 8)
                         | (pan_buf[2] << 16)
                         | (pan_buf[3] << 24);
        debug_printf("Pan = %.1f°\n", pan_val / 10.0);
    }

    // ==== 示例 2：设置水平角度到 45.0° ====
    uint32_t target = 450;  // 45.0° × 10
    ret = xu_subfunc_set(devh, CS_ID_PTZ_CONTROL, SUBFUNC_PAN,
                         (uint8_t*)&target, 4);

    // ==== 示例 3：读图像亮度 ====
    uint8_t bright_buf[2] = {0};
    ret = xu_subfunc_get(devh, CS_ID_IMAGE_CONFIG, SUBFUNC_BRIGHTNESS,
                         bright_buf, 2);
    if (ret > 0) {
        int16_t brightness = bright_buf[0] | (bright_buf[1] << 8);
        debug_printf("Brightness = %d\n", brightness);
    }

    // ==== 示例 4：变倍到 10x ====
    uint16_t zoom = 10;
    ret = xu_subfunc_set(devh, CS_ID_PTZ_CONTROL, SUBFUNC_ZOOM,
                         (uint8_t*)&zoom, 2);

    return 0;
}
#endif
