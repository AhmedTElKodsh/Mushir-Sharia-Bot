import json
from pathlib import Path

import pytest

from src.chatbot.commercial_assessment import ScenarioExtractor, StandardsRouter
from src.models.commercial import ContractFamily, SourceFamily


pytestmark = pytest.mark.service

GOLD_EVAL_PATH = Path("tests/data/gold_eval_set.json")
APPROVED_SIGNOFF_PREFIX = "Dr. "


def _cases():
    return json.loads(GOLD_EVAL_PATH.read_text(encoding="utf-8"))


def test_gold_eval_set_is_present_and_schema_valid():
    cases = _cases()

    assert cases
    required = {
        "case_id",
        "query_ar",
        "query_en",
        "contract_type",
        "party_role",
        "ruling",
        "applicable_standards",
        "forbidden_standards",
        "conditions",
        "scholar_sign_off",
    }
    for case in cases:
        assert required <= set(case)
        assert case["applicable_standards"]


def test_gold_eval_set_blocks_launch_until_scholar_signoff():
    cases = _cases()

    assert any(
        not str(case["scholar_sign_off"]).startswith(APPROVED_SIGNOFF_PREFIX)
        for case in cases
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["case_id"])
def test_routing_accuracy_skeleton_uses_expected_candidate_standards(case):
    query = f"{case['query_en']} {case['query_ar']}"
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    expected_family = ContractFamily(case["contract_type"])
    assert scenario.contract_family == expected_family
    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert set(case["applicable_standards"]) <= set(route.candidate_standards)
    assert set(case["forbidden_standards"]).isdisjoint(route.candidate_standards)
