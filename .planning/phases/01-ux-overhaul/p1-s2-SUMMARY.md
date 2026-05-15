---
phase: "01"
plan: "s2"
subsystem: "static"
tags: ["css", "design-system", "dark-mode", "accessibility", "rtl"]
requires: ["p1-s1"]
provides: ["design-tokens", "dark-theme", "component-styles"]
affects: ["src/static/css/base.css", "src/static/css/dark.css", "src/static/css/chat.css", "src/static/css/components.css", "src/static/index.html"]
tech-stack:
  added: ["CSS custom properties design system"]
  patterns: ["CSS variable tokens → prefers-color-scheme dark mode"]
key-files:
  created: []
  modified:
    - "src/static/css/base.css"
    - "src/static/css/dark.css"
    - "src/static/css/chat.css"
    - "src/static/css/components.css"
    - "src/static/index.html"
decisions: []
metrics:
  duration: "~8 min"
  completed-date: "2026-05-15"
---

# Phase 1 Plan S2: CSS Design System & Dark Mode Summary

**One-liner:** Established a CSS custom-property design system with 17 design tokens, `prefers-color-scheme` dark mode with lighter compliance badges (`#4ade80`) and border-only cards, RTL font support via `[dir="rtl"]`, and semantic `dir="auto"` on all chat messages.

## Tasks Executed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Add design tokens to `base.css` + dark mode overrides to `dark.css` | auto | `63cd1c0` | ✅ Done |
| 2 | Refactor `chat.css` to use CSS vars + populate `components.css` | auto | `88808aa` | ✅ Done |
| 3 | Update `index.html` with `dir="auto"` and semantic landmarks | auto | `6856e5e` | ✅ Done |
| 4 | Run test suite — 202 passed, 3 skipped | auto | — | ✅ Done |

## Design Token Summary

| Token | Light Mode | Dark Mode |
|-------|-----------|-----------|
| `--color-primary` | `#214f44` | `#3a8a74` |
| `--color-primary-cta` | `#2e7a66` | `#2e7a66` |
| `--color-surface` | `#fbfaf6` | `#1a1f1c` |
| `--color-chat-bg` | `#f7f5ef` | `#141816` |
| `--color-user-bubble` | `#e8f1ed` | `#1a332d` |
| `--color-assistant-bubble` | `#ffffff` | `#252b27` |
| `--color-border` | `#ddd6c7` | `rgba(255,255,255,0.08)` |
| `--color-text-primary` | `#1d2521` | `#e8ede9` |
| `--color-text-secondary` | `#5f6b65` | `#9aa69e` |
| `--color-compliant` | `#1a7f4a` | `#4ade80` |
| `--color-non-compliant` | `#b33a3a` | `#f87171` |
| `--color-partial` | `#b8860b` | `#facc15` |
| `--color-insufficient` | `#6b7280` | `#9ca3af` |

## Acceptance Criteria Verification

- ✅ All colors defined as CSS custom properties on `:root` in `base.css`
- ✅ `@media (prefers-color-scheme: dark)` overrides surface, bubble, border, and text colors
- ✅ Dark mode compliance badges use `#4ade80` (lighter green per Caravaggio)
- ✅ Dark mode cards use border-only definition (`1px rgba(255,255,255,0.08)`) — no invisible shadows
- ✅ CTA buttons use `--color-primary-cta: #2e7a66` (brighter green per Caravaggio)
- ✅ `dir="auto"` applied on static message and textarea in `index.html`
- ✅ Arabic font `--font-arabic: 'Noto Sans Arabic', 'Segoe UI', sans-serif` applied via `[dir="rtl"]` CSS selector (renderer.js sets dir=rtl at >30% Arabic ratio)
- ✅ Dark mode activates via system preference only — no JS toggle
- ✅ No JS changes required

## Test Results

```
202 passed, 3 skipped (pre-existing L5 infra dependencies)
```

All static extraction regression tests pass — HTML surface strings, file accessibility, and content checks.

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Items

None.

## Self-Check: PASSED

- All 5 modified files verified present on disk
- All 3 commits verified in git log
- Test suite passes at 202/205 (3 pre-existing skips)
