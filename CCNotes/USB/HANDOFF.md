# HANDOFF — USB 协议学习会话交接文档

> 更新时间：2026-08-16（第十二会话）
> 主线学习进度：81/88 知识点（92%）— ★ 全主线完成（Phase 7 跳过暂缓），下一步 SDK 动工
> 本会话重点：**Phase 5 连讲收官** + **Phase 6 全篇（应用层裁剪版）** + **Phase 8 全篇（8.1~8.5 + 平台深挖 + hotplug 真机验证）** + SETUP 三类语义修正 + 知识库两次篇章重排 + Phase 7 跳过决策 + 知识总计修正（67→88）
> 上一会话（第十一会话）：Phase 4 收官（4.2~4.12）+ TM5X 大数据流程 + 真机抓包分析

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

### 第十二会话（本次）：Phase 5 收官 + HID 篇（应用层裁剪版）+ Phase 7 跳过决策

**本会话主线**：Phase 5 从 5.1 讲到 5.6 收官（50/67，75%）后进入 Phase 6。期间用户连续追问：wLength 字节数质疑（催生"三类语义"修正版）、SETUP 必 ACK 场景类比（快递回执/法庭传票）、SET_INTERFACE 机制五问、"标准 UVC 能切帧率为什么还要 XU"、"设备可以不按参数发送呀"（解码契约 + 三层强制力 + 撒谎边界）。**HID 篇（6.1~6.7）讲至 6.3 时用户提出"应用层开发有必要学 Item 编码吗"→ 做出裁剪决策**：Report Descriptor 编码按"认字级"执行（6.4/6.5 压缩为速查、6.6 成品解剖图、6.7 类请求精讲）。用户另决定 **Phase 7（协议分析工具）跳过暂缓**（真机抓包已在 4.11/4.11a 完成）。知识库两次篇章重排（新增第五篇标准请求 + 新增第六篇 HID，原实战篇章后移至第七/八篇）。

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 知识库 | `USB-Protocol-Knowledge-Base.md` | **新增第五篇：标准请求与 Setup 包深度解析 §5.1~§5.6**（三类语义修正版 + 11 种请求全集 + GET_STATUS 三种响应 + Feature Selector 全集 + SET_INTERFACE 机制 + 参数速查，含三个深挖 Q&A）；附录新增 **A.10 标准请求参数总表**；**新增第六篇：设备类协议（§6.1~§6.26 全篇）**——HID（Item 编码认字级 + 键盘解剖图 + 六类请求精讲）+ CDC（四件套 byte 表 + SET_LINE_CODING 精讲 + 数据流）+ UVC（VC/VS 链 + 描述符认字级 + bmControls 全集 + Probe/Commit + Payload Header 拼帧）；**两次篇章重排**（原第五篇→第七篇、原第六篇→第八篇，交叉引用全部同步）；**知识总计修正 67→88**；前言/进度更新（5,137 行） |
| HTML | `usb-notes.html` | **Phase 5 占位符替换为 6 张真卡片**（kp-5-1 ~ kp-5-6）；**Phase 6 新增 17 张卡片**（kp-6-1 ~ kp-6-17，HID 7 + CDC 4 + UVC 6，以 desc-byte-map 单元格 + ASCII 结构图为主，减少文字）；Phase 7 标注跳过；CSS 新增 `.phase-note`；侧边栏 Phase 5 6/6 ✓ + Phase 6 26/26 ✓；进度条 86%（4,033 行） |
| 计划 | `usb-protocol-learning-plan.md` | 6.1~6.7 标记完成（应用层裁剪版说明）；**Phase 7 标记 ⏭ 跳过（暂缓）** |
| 代码 | `code/examples/` | **★ 新增 13 份最小可运行示例 + README**（01 枚举 ~ 13 综合骨架；统一头注释五要素；每份独立编译 `gcc -lusb-1.0`，10 加 `-luvc`+opencv、13 加 `-pthread`）；hotplug_demo.c 迁移为 02_hotplug_detect.c |
| HTML | `usb-sdk-examples.html` | **★ 新建**：13 份示例讲解页（单文件零依赖，暗色 IDE 风格，内嵌完整代码 + 逐段「代码↔协议」讲解 + 搜索/复制交互） |
| 文档 | `docs/superpowers/specs/2026-08-16-usb-sdk-examples-design.md` + `plans/2026-08-16-usb-sdk-examples.md` | **新建**：SDK 示例集设计规格与实现计划（SDD 流程执行，17 任务全部通过） |
| 交接 | `HANDOFF.md` | 更新（本会话） |

