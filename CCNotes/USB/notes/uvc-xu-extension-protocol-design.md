# UVC XU 扩展协议设计方案

> 设计目标：突破 UVC Extension Unit 的 CS_ID 单字节限制（最多 255 个功能号），通过引入 SubFunc ID（子功能标识符）实现分层命名空间，总控制能力扩展到 255×255 ≈ 65,000。

---

## 一、协议架构

```
┌─────────────────────────────────────────┐
│             CS_ID 命名空间               │
│                                         │
│ CS_ID = 0x05  功能切换（FUNC_SWITCH）    │
│ CS_ID = 0x17  云台控制（PTZ_CONTROL）    │
│ CS_ID = 0x18  图像参数（IMAGE_CONFIG）   │
│ CS_ID = 0x19  系统信息（SYS_INFO）       │
│ ...                                      │
│ CS_ID = 0xF0  错误码（ERRCODE）          │
│                                         │
│ 每个 CS_ID 下可挂 0x01~0xFF 个 SubFunc   │
└─────────────────────────────────────────┘
```

### CS_ID 分配策略

| 范围 | 用途 | 示例 |
|------|------|------|
| 0x01~0x04 | 保留（兼容 UVC 标准） | — |
| 0x05 | 功能切换（FUNC_SWITCH） | 协议基础设施 |
| 0x06 | 错误码读取（ERRCODE） | 0x00=成功，0x01=忙 |
| 0x10~0x1F | 设备控制类 | 0x17=云台，0x18=图像 |
| 0x20~0x2F | 数据流类 | 0x20=码流类型，0x21=帧率 |
| 0x30~0x3F | 系统信息类 | 0x30=固件版本，0x31=温度 |
| 0x80~0xEF | 厂商私有 | 扩展自定义功能 |
| 0xF0~0xFF | 诊断/调试 | 0xF0=错误码，0xF1=日志 |

---

## 二、核心流程（三阶段）

```
┌─────────────────────┐
│ 1. FUNC_SWITCH      │  SET_CUR, CS_ID=0x05
│ 选择 CS + SubFunc   │  wValue 高字节 = 0x05
│ Data: [CS_ID, Sub]  │  Data = 2 字节
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│ 2. GET_LEN          │  GET_LEN, CS_ID=目标
│ 获取参数长度        │  wValue 高字节 = 目标 CS_ID
│ 返回 2 字节 LE      │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│ 3. GET_CUR / SET_CUR│  读写参数数据
│ 长度 = GET_LEN 值   │  若 SET_CUR，写完再读错误码确认
└─────────────────────┘
```

### 读操作抓包实例（云台水平角度）

> 字节序说明（2026-08-13 修正）：wValue 的 CS_ID 在**高字节**（如 CS_ID=0x05 → wValue=0x0500）。这是本设备固件的惯例，与 UVC 规范的"CS 在低字节"不同，已由第六/八会话真机代码（xu_minimal_get.c / uvc_stream_viewer.cpp 中 `CS_ID << 8`）验证。

**CS_ID=0x17 (PTZ_CONTROL), SubFunc=0x01 (Pan)**

```
第 1 步 — FUNC_SWITCH:
CTL  21 01  00 05  00 0A  02 00     ← SET_CUR, CS_ID=0x05（wValue=0x0500，CS 在高字节）
OUT  17 01                          ← [CS_ID=0x17, SubFunc=0x01(Pan)]

第 2 步 — GET_LEN:
CTL  A1 85  17 00  00 0A  02 00     ← GET_LEN, CS_ID=0x17（wValue=0x0017）
IN   04 00                          ← param_len = 4 字节

第 3 步 — GET_CUR:
CTL  A1 81  17 00  00 0A  04 00     ← GET_CUR, CS_ID=0x17, wLength=4
IN   2C 01 00 00                    ← 0x012C = 300 → 30.0°
```

### 写操作抓包实例

**设置水平角度到 45.0°（450 → 0x01C2）：**

