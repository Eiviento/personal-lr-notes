# Phase 4 · 能力查询（读"自述文件"）

> 对应主干链第 ④ 步。学完本 Phase 你会：查清一台设备支持哪些格式/分辨率/帧率、哪些控制——这是后面谈判和控制的前提。
> 演示程序：`../demos/phase4_capabilities.c`（需先解决 D1 才能实跑）

---

## 1. 本 Phase 接口一览

| 接口 | 作用 | 拿到什么数据 |
|------|------|-------------|
| `uvc_print_diag` | 一键打印设备全部配置 | 直接打到 FILE*（stderr） |
| `uvc_get_format_descs` | 拿格式菜单链表头 | `const uvc_format_desc_t *` |
| `uvc_get_camera_terminal` | 找 Camera Terminal | `const uvc_input_terminal_t *`（可能 NULL） |
| `uvc_get_input_terminals` | 全部输入端子链表 | 链表头 |
| `uvc_get_processing_units` | 全部 PU 链表 | 链表头 |
| `uvc_get_extension_units` | 全部 XU 链表 | 链表头 |
| `uvc_get_selector_units` | 全部选择器单元链表 | 链表头 |
| `uvc_get_output_terminals` | 输出端子 | **恒为 NULL（v0.0.7 未实现）** |

共同前提：这些函数读的是 `uvc_open` 时解析好的描述符树（Phase 3 第 2 步的产物），**全部 O(1) 返回内部指针，不产生 USB 通信**。

---

## 2. 数据结构的"菜单"形状

```
devh->info->stream_ifs（视频流接口链表）
   └─ format_descs（格式链表：每个格式 = 一种编码）
        └─ frame_descs（帧链表：每个帧 = 一种 分辨率×帧率 组合）
```

一个典型摄像头：1 个流接口 → 2 个格式（YUYV 未压缩 + MJPEG）→ 每个格式下 5~15 个帧（160x120@30、320x240@30、640x480@30、1280x720@10…）。

### uvc_format_desc_t 关键字段

| 字段 | 含义 | 用途 |
|------|------|------|
| `bDescriptorSubtype` | 格式类型（Uncompressed / MJPEG / Frame-based） | 判断编码大类 |
| `bFormatIndex` | 格式编号 | **谈判时填进合同**（Phase 5） |
| `fourccFormat[4]` / `guidFormat[16]` | 四字符码或 GUID（同一段内存） | YUY2、MJPG 等 |
| `bBitsPerPixel` | 未压缩格式的每像素位数 | YUYV=16 |
| `bDefaultFrameIndex` | 默认帧编号 | 兜底选择 |

### uvc_frame_desc_t 关键字段

| 字段 | 含义 |
|------|------|
| `bFrameIndex` | 帧编号（谈判用） |
| `wWidth` / `wHeight` | 分辨率 |
| `dwDefaultFrameInterval` | 默认帧间隔（单位 100ns；fps = 10000000 / 该值） |
| `dwMinFrameInterval` / `dwMaxFrameInterval` / `dwFrameIntervalStep` | 连续帧率范围与步长（`bFrameIntervalType==0` 时有效） |
| `intervals` | 离散帧率表（0 结尾数组，单位 100ns；`bFrameIntervalType!=0` 时有效） |
| `dwMaxVideoFrameBufferSize` | 一帧最大字节数（分配缓冲的依据） |

**两个重要单位换算**：
- 帧间隔 100ns → fps：`fps = 10000000 / interval`（diag.c 里就是这么算的）
- 分辨率是 `uint16_t`，位深 16 位，别存进 int8。

## 3. uvc_get_camera_terminal：读"传感器能力位图"

```c
const uvc_input_terminal_t *uvc_get_camera_terminal(uvc_device_handle_t *devh);
```

