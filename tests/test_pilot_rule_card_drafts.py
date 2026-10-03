"""The V1.6 pilot draft cards load, stay pending, and can never reach the runtime."""
from pathlib import Path

from src.governance.rule_cards import approved_rule_cards, load_rule_cards

DRAFTS = Path(__file__).resolve().parents[1] / "data" / "rule_cards" / "pilot-draft-cards.yaml"


def test_pilot_drafts_load_and_none_is_runtime_eligible():
    cards = load_rule_cards(DRAFTS)
    assert {card.rule_id for card in cards} == {
        "instalment-plan-financier-v1",
        "late-payment-charge-beneficiary-v1",
        "rescheduling-added-margin-v1",
        "insurance-leg-v1",
        "early-settlement-rebate-v1",
    }
    assert approved_rule_cards(DRAFTS) == ()
    for card in cards:
        assert card.status == "draft"
        assert card.scholar_signoff.decision == "pending"
        assert card.precedence_note is None  # O1 is unanswered; approval must state it.
        assert set(card.unknown_fact_questions) == set(card.material_facts)


def test_iphone_case_asks_who_provides_the_plan():
    card = next(c for c in load_rule_cards(DRAFTS) if c.rule_id == "instalment-plan-financier-v1")
    assert card.unknown_fact_question.startswith("Who provides the instalment plan")