**本会话建立的深层理解（已存 KB 第五篇）：**

1. **SETUP 8 字节三类语义**：真正随请求换含义的只有 wValue+wIndex 这 4 字节；bmRequestType/bRequest/wLength 的"岗位职责"固定（bRequest 查哪张表由 D6-5 字典决定）
2. **SETUP 必 ACK 的设计哲学**：程序事实 vs 实体态度两层拆开（快递回执/法庭传票双类比）；"拒收视为送达"= SETUP 必 ACK 的法律版
3. **两种 STALL 生命周期**：EP0 一次性（下个 SETUP 自动清除）vs 数据端点粘性（CLEAR_FEATURE 才解冻）——EP0 不能锁死，数据端点锁死是事故报警机制；GET_STATUS 确认 → CLEAR_FEATURE 解冻的故障闭环
4. **Feature Selector 三开关**：ENDPOINT_HALT（两入口一出口）/ DEVICE_REMOTE_WAKEUP（能力 vs 权限分离）/ TEST_MODE（参数藏 wIndex 高字节，唯一禁止 CLEAR）；Interface 是标准请求里最清闲的接收者
5. **SET_INTERFACE 是"选择"不是"创造"**：Alt 索引指向描述符链里预先声明好的端点组合；UVC 主流是同一端点换 wMaxPacketSize（带宽配额），不是换通道；切 Alt 后 toggle 归零
6. **开流≠送流**：Host 中心化铁律——SET_INTERFACE 只让管道就绪，数据从 Host 第一个 IN Token 才开始（水龙头与泵类比）；等时 FIFO 空回零长度包、批量回 NAK，空包合法
7. **Probe/Commit 参数 = 解码契约不是命令**：三层强制力（物理带宽/标准解码器/认证与生态）；撒谎边界 = 哪里有标准验证者（2bdf:0101 的 YUYV→MJPEG 欺诈：格式层撒谎代价是解码器崩，内容层无人验证）；USB 可信度靠"遵守对厂商更有利"的利益结构

**HID 篇建立的深层理解（已存 KB 第六篇）：**

8. **HID Descriptor 是"档案索引卡"**：可变长 `6+3×bNumDescriptors`，类描述符 0x21 寄生在标准链里；wDescriptorLength 让读 Report Descriptor 复用标准 GET_DESCRIPTOR（wValue 高字节 0x22）——"标准请求的顺风车"
9. **Report Descriptor 前缀公式**：`(bTag<<4)|(bType<<2)|bSize`；Global 会传染 / Local 一次性 / Main 落笔；无校验位因为 CRC16 已在包层兜底
10. **Array vs Variable 是键盘与鼠标的本质区别**；8 字节 Boot 报表 = 修饰键位图(1B) + 保留(1B) + 6 键位槽；boot protocol（BIOS 固定格式）→ SET_PROTOCOL(1) 切 report protocol（传真机握手类比）
11. **应用层 HID SDK 全部招式 = 一条中断管道 + 六个类请求**（GET/SET_REPORT 带外查岗、Idle 上报频率、Protocol 格式切换）；"换类协议只换 bmRequestType 字典 + bRequest 编号"
12. **★ 裁剪决策（教学策略）**：知识挂不上用途就裁剪——Report Descriptor 逐位编码是固件作者的知识，应用层开发者学到"认字级"即可；"看不明白"的信号本身可能就是"这个知识点不该现在学"的信号

**CDC/UVC 篇建立的深层理解（已存 KB 第六篇）：**

13. **CDC 四件套**：Header 必须第一个、Union 是"结婚证"（绑控制/数据接口）、ACM D1 位=支持 LINE_CODING 组（没有它 OS 无法设波特率）；功能描述符 0x24 与 UVC CS 共用，靠 bInterfaceClass 分辨
14. **"打开串口"在 USB 上 = SET_LINE_CODING(7B: 波特率+停止位+校验+数据位) + SET_CONTROL_LINE_STATE(DTR|RTS) + 批量传输**；虚拟串口无串口帧结构，Line Coding 只是对端真实串口的配置
15. **UVC 描述符骨架**：VC 链顺序固定（Header→IT→PU→XU→OT），Terminal/Unit ID 是链内引用句柄；bTerminalLink 是 VC/VS 咬合点；guidFormat 前 4 字节 ASCII 认格式（MJPG/YUY2）；2bdf:0101 的 PU bmControls=00 00 实证"专业设备标准控制是空壳，全走 XU"
16. **Payload Header 拼帧**：FID 翻转 + EOF 收帧（libuvc 内部逻辑）；描述符是设备写的广告、帧数据才是实物

