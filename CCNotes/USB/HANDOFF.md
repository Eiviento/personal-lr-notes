# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-08-13（第十会话）
> 主线学习进度：33/67 知识点（49%）— Phase 4 进行中（4.1 已完成）
> 本会话重点：**Phase 4.1 枚举开讲** + UVC 标准控制问答（PU/XU/请求码全家桶）+ **wValue 字节序真机验证修正** + 知识库重编号（六篇结构）
> 上一会话（第九会话）：USB 协议知识库整理
> **⚠️ 工作分支: `redesign/usb-notes-3file`（未合并到 main）**

---

## 一、这个项目在做什么（给完全没有上下文的新会话）

### 主线任务：USB 协议系统学习

带一位 C/C++ 应用软件工程师从零开始学 USB 协议，最终目标是构建一个 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）。

用户选的是**方案 A（自底向上）**：先讲协议理论，最后才写代码。

### 副线任务：笔记 Web 可视化

把学习笔记做成**离线 HTML 页面**，零外部依赖，双击打开。已从单文件翻新为 3 文件架构：
- `usb-notes.html` — Phase 1-4 理论可视化（纯 HTML 结构，~2,670 行）
- `usb-notes.css` — 10 层分层样式（1,153 行，暗色默认 IDE 风格）
- `usb-notes.js` — 4 模块脚本（885 行，数据/渲染/交互/初始化）
- `descriptor-viewer.html` — 三台真实海康设备的描述符实战对比（未翻新，仍为单文件）

---

## 二、各会话完成了什么

### 第一~三会话：Phase 1-3 理论学习（32/67 知识点，48%）

| 阶段 | 内容 | 产物 |
|------|------|------|
| Phase 1 | USB 概述：拓扑、速度、总线架构 | `notes/phase1-usb-overview.md` |
| Phase 2 | 通信模型：四种传输、包结构 | `notes/phase2-communication-model.md` |
| Phase 3 | 描述符体系：逐字节解剖 | `notes/phase3-descriptors.md` |

### 第四会话：真实设备描述符实战剖析

用户提供三台海康设备 USB dump → 生成独立实战笔记 `real-device-descriptor-analysis.md`（~1300 行） + 独立 HTML `descriptor-viewer.html`。

### 第五会话：控制传输深层剖析 + SETUP 逐位 + UVC 扩展协议设计

控制传输 SETUP/DATA/STATUS 三阶段模型深层追问 → UVC XU CS_ID+SubFunc 二级命名空间协议设计。

### 第六会话：Ubuntu 实战——从零打通 XU 通信

用户在 Ubuntu 虚拟机上用热成像摄像头（HIK 2bdf:0101），从 `lsusb` 查描述符到写代码跑通第一条 XU 命令，中间踩坑 → 建立了一套完整的新设备上手方法论。

### 第七会话：usb-notes.html 全面翻新

将 `usb-notes.html` 从单文件 3,266 行全面翻新为 3 文件架构，使用 Subagent-Driven Development 流程执行。

**翻新动机**：用户要求优化前端页面，包括视觉设计（技术文档/IDE 风）、数据可视化、导航体验、代码质量、可访问性五个维度。经 brainstorming → spec → plan → implement 完整流程。

**本次会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| HTML | `usb-notes.html` | **重写**：单文件 3,266 行 → 纯结构 2,239 行。去掉 `<style>`/`<script>`，4 空格统一缩进，38/38 卡片完整迁移 |
| CSS | `usb-notes.css` | **新建**：1,153 行，10 层分层（变量→重置→排版→布局→组件→可视化→工具→响应式→减少动画→打印） |
| JS | `usb-notes.js` | **新建**：885 行，4 模块（Data→Renderers→Interaction→Init） |
| 备份 | `usb-notes-old.html` | **保留**：翻新前单文件完整备份 |
| 文档 | `docs/superpowers/specs/2026-08-02-usb-notes-redesign.md` | **新建**：设计规格 |
| 文档 | `docs/superpowers/plans/2026-08-02-usb-notes-redesign.md` | **新建**：实现计划（8 个 Task） |

**翻新要点：**
- 🎨 视觉：双色板体系（文档色板 + USB 语义色），暗色默认 IDE 风格，4px 间距网格，五级字号
- 📊 可视化：包图 tooltip 多行重设计、byte-map hover 发光、时间线胶囊形+左侧色条、Bus Hound CSS 行号
- 🧭 导航：260px 侧边栏 + 实时搜索过滤 + 48% 进度条 + rAF 节流滚动监听 + 回到顶部按钮
- ⚡ 代码质量：CSS 10 层分层、JS 4 模块、`<head>` 防闪白同步脚本阻断、meta 标签补全
- ♿ 可访问性：跳过链接、全部 ARIA 属性、`:focus-visible` 统一 focus 样式、`prefers-reduced-motion`、打印样式、移动端汉堡菜单 overlay
- 📱 响应式：≤1023px 单断点，侧边栏 → 顶部 sticky 导航条 + overlay

**翻新过程中发现并修复的 Bug：**
1. `txnDetail` 详情面板原放在 `<main>` 最底部（距时间线 700+ 行），点击展开屏幕外不可见 → 移至时间线正下方内嵌
2. 旧文件 kp-2-19 折叠区 HTML 结构断裂，Phase 3 卡片被错误嵌套其中 → 从 git 历史恢复完整结构
3. 坑 6 代码示例中 `</article>` 未转义 → 浏览器提前关闭卡片，坑 7/8 掉到卡片外 → 转义为 `&lt;/article&gt;`
4. 缺少旧 CSS 变量 `--svg-line`/`--svg-text`/`--svg-fill` 导致 SVG 图渲染异常 → 补入 CSS Layer 1
5. 移动端 overlay 为静态 HTML 副本 → JS `NavOverlay.open()` 改为 clone `.sidebar`

**本次会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 代码 | `code/xu_minimal_get.c` | **新增**：最小示例，直接读 CS_ID=0x04 协议版本（无 SubFunc） |
| 代码 | `code/xu_interactive.c` | **新增**：交互式 XU 调试工具，预置设备列表、手动选 CS_ID/SubFunc、每步展示 SETUP 8 字节包结构 |
| 笔记 | `notes/xu-new-device-setup-guide.md` | **新增**：新设备上手实操指南（8 章）——lsusb → 参数 → SETUP 包构造 → 取流流程 |
| 笔记 | `notes/phase2-communication-model.md` | 末尾新增「补充问答七：接口与端点的归属关系」——四条规则 + 真实设备数据验证 |
| HTML | `usb-notes.html` | 新增 **2.3a 接口与端点的归属关系**（四条规则 + 设备树 + libusb 对比表 + Alternate Setting 折叠区）<br>新增 **✏ 开发实战踩坑记录**（8 条折叠坑） |

