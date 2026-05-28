import pytest
from src.governance.propagation_engine import PropagationEngine, ScholarFeedback
from src.models.concept_graph import RoutingWeightStore, ChunkSignalOverlay
from src.models.query_intent import ContractClassification

@pytest.fixture
def empty_store():
    store = RoutingWeightStore()
    # Clear the baseline graph for isolated testing
    store._graph = {}
    return store

@pytest.fixture
def signal_overlay():
    return ChunkSignalOverlay()

@pytest.mark.unit
def test_scholar_feedback_updates_concept_weight(empty_store, signal_overlay):
    engine = PropagationEngine(empty_store, signal_overlay)
    
    # Simulate a query where "غرامة" was misclassified as DEBT, 
    # but the scholar corrects it to ISTISNA
    feedback = ScholarFeedback(
        query_id="q123",
        scholar_id="dr_ahmed",
        original_query="غرامة",
        corrected_contract=ContractClassification.ISTISNA
    )
    
    # Assert weight before feedback is 0.0
    assert empty_store.get_weight("غرامة", ContractClassification.ISTISNA.value) == 0.0
    
    engine.propagate(feedback)
    
    # Assert weight after feedback increased by learning_rate (0.05)
    new_weight = empty_store.get_weight("غرامة", ContractClassification.ISTISNA.value)
    assert new_weight == 0.05
    
    # Verify provenance was tracked
    edge = empty_store._graph["غرامة"][ContractClassification.ISTISNA.value]
    assert edge.provenance == "scholar_correction_dr_ahmed_q123"

@pytest.mark.unit
def test_scholar_feedback_updates_chunk_signals(empty_store, signal_overlay):
    engine = PropagationEngine(empty_store, signal_overlay)
    
    # Initial signals are 1.0 (baseline multiplier)
    assert signal_overlay.get_signal("chunk_good_1") == 1.0
    assert signal_overlay.get_signal("chunk_bad_1") == 1.0
    
    feedback = ScholarFeedback(
        query_id="q456",
        scholar_id="dr_fatima",
        promoted_chunk_ids=["chunk_good_1"],
        demoted_chunk_ids=["chunk_bad_1"]
    )
    
    engine.propagate(feedback)
    
    # Assert chunk_good_1 was boosted (1.0 + 0.05)
    assert signal_overlay.get_signal("chunk_good_1") == 1.05
    
    # Assert chunk_bad_1 was suppressed (1.0 - 0.05)
    assert signal_overlay.get_signal("chunk_bad_1") == 0.95
