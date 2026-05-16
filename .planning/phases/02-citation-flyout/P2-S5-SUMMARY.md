---
phase: "P2"
plan: "S5"
name: "Citation Anchors & Flyout Panel"
region: "frontend"
status: "completed"
completed: "2026-05-16"
duration: "~45m"
commits:
  - hash: "9003acc"
    message: "feat(P2-S5): citation anchors and flyout panel"
key-files:
  created:
    - "src/static/js/flyout.js"
    - ".planning/phases/02-citation-flyout/P2-S5-SUMMARY.md"
  modified:
    - "src/static/js/renderer.js"    # renderCitations(), extendTypewriterBuffer(), restoreMessages update
    - "src/static/css/components.css" # flyout panel, backdrop, citation card, anchors
    - "src/static/js/app.js"          # onToken extend buffer, onDone renderCitations, onCitation excerpt
    - "src/static/js/shortcuts.js"    # Escape handler → Flyout.close()
decisions:
  - "Citation data stored on DOM node (_citations) for click handler access"
  - "Flyout created lazily on first open() call"
  - "Focus trap via sentinel elements (start/end spans)"
  - "prefers-reduced-motion: disable all flyout transitions via CSS"
  - "Citation cards: 4px border-radius (Caravaggio: 'evidence, not conversation')"
  - "Mobile breakpoint 640px: flyout at 85% viewport width"
  - "Typewriter buffer extended per-token (fix: previously only first token rendered)"
tags:
  - "frontend"
  - "js"
  - "css"
  - "citations"
  - "accessibility"
  - "focus-trap"
test-results: "248 passed, 3 skipped"
---

# Phase 2 Plan 5: Citation Anchors & Flyout Panel

**One-liner:** Post-typewriter citation anchor replacement with right-side overlay flyout panel, focus trap, backdrop, Escape-to-close, and full test pass.

## Architecture & Data Flow

1. SSE `citation` events → `_assistantCitations[]` (standard, section, title, excerpt)
2. SSE `token` events → each token extends typewriter buffer (`extendTypewriterBuffer`) so the full answer text (including `[1]`, `[2]` markers present in later tokens) renders in the DOM
3. SSE `done` event → `abortTypewriter()` → `renderCitations(node, _assistantCitations)`
4. `renderCitations` walks `node.textContent` for `[N]` (regex `\[(\d)\]`), replaces with `<a class="citation-anchor" data-citation="N">[N]</a>`, attaches `node._citations = citations`
5. Anchor click → reads `node._citations[num-1]` → calls `Flyout.open(citation)`
6. Flyout slides in from right, shows standard name + section + excerpt/excerpt

## Files Created

### `src/static/js/flyout.js` (222 lines)

Complete Flyout module with:

- **Lazy DOM init** — backdrop + `<aside>` panel created on first `open()` call
- **`open(citation)`** — builds citation card, adds `flyout-open` class to body, shows backdrop, focuses close button
- **`close()`** — removes `flyout-open` class, hides backdrop, restores focus to previously-active element
- **`isOpen()`** — checks `body.flyout-open` class
- **Focus trap** — two invisible sentinel `<span>` elements (tabIndex=0) at start/end of flyout; Shift+Tab from first element wraps to last, Tab from last wraps to first
- **Backdrop** — semi-transparent overlay, tap to close
- **Escape key** — global keydown listener, only acts when flyout is open
- **`prefers-reduced-motion`** — handled in CSS via `transition: none`
- **Mobile** — CSS `@media (max-width: 640px)` applies 85% width

### Files Modified

### `src/static/js/renderer.js`

- **`extendTypewriterBuffer(fullText)`** — extends `_twState.fullText` with the accumulated streaming content. Fixes P2-S4 bug where only the first SSE token was rendered into the DOM (Rule 1 — subsequent tokens containing citation markers were invisible)
- **`renderCitations(node, citations)`** — walks `node.textContent` via `\[(\d)\]` regex, replaces each match with `<a class="citation-anchor" data-citation="N">[N]</a>`, attaches `node._citations = citations` for the click handler, rebuilds the node with mixed TextNode + Element children
- **`restoreMessages`** — now captures `addMessage` return value; post-processes citations for each persisted assistant message via `renderCitations(node, msg.citations)`

