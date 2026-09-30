"""Evidence boundaries and lossless wire records, independent of providers."""
import pytest
from pydantic import ValidationError

from src.models.evidence import (
    FACT_SLOTS, AnswerDecision, CaptureManifest, DecisionReviewRow, Dossier,
    EvidenceScope, FactObservation, FactSnapshot, Money, SourceProvenance,
    UserTurnProvenance,
)

NOW = "2026-09-30T12:00:00+02:00"


def scope(lane="personal"):
    return EvidenceScope(lane=lane, transaction_id="purchase-1" if lane == "personal" else None,
                         entity_id="company-1" if lane == "company" else None,
                         document_scope="schedule" if lane == "personal" else "template")


def turn():
    return UserTurnProvenance(session_id="s1", turn_id="t1", exact_text="  5000 down, 12 x 3000  ",
                              recorded_at=NOW, version=1, scope=scope())


def source(document_class="provider_standard_terms", **capture_changes):
    capture = dict(source_id="source-1", url="https://example.org/terms", captured_at=NOW,
                   sha256="a" * 64, content_type="text/html", language="ar",
                   access_status="accessible", document_version="v1")
    capture.update(capture_changes)
    return SourceProvenance(capture=capture, document_class=document_class,
                            exact_text="  exact clause نص  ", span_id="p2", scope=scope("company"))


def fact(**changes):
    data = dict(slot="down_payment", scope=scope(), version=1, recorded_at=NOW,
                status="user_reported", value=Money(amount=5000, currency="EGP"), source=turn())
    data.update(changes)
    return FactObservation(**data)


def test_iphone_numbers_remain_separate_without_inference():
    facts = (fact(), fact(slot="instalment_count", value=12),
             fact(slot="instalment_amount", value=Money(amount=3000, currency="EGP")),
             fact(slot="financing_party", status="unknown", value=None, source=None,
                  unobserved_reason="in_customer_schedule"),
             fact(slot="financed_or_final_price", status="unknown", value=None, source=None,
                  unobserved_reason="in_customer_schedule"))
    snapshot = FactSnapshot(snapshot_id="f1", version=1, recorded_at=NOW, facts=facts)
    restored = FactSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored == snapshot
    assert restored.facts[0].source.exact_text == "  5000 down, 12 x 3000  "
    assert restored.facts[-1].value is None


@pytest.mark.parametrize("value", [False, 0, 0.0, True, "0", (False, 0, "text")])
def test_known_values_round_trip_without_coercion(value):
    original = fact(slot="rule_specific_fact", value=value)
    restored = FactObservation.model_validate_json(original.model_dump_json())
    assert type(restored.value) is type(value)
    assert restored.value == value


@pytest.mark.parametrize("reason", ["not_publicly_found", "login_gated", "access_blocked", "in_customer_schedule"])
@pytest.mark.parametrize("slot", FACT_SLOTS)
def test_every_slot_can_remain_unknown(slot, reason):
    item = fact(slot=slot, status="unknown", value=None, source=None, unobserved_reason=reason)
    assert FactObservation.model_validate_json(item.model_dump_json()) == item


def test_conflict_preserves_all_candidates():
    item = fact(slot="instalment_count", status="conflicting", value=None, source=None, candidates=[
        dict(status="user_reported", value=5000, source=turn()),
        dict(status="user_reported", value=6000, source=turn().model_copy(update={"turn_id": "t2", "version": 2})),
    ])
    assert [c.value for c in FactObservation.model_validate_json(item.model_dump_json()).candidates] == [5000, 6000]


@pytest.mark.parametrize("changes", [
    {"status": "unknown", "unobserved_reason": "login_gated"},
    {"status": "observed"}, {"version": True}, {"version": 0},
    {"recorded_at": "2026-09-30T12:00:00"}, {"extra": "not silently discarded"},
    {"value": float("nan")}, {"value": None}, {"slot": " "},
    {"status": "conflicting", "value": None, "source": None},
])
def test_malformed_facts_fail(changes):
    with pytest.raises(ValidationError):
        fact(**changes)


