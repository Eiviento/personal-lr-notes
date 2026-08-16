# USB SDK 最小代码示例集 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出 13 份最小可独立运行的 USB C 示例（code/examples/）+ README 索引 + 独立 HTML 讲解页（usb-sdk-examples.html）。

**Architecture:** 每份示例一个单文件 .c（零跨文件依赖、统一头注释约定、统一编译命令），HTML 页面内嵌同一份代码并按统一卡片模板逐段讲解「代码 ↔ 协议」对照。.c 文件是唯一可编译真相源，HTML 为讲课本。

**Tech Stack:** C11 + libusb-1.0（示例 10 额外依赖 libuvc + OpenCV）；HTML 单文件零外部依赖（自带内嵌 CSS/JS）；git 提交到 main（项目惯例：不使用功能分支）。

## Global Constraints

- 所有 .c 文件放 `D:\CC\personal-lr-notes\CCNotes\USB\code\examples\`，文件名形如 `NN_name.c`（NN 两位序号，与规格一致）
- 每个 .c 文件顶部必须有统一头注释块（格式见 Task 0 的模板：学什么/对应知识点/编译/运行/预期）
- 统一编译命令 `gcc -o <name> <file>.c -lusb-1.0`（示例 10 例外：`gcc -o frame_mailbox 10_frame_mailbox.c -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)`；示例 13 例外：`gcc -o sdk_skeleton 13_sdk_skeleton.c -lusb-1.0 -pthread`）
- CLI 约定：VID/PID 用命令行参数（十六进制），默认值在 usage 里写明
- 运行需 `sudo`（Ubuntu VM 惯例）
- 4 空格缩进；错误检查：每个 libusb 调用返回 <0 时打印 `libusb_error_name` 并退出
- Windows 端只写文件；编译运行验证由用户在 Ubuntu VM（`~/桌面/hikusb/`）执行——每个任务包含一个「用户验证」步骤，列出编译命令与预期现象
- 真机目标设备：海康 2bdf:0101（UVC 示例）；TM5X 2bdf:028a（CDC/HID 示例）；预期现象以这两台设备为准
- 每任务结束 git commit（项目惯例：docs 风格 message + Co-Authored-By 尾注）

---

### Task 0: 目录与约定（含 02 迁移准备）

**Files:**
- Create: `code/examples/` 目录（随 Task 1 首次 commit 时入库）

**Interfaces:**
- Produces: 头注释模板（后续所有任务使用）：

```c
/* ============================================================
 * NN_name.c —— <一句话功能>
 *
 * 学什么:  <本示例对应的知识点，1~2 行>
 * 对应知识点: KB 第九篇 §9.x（或第六/八篇章节）
 * 编译:    gcc -o <name> NN_name.c -lusb-1.0
 * 运行:    sudo ./<name> [VID PID ...]
 * 预期:    <真机预期现象>
 * ============================================================ */
```

- [ ] **Step 1: 确认规格文档**（`docs/superpowers/specs/2026-08-16-usb-sdk-examples-design.md`）中 13 份示例清单与本节一致
- [ ] **Step 2: 在 HANDOFF.md 的文件结构区加入 `code/examples/` 目录预留行**（内容在 Task 14 完成后回填）
- [ ] **Step 3: 提交**（若 HANDOFF 有改动）

```bash
git add HANDOFF.md && git commit -m "docs: prep — examples dir placeholder in HANDOFF

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1: 01_enum_devices.c — 枚举设备

**Files:**
- Create: `code/examples/01_enum_devices.c`

**Interfaces:**
- Produces: 无（首个示例；建立"错误检查 + 遍历打印"范式，后续示例复用该范式）

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 01_enum_devices.c —— 枚举设备（抄内核花名册）
 *
 * 学什么:  libusb_get_device_list 与协议枚举的区别——这是"抄花名册"，
 *          不是"入职面试"（面试是内核在设备插入时完成的）
 * 对应知识点: KB 第九篇 §9.2（设备列表 ≠ 协议枚举）
 * 编译:    gcc -o enum_devices 01_enum_devices.c -lusb-1.0
 * 运行:    sudo ./enum_devices [VID PID]   （不带参数 = 列出全部）
 * 预期:    列出全部设备；带 2bdf 0101 时高亮海康热成像
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device **devs;
    ssize_t cnt, i;
    int target_vid = -1, target_pid = -1;   /* -1 = 不过滤 */

    if (argc == 3) {
        target_vid = (int)strtol(argv[1], NULL, 16);
        target_pid = (int)strtol(argv[2], NULL, 16);
    } else if (argc != 1) {
        printf("用法: %s [VID PID]\n", argv[0]);
        return 1;
    }

    if (libusb_init(&ctx) < 0) { perror("libusb_init"); return 1; }

    cnt = libusb_get_device_list(ctx, &devs);   /* ★ 抄花名册（零总线流量） */
    if (cnt < 0) { fprintf(stderr, "get_device_list: %s\n", libusb_error_name((int)cnt)); return 1; }

    printf("共 %zd 台设备\n", cnt);
    for (i = 0; i < cnt; i++) {
        struct libusb_device_descriptor desc;
        if (libusb_get_device_descriptor(devs[i], &desc) < 0)   /* 内核缓存的副本 */
            continue;
        int match = (target_vid < 0) ||
                    (desc.idVendor == target_vid && desc.idProduct == target_pid);
        printf("%s%04x:%04x  bus %d  address %d  %s\n",
               match ? ">>> " : "    ",
               desc.idVendor, desc.idProduct,
               libusb_get_bus_number(devs[i]),
               libusb_get_device_address(devs[i]),   /* §4.5 领的工牌号 */
               match ? "← 目标设备" : "");
    }

    libusb_free_device_list(devs, 1);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——对照头注释三要素：抄花名册语义、VID:PID 过滤、地址=工牌号（讲解要点已在注释/代码内）
- [ ] **Step 3: 用户验证**（Ubuntu VM）

