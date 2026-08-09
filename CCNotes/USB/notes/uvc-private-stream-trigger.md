# UVC 私有命令触发码流方案

> 核心思路：标准 UVC 管道搭好但不发有效帧，等待私有 XU 命令才真正开码流。
> 场景：标准 UVC 只管传输管道（分辨率/帧率/带宽），**数据内容**（编码器是否启动、sensor 是否出图）由私有协议控制。

---

## 一、背景：UVC 取流的两层控制

```
┌─────────────────────────────────────────────────┐
│ 层 1：UVC 标准协议（Host OS 驱动管）              │
│   Probe → Commit → SET_INTERFACE → ISOC/BULK     │
│   管"怎么传"：分辨率、帧率、带宽、端点              │
│   这一步完成后，管道已建立，但设备可以不发有效帧     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ 层 2：私有 XU 命令（厂商应用管）                   │
│   管"传什么"：编码器启停、sensor 出图、码流类型     │
│   设备端只看私有 XU 才真正启动编码/推流            │
└─────────────────────────────────────────────────┘
```

**关键理解**：UVC 标准命令（Probe/Commit/SET_INTERFACE）只是协商传输参数、建立管道，**不等价于"开始推流"**。设备端完全可以在 streaming on 之后不发有效帧，等待私有触发。

---

## 二、两种方案对比

### 方案 A：空帧占位（推荐，OS 兼容性好）

```
标准 UVC 协商 → VS_COMMIT → streaming on (SET_INTERFACE alt≠0)
    ↓
设备端：等时/批量通道跑起来，但只发"空帧"
    - payload = 0（仅 UVC 帧头）
    - 或纯 header 无数据
    ↓
主机发私有 XU 命令（XU_CODEC_START）
    ↓
设备端：编码器/Sensor 真正启动，开始填充有效帧
```

| 优点 | 缺点 |
|------|------|
| OS 驱动不会超时报错 | 上层应用看到的前几帧是黑的/空的 |
| 标准 Camera app 不会认为设备挂了 | 需要应用层丢弃空帧 |
| Windows DShow / Linux V4L2 均兼容 | 空帧期间仍占 USB 带宽（虽然很少） |

### 方案 B：私有触发独占

```
标准 UVC 协商 → VS_COMMIT → streaming on
    ↓
设备端：完全不发流，等时通道空闲（IN token 返回 NAK 或 ZLP）
    ↓
主机发私有 XU 命令 → 设备才开始真正推流
```

| 优点 | 缺点 |
|------|------|
| 控制权完全在私有应用手里 | 标准 UVC 驱动可能超时报错 |
| 零带宽浪费 | 标准 Camera app 无法使用 |
| 更安全（未授权应用看不到任何画面） | Windows DShow 可能几秒后报设备断开 |

---

## 三、XU 命令定义示例

```
Extension Unit (GUID: {厂商私有GUID})
├── Control Selector 0x10: CODEC_START      // 开启编码器
├── Control Selector 0x11: CODEC_STOP       // 停止编码器
├── Control Selector 0x12: CODEC_PARAMS     // 编码参数（码率/GOP/QP 等）
├── Control Selector 0x13: SENSOR_POWER     // Sensor 上下电
└── Control Selector 0x14: STREAM_STATE     // 查询当前码流状态（idle/sending）
```

Host 端通过 UVC 控制管道（EP0）发 `SET_CUR` / `GET_CUR` 到 XU 即可，**不需要额外内核驱动**（UVC 驱动本身支持透传 XU 命令）。

---

## 四、设备端固件状态机

```
                    ┌─────────┐
                    │  IDLE   │  Sensor 未上电，编码器未初始化
                    └────┬────┘
                         │ UVC streaming on (SET_INTERFACE alt≠0)
                         ↓
                    ┌─────────┐
                    │ PIPED   │  Sensor init 完成，ISP 就绪
                    │         │  等时通道发空帧（方案A）/ 不发（方案B）
                    └────┬────┘
                         │ 私有 XU: CODEC_START
                         ↓
                    ┌─────────┐
                    │ STREAM  │  编码器启动，填充有效帧
                    │ ACTIVE  │  正常推流中
                    └────┬────┘
                         │ 私有 XU: CODEC_STOP 或 streaming off
                         ↓
                    ┌─────────┐
                    │  IDLE   │  编码器停，Sensor 可下电（视策略）
                    └─────────┘
```

---

## 五、实际注意事项

| 问题 | 说明 | 建议 |
|------|------|------|
| **Sensor 初始化时机** | 标准 UVC 阶段 sensor 可能还没出图 | streaming on 时至少完成 sensor init + ISP 配置，XU 命令到后直接开编码器 |
| **启动延迟** | 从收到 XU 命令到出帧有延迟 | 在 CODEC_START 之后预留 100~200ms 再期望有效帧 |
| **OS 超时（方案 B）** | Windows DShow / Linux V4L2 在 streaming on 后预期数据到来 | 长时间无数据可能触发驱动层超时或错误回调；方案 A 可避免 |
| **功耗** | Sensor + ISP 早开但空跑浪费功耗 | streaming on 时只做最小初始化（ISP 配置），XU 到后再开 sensor 出图 |
| **多应用冲突** | 标准 camera app 打开设备 → streaming on 自动发 → 无 XU 命令就永远黑屏 | 方案 A 下至少标准 app 能看到"正在推流但无画面"；方案 B 下标准 app 直接报错 |
| **码流类型切换** | 先发 XU 切换码流类型，再开流（顺序不能反） | XU → usleep(200ms) → UVC streaming on。开流中途切码流必须先停流 |

---

## 六、和已有 XU 协议的关系

本方案建立在已有 XU 扩展协议之上（见 `uvc-xu-extension-protocol-design.md`）：

```
CS_ID=0x05 FUNC_SWITCH → 选择操作目标
    ↓
CS_ID=0x10 CODEC_CTRL → SubFunc=0x01 START / SubFunc=0x02 STOP / SubFunc=0x03 PARAMS
    ↓
CS_ID=0x06 ERRCODE → 校验执行结果
```

CODEC_CTRL 使用标准的三阶段流程（FUNC_SWITCH → GET_LEN → SET_CUR/GET_CUR）。

---

## 七、Host 端调用流程

```c
// 1. 标准 UVC 开流（建立管道）
uvc_open(&devh, &ctrl);
// 此时设备进入 PIPED 状态，发空帧

// 2. 私有 XU：启动编码器
xu_subfunc_set(devh, CS_ID_CODEC_CTRL, SUBFUNC_START, &params, sizeof(params));
// 等待设备启动
usleep(200000);  // 200ms

// 3. 正常收帧
uvc_start_streaming(devh, &ctrl, frame_cb, NULL, 0);

// 4. 停止编码器（可选的优雅关闭，先停码流再关管道）
xu_subfunc_set(devh, CS_ID_CODEC_CTRL, SUBFUNC_STOP, NULL, 0);
uvc_stop_streaming(devh);
uvc_close(devh);
```

---

## 八、一句话总结

**UVC 标准协商 = 建立水管（管径/流速/方向），私有 XU = 打开水龙头。** 管道搭好不等于水要流，设备端完全由固件控制"什么时候真正出图"。方案 A（空帧占位）是工程上最稳妥的选择。
