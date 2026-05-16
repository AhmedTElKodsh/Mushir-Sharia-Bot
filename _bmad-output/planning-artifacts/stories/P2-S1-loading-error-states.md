# P2-S1: Loading & Error States

**Phase:** 2 (Wave 1)
**Priority:** 1
**Effort:** Small
**Dependencies:** P1-S1

## Description

Add typing indicator during LLM response generation and error recovery UI when the SSE stream fails.

## Acceptance Criteria

- [ ] Three animated dots ("...") shown from SSE `started` event until first `token` event
- [ ] Typing indicator appears inside an assistant bubble placeholder
- [ ] On SSE `error` event, replace indicator with red-bordered error bubble + "Retry" button
- [ ] "Retry" re-sends the last user message through the same SSE stream
- [ ] On SSE `done` event, remove indicator, render final answer
- [ ] `prefers-reduced-motion`: disable dot animation, show static "Mushir is composing..." text
- [ ] No backend changes

## Files Touched

- `src/static/js/renderer.js` â€” typing indicator DOM, error bubble, retry handler
- `src/static/js/sse-client.js` â€” event lifecycle hooks
- `src/static/css/components.css` â€” indicator styles, error styles

## Verification

1. Submit query â†’ typing indicator appears within 500ms
2. SSE error â†’ indicator replaced by error bubble + retry
3. Click retry â†’ query re-submitted, indicator reappears
4. Normal flow â†’ indicator disappears when first token arrives
