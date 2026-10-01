"""Local scripted EN/AR conversation acceptance; no live model assertions."""
from unittest.mock import Mock

import pytest

from src.models.evidence import DecisionReviewRow
from src.models.ruling import ComplianceStatus
from tests.test_described_operation_flow import STORY, service


def facts(answer):
    return {f.slot: f for f in DecisionReviewRow.model_validate(answer.metadata["decision_review"]).fact_snapshot.facts}


@pytest.mark.parametrize("query,language", [
    (STORY + " Answer in Arabic.", "ar"),
    ("أريد شراء آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه. أجب بالإنجليزية", "en"),
    ("أريد شراء آيفون بمقدم 5000 جنيه و12 قسط كل قسط 3000 جنيه", "ar"),
])
def test_requested_language_and_standard_arabic_preserve_equivalent_facts(query, language):
    answer = service().answer(query, session_id="s")
    assert answer.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert answer.metadata["response_language"] == language
    assert answer.metadata["decision_trace"]["understood_as"]["language"] == language
    assert facts(answer)["down_payment"].value.amount == 5000
    assert facts(answer)["instalment_count"].value == 12


@pytest.mark.parametrize("first,reply,language", [
    (STORY, "المحل نفسه", "ar"),
    (STORY, "The store itself. Answer in Arabic", "ar"),
    ("اشتريت آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه", "Reply in English: Contact", "en"),
])
def test_language_switch_preserves_facts(first, reply, language):
    app = service()
    before = app.answer(first, session_id="s")
    after = app.answer(reply, session_id="s")
    assert after.metadata["response_language"] == language
    assert facts(after)["down_payment"].value == facts(before)["down_payment"].value
    assert facts(after)["financing_party"].status == "user_reported"
    assert facts(after)["contract_family"].status == "unknown"


@pytest.mark.parametrize("query,reply", [
    ("Help me with financing", "My purchase"),
    ("ساعدني في التقسيط", "أريد فهم معاملة شراء تخصني"),
])
def test_broad_request_discovers_purpose_then_one_material_question(query, reply):
    app = service()
    first = app.answer(query, session_id="s")
    assert first.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert first.metadata["decision_trace"]["decided_by"]["reason_code"] == "purpose_needed"
    assert first.answer.count("?") + first.answer.count("؟") == 1
    next_answer = app.answer(reply, session_id="s")
    assert next_answer.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert "store" in next_answer.answer or "المحل" in next_answer.answer
    assert next_answer.answer.count("?") + next_answer.answer.count("؟") == 1
    app.retriever.retrieve.assert_not_called()


@pytest.mark.parametrize("reply", [
    "Contact; the cash price is EGP 39000; the total payable is EGP 41000.",
    "كونتكت؛ السعر النقدي 39000 جنيه؛ السعر النهائي 41000 جنيه.",
])
def test_compound_reply_retains_all_material_assertions(reply):
    app = service()
    app.answer(STORY, session_id="s")
    answer = app.answer(reply, session_id="s")
    snapshot = facts(answer)
    assert snapshot["cash_price"].value.amount == 39000
    assert snapshot["financed_or_final_price"].value.amount == 41000
    assert snapshot["financing_party"].status == "user_reported"
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA


@pytest.mark.parametrize("slot,reply,expected", [
    ("cash_price", "39000", 39000), ("cash_price", "٣٩٠٠٠", 39000),
    ("financed_or_final_price", "41000", 41000), ("financed_or_final_price", "٤١٠٠٠", 41000),
    ("down_payment", "5000", 5000), ("down_payment", "٥٠٠٠", 5000),
    ("instalment_amount", "3000", 3000), ("instalment_amount", "٣٠٠٠", 3000),
    ("instalment_count", "12", 12), ("instalment_count", "١٢", 12),
])
def test_unambiguous_short_reply_binds_only_pending_field(slot, reply, expected):
    app = service()
    app.answer(STORY, session_id="s")
    state = app.session_store.get_session("s")
    state.metadata["described_operation"]["pending_slot"] = slot
    answer = app.answer(reply, session_id="s")
    fact = facts(answer)[slot]
    assert fact.status == "user_reported"
    assert (fact.value.amount if hasattr(fact.value, "amount") else fact.value) == expected