**用户已彻底掌握的新概念：**

1. **lsusb 三件套**：`lsusb`（找 VID/PID）→ `sudo lsusb -v -d VID:PID`（找 bUnitID/bInterfaceNumber/bmControls）→ 参数填入代码
2. **SETUP 包 8 字节换设备只改一处**：wIndex 高字节 = XU Unit ID，其他 7 字节照抄 UVC 规范
3. **libusb_control_transfer = 完整控制传输**（不是单个事务）= SETUP + DATA + STATUS 三阶段，Bus Hound 显示为 CTL + IN/OUT 两行
4. **Interface ≠ Endpoint**：Interface 是功能分类（bmRequestType 选 Inerface），Endpoint 是数据管道（批量传输直接走端点地址）。EP0 所有 Interface 共用
5. **端点归属规则**：非 EP0 端点只属于一个 Interface，两个 Interface 不能声明同一 EndpointID，Alternate Setting 可复用端点号
6. **标准 UVC 取流**：Probe(SET_CUR→GET_CUR) → Commit → SET_INTERFACE(Standard, 不是 Class!) → libusb_bulk_transfer
7. **三种 wIndex**：VC XU = `(XU_ID<<8)|VC_IF`，VS = `VS_IF`，SET_INTERFACE = Standard bmRequestType + alt_setting
8. **bmControls 位图**：`0xFF, 0x03` = bit 0~9 置位 → CS_ID 0x01~0x0A 存在

### 第十会话（本次）：Phase 4.1 枚举开讲 + UVC 标准控制问答 + 字节序真机修正

**本会话主线**：主线推进到 Phase 4（枚举）——讲完 4.1 枚举完整时间线（33/67，49%），已存知识库 + HTML。同时密集回答 UVC 标准控制追问，并完成一次重大勘误（wValue 字节序）。（用户明确说过"USB 标准请求用途"那节可以不存——其核心结论已并入第四篇 §4.1 引言。）

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 知识库 | `USB-Protocol-Knowledge-Base.md` | 新增 §6.8 标准 UVC 控制（PU）完整教程（16 条控制报文全表）；新增 §5.6 bulk-vs-等时小节、§6.5 libuvc 抽象层小节；**新增第四篇：USB 枚举过程（§4.1）**；原第四/五篇重编号为第五/六篇（4.x→5.x、5.x→6.x，交叉引用全部同步） |
| 笔记 | `notes/uvc-xu-extension-protocol-design.md` | 修正 3 处示例抓包 wValue 字节序（CS_ID 改放高字节）+ 字节序说明（2026-08-13 修正） |
| 笔记 | `notes/real-device-descriptor-analysis.md` | §3.6 从"推测"升级为"真机验证"：CS_ID 在 wValue 高字节（海康固件惯例，与 UVC 规范低字节写法不同） |
| HTML | `usb-notes.html` | 修正 10 处抓包字节序 + wIndex 表 Interface 行错误（接口号在低字节）+ 决策流图；新增 Phase 4 章节 + kp-4-1 卡片；侧边栏 1/12 ▶、进度条 49% |
| 交接 | `HANDOFF.md` | 更新（本会话） |

**本会话建立的深层理解（已存 KB）：**

1. **PU vs XU**：PU=标准处理单元（亮度/对比度等标准控制，bmControls 位图声明），XU=厂商扩展（Class 信封 + Vendor 内容，guidExtensionCode 是厂商签名）
2. **bmRequestType D6-5 三层字典**：Standard=OS USB 核心（枚举/生命周期）、Class=类驱动/应用、Vendor=厂商 SDK；半字节速判 0x0_/0x8_=Standard、0x2_/0xA_=Class、0x4_/0xC_=Vendor
3. **UVC 请求码全家桶**：SET_CUR 0x01 / GET_CUR 0x81 / GET_MIN 0x82 / GET_MAX 0x83 / GET_RES 0x84 / GET_LEN 0x85 / GET_INFO 0x86 / GET_DEF 0x87；GET_INFO 位图 D0=GET 支持、D1=SET 支持、D2=被自动模式禁用
4. **★ wValue 字节序真机事实**：海康 2bdf:0101 固件 CS_ID 在 wValue **高字节**（`CS_ID<<8`），由 xu_minimal_get.c / uvc_stream_viewer.cpp 真机验证；UVC 规范标准写法是低字节。**工作代码 > 手绘抓包 > 推测**
5. **开流 = SET_INTERFACE 切 Alt Setting**：Alt0=零带宽（无端点）、Alt1+=流端点；SET_INTERFACE 本身就是设备"开流"开关（UVC 规范 4.3.1.1）
6. **视频为什么可以用 Bulk**：完整性 vs 实时性权衡；等时=保证带宽/不重传（直播），Bulk=自动重传/不保证延迟（文件下载）；UVC 1.0/1.1 只定义等时、1.5 才加入 Bulk；热成像低分辨率+测温要完整 → 选 Bulk
7. **libuvc 抽象层**：uvc_start_streaming() 内部读描述符 → 按 bmAttributes 分叉 bulk/isoc → 用 12 字节 UVC 载荷头（FID/EOF）拼完整帧 → 回调交付 uvc_frame_t；用户代码依赖"帧"接口不依赖"包"接口
8. **枚举全景（4.1）**：6 状态机（Attached→Powered→Default→Address→Configured/Suspended）；10 步时间线；Device Descriptor 读两次（先 8 字节拿 bMaxPacketSize0）；Config 先读 9 字节头（wTotalLength）；枚举全走 EP0

### 第九会话（上一会话）：USB 协议知识库整理

**本会话任务**：用户注意到 usb-notes 中有很多分散的文件（7 个 .md + 1 个 HTML），希望把所有知识点整理成一份结构清晰、内容完整的文档。

经过 brainstorming → 设计确认 → 实施，完成了：

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 知识库 | `USB-Protocol-Knowledge-Base.md` | **★ 新建**：2,337 行单文件 Markdown，覆盖全部 7 个源文件的知识点 |
| 设计 | `docs/superpowers/specs/2026-08-02-usb-knowledge-base-design.md` | **新建**：知识库整理设计规格 |
| 交接 | `HANDOFF.md` | **更新**：补充第九会话记录和最新文件结构 |

**文档结构（六篇 + 附录，经第十会话扩充）：**