**实现**（device.c）：遍历 input_terminals 链表，返回第一个 `wTerminalType == UVC_ITT_CAMERA (0x0201)` 的。**找不到返回 NULL**（不是所有设备都有 camera terminal——例如只有 XU 的工业相机）。

拿到的结构里最值钱的是 `bmControls`（uint64_t 位图）：**bit N = 1 表示支持控制选择器 N**（N 即 `uvc_ct_ctrl_selector` 枚举值，如 0x02=自动曝光、0x06=对焦）。Phase 9 调用任何高层控制前，可以先用这个位图判断设备支不支持，避免白问。

**坑**：位图只能告诉你"描述符里宣称支持"，**不保证真能用**——部分厂商描述符写得比实际功能多。最终以实际调用返回为准（Phase 9 演示的容错写法就是为这个）。

## 4. PU / XU：处理与扩展

| 结构 | 关键字段 | 意义 |
|------|---------|------|
| `uvc_processing_unit_t` | `bUnitID`（Phase 8 寻址用）、`bSourceID`（上游是谁）、`bmControls`（PU 控制位图） | 亮度/对比度/白平衡等图像处理 |
| `uvc_extension_unit_t` | `bUnitID`、`guidExtensionCode[16]`（GUID 标识）、`bmControls` | 厂商自定义功能（HIKVISION 相机的 XU 就在这里） |

**链表的坑**：这些 getter 返回链表头，遍历要用 `->next`；`uvc_get_camera_terminal` 文档特别警告——遍历会破坏"这是 camera terminal"的语义，别修改返回结构。

## 5. uvc_print_diag：一键自述文件

官方诊断函数，输出"设备能干什么"的全景。输出结构（diag.c）：

```
DEVICE CONFIGURATION (04f2:b76f/200901010001) ---
Status: idle
VideoControl:
    bcdUVC: 0x0110
VideoStreaming(1):
    bEndpointAddress: 129
    Formats:
        UncompressedFormat(1)
              bits per pixel: 16
              GUID: 32595559...(YUY2)
              default frame: 3
              ...
            FrameDescriptor(1)
              size: 640x480
              default interval: 1/30
              ...
END DEVICE CONFIGURATION
```

**从这里能读到**：UVC 版本（bcdUVC 0x0100=1.0 / 0x010a=1.1 / 0x0110=1.5）、端点地址、每个格式与帧的完整参数——**Phase 5 谈判的所有输入都在这份菜单上**。

## 6. 真实运行示例

`demos/phase4_capabilities.c`（需 D1 解决后运行）：print_diag → 手动遍历格式/帧 → camera terminal 位图 → PU/XU 列表。预期关键输出（以 ACER 内置摄像头为例，实际以运行为准）：

```
===== uvc_print_diag 输出（stderr）=====
DEVICE CONFIGURATION (04f2:b76f/200901010001) ---
...
Camera Terminal: ID=1 类型=0x0201
  焦距范围: x~y mm
  bmControls 位图: ...（bit 位 = CT 控制选择器编号）
Processing Unit: ID=2 上游源ID=1 bmControls=...
Extension Unit: ...（若有）
```

---

## 7. 本 Phase 小结

```
uvc_get_format_descs ──> 格式菜单（格式→帧 两级链表）
uvc_get_camera_terminal ──> 传感器能力位图（bit=控制选择器）
uvc_get_processing_units / extension_units ──> 处理/扩展单元（Phase 8 寻址用）
uvc_print_diag ──> 一键全景
全部零 USB 通信：读的是 open 时缓存好的描述符树
```

自检清单：
- [ ] 知道格式→帧两级链表结构，格式索引和帧索引是谈判的输入
- [ ] 会换算帧间隔 100ns ↔ fps
- [ ] 知道 bmControls 位图的含义，以及"宣称支持≠真支持"
- [ ] 知道 uvc_get_output_terminals 恒 NULL（v0.0.7 未实现）

下一步：Phase 5 流协商——拿菜单去和摄像头谈判，签"合同"。