def test_authority_scope_and_mutation_boundaries():
    public = source()
    observed = fact(status="observed", scope=scope("company"), source=public)
    assert FactObservation.model_validate_json(observed.model_dump_json()) == observed
    for changes in ({"status": "user_reported"}, {"scope": scope()},
                    {"source": source("synthetic_counterfactual")},
                    {"source": source(access_status="login_gated")},
                    {"slot": "contract_family", "source": source("provider_claim")}):
        with pytest.raises(ValidationError):
            observed.model_copy(update=changes)
    with pytest.raises(ValidationError):
        observed.value = 6
    with pytest.raises(ValidationError):
        turn().model_copy(update={"scope": scope("company")})


@pytest.mark.parametrize("missing", ["source_id", "url", "captured_at", "sha256", "document_version"])
def test_missing_capture_provenance_fails(missing):
    data = source().capture.model_dump()
    del data[missing]
    with pytest.raises(ValidationError):
        CaptureManifest(**data)


@pytest.mark.parametrize("missing", ["exact_text", "span_id", "scope"])
def test_missing_span_provenance_fails(missing):
    data = source().model_dump()
    del data[missing]
    with pytest.raises(ValidationError):
        SourceProvenance(**data)


@pytest.mark.parametrize("document_class", ["marketing", "faq", "provider_standard_terms", "regulator_model",
    "transaction_specific_disclosure", "user_supplied_schedule", "donated_agreement", "synthetic_counterfactual", "provider_claim"])
def test_all_document_classes_serialize(document_class):
    item = source(document_class)
    assert SourceProvenance.model_validate_json(item.model_dump_json()) == item


def test_complete_dossier_round_trip_and_personal_boundary():
    public = source()
    item = Dossier(dossier_id="d1", entity_name="Company", aliases=["alias"], official_domain="example.org",
                   scope=scope("company"), document_version="v1", operation_id="op1",
                   published_offer_period="September 2026", roles=[dict(role="seller", party_id="c1", evidence=[public])],
                   link_graph=[dict(from_url="https://example.org", to_url=public.capture.url, relation="terms")],
                   public_buyer_journey=[dict(order=1, url=public.capture.url, description="Terms", access_status="accessible")],
                   capture_manifest=[public.capture], field_observations=[fact(status="observed", scope=scope("company"), source=public)],
                   older_versions=["v0"], conflicts=["prior price differs"],
                   analyst_verification=dict(reviewer_id="a1", recorded_at=NOW, decision="verified", notes="checked span"),
                   scholar_rule_mapping_review=dict(reviewer_id="s1", recorded_at=NOW, decision="pending", notes="unreviewed"))
    assert Dossier.model_validate_json(item.model_dump_json()) == item
    with pytest.raises(ValidationError):
        item.model_copy(update={"field_observations": [fact()]})


@pytest.mark.parametrize("decision", [
    dict(decision="CLARIFICATION_NEEDED", questions=["Who provides the instalment plan?"]),
    dict(decision="INSUFFICIENT_DATA", needed_documents_or_reviews=["Customer repayment schedule"]),
    dict(decision="ANSWER", answer="The user reports EGP 5000 down.", cited_claims=[dict(text="EGP 5000 down", sources=[turn()])]),
])
def test_decisions_and_review_rows_round_trip(decision):
    result = AnswerDecision(reason="Evidence boundary", gates=[dict(gate="material_fact", status="blocked", reason="financier unknown")], **decision)
    row = DecisionReviewRow(review_id="r1", request_id="req1", session_id="s1", turn_id="t1", version=1,
                            recorded_at=NOW, intent="described_operation", query="Is this permissible?",
                            fact_snapshot=FactSnapshot(snapshot_id="f1", version=1, recorded_at=NOW, facts=[fact()]),
                            decision=result, clarifying_turn=turn())
    assert DecisionReviewRow.model_validate_json(row.model_dump_json()) == row
    with pytest.raises(ValidationError):
        row.model_copy(update={"request_id": ""})


@pytest.mark.parametrize("data", [
    dict(decision="CLARIFICATION_NEEDED", questions=[]),
    dict(decision="CLARIFICATION_NEEDED", questions=["First?", "Second?"]),
    dict(decision="CLARIFICATION_NEEDED", questions=["Who?"], answer="Permissible"),
    dict(decision="INSUFFICIENT_DATA"),
    dict(decision="INSUFFICIENT_DATA", needed_documents_or_reviews=["review"], questions=["Who?"]),
    dict(decision="ANSWER", answer="unsupported"),
])
def test_invalid_decision_shapes_fail(data):
    with pytest.raises(ValidationError):
        AnswerDecision(reason="missing facts", **data)


