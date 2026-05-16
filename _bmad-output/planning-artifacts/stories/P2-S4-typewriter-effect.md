# P2-S4: Typewriter Effect

**Phase:** 2 (Wave 1)
**Priority:** 2
**Effort:** Medium
**Dependencies:** P1-S1

## Description

Simulate real-time streaming by rendering the answer text character-by-character in the assistant bubble. The full answer arrives in one SSE `token` event — the frontend reveals it gradually.

## Acceptance Criteria

- [ ] On SSE `token` event, buffer the full answer text
- [ ] Render characters one-at-a-time using `requestAnimationFrame` at configurable speed (default ~25ms/char)
- [ ] Citation markers `[1]`, `[2]` render as visible text markers initially (S5 converts to anchors)
- [ ] Typewriter aborts cleanly if user submits a new message mid-stream
- [ ] Typewriter aborts on SSE `done` (renders remaining text instantly)
- [ ] When streaming complete, no "jump" or flicker — final text matches full answer
- [ ] `prefers-reduced-motion`: render full text instantly, no animation
- [ ] Compliance badge is already visible (from S2) before typewriter begins
- [ ] No backend changes

## Implementation Notes

- Use `requestAnimationFrame` loop with character counter
- Store unresolved answer in module-scoped buffer
- Abort signal: check `appState.streaming` flag each frame
- Speed stored as `config.typewriterSpeed` (ms per char) — adjustable

## Files Touched

- `src/static/js/renderer.js` — `renderTypewriter()` method
- `src/static/js/sse-client.js` — wire token handler to typewriter
- `src/static/css/chat.css` — cursor blink animation

## Verification

1. Submit query → characters appear one-by-one at ~25ms intervals
2. Submit new query mid-typewriter → current stream aborts, new begins
3. SSE done → remaining text renders instantly
4. Enable `prefers-reduced-motion` → full text appears instantly
5. Compliance badge visible before first character appears
