# Task 6 Review: 5-in-1 REF_TABLES with Tab Switching and Search

**Commit:** 006d261
**Review Date:** 2026-07-19
**Reviewer:** Automated Review

---

## Verdict 1: Spec Compliance -- MINOR ISSUES

| Check | Result | Detail |
|-------|--------|--------|
| Tab bar with 5 buttons that switch tables | PASS | 5 tabs (LL Control, SMP, ATT, CID, AD Type) created from `REF_TABLES` array; click handler switches `currentId` and re-renders |
| Search input filters in real-time | PASS | `input` event listener calls `renderTable` with current filter value; filters across all columns via `row.some()` |
| Correct column headers for each table | PASS | Headers match data schema: ll-control (4 cols), smp (4 cols), att (4 cols), cid (3 cols), ad-type (4 cols) |
| Search clears on tab switch | **FAIL** (Minor) | `filterText` is NOT reset when switching tabs. The tab click handler calls `renderTable(t, filterText)` with the stale search term, so the filter persists across tables. This is unexpected UX -- user searches "ENC" on LL table, switches to SMP, and SMP table is also filtered by "ENC". |

**Recommendation:** Reset `filterText = ''` and `searchInput.value = ''` inside the tab click handler before calling `renderTable`.

---

## Verdict 2: Code Quality -- MINOR ISSUES

| Check | Result | Detail |
|-------|--------|--------|
| Critical data accuracy (4 mandatory items) | PASS | All verified: (1) LL_START_ENC_REQ 0x05 has "⚠ 本身明文！", (2) LL_START_ENC_RSP 0x06 has "⚠ 本身明文！", (3) SMP Confirm 0x03 mentions both Legacy AES-CMAC and SC Numeric Comparison, (4) AD Type 0x01 includes "必须排第一个" with bit flag descriptions |
| Row counts (20+14+26+4+8) | PASS | ll-control: 20 rows (0x00-0x0E, 0x14-0x17, 0x19); smp: 14 rows (0x01-0x0E); att: 26 rows; cid: 4 rows; ad-type: 8 rows |
| Opcode/data accuracy | PASS | All opcode values and descriptions verified against BLE Core Specification v5.x. New descriptions are more detailed and accurate than replaced static tables (e.g., separating combined opcodes like 0x08/09 into individual rows) |
| Search filtering across all columns | PASS | `row.some()` iterates all cells. Minor note: operates on raw HTML (e.g., `<strong>0x01</strong>`), so searching for tag names like "strong" would produce false matches -- low real-world impact |
| Dead CSS class | **Minor** | `.ref-table tr.ref-hidden { display:none; }` is defined (line 241) but never used. The JS rebuilds `innerHTML` entirely rather than toggling visibility classes. |
| Redundant filter condition | **Minor** | The match logic includes `(table.id === 'll-control' && row[0].toLowerCase().indexOf(filter) !== -1)` which is redundant because `row.some()` already checks `row[0]`. Harmless but unnecessary. |
| No empty state | **Minor** | When search yields zero results, the table body is empty and the count shows "0 / X 条". No user-facing message like "无匹配结果" is displayed. |
| No external resources | PASS | Zero external dependencies; no localStorage usage; pure CSS + vanilla JS. |

**Recommendations:**
1. Remove unused `.ref-table tr.ref-hidden` CSS rule (or implement show/hide row toggling instead of innerHTML rebuild).
2. Remove the redundant `table.id === 'll-control'` guard in the filter logic.
3. Add an empty-state message when filtered results are zero.

---

## Summary

The implementation is functionally correct and passes all critical accuracy checks. All four mandatory items (START_ENC_REQ/RSP warnings, SMP Confirm dual meaning, AD Type 0x01 ordering requirement) are present with correct content. Row counts match spec. Tab switching and real-time search work. The two minor issues are: (1) search filter does not clear on tab switch (UX consistency), and (2) dead CSS / minor code hygiene items. No critical or important issues were found.
