# Task 5 Report — 27-step Message Sequence Timeline

## Status
**Complete**

## Commit
`39bd94a` — feat: add 27-step message sequence timeline with auto-play

## Changes Made
All modifications to `ble-protocol-manual.html`:

1. **CSS** — Added `.timeline-btn` styles (5 lines) at end of `<style>` block
2. **TIMING_STEPS data** — Array of 27 step objects inserted after `renderAllBitLayouts()` function
3. **renderTimeline(container)** — Full rendering function ~180 lines, with:
   - Phase separators with colored backgrounds (broadcast=blue, connection=green, SMP=purple, encryption=red, ATT=orange, disconnect=gray)
   - Clickable step rows with device labels, direction arrows, layer badges (LL/SMP/ATT)
   - Expandable detail panel showing step summary on click
   - Control buttons: Play, Pause, Reset
   - Speed selector: 0.5x (6000ms), 1x (3000ms), 2x (1500ms)
   - Auto-play highlights steps sequentially and scrolls to each
4. **DOMContentLoaded wiring** — Added timeline initialization at end of existing handler: finds `[data-component="timeline"]` and calls `renderTimeline()`

## Critical Accuracy Checks
- [x] Step #21 (LL_START_ENC_REQ) summary: "Opcode=0x05 (⚠ 明文！) 对方必须先读到才能切换解密引擎"
- [x] Step #22 (LL_START_ENC_RSP) summary: "Opcode=0x06 (⚠ 明文！) 此后全部 AES-CCM 加密"
- [x] All 27 steps present with correct phase grouping (broadcast, connection, SMP pairing, SMP key distribution, link encryption, ATT data, disconnect)
- [x] No existing HTML, CSS, or JS functions modified — only new code added

## Concerns
None. All requirements met.

## Report Path
`D:\CC\personal-lr-notes\CCNotes\BLE\.superpowers\sdd\task-5-report.md`
