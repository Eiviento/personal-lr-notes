# Phase 9 · 高层相机控制族（35+ 对 get/set 全览）

> 控制线的主力军。学完本 Phase 你会：随手调曝光、对焦、白平衡、亮度……并对全部高层控制有个完整的索引。
> 演示程序：`../demos/phase9_controls.c`（需先解决 D1 才能实跑）

---

## 1. 先看透本质：它们全是 Phase 8 的"套壳"

ctrl-gen.c 是**脚本自动生成**的文件（`ctrl-gen.py`），每个函数都是同一个模板：

```c
uvc_error_t uvc_set_brightness(uvc_device_handle_t *devh, int16_t brightness) {
  uint8_t data[2];
  SHORT_TO_SW(brightness, data + 0);              /* 值打包成小端 */
  ret = libusb_control_transfer(devh->usb_devh,
      REQ_TYPE_SET, UVC_SET_CUR,
      UVC_PU_BRIGHTNESS_CONTROL << 8,             /* 选择器 */
      uvc_get_processing_units(devh)->bUnitID << 8 | devh->info->ctrl_if.bInterfaceNumber,
      data, sizeof(data), 0);
  ...
}
```

**规律**（对照 Phase 8 的寻址）：
- CT 系控制（曝光/对焦/变焦/云台…）→ unit = `uvc_get_camera_terminal(devh)->bTerminalID`
- PU 系控制（亮度/对比度/白平衡…）→ unit = `uvc_get_processing_units(devh)->bUnitID`（**只取第一个 PU**）
- 每个 get 都有 `req_code` 参数（可传 GET_MIN/GET_MAX/GET_DEF 问边界），set 固定 SET_CUR
- 全部封装"字节数匹配才算成功"的校验，返回 `UVC_SUCCESS` 或错误码（不支持 → PIPE）

**所以学习策略：表格通读一遍混脸熟，会用一个就会全部。**

---

## 2. Camera Terminal 控制族（传感器侧，unit = camera terminal ID）

### 2.1 曝光

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_ae_mode` | `uint8_t` | 曝光模式：1=手动 2=自动 4=快门优先 8=光圈优先 |
| `get/set_ae_priority` | `uint8_t` | 自动曝光时可否牺牲帧率：0=帧率恒定 1=帧率可变 |
| `get/set_exposure_abs` | `uint32_t` | 曝光时间绝对值，**单位 0.1ms**（值 100 = 10ms） |
| `get/set_exposure_rel` | `int8_t` | 曝光相对步进（EV 步） |

**典型流程**：`set_ae_mode(1)` 切手动 → `get_exposure_abs(GET_MIN/GET_MAX)` 问范围 → `set_exposure_abs(想要的值)`。官方示例演示了自动模式的容错写法：设 mode=2 失败(PIPE)就退而试 mode=8。

### 2.2 对焦（无机械对焦的定焦摄像头全部不支持）

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_focus_abs` | `uint16_t` | 对焦位置绝对值（0~65535，近~远） |
| `get/set_focus_rel` | `int8_t` + `uint8_t` | 相对移动：方向/步数 + 速度 |
| `get/set_focus_simple_range` | `uint8_t` | 简单对焦：0=全范围 1=近距 2=远距 3=微距（数值随设备） |
| `get/set_focus_auto` | `uint8_t` | 自动对焦开关：0=关 1=开 |

### 2.3 光圈 / 变焦 / 云台 / 滚转（机械镜头设备专属）

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_iris_abs` | `uint16_t` | 光圈 F 值 ×100（如 280 = f/2.8） |
| `get/set_iris_rel` | `uint8_t` | 光圈相对开合 |
| `get/set_zoom_abs` | `uint16_t` | 焦距 mm（如 500 = 5.0mm） |
| `get/set_zoom_rel` | `int8_t` + `uint8_t` + `uint8_t` | 变焦方向 + 数字变焦开关 + 速度 |
| `get/set_pantilt_abs` | `int32_t` + `int32_t` | 水平/垂直角度，单位 0.0001°（360000 = 36°） |
| `get/set_pantilt_rel` | 4 个参数 | 水平/垂直方向与速度 |
| `get/set_roll_abs` | `int16_t` | 滚转角度 0.01° 单位 |
| `get/set_roll_rel` | `int8_t` + `uint8_t` | 滚转方向 + 速度 |

### 2.4 其他 CT 控制

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_scanning_mode` | `uint8_t` | 扫描模式：0=隔行 1=逐行（模拟摄像头时代遗产） |
| `get/set_privacy` | `uint8_t` | 隐私模式（电子镜头盖）：0=关 1=开 |
| `get/set_digital_window` | 6×`uint16_t` | 数字窗口：上/左/下/右边距 + 步数 + 步进单位 |
| `get/set_digital_roi` | 5×`uint16_t` | 感兴趣区域：上/左/下/右 + 自动控制标志 |

---