| 篇章 | 内容 | 来源 |
|------|------|------|
| 前言 | 67 知识点全景 + 学习路线图 | `usb-protocol-learning-plan.md` |
| 第一篇 | Phase 1 — USB 概览与总线拓扑（5 节） | `phase1-usb-overview.md` |
| 第二篇 | Phase 2 — 通信模型（16 节 + 4 篇补充问答） | `phase2-communication-model.md` |
| 第三篇 | Phase 3 — 描述符体系（11 节 + 4 篇补充问答 + CDC 综合示例） | `phase3-descriptors.md` |
| 第四篇 | USB 枚举过程（4.1 枚举完整时间线） | 第十会话新增（主线 Phase 4） |
| 第五篇 | 真实设备描述符实战（5 章 + 10 FAQ） | `real-device-descriptor-analysis.md` |
| 第六篇 | UVC XU 控制与取流实战（7 节 + 7 条踩坑记录） | `uvc-xu-extension-protocol-design.md` + `xu-new-device-setup-guide.md` |
| 附录 | 快速参考手册（9 张速查表：SETUP、wIndex、PID、描述符、MQTT 类比等） | 全部笔记提炼 |

**整理策略：**
- **只整合不删减**：所有笔记内容全部保留，不丢失任何知识点
- **去重归并**：SETUP 包结构在第二篇详述，后续篇章用交叉引用；wIndex 三种填法归并到第二篇，附录保留速查
- **实战紧跟理论**：描述符理论后面直接跟真实设备分析（第五篇），传输理论后面直接跟 XU 踩坑（第六篇）
- **保持原始深度**：逐字节解析、HEX dump、Bus Hound 抓包、MQTT 类比全部保留

### 第八会话：UVC 取流实战——libuvc + OpenCV + XU 码流切换

**本会话主线**：在 `xu_interactive.c`（EP0 控制传输）和裸 libusb 批量取流之间补上最后一环——**用 libuvc 做标准 UVC 取流 + OpenCV 实时显示**，并解决了热成像摄像头特有的码流类型切换问题。

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 代码 | `code/xu_interactive.c` | **修改**：GET_LEN 后新增 SET_CUR 自由选择（原来是硬编码只做 GET_CUR） |
| 代码 | `code/uvc_stream_viewer.cpp` | **★ 新建**：libuvc 取流 + OpenCV 显示，约 400 行，完整 7 步流程 |
| 笔记 | `notes/xu-new-device-setup-guide.md` | **新增第九章**：码流类型切换——为什么、什么时候、怎么切（约 200 行） |
| HTML | `usb-notes.html` | **新增 kp-2-21**「⚡ 码流类型切换实战」卡片——热成像数据分层、XU/UVC 顺序、MJPEG 欺诈 |

**本会话踩坑全记录（7 条，最重要的用 ★★★ 标注）：**

| # | 症状 | 根因 | 修复 | 重要度 |
|---|------|------|------|--------|
| 1 | SDL2 播放数秒后 segfault | 回调线程和主线程同时写/读帧缓冲区，无锁 | 换 OpenCV + `pthread_mutex_t` 保护所有帧访问 | ★★ |
| 2 | 花屏（雪花状噪点） | 默认码流类型含测温数据混在 YUV 里 | XU 命令切到类型 10 (YUV_ONLY)：FUNC_SWITCH → GET_LEN → SET_CUR [01 0A] | ★★ |
| 3 | 花屏仍在，帧只有 ~10000 字节（应该是 38400） | **描述符声称 YUYV，实际送 MJPEG**（帧数据以 `FF D8` JPEG SOI 开头） | 帧回调检测 `FF D8` 头 → 强制 `cv::imdecode` | ★★★ |
| 4 | XU 命令不执行（编译报错参数数量不对） | `libusb_control_transfer` 8 个参数漏了 `bRequest` | 补全：bmRT + bReq + wVal + wIdx + data + wLen + timeout | ★★★ |
| 5 | XU 返回 `LIBUSB_ERROR_IO` | XU 在 `uvc_open` 之后发，设备已被 uvc 占用状态不一致 | **XU 必须在 `uvc_open` 之前发**，复用 detach 时的 libusb 句柄 | ★★★ |
| 6 | OpenCV `cvtColor(YUV2BGR)` 花屏 | OpenCV YUYV 字节序与该设备不匹配 | 统一用 libuvc 的 `uvc_any2rgb` + `cvtColor(RGB2BGR)` | ★ |
| 7 | `frame->data[0]` 编译报错 | `uvc_frame_t::data` 是 `void*`，C++ 不允许 void* 下标 | 先转 `(const uint8_t *)frame->data` | ★ |

**本会话建立的深层理解：**

1. **UVC 管传输、XU 管内容** — 两层独立，标准 UVC（Probe/Commit/SET_INTERFACE）只管分辨率/帧率/编码，XU 命令管帧里装什么数据。类比：UVC=快递公司，XU=包裹内容单。
2. **先 XU 后 UVC** — 顺序不可逆。必须先发 XU 配置码流类型，等设备就绪后再开 UVC 管道。如果先开流再发 XU 切换，管道中数据格式突变 → 解码器崩溃。
3. **取流中能发 XU，但要看命令类型** — 切换码流类型：❌不能（数据格式突变）。切换伪彩/读版本/读错误码：✅能（不改数据格式）。判断标准不是物理冲突（都走 EP0），而是语义影响。
4. **不能信任 UVC 描述符** — 此设备（2bdf:0101）描述符报 YUYV，实际帧数据以 `FF D8`（JPEG mark）开头。必须在回调里检测实际数据头。
5. **MJPEG 省 74% 带宽** — 120x160 YUYV=38400 字节，MJPEG 压缩后 ~10000 字节。摄像头说谎是为了兼容性（YUYV 描述符更容易被 OS 匹配）但实际送 MJPEG 省带宽。
6. **热成像数据分层** — 探测器→测温矩阵/伪彩映射→码流多路复用器（XU CS_ID=0x03）→UVC 传输层→USB。6 种码流类型（2/3/6/8/9/10），看画面用类型 10（YUV_ONLY），测温用类型 2（TEMP_FULL）。
7. **`libusb_control_transfer` 签名** — 8 个参数：`(devh, bmRequestType, bRequest, wValue, wIndex, data, wLength, timeout)`。极易漏 bRequest。
8. **XU 控制传输走 EP0，不需要 claim 接口** — 可以独立开 libusb 句柄发 XU，和 uvc 的 VS 管道互不影响。

---

## 三、当前文件结构