**Phase 8（8.1~8.3）建立的深层理解（已存 KB 第九篇）：**

17. **libusb 每个概念都有协议原型**：device/handle = 花名册 vs 话筒；get_device_list = 抄内核花名册（枚举早已完成，零总线流量）；get_device_address = §4.5 领的工牌号；描述符结构体 = §3.1 树的 C 版（interface[i].altsetting[j].endpoint[k]）
18. **libuvc = libusb 传输封装 + UVC 协议引擎**：传输层零新接口；协议层（描述符解析/Probe-Commit/拼帧/事件线程）才是增值——uvc_stream_viewer vs TM76 裸 libusb 之差即其全部
19. **两层回调同一线程**：libuvc 内部回调（每包 ~600 次/秒）拼帧后当场调用用户回调（每帧 30 次/秒）；阻塞 = 事件泵停摆——★ 帧回调规则：uvc_frame_t 仅回调期有效、不阻塞、耗时<<帧间隔、跟不上丢帧
20. **open ≠ 开流（四层动作）**：软件层 open（零流量）→ 内核层 detach/claim（内核记账）→ 协议层 set_configuration/set_interface_alt_setting（SET_INTERFACE 代码版）→ 数据层 transfer
21. **★ claim 机制**：接口级所有权登记（零总线流量）；claim 单位是接口（EP0 不需要 claim 的完整解释）；进程退出 claim 自动释放但 detach 不自动恢复——恢复三招：attach / sysfs bind / usbreset（软件版重插）
22. **★ Windows↔Linux**：接管时机不同（Linux 运行时换班 vs Windows 装驱动定岗，Zadig=换岗不是打电话）；Windows 三大类原生司机齐全（usbvideo/usbser/hidusb），不一定要 Zadig；错误方言不同（PIPE/BUSY ↔ HRESULT）但根因同一；libusb 代码 95% 跨平台（detach/claim 在 Windows 自动空操作）；复合设备 Zadig 按 MI_xx 接口装
23. **★ 信箱模式（三线程协调）**：内部拼帧回调与用户回调同一线程，合并成"收帧的人"；两方 + 一个只能放一帧的信箱；规则一条——信箱满就丢新帧不等待；主线程慢=慢动作不崩（可控丢帧），回调慢=设备/总线被动丢（不可控）；食堂窗口类比；队列吸收抖动不创造产能
24. **三种传输的 libusb 形态**：endpoint 参数 = bEndpointAddress 原样；transferred 输出参数（短包终止）；PIPE=Halted → libusb_clear_halt（5.3 闭环兑现）；等时 = iso_packet_descriptor 包数组 + set_iso_packet_lengths（wMaxPacketSize 变参数）；resubmit 模式 = 自动续订接收机
25. **★ 热插拔（主线终点）**：4.2 的"电平宣告存在"经内核 netlink → libusb 事件 → 事件泵 → 回调，闭环到应用层；回调靠事件泵驱动、ENUMERATE 回放现有设备、LEFT 时设备已死只做收尾；examples/02_hotplug_detect.c 已真机验证——**全主线收官，下一步 SDK 动工**

### 第十一会话：Phase 4 收官 + TM5X 大数据流程 + 真机抓包分析

**本会话主线**：Phase 4 从 4.2 一路讲到 4.12，枚举篇收官（44/67，66%）。副线：解析 TM5X 开发指南的大数据交互流程（新增 §8.9，当时的第六篇）、用 Python 解析 USBPcap 抓包并逐包对照枚举教学（新增 §4.11a，三处真机勘误）、HID/CDC 类概念问答（第三篇补充问答五/六）。另：翻新分支清理（全部合并回 main，此后只在 main 开发）。

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 知识库 | `USB-Protocol-Knowledge-Base.md` | **第四篇补齐 §4.2~§4.12**（枚举 10 步逐包 + 抓包实战 + 真机分析 + 失败排查，Phase 4 完成 12/12）；第八篇新增 **§8.9 TM5X 大数据交互流程**（64/512/65535 三层上限、分包协议、两层确认机制，当时为第六篇，2026-08-16 两次重排后为第八篇）；第三篇新增 **补充问答五/六**（HID/CDC 类家族、USB 虚拟串口机制） |
| HTML | `usb-notes.html` | **Phase 4 占位符替换为 12 张真卡片**（kp-4-2 ~ kp-4-12 + kp-4-11a 真机实战）；侧边栏 12/12 ✓；进度条 66%（3,152 行） |
| 抓包 | `capture.pcapng` | 用户真机抓包：174,032 包 / 225.7s / 6 台设备（含 TM5X 2bdf:028a 完整枚举） |
| 抓包 | `capture-tm5x-2bdf028a.pcapng` | **从全量抓包切出的 TM5X 单设备抓包**（206 包，KB §4.11a 引用） |
| 交接 | `HANDOFF.md` | 更新（本会话） |

