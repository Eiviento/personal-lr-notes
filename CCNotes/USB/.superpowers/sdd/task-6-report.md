# Task 6 Report: Rewrite usb-notes.html (3-file redesign)

## Status: DONE_WITH_CONCERNS

## Files

- Created: `D:\CC\personal-lr-notes\CCNotes\USB\usb-notes.html` (2323 lines, 165,555 bytes, UTF-8 no BOM, LF)
- Backup: `D:\CC\personal-lr-notes\CCNotes\USB\usb-notes-old.html` (3266 lines, 194,993 bytes — byte-identical copy of the original)

## Card count

- Old: **38** (`grep -c 'class="card" id="kp-'` on old file)
- New: **38** — identical. All 38 card ids present exactly once, in order:
  Phase 1: kp-1-1..1-5 → Phase 2: kp-2-1..2-19, kp-2-20, kp-dev-tips → Phase 3: kp-3-1..3-11

## Line count

- Old: 3266 → New: 2323 (old inline `<style>` ~410 lines and inline `<script>` ~660 lines removed; CSS/JS now external per the 3-file architecture)

## Content fidelity verification

- Programmatic per-card check: every inner line of every card in the new file == old-file line with a uniform +4-space indent (0 mismatches; blank lines preserved as blank). Pre-block inner text also got the uniform +4 shift — relative ASCII-art alignment is byte-preserved, rendering identical.
- Structural element counts (main region, old body vs new main): `<table>` 111→112, `<pre>` 69→70, `<svg>` 8→8, `<details>` 23→23. The +1 table / +1 pre are exactly the content restored into kp-2-19 (see repair note).
- Old inline JS (PACKET_DATA, FRAME_TRANSACTIONS, renderers, theme) fully removed from HTML — now in `usb-notes.js`; `usb-notes.js` passes `node --check`.
- Anti-flash script verified as valid JS; localStorage key (`usb-notes-theme`) matches ThemeManager.

## ID verification (all present exactly once)

- Cards: all 38 `id="kp-*"` — one each
- Shell: `#main-content`, `#sidebarSearch`, `#mobileNavBtn`, `#sidebarOverlay`, `#sidebarOverlayContent`, `#themeToggle`, `#scrollTopBtn`
- Timeline/detail: `#frameTimeline` (inside kp-2-18), `#txnDetail`, `#txnDetailTitle`, `#txnDetailBody`, `#txnDetailClose` (txnDetail at bottom of `<main>` per brief Step 5)
- Packet containers: `#pkt-token`, `#pkt-sof`, `#pkt-data`, `#pkt-handshake` (rendered by JS)
- Sidebar: all 38 old sub-item links present in both `.sidebar` and the mobile overlay (76 total); link set diff vs old sidebar = identical

## Structural repairs performed (old file was broken HTML)

1. **kp-2-19 / Phase 3 entanglement** — in the old file, the Phase 3 header + kp-3-1..3-11, kp-2-20 and kp-dev-tips were physically nested inside kp-2-19's `<details class="txn-fold">` (unclosed `<pre>`, unclosed fold), and kp-2-19's fold had lost its middle section (the "合计" line, the "127 个设备各问一句" paragraph, the "但纯 NAK 毫无意义" table header + first 3 rows). The missing block was restored byte-exactly from commit `ca6e65d` (the commit that originally added card 2.19); all cards are now siblings in the correct phase order matching the sidebar.
2. **Stale duplicate removed** — the second "Phase 3 ◐ 待学习" header + Phase 3 placeholder div (superseded by the actual 11 cards) was dropped; Phase 4-8 headers + placeholders preserved.
3. **txnDetail relocated** — moved out of kp-2-18's card to the bottom of `<main>` (per brief Step 5); frameTimeline stays inside the card.

## Concerns (recommend follow-ups)

1. **Legacy CSS-var compat layer added to head** — the new `usb-notes.css` does not define `--svg-line`, `--svg-text`, `--border` (used inline by card SVGs) nor `.placeholder` / `.diagram-container` (used by Phase 4-8 stubs). To keep card content byte-identical while having diagrams/placeholders render, a small commented `<style>` block was added in the head mapping them to new tokens (e.g. `--svg-line: var(--text-muted)`). This deviates from the brief's "exact head" — consider folding these definitions into `usb-notes.css` instead.
2. **Timeline detail panel UX** — old JS called `detail.scrollIntoView(...)`; the new `usb-notes.js` TimelineRenderer does not. With txnDetail at the bottom of `<main>`, clicking a timeline block fills the panel off-screen. Recommend adding `detail.scrollIntoView({behavior:'smooth', block:'nearest'})` in `showDetail`.
3. **Mobile overlay** — `usb-notes.js` NavOverlay opens/closes `#sidebarOverlay` but does not clone `.sidebar` into it (the brief's comment anticipated JS cloning). The overlay content therefore carries a static duplicate of the nav markup: no search box (avoids a second `#sidebarSearch` id), scroll-spy highlight applies to the desktop sidebar only, and the overlay stays open after tapping a link (no close-on-link handler). Recommend a follow-up JS task.
4. **Inherited quirk (not fixed, by design)** — kp-dev-tips "坑 6" code example contains a literal `</article>` inside `<pre><code>`; real HTML parsers close the article there (identical behavior to the old file). Kept byte-identical per the "card content unchanged" rule; recommend escaping to `&lt;/article&gt;` in a future pass.
5. **Badge spans added to Phase 1/2 headers** (5/5 ✓, 19/19 ✓) per the brief's Step 4 example — old file had bare h2 headers; Phase 3 keeps its original inline span.
6. **Not verified in a browser** — no browser available in this environment; structural checks, DOM-id checks, tag-balance parsing (only known-issue stray closes reported), and JS syntax checks were performed. Visual verification per brief Step 6 still needed.

## Files touched

- Created/overwritten: `D:\CC\personal-lr-notes\CCNotes\USB\usb-notes.html`
- Backup: `D:\CC\personal-lr-notes\CCNotes\USB\usb-notes-old.html`
- Report: `D:\CC\personal-lr-notes\CCNotes\USB\.superpowers\sdd\task-6-report.md` (this file; overwrote a stale report from an older plan)
