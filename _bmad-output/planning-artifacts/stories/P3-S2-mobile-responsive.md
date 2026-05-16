# P3-S2: Full Mobile Responsive Pass

**Phase:** 3
**Priority:** 2
**Effort:** Medium
**Dependencies:** P2-S5, P2-S6

## Description

Audit and fix all UI components at mobile viewport sizes (320px-640px). Ensure the chat is fully usable on phone-sized screens.

## Acceptance Criteria

- [ ] Chat bubbles at 100% width below 640px (not 65%)
- [ ] Header condenses padding: `22px 28px` desktop → `16px` mobile
- [ ] Input area full-width, Send button spans full width on very narrow (<400px)
- [ ] Disclaimer banner text wraps correctly at all widths
- [ ] Citation flyout: 85% viewport width on mobile (already implemented in P2-S5)
- [ ] Compliance badges don't overflow or break at narrow widths
- [ ] Typewriter text wraps naturally — no horizontal scroll
- [ ] New Chat button visible and tappable (≥44px touch target)
- [ ] Sidebar (Phase 4, but prepare): hidden on mobile by default
- [ ] Form elements don't zoom on iOS (font-size ≥16px in inputs)
- [ ] Tested at: 320px, 375px, 414px, 640px

## Files Touched

- `src/static/css/chat.css` — mobile breakpoints, bubble width, header padding
- `src/static/css/components.css` — mobile adjustments for badges, flyout, disclaimer
- `src/static/css/base.css` — font-size adjustments if needed

## Verification

1. Open DevTools → responsive mode → 375px (iPhone SE)
2. Full flow: send query → typewriter → badge → citations → flyout → follow-up
3. Verify no horizontal scroll, no overflow, no zoom on input focus
4. Repeat at 320px, 414px, 640px
