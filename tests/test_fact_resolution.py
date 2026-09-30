from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from src.chatbot.described_operation_facts import extract_operation_facts, reconcile_operation_facts, resolve_operation_fact
from src.models.evidence import FactCandidate, FactResolution, SourceProvenance

NOW = datetime(2026, 9, 30, tzinfo=UTC)


def snapshot(amount, version, session="s1", transaction="purchase"):
    return extract_operation_facts(f"total payable is EGP {amount}", session_id=session, transaction_id=transaction,
                                   turn_id=f"turn-{version}", version=version, recorded_at=NOW)


def conflict():
    return reconcile_operation_facts(snapshot(41000, 1), snapshot(45000, 2))


def test_resolution_keeps_conflict_and_uses_new_turn_as_user_reported():
    result, trace = resolve_operation_fact(conflict(), snapshot(41000, 3), slot="financed_or_final_price")
    assert trace.previous_fact.status == "conflicting"
    assert trace.selected_fact.status == "user_reported"
    assert trace.selected_fact.source.turn_id == "turn-3"
    assert trace.selected_fact in result.facts
    assert FactResolution.model_validate_json(trace.model_dump_json()) == trace


@pytest.mark.parametrize("options", [{"session": "other"}, {"transaction": "other"}, {"version": 2}])
def test_resolution_rejects_cross_session_scope_and_stale_revision(options):
    with pytest.raises(ValueError):
        resolve_operation_fact(conflict(), snapshot(41000, **({"version": 3} | options)), slot="financed_or_final_price")


def test_resolution_cannot_replace_an_observed_document_conflict():
    old = next(fact for fact in conflict().facts if fact.slot == "financed_or_final_price")
    source = SourceProvenance(scope=old.scope, exact_text="fixture document clause", span_id="s1",
                              document_class="transaction_specific_disclosure", capture=dict(
                                  source_id="fixture", url="https://example.org/fixture", captured_at=NOW,
                                  sha256="a" * 64, content_type="text/plain", language="en",
                                  access_status="accessible", document_version="v1"))
    old = old.model_copy(update={"candidates": (FactCandidate(status="observed", value=old.candidates[0].value, source=source), old.candidates[1])})
    selected = next(fact for fact in snapshot(41000, 3).facts if fact.slot == old.slot)
    with pytest.raises(ValidationError, match="own assertions"):
        FactResolution(previous_fact=old, selected_fact=selected)


def test_ordinary_known_fact_cannot_be_promoted_as_conflict_resolution():
    with pytest.raises(ValueError):
        resolve_operation_fact(snapshot(41000, 1), snapshot(45000, 2), slot="financed_or_final_price")
