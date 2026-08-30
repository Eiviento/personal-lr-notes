# Phase 2 · 设备发现（枚举 / 查找 / 设备信息）

> 对应主干链第 ② 步。学完本 Phase 你会：列出机器上所有 UVC 设备、按 VID/PID/序列号找设备、读取设备"名片"信息。
> 演示程序：`../demos/phase2_device_list.c`，真实运行输出：`../outputs/phase2_run.txt`
> 好消息：枚举**不需要打开设备**，本 Phase 演示任何机器都能实跑。

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 | 返回 |
|------|------|------|-------------|------|
| `uvc_get_device_list` | 枚举所有 UVC 设备 | `ctx` | `uvc_device_t **`（NULL 结尾的数组） | 错误码 |
| `uvc_free_device_list` | 释放列表 | 列表 + `unref_devices` 标志 | 无 | void |
| `uvc_get_device_descriptor` | 读设备"名片" | `dev` | `uvc_device_descriptor_t *`（VID/PID/序列号/厂家/产品名） | 错误码 |
| `uvc_free_device_descriptor` | 释放名片 | `desc` | 无 | void |
| `uvc_get_bus_number` | 读总线号 | `dev` | `uint8_t` | — |
| `uvc_get_device_address` | 读设备地址 | `dev` | `uint8_t` | — |
| `uvc_find_device` | 按条件找**一台** | `ctx` + vid/pid/sn | `uvc_device_t *` | `UVC_SUCCESS` / `UVC_ERROR_NO_DEVICE` |
| `uvc_find_devices` | 按条件找**全部** | 同上 | `uvc_device_t **` 数组 | 同上 |
| `uvc_ref_device` / `uvc_unref_device` | 引用计数 +1 / -1 | `dev` | 无 | void |

---

## 2. 核心概念：设备"名片"（uvc_device_t）

第 ① 步拿到的工作台是空的。`uvc_device_t` 就是贴在设备上的一张**名片**：只包含"设备是谁、在哪"，**不接触设备本身**。理解这一点能避免最常见的误会：

> `uvc_get_device_list` / `uvc_find_device` 之后还不能收发数据，也不能改参数。它们只负责"认门"。

拿到名片后，下一步动作（Phase 3）才是敲门——`uvc_open(dev, ...)`。

---

## 3. uvc_get_device_list：怎么判断一台设备是不是 UVC 的？

读 device.c 源码，实现逻辑：

```
libusb_get_device_list          获取系统花名册（所有 USB 设备）
    └─ 对每台设备读配置描述符
        └─ 逐个接口检查：bInterfaceClass == 14 (Video)
                         且 bInterfaceSubClass == 2 (Streaming)
            └─ 命中 => 记入 UVC 名单
```

**做什么**：把 USB 总线上的设备全部过一遍筛子，只留下"视频流接口"的。
**拿到什么**：`uvc_device_t **list`——一个 **NULL 结尾的指针数组**（C 惯例，遍历到 NULL 停）。本机实测只有 1 台。

**坑**：
- 遍历必须用 `list[i] != NULL` 判断结尾，**不能**依赖任何"个数"返回值——函数不返回个数。
- 释放要用 `uvc_free_device_list(list, 1)`。第二个参数 `unref_devices=1` 表示"对每台设备 unref 一次"（列表生成时每台 ref 过 1 次，这里抵消）。传 0 只释放数组本身——**不推荐**，除非你确定设备另有引用。

## 4. uvc_get_device_descriptor：读名片上的字

```c
typedef struct uvc_device_descriptor {
  uint16_t idVendor;      /* 厂商标识，如 04f2 = 群光 */
  uint16_t idProduct;     /* 产品标识 */
  uint16_t bcdUVC;        /* UVC 规范版本（v0.0.7 里恒为 0，见坑） */
  const char *serialNumber; /* 序列号（可能为 NULL） */
  const char *manufacturer; /* 厂家（可能为 NULL） */
  const char *product;      /* 产品名（可能为 NULL） */
} uvc_device_descriptor_t;
```

**做什么**：VID/PID 从设备描述符直接读；三个字符串需要 `libusb_open` + 读字符串描述符（device.c 源码：打开失败就静默跳过，只给 NULL）。
**拿到什么**：一张需要 `uvc_free_device_descriptor` 释放的堆结构。

