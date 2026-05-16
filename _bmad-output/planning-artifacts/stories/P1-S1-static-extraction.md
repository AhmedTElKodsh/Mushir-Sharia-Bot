# P1-S1: Static Extraction & Baseline

**Phase:** 1
**Priority:** 1 (blocking)
**Effort:** Medium
**Dependencies:** None

## Description

Extract the inline `CHAT_HTML` string from `src/api/main.py` into separate static files served by FastAPI. Zero functional or visual change — this is pure refactoring.

## Acceptance Criteria

- [ ] FastAPI mounts `src/static/` directory via `StaticFiles`
- [ ] `src/static/index.html` renders identically to the current inline CHAT_HTML
- [ ] All CSS extracted to `src/static/css/` (base.css, chat.css, components.css, dark.css)
- [ ] All JS extracted to `src/static/js/` (app.js, sse-client.js, renderer.js, storage.js, shortcuts.js)
- [ ] No visual or behavioral regression
- [ ] No new features introduced
- [ ] Existing `GET /` and `GET /chat` routes serve the extracted `index.html`
- [ ] CSP headers in `main.py` updated to allow static resource loading
- [ ] Existing test suite passes unchanged

## Files Touched

- `src/api/main.py` — remove CHAT_HTML, add StaticFiles mount
- `src/api/routes.py` — no changes expected
- `src/static/index.html` — new (extracted from CHAT_HTML)
- `src/static/css/base.css` — new (CSS reset + custom properties)
- `src/static/css/chat.css` — new (bubbles, layout, input area)
- `src/static/css/components.css` — new (badges, citations, buttons)
- `src/static/css/dark.css` — new (prefers-color-scheme overrides)
- `src/static/js/app.js` — new (orchestrator + init)

## Verification

1. Start server, open `http://localhost:8000/chat`
2. Confirm page renders identically to before extraction
3. Run `pytest tests/ -v` — all pass
4. Confirm dark mode via DevTools "Emulate CSS prefers-color-scheme: dark"

## Notes

- The current `parseSse()` function in CHAT_HTML should be extracted into `sse-client.js`
- Event type dispatch logic belongs in `app.js`
- No backend SSE changes needed — Winston confirmed all `_sse()` paths are correct
