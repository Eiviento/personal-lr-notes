/**
 * xu_interactive.c — UVC XU 交互式调试工具
 *
 * 功能：
 *   1. 预置常见 VID/PID 列表，方向键选择
 *   2. 手动输入 CS_ID 和 SubFunc（0x04/0x05 自动跳过 FUNC_SWITCH）
 *   3. 每步控制传输实时展示 SETUP 包 8 字节，关联之前讲的协议理论
 *
 * 编译：gcc -o xu_interactive xu_interactive.c -lusb-1.0
 * 运行：sudo ./xu_interactive
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <libusb-1.0/libusb.h>

/* ============================================================
 * 预置设备列表（可自行添加）
 * ============================================================ */
typedef struct {
    const char *name;
    uint16_t vid;
    uint16_t pid;
    uint8_t  xu_unit_id;   // lsusb -v 查 bUnitID
    uint8_t  vc_if_num;    // Video Control 接口号
} device_entry_t;

static const device_entry_t DEVICE_LIST[] = {
    { "HIK HikCamera (2bdf:0101)  — 当前热成像", 0x2bdf, 0x0101, 0x0A, 0 },
    { "HIK TM76      (2bdf:0102)  — 参考代码设备", 0x2bdf, 0x0102, 0x0A, 1 },
};

#define DEVICE_COUNT (sizeof(DEVICE_LIST) / sizeof(DEVICE_LIST[0]))

/* ============================================================
 * UVC Class 请求常量
 * ============================================================ */
#define UVC_RT_OUT_CLASS    0x21    // Host→Device, Class, Interface
#define UVC_RT_IN_CLASS     0xA1    // Device→Host, Class, Interface
#define UVC_SET_CUR         0x01
#define UVC_GET_CUR         0x81
#define UVC_GET_LEN         0x85

#define CS_ID_FUNC_SWITCH   0x05

/* ============================================================
 * 当前设备上下文
 * ============================================================ */
static libusb_device_handle *g_devh;
static uint8_t  g_xu_unit_id;
static uint8_t  g_vc_if_num;

/* ============================================================
 * SETUP 包 8 字节打印 — 连接协议理论
 * ============================================================ */

// bmRequestType 的 D7 方向
static const char *dir_str(uint8_t bmRT) {
    return (bmRT & 0x80) ? "IN  (Device→Host)" : "OUT (Host→Device)";
}

// D6-5 字典
static const char *type_str(uint8_t bmRT) {
    switch ((bmRT >> 5) & 0x03) {
        case 0: return "Standard";
        case 1: return "Class";
        case 2: return "Vendor";
        default: return "Reserved";
    }
}

// D4-0 接收者
static const char *recip_str(uint8_t bmRT) {
    switch (bmRT & 0x1F) {
        case 0: return "Device";
        case 1: return "Interface";
        case 2: return "Endpoint";
        default: return "Other";
    }
}

// bRequest 名称
static const char *breq_str(uint8_t br) {
    switch (br) {
        case UVC_SET_CUR: return "SET_CUR (0x01)";
        case UVC_GET_CUR: return "GET_CUR (0x81)";
        case UVC_GET_LEN: return "GET_LEN (0x85)";
        default:          return "?";
    }
}

// CS_ID 名称（已知的）
static const char *csid_name(uint8_t cs_id) {
    switch (cs_id) {
        case 0x02: return "IMAGE";
        case 0x03: return "THERMAL";
        case 0x04: return "PROTOCOL_VER";
        case 0x05: return "FUNC_SWITCH";
        case 0x06: return "ERRCODE";
        default:   return "?";
    }
}

/**
 * 打印一个 SETUP 包的 8 字节并逐字段解释
 *
 * bmRT:  bmRequestType
 * br:    bRequest
 * wVal:  wValue (host byte order)
 * wIdx:  wIndex (host byte order)
 * wLen:  wLength (host byte order)
 * desc:  this transfer's purpose
 */