@pytest.mark.parametrize("question", ["Who? What?", "Who?\nWhat", "- Who?", "Who"])
def test_one_string_cannot_hide_multiple_questions(question):
    with pytest.raises(ValidationError):
        AnswerDecision(decision="CLARIFICATION_NEEDED", reason="financier missing", questions=[question])


@pytest.mark.parametrize("value", [False, "12", 12.5, -1])
def test_instalment_count_is_a_nonnegative_integer(value):
    with pytest.raises(ValidationError):
        fact(slot="instalment_count", value=value)


def test_money_preserves_decimal_precision_and_rejects_float():
    amount = "12345678901234567890.123456789"
    money = Money(amount=amount, currency="EGP")
    restored = Money.model_validate_json(money.model_dump_json())
    assert str(restored.amount) == amount
    with pytest.raises(ValidationError):
        Money(amount=0.1, currency="EGP")


@pytest.mark.parametrize("document_class,access", [
    ("synthetic_counterfactual", "accessible"),
    ("provider_claim", "accessible"),
    ("provider_standard_terms", "access_blocked"),
])
def test_dossier_roles_cannot_bypass_evidence_authority(document_class, access):
    from src.models.evidence import DossierRole

    with pytest.raises(ValidationError):
        DossierRole(role="financier", party_id="c1", evidence=[source(document_class, access_status=access)])


@pytest.mark.parametrize("evidence", [source("synthetic_counterfactual"), source(access_status="login_gated")])
def test_answer_citations_enforce_source_admissibility(evidence):
    from src.models.evidence import CitedClaim
    with pytest.raises(ValidationError):
        CitedClaim(text="Unsupported assertion", sources=[evidence])


@pytest.mark.parametrize("location", ["fact", "conflict", "citation", "clarification"])
def test_review_rejects_foreign_session_provenance(location):
    foreign = turn().model_copy(update={"session_id": "another-session"})
    facts = [fact()]
    decision = AnswerDecision(decision="INSUFFICIENT_DATA", reason="missing evidence", needed_documents_or_reviews=["agreement"])
    if location == "fact":
        facts = [fact(source=foreign)]
    elif location == "conflict":
        facts = [fact(slot="instalment_count", status="conflicting", source=None, value=None, candidates=[
            dict(value=12, status="user_reported", source=turn()),
            dict(value=24, status="user_reported", source=foreign),
        ])]
    elif location == "citation":
        decision = AnswerDecision(decision="ANSWER", reason="reported fact", answer="12 payments",
                                  cited_claims=[dict(text="12 payments", sources=[foreign])])
    with pytest.raises(ValidationError, match="review session"):
        DecisionReviewRow(review_id="r", request_id="q", session_id="s1", turn_id="t1", version=1,
                          recorded_at=NOW, intent="described_operation", query="Is this allowed?",
                          fact_snapshot=FactSnapshot(snapshot_id="s", version=1, recorded_at=NOW, facts=facts),
                          decision=decision, clarifying_turn=foreign if location == "clarification" else None)


def test_snapshot_rejects_duplicate_active_slot():
    with pytest.raises(ValidationError, match="one active fact"):
        FactSnapshot(snapshot_id="s", version=1, recorded_at=NOW, facts=[fact(), fact()])


def test_unknown_fact_keeps_failed_access_attempt_without_asserting_value():
    capture = source(access_status="access_blocked").capture
    unknown = fact(status="unknown", value=None, source=None, unobserved_reason="access_blocked", access_attempts=[capture])
    restored = FactObservation.model_validate_json(unknown.model_dump_json())
    assert restored.access_attempts == (capture,)
    assert restored.value is None and restored.source is None


def test_dossier_rejects_conflicting_manifest_for_same_capture():
    capture = source().capture
    with pytest.raises(ValidationError, match="conflicting manifests"):
        Dossier(dossier_id="d", entity_name="Company", official_domain="example.org",
                scope=scope("company"), document_version="v1", operation_id="op",
                capture_manifest=[capture, capture.model_copy(update={"sha256": "b" * 64})])


def test_decision_rejects_duplicate_gate_results():
    gate = dict(gate="material_fact", status="blocked", reason="missing financier")
    with pytest.raises(ValidationError, match="at most one"):
        AnswerDecision(decision="INSUFFICIENT_DATA", reason="missing evidence",
                       needed_documents_or_reviews=["schedule"], gates=[gate, gate])
