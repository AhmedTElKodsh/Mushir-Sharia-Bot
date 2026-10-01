"""Pytest collection guardrails for fast default gates."""
from pathlib import Path

import pytest


# Gold-set expectations that wait for a scholar or product owner to restate them.
# Code must not be changed to satisfy them; strict=True fails the run the moment
# one starts passing, so a restated label or a regression cannot slip by silently.
_WITHHELD_VERDICT = (
    "Pending scholar restatement: no rule card is scholar-approved, so the judgment gate "
    "withholds this verdict (deferred-work ledger item 1)."
)
_GENERIC_MECHANISM = (
    "Pending scholar adjudication: generic wording no longer supplies a contract family; "
    "see _bmad-output/implementation-artifacts/mechanism-label-review.json."
)
PENDING_GOLD_EXPECTATIONS = {
    "test_ruling_correctness": {
        case_id: _WITHHELD_VERDICT
        for case_id in ("GC-003", "GC-005", "GC-007", "GC-008", "GC-009",
                        "GC-010", "GC-012", "GC-016", "GC-017", "GC-019")
    },
    "test_routing_accuracy_skeleton_uses_expected_candidate_standards": {
        "TC-F1": _GENERIC_MECHANISM,
        "TC-G1": _GENERIC_MECHANISM,
    },
}


def pytest_ignore_collect(collection_path, config):
    marker_expression = config.option.markexpr or ""
    if "integration" not in marker_expression and "smoke" not in marker_expression:
        if Path(str(collection_path)).name == "test_rag_smoke.py":
            return True
    return False


def pytest_collection_modifyitems(config, items):
    for item in items:
        pending = PENDING_GOLD_EXPECTATIONS.get(getattr(item, "originalname", item.name), {})
        callspec = getattr(item, "callspec", None)
        reason = pending.get(callspec.id) if callspec else None
        if reason:
            item.add_marker(pytest.mark.xfail(reason=reason, strict=True))
