"""Pytest collection guardrails for fast default gates."""
from pathlib import Path


def pytest_ignore_collect(collection_path, config):
    marker_expression = config.option.markexpr or ""
    if "integration" not in marker_expression and "smoke" not in marker_expression:
        if Path(str(collection_path)).name == "test_rag_smoke.py":
            return True
    return False
