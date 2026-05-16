# P2-S2: Compliance Badges

**Phase:** 2 (Wave 1)
**Priority:** 1
**Effort:** Small
**Dependencies:** P1-S1

## Description

Render a color-coded compliance badge as the first content in every assistant message — before the answer text starts streaming. The badge gives instant emotional comprehension of the verdict.

## Acceptance Criteria

- [ ] Badge renders as a pill: 12px/700 text, 2px 10px padding, 12px border-radius
- [ ] Badge renders BEFORE any answer text appears (on SSE `started` or `retrieval`)
- [ ] Four statuses with distinct colors and icons:
  - COMPLIANT: `#1a7f4a` green + checkmark icon
  - NON_COMPLIANT: `#b33a3a` red + X icon
  - PARTIALLY_COMPLIANT: `#b8860b` amber + divided circle icon (per Caravaggio)
  - INSUFFICIENT_DATA: `#6b7280` gray + dash icon
- [ ] Status determined from backend compliance_status in SSE response
- [ ] Badge has `data-status="compliant"` attribute for test targeting
- [ ] Badge works in both light and dark mode (dark: lighter greens `#4ade80`)
- [ ] `role="status"` + `aria-label` for screen reader announcement
- [ ] No backend changes

## Files Touched

- `src/static/js/renderer.js` — badge DOM creation
- `src/static/css/components.css` — badge styles per status

## Verification

1. Submit query for a compliant scenario → green badge renders immediately
2. Submit query for non-compliant → red badge renders
3. Submit insufficient data query → gray badge renders
4. All four statuses visible with correct colors
5. Dark mode: badge colors use lighter variants
6. Screen reader announces badge content
