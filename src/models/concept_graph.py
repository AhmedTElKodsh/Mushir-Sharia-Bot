from dataclasses import dataclass, field
from typing import Dict, List, Optional
from src.models.query_intent import ContractClassification, ClauseClassification

@dataclass
class EdgeWeight:
    weight: float
    provenance: str  # e.g., 'baseline', 'scholar_correction_123'
    
class RoutingWeightStore:
    def __init__(self):
        # Baseline static weights. In the future, this will be dynamically 
        # loaded and updated by the Bayesian prior nudges (RLHF loop).
        self._graph: Dict[str, Dict[str, EdgeWeight]] = {
            "مقاولات": {
                ContractClassification.ISTISNA.value: EdgeWeight(0.9, "baseline"),
                ContractClassification.IJARAH.value: EdgeWeight(0.2, "baseline")
            },
            "المقاولات": {
                ContractClassification.ISTISNA.value: EdgeWeight(0.9, "baseline"),
                ContractClassification.IJARAH.value: EdgeWeight(0.2, "baseline")
            },
            "غرامة": {
                ClauseClassification.DELAY_PENALTY.value: EdgeWeight(0.95, "baseline")
            },
            "القرض": {
                ContractClassification.QARD.value: EdgeWeight(0.95, "baseline")
            },
            "المرابحة": {
                ContractClassification.MURABAHA.value: EdgeWeight(0.95, "baseline")
            },
            "الوعد": {
                ClauseClassification.BINDING_PROMISE.value: EdgeWeight(0.9, "baseline")
            }
        }
        
    def get_weight(self, term: str, concept: str) -> float:
        """Get the weight of a term mapping to a specific concept."""
        if term in self._graph and concept in self._graph[term]:
            return self._graph[term][concept].weight
        return 0.0
        
    def update_weight(self, term: str, concept: str, delta: float, provenance: str):
        """Update a weight, bounded by LEARNING_RATE constraints from the Scholar Review Loop."""
        if term not in self._graph:
            self._graph[term] = {}
            
        current = self.get_weight(term, concept)
        new_weight = max(0.0, min(1.0, current + delta))
        self._graph[term][concept] = EdgeWeight(new_weight, provenance)

class ChunkSignalOverlay:
    """
    Applies post-retrieval boost/suppress signals to chunks without needing re-embedding.
    Used by the Hybrid Retrieval layer.
    """
    def __init__(self):
        # Stores chunk_id -> boost_multiplier
        self._signals: Dict[str, float] = {}
        
    def set_signal(self, chunk_id: str, multiplier: float):
        self._signals[chunk_id] = multiplier
        
    def get_signal(self, chunk_id: str) -> float:
        return self._signals.get(chunk_id, 1.0)