```bash
gcc -o enum_devices 01_enum_devices.c -lusb-1.0 && sudo ./enum_devices
sudo ./enum_devices 2bdf 0101   # 预期: 高亮 >>> 2bdf:0101
```

- [ ] **Step 4: 提交**

```bash
git add code/examples/01_enum_devices.c && git commit -m "feat: example 01 — enumerate devices

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 02_hotplug_detect.c — 热插拔检测（迁移）

**Files:**
- Create: `code/examples/02_hotplug_detect.c`
- Delete: `code/hotplug_demo.c`
- Modify: `HANDOFF.md`（文件结构区 hotplug_demo.c 行 → examples/02_hotplug_detect.c）

**Interfaces:**
- Consumes: Task 0 头注释模板
- Produces: 无新接口

- [ ] **Step 1: 复制现有文件并改名**

```bash
cp code/hotplug_demo.c code/examples/02_hotplug_detect.c
```

- [ ] **Step 2: 替换文件头注释为统一模板**

```c
/* ============================================================
 * 02_hotplug_detect.c —— 热插拔检测（ARRIVED/LEFT 回调）
 *
 * 学什么:  设备插入/拔出如何变成你的回调——4.2 的"电平宣告存在"
 *          经内核 netlink → libusb 事件 → 事件泵 → 打印，闭环到应用层
 * 对应知识点: KB 第九篇 §9.5（热插拔检测）
 * 编译:    gcc -o hotplug_detect 02_hotplug_detect.c -lusb-1.0
 * 运行:    sudo ./hotplug_detect              ← 监听所有设备
 *          sudo ./hotplug_detect 2bdf 0101    ← 只监听海康
 * 预期:    启动瞬间 ENUMERATE 刷出全部现有设备；插拔实时打印 +/-
 * ============================================================ */
```

- [ ] **Step 3: 更新 HANDOFF.md 引用**（`code/hotplug_demo.c` → `code/examples/02_hotplug_detect.c`，两处：文件结构区、深层理解 #25 提及处）
- [ ] **Step 4: 删除旧文件并提交**

```bash
rm code/hotplug_demo.c
git add -A && git commit -m "refactor: move hotplug demo to examples/02_hotplug_detect.c

Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 5: 用户验证**（可选——代码逻辑未变，仅迁移）`gcc -o hotplug_detect 02_hotplug_detect.c -lusb-1.0 && sudo ./hotplug_detect 2bdf 0101`

---

### Task 3: 03_desc_tree_walk.c — 描述符树遍历

**Files:**
- Create: `code/examples/03_desc_tree_walk.c`

**Interfaces:**
- Consumes: Task 1 的 open-by-VidPid 范式
- Produces: 无新接口

- [ ] **Step 1: 写入完整代码**

```c
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
```

- [ ] **Step 2: 自查**——树形三层结构、零带宽标注、bmAttributes 低 2 位映射四种传输（2.4/2.13 知识）
- [ ] **Step 3: 用户验证**

```bash
gcc -o desc_tree 03_desc_tree_walk.c -lusb-1.0 && sudo ./desc_tree 2bdf 0101
# 预期: Interface 0 (class 0x0e) → Alt 0 零带宽 / Alt 1+ 批量 EP 0x81...
```

- [ ] **Step 4: 提交** `git add code/examples/03_desc_tree_walk.c && git commit -m "feat: example 03 — descriptor tree walk"`（附 Co-Authored-By 尾注，下同，不再重复展示）

---

### Task 4: 04_claim_alt_setting.c — claim + 切 Alt

