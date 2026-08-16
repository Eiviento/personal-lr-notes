# USB 协议学习项目 — 导航说明

> 这是一份文件导航：长时间没看这个项目时，先读本文件，30 秒内找到你要的东西。
> 整理日期：2026-08-16。当前状态：**协议主线全部学完（81/88 知识点），下一步是 SDK 动工**。

---

## 一、我该先看什么？（按你的目的对号入座）

| 你想做的事 | 去哪 | 怎么用 |
|-----------|------|--------|
| **刚回来，不知道进度到哪** | `HANDOFF.md` | 会话交接文档：进度、各会话干了什么、下一步计划，全在里面 |
| **复习/查某个协议知识点** | `USB-Protocol-Knowledge-Base.md` | 单文件全量知识库（九篇 + 附录速查表），Ctrl+F 搜关键词 |
| **看理论学习可视化** | 双击 `usb-notes.html` | 暗色 IDE 风格网页，Phase 1-8 全部卡片 + 搜索 |
| **查最小代码示例（写 SDK 用）** | 双击 `usb-sdk-examples.html` | 13 份示例讲解页：每份含完整代码 + 编译命令 + 预期现象 |
| **编译运行示例代码** | `code/examples/` | 13 份独立 .c 文件，拷到 Ubuntu VM 逐个编译（README 表在 examples/README.md） |
| **参考实战工具代码** | `code/tools/` | 取流 viewer、XU 调试工具、TM76 完整参考 |
| **看学习计划全貌** | `usb-protocol-learning-plan.md` | 88 个知识点的清单与完成状态 |
| **查真机抓包/描述符 dump** | `captures/` | 2 个 pcapng（Wireshark 打开）+ 3 台设备的原始描述符 |
| **看三设备描述符对比** | 双击 `descriptor-viewer.html` | 三台海康设备描述符逐字节对比页 |
| **查历史设计文档** | `docs/superpowers/` | specs/ 设计规格、plans/ 实现计划 |

**最常用的四个入口，记住就行**：`HANDOFF.md`（进度）→ `USB-Protocol-Knowledge-Base.md`（知识）→ `usb-notes.html`（可视化）→ `usb-sdk-examples.html`（代码）。

---

## 二、目录结构总览

