"""Pytest collection guardrails for fast default gates."""
from pathlib import Path

import pytest


# Gold-set expectations that wait for a scholar decision.
# Code must not be changed to satisfy them; strict=True fails the run the moment
# one starts passing, so a restated label or a regression cannot slip by silently.
_GENERIC_MECHANISM = (
    "Pending scholar adjudication: generic wording no longer supplies a contract family; "
    "see _bmad-output/implementation-artifacts/mechanism-label-review.json."
)
PENDING_GOLD_EXPECTATIONS = {
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


@pytest.fixture(autouse=True)
def isolated_runtime_stores(tmp_path, monkeypatch):
    """No app test may open the operator's review history or remote mirror."""
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "reviews.sqlite3"))
    monkeypatch.setenv("DECISION_REVIEW_ARCHIVE_PATH", str(tmp_path / "archive.sqlite3"))
    for key in ("DECISION_REVIEW_DATABASE_URL", "DATABASE_URL", "SPACE_ID", "SPACE_HOST"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DECISION_REVIEW_REQUIRE_MIRROR", "false")
