# USB 协议知识库整理 — 设计规格

> 日期：2026-08-02
> 目标：将分散在 7 个 .md 文件和 1 个 HTML 文件中的所有 USB 知识点，整理为一份结构清晰的 Markdown 单文件

## 设计决策

- **格式**：Markdown 单文件
- **组织**：按学习阶段（Phase 1→5），实战案例穿插在对应理论篇章中
- **原则**：只整合不删减、去重归并、层次分明、保持原始深度

## 文档结构

```
前言：学习路线图
第一篇：USB 概览与总线拓扑 (Phase 1, 5 节)
第二篇：USB 通信模型 (Phase 2, 16 节 + 7 篇补充问答)
第三篇：USB 描述符体系 (Phase 3, 11 节 + 4 篇补充问答 + CDC 综合示例)
第四篇：真实设备描述符实战 (5 章 + 10 FAQ)
第五篇：UVC XU 控制与取流实战 (XU 协议 + 上手指南 + 取流流程 + 码流切换 + 踩坑记录)
附录：快速参考手册 (9 张速查表)
```

## 源文件映射

| 源文件 | 目标篇章 |
|--------|---------|
| phase1-usb-overview.md | 第一篇 |
| phase2-communication-model.md | 第二篇 |
| phase3-descriptors.md | 第三篇 |
| real-device-descriptor-analysis.md | 第四篇 |
| uvc-xu-extension-protocol-design.md | 第五篇 §XU 协议 |
| xu-new-device-setup-guide.md | 第五篇 §上手指南+取流+码流切换 |
| usb-protocol-learning-plan.md | 前言 |
| usb-notes.html (kp-2-21 等) | 对应篇章 |

## 去重策略

- SETUP 包结构：在第二篇 2.10 详述，后续篇章用交叉引用
- wIndex 三种填法：第二篇和第五篇各出现，归并到第二篇，附录保留速查
- 七条踩坑记录：集中在第五篇末尾
- MQTT 类比：分散在各篇章保留，附录汇总速查表