**本会话建立的深层理解（已存 KB）：**

1. **设备检测是零字节信息**：电阻位置（D+/D-）宣告速度、电平边沿宣告存在——USB 第一个"信息编码"是硬件位置
2. **SE0 持续时间就是语义**：EOP≈167ns vs 复位≥10ms——不引入新电平，用"按多久"区分（设备响应门槛 2.5μs，双重余量）
3. **8 字节保底铁律**：bMaxPacketSize0 恰在 offset 7（前 8 字节最后一个），8 = 所有设备最小 EP0——规范破解"鸡生蛋"的唯一解法
4. **SET_ADDRESS 换牌时序**：STATUS 用旧地址签收，完成后才切新地址（2ms 内须响应）——固件写错 = 永远枚举不成功（"设定地址失败"）
5. **三层上限模型**：64（总线事务）/ 512（海康协议帧）/ 65535（wLength 字段）各管一层——"65535 是 USB 给的字段上限，512 是机芯给的胃容量"
6. **枚举失败 = 卡点定位**：症状（报错文案/抓包断点）→ 10 步中的某一步 → 故障层；Windows 43=描述符层、设定地址失败=地址层、28=驱动层
7. **真机三勘误**：现代 Windows 一次读 18 字节（不做 8 字节探测）、String 用"先读 4B 头"两步读、SET_ADDRESS 在设备级抓包不可见（hub 层）
8. **TM5X (2bdf:028a) 是三合一复合设备**：UVC（VS 等时，非 Bulk）+ CDC 串口 + 厂商 HID（1023B Report）——SDK 三大目标的合体标本

### 第十会话：Phase 4.1 枚举开讲 + UVC 标准控制问答 + 字节序真机修正

**本会话主线**：主线推进到 Phase 4（枚举）——讲完 4.1 枚举完整时间线（33/67，49%），已存知识库 + HTML。同时密集回答 UVC 标准控制追问，并完成一次重大勘误（wValue 字节序）。（用户明确说过"USB 标准请求用途"那节可以不存——其核心结论已并入第四篇 §4.1 引言。）

**本会话产出：**

| 类型 | 文件 | 变更 |
|------|------|------|
| 知识库 | `USB-Protocol-Knowledge-Base.md` | 新增 §8.8 标准 UVC 控制（PU）完整教程（16 条控制报文全表）；新增 §7.6 bulk-vs-等时小节、§8.5 libuvc 抽象层小节；**新增第四篇：USB 枚举过程（§4.1）**；原第四/五篇重编号为第五/六篇（4.x→5.x、5.x→6.x，交叉引用全部同步）（编号按当时口径，2026-08-16 两次重排后见现行八篇编号） |
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

**文档结构（八篇 + 附录，经第十二会话扩充）：**

| 篇章 | 内容 | 来源 |
|------|------|------|
| 前言 | 67 知识点全景 + 学习路线图 | `usb-protocol-learning-plan.md` |
| 第一篇 | Phase 1 — USB 概览与总线拓扑（5 节） | `phase1-usb-overview.md` |
| 第二篇 | Phase 2 — 通信模型（16 节 + 4 篇补充问答） | `phase2-communication-model.md` |
| 第三篇 | Phase 3 — 描述符体系（11 节 + 4 篇补充问答 + CDC 综合示例） | `phase3-descriptors.md` |
| 第四篇 | USB 枚举过程（4.1~4.12 + 4.11a 真机实战） | 第十~十一会话（主线 Phase 4） |
| 第五篇 | 标准请求与 Setup 包深度解析（5.1~5.6 + 三个深挖 Q&A） | 第十二会话新增（主线 Phase 5） |
| 第六篇 | 设备类协议逐字节解析（6.1~6.26：HID 7 + CDC 7 + UVC 12，应用层裁剪版） | 第十二会话新增（主线 Phase 6，全部完成） |
| 第七篇 | 真实设备描述符实战（7 章 + 10 FAQ） | `real-device-descriptor-analysis.md` |
| 第八篇 | UVC XU 控制与取流实战（9 节 + 7 条踩坑记录） | `uvc-xu-extension-protocol-design.md` + `xu-new-device-setup-guide.md` |
| 第九篇 | libusb 编程衔接（9.1~9.5 全篇 + 深挖：libuvc 关系/两层回调/★帧回调规则/★open-claim/★Windows 对照/★信箱模式/★热插拔） | 第十二会话新增（主线 Phase 8，全部完成） |
| 附录 | 快速参考手册（10 张速查表：SETUP、标准请求参数总表 A.10、wIndex、PID、描述符、MQTT 类比等） | 全部笔记提炼 |

