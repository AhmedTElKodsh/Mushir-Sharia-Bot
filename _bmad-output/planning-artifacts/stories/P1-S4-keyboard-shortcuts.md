# P1-S4: Keyboard Shortcuts

**Phase:** 1
**Priority:** 4
**Effort:** Small
**Dependencies:** P1-S1

## Description

Add keyboard shortcuts for power users. Shortcuts must not fire when the user is typing in the input area or when a modal/flyout is open.

## Acceptance Criteria

- [ ] `Ctrl+Enter` or `Cmd+Enter` sends the current message (same as clicking Send)
- [ ] `/` (forward slash) focuses the input when not already focused
- [ ] `Escape` blurs the input field
- [ ] `Escape` closes the citation flyout if open
- [ ] No shortcuts fire when input is focused (except send)
- [ ] No shortcuts fire when citation flyout or dialog is open
- [ ] Shortcuts work cross-browser (Chrome, Firefox, Safari, Edge)
- [ ] No backend changes

## Implementation Notes

- Use `keydown` event listener on `document`
- Check `event.target` to determine if input is focused
- Check for open flyout/dialog via CSS class or DOM query
- Modifier key detection: `event.ctrlKey || event.metaKey`
- Extract into `src/static/js/shortcuts.js` module

## Files Touched

- `src/static/js/shortcuts.js` — new module
- `src/static/js/app.js` — register shortcuts on init

## Verification

1. Load page, press `/` → input focuses
2. Type text, press `Ctrl+Enter` → message sends
3. Press `Escape` → input blurs
4. Open citation flyout, press `Escape` → flyout closes
5. With flyout open, press `/` → NOT redirected to input
