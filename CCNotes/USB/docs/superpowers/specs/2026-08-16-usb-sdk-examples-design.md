# USB SDK 最小代码示例集 — 设计规格

> 创建日期：2026-08-16（第十二会话）
> 状态：设计已与用户逐节确认（示例清单 / 存放形式 / 页面风格 / 实现方案 / 设计决策）

## 一、背景与目标

主线学习（81/88）全部完成，项目进入 SDK 动工阶段。用户需要一个**独立 HTML 页面**，收录**最小可独立运行的 USB 代码示例**，每份聚焦一个功能（可独立编译、含编译命令），并配详细的功能讲解，作为写 SDK 前的"代码地图"和速查手册。

目标用户：用户本人（C/C++ 应用工程师，已完成 Phase 1-8 学习）——页面定位是**讲课本 + 实验手册**，不是产品文档。

## 二、文件清单

```
code/examples/                      ← 13 份可独立编译的最小示例（新增目录）
    ├── 01_enum_devices.c
    ├── 02_hotplug_detect.c         ← 由现有 code/hotplug_demo.c 迁移改名（迁移完成后删除原 code/hotplug_demo.c 避免双份，HANDOFF 引用同步更新为 examples/02_hotplug_detect.c）
    ├── 03_desc_tree_walk.c
    ├── 04_claim_alt_setting.c
    ├── 05_clear_halt.c
    ├── 06_uvc_brightness.c
    ├── 07_uvc_probe_commit.c
    ├── 08_uvc_open_stream.c
    ├── 09_xu_minimal.c
    ├── 10_frame_mailbox.c
    ├── 11_cdc_serial.c
    ├── 12_hid_report.c
    └── 13_sdk_skeleton.c
code/examples/README.md              ← 索引表 + 学习路径 + 同步纪律
usb-sdk-examples.html                ← 新页面（单文件零依赖）：13 份代码内嵌 + 讲解
```

## 三、13 份示例清单

统一编译命令 `gcc -o xxx xxx.c -lusb-1.0`（例外的标出）。运行统一 `sudo ./xxx`（10 例外）。

| # | 文件 | 学什么 | 编译 | 真机预期（2bdf:0101） |
|---|------|--------|------|------|
| 01 | 01_enum_devices.c | 枚举：抄花名册，过滤 VID:PID | 标准 | 列出全部设备，高亮 2bdf:0101 |
| 02 | 02_hotplug_detect.c | 热插拔：ARRIVED/LEFT 回调 | 标准 | ENUMERATE 刷屏 + 实时打印（已真机验证） |
| 03 | 03_desc_tree_walk.c | 描述符树：递归打印 config→iface→alt→ep | 标准 | 打印 433 字节链的树形结构 |
| 04 | 04_claim_alt_setting.c | claim + 切 Alt：四层动作后两层 | 标准 | claim 成功；Alt0→Alt1 切换成功 |
| 05 | 05_clear_halt.c | Halt 恢复闭环：STALL→GET_STATUS→clear_halt | 标准 | 对不存在端点发请求 → PIPE → 闭环演示 |
| 06 | 06_uvc_brightness.c | 标准 UVC 亮度：PU GET_CUR/SET_CUR | 标准 | ★ GET_CUR 返回 STALL（本设备 PU 空壳，bmControls=00 00） |
| 07 | 07_uvc_probe_commit.c | Probe/Commit：GET_MIN/MAX/DEF + 试问 | 标准 | 打印设备自报格式/分辨率/帧率范围 |
| 08 | 08_uvc_open_stream.c | 开流：Probe/Commit + SET_INTERFACE + 收 1 秒统计 | 标准 | 开流后收 1 秒裸数据，打印字节数（不拼帧只统计） |
| 09 | 09_xu_minimal.c | XU：FUNC_SWITCH→GET_LEN→GET_CUR（读版本） | 标准 | GET_LEN CS_ID=0x04 返回 2 字节版本号 |
| 10 | 10_frame_mailbox.c | 信箱模式：libuvc 取流 + 标志位回调 | `gcc -o xxx xxx.c -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)` | 窗口显示画面，主线程渲染 |
| 11 | 11_cdc_serial.c | CDC 串口：SET_LINE_CODING + 批量收发 | 标准 | ★ 需 CDC 设备（默认 2bdf:028a，参数化 VID:PID） |
| 12 | 12_hid_report.c | HID 报表：中断 IN 读报表 | 标准 | ★ 需 HID 设备（默认 2bdf:028a 厂商 HID，或键盘） |
| 13 | 13_sdk_skeleton.c | 综合骨架：热插拔 + 枚举 + 打开 + 开流串联 | `-lusb-1.0 -pthread` | 启动刷现有设备 → 插拔自动响应 → 对摄像头自动开流 |