**Files:**
- Create: `code/examples/04_claim_alt_setting.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 04_claim_alt_setting.c —— claim 接口 + 切换 Alt Setting
 *
 * 学什么:  四层动作的后两层——claim（所有权登记，零总线流量）与
 *          set_interface_alt_setting（SET_INTERFACE 的代码版，设备
 *          固件执行"旧端点失效→新端点激活→toggle 归零"）
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流 / claim 与 detach）
 * 编译:    gcc -o claim_alt 04_claim_alt_setting.c -lusb-1.0
 * 运行:    sudo ./claim_alt 2bdf 0101
 * 预期:    detach+claim 成功 → VS 接口 Alt1 激活 → 打印端点 → 还原
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    int vs_if = 1, vs_alt1 = 1;   /* 2bdf:0101: VS 接口 1，Alt1 有流端点 */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 【内核层】detach 司机（video0 消失）+ claim 登记（零总线流量） */
    if ((r = libusb_kernel_driver_active(devh, vs_if)) == 1) {
        libusb_detach_kernel_driver(devh, vs_if);
        printf("[内核层] 已请内核司机下车（/dev/video0 消失）\n");
    }
    if ((r = libusb_claim_interface(devh, vs_if)) < 0) {
        fprintf(stderr, "claim 失败: %s\n", libusb_error_name(r)); return 1;
    }
    printf("[内核层] claim 接口 %d 成功（所有权登记，无总线流量）\n", vs_if);

    /* 【协议层】SET_INTERFACE = 开流开关 */
    r = libusb_set_interface_alt_setting(devh, vs_if, vs_alt1);
    if (r < 0) { fprintf(stderr, "切 Alt 失败: %s\n", libusb_error_name(r)); return 1; }
    printf("[协议层] SET_INTERFACE(Alt%d) 成功——流端点已激活，toggle 归零\n", vs_alt1);

    /* 查看 Alt1 的端点 */
    struct libusb_config_descriptor *cfg;
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    const struct libusb_interface_descriptor *alt = &cfg->interface[vs_if].altsetting[vs_alt1];
    printf("[查看]   Alt%d 有 %d 个端点:", vs_alt1, alt->bNumEndpoints);
    for (int i = 0; i < alt->bNumEndpoints; i++)
        printf(" 0x%02x", alt->endpoint[i].bEndpointAddress);
    printf("\n");
    libusb_free_config_descriptor(cfg);

    /* 还原：切回 Alt0（关流）+ 还车 + 司机复工 */
    libusb_set_interface_alt_setting(devh, vs_if, 0);
    libusb_release_interface(devh, vs_if);
    libusb_attach_kernel_driver(devh, vs_if);
    printf("[还原]  Alt0 + release + attach 完成（司机复工）\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——四层动作的标注注释齐全；还原路径完整（attach 防止 video0 消失）
- [ ] **Step 3: 用户验证** `gcc -o claim_alt 04_claim_alt_setting.c -lusb-1.0 && sudo ./claim_alt 2bdf 0101`（预期三步打印齐全；跑完 `ls /dev/video*` 确认司机已复工）
- [ ] **Step 4: 提交**

---

### Task 5: 05_clear_halt.c — 端点 Halt 恢复闭环

**Files:**
- Create: `code/examples/05_clear_halt.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 05_clear_halt.c —— 端点 Halt 恢复闭环
 *
 * 学什么:  5.3 的故障闭环写成代码——STALL 现形为 PIPE →
 *          GET_STATUS 确认 → libusb_clear_halt 解冻 → 重试
 * 对应知识点: KB 第五篇 §5.3（两种 STALL 生命周期）+ 第九篇 §9.4
 * 编译:    gcc -o clear_halt 05_clear_halt.c -lusb-1.0
 * 运行:    sudo ./clear_halt 2bdf 0101
 * 预期:    故意发错 wIndex 高字节 → PIPE（STATUS 回 STALL 现形）→
 *          演示闭环三步（GET_STATUS → clear_halt → 重试恢复）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    unsigned char buf[16];
    int vc_if = 0;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* ① 故意发错 wIndex 高字节（XU ID=0xFF 不存在）→ 设备 STATUS 回 STALL */
    r = libusb_control_transfer(devh, 0xA1, 0x85, 0x0400, 0xFF00, buf, 2, 1000);
    if (r == LIBUSB_ERROR_PIPE)
        printf("① 故意错发: PIPE —— 这就是 STATUS 阶段的 STALL（§5.1 拒绝唯一入口）\n");
    else
        printf("① 意外: %s\n", libusb_error_name(r));

    /* ② 闭环演示：GET_STATUS 确认 → clear_halt 解冻 → 重试 */
    /*    （注：EP0 的 STALL 是一次性的——下个 SETUP 自动清除；数据端点才需要本闭环。
     *     这里演示的是数据端点故障时的标准处理路径。） */
    int ep = 0x81;   /* VS 批量 IN 端点 */
    unsigned char status[2];
    r = libusb_control_transfer(devh, 0x82, 0x00, 0, ep, status, 2, 1000);
    printf("② GET_STATUS(EP 0x%02x) = %02x %02x（D0=Halt:%d）\n",
           ep, status[0], status[1], status[0] & 1);

    r = libusb_clear_halt(devh, ep);   /* = CLEAR_FEATURE(ENDPOINT_HALT) 的封装 */
    printf("③ libusb_clear_halt(0x%02x): %s（解冻，管道恢复可重试）\n",
           ep, r < 0 ? libusb_error_name(r) : "成功");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——EP0 一次性 vs 数据端点粘性已在注释说明；闭环三步齐全
- [ ] **Step 3: 用户验证** `gcc -o clear_halt 05_clear_halt.c -lusb-1.0 && sudo ./clear_halt 2bdf 0101`（预期 ①PIPE ②状态字节 ③成功）
- [ ] **Step 4: 提交**

---

### Task 6: 06_uvc_brightness.c — 标准 UVC 亮度（预期 STALL 教学点）

**Files:**
- Create: `code/examples/06_uvc_brightness.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 06_uvc_brightness.c —— 标准 UVC 亮度控制（PU GET_CUR/SET_CUR）
 *
 * 学什么:  标准 UVC 类请求的形状（0x21/0xA1 + wValue 高字节=CS_ID）
 *          与"专业设备 PU 是空壳"的现实——2bdf:0101 的 PU
 *          bmControls=00 00，GET_CUR 必然 STALL（预期失败=教学点）
 * 对应知识点: KB 第六篇 §6.20（bmControls 位图）+ 第八篇 §8.8
 * 编译:    gcc -o uvc_brightness 06_uvc_brightness.c -lusb-1.0
 * 运行:    sudo ./uvc_brightness 2bdf 0101
 * 预期:    GET_CUR(Brightness) → PIPE；程序打印解释并退出
 *          （换罗技等标准摄像头，同一份代码会返回亮度值并成功 SET_CUR）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define CS_BRIGHTNESS  0x01   /* PU 控制选择子（§6.20 位图表） */

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    int vid, pid, r;
    unsigned char val[2];
    int vc_if = 0;   /* 2bdf:0101 的 VC 接口号（lsusb -v 确认） */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }
    libusb_claim_interface(devh, vc_if);   /* PU 控制走 EP0，其实不 claim 也行 */

    /* 读亮度: IN Class Interface, GET_CUR, wValue 高字节=CS_BRIGHTNESS,
     * wIndex=VC 接口号（PU 没有 Unit ID——那是 XU 的专利） */
    r = libusb_control_transfer(devh, 0xA1, 0x81, CS_BRIGHTNESS << 8,
                                vc_if, val, 2, 1000);
    if (r == LIBUSB_ERROR_PIPE) {
        printf("GET_CUR(Brightness) → PIPE（STATUS 回 STALL）\n");
        printf("★ 预期内：本设备 PU bmControls=00 00，标准控制是空壳\n");
        printf("  （第六篇 §6.20 的专业设备常态——亮度/对比度全塞进 XU，\n");
        printf("   见示例 09。换标准摄像头则本代码直接返回亮度值。）\n");
    } else if (r >= 0) {
        int brightness = val[0] | (val[1] << 8);
        printf("当前亮度 = %d（小端 %02x %02x）\n", brightness, val[0], val[1]);

        /* 设亮度 = 当前值（标准设备上可改任意 0~100 试试） */
        r = libusb_control_transfer(devh, 0x21, 0x01, CS_BRIGHTNESS << 8,
                                    vc_if, val, 2, 1000);
        printf("SET_CUR(Brightness=%d): %s\n", brightness,
               r < 0 ? libusb_error_name(r) : "成功");
    } else {
        printf("意外: %s\n", libusb_error_name(r));
    }

    libusb_release_interface(devh, vc_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——★ 预期失败说明完整；SET_CUR 只在 GET 成功分支执行
- [ ] **Step 3: 用户验证** `gcc -o uvc_brightness 06_uvc_brightness.c -lusb-1.0 && sudo ./uvc_brightness 2bdf 0101`（预期打印 ★ 三段说明）
- [ ] **Step 4: 提交**

---

### Task 7: 07_uvc_probe_commit.c — Probe/Commit 协商

**Files:**
- Create: `code/examples/07_uvc_probe_commit.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 07_uvc_probe_commit.c —— Probe/Commit 协商（不取流只看对话）
 *
 * 学什么:  6.25 的协商机制——GET_MIN/MAX/DEF 问范围 → SET_CUR Probe
 *          试问 → GET_CUR 看设备敲定的参数；26 字节负载的字段解析
 * 对应知识点: KB 第六篇 §6.25 + 第十会话（UVC 请求码全家桶）
 * 编译:    gcc -o uvc_probe 07_uvc_probe_commit.c -lusb-1.0
 * 运行:    sudo ./uvc_probe 2bdf 0101
 * 预期:    打印设备自报的格式索引/帧索引/帧率/单帧最大字节数
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libusb-1.0/libusb.h>