**整理策略：**
- **只整合不删减**：所有笔记内容全部保留，不丢失任何知识点
- **去重归并**：SETUP 包结构在第二篇详述，后续篇章用交叉引用；wIndex 三种填法归并到第二篇，附录保留速查
- **实战紧跟理论**：描述符理论后面直接跟真实设备分析（第七篇），传输理论后面直接跟 XU 踩坑（第八篇）
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
├── USB-Protocol-Knowledge-Base.md                 ← ★ 知识库整合文档（~5,745 行，九篇 + 附录，★ 全主线完成）
├── usb-protocol-learning-plan.md                 ← 完整学习计划（88知识点清单，原"67"已修正，★ 主线全部完成）
├── usb-notes.html                                ← Phase 1-8 理论可视化（4,490 行，含 kp-4-1 ~ kp-4-12 + kp-4-11a + kp-5-1 ~ kp-5-6 + kp-6-1 ~ kp-6-17 + kp-8-1 ~ kp-8-5）
├── usb-sdk-examples.html                         ← ★ 13 份最小示例讲解页（761 行，单文件零依赖，配 code/examples/）
├── usb-notes.css                                 ← 10 层分层样式（暗色默认 IDE 风格）
├── usb-notes.js                                  ← 4 模块脚本（数据/渲染/交互/初始化）
├── usb-notes-old.html                            ← 旧版备份（翻新前单文件版本）
├── descriptor-viewer.html                        ← 三设备描述符实战对比
├── usb设备1的描述符.txt                            ← 设备1 原始 dump
├── usb设备2的描述符.txt                            ← 设备2 原始 dump
├── usb设备3的描述符.txt                            ← 设备3 原始 dump（无 Extension Unit）
├── capture.pcapng                                ← 全量真机抓包（174K 包，6 设备）
├── capture-tm5x-2bdf028a.pcapng                  ← ★ TM5X 单设备抓包（206 包，KB §4.11a 引用）
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
│   └── hotplug_demo.c                            ← （已迁移至 examples/02_hotplug_detect.c）
│   └── examples/                                 ← ★ 13 份最小可运行示例 + README（第十二会话，配 usb-sdk-examples.html）
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

### ★ 主线全部完成（81/88，92%），项目进入新阶段：SDK 动工

**协议理论学习全部结束。** Phase 1-8 完成（Phase 7 跳过暂缓，真机抓包已在 4.11/4.11a 完成）。第十二会话最后实测验证了 examples/02_hotplug_detect.c（Ubuntu VM 上 ENUMERATE 刷屏 + 插拔实时打印，用户确认验证成功）。

**下一步（项目层面，不再是"讲知识点"）**：用户最初的目标——**构建 USB SDK（UVC 摄像头 + CDC 串口 + HID 设备）**。弹药已齐备：

| SDK 模块 | 理论弹药 | 代码基础 |
|---------|---------|---------|
| UVC 摄像头 | XU 控制（第八篇）+ Probe/Commit + Payload Header（第六篇） | uvc_stream_viewer.cpp / libuvc 或裸 libusb（TM76 改写） |
| CDC 串口 | SET_LINE_CODING 7 字节 + 批量管道（第六篇） | 裸 libusb（类请求 + bulk） |
| HID | 中断报表 + 六类请求（第六篇） | 裸 libusb（interrupt + 类请求） |
| 地基 | 热插拔回调 + 事件泵 + 信箱模式（第九篇） | examples/02_hotplug_detect.c 骨架 |

**可能的动工方式**（用户说想做什么就做什么）：① 先写 SDK 骨架（热插拔 + 设备发现 + 统一打开接口）；② 按 UVC→CDC→HID 顺序逐个模块；③ 把 TM76 裸 libusb 拼帧逻辑改写面向 2bdf:0101。**动工前建议先 brainstorming 定 SDK 的接口设计和模块划分**（第七会话的完整流程：brainstorming → spec → plan → implement）。

### 副线一：UVC 取流工具已完成基础