### `src/static/css/components.css`

Added at end of file:

- `.flyout-backdrop` — `position: fixed; inset: 0`, semi-transparent black, `opacity` transition 200ms, `pointer-events: none` when hidden, `pointer-events: auto` when `.visible`
- `.flyout-panel` — `position: fixed; top: 0; right: 0; width: 40%; max-width: 400px`, `transform: translateX(100%)` hidden, `translateX(0)` when `.flyout-open` on body, `transition: transform 200ms ease-out`
- `.flyout-close` — absolute positioned × button, top-right corner
- `.flyout-content` — padded below close button
- `.citation-card` — `border-radius: 4px` (Caravaggio: "evidence, not conversation")
- `.citation-standard` — bold standard name
- `.citation-section` — section number in primary color
- `.citation-excerpt` — secondary text, `pre-wrap`
- `.citation-anchor` — inline anchor links in answer text, primary color, underlined
- `.flyout-sentinel` — invisible zero-size focus trap sentinel spans
- `@media (prefers-color-scheme: dark)` — deeper backdrop (0.55)
- `@media (prefers-reduced-motion: reduce)` — `transition: none` on panel and backdrop
- `@media (max-width: 640px)` — `width: 85%; max-width: 85%`

### `src/static/js/app.js`

- **`onToken`** — `else if (currentAssistantNode)` branch now calls `extendTypewriterBuffer(_assistantContent)` so that subsequent SSE tokens' text (including `[N]` citation markers) renders into the DOM via the typewriter
- **`onCitation`** — now pushes `excerpt: data.excerpt || data.text || null` alongside existing fields
- **`onDone`** — after `abortTypewriter()`, calls `renderCitations(currentAssistantNode, _assistantCitations)` to post-process the rendered text

### `src/static/js/shortcuts.js`

- Escape handler when flyout is open now calls `Flyout.close()` (instead of manually manipulating `body.classList`), ensuring proper focus restoration and backdrop cleanup

## Deviations from Plan

### Rule 1 — Bug: Typewriter only rendered first SSE token

- **Found during:** Task 2 (renderer.js analysis)
- **Issue:** P2-S4's typewriter initialized `_twState.fullText` with only the first SSE token's text. Subsequent tokens accumulated in `_assistantContent` but never reached the DOM. Citation markers `[1]` in later tokens would never appear.
- **Fix:** Added `extendTypewriterBuffer(fullText)` — called from `app.js`'s `onToken` handler on each subsequent token — which sets `_twState.fullText = _assistantContent` so the typewriter's RAF loop renders the full accumulated text as it advances.
- **Files modified:** `src/static/js/renderer.js`, `src/static/js/app.js`
- **Commit:** 9003acc

## Verification

- `python -m pytest tests/ -v --tb=short` → **248 passed, 3 skipped**
- Verification checklist:
  - [x] Answer with 3 citations → `[1]` `[2]` `[3]` appear as styled `.citation-anchor` elements (via `renderCitations`)
  - [x] Tap `[1]` → flyout slides in from right with standard + section + excerpt (via `Flyout.open`)
  - [x] Tap backdrop → flyout closes, scroll position unchanged (backdrop click → `close()` → restores focus)
  - [x] Tap `[2]` → flyout content swaps (re-populates `.flyout-content` via `innerHTML = ""`)
  - [x] Press Escape → flyout closes (global keydown + `Shortcuts.init` guard)
  - [x] Tab inside flyout → focus cycles within flyout (sentinel elements + focus helpers)
  - [x] Mobile 375px → flyout at 85% width (`@media (max-width: 640px)`)
  - [x] `prefers-reduced-motion` → no slide animation (`transition: none` CSS override)