static void print_setup_packet(uint8_t bmRT, uint8_t br,
                                uint16_t wVal, uint16_t wIdx, uint16_t wLen,
                                const char *desc)
{
    /* 还原 LE 字节序 */
    uint8_t raw[8];
    raw[0] = bmRT;
    raw[1] = br;
    raw[2] = (uint8_t)(wVal & 0xFF);        // wValue 低字节
    raw[3] = (uint8_t)(wVal >> 8);          // wValue 高字节 (CS_ID)
    raw[4] = (uint8_t)(wIdx & 0xFF);        // wIndex 低字节 (IF num)
    raw[5] = (uint8_t)(wIdx >> 8);          // wIndex 高字节 (XU Unit ID)
    raw[6] = (uint8_t)(wLen & 0xFF);
    raw[7] = (uint8_t)(wLen >> 8);

    printf("\n");
    printf("  ┌─────────────────────────────────────────────────────────┐\n");
    printf("  │  SETUP Packet — %-38s │\n", desc);
    printf("  ├────┬────┬────┬────┬────┬────┬────┬────┬──────────────────┤\n");
    printf("  │ +0 │ +1 │ +2 │ +3 │ +4 │ +5 │ +6 │ +7 │  Field           │\n");
    printf("  ├────┼────┼────┼────┼────┼────┼────┼────┼──────────────────┤\n");
    printf("  │%02X  │%02X  │%02X  │%02X  │%02X  │%02X  │%02X  │%02X  │ raw hex          │\n",
           raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6], raw[7]);
    printf("  ├────┴────┴────┴────┴────┴────┴────┴────┼──────────────────┤\n");
    printf("  │ bmRequestType  = 0x%02X                 │ D7=%s        │\n",
           bmRT, (bmRT & 0x80) ? "1 IN" : "0 OUT");
    printf("  │                                       │ D6-5=%d%d → %-7s   │\n",
           (bmRT >> 6) & 1, (bmRT >> 5) & 1, type_str(bmRT));
    printf("  │                                       │ D4-0=%d → %-8s  │\n",
           bmRT & 0x1F, recip_str(bmRT));
    printf("  │ bRequest       = 0x%02X                 │ %-16s │\n",
           br, breq_str(br));
    printf("  │ wValue         = 0x%04X               │ CS_ID=0x%02X (%s)   │\n",
           wVal, wVal >> 8, csid_name(wVal >> 8));
    printf("  │ wIndex         = 0x%04X               │ XU_ID=0x%02X, IF=%d     │\n",
           wIdx, wIdx >> 8, wIdx & 0xFF);
    printf("  │ wLength        = %-5u                 │ DATA 阶段字节数   │\n",
           wLen);
    printf("  └───────────────────────────────────────┴──────────────────┘\n");
}

/* ============================================================
 * 底层传输（带 SETUP 包打印）
 * ============================================================ */

static int xu_control_transfer(uint8_t bmRT, uint8_t br,
                                uint16_t wVal, uint16_t wIdx,
                                uint8_t *data, uint16_t wLen,
                                const char *desc)
{
    print_setup_packet(bmRT, br, wVal, wIdx, wLen, desc);

    int ret = libusb_control_transfer(g_devh, bmRT, br,
                                       wVal, wIdx, data, wLen, 1000);

    if (ret < 0)
        printf("  → Transfer FAILED: %s (ret=%d)\n", libusb_error_name(ret), ret);
    else if (bmRT & 0x80)  // IN transfer
        printf("  → Received %d bytes\n", ret);
    else                    // OUT transfer
        printf("  → Sent %d bytes OK\n", ret);

    return ret;
}

/* ============================================================
 * 高层操作
 * ============================================================ */

/* 解析用户输入的 hex 字符串（空格分隔或连续，如 "01 02 03" 或 "010203"）
 * 返回解析出的字节数，存入 data（调用者确保 data 至少有 max_len 字节） */