```
SET_CUR:
CTL  21 01  00 17  00 0A  04 00     ← SET_CUR, CS_ID=0x17（wValue=0x0017）, wLength=4
OUT  C2 01 00 00                    ← 0x01C2 = 450 → 45.0°

写后校验 — 读错误码:
CTL  A1 81  F0 00  00 0A  01 00     ← GET_CUR, CS_ID=0xF0(ERRCODE)（wValue=0x00F0）
IN   00                             ← err=0x00 = 成功 ✓
```

---

## 三、SubFunc 定义示例

### CS_ID=0x17 — 云台控制 (PTZ_CONTROL)

| SubFunc ID | 名称 | 数据长度 | 数据类型 | 说明 |
|-----------|------|---------|---------|------|
| 0x01 | Pan（水平） | 4B | `uint32_t` LE | 单位 0.1°，0~3600 = 0°~360° |
| 0x02 | Tilt（垂直） | 4B | `int32_t` LE | 单位 0.1°，-900~900 = -90°~+90° |
| 0x03 | Zoom（变倍） | 2B | `uint16_t` LE | 单位 1x，范围 1~30 |
| 0x04 | Focus（对焦） | 2B | `uint16_t` LE | 手动/自动焦距值 |
| 0x05 | Preset（预置位） | 6B | struct | Byte 0=预置位号(1~255)，Byte 1-5=名称 |

### CS_ID=0x18 — 图像参数 (IMAGE_CONFIG)

| SubFunc ID | 名称 | 数据长度 | 数据类型 | 说明 |
|-----------|------|---------|---------|------|
| 0x01 | Brightness | 2B | `int16_t` LE | 亮度 |
| 0x02 | Contrast | 2B | `int16_t` LE | 对比度 |
| 0x03 | Saturation | 2B | `int16_t` LE | 饱和度 |
| 0x04 | Sharpness | 2B | `int16_t` LE | 锐度 |
| 0x05 | PaletteMode | 1B | `uint8_t` | 伪彩模式（兼容海康现有定义） |

---

## 四、FUNC_SWITCH 设计约束

1. **切换先于读写：** 每次 GET_LEN / GET_CUR / SET_CUR 之前必须调用 FUNC_SWITCH。固件内部维护一个"当前激活的 {CS_ID, SubFunc}"寄存器。

2. **幂等性：** 如果上一个请求已经切到同一对 {CS_ID, SubFunc}，再次切换是安全的——固件应设计为"相同则不重复初始化"。

3. **错误处理：** FUNC_SWITCH 成功后，SET_CUR 返回的 STATUS 可能是 STALL（功能不支持）；也可能是 ACK 但错误码寄存器非零。两者都检查才算完整校验。

4. **GET_LEN 返回 2 字节 LE：** 统一协议规则——任何 CS_ID 的 GET_LEN 都返回 2 字节 uint16 LE，表示该功能（当前 SubFunc）的参数字节长度。0 表示无参数。

---

## 五、CS_ID 校验与错误处理

### 固件端的 CS_ID 白名单

设备固件应维护一个支持的 CS_ID 范围。例如设备只支持 1~16，当 Host 传入 CS_ID=0x20：

```
第 1 层 — USB 硬件层 STALL（协议拒绝）:
  CTL  A1 85  00 20  00 0A  02 00    ← GET_LEN, CS_ID=0x20
  IN   (STALL)                        ← 固件检测到 CS_ID 超出范围，直接 STALL

  CTL  21 01  20 00  00 0A  02 00    ← SET_CUR, CS_ID=0x20
  OUT  17 01                          ← 数据还没传完
  OUT  (STALL)                        ← 固件直接 STALL，不收数据

第 2 层 — 应用层错误码（语义拒绝）:
  CTL  A1 81  00 06  00 0A  01 00    ← 读错误码 CS_ID=0x06
  IN   06                             ← 0x06 = "Unsupported CS ID"
```

### STALL vs 错误码：两层拒绝的分工

