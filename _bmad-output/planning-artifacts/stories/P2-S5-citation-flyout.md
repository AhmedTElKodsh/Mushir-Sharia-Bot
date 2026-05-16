# P2-S5: Citation Anchors & Flyout Panel

**Phase:** 2 (Wave 2)
**Priority:** 3
**Effort:** Medium
**Dependencies:** P2-S4

## Description

Convert plain text citation markers `[1]`, `[2]` into interactive tap targets. Tapping a citation anchor opens a right-side flyout panel showing the AAOIFI standard excerpt — without losing scroll position.

## Acceptance Criteria

- [ ] After typewriter completes, walk rendered text for `[N]` patterns (N = 1-9)
- [ ] Replace plain `[N]` markers with `<a class="citation-anchor" data-citation="N">` elements
- [ ] Tapping anchor opens right-side flyout panel
- [ ] Flyout: 40% viewport width (max 400px), slide-in animation (200ms ease-out)
- [ ] Flyout has semi-transparent backdrop overlay — tap backdrop to close
- [ ] Flyout body: AAOIFI standard name + section number + excerpt text
- [ ] Citation cards use 4px border-radius (not 8px — per Caravaggio, citations are "evidence, not conversation")
- [ ] `Escape` key closes flyout
- [ ] Focus trapped inside flyout when open
- [ ] Flyout renders as overlay — does NOT push or shift chat content
- [ ] Multiple citations supported — tap different anchors opens different content in same flyout
- [ ] `prefers-reduced-motion`: disable slide animation, instant open

## Files Touched

- `src/static/js/renderer.js` — citation anchor replacement
- `src/static/js/flyout.js` — new module: flyout DOM, open/close, focus trap
- `src/static/css/components.css` — flyout styles, backdrop, citation cards

## Verification

1. Answer with 3 citations → `[1]` `[2]` `[3]` appear as styled anchors
2. Tap `[1]` → flyout slides in from right showing FAS standard + excerpt
3. Tap backdrop → flyout closes, scroll position unchanged
4. Tap `[2]` → flyout content replaced
5. Press `Escape` → flyout closes
6. Tab inside flyout → focus cycles within flyout
7. Mobile 375px → flyout goes to 85% width
