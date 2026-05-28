import os
from typing import Optional
from src.models.query_intent import (
    ResolvedQueryIntent,
    ContractClassification,
    ClauseClassification,
    LegalClassification,
    ScoredToken
)

# Feature flag for migration, default to False to keep baseline passing
USE_LAYERED_EXTRACTOR = os.getenv("USE_LAYERED_EXTRACTOR", "false").lower() == "true"
INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.45"))

class LayeredScenarioExtractor:
    def __init__(self):
        # We will initialize the concept graph connection here in Part 3
        pass
        
    def extract_intent(self, query: str) -> ResolvedQueryIntent:
        """
        Classify-first scenario extraction.
        Analyzes the query in 3 layers: Contract, Clause, and Legal.
        """
        # --- Mocked extraction logic for TDD baseline ---
        # In a full implementation, this uses the Concept Graph (Part 3) 
        # and specialized NLP/LLM routing.
        
        from src.models.concept_graph import RoutingWeightStore
        
        contract = ContractClassification.UNCLEAR
        clause = ClauseClassification.UNCLEAR
        legal = LegalClassification.UNCLEAR
        confidence = 0.0
        
        # Integration with Concept Graph (Layer 2)
        store = RoutingWeightStore()
        
        # We find the highest weighted contract and clause
        contract_scores = {}
        clause_scores = {}
        
        for term in query.split():
            # In a full implementation, we'd use N-grams and token normalization here
            for c in ContractClassification:
                w = store.get_weight(term, c.value)
                if w > 0:
                    contract_scores[c] = max(contract_scores.get(c, 0), w)
                    
            for cl in ClauseClassification:
                w = store.get_weight(term, cl.value)
                if w > 0:
                    clause_scores[cl] = max(clause_scores.get(cl, 0), w)
                    
        if contract_scores:
            contract = max(contract_scores, key=contract_scores.get)
            confidence = contract_scores[contract]
            
        if clause_scores:
            clause = max(clause_scores, key=clause_scores.get)
            
        # Specific TDD logic for legal routing based on combined terms
        if contract == ContractClassification.ISTISNA and clause == ClauseClassification.DELAY_PENALTY:
            legal = LegalClassification.PERMISSIBLE_WITH_CONDITIONS
        elif contract == ContractClassification.QARD and clause == ClauseClassification.DELAY_PENALTY:
            legal = LegalClassification.PROHIBITED
        elif contract == ContractClassification.MURABAHA and clause == ClauseClassification.BINDING_PROMISE:
            legal = LegalClassification.PERMISSIBLE_WITH_CONDITIONS
            
        trigger = None
        if confidence < INTENT_CONFIDENCE_THRESHOLD:
            trigger = "CONFIDENCE_TOO_LOW"
            
        return ResolvedQueryIntent(
            contract_family=contract,
            clause_type=clause,
            legal_context=legal,
            confidence_score=confidence,
            clarification_trigger=trigger
        )
