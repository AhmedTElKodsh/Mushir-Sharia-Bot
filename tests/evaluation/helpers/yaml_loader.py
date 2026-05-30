"""
Load, validate, and index all gold-set YAML cases.
Validates against schema.json before returning.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import jsonschema
import yaml

GOLD_SET_DIR = Path(__file__).parent.parent / "gold_set"
SCHEMA_PATH = GOLD_SET_DIR / "schema.json"

_REQUIRED_FIELDS = {
    "case_id", "query_ar", "query_en", "contract_family",
    "expected_standards", "expected_ruling", "forbidden_citations",
    "clarification_required", "risk_class", "severity", "authority",
}

_VALID_RULINGS = {"PERMISSIBLE", "PROHIBITED", "DISPUTED", "CLARIFY"}
_VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM"}
_VALID_FAMILIES = {
    "MURABAHA", "IJARA", "MUQAWALA", "MUSHARAKA", "MUDHARABA",
    "WAKALA", "KAFALA", "GENERAL_SHARIA", "AMBIGUOUS",
}


def load_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


def iter_gold_cases(
    severity_filter: str | None = None,
) -> Iterator[dict]:
    """
    Yield every gold-set case dict, optionally filtered by severity.
    Raises AssertionError if any YAML fails schema validation.
    """
    schema = load_schema()
    subdirs = (
        [GOLD_SET_DIR / severity_filter.lower()]
        if severity_filter
        else [GOLD_SET_DIR / d for d in ("critical", "high", "medium")]
    )
    for subdir in subdirs:
        for yaml_path in sorted(subdir.glob("*.yaml")):
            with yaml_path.open(encoding="utf-8") as f:
                case = yaml.safe_load(f)
            # Schema validation
            jsonschema.validate(instance=case, schema=schema)
            # Semantic validation
            _validate_case(case, yaml_path)
            yield case


def _validate_case(case: dict, source: Path) -> None:
    missing = _REQUIRED_FIELDS - case.keys()
    assert not missing, f"{source}: missing fields {missing}"
    assert case["expected_ruling"] in _VALID_RULINGS, (
        f"{source}: invalid ruling '{case['expected_ruling']}'"
    )
    assert case["severity"] in _VALID_SEVERITIES, (
        f"{source}: invalid severity '{case['severity']}'"
    )
    assert case["contract_family"] in _VALID_FAMILIES, (
        f"{source}: invalid contract family '{case['contract_family']}'"
    )


def cases_by_severity(severity: str) -> list[dict]:
    return list(iter_gold_cases(severity_filter=severity))


def cases_requiring_clarification() -> list[dict]:
    return [c for c in iter_gold_cases() if c["clarification_required"]]


def cases_with_forbidden_citations() -> list[dict]:
    return [c for c in iter_gold_cases() if c["forbidden_citations"]]