```
CCNotes/USB/
├── README.md                        ← 你正在看的导航文件
├── HANDOFF.md                       ← ★ 会话交接（每次新会话必读的第一份）
├── USB-Protocol-Knowledge-Base.md   ← ★ 知识库整合文档（全部知识点的唯一真相源）
├── usb-protocol-learning-plan.md    ← 学习计划（88 知识点，主线全部完成）
│
├── usb-notes.html                   ← ★ 理论可视化主页面（双击打开）
├── usb-notes.css                    ←  ↑ 它的样式（3 文件架构，改样式改这里）
├── usb-notes.js                     ←  ↑ 它的脚本（改交互改这里）
├── usb-sdk-examples.html            ← ★ 13 份最小示例讲解页（单文件，双击打开）
├── descriptor-viewer.html           ← 三设备描述符对比页（单文件，双击打开）
│
├── archive/
│   └── usb-notes-old.html           ← 翻新前的旧版页面备份（只存档，不看）
│
├── captures/                        ← 真机采集数据（不编辑，只查阅）
│   ├── capture.pcapng               ← 全量抓包：174K 包 / 6 设备 / 225.7s
│   ├── capture-tm5x-2bdf028a.pcapng ← TM5X 单设备抓包（知识库 §4.11a 的引用对象）
│   └── usb设备1/2/3的描述符.txt      ← 三台海康设备的原始描述符 dump
│
├── code/
│   ├── examples/                    ← ★ 教学示例（写 SDK 前先跑通这些）
│   │   ├── 01_enum_devices.c        ←   枚举设备
│   │   ├── 02_hotplug_detect.c      ←   热插拔检测
│   │   ├── 03_desc_tree_walk.c      ←   描述符树遍历
│   │   ├── 04_claim_alt_setting.c   ←   claim + 切 Alt
│   │   ├── 05_clear_halt.c          ←   Halt 恢复闭环
│   │   ├── 06_uvc_brightness.c      ←   标准 UVC 亮度（★ 预期 STALL 教学点）
│   │   ├── 07_uvc_probe_commit.c    ←   Probe/Commit 协商
│   │   ├── 08_uvc_open_stream.c     ←   开流
│   │   ├── 09_xu_minimal.c          ←   XU 扩展单元通信
│   │   ├── 10_frame_mailbox.c       ←   信箱模式取流（libuvc + OpenCV）
│   │   ├── 11_cdc_serial.c          ←   CDC 串口（需 TM5X 2bdf:028a）
│   │   ├── 12_hid_report.c          ←   HID 报表（需 TM5X 2bdf:028a）
│   │   ├── 13_sdk_skeleton.c        ←   综合骨架（热插拔+打开+开流）
│   │   └── README.md                ←   13 份示例的编译命令总表
│   └── tools/                       ← 实战工具（历史产物，写 SDK 时参考）
│       ├── uvc_stream_viewer.cpp    ← ★ libuvc 取流 + OpenCV 显示（能直接跑）
│       ├── xu_interactive.c         ← 交互式 XU 调试工具
│       ├── xu_minimal_get.c         ← 最简 XU 读示例
│       ├── HIKVISION_TM76_libusb_3.c ← 海康 TM76 裸 libusb 完整参考（手工拼帧）
│       └── uvc_xu_subfunc_framework.c ← UVC XU 封装库
│
├── notes/                           ← 分阶段学习笔记（原始素材）
│   ├── phase1/2/3-*.md              ← Phase 1-3 阶段笔记
│   ├── real-device-descriptor-analysis.md ← 三设备描述符实战笔记
│   ├── uvc-xu-extension-protocol-design.md ← UVC XU 协议设计
│   ├── uvc-private-stream-trigger.md ← UVC 私有命令触发码流方案
│   └── xu-new-device-setup-guide.md ← 新设备上手实操指南
│   （注：这些内容已全部整合进知识库，笔记只作原始存档）
│
├── docs/superpowers/
│   ├── specs/                       ← 各阶段设计规格（5 份，按日期命名）
│   └── plans/                       ← 各阶段实现计划（4 份，按日期命名）
│
└── .superpowers/sdd/                ← SDD 进度账本（开发流程用的临时文件，git 忽略）
```

---

## 三、编辑约定（改文件前必读）

| 改什么 | 去哪改 | 注意 |
|--------|--------|------|
| 知识点内容 | `USB-Protocol-Knowledge-Base.md` | 知识库是唯一真相源；改完同步 HANDOFF 的交叉引用 |
| 理论可视化页面 | `usb-notes.html`（内容）/ `.css`（样式）/ `.js`（行为） | 3 文件架构，4 空格缩进 |
| 示例讲解页 | `usb-sdk-examples.html` | 内嵌代码必须与 `code/examples/*.c` 保持逐字节一致（同步纪律） |
| 示例代码 | `code/examples/*.c` | 每份独立可编译；头注释五要素（学什么/知识点/编译/运行/预期） |
| 会话记录/进度 | `HANDOFF.md` | 每次会话结束更新 |

**Git 习惯**：所有工作直接在 main 分支上进行，不用功能分支；写文件 → commit → push。

---

## 四、Ubuntu 虚拟机配套

- 代码在 Windows 上编辑（本目录），拷到 Ubuntu VM `~/桌面/hikusb/` 编译运行
- 编译命令：`gcc -o xxx xxx.c -lusb-1.0`（示例 10 加 `-luvc` + opencv，示例 13 加 `-pthread`）
- 运行需要 `sudo`；真机设备：海康热成像 2bdf:0101（UVC）、TM5X 2bdf:028a（UVC+CDC+HID 三合一）