`uvc_stream_viewer.cpp` 可以正常工作——打开摄像头、切码流、取流、OpenCV 实时显示。输出为 120x160 MJPEG（经 cv::imdecode 解码后正常显示）。

**可以改进的方向：**
- 支持命令行选择分辨率（目前自动选第一个可用的，120x160）
- 支持录制（`cv::VideoWriter` 写 .avi）
- 支持截图（空格键保存当前帧）
- 支持伪彩热切换（取流中发 XU CS_ID=0x02 换调色板，~200ms 生效）
- F 键全屏切换（代码骨架已留，未实现）
- 多设备支持（当前只取第一台或指定 VID:PID）

### 副线二：usb-notes.html 翻新已完成（已合并到 main）

翻新分支 `redesign/usb-notes-3file` 已合并回 main，本地分支已删除。**后续所有开发直接在主分支上进行，不再使用功能分支。**

备份文件 `usb-notes-old.html` 已无引用，可随时删除。

### 未来可能的前端优化

- `descriptor-viewer.html` 同样做 3 文件翻新
- 时间线详情面板加键盘 Escape 关闭的 focus 自动移回
- 移动端 overlay 克隆的搜索框目前是装饰（未绑定 JS）
- `color-mix()` 在极旧浏览器不支持，可视需要加 fallback

### 用户可能要求的下一步

- **主线**：理论学习已全部完成。用户如果说"继续" → 进入 **SDK 动工**（先 brainstorming 定接口设计，再 spec → plan → implement）
- **知识库**：在 `USB-Protocol-Knowledge-Base.md` 中补充后续学习内容（Phase 4+）
- **取流工具**：加录制/截图/伪彩切换/全屏
- **XU 探索**：`xu_interactive.c` 加 SET_CUR 暴力扫描未知 CS_ID
- **裸 libusb 取流**：把 TM76 的 `uvc_read_one_frame()` 逻辑改写为面向 2bdf:0101
- **前端翻新**：翻新 `descriptor-viewer.html`
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
19. **零字节速度宣告**：D+ 上拉=FS/HS、D- 上拉=LS；检测阶段只分 LS/非 LS，HS 身份等 Chirp；SE0 持续时间就是语义（EOP≈167ns vs 复位≥10ms） — ★ 第十一会话
20. **8 字节保底 + 短包规则**：bMaxPacketSize0 卡在 offset 7，破解"鸡生蛋"；短包=传输结束，枚举多次兜底 — ★ 第十一会话
21. **STATUS 签完才换牌**：Set_Address 的新地址在 STATUS 完成后生效（2ms 内须响应）——写错就是"设定地址失败" — ★ 第十一会话
22. **三层上限 64/512/65535**：总线事务 / 海康协议帧 / wLength 字段，各管一层；TM5X 大数据走"每帧一个 SETUP"的分包链（§8.9） — ★ 第十一会话
23. **枚举失败卡点定位法**：症状→10 步中的某一步→故障层；Windows 43=描述符层、设定地址失败=地址层、28=驱动层 — ★ 第十一会话
24. **TM5X 2bdf:028a 三合一**（UVC 等时 + CDC 串口 + HID）；真机三勘误（Windows 一次读 18、String 两步读、SET_ADDRESS 设备级抓包不可见） — ★ 第十一会话
25. **SETUP 8 字节三类语义**：只有 wValue+wIndex（4 字节）随请求换含义；bmRequestType/bRequest/wLength 岗位职责固定；bRequest 查哪张表由 D6-5 字典决定（0x01：Standard=CLEAR_FEATURE，UVC=SET_CUR） — ★ 第十二会话
26. **SETUP 必 ACK = 程序事实 vs 实体态度两层拆开**：快递回执/法庭传票双类比；"拒收视为送达"= SETUP 必 ACK 的法律版；抓包见 SETUP 后非 ACK 即固件违规 — ★ 第十二会话
27. **两种 STALL 生命周期**：EP0 一次性（下个 SETUP 自动清）vs 数据端点粘性（CLEAR_FEATURE 才解冻）；故障闭环 = 设备 STALL 报警 → GET_STATUS 确认 D0=1 → CLEAR_FEATURE 解冻；libusb 里就是 `libusb_clear_halt()` — ★ 第十二会话
28. **Feature Selector 三开关**：ENDPOINT_HALT（两入口一出口）/ DEVICE_REMOTE_WAKEUP（能力 vs 权限分离，静音开关在主持人手里）/ TEST_MODE（参数藏 wIndex 高字节，唯一禁 CLEAR）；Interface 是标准请求里最清闲的接收者 — ★ 第十二会话
29. **SET_INTERFACE 是"选择"不是"创造"**：Alt 索引指向描述符链里预先声明好的端点组合；UVC 主流是同一端点换 wMaxPacketSize（带宽配额）不换通道；切 Alt 后 toggle 归零；等时→批量协议可以但现实几乎不（传输类型由数据语义决定） — ★ 第十二会话
30. **开流≠送流**：Host 中心化——SET_INTERFACE 只让管道就绪，数据从 Host 第一个 IN Token 才开始（水龙头与泵）；等时 FIFO 空回零长度包、批量回 NAK，空包合法；"没 XU 就没流"不成立（默认码流类型 8/6 的花屏反证） — ★ 第十二会话
31. **Probe/Commit 参数 = 解码契约不是命令**：三层强制力（物理带宽/标准解码器/认证生态）；撒谎边界 = 哪里有标准验证者（2bdf:0101 报 YUYV 送 MJPEG）；XU 内容层没有标准验证者所以是灰色地带；USB 可信度靠"遵守对厂商更有利"的利益结构 — ★ 第十二会话
32. **HID Descriptor 是"档案索引卡"**：可变长 `6+3×bNumDescriptors`；类描述符 0x21 寄生在标准链里（UVC 0x24/0x25 同套路）；wDescriptorLength 让读 Report Descriptor 复用标准 GET_DESCRIPTOR（wValue 高字节 0x22）——"标准请求的顺风车"；Report Descriptor（说明书）≠ Report（数据） — ★ 第十二会话
33. **Report Descriptor 前缀公式**：`(bTag<<4)|(bType<<2)|bSize`；Global 会传染 / Local 一次性 / Main 落笔；无校验位因为 CRC16 已在包层兜底 — ★ 第十二会话
34. **Array vs Variable 是键盘与鼠标的本质区别**；8 字节 Boot 报表 = 修饰键位图(1B) + 保留(1B) + 6 键位槽；boot protocol（BIOS 固定格式）→ SET_PROTOCOL(1) 切 report protocol（传真机握手类比） — ★ 第十二会话
35. **应用层 HID SDK 全部招式 = 一条中断管道 + 六个类请求**（GET/SET_REPORT 带外查岗、Idle 上报频率、Protocol 格式切换）；"换类协议只换 bmRequestType 字典 + bRequest 编号" — ★ 第十二会话
36. **★ 裁剪决策（教学策略，重要！）**：知识挂不上用途就裁剪——Report Descriptor 逐位编码是固件作者的知识，应用层开发者学到"认字级"即可。**用户说"看不明白/有必要学吗"的信号本身可能就是"这个知识点不该现在学"**——此时应当给分层建议（写设备 vs 消费设备）而不是硬推。Phase 7 已按同样逻辑跳过 — ★ 第十二会话

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