/* VS Probe 26 字节负载的字段偏移（UVC 1.1） */
#define OFF_FORMAT_IDX     1
#define OFF_FRAME_IDX      2
#define OFF_FRAME_INTERVAL 3
#define OFF_MAX_FRAME_SIZE 17
#define OFF_MAX_PAYLOAD    21
#define PROBE_LEN          26

static void print_probe(const char *tag, unsigned char *p)
{
    printf("%s: Format=%d Frame=%d interval=%.1fms MaxFrameSize=%d Payload=%d\n",
           tag, p[OFF_FORMAT_IDX], p[OFF_FRAME_IDX],
           (p[OFF_FRAME_INTERVAL] | p[OFF_FRAME_INTERVAL+1]<<8 |
            p[OFF_FRAME_INTERVAL+2]<<16 | p[OFF_FRAME_INTERVAL+3]<<24) / 10000.0,
           p[OFF_MAX_FRAME_SIZE] | p[OFF_MAX_FRAME_SIZE+1]<<8 |
           p[OFF_MAX_FRAME_SIZE+2]<<16 | p[OFF_MAX_FRAME_SIZE+3]<<24,
           p[OFF_MAX_PAYLOAD] | p[OFF_MAX_PAYLOAD+1]<<8 |
           p[OFF_MAX_PAYLOAD+2]<<16 | p[OFF_MAX_PAYLOAD+3]<<24);
}

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    unsigned char buf[PROBE_LEN];
    int vid, pid, r;
    int vs_if = 1;   /* 2bdf:0101 的 VS 接口号 */

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }
    libusb_claim_interface(devh, vs_if);

    /* 问范围: VS Probe 的 CS_ID=0x01，wIndex=VS 接口号（没有 Unit ID！） */
    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x82, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_MIN", buf); else printf("GET_MIN: %s\n", libusb_error_name(r));

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x83, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_MAX", buf); else printf("GET_MAX: %s\n", libusb_error_name(r));

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x87, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_DEF", buf); else printf("GET_DEF: %s\n", libusb_error_name(r));

    /* 试问: 用默认值 Probe */
    memset(buf, 0, sizeof(buf));
    buf[OFF_FORMAT_IDX] = 1;
    buf[OFF_FRAME_IDX]  = 1;
    r = libusb_control_transfer(devh, 0x21, 0x01, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("SET_CUR Probe", buf); else printf("Probe: %s\n", libusb_error_name(r));

    memset(buf, 0, sizeof(buf));
    r = libusb_control_transfer(devh, 0xA1, 0x81, 0x0100, vs_if, buf, PROBE_LEN, 1000);
    if (r >= 0) print_probe("GET_CUR 设备敲定", buf); else printf("GET_CUR: %s\n", libusb_error_name(r));
    printf("（未发 Commit、未开流——纯协商对话到此为止）\n");

    libusb_release_interface(devh, vs_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——请求码 0x82/0x83/0x87/0x01/0x81 与第十会话全家桶一致；dwFrameInterval 100ns→ms 换算正确（/10000）
- [ ] **Step 3: 用户验证** `gcc -o uvc_probe 07_uvc_probe_commit.c -lusb-1.0 && sudo ./uvc_probe 2bdf 0101`
- [ ] **Step 4: 提交**

---

### Task 8: 08_uvc_open_stream.c — 开流

**Files:**
- Create: `code/examples/08_uvc_open_stream.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 08_uvc_open_stream.c —— 标准 UVC 开流（SET_INTERFACE + 收 1 秒统计）
 *
 * 学什么:  开流全流程——找 Alt（自动选第一个有端点的）→ SET_INTERFACE
 *          → 批量收 1 秒裸数据统计字节数（不拼帧，证明管道通即可）
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流）+ 第十会话（开流=切通道）
 * 编译:    gcc -o uvc_open_stream 08_uvc_open_stream.c -lusb-1.0
 * 运行:    sudo ./uvc_open_stream 2bdf 0101
 * 预期:    打印选中的 Alt 与端点 → 收 1 秒 → 字节数（每秒约几十万字节）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, r;
    int vs_if = 1, alt_num = -1, ep_in = -1, ep_pkt = 0;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 自动找第一个"有端点的 Alt"（跳过 Alt0 零带宽） */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    const struct libusb_interface *iface = &cfg->interface[vs_if];
    for (int j = 0; j < iface->num_altsetting; j++) {
        const struct libusb_interface_descriptor *alt = &iface->altsetting[j];
        for (int k = 0; k < alt->bNumEndpoints; k++) {
            if (alt->endpoint[k].bEndpointAddress & 0x80) {  /* IN 端点 */
                alt_num = alt->bAlternateSetting;
                ep_in = alt->endpoint[k].bEndpointAddress;
                ep_pkt = alt->endpoint[k].wMaxPacketSize;
                break;
            }
        }
        if (ep_in >= 0) break;
    }
    libusb_free_config_descriptor(cfg);
    if (ep_in < 0) { fprintf(stderr, "没找到流端点\n"); return 1; }
    printf("选中的流管道: Alt%d, EP 0x%02x, wMaxPacketSize=%d（带宽配额）\n",
           alt_num, ep_in, ep_pkt);

    /* 接管 + 开流（SET_INTERFACE 的代码版） */
    if (libusb_kernel_driver_active(devh, vs_if) == 1)
        libusb_detach_kernel_driver(devh, vs_if);
    libusb_claim_interface(devh, vs_if);
    r = libusb_set_interface_alt_setting(devh, vs_if, alt_num);
    if (r < 0) { fprintf(stderr, "开流失败: %s\n", libusb_error_name(r)); return 1; }
    printf("★ 开流成功——设备已激活流端点；数据要等 Host 的 IN Token（现在开始收 1 秒）\n");

    /* 收 1 秒裸数据（不拼帧，只统计——拼帧见示例 10 由 libuvc 代劳） */
    unsigned char buf[512 * 64];
    long long total = 0;
    time_t t0 = time(NULL);
    while (time(NULL) - t0 < 1) {
        int got = 0;
        r = libusb_bulk_transfer(devh, ep_in, buf, sizeof(buf), &got, 100);
        if (r == 0) total += got;
        else if (r != LIBUSB_ERROR_TIMEOUT) { printf("传输: %s\n", libusb_error_name(r)); break; }
    }
    printf("1 秒收到 %lld 字节（约 %lld KB/s）——管道已通\n", total, total / 1024);

    /* 关流 + 还车 + 司机复工 */
    libusb_set_interface_alt_setting(devh, vs_if, 0);
    libusb_release_interface(devh, vs_if);
    libusb_attach_kernel_driver(devh, vs_if);
    printf("已关流（Alt0）+ release + attach\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——"开流后数据靠 IN Token 拉动"注释到位；timeout=100ms 循环容忍 NAK 间隔
- [ ] **Step 3: 用户验证** `gcc -o uvc_open_stream 08_uvc_open_stream.c -lusb-1.0 && sudo ./uvc_open_stream 2bdf 0101`
- [ ] **Step 4: 提交**

---

### Task 9: 09_xu_minimal.c — XU 扩展单元通信

**Files:**
- Create: `code/examples/09_xu_minimal.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 09_xu_minimal.c —— 最小 XU 扩展单元通信（读协议版本）
 *
 * 学什么:  XU 三把钥匙的填法——wValue 高字节=CS_ID（海康惯例）、
 *          wIndex 高字节=XU Unit ID（换设备只改这里）；GET_LEN 试通
 * 对应知识点: KB 第八篇 §8.1（XU 协议设计）+ 第六会话方法论
 * 编译:    gcc -o xu_minimal 09_xu_minimal.c -lusb-1.0
 * 运行:    sudo ./xu_minimal 2bdf 0101 <VC_IF> <XU_ID>
 *          （XU_ID 从 sudo lsusb -v -d 2bdf:0101 的 bUnitID 查）
 * 预期:    GET_LEN 返回 2 字节协议版本号
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define CS_PROTOCOL_VERSION 0x04   /* 本设备 CS_ID=0x04 是协议版本（第六会话验证） */

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    unsigned char len[2], ver[8];
    int vid, pid, vc_if, xu_id, r, got;

    if (argc != 5) {
        printf("用法: %s VID PID VC_IF XU_ID\n", argv[0]);
        printf("  XU_ID 查法: sudo lsusb -v -d VID:PID | grep bUnitID\n");
        return 1;
    }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);
    vc_if = atoi(argv[3]);
    xu_id = atoi(argv[4]);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 三阶段: GET_LEN → GET_CUR（FUNC_SWITCH 对只读 CS 可省略） */
    /* bmRequestType=0xA1(IN Class IF), wValue=CS_ID<<8（海康惯例）,
     * wIndex=(XU_ID<<8)|VC_IF —— 换设备只改 XU_ID！ */
    r = libusb_control_transfer(devh, 0xA1, 0x85, CS_PROTOCOL_VERSION << 8,
                                (xu_id << 8) | vc_if, len, 2, 1000);
    if (r < 0) { fprintf(stderr, "GET_LEN: %s（XU_ID 填对了吗？）\n", libusb_error_name(r)); return 1; }
    int len_val = len[0] | (len[1] << 8);
    printf("GET_LEN(CS=0x%02x) → 应答长度 %d 字节\n", CS_PROTOCOL_VERSION, len_val);
    if (len_val == 0) { printf("（长度 0 = 该 CS 无参数或为触发型命令，正常）\n"); return 0; }
    if (len_val > (int)sizeof(ver)) len_val = sizeof(ver);

    r = libusb_control_transfer(devh, 0xA1, 0x81, CS_PROTOCOL_VERSION << 8,
                                (xu_id << 8) | vc_if, ver, len_val, 1000);
    if (r < 0) { fprintf(stderr, "GET_CUR: %s\n", libusb_error_name(r)); return 1; }
    printf("GET_CUR → %d 字节:", r);
    for (int i = 0; i < r; i++) printf(" %02x", ver[i]);
    printf("\n");

    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——GET_LEN 返回 0 的合法性说明（第六会话踩坑 24）；换设备只改 XU_ID 的注释
- [ ] **Step 3: 用户验证** `gcc -o xu_minimal 09_xu_minimal.c -lusb-1.0 && sudo lsusb -v -d 2bdf:0101 | grep -i unit && sudo ./xu_minimal 2bdf 0101 0 <XU_ID>`
- [ ] **Step 4: 提交**

---

### Task 10: 10_frame_mailbox.c — 信箱模式取流回调

**Files:**
- Create: `code/examples/10_frame_mailbox.c`

**Interfaces:**
- Consumes: Task 0 约定；编译命令为特例（-luvc + opencv）

- [ ] **Step 1: 写入完整代码**

```c
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
```

- [ ] **Step 2: 自查**——回调里无阻塞调用（imdecode 小帧可接受）；主线程渲染在锁外；MJPEG 欺诈检测保留
- [ ] **Step 3: 用户验证** `gcc -o frame_mailbox 10_frame_mailbox.c -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4) && sudo ./frame_mailbox 2bdf 0101`
- [ ] **Step 4: 提交**

---

### Task 11: 11_cdc_serial.c — CDC 串口收发

**Files:**
- Create: `code/examples/11_cdc_serial.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 11_cdc_serial.c —— CDC 虚拟串口收发（SET_LINE_CODING + 批量）
 *
 * 学什么:  6.13 的 SET_LINE_CODING 7 字节在代码里的完整形态；
 *          "打开串口"= 行编码 + 控制线状态 + 批量传输三件事
 * 对应知识点: KB 第六篇 §6.13/§6.14（CDC 类请求与数据流）
 * 编译:    gcc -o cdc_serial 11_cdc_serial.c -lusb-1.0
 * 运行:    sudo ./cdc_serial 2bdf 028a    （TM5X 的 CDC 接口）
 * 预期:    打印 line coding 设置 → 收 1 秒数据统计字节数
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, r;
    int ctrl_if = -1, data_if = -1, ep_in = -1;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 按 bInterfaceClass 找 CDC 控制接口(0x02)与数据接口(0x0A) */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    for (int i = 0; i < cfg->bNumInterfaces; i++) {
        int cls = cfg->interface[i].altsetting[0].bInterfaceClass;
        if (cls == 0x02) ctrl_if = i;
        if (cls == 0x0A) {
            data_if = i;
            for (int k = 0; k < cfg->interface[i].altsetting[0].bNumEndpoints; k++)
                if (cfg->interface[i].altsetting[0].endpoint[k].bEndpointAddress & 0x80)
                    ep_in = cfg->interface[i].altsetting[0].endpoint[k].bEndpointAddress;
        }
    }
    libusb_free_config_descriptor(cfg);
    if (ctrl_if < 0 || data_if < 0) { fprintf(stderr, "没找到 CDC 接口\n"); return 1; }
    printf("CDC: 控制接口 %d, 数据接口 %d (EP IN 0x%02x)\n", ctrl_if, data_if, ep_in);

    /* 打开串口 = SET_LINE_CODING（7 字节）+ SET_CONTROL_LINE_STATE */
    uint8_t line_coding[7] = {0x00, 0xC2, 0x01, 0x00, 0x00, 0x00, 0x08};
    /*                       115200 LE        停止位  校验  数据位 */
    r = libusb_control_transfer(devh, 0x21, 0x20, 0, ctrl_if, line_coding, 7, 1000);
    if (r < 0) { fprintf(stderr, "SET_LINE_CODING: %s\n", libusb_error_name(r)); return 1; }
    printf("SET_LINE_CODING: 115200 8N1 已发送\n");

    r = libusb_control_transfer(devh, 0x21, 0x22, 0x0003, ctrl_if, NULL, 0, 1000);
    if (r < 0) { fprintf(stderr, "SET_CONTROL_LINE_STATE: %s\n", libusb_error_name(r)); return 1; }
    printf("SET_CONTROL_LINE_STATE: DTR|RTS 已拉起\n");

    /* 数据层：claim 数据接口，批量收 1 秒 */
    if (libusb_kernel_driver_active(devh, data_if) == 1)
        libusb_detach_kernel_driver(devh, data_if);
    libusb_claim_interface(devh, data_if);

    unsigned char buf[4096];
    long long total = 0;
    time_t t0 = time(NULL);
    while (time(NULL) - t0 < 1) {
        int got = 0;
        r = libusb_bulk_transfer(devh, ep_in, buf, sizeof(buf), &got, 100);
        if (r == 0) total += got;
        else if (r != LIBUSB_ERROR_TIMEOUT) { printf("传输: %s\n", libusb_error_name(r)); break; }
    }
    printf("1 秒收到 %lld 字节（串口无数据时通常为 0——发数据才有流）\n", total);

    libusb_release_interface(devh, data_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——line_coding 数组注释与 6.13 byte-map 一致；接口按 class 自动发现
- [ ] **Step 3: 用户验证** `gcc -o cdc_serial 11_cdc_serial.c -lusb-1.0 && sudo ./cdc_serial 2bdf 028a`（预期打印两步成功 + 1 秒统计）
- [ ] **Step 4: 提交**

---

### Task 12: 12_hid_report.c — HID 中断报表

**Files:**
- Create: `code/examples/12_hid_report.c`

- [ ] **Step 1: 写入完整代码**

```c
/* ============================================================
 * 12_hid_report.c —— HID 中断报表读取
 *
 * 学什么:  6.7 的"中断管道 = 设备主动汇报"——interrupt_transfer
 *          周期轮询；报表字节原样打印（对照 6.6 的报表结构）
 * 对应知识点: KB 第六篇 §6.7（HID Report 协议）+ 第九篇 §9.4
 * 编译:    gcc -o hid_report 12_hid_report.c -lusb-1.0
 * 运行:    sudo ./hid_report 2bdf 028a    （TM5X 的厂商 HID 接口）
 * 预期:    每 100ms 读一次报表，打印前 32 字节 hex（1023B 报表的头部）
 * ============================================================ */

#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

int main(int argc, char **argv)
{
    libusb_context *ctx = NULL;
    libusb_device_handle *devh = NULL;
    struct libusb_config_descriptor *cfg;
    int vid, pid, r;
    int hid_if = -1, ep_in = -1, ep_interval = 0;

    if (argc != 3) { printf("用法: %s VID PID\n", argv[0]); return 1; }
    vid = (int)strtol(argv[1], NULL, 16);
    pid = (int)strtol(argv[2], NULL, 16);

    libusb_init(&ctx);
    devh = libusb_open_device_with_vid_pid(ctx, vid, pid);
    if (!devh) { fprintf(stderr, "打开失败\n"); return 1; }

    /* 按 bInterfaceClass=0x03 找 HID 接口 + 中断 IN 端点 */
    libusb_get_active_config_descriptor(libusb_get_device(devh), &cfg);
    for (int i = 0; i < cfg->bNumInterfaces; i++) {
        if (cfg->interface[i].altsetting[0].bInterfaceClass == 0x03) {
            hid_if = i;
            for (int k = 0; k < cfg->interface[i].altsetting[0].bNumEndpoints; k++) {
                const struct libusb_endpoint_descriptor *ep =
                    &cfg->interface[i].altsetting[0].endpoint[k];
                if ((ep->bmAttributes & 0x03) == 3 && (ep->bEndpointAddress & 0x80)) {
                    ep_in = ep->bEndpointAddress;
                    ep_interval = ep->bInterval;
                }
            }
        }
    }
    libusb_free_config_descriptor(cfg);
    if (hid_if < 0) { fprintf(stderr, "没找到 HID 接口\n"); return 1; }
    printf("HID 接口 %d, 中断 IN EP 0x%02x, bInterval=%d\n", hid_if, ep_in, ep_interval);

    if (libusb_kernel_driver_active(devh, hid_if) == 1)
        libusb_detach_kernel_driver(devh, hid_if);
    libusb_claim_interface(devh, hid_if);

    /* 中断传输循环：Host 周期发 IN Token（bInterval 节奏），设备有数据就回 */
    unsigned char buf[1024];
    for (int n = 0; n < 10; n++) {
        int got = 0;
        r = libusb_interrupt_transfer(devh, ep_in, buf, sizeof(buf), &got, 1000);
        if (r == 0 && got > 0) {
            printf("报表 #%d (%d 字节):", n, got);
            for (int i = 0; i < got && i < 32; i++) printf(" %02x", buf[i]);
            printf("%s\n", got > 32 ? " ..." : "");
        } else if (r == LIBUSB_ERROR_TIMEOUT) {
            printf("报表 #%d: （无数据，设备 NAK）\n", n);
        } else {
            printf("报表 #%d: %s\n", n, libusb_error_name(r)); break;
        }
    }

    libusb_release_interface(devh, hid_if);
    libusb_close(devh);
    libusb_exit(ctx);
    return 0;
}
```

- [ ] **Step 2: 自查**——bmAttributes 低 2 位 == 3 为中断传输（2.4 知识）；NAK→TIMEOUT 说明
- [ ] **Step 3: 用户验证** `gcc -o hid_report 12_hid_report.c -lusb-1.0 && sudo ./hid_report 2bdf 028a`
- [ ] **Step 4: 提交**

---

### Task 13: 13_sdk_skeleton.c — 综合骨架

**Files:**
- Create: `code/examples/13_sdk_skeleton.c`

- [ ] **Step 1: 写入完整代码**

```c
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
```

- [ ] **Step 2: 自查**——事件泵独立线程；LEFT 时只 close 不发 USB 操作（设备已死）；devh 判空防重复打开
- [ ] **Step 3: 用户验证** `gcc -o sdk_skeleton 13_sdk_skeleton.c -lusb-1.0 -pthread && sudo ./sdk_skeleton 2bdf 0101`（插拔摄像头看自动响应）
- [ ] **Step 4: 提交**

---

### Task 14: code/examples/README.md

**Files:**
- Create: `code/examples/README.md`
- Modify: `HANDOFF.md`（文件结构区 examples/ 条目回填）

- [ ] **Step 1: 写入 README**

```markdown
# USB SDK 最小代码示例集

13 份最小可独立运行的 libusb 示例，每份聚焦一个功能。配套讲解页：`../usb-sdk-examples.html`（双击打开）。

**编译运行环境**：Ubuntu VM（`~/桌面/hikusb/`），需 `sudo`。

| # | 文件 | 学什么 | 编译 | 真机预期 |
|---|------|--------|------|---------|
| 01 | 01_enum_devices.c | 枚举：抄内核花名册 | `gcc -o enum_devices 01_enum_devices.c -lusb-1.0` | 列出设备，高亮目标 VID:PID |
| 02 | 02_hotplug_detect.c | 热插拔：ARRIVED/LEFT 回调 | 同上模式 | ENUMERATE 刷屏 + 实时打印 |
| 03 | 03_desc_tree_walk.c | 描述符树：3.1 树的 C 版 | 同上模式 | 打印 433 字节链树形结构 |
| 04 | 04_claim_alt_setting.c | claim + 切 Alt：四层动作 | 同上模式 | claim 成功 → Alt1 激活 → 还原 |
| 05 | 05_clear_halt.c | Halt 恢复闭环 | 同上模式 | PIPE → GET_STATUS → clear_halt |
| 06 | 06_uvc_brightness.c | 标准 UVC 亮度（PU） | 同上模式 | ★ STALL（本设备 PU 空壳，预期失败=教学点） |
| 07 | 07_uvc_probe_commit.c | Probe/Commit 协商 | 同上模式 | 打印设备自报格式/帧率范围 |
| 08 | 08_uvc_open_stream.c | 开流：SET_INTERFACE + 收 1 秒 | 同上模式 | 打印字节速率（管道已通） |
| 09 | 09_xu_minimal.c | XU：GET_LEN 读版本 | 同上模式 | 返回协议版本号 |
| 10 | 10_frame_mailbox.c | 信箱模式取流（libuvc） | `gcc -o frame_mailbox 10_frame_mailbox.c -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)` | 窗口显示画面 |
| 11 | 11_cdc_serial.c | CDC 串口收发 | 同上模式 | 行编码 + 控制线 + 批量统计（需 2bdf:028a） |
| 12 | 12_hid_report.c | HID 中断报表 | 同上模式 | 每 100ms 打印报表 hex（需 2bdf:028a） |
| 13 | 13_sdk_skeleton.c | 综合骨架 | `gcc -o sdk_skeleton 13_sdk_skeleton.c -lusb-1.0 -pthread` | 插拔自动响应 |

**学习路径建议**：01 设备层 → 06~10 UVC 主战场 → 11/12 其他类 → 13 综合。

**同步纪律**：本目录 .c 文件是唯一可编译真相源；`../usb-sdk-examples.html` 内嵌同一份代码，改动时两边同步。
```

- [ ] **Step 2: HANDOFF 文件结构区回填**（Task 0 预留行 → `code/examples/ ← 13 份最小示例 + README（第十二会话）`）
- [ ] **Step 3: 提交**

---

### Task 15: usb-sdk-examples.html

**Files:**
- Create: `usb-sdk-examples.html`

**Interfaces:**
- Consumes: 01~13 的 .c 文件（代码原文）、头注释（目标/编译/预期三要素）
- Produces: 页面卡片模板（后续新增示例沿用）

- [ ] **Step 1: 骨架**——`<!DOCTYPE html>` + `<head>`（meta、title「USB SDK 最小代码示例」、内嵌 `<style>`）+ `<body>`：侧边栏（标题、简介、搜索框、四组折叠目录：设备层 01~05 / UVC 层 06~10 / 其他类 11~12 / 综合骨架 13、编译模板提示）+ `<main>`
- [ ] **Step 2: CSS**（内嵌，~300 行）——暗色 IDE 风格；变量：`--bg`（#1a1a2e 系）、`--card-bg`、`--hl`（关键行高亮底）、`--star`（★ 教学点黄）；卡片/代码块/行号（CSS counter）/表格/侧边栏固定 260px/响应式断点 ≤900px 侧边栏隐藏
- [ ] **Step 3: JS**（内嵌，~30 行）——搜索过滤（`input` 事件匹配卡片标题/代码文本，`hidden` 切换）；复制按钮（`navigator.clipboard.writeText` + 2 秒「已复制」反馈）；折叠组（`<details open>`）
- [ ] **Step 4: 13 张卡片**——每张卡片模板：

```html
<article class="card" id="ex-01">
  <h3>01 枚举设备 · enum_devices.c</h3>
  <div class="goal">目标：抄内核花名册——设备列表 ≠ 协议枚举（KB §9.2）</div>
  <div class="build">
    <code>gcc -o enum_devices 01_enum_devices.c -lusb-1.0</code>
    <code>sudo ./enum_devices [VID PID]</code>
    <button class="copy">复制</button>
  </div>
  <div class="expect">预期：列出全部设备；带 2bdf 0101 时高亮海康热成像</div>
  <pre class="code"><code>&lt;!-- 内嵌 01_enum_devices.c 原文，关键行加 &lt;span class="hl"&gt; --&gt;</code></pre>
  <div class="notes">
    <h4>逐段讲解</h4>
    <!-- 3~5 段「代码 ↔ 协议」对照 -->
  </div>
</article>
```

各卡片的讲解要点（实现时展开为 3~5 段，每段引用代码行 + KB 章节）：

- ex-01：get_device_list=花名册（零总线流量）↔ §9.2；device_address=§4.5 工牌号；VID:PID=身份证
- ex-02：4.2 电平宣告存在 → netlink → 回调的完整链条；ENUMERATE 回放；LEFT 设备已死
- ex-03：三层循环 ↔ §3.1 树；Alt 数组形态 ↔ 第五篇深挖；bmAttributes 低 2 位 ↔ 2.4
- ex-04：四层动作的后两层；claim 零总线流量；切 Alt 的设备侧动作序列（§5.5）；还原的重要性
- ex-05：PIPE=STALL 现形（§5.1 拒绝唯一入口）；GET_STATUS→clear_halt 闭环（§5.3）；EP0 一次性 vs 数据端点粘性
- ex-06：类请求形状（0xA1/0x81/wValue 高字节=CS）↔ §5.2 三层法律；★ STALL=教学点（PU 空壳 §6.20）；换标准摄像头即生效
- ex-07：GET_MIN/MAX/DEF/SET_CUR/GET_CUR 全家桶（第十会话）；26 字节负载偏移；wIndex 无 Unit ID
- ex-08：自动选 Alt（跳过零带宽）；SET_INTERFACE=开流开关；Host 中心化（数据靠 IN Token 拉）；关流还原
- ex-09：三把钥匙填法；换设备只改 XU_ID（第六会话）；GET_LEN=0 合法
- ex-10：两方一信箱图；回调不阻塞=事件泵不停摆（第八会话踩坑）；MJPEG 欺诈检测；渲染在锁外
- ex-11：line_coding 7 字节逐位 ↔ §6.13；"打开串口"三件事；接口按 class 自动发现
- ex-12：中断传输=设备主动汇报 ↔ §6.7；NAK→TIMEOUT；报表 hex ↔ §6.6 结构
- ex-13：事件泵线程 + 热插拔回调的完整组合（§9.5 SDK 骨架）；LEFT 只收尾

- [ ] **Step 5: 自查**——双击打开：无外链资源、搜索可用、复制可用、13 卡齐全、代码与 .c 文件逐字节一致
- [ ] **Step 6: 提交**

---

### Task 16: HANDOFF 收尾 + 推送

**Files:**
- Modify: `HANDOFF.md`

- [ ] **Step 1: 更新 HANDOFF**——第十二会话产出表追加一行（`usb-sdk-examples.html` + `code/examples/` 13 例 + README + 规格/计划文档）；文件结构区 examples/ 条目确认；「用户可能要求的下一步」增加"看代码示例 → 双击 usb-sdk-examples.html"
- [ ] **Step 2: 提交并推送**

```bash
git add -A && git commit -m "feat: USB SDK minimal examples — 13 runnable samples + HTML guide page

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 3: 用户全量验证**——Ubuntu 上把 code/examples/ 全目录拷到 `~/桌面/hikusb/examples/`，按 README 逐个编译运行 01~13（06 预期 STALL、11/12 需 2bdf:028a），确认全部符合预期后报告结果
