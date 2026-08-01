# Real-Device Descriptor Analysis — Design Spec

> 状态：approved | 日期：2026-08-01

## 目标

基于三台真实 USB 设备（两台 HikCamera 热成像 + 一台 2K 前端带音频），写一份独立实战手册 + 一个可视化 HTML 页面，用于剖析 USB 设备描述符的每个字段含义。

## 交付物

| 文件 | 定位 |
|------|------|
| `notes/real-device-descriptor-analysis.md` | 独立实战手册，从零可读 |
| `descriptor-viewer.html` | 交互式对比查看器，单文件离线 |

## 数据源

| 设备 | VID:PID | 类型 | 描述符数据完整度 |
|------|---------|------|------------------|
| 设备1 | 0x2BDF:0x0101 | HikCamera (UVC) | 完整 USB dump + 类专用 |
| 设备2 | 0x2BDF:0x0101 | HikCamera (UVC) 同型号另一台 | 完整 USB dump + Device Qualifier + Other Speed Config |
| 设备3 | 0x2BDF:0x028A | 2K Camera + Audio | 仅 KS 层数据，缺原始 USB 描述符 |

## 笔记结构（5 章 + 3 附录）

### 第 1 章：描述符是什么
- TLV 铁律（bLength + bDescriptorType）
- 描述符获取流程
- ASCII 层级树图
- 三台设备速览表

### 第 2 章：标准描述符逐字节
涵盖 6 种标准描述符：Device(18B) / Config(9B) / IAD(8B) / Interface×2(9B) / Endpoint×2(7B)
每种描述符 4 小节：标准定义表格 → byte-map 色块图 → 三设备对照表 → 关键字段深入

### 第 3 章：类专用描述符机制
- 0x24/0x25 分发原理 + bInterfaceClass 上下文切换
- UVC VC Header 逐字节拆解示例
- UVC 描述符拓扑图
- USB Audio Class 简要提及

### 第 4 章：综合实战
- 4.1 设备1 433 字节描述符链追踪
- 4.2 设备1 vs 设备2 差异分析（Device Qualifier / Other Speed Config）
- 4.3 设备3 从 KS 数据反推描述符结构

### 第 5 章：FAQ

### 附录
- A: 设备1 完整原始 dump
- B: 设备2 完整原始 dump
- C: 设备3 KS 数据

## HTML 页面设计

### 布局
- Grid 布局：侧边栏 280px + 主内容区 1fr
- 复用 usb-notes.html 的 CSS 变量体系（`:root` + `.dark` 双主题）
- LF 换行符，制表符缩进

### 组件

| 组件 | 说明 |
|------|------|
| 侧边栏 | 导航树 + 主题切换 |
| 描述符 byte-map | 复用 `.desc-byte-map` + `.dcell` + `.dc-bg-*` |
| 三栏对比表 | 新组件 `.cmp-table`：字段名/设备1值/设备2值，差异行高亮 |
| 设备列切换 | 三个 tab 切换显示设备1/2/3 的数据列 |
| 折叠字段讲解 | 复用 `<details class="txn-fold">` |
| 描述符层级面包屑 | 新组件，显示当前在描述符树中的位置 |

### 颜色体系
- 标准描述符 byte-map：复用现有 15 个 `.dc-bg-*` 颜色类
- 差异高亮：`--diff-highlight` 变量（浅黄/暗黄）
- 缺失数据标记：`--missing` 变量（灰色斜体）

## 不修改的文件
- `usb-notes.html` — 保持独立，不引用
- `notes/phase3-descriptors.md` — Phase 3 理论笔记独立存在
- `HANDOFF.md` — 交接文档本次不更新

## 实现约束
- HTML 单文件，零外部依赖（CSS 在 `<style>`，JS 在 `<script>`）
- 笔记用 .md 格式，中文撰写
- 颜色变量 `:root` 和 `.dark` 两个块都必须加
- 一次讲一个描述符字段的节奏，保持 MQTT 级别精度
- 设备 3 缺失字段标注为 "无数据" 而非留空