44. **★★★ 知识库篇章编号已两次重排，现行八篇为最终布局！** 第六篇=设备类协议（HID 篇，5.x 主干），第七篇=真实设备描述符实战（原第五/六篇，6.x→7.x），第八篇=UVC XU 控制与取流实战（原第六/七篇，7.x→8.x）。**不要再写旧编号**——"第七篇 §7.9 TM5X"现在应写"第八篇 §8.9"，"第六篇 FAQ Q8"现在应写"第七篇 FAQ Q8"。**后续 CDC（6.8+）/UVC（6.15+）内容直接补进第六篇，不再重排**；Phase 8（libusb）将来新增为第九篇，加在第八篇之后即可。
45. **★★★ wValue 字节序（海康惯例 vs UVC 规范）**：2bdf:0101 固件把 CS_ID 放在 wValue **高字节**（`CS_ID << 8`，如 CS_ID=0x05 → wValue=0x0500）；UVC 规范标准写法是低字节。已由真机代码验证：`code/xu_minimal_get.c`（`uint16_t wValue = (TARGET_CS_ID << 8)`）、`code/uvc_stream_viewer.cpp`（`0x0500 /* CS_ID=0x05 */`）。**工作代码 > 手绘抓包 > 推测**——本会话曾差点按手绘抓包把对的改错，改文档前先核对真机代码。
46. **wIndex 的 Interface 接收者**：接口号在 wIndex **低字节**（0x0001=接口 1）；只有 XU 命令的高字节才是 Unit ID。usb-notes.html 的 wIndex 表和决策流图曾写反，本会话已修正。
47. **枚举主线骨架（4.2~4.10 逐包讲解会反复用到）**：Device Descriptor 读两次（第一次只读 8 字节拿 bMaxPacketSize0）；Config 先读 9 字节头拿 wTotalLength；SET_ADDRESS 之前设备共用地址 0；枚举全走 EP0。

