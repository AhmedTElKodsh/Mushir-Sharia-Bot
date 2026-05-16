# P1-S2: CSS Design System & Dark Mode

**Phase:** 1
**Priority:** 2
**Effort:** Small
**Dependencies:** P1-S1

## Description

Implement the CSS custom properties design system with dark mode support via `prefers-color-scheme`. Establish all design tokens as CSS custom properties on `:root`. Add RTL layout support.

## Acceptance Criteria

- [ ] All colors defined as CSS custom properties on `:root` (light theme defaults)
- [ ] `@media (prefers-color-scheme: dark)` overrides surface, bubble, border, and text colors
- [ ] Status badge colors: `--color-compliant`, `--color-non-compliant`, `--color-partial`, `--color-insufficient`
- [ ] Compliance badges use `#4ade80` green in dark mode (per Caravaggio)
- [ ] Dark mode cards use border-only definition (1px `rgba(255,255,255,0.08)`) — no invisible shadows
- [ ] `dir="auto"` applied per-message for RTL detection
- [ ] Arabic font: `'Noto Sans Arabic', 'Segoe UI', sans-serif` applied when Arabic ratio >30%
- [ ] No visual regression in light mode
- [ ] No JS changes required

## Design Tokens

```css
:root {
  --color-primary: #214f44;
  --color-primary-cta: #2e7a66;  /* brighter for buttons per Caravaggio */
  --color-surface: #fbfaf6;
  --color-chat-bg: #f7f5ef;
  --color-user-bubble: #e8f1ed;
  --color-assistant-bubble: #ffffff;
  --color-border: #ddd6c7;
  --color-text-primary: #1d2521;
  --color-text-secondary: #5f6b65;
  --color-compliant: #1a7f4a;
  --color-non-compliant: #b33a3a;
  --color-partial: #b8860b;
  --color-insufficient: #6b7280;
}
```

## Files Touched

- `src/static/css/base.css` — add custom properties
- `src/static/css/dark.css` — dark mode overrides

## Verification

1. Load page, confirm light theme renders correctly
2. Toggle DevTools → Rendering → Emulate CSS prefers-color-scheme: dark
3. Confirm all surfaces, bubbles, and badges switch to dark palette
4. Verify compliance badge greens are lighter in dark mode (`#4ade80` range)
5. Confirm card borders visible in dark mode (no invisible drop shadows)
