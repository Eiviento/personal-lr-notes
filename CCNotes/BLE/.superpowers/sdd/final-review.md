# Final Whole-Branch Review: BLE Protocol Interactive HTML Manual

**Review Date:** 2026-07-19
**Branch Range:** 59d5ce6..164542e (9 commits)
**Target File:** `D:\CC\personal-lr-notes\CCNotes\BLE\ble-protocol-manual.html`
**Source Manual:** `D:\CC\personal-lr-notes\CCNotes\BLE\附录-BLE协议交互报文完整手册.md`

---

## Overall Verdict: **Ready to ship**

All 10 spec requirements are met, all 8 critical accuracy constraints from HANDOFF.md pass, and the remaining minor issues are cosmetic/documentation-level with no functional impact. Single file, no external dependencies, no localStorage, correct BLE protocol data.

---

## Part A: Spec Coverage (from Design Spec)

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Single file HTML, no external resources | **PASS** | No CDN/HTTP imports, no external fonts/images; CSS+JS inline in `ble-protocol-manual.html` |
| 2 | 10 chapters + appendix all present | **PASS** | 11 `<section>` elements: sec-overview through sec-timeline, all with correct IDs |
| 3 | Left sidebar tree navigation with scroll tracking | **PASS** | `TREE` data (44 anchors), `renderTree()`, `scrollToSection()`, `IntersectionObserver` with `rootMargin: '-20% 0px -70% 0px'` |
| 4 | Bit layout component (color bar + detail table, hover linkage) | **PASS** | 5 BIT_LAYOUTS defined (air-frame, adv-pdu-header, data-pdu-header, connect-ind-payload, ltv-structure). Bidirectional hover linkage via `is-highlighted` class |
| 5 | 27-step message timeline (click expand + auto-play) | **PASS** | 27 TIMING_STEPS (id 1-27), `renderTimeline()` with phase separators, click-to-detail, play/pause/reset controls, 3-speed selector (0.5x/1x/2x) |
| 6 | 5-in-1 reference tables (tab switch + search filter) | **PASS** | 5 REF_TABLES (LL Control, SMP, ATT, CID, AD Type), `renderRefTables()` with tab switching and real-time search filtering |
| 7 | CSS flowcharts (protocol stack, pairing phases, auth paths, encryption range) | **PASS** | Four flowchart components: `renderProtocolStack()` (7-layer flexbox), `renderFlowchart('pairing-phases')` (4-phase collapsible nodes), `renderAuthPaths()` (4-column branch grid), `renderEncRange()` (plaintext/ciphertext color bar with legend) |
| 8 | Dark/light theme toggle (follows prefers-color-scheme, NO localStorage) | **PASS** | Theme init reads `prefers-color-scheme` only, no localStorage calls. `matchMedia('change')` listener updates on OS theme change |
| 9 | Responsive (900px sidebar drawer, 600px table scroll) | **PASS** | `@media(max-width:900px)`: sidebar transforms to fixed drawer with hamburger + scrim. `@media(max-width:600px)`: table `overflow-x:auto`, bit-layout bar height 40px, smaller font |
| 10 | Global search with highlight | **PASS** | `initGlobalSearch()` debounced (200ms), highlights matches with `.search-highlight` class, `Escape` clears, scrolls to first match |

**Spec Coverage Score: 10/10**

---

## Part B: Critical Accuracy (from HANDOFF.md — Task 9)

| # | Constraint | Source Manual Check | Status |
|---|-----------|-------------------|--------|
| 1 | PDU Type is **4 bit** (not 2 bit) — check adv-pdu-header | Source manual §3.1: `PDU Type │ 4 bit │ [3:0]`. HTML line 1964: `bits: 4`. Table line 486: "4 bit". ASCII line 476: "4 bit" | **PASS** |
| 2 | 广播 PDU Header Length is **8 bit** — check adv-pdu-header | Source manual §3.1: `Length │ 8 bit │ [15:8]`. HTML line 1959: `bits: 8`. Table line 491: "8 bit". ASCII line 475: "8 bit" | **PASS** |
| 3 | LL_START_ENC_REQ (step 21) marked **明文** | Source manual §9.2: "明文！". HTML TIMING_STEPS[20] (step 21) line 2158: `"Opcode=0x05 (⚠ 明文！)..."` | **PASS** |
| 4 | LL_START_ENC_RSP (step 22) marked **明文** | Source manual §9.2: "明文！". HTML TIMING_STEPS[21] (step 22) line 2159: `"Opcode=0x06 (⚠ 明文！)..."` | **PASS** |
| 5 | SMP Confirm (0x03) has **BOTH Legacy and SC meanings** in ref tables | Source manual §7.1: 0x03 described as Legacy pairing confirm; §7.5 Path A: SC Numeric Comparison uses 0x03. HTML REF_TABLES[1].rows[2] line 2379: `"Legacy: 配对确认值...；SC: Numeric Comparison 用户肉眼比对后发送"` | **PASS** |
| 6 | CONNECT_IND (step 4) **not followed by ACK** | Source manual §3.4: "从设备不回复 ACK——真正的确认是第一次连接事件..." HTML line 677 matches. Timeline steps 4->5 transition from broadcast to connection phase with no ACK between | **PASS** |
| 7 | Access Address is **frame header** not PDU field (check air-frame layout) | Source manual §2.1: Access Address sits between Preamble and PDU in the air frame. HTML `BIT_LAYOUTS['air-frame']` lines 1941-1952 places AA as separate field before LL Header. ASCII diagram line 419-424 shows correct layout | **PASS** |
| 8 | CCCD disconnect auto-reset mentioned somewhere in chapter 8 | Source manual §8.3: "CCCD 值 0x0000 = 关闭（默认值，连接断开时自动重置为此值）". HTML table line 1417: `"关闭（默认值，连接断开时自动重置为此值）"`. Callout line 1423: `"重连后必须重新写 CCCD——连接断开时设备端 CCCD 自动归零。"` | **PASS** |

