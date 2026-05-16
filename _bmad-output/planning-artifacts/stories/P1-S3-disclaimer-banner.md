# P1-S3: Disclaimer Banner

**Phase:** 1
**Priority:** 3
**Effort:** Small
**Dependencies:** P1-S1

## Description

Add a persistent, non-modal disclaimer banner to the chat UI. The banner sits below the header and above the message area. It must be visible on first visit and remain dismissible (acknowledged) without a modal popup.

## Acceptance Criteria

- [ ] Banner renders below header, above chat messages
- [ ] Text matches existing disclaimer content from `CHAT_HTML`
- [ ] Banner persists across page reload (sessionStorage flag)
- [ ] User can acknowledge/dismiss the banner with one click
- [ ] After dismissal, banner does not reappear this session
- [ ] On new session (New Chat), banner reappears
- [ ] Banner is responsive — full-width below header on all breakpoints
- [ ] Banner uses `role="alert"` for screen reader announcement
- [ ] No modal, no blocking overlay

## UX State Machine

```
Cold visit → Banner visible
  → User dismisses → Banner hidden for session
  → User clicks New Chat → Banner reappears
```

## Files Touched

- `src/static/index.html` — banner HTML element
- `src/static/css/components.css` — banner styles
- `src/static/js/app.js` — dismiss handler + sessionStorage flag

## Verification

1. Cold load → banner visible at top of chat
2. Click dismiss → banner hides
3. Refresh page → banner stays hidden (sessionStorage)
4. Click New Chat → banner reappears
5. Resize to mobile 375px → banner wraps correctly
6. VoiceOver/NVDA reads banner content as alert
