from datetime import datetime, UTC

import pytest

from src.chatbot.described_operation_facts import extract_operation_facts, reconcile_operation_facts
from src.models.evidence import Money

NOW = datetime(2026, 9, 30, tzinfo=UTC)


def extract(text, version=1, session="s1", transaction="purchase"):
    return extract_operation_facts(text, session_id=session, transaction_id=transaction,
                                   turn_id=f"turn-{version}", version=version, recorded_at=NOW)


def slots(snapshot):
    return {fact.slot: fact for fact in snapshot.facts}


@pytest.mark.parametrize("text", [
    "I want to buy an iPhone with a deposit of EGP 5,000 and 12 x EGP 3,000.",
    "عايز اشتري آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه.",
    "عايز iPhone بمقدم EGP 5000 و12 x EGP 3000",
    "I bought an iPhone, paid EGP 5,000 down, and owe EGP 3,000 monthly for 12 months. Is it halal?",
])
def test_iphone_story_extracts_supported_slots_without_inventing_price(text):
    values = slots(extract(text))
    assert values["asset"].value == "iPhone"
    assert values["down_payment"].value == Money(amount=5000, currency="EGP")
    assert values["instalment_count"].value == 12
    assert values["instalment_amount"].value == Money(amount=3000, currency="EGP")
    for slot in ("cash_price", "financed_or_final_price", "financing_party", "contract_family"):
        assert values[slot].status == "unknown"
    assert values["down_payment"].source.exact_text == text
    assert values["down_payment"].source.session_id == "s1"


def test_first_money_figure_is_not_cash_price():
    values = slots(extract("I want an iPhone for EGP 5000, paying 12 x EGP 3000"))
    assert values["cash_price"].status == "unknown"
    assert values["down_payment"].status == "unknown"


def test_currency_is_not_assumed():
    values = slots(extract("I want an iPhone, deposit 5000 and 12 x 3000"))
    assert values["down_payment"].status == "unknown"
    assert values["instalment_amount"].status == "unknown"
    assert values["instalment_count"].value == 12


def test_followup_retains_prior_facts_and_does_not_infer_mechanism():
    initial = extract("I want an iPhone, deposit EGP 5000 and 12 x EGP 3000")
    followup = extract("The financing party is Example Finance.", version=2)
    values = slots(reconcile_operation_facts(initial, followup))
    assert values["down_payment"].value.amount == 5000
    assert values["financing_party"].value == "Example Finance"
    assert values["contract_family"].status == "unknown"
    assert values["financing_party"].source.turn_id == "turn-2"


def test_followup_cannot_silently_overwrite_total():
    first = extract("The total payable is EGP 41000.")
    second = extract("The total payable is EGP 45000.", version=2)
    total = slots(reconcile_operation_facts(first, second))["financed_or_final_price"]
    assert total.status == "conflicting"
    assert total.value is None
    assert [item.value.amount for item in total.candidates] == [41000, 45000]
    assert [item.source.turn_id for item in total.candidates] == ["turn-1", "turn-2"]


@pytest.mark.parametrize("changes", [{"session": "other"}, {"transaction": "other"}, {"version": 1}])
def test_wrong_session_scope_or_revision_cannot_reconcile(changes):
    first = extract("deposit EGP 5000")
    options = {"version": 2} | changes
    second = extract("deposit EGP 6000", **options)
    with pytest.raises(ValueError):
        reconcile_operation_facts(first, second)


def test_repeated_same_value_does_not_create_conflict():
    first = extract("deposit EGP 5000")
    second = extract("deposit EGP 5000", version=2)
    assert slots(reconcile_operation_facts(first, second))["down_payment"].status == "user_reported"


def test_conflicting_assertions_in_one_turn_stay_conflicting():
    value = slots(extract("deposit EGP 5000, deposit EGP 6000"))["down_payment"]
    assert value.status == "conflicting"


@pytest.mark.parametrize("text", ["deposit EGP -5000", "deposit EGP 5,00", "deposit USD 5000 and total EGP 41000"])
def test_ambiguous_or_unsupported_amounts_remain_unknown(text):
    assert slots(extract(text))["down_payment"].status == "unknown"


@pytest.mark.parametrize("text", [
    "I did not pay a deposit EGP 5000",
    "deposit EGP 5000 or EGP 6000",
    "مش هدفع مقدم 5000 جنيه",
    "مقدم 5000 جنيه أو 6000 جنيه",
])
def test_negated_and_alternative_amounts_are_not_asserted(text):
    assert slots(extract(text))["down_payment"].status == "unknown"


def test_currency_from_unrelated_sentence_is_not_inherited():
    values = slots(extract("My old cash price was EGP 1000. I now have deposit 200 and 12 x 50"))
    assert values["down_payment"].status == "unknown"
    assert values["instalment_amount"].status == "unknown"


@pytest.mark.parametrize("amount", ["5k", "5 million", "5 thousand", "5 000", "5000%", "5 ألف"])
def test_unsupported_amount_suffix_cannot_truncate_to_a_smaller_amount(amount):
    assert slots(extract(f"deposit EGP {amount}"))["down_payment"].status == "unknown"
