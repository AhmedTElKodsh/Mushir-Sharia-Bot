"""
Root conftest for evaluation suite.
Registers all fixtures and parametrizes gold-set cases.
"""
from __future__ import annotations

import pytest

from helpers.yaml_loader import (
    cases_by_severity,
    cases_requiring_clarification,
    cases_with_forbidden_citations,
    iter_gold_cases,
)
from fixtures.pipeline import build_pipeline_under_test
from fixtures.scholar_review import ScholarReviewQueue
from fixtures.citation_detector import ForbiddenCitationDetector
from fixtures.calibration import CalibrationBucket


# ---------------------------------------------------------------------------
# Custom pytest marks
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line("markers", "critical_goldset: CRITICAL severity gold cases")
    config.addinivalue_line("markers", "high_goldset: HIGH severity gold cases")
    config.addinivalue_line("markers", "medium_goldset: MEDIUM severity gold cases")
    config.addinivalue_line("markers", "forbidden_citation: cases with forbidden_citations list")
    config.addinivalue_line("markers", "clarification_required: cases where clarification must fire")
    config.addinivalue_line("markers", "bilingual: bilingual parity cases")
    config.addinivalue_line("markers", "scholar_disagreement: cases with cross-scholar conflict")


# ---------------------------------------------------------------------------
# Parametrized fixtures per severity tier
# ---------------------------------------------------------------------------
def _case_id(case: dict) -> str:
    return case["case_id"]


def pytest_generate_tests(metafunc):
    """
    Dynamically parametrize based on which fixture name is requested.
    This runs before collection, so marks are applied per-parameter.
    """
    if "critical_case" in metafunc.fixturenames:
        cases = cases_by_severity("CRITICAL")
        metafunc.parametrize(
            "critical_case",
            cases,
            ids=[_case_id(c) for c in cases],
        )

    if "high_case" in metafunc.fixturenames:
        cases = cases_by_severity("HIGH")
        metafunc.parametrize(
            "high_case",
            cases,
            ids=[_case_id(c) for c in cases],
        )

    if "clarification_case" in metafunc.fixturenames:
        cases = cases_requiring_clarification()
        metafunc.parametrize(
            "clarification_case",
            cases,
            ids=[_case_id(c) for c in cases],
        )

    if "any_gold_case" in metafunc.fixturenames:
        cases = list(iter_gold_cases())
        metafunc.parametrize(
            "any_gold_case",
            cases,
            ids=[_case_id(c) for c in cases],
        )


# ---------------------------------------------------------------------------
# Session-scoped pipeline fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def pipeline_under_test():
    """Full pipeline; LLM calls mocked, vector store is in-memory test corpus."""
    pipeline = build_pipeline_under_test()
    yield pipeline
    pipeline.teardown()


# ---------------------------------------------------------------------------
# Function-scoped scholar review queue
# ---------------------------------------------------------------------------
@pytest.fixture
def scholar_review_queue():
    queue = ScholarReviewQueue()
    yield queue
    # After each test, assert queue was consumed if non-empty
    if queue.pending:
        pytest.fail(
            f"scholar_review_queue has {len(queue.pending)} unconsumed items: "
            f"{[e['case_id'] for e in queue.pending]}"
        )


# ---------------------------------------------------------------------------
# Session-scoped forbidden citation detector (stateless helper)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def forbidden_citation_detector():
    return ForbiddenCitationDetector()


# ---------------------------------------------------------------------------
# Session-scoped calibration bucket
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def confidence_calibration_bucket():
    bucket = CalibrationBucket()
    yield bucket
    # After full session: write ECE report
    bucket.write_report()
