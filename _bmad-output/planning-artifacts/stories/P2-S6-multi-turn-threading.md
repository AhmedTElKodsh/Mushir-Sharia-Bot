# P2-S6: Multi-Turn Threading

**Phase:** 2 (Wave 3)
**Priority:** 3
**Effort:** Medium
**Dependencies:** P2-S3

## Description

Enable follow-up queries within the same conversation thread. Each user query appends to the visible scroll history. Full conversation context is sent to the backend on every turn.

## Acceptance Criteria

- [ ] Each user query appends as a new user bubble below previous messages
- [ ] Each assistant response appends as a new assistant bubble below the user's query
- [ ] Full conversation history restored from P2-S3 storage on reload
- [ ] Backend receives `conversation_history` array with every POST:
  ```json
  { "query": "follow-up question", "conversation_history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}] }
  ```
- [ ] Scroll position anchored at bottom — auto-scroll on new content
- [ ] Context carries automatically — no re-explaining needed between turns
- [ ] "New Chat" button clears thread and starts fresh session
- [ ] No backend changes needed (existing session management handles history)

## Files Touched

- `src/static/js/app.js` — conversation state management
- `src/static/js/sse-client.js` — attach history to POST body
- `src/static/js/renderer.js` — append mode (not replace mode)

## Verification

1. Send query → user bubble + assistant bubble render
2. Send follow-up → new user bubble below previous, new assistant bubble below that
3. At least 5 turns visible in scroll — no content replaced
4. Refresh page → all 5 turns restored
5. Click New Chat → thread cleared, welcome view
6. DevTools network → inspect POST body includes conversation_history array
