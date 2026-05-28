from dataclasses import dataclass
from typing import Optional, List
from src.models.concept_graph import RoutingWeightStore, ChunkSignalOverlay
from src.models.query_intent import ContractClassification, ClauseClassification

@dataclass
class ScholarFeedback:
    query_id: str
    scholar_id: str
    corrected_contract: Optional[ContractClassification] = None
    corrected_clause: Optional[ClauseClassification] = None
    promoted_chunk_ids: List[str] = None
    demoted_chunk_ids: List[str] = None
    original_query: str = ""
    
    def __post_init__(self):
        if self.promoted_chunk_ids is None:
            self.promoted_chunk_ids = []
        if self.demoted_chunk_ids is None:
            self.demoted_chunk_ids = []


class PropagationEngine:
    """
    Consumes scholar feedback and propagates it backward into the 
    Concept Graph (Routing weights) and Retrieval layer (Chunk signals).
    """
    
    def __init__(self, weight_store: RoutingWeightStore, signal_overlay: ChunkSignalOverlay):
        self.weight_store = weight_store
        self.signal_overlay = signal_overlay
        self.learning_rate = 0.05  # As requested: "Start conservative at 0.05"
        
    def propagate(self, feedback: ScholarFeedback):
        provenance = f"scholar_correction_{feedback.scholar_id}_{feedback.query_id}"
        
        # 1. Update Concept Weights
        if feedback.original_query:
            terms = feedback.original_query.split()
            
            for term in terms:
                if feedback.corrected_contract:
                    self.weight_store.update_weight(
                        term=term, 
                        concept=feedback.corrected_contract.value, 
                        delta=self.learning_rate, 
                        provenance=provenance
                    )
                if feedback.corrected_clause:
                    self.weight_store.update_weight(
                        term=term, 
                        concept=feedback.corrected_clause.value, 
                        delta=self.learning_rate, 
                        provenance=provenance
                    )
                    
        # 2. Update Chunk Signals (Post-Retrieval Boost/Suppress)
        # Promoted chunks get a positive multiplier boost
        for chunk_id in feedback.promoted_chunk_ids:
            current_signal = self.signal_overlay.get_signal(chunk_id)
            self.signal_overlay.set_signal(chunk_id, current_signal + self.learning_rate)
            
        # Demoted chunks get a negative multiplier penalty
        for chunk_id in feedback.demoted_chunk_ids:
            current_signal = self.signal_overlay.get_signal(chunk_id)
            # Ensure it doesn't drop below 0
            new_signal = max(0.0, current_signal - self.learning_rate)
            self.signal_overlay.set_signal(chunk_id, new_signal)
