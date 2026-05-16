# P2-S3: Message Persistence

**Phase:** 2 (Wave 1)
**Priority:** 2
**Effort:** Medium
**Dependencies:** P1-S1

## Description

Persist conversation history to `sessionStorage` so page refresh preserves the chat thread. On load, restore messages in correct order with no flash-of-empty.

## Acceptance Criteria

- [ ] After each complete assistant message (SSE `done`), serialize full conversation to `sessionStorage`
- [ ] Storage key includes session_id + timestamp for multi-session support
- [ ] On page load, synchronous read from `sessionStorage` populates chat container before first render
- [ ] Messages restored in correct chronological order
- [ ] No flash-of-empty — storage read completes before DOM paints
- [ ] "New Chat" clears storage for the current session
- [ ] Storage schema: `{ messages: [{role, content, timestamp, status, citations}], session_id }`
- [ ] Handles storage quota errors gracefully (console.warn, app continues)
- [ ] No backend changes

## Files Touched

- `src/static/js/storage.js` — new module: save, load, clear
- `src/static/js/app.js` — wire persistence hooks
- `src/static/js/renderer.js` — restore render path

## Verification

1. Send query → receive answer
2. Refresh page → full conversation visible, same order
3. Send follow-up → new messages append correctly
4. Click New Chat → storage cleared, fresh welcome view
5. Open DevTools → Application → Session Storage → verify schema