```
D:\CC\personal-lr-notes\CCNotes\USB\
├── HANDOFF.md                                    ← 你正在看的这份交接文档
├── USB-Protocol-Knowledge-Base.md                 ← ★ 知识库整合文档（~2,810 行，六篇 + 附录，覆盖全部笔记）
├── usb-protocol-learning-plan.md                 ← 完整学习计划（67知识点清单）
├── usb-notes.html                                ← Phase 1-3 理论可视化（纯 HTML 结构）
├── usb-notes.css                                 ← 10 层分层样式（暗色默认 IDE 风格）
├── usb-notes.js                                  ← 4 模块脚本（数据/渲染/交互/初始化）
├── usb-notes-old.html                            ← 旧版备份（翻新前单文件版本）
├── descriptor-viewer.html                        ← 三设备描述符实战对比
├── usb设备1的描述符.txt                            ← 设备1 原始 dump
├── usb设备2的描述符.txt                            ← 设备2 原始 dump
├── usb设备3的描述符.txt                            ← 设备3 原始 dump（无 Extension Unit）
├── docs/superpowers/
│   ├── specs/
│   │   ├── 2026-08-02-usb-notes-redesign.md      ← 前端翻新设计规格
│   │   └── 2026-08-02-usb-knowledge-base-design.md ← ★ 知识库整理设计规格
│   └── plans/
│       └── 2026-08-02-usb-notes-redesign.md      ← 前端翻新实现计划
├── code/
│   ├── HIKVISION_TM76_libusb_3.c                 ← 海康 TM76 完整参考（伪彩/码流/视频流）
│   ├── uvc_xu_subfunc_framework.c                ← UVC XU 扩展协议封装库
│   ├── xu_minimal_get.c                          ← 最简示例（读 CS_ID=0x04）
│   ├── xu_interactive.c                          ← 交互式 XU 调试工具（★ 支持 SET_CUR 选择）
│   └── uvc_stream_viewer.cpp                     ← ★★★ libuvc 取流 + OpenCV 显示（第八会话核心产出）
├── notes/
│   ├── phase1-usb-overview.md                    ← Phase 1
│   ├── phase2-communication-model.md             ← Phase 2（新增接口-端点关系问答）
│   ├── phase3-descriptors.md                     ← Phase 3
│   ├── real-device-descriptor-analysis.md        ← 实战手册（FAQ 10 个）
│   ├── uvc-xu-extension-protocol-design.md       ← UVC XU 扩展协议设计
│   └── xu-new-device-setup-guide.md              ← 新设备上手实操指南（含第九章码流切换）
└── .superpowers/sdd/                             ← SDD 进度账本
```

---

## 四、当前卡在哪 + 下一步计划

### 主线学习：Phase 4 进行中（4.1 已完成）

**没有卡住。** Phase 1-3 已完成，4.1 已讲完（33/67，49%）。

**下一步：Phase 4.2 — 阶段 0：设备检测（D+ 上拉 FS/HS 或 D- 上拉 LS → Host 检测电平变化）**

一次一个知识点。当用户说"继续"时，从这里开始。

### 副线一：UVC 取流工具已完成基础

`uvc_stream_viewer.cpp` 可以正常工作——打开摄像头、切码流、取流、OpenCV 实时显示。输出为 120x160 MJPEG（经 cv::imdecode 解码后正常显示）。

**可以改进的方向：**
- 支持命令行选择分辨率（目前自动选第一个可用的，120x160）
- 支持录制（`cv::VideoWriter` 写 .avi）
- 支持截图（空格键保存当前帧）
- 支持伪彩热切换（取流中发 XU CS_ID=0x02 换调色板，~200ms 生效）
- F 键全屏切换（代码骨架已留，未实现）
- 多设备支持（当前只取第一台或指定 VID:PID）

### 副线二：usb-notes.html 翻新已完成基础，待合并

**⚠️ 翻新工作在分支 `redesign/usb-notes-3file` 上，未合并到 main。**

**合并前需用户在浏览器中验证：**
- 双击 `usb-notes.html` → 确认侧边栏搜索、主题切换、滚动监听、包图渲染、时间线点击展开、新增的 kp-2-21 卡片均正常
- 缩窄浏览器窗口到 <1024px → 确认移动端汉堡菜单 overlay 正常

验证通过后合并：
```bash
git checkout main
git merge redesign/usb-notes-3file
git branch -d redesign/usb-notes-3file
```
合并后可删除备份文件 `usb-notes-old.html`。

### 未来可能的前端优化

- `descriptor-viewer.html` 同样做 3 文件翻新
- 时间线详情面板加键盘 Escape 关闭的 focus 自动移回
- 移动端 overlay 克隆的搜索框目前是装饰（未绑定 JS）
- `color-mix()` 在极旧浏览器不支持，可视需要加 fallback

### 用户可能要求的下一步

- **主线**：说"继续" → Phase 4.2（阶段 0：设备检测——D+ 上拉/ D- 上拉的电平细节）
- **知识库**：在 `USB-Protocol-Knowledge-Base.md` 中补充后续学习内容（Phase 4+）
- **取流工具**：加录制/截图/伪彩切换/全屏
- **XU 探索**：`xu_interactive.c` 加 SET_CUR 暴力扫描未知 CS_ID
- **裸 libusb 取流**：把 TM76 的 `uvc_read_one_frame()` 逻辑改写为面向 2bdf:0101
- **前端翻新**：合并 `redesign/usb-notes-3file` 分支，或翻新 `descriptor-viewer.html`
- **编辑 HTML**：改内容→`usb-notes.html`，改样式→`usb-notes.css`，改行为→`usb-notes.js`（3 文件架构，4 空格缩进）
- **查阅知识库**：需要系统复习某个主题时，直接读 `USB-Protocol-Knowledge-Base.md`（单文件，结构清晰，含 9 张速查表）

---

## 五、用户已建立的深层理解（跨会话累积，关键！）

以下概念用户已彻底搞懂，不要重复讲解，但可以用做类比基础：