**Critical Accuracy Score: 8/8**

---

## Part C: Accumulated Minor Issues

| # | Issue | Source | Current Status | Detail |
|---|-------|--------|---------------|--------|
| 1 | Badge colors used hex instead of CSS vars | Task 5 review | **FIXED** in Task 8 | Badge colors now use CSS vars: `var(--blue)`, `var(--purple)`, `var(--orange)` (HTML line 2232) |
| 2 | Search doesn't clear on tab switch | Task 6 review | **REMAINS** (Minor) | Tab click handler (line 2489-2494) does not reset `filterText` or `searchInput.value` when switching tabs. The search term persists across tables, which is unexpected UX |
| 3 | No "no results" empty state message | Task 6 review | **REMAINS** (Minor) | When search yields zero results, `renderTable()` shows an empty `<tbody>` and count "0 / X 条". No user-facing placeholder like "无匹配结果" displayed |
| 4 | App layer in protocol stack links to sec-att vs sec-gatt | Task 7 review | **NOT AN ISSUE** | The `sec-att` section covers both ATT and GATT (title: "八、ATT / GATT — 属性协议"). Linking to `sec-att` is correct. |

**Accumulated Issues: 2 remain (both Minor)**

---

## New Issues Found

### Minor — Protocol stack uses hardcoded hex colors for two layers

- **Location:** `renderProtocolStack()` function, HTML lines 2536 and 2542
- **Detail:** The "应用层" layer uses `color: '#6366F1'` and "物理层" layer uses `color: '#EC4899'`. These are hardcoded hex values rather than CSS custom properties, so they won't adapt to the dark theme. All other stack layers use CSS vars (`var(--purple)`, `var(--cyan)`, etc.).
- **Impact:** These two layers appear with the same bright indigo/pink in both light and dark themes, while other layers correctly shift colors. Visual inconsistency only.
- **Recommendation:** Either define new CSS vars for these colors (e.g., `--indigo`/`--pink`) with dark-mode overrides, or choose colors from the existing CSS var palette.

### Minor — Unused CSS rule `.ref-table tr.ref-hidden`

- **Location:** HTML line 244
- **Detail:** The CSS rule `.ref-table tr.ref-hidden { display:none; }` is defined but never applied by any JS code. The `renderRefTables()` function rebuilds the table HTML from scratch on every filter change instead of toggling visibility classes on existing rows.
- **Impact:** Dead CSS (~50 bytes). No functional issue.
- **Recommendation:** Either remove the unused rule, or refactor `renderTable()` to toggle row visibility (which would preserve DOM event listeners if any were attached).

### Minor — Auto-play detail panel omits direction information

- **Location:** `highlightStep()` function, HTML line 2293
- **Detail:** The click-handler's detail panel (line 2260-2263) shows `方向: 设备X → 设备Y`, but the auto-play `highlightStep()` function (line 2293-2296) omits this line. The detail panel content is inconsistent between click-triggered and auto-play-triggered views.
- **Impact:** Minor UX inconsistency during auto-play.

---

## Summary

| Category | Result |
|----------|--------|
| **Spec Coverage** | 10/10 — All requirements met |
| **Critical Accuracy** | 8/8 — All HANDOFF.md constraints pass |
| **Accumulated Minor Issues** | 2 remain (search clear on tab switch, no empty state) |
| **New Issues** | 3 Minor (hex colors in stack, unused CSS, auto-play detail inconsistency) |
| **Overall Verdict** | **Ready to ship** |

The file is a complete, self-contained BLE protocol teaching manual. All critical data accuracy constraints are verified against the source markdown. No functional bugs, no external dependencies, no localStorage violations. The remaining issues are cosmetic or minor UX polish items.