## 3. Processing Unit 控制族（图像处理侧，unit = 第一个 PU 的 ID）

### 3.1 图像质量（家用摄像头最常支持的一组）

| 接口 | 数据 | 含义/范围 |
|------|------|----------|
| `get/set_brightness` | `int16_t` | 亮度（有符号！先 GET_MIN/MAX 问范围） |
| `get/set_contrast` | `uint16_t` | 对比度 |
| `get/set_contrast_auto` | `uint8_t` | 自动对比度开关 |
| `get/set_gain` | `uint16_t` | 增益 |
| `get/set_saturation` | `uint16_t` | 饱和度 |
| `get/set_sharpness` | `uint16_t` | 锐度 |
| `get/set_gamma` | `uint16_t` | 伽马 |
| `get/set_hue` | `int16_t` | 色相（度，有符号，如 -180~180） |
| `get/set_hue_auto` | `uint8_t` | 自动色相开关 |
| `get/set_backlight_compensation` | `uint16_t` | 背光补偿 |
| `get/set_power_line_frequency` | `uint8_t` | 防闪烁频率：0=关 1=50Hz 2=60Hz（**中国用 50Hz**） |
| `get/set_digital_multiplier` | `uint16_t` | 数字放大倍数（步进值） |
| `get/set_digital_multiplier_limit` | `uint16_t` | 数字放大上限 |

### 3.2 白平衡

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_white_balance_temperature` | `uint16_t` | 色温 K（如 5000 = 5000K） |
| `get/set_white_balance_temperature_auto` | `uint8_t` | 自动白平衡开关 |
| `get/set_white_balance_component` | `uint16_t` + `uint16_t` | 蓝/红分量增益 |
| `get/set_white_balance_component_auto` | `uint8_t` | 分量自动白平衡开关 |

### 3.3 模拟视频遗产

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_analog_video_standard` | `uint8_t` | 制式（PAL/NTSC/SECAM…） |
| `get/set_analog_video_lock_status` | `uint8_t` | 模拟信号锁定状态 |

### 3.4 选择器单元

| 接口 | 数据 | 含义 |
|------|------|------|
| `get/set_input_select` | `uint8_t` | 多输入设备（如双摄像头模块）选择哪一路输入 |

> 加上 Phase 8 的电源模式，就是 v0.0.7 高层控制的全部家底。

---

## 4. 四个使用通则

1. **先问边界再写值**：任何 set 之前，用 get 的 `GET_MIN`/`GET_MAX` 问清范围（演示程序对曝光就是这么做的）。盲写超范围值，设备要么拒绝（PIPE）要么钳制，结果不可预期。
2. **每个调用独立容错**：家用摄像头控制支持参差不齐（定焦没对焦、廉价货没白平衡），像演示程序那样每个调用单独判断、失败继续。
3. **流中可用**：控制线不依赖数据线（第 00 课的两条分线），开流后照样调（官方示例在流中设 AE 模式；Phase 11 演示流中读 AE 模式）。
4. **自动/手动互斥要自己维护**：比如手动白平衡生效前通常要先关自动白平衡——libuvc 不会替你排队这些语义。

## 5. 真实运行示例

`demos/phase9_controls.c`（需 D1 解决后运行）：曝光（AE 模式 + 曝光时间读写回环）→ 白平衡（色温/分量/自动）→ 图像质量（亮度 +10 写回验证再恢复，其余只读）→ 其他（电源频率/变焦/隐私）。

预期输出形态（ACER 内置摄像头，实际以真机为准）：

```
== 曝光 ==
  当前 AE 模式: 2 (1=手动 2=自动 4=快门优先 8=光圈优先)
  曝光时间: 78 (7 ms)
  set_exposure_abs(一半) -> 成功
  读回曝光: 39
== 图像质量 (Processing Unit) ==
  亮度: 128（最小/最大见 GET_MIN/GET_MAX）
  set_brightness(+10) -> 成功
  写后读回: 138
== 其他 ==
  焦距(变焦): 不支持（定焦摄像头）
```

**验证点**：写入后读回一致（写回环验证）；不支持的控制干净报错。

---

## 6. 本 Phase 小结

- 全部高层控制 = Phase 8 万能通道的模板化封装（CT 用 camera terminal ID，PU 用第一个 PU ID）
- 三大使用通则：先问范围、独立容错、流中可用
- 完整函数清单与数据含义见上表（共 35 对 + 电源模式，覆盖 v0.0.7 全部）

自检清单：
- [ ] 知道 CT 系与 PU 系控制寻址到不同 unit
- [ ] 能背出最常用 5 个：ae_mode、exposure_abs、brightness、wb_temperature、gain 的数据类型
- [ ] 知道 brightness/hue 是有符号的，exposure_abs 单位 0.1ms，pantilt_abs 单位 0.0001°
- [ ] 会用 GET_MIN/GET_MAX 先问范围再写

下一步：Phase 10 帧格式转换——把 YUYV 变成能显示/能存盘的 RGB。