1. **ACK vs STATUS**：ACK = 包级确认（快递扫码），STATUS = 传输级确认（合同盖章）—— 来自第五会话
2. **SETUP 包 8 字节解析**：bmRequestType 的 D7(方向) + D6-5(字典) + D4-0(接收者) 三把钥匙决定其余 7 字节含义
3. **Bus Hound 局限性**：软件层抓包（URB 层），看不到 Token/PID/CRC/STATUS 阶段
4. **CS_ID + SubFunc 二级命名空间**：FUNC_SWITCH → GET_LEN → GET_CUR 三阶段
5. **STALL vs 错误码两层拒绝**：STALL=硬件拒绝，错误码=语义拒绝
6. **libusb_control_transfer = 完整控制传输**：一次调用 = 2~3 个总线事务，不是单个事务 — ★ 第六会话
7. **换新设备只改 wIndex 高字节**：XU Unit ID 从 lsusb -v 的 bUnitID 获取，其他 7 字节照抄 — ★ 第六会话
8. **Interface ≠ Endpoint**：Interface=功能分类（控制传输用），Endpoint=数据管道（批量传输用），EP0 共用 — ★ 第六会话
9. **端点归属**：非 EP0 端点只属于一个 Interface，Alternate Setting 可复用端点号 — ★ 第六会话
10. **三种 wIndex 填法**：VC XU(带 Unit ID)、VS(只有接口号)、SET_INTERFACE(Standard bmRT+alt) — ★ 第六会话
11. **bmControls 位图**：小端字节序，bit N=1 → CS_ID(N+1) 存在 — ★ 第六会话
12. **PU 与 XU 的分工**：PU=标准控制（Class 请求寻址，bmControls 位图声明支持哪些），XU=厂商私有（Class 信封 + Vendor 内容） — ★ 第十会话
13. **bmRequestType D6-5 字典速判**：0x0_/0x8_=Standard（OS USB 核心，枚举/生命周期），0x2_/0xA_=Class（类驱动/应用），0x4_/0xC_=Vendor（厂商 SDK） — ★ 第十会话
14. **wValue 字节序（海康惯例）**：CS_ID 在高字节（`CS_ID<<8`）；UVC 规范标准是低字节；真机工作代码是唯一真相 — ★ 第十会话
15. **开流 = SET_INTERFACE 切通道**：Alt0 零带宽 / Alt1+ 流端点，SET_INTERFACE 就是设备的"开流"开关 — ★ 第十会话
16. **视频 Bulk vs 等时**：完整性 vs 实时性权衡；UVC 1.5 才定义 Bulk；热成像选 Bulk 的理由 — ★ 第十会话
17. **libuvc 抽象层**：描述符→分叉 bulk/isoc→12 字节载荷头（FID/EOF）拼帧→回调交付 uvc_frame_t；依赖"帧"接口不依赖"包"接口 — ★ 第十会话
18. **枚举全景**：6 状态机、10 步时间线、Device Descriptor 读两次的原因、Config 先读 9 字节头的原因、枚举全走 EP0 — ★ 第十会话

---

## 六、不要踩的坑

### 关于用户和教学（继承）

1. **方案 A（自底向上）。** 不要催写代码。先讲协议理论，Phase 8 才是 libusb。
2. **MQTT 级别的精度。** 每个 byte 的每个 bit 含义都要展开。
3. **一次只讲一个知识点。** 等用户说"继续"才推进。
4. **方向永远从 Host 视角。** IN = Device→Host, OUT = Host→Device。
5. **"会用+懂原理"（B 档），不是内核驱动级。**
6. **用户喜欢类比。** MQTT、TCP/HTTP、快递/合同——用得好的比单纯列表有效 10 倍。
7. **计划文件是唯一真相源。**
8. **回答完追问后主动问"要不要保存到笔记？要不要补充到 HTML？"** —— 用户几乎总是说"要"。
9. **用户现在喜欢在 HTML 2.10 附近积累控制传输的知识。** 新增内容优先放那里。如果要加的内容自成体系，就开新章节。

### 关于 HTML 编辑（已翻新 — 2026-08-02）

10. **usb-notes 已翻新为 3 文件架构**：`usb-notes.html`（纯结构）+ `usb-notes.css`（全部样式）+ `usb-notes.js`（全部脚本）。编辑 HTML 时无需再处理 `<style>`/`<script>` 块。
10a. **全部文件统一 4 空格缩进**，不再有 Tab/空格混用问题。Edit 前无需用 `cat -A` 检查缩进。
10b. **零外部依赖原则不变**：CSS 和 JS 在同目录，`<link>` + `<script defer>` 引用，双击 HTML 即用。
15. **折叠用 `<details class="txn-fold">`。** 不要嵌套折叠区。
16. **描述符 byte-map 用 `.desc-byte-map` + `.dcell` + `.dc-bg-*` 类。**
17. **新增的 `.txn-annot-*` CSS 类**：用于在 Bus Hound 抓包下方标注 USB 总线事务。

### Ubuntu 实战踩坑（★ 第六会话）

18. **`lsusb -v` 必须加 `sudo`。** 不加只能看到基本设备信息，"Couldn't open device"意味着深层描述符树（Extension Unit 等）读不到。
19. **VID/PID 不要假设。** 即使是同厂商不同型号，PID 也可能不同。永远从 `lsusb` 确认。
20. **VC_IF_NUM 从 `bInterfaceNumber` 获取，不固定。** 同一个厂商的海康摄像头，TM76 的 VC 接口是 1，但 2bdf:0101 是 0。从 `lsusb -v` 找 `bInterfaceClass=14(Video) + bInterfaceSubClass=1(Video Control)` 的 `bInterfaceNumber`。
21. **`gcc -o output source.c` 不要写反。** `gcc -o xu_minimal_get.c -lusb-1.0` 会把源文件覆盖为空文件！`-o` 后面是输出文件名，源文件在后面。编译后检查 `wc -c source.c`。
22. **Linux 必须先 detach 内核驱动再 claim 接口。** `libusb_kernel_driver_active()` → `libusb_detach_kernel_driver()` → `libusb_claim_interface()`，释放时反向：release → attach。Windows 不需要这步（WinUSB 自动替换驱动）。
23. **运行程序也要 `sudo`（除非配了 udev 规则）。** 长期使用建议写 `/etc/udev/rules.d/99-thermal.rules`。
24. **GET_LEN 返回 0 是合法的，不一定是错误。** 可能是该 SubFunc 号不存在、无参数、或是触发型命令。先换已知 CS_ID（如 0x04）确认通道正常。
25. **libusb_control_transfer 是一次完整控制传输，不是单个事务。** 对应 Bus Hound 里的一行 CTL + 一行 IN/OUT = USB 总线上的 2~3 个事务。
26. **wIndex 填法取决于你在操作 VC 还是 VS。** VC XU 命令：`wIndex = (XU_ID<<8) | VC_IF`；VS 命令（Probe/Commit）：`wIndex = VS_IF`（没有 Unit ID！）；SET_INTERFACE：`bmRequestType=0x01(Standard)`，`wValue=altsetting`，`wIndex=VS_IF`。

### HTML 翻新踩坑（★ 第七会话新增）