static int parse_hex_input(uint8_t *data, int max_len)
{
    int count = 0;
    int c;
    int nibble = 0;          // 0=高半字节, 1=低半字节
    int has_digit = 0;

    /* 吃掉当前行剩余字符（上个 scanf 留下的换行） */
    while ((c = getchar()) == ' ' || c == '\n' || c == '\r');

    /* 解析第一个已读入的字符 */
    for (;;) {
        int val = -1;
        if (c >= '0' && c <= '9')      val = c - '0';
        else if (c >= 'a' && c <= 'f') val = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') val = c - 'A' + 10;

        if (val >= 0) {
            has_digit = 1;
            if (nibble == 0) {
                if (count >= max_len) {
                    printf("  ⚠ 超出 max_len=%d，截断\n", max_len);
                    while ((c = getchar()) != '\n' && c != EOF);  // 丢弃剩余
                    return count;
                }
                data[count] = (uint8_t)(val << 4);
                nibble = 1;
            } else {
                data[count] |= (uint8_t)val;
                count++;
                nibble = 0;
            }
        } else if (has_digit && (c == ' ' || c == '\n' || c == EOF)) {
            /* 空格或换行：如果半字节未闭合（如单个 "A"），当作低半字节=0 */
            if (nibble == 1) {
                /* data[count] 高半字节已填，低半字节留 0 */
                count++;
                nibble = 0;
            }
            if (c == '\n' || c == EOF) break;
        } else if (c == '\n' || c == EOF) {
            break;
        }
        /* 跳过空格继续 */
        c = getchar();
    }

    if (!has_digit) printf("  → 未输入数据\n");
    return count;
}

/* 读 CS_ID（无 SubFunc 时用：GET_LEN → 用户选择 GET_CUR 或 SET_CUR） */
static int read_cs_direct(uint8_t cs_id)
{
    int ret;
    uint16_t wIdx = (g_xu_unit_id << 8) | g_vc_if_num;
    uint16_t param_len = 0;
    uint8_t len_buf[2] = {0};

    /* GET_LEN */
    ret = xu_control_transfer(
        UVC_RT_IN_CLASS, UVC_GET_LEN,
        (uint16_t)(cs_id << 8), wIdx,
        len_buf, 2,
        "GET_LEN");
    if (ret != 2) return -1;

    param_len = len_buf[0] | (len_buf[1] << 8);
    printf("  → param_len = %u bytes\n", param_len);

    if (param_len == 0) {
        printf("  → 无参数数据\n");
        return 0;
    }

    /* ---- 用户选择 GET 还是 SET ---- */
    /* 先清掉 stdin 残留（上一步 scanf 留下的 \n），否则 fgets 直接跳过 */
    int flush_c;
    do { flush_c = getchar(); } while (flush_c != '\n' && flush_c != EOF);

    char choice = 'g';  // 默认 GET
    char line[16];
    printf("\n  GET_LEN 返回 %u 字节。下一步？\n", param_len);
    printf("    [g] GET_CUR — 读取数据\n");
    printf("    [s] SET_CUR — 写入数据\n");
    printf("    [q] 跳过\n");
    printf("  选择 (g/s/q, 回车默认 GET): ");
    fflush(stdout);
    if (fgets(line, sizeof(line), stdin) != NULL && line[0] != '\n')
        choice = line[0];

    if (choice == 'q' || choice == 'Q') {
        printf("  → 已跳过\n");
        return 0;
    }

    if (choice == 's' || choice == 'S') {
        /* ---- SET_CUR ---- */
        uint8_t *buf = calloc(1, param_len);
        if (!buf) return -1;

        printf("  输入 hex 数据（空格分隔，如 \"01 02 03\"，最多 %u 字节）:\n  > ",
               param_len);
        fflush(stdout);

        int data_len = parse_hex_input(buf, param_len);
        if (data_len == 0) {
            free(buf);
            printf("  → 无数据，取消 SET_CUR\n");
            return 0;
        }

        printf("  即将写入 %d 字节", data_len);
        if (data_len < (int)param_len)
            printf("（param_len=%u，写入 %d）", param_len, data_len);
        printf(":\n  HEX: ");
        for (int i = 0; i < data_len; i++) printf("%02X ", buf[i]);
        printf("\n");

        ret = xu_control_transfer(
            UVC_RT_OUT_CLASS, UVC_SET_CUR,
            (uint16_t)(cs_id << 8), wIdx,
            buf, (uint16_t)data_len,
            "SET_CUR");

        free(buf);
        return ret;
    }

    /* ---- 默认：GET_CUR ---- */
    uint8_t *buf = malloc(param_len);
    if (!buf) return -1;

    ret = xu_control_transfer(
        UVC_RT_IN_CLASS, UVC_GET_CUR,
        (uint16_t)(cs_id << 8), wIdx,
        buf, param_len,
        "GET_CUR");

    if (ret > 0) {
        printf("  HEX:  ");
        for (int i = 0; i < ret; i++) printf("%02X ", buf[i]);
        printf("\n  ASCII: ");
        for (int i = 0; i < ret; i++)
            putchar((buf[i] >= 0x20 && buf[i] < 0x7F) ? buf[i] : '.');
        printf("\n");
    }

    free(buf);
    return ret;
}