## 四、页面结构与视觉规范

### 页面骨架（usb-sdk-examples.html）

```
┌────────────────────────────────────────────┐
│ 侧边栏（260px）            │ 正文          │
│ ├─ 标题 + 简介             │               │
│ ├─ 搜索过滤                │               │
│ ├─ 目录（13 项，按组折叠）   │               │
│ │   ├─ 设备层 01~05        │               │
│ │   ├─ UVC 层 06~10        │               │
│ │   ├─ 其他类 11~12        │               │
│ │   └─ 综合骨架 13         │               │
│ └─ 快捷提示（编译命令模板）  │               │
└────────────────────────────┴───────────────┘
```

### 示例卡片模板（每个示例一张卡，统一结构）

1. **标题**：`01 枚举设备 · enum_devices.c`
2. **目标卡**：学什么（1 行）
3. **编译运行卡**：编译命令 + 运行命令（带一键复制按钮，`navigator.clipboard`）
4. **预期现象卡**：真机跑起来会看到什么（★ 教学点黄色调标注，如 06 的 STALL）
5. **代码块**：完整源码，`<pre>` + CSS 行号，**关键行高亮**（`<span class="hl">` 标出与协议对应的行）
6. **逐段讲解**：3~5 段「代码 ↔ 协议」对照（引用代码片段 + KB 章节引用）

### 视觉规范

- 暗色 IDE 风格，沿用 usb-notes 语义色板（帧/CRC/数据等颜色继续使用），自带独立小 CSS（约 300 行）
- 交互：锚点滚动 + 搜索过滤（简单字符串匹配，~30 行 JS）+ 复制按钮 + 折叠组
- 示例顺序即学习路径：设备层 → UVC 主战场 → 其他类 → 综合；页面顶部放"建议学习顺序"说明

## 五、.c 头注释约定 + README

### 每个 .c 文件统一头注释

```c
/* ============================================================
 * 04_claim_alt_setting.c —— claim 接口 + 切换 Alt Setting
 *
 * 学什么:  四层动作的后两层——claim（所有权登记）与 set_interface_alt_setting
 *          （SET_INTERFACE 的代码版），以及切换前后端点状态的变化
 * 对应知识点: KB 第九篇 §9.2 深挖（open ≠ 开流）
 * 编译:    gcc -o claim_alt claim_alt_setting.c -lusb-1.0
 * 运行:    sudo ./claim_alt 2bdf 0101
 * 预期:    打印 claim 结果 → Alt0 切 Alt1 → 打印新端点状态
 * ============================================================ */
```

### README.md 结构

一张总表（序号/文件/学什么/编译/预期）+ 学习路径建议 + 与 HTML 页面的关系说明。

## 六、设计决策（已确认）

1. **06 亮度示例的"预期失败"**：2bdf:0101 的 PU 是空壳（bmControls=00 00），GET_CUR 必然 STALL→PIPE。代码写好错误处理并打印说明；页面预期现象卡用 ★ 标注这是**教学点不是 bug**（第六篇 §6.20 的专业设备常态）。换罗技等标准摄像头同一份代码直接生效。
2. **11/12 设备前提**：CDC/HID 示例需对应设备（TM5X 2bdf:028a 同时有 CDC+HID 一台搞定）。VID:PID 参数化，默认 2bdf:028a。
3. **代码同步政策**：code/examples/*.c 是唯一可编译真相源；HTML 内嵌副本。改动时两边同步（README 写明纪律）。
4. **范围外声明**：不做异步等时取流完整实现（libuvc 的活）、不做 Windows 构建支持（示例面向 Ubuntu VM，代码本身兼容）、不做代码生成器。

## 七、范围检查

- 13 份示例全部面向"最小可独立运行"（单文件、统一编译命令、无跨文件依赖）
- 页面单文件零依赖（双击即用，与 usb-notes 原则一致）
- 无 TBD/占位符；矛盾点已核对（04 与 08 的分工：04 专注 claim+切Alt 动作本身，08 专注 UVC 开流全流程）
