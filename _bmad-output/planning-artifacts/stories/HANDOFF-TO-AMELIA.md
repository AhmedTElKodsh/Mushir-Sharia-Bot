# Handoff to Amelia

## Project
Mushir Sharia Compliance Chatbot — RAG-based AAOIFI Islamic finance chatbot

## Complete UX Design Specification
`_bmad-output/planning-artifacts/ux-design-specification.md`

## Design Direction Visualizer (open in browser)
`_bmad-output/planning-artifacts/ux-design-directions.html`

## SSE Stream — Verified Correct

All 6 event types (`started`, `retrieval`, `token`, `citation`, `done`, `error`) already use `_sse()` helper. No backend changes needed for Phases 1-3.

**Critical finding:** The `token` event emits the **full answer at once**, not streaming characters. Typewriter must be client-side simulated (S4).

## Implementation Roadmap

### Phase 1 — Static Extraction + CSS (parallel stories after S1)

| Story | File | Effort | Deps |
|-------|------|--------|------|
| **P1-S1** Static Extraction | `stories/P1-S1-static-extraction.md` | Medium | None |
| **P1-S2** Design System + Dark Mode | `stories/P1-S2-design-system-dark-mode.md` | Small | S1 |
| **P1-S3** Disclaimer Banner | `stories/P1-S3-disclaimer-banner.md` | Small | S1 |
| **P1-S4** Keyboard Shortcuts | `stories/P1-S4-keyboard-shortcuts.md` | Small | S1 |

### Phase 2 — Core UX Features (Wave 1 → Wave 2 → Wave 3)

| Story | File | Effort | Deps |
|-------|------|--------|------|
| **P2-S1** Loading & Error States | `stories/P2-S1-loading-error-states.md` | Small | P1-S1 |
| **P2-S2** Compliance Badges | `stories/P2-S2-compliance-badges.md` | Small | P1-S1 |
| **P2-S3** Message Persistence | `stories/P2-S3-message-persistence.md` | Medium | P1-S1 |
| **P2-S4** Typewriter Effect | `stories/P2-S4-typewriter-effect.md` | Medium | P1-S1 |
| **P2-S5** Citation Flyout | `stories/P2-S5-citation-flyout.md` | Medium | P2-S4 |
| **P2-S6** Multi-Turn Threading | `stories/P2-S6-multi-turn-threading.md` | Medium | P2-S3 |

## Execution Order (Recommended)

1. **P1-S1** (blocking — extract static files first)
2. **P1-S2** + **P1-S3** + **P1-S4** in parallel (CSS-only, no JS coupling)
3. **P2-S1** + **P2-S2** + **P2-S3** + **P2-S4** in parallel (Wave 1)
4. **P2-S5** (Wave 2 — needs S4's typewriter text)
5. **P2-S6** (Wave 3 — needs S3's persistence)

## File Architecture (target)

```
src/static/
├── index.html              # Extracted from CHAT_HTML
├── css/
│   ├── base.css            # CSS reset + custom properties (design tokens)
│   ├── chat.css            # Message bubbles, layout, input area
│   ├── components.css      # Badges, citations, buttons, disclaimer
│   └── dark.css            # prefers-color-scheme overrides
└── js/
    ├── app.js              # Orchestrator, init, state machine
    ├── sse-client.js       # EventSource wrapper + event dispatch
    ├── renderer.js         # DOM: messages, typewriter, badges
    ├── flyout.js           # Citation flyout panel
    ├── storage.js          # sessionStorage persistence
    └── shortcuts.js        # Keyboard keybindings
```

## Key Design Decisions
- **No framework, no build step** — vanilla HTML/CSS/JS
- **Dark mode** via `prefers-color-scheme`, no toggle
- **Mobile-first** breakpoints: 640px, 1024px
- **RTL** via `dir="auto"` per-message
- **Citations** flyout panel (not expand/collapse), 4px radius
- **Compliance badge** renders BEFORE answer text
- **Typewriter** client-side `requestAnimationFrame` loop
- **Accessibility** WCAG AA: axe-core in CI, `aria-live`, focus management