---

## 七、新会话启动步骤

1. **读这份交接文档** — `Read HANDOFF.md`
2. **确认在 main 分支** — `git branch`。翻新分支已合并删除，后续全部工作在 main 上进行。
3. **读知识库** — `Read USB-Protocol-Knowledge-Base.md`（★ 第九会话新建、第十二会话扩充：~4,803 行，八篇 + 附录，读它就能获得所有上下文）
4. **读学习计划** — `Read usb-protocol-learning-plan.md`（如需了解后续 34 个未完成的知识点）
5. **确定用户意图：**
   - 如果用户说"继续" → 进入 SDK 动工阶段（brainstorming 先行，不再按"一次一个知识点"讲课）
   - 如果用户要复习/查阅某主题 → `USB-Protocol-Knowledge-Base.md`（单文件，含 10 张速查表）
   - 如果用户要看理论学习可视化 → 双击 `usb-notes.html`（3 文件架构）
   - 如果用户要看描述符实战 → 双击 `descriptor-viewer.html`
   - 如果用户要看 **摄像头取流+显示** → `code/uvc_stream_viewer.cpp`（libuvc+OpenCV，完整 7 步流程）
   - 如果用户要查**最小代码示例** → 双击 `usb-sdk-examples.html`（13 份示例讲解页）/ `code/examples/`（可编译源码）
   - 如果用户要调 XU → `code/xu_interactive.c`（支持 GET_LEN 后选 GET_CUR 或 SET_CUR）
   - 如果用户要看 **标准请求参数速查** → `USB-Protocol-Knowledge-Base.md` 第五篇 §5.6 / 附录 A.10
   - 如果用户要看 **HID 篇** → `USB-Protocol-Knowledge-Base.md` 第六篇 §6.1~§6.7（应用层裁剪版）
   - 如果用户要看 **码流类型切换原理** → `USB-Protocol-Knowledge-Base.md` 第八篇 §8.4
   - 如果用户要看新设备上手方法 → `USB-Protocol-Knowledge-Base.md` 第八篇 §8.2
   - 如果用户要看 UVC XU 协议设计 → `notes/uvc-xu-extension-protocol-design.md`
   - 如果用户要看最小读 XU 示例 → `code/xu_minimal_get.c`
   - 如果用户要看海康 TM76 完整代码（裸 libusb 取流） → `code/HIKVISION_TM76_libusb_3.c`
   - 如果用户问 Bus Hound 抓包 → `USB-Protocol-Knowledge-Base.md` 第七篇 FAQ Q8
   - 如果用户问 Interface vs Endpoint → `USB-Protocol-Knowledge-Base.md` §2.3a
   - 如果用户问 **标准 UVC 取流流程** → `USB-Protocol-Knowledge-Base.md` §8.3
   - 如果用户问 **XU 和 UVC 的先后顺序** → `USB-Protocol-Knowledge-Base.md` §8.4（★★★ 必读）
   - 如果用户想继续前端翻新 → `descriptor-viewer.html` 还没翻新
   - 如果用户说提交/推送 → 直接在 main 分支上操作（不再使用功能分支）
   - 如果用户要编辑知识库 → 直接编辑 `USB-Protocol-Knowledge-Base.md`（4 空格缩进）
   - 如果用户要编辑 HTML → 改内容 `usb-notes.html`，改样式 `usb-notes.css`，改行为 `usb-notes.js`
6. **如果用户不确定到哪了：**
   > "★ 主线全部完成（81/88，92%；Phase 7 跳过暂缓）。第十二会话完成 Phase 5 收官 + Phase 6 全篇（应用层裁剪版）+ Phase 8 全篇（含信箱模式、热插拔真机验证 examples/02_hotplug_detect.c）+ 知识库两次重排（现行九篇）+ 知识总计修正 67→88。协议理论学习结束，下一步进入 SDK 动工（brainstorming 先行）。"
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

### 枚举失败速查（Windows 报错 → 卡点）

| 报错文案 | 代码 | 卡在哪一步 |
|---------|:---:|-----------|
| 设备描述符请求失败 | 43 | 描述符层（bMaxPacketSize0 错 / CRC 错） |
| 设定地址失败 | — | 地址层（STATUS 后不响应新地址） |
| 未安装驱动程序 | 28 | 驱动层（VID:PID 无匹配） |
| 设备无法启动 | 10 | 驱动加载崩溃 |
| 端口上的电涌 | — | 电气层（供电过流） |

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
