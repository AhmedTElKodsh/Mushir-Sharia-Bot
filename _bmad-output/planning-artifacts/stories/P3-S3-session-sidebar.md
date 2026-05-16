# P3-S3: Session Sidebar

**Phase:** 3
**Priority:** 3
**Effort:** Medium
**Dependencies:** P3-S2

## Description

Add a collapsible sidebar showing recent conversation sessions. Users can click a session to load its history, or start a new chat.

## Acceptance Criteria

- [ ] Sidebar renders on the left side of the chat view (desktop only)
- [ ] Sidebar width: 260px
- [ ] Shows list of recent sessions with: title (first query), preview (last message), timestamp
- [ ] Click session → loads that session's history into main chat view
- [ ] Active session highlighted
- [ ] Sidebar collapse/expand with a permanent visible chevron handle (per Caravaggio — no hamburger hunt)
- [ ] Sidebar hidden on mobile (<640px)
- [ ] Session list sourced from localStorage (StorageAdapter)
- [ ] "New Chat" available in both sidebar and header
- [ ] Empty state: "Your previous conversations will appear here"

## Design Decisions (from Caravaggio's review)
- Collapse handle is a skinny chrome vertical bar with chevron — always visible, zero learning curve
- Sidebar overlays on mobile (slide in from left) — not shown by default, triggered by hamburger

## Files Touched

- `src/static/js/app.js` — session list state, sidebar toggle
- `src/static/js/sidebar.js` — new: sidebar DOM, session list render, click handlers
- `src/static/css/chat.css` — sidebar layout (flex parent)
- `src/static/css/components.css` — sidebar styles, collapse handle, session items
- `src/static/index.html` — sidebar HTML structure

## Verification

1. Desktop: sidebar visible on load with session list
2. Click session → loads conversation into main view
3. Click collapse chevron → sidebar hides, main content expands
4. Mobile <640px: sidebar hidden, hamburger in header
5. Empty state shown when no sessions exist
6. Tests pass