**本机真实输出**（`outputs/phase2_run.txt`）：

```
设备[0]
  VID:PID     = 04f2:b76f
  bcdUVC      = 0000
  序列号      = 200901010001
  厂家        = Generic
  产品名      = ACER HD User Facing
  总线/地址   = 2/2
```

两个有意思的事实：
1. **字符串居然读得到**——虽然设备被 usbvideo.sys 占用。因为读字符串描述符只需要 `libusb_open` 成功（打开句柄），不需要 claim 接口（后者才是 Phase 3 卡住的地方）。
2. **bcdUVC = 0000**。这是 v0.0.7 的已知小缺陷：`uvc_get_device_descriptor` 从不填充该字段。真正的 UVC 版本要在 open 之后从 VideoControl 头解析（Phase 4 `uvc_print_diag` 能看到）。

**坑**：三个字符串可能为 NULL，打印前必须判空；`uvc_free_device_descriptor` 内部会 free 它们，所以**不要**自己 free。

## 5. uvc_find_device / uvc_find_devices：按条件找人

```c
uvc_error_t uvc_find_device(uvc_context_t *ctx, uvc_device_t **dev,
                            int vid, int pid, const char *sn);
```

**匹配规则**（device.c 源码）：三个条件**全是可选的**——`0` 或 `NULL` 表示"不挑"：

| 传参 | 含义 |
|------|------|
| `(0, 0, NULL)` | 任意设备 → 返回第一台（官方示例的用法） |
| `(0x04f2, 0xb76f, NULL)` | 指定 VID:PID |
| `(0, 0, "200901010001")` | 指定序列号 |
| 组合 | 三者都满足才算命中 |

**拿到什么**：`uvc_find_device` 返回单台（`*dev`，找不到返回 `UVC_ERROR_NO_DEVICE`）；`uvc_find_devices` 返回 NULL 结尾数组（用 `free()` 释放数组本身 + 逐个 `uvc_unref_device`）。
**内部实现**：两者都是 `uvc_get_device_list` + 过滤的封装——所以它们其实就是"枚举 + 条件"的快捷方式。

**本机实测**：
```
uvc_find_device(0,0,NULL)      -> Success
uvc_find_device(0xffff,0xffff) -> No such device (-4)
uvc_find_devices 命中[0]: 04f2:b76f
```

## 6. 引用计数：ref / unref

每张名片内部有个计数器。规则很简单：

| 操作 | 计数变化 |
|------|---------|
| `uvc_get_device_list` / `uvc_find_device` 找到设备 | +1 |
| `uvc_ref_device` | +1 |
| `uvc_unref_device` | -1，减到 0 时设备结构被 free |

**为什么需要**：同一台物理设备可能同时出现在"枚举列表"和"你手上的 dev"里。计数保证最后一个使用者归还时才真正释放。**不做的后果**：少 unref 一次 = 内存泄漏；多 unref 一次 = 悬垂指针崩溃。

## 7. 真实运行示例

程序见 `../demos/phase2_device_list.c`：枚举 → 逐个打印名片 → 通配 find → 错误 find → find_devices → 释放。完整输出见 `../outputs/phase2_run.txt`（上文已摘录关键行）。

---

## 8. 本 Phase 小结

```
uvc_get_device_list ──> [dev0, dev1, ..., NULL]    （花名册过筛）
uvc_find_device      ──> 单台（内部 = 枚举+过滤）
uvc_get_device_descriptor ──> 名片上的字（VID/PID/序列号/厂家/产品名）
uvc_get_bus_number / device_address ──> 物理位置
所有设备都要 uvc_unref_device；列表要 uvc_free_device_list(list, 1)
```

自检清单：
- [ ] 知道列表是 NULL 结尾数组，遍历与释放的正确姿势
- [ ] 知道 find_device 的 (0,0,NULL) 通配含义，找不到返回 NO_DEVICE
- [ ] 知道描述符三个字符串可能为 NULL、bcdUVC 恒 0 是 v0.0.7 的坑
- [ ] 能说出 ref/unref 配对的理由

下一步：Phase 3 打开设备——本机会在这一步撞上 Windows 驱动墙（检查点 D1），文档里有完整解决方案。