27. **`<pre><code>` 里的 HTML 标签仍需转义！** 浏览器在 `<pre>` 内**仍然解析 HTML 标签**，`<pre>` 只保留空格/换行。代码示例中出现 `</article>` 会把外层卡片提前关闭。永远写成 `&lt;/article&gt;`。旧文件就有这个 bug，只是因为浏览器容错没暴露。
28. **详情面板必须放在触发元素附近。** `txnDetail` 面板放在页面底部 → 点击时间线块后 `display:block` 生效但面板在屏幕外，用户感知为"点不动"。详情面板紧贴触发元素下方（内嵌在同级 DOM 中）。
29. **移动端 overlay 要用 JS clone 侧边栏，不要写静态副本。** 静态副本不会同步搜索框、进度条、active 状态。`NavOverlay.open()` 应 `cloneNode(true)` 把 `.sidebar` 完整复制进 overlay。
30. **旧 CSS 变量迁移要全量覆盖。** 翻新时新增的 CSS 变量体系可能漏掉旧页面使用的变量（如 SVG 图的 `--svg-line`、占位区的 `.placeholder`）。翻新后用浏览器 DevTools "Styles 面板"检查所有未解析的 `var(--xxx)`。
31. **子代理（subagent）不提交代码。** 用 Subagent-Driven Development 时，每个 implementer agent 只创建/修改文件但不 `git commit`。调度者（controller）必须在每个 task 完成后手动 commit，否则所有改动堆在工作区无法分离。
32. **`task-brief` 脚本输出路径 = git repo root，不是当前子目录。** brief 文件写入 `.superpowers/sdd/` 下（git root），给 agent 的文件路径要指向正确位置。

### 关于协议知识（继承）

27. **Bus Hound 显示控制传输为两行：`CTL` = SETUP 包 8 字节，`OUT`/`IN` = DATA 阶段数据。** STATUS 阶段 Bus Hound 不显示（驱动层已合并）。
28. **数据走 OUT/IN 端点时 wLength 就是 Bus Hound 显示的那一行长度。**
29. **SETUP 包里 wValue/wIndex 含义由 bmRequestType 的 D6-5 和 D4-0 决定。** 不是"CS_ID 永远在 wValue 高字节"——那是 UVC Class 请求的惯例。

### UVC 取流 + XU 码流切换（★ 第八会话新增）★★★

30. **★★★ `libusb_control_transfer` 有 8 个参数，极易漏掉 `bRequest`。** 签名：`(devh, bmRequestType, bRequest, wValue, wIndex, data, wLength, timeout)`。如果写成 7 个参数——把 wValue 放在 bRequest 的位置——所有后续参数全部错位，编译报"too few arguments"或运行报 LIBUSB_ERROR_IO。
31. **★★★ XU 命令必须在 `uvc_open` 之前发，不能在之后。** `uvc_open` 之后设备被 libuvc 占用状态。在 `uvc_open` 之前用独立 libusb 句柄发 XU（EP0 不需要 claim 接口），发完再 `uvc_open`。正确流程：detach 内核驱动 → XU 切换码流类型 → uvc_open → Probe/Commit → uvc_start_streaming。
32. **★★★ 不能信任 UVC 描述符的格式声明。** 此设备（2bdf:0101）描述符报 YUYV (UncompressedFormat, GUID=YUY2)，但实际帧数据以 `FF D8`（JPEG SOI mark）开头。帧大小 ~10000 字节而非期望的 38400。必须在帧回调里检测实际数据头：`if (raw[0]==0xFF && raw[1]==0xD8) → cv::imdecode`。
33. **XU 控制传输走 EP0，不需要 claim 接口。** 可以独立于 uvc 句柄另开一个 libusb 句柄发 XU 命令。控制传输不需要 claim，只有批量/中断/等时传输才需要。两个 libusb 句柄可以同时打开同一个设备。
34. **热成像摄像头默认输出不是纯 YUV。** 码流类型多路复用器（XU CS_ID=0x03 SubFunc=0x05）默认输出类型 8（测温+YUV 混合）或类型 6（YUV+测温头）。必须先发 XU 命令切到类型 10（YUV_ONLY，数据 `[0x01, 0x0A]`）才能拿到标准解码器能用的纯 YUV 数据。
35. **取流中可以发 XU，但要分类讨论。** 切换码流类型：❌不能（数据格式突变）。切换伪彩/读版本/读错误码：✅能（不改数据格式或纯读操作）。物理上不冲突（控制传输走 EP0，视频流走 ISOC/BULK 端点），冲突在语义层。
36. **帧回调跑在 libuvc 内部线程，不能在里面做 SDL/OpenCV 渲染。** 回调只做数据转换（YUYV/MJPEG→BGR），设标志位；主线程检测标志位→加锁→读帧→渲染→解锁。用 `pthread_mutex_t` 或 `SDL_mutex` 保护帧缓冲区。
37. **`uvc_frame_t::data` 是 `void*`，C++ 编译不能直接下标。** 必须先转 `(const uint8_t *)frame->data` 再访问 `[0]` 和 `[1]`。
38. **`uvc_get_stream_ctrl_format_size` 的自动协商可能选不到正确格式。** 如果常规协商（传 YUYV/MJPEG 枚举值）全部失败，回退到遍历原始格式描述符链（`uvc_get_format_descs`），逐个 `wWidth`/`wHeight`/`dwDefaultFrameInterval` 去试。fps 传 0 表示"无所谓"。

### 关于平台