@pytest.mark.parametrize("slot,en,ar,value", [
    ("down_payment", "deposit EGP 6000", "المقدم 6000 جنيه", 6000),
    ("cash_price", "cash price EGP 42000", "السعر النقدي 42000 جنيه", 42000),
    ("financed_or_final_price", "total payable EGP 45000", "السعر النهائي 45000 جنيه", 45000),
    ("instalment_amount", "instalment amount EGP 3200", "قيمة القسط 3200 جنيه", 3200),
    ("instalment_count", "instalment count 15", "عدد الأقساط 15", 15),
    ("financing_party", "financing party is Shop B", "جهة التمويل هي شركة ب", None),
])
@pytest.mark.parametrize("language", ["en", "ar"])
def test_explicit_correction_supersedes_active_fact_and_preserves_history(slot, en, ar, value, language):
    app = service()
    first = app.answer(STORY + " The financing party is Shop A. The cash price is EGP 39000. The total payable is EGP 41000.", session_id="s")
    correction = ("Correction: " + en) if language == "en" else ("تصحيح: " + ar)
    answer = app.answer(correction, session_id="s")
    row = DecisionReviewRow.model_validate(answer.metadata["decision_review"])
    active = facts(answer)[slot]
    assert active.status == "user_reported"
    if value:
        assert (active.value.amount if hasattr(active.value, "amount") else active.value) == value
    assert len(row.fact_resolutions) == 1
    assert row.fact_resolutions[0].basis == "explicit_user_correction"
    assert row.fact_resolutions[0].previous_fact == facts(first)[slot]
    # Old persisted working rows retain their original assertion.
    assert app.session_store.get_session("s").metadata["operation_review_rows"][0]["fact_snapshot"] == first.metadata["decision_review"]["fact_snapshot"]


@pytest.mark.parametrize("reply", ["I will not share the financier", "I cannot access the agreement",
    "لن أشارك جهة التمويل", "لا أستطيع الوصول إلى العقد", "I don't know", "مش عارف"])
def test_refusal_or_inaccessible_evidence_stops_repeating_question(reply):
    app = service()
    app.answer(STORY, session_id="s")
    for _ in range(2):
        answer = app.answer(reply, session_id="s")
        assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
        assert answer.clarification_question is None
        assert facts(answer)["financing_party"].status == "unknown"
        assert "seller" in answer.answer or "البائع" in answer.answer


@pytest.mark.parametrize("purchase,confirmation", [
    ("I bought a laptop with deposit EGP 1000 and 6 x EGP 2000", "Yes"),
    ("اشتريت لابتوب بمقدم ١٠٠٠ جنيه و٦ قسط كل قسط ٢٠٠٠ جنيه", "نعم"),
])
def test_ambiguous_purchase_requires_confirmation_and_isolates_facts(purchase, confirmation):
    app = service()
    before = app.answer(STORY + " The financing party is Shop A.", session_id="s")
    pending = app.answer(purchase, session_id="s")
    assert pending.metadata["decision_trace"]["decided_by"]["reason_code"] == "scenario_switch_confirmation"
    assert facts(pending)["down_payment"].value.amount == 5000
    after = app.answer(confirmation, session_id="s")
    assert facts(after)["down_payment"].value.amount == 1000
    assert facts(after)["financing_party"].status == "unknown"
    assert facts(after)["asset"].scope != facts(before)["asset"].scope
    assert after.metadata["decision_review"]["query"] == confirmation
    assert facts(after)["down_payment"].source.exact_text == purchase
    assert facts(after)["down_payment"].source.turn_id == pending.metadata["decision_review"]["turn_id"]


