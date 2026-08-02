# Task Fix Report — USB Notes Redesign

- Status: DONE
- Date: 2026-08-02
- Files touched:
  - `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.css`
  - `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.html`
  - `D:/CC/personal-lr-notes/CCNotes/USB/usb-notes.js`

## ISSUE 1 — Missing CSS variables for SVG diagrams

### What was fixed

1. **`usb-notes.css` Layer 1 `:root`** — added a new section "SVG 图例兼容变量":
   - `--svg-line: #adb5bd;`
   - `--svg-text: #e9ecef;`
   - `--svg-fill: #25262b;`
   - `--border: var(--card-border);` (maps the old `--border` to the design token; the
     var() substitution resolves per-element, so light mode correctly inherits the
     `.light` value of `--card-border`)

2. **`usb-notes.css` Layer 1 `.light`** — added:
   - `--svg-line: #495057;`
   - `--svg-text: #212529;`
   - `--svg-fill: #f8f9fa;`
   - `--border: var(--card-border);`

3. **`usb-notes.css` Layer 5 (Components)** — added section `5.11 Legacy 兼容类` with
   `.placeholder` (incl. `h3` and `ul` rules) and `.diagram-container` / `svg` rules,
   exactly as specified in the task (tokenized: `--radius-md`, `--space-7`, etc.).

4. **`usb-notes.html`** — removed the entire compat `<style>` block (the `<!-- 兼容层 -->`
   comment, the `:root` var mapping, and the `.placeholder` / `.diagram-container` rules)
   from `<head>`. The anti-flash script now flows directly into the `usb-notes.js` include.

## ISSUE 2 — Mobile sidebar overlay doesn't clone the actual sidebar

### What was fixed

1. **`usb-notes.js` `NavOverlay.open()`** — now clones `document.querySelector('.sidebar')`
   into `#sidebarOverlayContent` (guarded by `!content.children.length`) before adding the
   `open` class, so mobile users get the full sidebar: search box, progress bar, all links,
   and current active states.

2. **`usb-notes.js` `NavOverlay.init()`** — added a click listener on
   `#sidebarOverlayContent` that calls `self.close()` when a `.sub-item` is clicked.

3. **`usb-notes.html`** — the static hard-coded copy inside `#sidebarOverlayContent`
   (2 phase blocks + 6 placeholder `<details>`, ~70 lines) was removed and the container
   is now empty; otherwise the `!content.children.length` guard would never pass and the
   clone would never run. The stale HTML comment was updated to describe the cloning
   behavior.

4. **`usb-notes.css` Layer 8 (Responsive)** — added `.sidebar-overlay-content .sidebar`
   override inside `@media (max-width: 1023px)` (`position: static; display: block;
   width: 100%; height: auto; border-right: none; padding: 0`). This is required: the
   media query's `display: none` targets the class selector `.sidebar`, which the clone
   retains, so without this rule the cloned sidebar would be invisible inside the overlay.

## Verification results

1. Compat `<style>` block gone from `usb-notes.html` — confirmed: no `<style>` tag and no
   "兼容层" comment remain in the file.
2. `grep -c "svg-line\|svg-text\|svg-fill" usb-notes.css` → **6** (3 definitions in `:root`
   + 3 in `.light`; requirement was ≥ 3).
3. `node --check usb-notes.js` → **PASS**.
4. Integrity checks: `id="sidebarOverlayContent"` occurs exactly once in HTML; the only
   `id` inside the sidebar is `sidebarSearch`; the inline SVGs' references to
   `var(--svg-line)` / `var(--svg-text)` / `var(--border)` now resolve from
   `usb-notes.css` instead of the deleted compat block.

## Concerns / notes (non-blocking)

- `--svg-fill` is **not referenced** anywhere in the current `usb-notes.html` (verified by
  grep: 0 occurrences). It was added anyway per the task's specified values, for parity
  with the old theme and future use.
- After the first overlay open, the cloned sidebar introduces a **duplicate
  `id="sidebarSearch"`** in the DOM. This is benign in practice: the only
  `getElementById('sidebarSearch')` call (SearchFilter.init) runs at DOMContentLoaded,
  before the clone exists, so desktop search stays bound to the real input; ScrollSpy and
  SearchFilter re-query `.sidebar .sub-item` on every event, so active states and
  filtering stay in sync with the clone too.
- The cloned search box in the overlay is **inert** (its input has no listener). This
  matches the previous behavior of the static copy (the old HTML comment documented the
  same limitation), and is out of scope for this fix.
- The clone is created only once (first open) because of the `!content.children.length`
  guard; active states still propagate to it afterwards via ScrollSpy's live re-query.