| | STALL（硬件层） | 错误码 0x06（应用层） |
|---|---|---|
| 发生时机 | 控制传输中途 | 下一笔读错误码时 |
| 含义 | "我不认识这个请求" | "上次那个 CS_ID 我不支持" |
| Bus Hound 显示 | `IN (STALL)` | `IN 06` |
| libusb 返回 | `LIBUSB_ERROR_PIPE` | 成功，但 `err=0x06` |
| 适用场景 | CS_ID 完全不存在 | SubFunc 不支持、参数非法等 |

### 推荐的分层拒绝策略

```
CS_ID 不在白名单内    → STALL（硬件拒绝，最快）
CS_ID 在白名单内，但:
  SubFunc 不支持       → ACK → 错误码 0x09
  参数值非法           → ACK → 错误码 0x04 或 0x08
  设备忙               → ACK → 错误码 0x01
```

### Host 端调用流程

```c
ret = xu_subfunc_get(devh, CS_ID_PTZ_CONTROL, SUBFUNC_PAN, buf, 8);

if (ret == LIBUSB_ERROR_PIPE) {
    // CS_ID 本身不支持 → 固件回了 STALL
    debug_printf("CS_ID not supported by device firmware\n");
} else if (ret < -100) {
    // SubFunc/参数被拒 → 查看具体错误码
    uint8_t err = -(ret + 100);
    debug_printf("Device rejected: 0x%02X — %s\n", err, xu_err_desc(err));
} else if (ret > 0) {
    // 成功读取 ret 字节
    process_data(buf, ret);
}
```

STALL 在 USB 总线层面的行为与控制传输正常流程不同——STALL 直接终止传输，没有 STATUS 阶段：

```
SETUP Token → DATA0{8B} → Device ACK     ← SETUP 必须 ACK
IN Token → Device STALL                    ← 拒绝在这里！
(无 STATUS 阶段 — STALL 直接终止传输)

对比正常流程:
SETUP Token → DATA0{8B} → Device ACK
IN Token → DATA1{data} → Host ACK
STATUS: OUT Token → DATA1(ZLP) → Device ACK
```

---

## 六、USB 总线层面的事务映射

Bus Hound 抓到的每一行控制传输在 USB 物理总线上都经历了完整的 SETUP → DATA → STATUS 三阶段。以 `GET_LEN` 为例：

```
Bus Hound:
  CTL  A1 85  00 17  00 0A  02 00     ← 抓包工具显示为一行的 SETUP + DATA

USB 总线实际发生的包交互:
  ┌─ SETUP 阶段 ─────────────────────────────────────
  │ Host → SETUP Token (ADDR, EP0)
  │ Host → DATA0 { A1 85 00 17 00 0A 02 00 }  8 字节 SETUP 包
  │ Host ← ACK (Device 必须 ACK)
  ├─ DATA 阶段 ──────────────────────────────────────
  │ Host → IN Token (ADDR, EP0)
  │ Host ← DATA1 { 04 00 }                       2 字节参数长度
  │ Host → ACK
  ├─ STATUS 阶段 ────────────────────────────────────
  │ Host → OUT Token (ADDR, EP0)
  │ Host → DATA1 (ZLP, 零长度包)                   交易关账
  │ Host ← ACK
  └──────────────────────────────────────────────────
```

STATUS 阶段的意义不是"最后一个包收到了"，而是"这笔控制传输的交易正式关闭，可以发下一个 SETUP 了"。如果 Device 不支持该 CS_ID 或不认识该 SubFunc，拒绝在 STATUS 阶段发生——Device 回 STALL 代替 ACK。

---

## 七、扩展性

- **每个 CS_ID 下最多 255 个 SubFunc**（0x01~0xFF，0x00 保留）
- **CS_ID 本身 1 字节** → 最多 255 个功能大类（去掉 0x00 和保留值，实际约 200 个可用）
- **总命令空间：** ~200 × 255 ≈ 51,000 个独立控制项
- **GET_LEN 统一 2 字节返回：** 参数长度最多 65535 字节，足够覆盖任何复杂参数结构

---

> 代码实现见 `code/uvc_xu_subfunc_framework.c`。
> HTML 可视化见 `usb-notes.html` → 2.20 章节。