@pytest.mark.parametrize("unknown", ["I don't know", "مش عارف"])
def test_unknown_purchase_switch_does_not_repeat_or_merge(unknown):
    app = service()
    app.answer(STORY, session_id="s")
    app.answer("I bought a laptop with deposit EGP 1000 and 6 x EGP 2000", session_id="s")
    answer = app.answer(unknown, session_id="s")
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.clarification_question is None
    assert facts(answer)["down_payment"].value.amount == 5000
    assert answer.metadata["decision_trace"]["decided_by"]["gate"] == "scope"


@pytest.mark.parametrize("reply", ["Correction: maybe the deposit is EGP 6000", "تصحيح: ربما المقدم 6000 جنيه"])
def test_uncertain_correction_does_not_silently_supersede_user_history(reply):
    app = service()
    app.answer(STORY, session_id="s")
    answer = app.answer(reply, session_id="s")
    assert facts(answer)["down_payment"].status == "conflicting"
    assert answer.metadata["decision_review"]["fact_resolutions"] == []


@pytest.mark.parametrize("text", ["5000", "٥٠٠٠", "5000 USD", "٥٠٠٠ دولار"])
def test_short_amount_does_not_introduce_currency(text):
    from src.chatbot.described_operation import DescribedOperationService
    assert not DescribedOperationService._answers_pending(text, "cash_price", None)


@pytest.mark.parametrize("reply", ["The seller is Shop A; the financing party is Shop B.",
                                  "البائع هو محل أ؛ جهة التمويل هي شركة ب."])
def test_seller_is_not_substituted_for_explicit_financier(reply):
    app = service()
    app.answer(STORY, session_id="s")
    answer = app.answer(reply, session_id="s")
    fact = facts(answer)["financing_party"]
    assert fact.value in {"Shop B", "شركة ب"}
    assert facts(answer)["contract_family"].status == "unknown"


@pytest.mark.parametrize("story", [STORY, "اشتريت آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه"])
def test_conditional_subtotal_keeps_unknown_fees_and_total(story):
    answer = service().answer(story, session_id="s")
    assert "41000 EGP" in answer.answer
    assert "conditional subtotal" in answer.answer or "مجموع مشروط" in answer.answer
    assert "fees are unknown" in answer.answer or "الرسوم الأخرى غير معلومة" in answer.answer
    assert facts(answer)["financed_or_final_price"].status == "unknown"


@pytest.mark.parametrize("reply", ["the seller or bank", "المحل أو البنك", "5000 USD", "٥٠٠٠ دولار"])
def test_ambiguous_financier_reply_never_becomes_identity(reply):
    app = service()
    app.answer(STORY, session_id="s")
    # Such text does not bind to the pending identity slot.
    from src.chatbot.described_operation import DescribedOperationService
    assert not DescribedOperationService._financier_reply(reply)


def test_paired_material_change_and_paraphrase_regression():
    answers = [service().answer(query, session_id="s") for query in [
        STORY, "My iPhone purchase has deposit EGP 5000 and 12 x EGP 3000.",
        STORY.replace("5,000", "6,000")]]
    assert facts(answers[0])["down_payment"].value == facts(answers[1])["down_payment"].value
    assert facts(answers[2])["down_payment"].value.amount == 6000
    assert [a.metadata["decision_trace"]["decided_by"] for a in answers] == [answers[0].metadata["decision_trace"]["decided_by"]] * 3
    assert "41000 EGP" in answers[0].answer and "42000 EGP" in answers[2].answer


def test_overlapping_company_sessions_never_share_facts_or_review_rows():
    app = service()
    one = app.answer(STORY + " The financing party is Contact.", session_id="one")
    two = app.answer(STORY.replace("5,000", "6,000") + " The financing party is Contact.", session_id="two")
    assert facts(one)["down_payment"].value.amount == 5000
    assert facts(two)["down_payment"].value.amount == 6000
    assert one.metadata["decision_review"]["review_id"] != two.metadata["decision_review"]["review_id"]
    assert {r["session_id"] for r in app.session_store.get_session("two").metadata["operation_review_rows"]} == {"two"}
