---
phase: "02"
plan: "s2"
subsystem: "frontend"
tags: ["badge", "compliance", "SSE", "status", "a11y", "dark-mode"]
provides: ["compliance-badge-rendering"]
affects: ["renderer.js", "components.css", "app.js"]
tech-stack:
  added: []
  patterns: ["SSE done-event status extraction", "DOM insertBefore for ordered rendering"]
key-files:
  created: []
  modified:
    - "src/static/css/components.css"
    - "src/static/js/renderer.js"
    - "src/static/js/app.js"
decisions:
  - "Render badge from SSE done event (not retrieval) — backend retrieval event only sends confidence, not status"
  - "Insert badge before last .message.assistant node rather than appending to messages, preserving badge-before-text visual order"
metrics:
  duration: "~30m"
  completed: "2026-05-16"
---

# Phase 02 Plan S2: Compliance Badges

Compliance status badge pill rendered before assistant answer text via SSE streaming, with distinct color/icon per status, dark mode support, and ARIA accessibility.

## Deviations from Plan

The renderBadge function, badge CSS, and app.js integration hook were already committed in prior work (appears to have been scaffolded ahead of time). Two blocking bugs prevented the badge from ever rendering. Fixed inline:

### Auto-fixed Issues

**1. [Rule 1 - Bug] CSS class names mismatched between renderer.js and components.css**

- **Found during:** task execution — code review of renderer.js vs components.css
- **Issue:** `renderBadge()` normalizes `PARTIALLY_COMPLIANT` to `"partially-compliant"` and `INSUFFICIENT_DATA` to `"insufficient-data"`, but components.css had classes `.badge.partial` and `.badge.insufficient`. Badges for these two statuses rendered with no background color — invisible pills.
- **Fix:** Renamed `.badge.partial` → `.badge.partially-compliant` and `.badge.insufficient` → `.badge.insufficient-data` in components.css
- **Files modified:** `src/static/css/components.css`
- **Commit:** 6b897fd

**2. [Rule 1 - Bug] renderBadge called from onRetrieval where status is never present**

- **Found during:** tracing SSE event payloads — reviewed `src/api/routes.py` line 193
- **Issue:** The SSE `retrieval` event only sends `{"confidence": ...}` per backend (`yield _sse("retrieval", {"confidence": response["metadata"].get("confidence", 0.0)})`). The status field is ONLY in the `done` event. The check `if (data.status) renderBadge(data.status)` at line 117 of app.js was always falsy → badge never rendered for any query.
- **Fix:** Moved `renderBadge(data.status)` from `onRetrieval` to `onDone` in app.js, inserted before the completion event message. Added comment explaining the backend payload structure.
- **Files modified:** `src/static/js/app.js`
- **Commit:** 6b897fd

**3. [Rule 2 - Missing critical functionality] Badge appended after assistant text**

- **Found during:** DOM order analysis — `messages.appendChild(badge)` places badge at end of chat, after all message text
- **Issue:** AC 2 requires badge to render BEFORE answer text. Appending to `messages` puts it after the assistant bubble.
- **Fix:** Changed to `messages.insertBefore(badge, lastAssistant)` which inserts the badge before the last `.message.assistant` node in the DOM, preserving badge-before-text visual order.
- **Files modified:** `src/static/js/renderer.js`
- **Commit:** 6b897fd

## Decision Log

| Decision | Context | Outcome |
|----------|---------|---------|
| Badge rendering trigger | Status only available in SSE done event | renderBadge called from onDone, not onRetrieval |
| Badge DOM insertion | Must appear before message text | insertBefore last assistant node vs appendChild |
| CSS class naming | Normalized status strings vs abbreviated | Match JS-generated class names (partially-compliant, insufficient-data) |

## Verification

- ✅ All 248 tests pass (3 skipped: Redis/Postgres/Qdrant — external services)
- ✅ `test_js_restoreMessages_renders_badges` confirms restoreMessages checks for badges
- ✅ Compliance badge renders in correct position (before assistant text)
- ✅ Four statuses: COMPLIANT (green ✓), NON_COMPLIANT (red ✗), PARTIALLY_COMPLIANT (amber ◐), INSUFFICIENT_DATA (gray —)
- ✅ Dark mode: lighter badge colors via dark.css overrides
- ✅ role="status" + aria-label for screen readers
- ✅ data-status attribute on badge for test targeting
- ✅ No backend changes

## Commit

```
6b897fd feat(P2-S2): fix compliance badge rendering — move to onDone, fix CSS class names, insert before text
```
