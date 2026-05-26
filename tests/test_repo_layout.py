from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_planning_entrypoints_exist():
    required_paths = [
        ".planning/STATE.md",
        ".planning/sharia-compliance-chatbot/docs/index.md",
        ".planning/sharia-compliance-chatbot/docs/project-documentation.md",
        ".planning/sharia-compliance-chatbot/docs/AI_AGENT_PROJECT_HANDOFF.md",
        ".planning/sharia-compliance-chatbot/next-level-plans/README.md",
        "artifacts/l6_scrape/README.md",
        "scripts/legacy/README.md",
    ]

    for path in required_paths:
        assert (ROOT / path).exists(), path


def test_active_entry_docs_do_not_point_to_deleted_kiro_specs():
    active_docs = [
        ROOT / "README.md",
        ROOT / "project-context.md",
        ROOT / ".planning" / "STATE.md",
        ROOT / ".planning" / "sharia-compliance-chatbot" / "docs" / "AI_AGENT_PROJECT_HANDOFF.md",
        ROOT / ".planning" / "sharia-compliance-chatbot" / "docs" / "ai-project-brief.md",
        ROOT / ".planning" / "sharia-compliance-chatbot" / "docs" / "chatbot-architecture.md",
        ROOT / ".planning" / "sharia-compliance-chatbot" / "docs" / "project-documentation.md",
    ]

    stale_active_markers = [
        "First read project-context.md and .kiro/specs/sharia-compliance-chatbot",
        "| `.kiro/specs/sharia-compliance-chatbot/",
        "- `.kiro/specs/sharia-compliance-chatbot/",
        "**Design Document:** `.kiro/specs/sharia-compliance-chatbot/",
    ]
    for path in active_docs:
        text = path.read_text(encoding="utf-8")
        for marker in stale_active_markers:
            assert marker not in text, f"{path}: {marker}"
