# P3-S1: Accessibility Audit

**Phase:** 3
**Priority:** 1
**Effort:** Medium
**Dependencies:** P2-S6

## Description

Integrate axe-core accessibility checks into the CI pipeline and fix critical WCAG AA violations found. Per Amelia's recommendation: `@axe-core/playwright` as a CI gating check.

## Acceptance Criteria

- [ ] `@axe-core/playwright` installed and configured
- [ ] Playwright test that loads the chat page and runs `injectAxe()` + `checkA11y()`
- [ ] All critical/serious violations resolved:
  - Color contrast ratios ≥4.5:1 for all text
  - ARIA labels on all interactive elements (Send, New Chat, citation anchors, flyout close)
  - Focus-visible ring on all interactive elements
  - `aria-live="polite"` on message area for screen reader streaming
  - `role="status"` on compliance badges
  - `role="alert"` on disclaimer banner
  - `role="dialog"` + focus trap on citation flyout
- [ ] Keyboard navigation: Tab through all interactive elements, Enter to activate
- [ ] `prefers-reduced-motion` disables typewriter animation
- [ ] axe-core test added to CI pipeline (or documented as manual step)
- [ ] No functional regression

## Files Touched

- `package.json` or `requirements-dev.txt` — add `@axe-core/playwright`
- `tests/test_accessibility.py` — new: Playwright + axe-core smoke test
- `src/static/index.html` — add missing ARIA labels
- `src/static/js/flyout.js` — verify focus trap + role="dialog" correct
- `src/static/css/chat.css` — verify focus-visible ring present

## Verification

1. `npx playwright test tests/test_accessibility.py` — 0 violations
2. Tab through entire chat flow: all elements reachable
3. VoiceOver/NVDA: reads message area, badges, disclaimer
4. `prefers-reduced-motion` → typewriter disabled