39. **用户环境是 Windows + Git Bash。** Shell 用 Bash 语法，路径用正斜杠。
40. **git 仓库根目录在 `D:/CC/personal-lr-notes/`。** USB 项目在 `CCNotes/USB/` 子目录。
41. **Windows 端编辑代码，Ubuntu VM 端编译运行。** 代码在 Windows（`D:\CC\personal-lr-notes\CCNotes\USB\code\`），需每次拷贝到 Ubuntu VM（`~/桌面/hikusb/`）再 `gcc`/`g++` 编译。文件不同步是常见问题——VM 里编译报旧错误先检查文件是否最新。
42. **网络需要代理（127.0.0.1:7890）。**
43. **Ubuntu 虚拟机**（`fdl@fdl-virtual-machine`），工作目录 `~/桌面/hikusb/`。

### 知识库结构与协议事实（★ 第十会话新增）

44. **★★★ 知识库篇章编号已重排（2026-08-13）！** 现在是六篇：第四篇=USB 枚举过程（新），第五篇=真实设备描述符实战（原第四篇，4.x→5.x），第六篇=UVC XU 控制与取流实战（原第五篇，5.x→6.x）。KB 与 HANDOFF 的交叉引用已全部同步，**不要再写旧编号**——"第五篇 §5.4 码流切换"现在应写"第六篇 §6.4"。
45. **★★★ wValue 字节序（海康惯例 vs UVC 规范）**：2bdf:0101 固件把 CS_ID 放在 wValue **高字节**（`CS_ID << 8`，如 CS_ID=0x05 → wValue=0x0500）；UVC 规范标准写法是低字节。已由真机代码验证：`code/xu_minimal_get.c`（`uint16_t wValue = (TARGET_CS_ID << 8)`）、`code/uvc_stream_viewer.cpp`（`0x0500 /* CS_ID=0x05 */`）。**工作代码 > 手绘抓包 > 推测**——本会话曾差点按手绘抓包把对的改错，改文档前先核对真机代码。
46. **wIndex 的 Interface 接收者**：接口号在 wIndex **低字节**（0x0001=接口 1）；只有 XU 命令的高字节才是 Unit ID。usb-notes.html 的 wIndex 表和决策流图曾写反，本会话已修正。
47. **枚举主线骨架（4.2~4.10 逐包讲解会反复用到）**：Device Descriptor 读两次（第一次只读 8 字节拿 bMaxPacketSize0）；Config 先读 9 字节头拿 wTotalLength；SET_ADDRESS 之前设备共用地址 0；枚举全走 EP0。
48. **本会话全部改动未提交。** 工作区有 5 个文件未 commit（HANDOFF / 知识库 / 两个 notes / usb-notes.html），在 `redesign/usb-notes-3file` 分支上。

---

## 七、新会话启动步骤

1. **读这份交接文档** — `Read HANDOFF.md`
2. **检查 git 分支** — `git branch`。如果仍在 `redesign/usb-notes-3file` 分支上，说明翻新还未合并。确认是否继续翻新工作还是切回 `main`。
3. **读知识库** — `Read USB-Protocol-Knowledge-Base.md`（★ 第九会话新建、第十会话扩充：~2,810 行，六篇 + 附录，读它就能获得所有上下文）
4. **读学习计划** — `Read usb-protocol-learning-plan.md`（如需了解后续 34 个未完成的知识点）
5. **确定用户意图：**
   - 如果用户说"继续" → 从 Phase 4 的 4.2（阶段 0：设备检测）开始讲，一次一个知识点
   - 如果用户要复习/查阅某主题 → `USB-Protocol-Knowledge-Base.md`（单文件，含 9 张速查表）
   - 如果用户要看理论学习可视化 → 双击 `usb-notes.html`（3 文件架构）
   - 如果用户要看描述符实战 → 双击 `descriptor-viewer.html`
   - 如果用户要看 **摄像头取流+显示** → `code/uvc_stream_viewer.cpp`（libuvc+OpenCV，完整 7 步流程）
   - 如果用户要调 XU → `code/xu_interactive.c`（支持 GET_LEN 后选 GET_CUR 或 SET_CUR）
   - 如果用户要看 **码流类型切换原理** → `USB-Protocol-Knowledge-Base.md` 第六篇 §6.4
   - 如果用户要看新设备上手方法 → `USB-Protocol-Knowledge-Base.md` 第六篇 §6.2
   - 如果用户要看 UVC XU 协议设计 → `notes/uvc-xu-extension-protocol-design.md`
   - 如果用户要看最小读 XU 示例 → `code/xu_minimal_get.c`
   - 如果用户要看海康 TM76 完整代码（裸 libusb 取流） → `code/HIKVISION_TM76_libusb_3.c`
   - 如果用户问 Bus Hound 抓包 → `USB-Protocol-Knowledge-Base.md` 第五篇 FAQ Q8
   - 如果用户问 Interface vs Endpoint → `USB-Protocol-Knowledge-Base.md` §2.3a
   - 如果用户问 **标准 UVC 取流流程** → `USB-Protocol-Knowledge-Base.md` §6.3
   - 如果用户问 **XU 和 UVC 的先后顺序** → `USB-Protocol-Knowledge-Base.md` §6.4（★★★ 必读）
   - 如果用户想继续前端翻新 → `descriptor-viewer.html` 还没翻新，或合并 `redesign/usb-notes-3file` 分支
   - 如果用户说提交/pr/合并 → 先确认在哪个分支，验证后合并到 main
   - 如果用户要编辑知识库 → 直接编辑 `USB-Protocol-Knowledge-Base.md`（4 空格缩进）
   - 如果用户要编辑 HTML → 改内容 `usb-notes.html`，改样式 `usb-notes.css`，改行为 `usb-notes.js`
6. **如果用户不确定到哪了：**
   > "Phase 1-3 已完成 + 4.1 已讲（33/67，49%）。上次会话（第十会话）开讲 Phase 4.1 枚举时间线，并完成 UVC 标准控制问答（PU/XU/请求码全家桶）、wValue 字节序真机验证修正、知识库重编号（第四篇=枚举、第五篇=真实设备、第六篇=XU）。翻新在 `redesign/usb-notes-3file` 分支上，还没合并到 main。准备好了说继续（4.2 阶段 0：设备检测）。"
7. **★ 最重要的几条规则（新会话开始务必重申）：**
   - **XU 必须在 `uvc_open` 之前发**，否则报 LIBUSB_ERROR_IO
   - **`libusb_control_transfer` 有 8 个参数**：bmRT + bReq + wVal + wIdx + data + wLen + timeout（极易漏 bRequest！）
   - **不能信任 UVC 描述符的格式**：帧回调里检测 FF D8 头判断是否 MJPEG
   - **帧回调不能做渲染**：回调只转换数据，主线程渲染，用 pthread_mutex_t 保护
   - **代码在 Windows 编辑，Ubuntu VM 编译运行**，注意文件同步
   - **新会话先读 `USB-Protocol-Knowledge-Base.md`** 获取完整上下文，再读 HANDOFF.md 了解最新进度

---

## 八、快速参考

### SETUP 包 8 字节速查（最常用）

```
Byte 0: bmRequestType    0x21=OUT Class IF   0xA1=IN Class IF   0x01=Standard
Byte 1: bRequest         0x01=SET_CUR        0x81=GET_CUR       0x85=GET_LEN
Byte 2-3: wValue (LE)   高字节=CS_ID, 低字节=0   ← 海康固件惯例；UVC 规范标准写法是低字节=CS
Byte 4-5: wIndex  (LE)  高字节=XU Unit ID, 低字节=接口号  — 换设备只改这里！
Byte 6-7: wLength (LE)  DATA 阶段字节数
```

### 三种 wIndex 填法

| 场景 | wIndex | bmRequestType |
|------|--------|--------------|
| VC XU 命令 | `(XU_ID<<8) \| VC_IF` | 0x21/0xA1 (Class) |
| VS Probe/Commit | `VS_IF` | 0x21/0xA1 (Class) |
| SET_INTERFACE 开流 | `VS_IF` | 0x01 (Standard), bReq=0x0B |

### 控制传输核心

- **三阶段模型**：SETUP(必须ACK) + DATA(可选) + STATUS(方向与DATA相反，零长度包)
- **SETUP 包 8 字节**：bmRequestType(1) + bRequest(1) + wValue(2 LE) + wIndex(2 LE) + wLength(2 LE)
- **bmRequestType 三把钥匙**：D7=方向(IN/OUT), D6-5=字典(Standard/Class/Vendor), D4-0=接收者(Device/Interface/Endpoint)
- **ACK vs STATUS**：ACK=包级"CRC对了"，STATUS=传输级"交易关闭/拒绝"
- **STATUS 是拒绝唯一入口**：SETUP 必须 ACK → 不支持的请求只能在 STATUS 回 STALL
- **批量传输无 STATUS**：ACK 就是事务终点

### 新设备上线检查清单

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU Unit ID)
□                                       bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 IF 填对              → SETUP wIndex 高/低字节
□ 用 CS_ID=0x04 GET_LEN 试通         → 验证通道 + 拿到协议版本
□ 看 bmControls 位图                 → 了解支持哪些 CS_ID
□ 选一个已知 CS_ID 走三阶段          → FUNC_SWITCH → GET_LEN → GET_CUR
```

