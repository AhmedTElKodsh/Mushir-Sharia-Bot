---
gsd_state_version: 1.1
milestone: source-governed-mushir
milestone_name: Source-Governed Mushir Planning
status: active
last_updated: "2026-05-24"
canonical_root: ".planning/sharia-compliance-chatbot"
---

# Planning State

The canonical planning tree is now:

```text
.planning/sharia-compliance-chatbot/
```

The older tracked layout under `.planning/phases/...` has been superseded by
the namespaced project layout above. Keep planning work inside the canonical
root so Mushir planning, copied documentation, phase summaries, research
evidence, and L6 scrape artifacts do not mix with unrelated project planning.

## Active Entry Points

| Purpose | File |
| --- | --- |
| Current planning and documentation index | `.planning/sharia-compliance-chatbot/docs/index.md` |
| Next-level roadmap | `.planning/sharia-compliance-chatbot/next-level-plans/README.md` |
| Current requirements | `.planning/sharia-compliance-chatbot/docs/requirements.md` |
| Current design | `.planning/sharia-compliance-chatbot/docs/design.md` |
| Current task backlog | `.planning/sharia-compliance-chatbot/docs/tasks.md` |
| L5 readiness plan | `.planning/sharia-compliance-chatbot/next-level-plans/L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md` |
| L6 rules-first evaluator plan | `.planning/sharia-compliance-chatbot/next-level-plans/L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md` |
| L6 Egypt institution evidence-corpus plan | `.planning/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md` |
| Historical UI phase summaries | `.planning/sharia-compliance-chatbot/phases/` |

## Folder Roles

| Folder | Role | Cleanup Rule |
| --- | --- | --- |
| `docs/` | Planning copies of maintained project docs, research syntheses, client handoff docs, and L6 evidence notes. | Keep as the readable planning/documentation surface. |
| `next-level-plans/` | Historical L0-L4, active L5, and future L6 roadmap files. | Keep; do not merge away milestone files because they represent separate decision records. |
| `phases/` | Historical UI implementation summaries from the earlier GSD planning layout. | Retain only as history; do not treat as active roadmap. |
| `docs/research/raw/` | Raw web/research evidence snapshots. | Keep as source evidence, but do not edit into narrative docs. |
| `docs/l6_scrape/` | L6 Egypt institution scrape outputs, manifests, raw artifacts, extracted text, and review CSV/XLSX files. | Keep grouped under this folder; generated outputs should stay out of the root docs surface. |
| `_legacy/root-outline-docs/` | Historical root markdown reports and setup/status files. | Archive only; keep the project root limited to current entry/config files. |
| `_legacy/root-smoke-screenshots/` | Historical root smoke screenshots. | Archive only; create fresh evidence for new releases. |
| `_legacy/browser-smoke/` | Historical browser smoke screenshots and local smoke process evidence. | Archive only; create fresh evidence for new releases. |
| `_legacy/runtime-logs/` | Historical root runtime logs from before the default moved to `data/runtime/logs/`. | Archive only; do not use as current runtime evidence. |
| `scripts/legacy/` | Old root batch wrappers. | Archive only; prefer maintained `scripts/` commands. |

## Completed Phase Summary

| Phase-Plan | Description | Current Location |
| --- | --- | --- |
| P1-S2 | CSS design system and dark mode | `.planning/sharia-compliance-chatbot/phases/01-ux-overhaul/p1-s2-SUMMARY.md` |
| P1-S3 | Static chat UI refinement | `.planning/sharia-compliance-chatbot/phases/01-ux-overhaul/p1-s3-SUMMARY.md` |
| P1-S4 | Browser chat interaction polish | `.planning/sharia-compliance-chatbot/phases/01-ux-overhaul/p1-s4-SUMMARY.md` |
| P1-S5 | UX overhaul completion summary | `.planning/sharia-compliance-chatbot/phases/01-ux-overhaul/p1-s5-SUMMARY.md` |
| P2-S1 | Loading and error states | `.planning/sharia-compliance-chatbot/phases/02-loading-error-states/P2-S1-SUMMARY.md` |
| P2-S2 | Compliance badges | `.planning/sharia-compliance-chatbot/phases/02-compliance-badges/P2-S2-SUMMARY.md` |
| P2-S3 | Message persistence | `.planning/sharia-compliance-chatbot/phases/02-message-persistence/P2-S3-SUMMARY.md` |
| P2-S4 | Typewriter/code-review command work | `.planning/sharia-compliance-chatbot/phases/02-code-review-command/P2-S4-SUMMARY.md` |
| P2-S5 | Citation anchors and flyout | `.planning/sharia-compliance-chatbot/phases/02-citation-flyout/P2-S5-SUMMARY.md` |
| P2-S6 | Multi-turn threading | `.planning/sharia-compliance-chatbot/phases/02-multi-turn-threading/P2-S6-SUMMARY.md` |

## Guardrails

- Keep `.agents`, `.bob`, `.cline`, `.trae`, `.claude`, and `.kiro` in place.
- Do not move raw scrape binaries or review workbooks into the root directory.
- Do not put historical reports, old screenshots, or legacy script wrappers back in the project root.
- Do not put runtime logs back in the root `logs/` folder; use `LOG_DIR` or the default `data/runtime/logs/`.
- Do not merge milestone plans into one large document; use the index files to connect them.
- Do not present generated scrape artifacts as reviewed Sharia authority.
- Keep historical planning marked as historical when it predates the current source-governed architecture.