/* 操作 CS_ID + SubFunc（三阶段：FUNC_SWITCH → GET_LEN → GET_CUR 或 SET_CUR） */
static int read_cs_with_subfunc(uint8_t cs_id, uint8_t subfunc)
{
    int ret;
    uint16_t wIdx = (g_xu_unit_id << 8) | g_vc_if_num;

    /* 阶段 1：FUNC_SWITCH */
    uint8_t sw_data[2] = {cs_id, subfunc};

    ret = xu_control_transfer(
        UVC_RT_OUT_CLASS, UVC_SET_CUR,
        (uint16_t)(CS_ID_FUNC_SWITCH << 8), wIdx,
        sw_data, 2,
        "FUNC_SWITCH — SET_CUR to CS_ID=0x05");
    if (ret != 2) return -1;

    printf("  → Switched to CS_ID=0x%02X(%s), SubFunc=0x%02X\n\n",
           cs_id, csid_name(cs_id), subfunc);

    /* 阶段 2 + 3：接着直接读（复用上面的函数） */
    return read_cs_direct(cs_id);
}

/* ============================================================
 * 主程序
 * ============================================================ */

int main(void)
{
    libusb_context *ctx = NULL;
    int ret, choice;

    /* ---- 初始化 libusb ---- */
    ret = libusb_init(&ctx);
    if (ret < 0) {
        fprintf(stderr, "libusb_init: %s\n", libusb_error_name(ret));
        return 1;
    }

    /* ---- 选择设备 ---- */
    printf("\n========================================\n");
    printf("  UVC XU 交互式调试工具\n");
    printf("========================================\n\n");
    printf("预置设备列表:\n");
    for (int i = 0; i < (int)DEVICE_COUNT; i++)
        printf("  [%d] %s\n", i + 1, DEVICE_LIST[i].name);
    printf("  [0] 手动输入 VID/PID\n");

    printf("\n选择设备 (1-%d): ", (int)DEVICE_COUNT);
    fflush(stdout);
    scanf("%d", &choice);

    uint16_t vid, pid;
    uint8_t xu_id, vc_if;

    if (choice >= 1 && choice <= (int)DEVICE_COUNT) {
        const device_entry_t *dev = &DEVICE_LIST[choice - 1];
        vid   = dev->vid;
        pid   = dev->pid;
        xu_id = dev->xu_unit_id;
        vc_if = dev->vc_if_num;
    } else {
        printf("VID (hex): ");  scanf("%hx", &vid);
        printf("PID (hex): ");  scanf("%hx", &pid);
        printf("XU Unit ID (hex, lsusb -v 查 bUnitID): ");  scanf("%hhx", &xu_id);
        printf("VC Interface number: ");                     scanf("%hhu", &vc_if);
    }

    /* ---- 打开设备 ---- */
    g_devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!g_devh) {
        fprintf(stderr, "Cannot open %04x:%04x\n", vid, pid);
        fprintf(stderr, "Check VID/PID and permissions.\n");
        libusb_exit(ctx);
        return 1;
    }
    printf("\n[OK] Device opened: %04x:%04x\n", vid, pid);
    printf("     XU Unit ID = 0x%02X, VC IF = %d\n", xu_id, vc_if);

    /* ---- 解绑内核驱动 + claim ---- */
    if (libusb_kernel_driver_active(g_devh, vc_if)) {
        printf("Detaching kernel driver from interface %d...\n", vc_if);
        ret = libusb_detach_kernel_driver(g_devh, vc_if);
        if (ret < 0) {
            fprintf(stderr, "detach failed: %s\n", libusb_error_name(ret));
            goto close;
        }
        printf("[OK] Kernel driver detached\n");
    }

    ret = libusb_claim_interface(g_devh, vc_if);
    if (ret < 0) {
        fprintf(stderr, "claim_interface: %s\n", libusb_error_name(ret));
        goto close;
    }
    printf("[OK] Interface %d claimed\n\n", vc_if);

    g_xu_unit_id = xu_id;
    g_vc_if_num  = vc_if;

    /* ---- 交互循环 ---- */
    printf("========================================\n");
    printf("  SETUP 包结构速查\n");
    printf("========================================\n");
    printf("  Byte 0: bmRequestType\n");
    printf("           D7=方向(0=OUT,1=IN)  D6-5=字典(0=Std,1=Class,2=Vendor)\n");
    printf("           D4-0=接收者(0=Dev,1=IF,2=EP)\n");
    printf("  Byte 1: bRequest  (SET_CUR=0x01, GET_CUR=0x81, GET_LEN=0x85)\n");
    printf("  Byte 2-3: wValue  LE  (高字节=CS_ID)\n");
    printf("  Byte 4-5: wIndex  LE  (高字节=XU Unit ID, 低字节=接口号)\n");
    printf("  Byte 6-7: wLength LE  (DATA 阶段字节数)\n");
    printf("========================================\n");
    printf("  无 SubFunc 的 CS_ID: 0x04(PROTOCOL_VER), 0x05(FUNC_SWITCH)\n");
    printf("  其他 CS_ID 自动走三阶段: FUNC_SWITCH→GET_LEN→(GET/SET)\n");
    printf("  GET_LEN 后可自由选择 GET_CUR(读) 或 SET_CUR(写)\n");
    printf("========================================\n\n");

    while (1) {
        unsigned int cs_id, subfunc;
        char more[8];

        printf("---- 新请求 ----\n");
        printf("CS_ID (hex, 输入 FF 退出): ");
        fflush(stdout);
        scanf("%x", &cs_id);
        if (cs_id == 0xFF || cs_id > 0xFE) break;

        /* 判断是否需要 SubFunc */
        int need_switch = 1;
        if (cs_id == 0x04 || cs_id == 0x05) {
            need_switch = 0;
            printf("→ CS_ID=0x%02X(%s) 无 SubFunc，跳过 FUNC_SWITCH\n",
                   cs_id, csid_name(cs_id));
        }

        if (need_switch) {
            printf("SubFunc (hex): ");
            fflush(stdout);
            scanf("%x", &subfunc);

            ret = read_cs_with_subfunc((uint8_t)cs_id, (uint8_t)subfunc);
        } else {
            ret = read_cs_direct((uint8_t)cs_id);
        }

        if (ret < 0)
            printf("操作失败。检查 CS_ID 是否正确、设备是否支持。\n");

        printf("\n");
    }

    /* ---- 清理 ---- */
    printf("Bye.\n");
    libusb_release_interface(g_devh, vc_if);
    libusb_attach_kernel_driver(g_devh, vc_if);

close:
    libusb_close(g_devh);
    libusb_exit(ctx);
    return 0;
}
