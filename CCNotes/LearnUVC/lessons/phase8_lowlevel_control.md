# Phase 8 · 通用控制底层（遥控器的万能通道）

> 控制线（VC 接口）的底座。学完本 Phase 你会：用三个函数读写**任意**控制——包括高层接口覆盖不到的标准控制、以及厂商自定义的 XU 控制。
> 演示程序：`../demos/phase8_lowlevel_ctrl.c`（需先解决 D1 才能实跑）

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 输入 | 拿到什么数据 |
|------|------|------|-------------|
| `uvc_get_ctrl_len` | 问一个控制的数据长度 | devh + unit + ctrl | `int` 长度（负数为错误） |
| `uvc_get_ctrl` | 万能读（GET_CUR/MIN/MAX/RES/DEF/INFO） | devh + unit + ctrl + 缓冲 + len + req_code | 实际传输字节数 |
| `uvc_set_ctrl` | 万能写（SET_CUR） | devh + unit + ctrl + 数据 + len | 实际传输字节数 |
| `uvc_get_power_mode` / `uvc_set_power_mode` | 电源模式读写 | devh (+mode) | `enum uvc_device_power_mode` |

---

## 2. 寻址三要素：unit + ctrl + req_code

这三个函数是"万能钥匙"——UVC 规范里所有控制（标准 + 厂商自定义）都靠同一套寻址访问：

```
目标控制 = (unit ID, control selector, 请求码)
```

对应到 USB 控制传输的字段（ctrl.c 源码，就这么薄）：

```c
libusb_control_transfer(devh->usb_devh,
    0x21 或 0xA1,             /* bmRequestType：SET / GET */
    req_code,                 /* bRequest：UVC_SET_CUR=0x01, GET_CUR=0x81... */
    ctrl << 8,                /* wValue：控制选择器 */
    unit << 8 | bInterfaceNumber,  /* wIndex：单元ID + VC接口号 */
    data, len, 0);
```

| 要素 | 从哪里拿 | 例子 |
|------|---------|------|
| `unit`（单元 ID） | Phase 4 的 getter：`uvc_get_camera_terminal(devh)->bTerminalID`、`uvc_get_processing_units(devh)->bUnitID`、`uvc_get_extension_units(devh)->bUnitID` | 曝光属于 CT → 用 CT 的 ID |
| `ctrl`（控制选择器） | `uvc_ct_ctrl_selector` / `uvc_pu_ctrl_selector` 枚举（libuvc.h），或厂商文档给的 XU 自定义编号 | `UVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL = 0x04` |
| `req_code` | `uvc_req_code` 枚举 | 见下表 |

## 3. 请求码全表：uvc_req_code

| 请求码 | 值 | 问什么 |
|--------|----|--------|
| `UVC_SET_CUR` | 0x01 | 设置当前值 |
| `UVC_GET_CUR` | 0x81 | 当前值 |
| `UVC_GET_MIN` | 0x82 | 最小值 |
| `UVC_GET_MAX` | 0x83 | 最大值 |
| `UVC_GET_RES` | 0x84 | 分辨率（最小步进） |
| `UVC_GET_LEN` | 0x85 | 数据长度 |
| `UVC_GET_INFO` | 0x86 | 能力信息位图 |
| `UVC_GET_DEF` | 0x87 | 默认值 |

**为什么有这些**：GET_MIN/MAX/RES 让你画 UI 滑条；GET_DEF 让你做"恢复默认"按钮。一个标准控制查询程序（读曝光时间）的完整动作就是 Phase 8 演示里 `demo_ctrl` 做的事：

```
GET_LEN 问长度 → GET_CUR/MIN/MAX/RES/DEF 各问一遍 → SET_CUR 写回
```

## 4. 三个函数的返回值细节

- `uvc_get_ctrl_len`：成功返回长度（如曝光 4 字节）；设备不支持该控制时返回**负错误码**（PIPE/STALL）。判 `<= 0` 即不支持。
- `uvc_get_ctrl` / `uvc_set_ctrl`：成功返回**实际传输字节数**（应等于 len）；失败返回负错误码。
- 数据都是**小端**（设备发来的原始字节序），演示程序里有手工解码示例。

**坑 1：不是所有控制都存在**。UVC 规范列的清单只是"可以有"，实际由设备 bmControls 位图（Phase 4）决定。问不存在的控制 → `UVC_ERROR_PIPE (-9)`（设备 STALL）。所以通用控制必须容错。

**坑 2：接口级控制 vs 单元级控制**。电源模式（`uvc_get_power_mode`）属于 VC 接口整体，寻址时 **wIndex 不带 unit**（ctrl.c 里直接 `bInterfaceNumber`），wValue 用 `UVC_VC_VIDEO_POWER_MODE_CONTROL << 8`。和单元级控制对比着看，能加深对 wValue/wIndex 的理解。

## 5. 什么时候必须用底层通道

高层接口（Phase 9）覆盖了规范里所有标准控制。但两种场景只能用这三个函数：

1. **XU 扩展单元**——厂商自定义功能（工业相机的高频刚需，你 USB 学习项目里 HIKVISION 的 XU 框架就是这套东西）。控制选择器编号由厂商文档给出，unit ID 从 `uvc_get_extension_units` 拿到。
2. **高层接口没封装的冷门控制**（如 GET_INFO 查询能力位图）。

## 6. 真实运行示例

`demos/phase8_lowlevel_ctrl.c`（需 D1 解决后运行）：拿 CT 的 unit ID → 万能读曝光时间的 LEN/CUR/MIN/MAX/RES/DEF → 变焦（预期不支持，演示 PIPE 容错）→ 写回曝光当前值 → 电源模式读+写回。

预期输出形态：

```
Camera Terminal ID = 1

[曝光时间(绝对值)] 数据长度 4 字节:
  GET_CUR 当前值        -> 78（原始字节: 4e 00 00 00）
  GET_MIN 最小值        -> 3
  GET_MAX 最大值        -> 5000
  GET_RES 分辨率        -> 1
  GET_DEF 默认值        -> 156
[焦距(变焦)] 设备不支持 (get_ctrl_len -> Pipe)
uvc_set_ctrl(曝光, 写回当前值) -> 成功
电源模式: FULL
uvc_set_power_mode(写回) -> Success
```

**验证点**：曝光最大值/最小值落在物理合理范围（如 3~5000，单位 0.1ms）；不支持的控制干净地报 PIPE 而不是崩。

---

## 7. 本 Phase 小结

```
万能通道三件套：
  uvc_get_ctrl_len(devh, unit, ctrl)
  uvc_get_ctrl    (devh, unit, ctrl, buf, len, UVC_GET_CUR|MIN|MAX|RES|DEF)
  uvc_set_ctrl    (devh, unit, ctrl, buf, len)

寻址 = unit（CT/PU/XU 的 ID） + ctrl（选择器） + req_code（请求码）
底层 USB 包：wValue = ctrl<<8, wIndex = unit<<8|接口号
```

自检清单：
- [ ] 能解释寻址三要素各从哪来
- [ ] 知道 8 个请求码各自的用途
- [ ] 知道不支持的控制返回 PIPE，必须容错
- [ ] 知道电源模式是接口级控制（wIndex 无 unit），与单元级控制对照

下一步：Phase 9 高层相机控制族——35+ 对 get/set 全览，其实全是本 Phase 的"套壳"。
