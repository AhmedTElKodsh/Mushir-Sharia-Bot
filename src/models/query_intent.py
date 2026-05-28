from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, FrozenSet

class ContractClassification(Enum):
    ISTISNA = "ISTISNA"
    DEBT = "DEBT"
    MURABAHA = "MURABAHA"
    QARD = "QARD"
    IJARAH = "IJARAH"
    WAKALAH = "WAKALAH"
    MUDHARABAH = "MUDHARABAH"
    MUSHARAKAH = "MUSHARAKAH"
    KAFALAH = "KAFALAH"
    UNCLEAR = "UNCLEAR"

class ClauseClassification(Enum):
    DELAY_PENALTY = "DELAY_PENALTY"
    BINDING_PROMISE = "BINDING_PROMISE"
    PROFIT_DISTRIBUTION = "PROFIT_DISTRIBUTION"
    VARIABLE_BENCHMARK = "VARIABLE_BENCHMARK"
    DEFAULT = "DEFAULT"
    UNCLEAR = "UNCLEAR"

class LegalClassification(Enum):
    PERMISSIBLE = "PERMISSIBLE"
    PROHIBITED = "PROHIBITED"
    PERMISSIBLE_WITH_CONDITIONS = "PERMISSIBLE_WITH_CONDITIONS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNCLEAR = "UNCLEAR"

@dataclass(frozen=True)
class ScoredToken:
    token: str
    score: float
    layer: str  # e.g., 'contract', 'clause', 'legal'

AAOIFI_HINTS_BY_CONTRACT: Dict[ContractClassification, List[str]] = {
    ContractClassification.ISTISNA: ["SS-11", "SS-05"],
    ContractClassification.DEBT: ["FAS-30", "SS-19"],
    ContractClassification.QARD: ["SS-19", "SS-03"],
    ContractClassification.MURABAHA: ["SS-08"],
    ContractClassification.IJARAH: ["SS-09"]
}

@dataclass(frozen=True)
class ResolvedQueryIntent:
    contract_family: ContractClassification
    clause_type: ClauseClassification
    legal_context: LegalClassification
    tokens: FrozenSet[ScoredToken] = field(default_factory=frozenset)
    confidence_score: float = 0.0
    clarification_trigger: Optional[str] = None
    
    @property
    def aaoifi_hints(self) -> List[str]:
        return AAOIFI_HINTS_BY_CONTRACT.get(self.contract_family, [])