### Ubuntu 编译运行速查

```bash
# 编译
gcc -o xu_interactive xu_interactive.c -lusb-1.0

# 查描述符
sudo lsusb -v -d 2bdf:0101 > /tmp/cam.txt
grep -n "EXTENSION_UNIT\|bUnitID\|bInterfaceNumber" /tmp/cam.txt

# 运行
sudo ./xu_interactive
```

### 前端文件速查（★ 翻新后）

| 文件 | 行数 | 做什么 |
|------|------|--------|
| `usb-notes.html` | ~2,670 | 纯 HTML 结构，4 空格缩进，不含 `<style>`/`<script>`。含 kp-2-21（码流切换）、kp-4-1（枚举） |
| `usb-notes.css` | 1,153 | 全部样式，10 层分层（Layer 1 变量, Layer 5 组件, Layer 6 可视化…） |
| `usb-notes.js` | 885 | 全部脚本，4 模块（DATA → RENDERERS → INTERACTION → INIT） |
| `usb-notes-old.html` | 3,266 | 翻新前单文件备份 |

**编辑前端时**：
- 改样式 → `usb-notes.css`，找到对应 Layer
- 改行为 → `usb-notes.js`，找到对应 manager
- 改内容 → `usb-notes.html`，现在是纯结构，4 空格缩进
- CSS 变量全在 Layer 1（`:root` 暗色 / `.light` 亮色）
- 不要直接在 HTML 里加 `<style>` 或 `<script>`

### 取流代码速查（★ 第八会话新增）

| 文件 | 语言 | 做什么 | 编译 |
|------|------|--------|------|
| `uvc_stream_viewer.cpp` | C++ | libuvc 取流 + OpenCV 显示 | `g++ -o uvc_stream_viewer uvc_stream_viewer.cpp -luvc -lusb-1.0 $(pkg-config --cflags --libs opencv4)` |
| `xu_interactive.c` | C | 交互式 XU 调试，新增 GET_LEN 后可选 SET_CUR | `gcc -o xu_interactive xu_interactive.c -lusb-1.0` |
| `xu_minimal_get.c` | C | 最简 XU 读示例 | `gcc -o xu_minimal_get xu_minimal_get.c -lusb-1.0` |

**uvc_stream_viewer 完整流程**：
```
① libusb 打开 → detach 内核驱动
② XU FUNC_SWITCH → XU SET_CUR [01 0A] (YUV_ONLY)  ← 必须在 uvc_open 之前
③ usleep(200ms)
④ uvc_open → uvc_get_stream_ctrl_format_size → uvc_start_streaming
⑤ 帧回调：检测 FF D8 → cv::imdecode(MJPEG) 或 uvc_any2rgb(YUYV) → cv::cvtColor(RGB2BGR)
⑥ cv::imshow → cv::waitKey(10) → ESC 退出
```

### 新设备码流切换检查清单（★ 新增）

```
□ lsusb                              → VID:PID
□ sudo lsusb -v -d VID:PID           → bUnitID (XU), bInterfaceNumber (VC IF)
□ 确认 XU_ID 和 VC_IF                → wIndex = (XU_ID<<8) | VC_IF
□ ★ 先发 XU 切码流类型                → FUNC_SWITCH → GET_LEN → SET_CUR [01 0A]
  □ 用独立 libusb 句柄，EP0 不需要 claim
  □ 在 uvc_open 之前！不要之后！
  □ usleep(200ms) 等设备就绪
□ uvc_open → uvc_get_stream_ctrl_format_size（可能需要 raw descriptor walk）
□ 帧回调检测 FF D8 头 → 如果是 JPEG 走 cv::imdecode，否则走 uvc_any2rgb
□ 帧回调只做转换，不渲染。渲染在主线程，加 pthread_mutex_t 保护
```

### descriptor-viewer.html 关键架构

- **未翻新**，仍为单文件（`<style>` + `<script>` 内嵌），2 空格缩进
- 与 usb-notes.html 共享 35 变量 CSS 体系（翻新后 CSS 变量独立，不再共享）
- 三栏对比表 `.cmp-table`：`.row-diff` 黄色差异高亮, `.row-missing` 灰色斜体
- 侧边栏 280px Grid 布局

### MQTT 类比速查

| MQTT | USB |
|------|-----|
| CONNECT 报文 | Device Descriptor |
| Topic 权限声明 | Configuration Descriptor |
| Topic QoS 定义 | Interface Descriptor |
| TCP 连接参数 | Endpoint Descriptor |
| `$SYS/` 系统主题 | EP0（控制端点） |
| PUBLISH body | 流管道（中断/批量/等时） |
| QoS | ACK/NAK/STALL 握手机制 |
| Topic 下挂子 Topic | Interface 下挂 Endpoint |
| 多个 Topic 共用一个 TCP 连接 | 多个 Interface 共用 EP0 |
