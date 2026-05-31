import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GoldCase:
    id: str
    query_ar: str
    query_en: str
    expected_contract_family: str
    expected_standards: List[str]
    expected_ruling_direction: str
    critical_misclassification_risk: str
    source_authority: str

class GoldSet:
    def __init__(self, cases_path: Optional[Path] = None):
        if cases_path is None:
            cases_path = Path(__file__).parent / "cases.json"
        
        with open(cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.tier_1 = [GoldCase(**c) for c in data.get("tier_1_authoritative", [])]
        self.tier_2 = [GoldCase(**c) for c in data.get("tier_2_boundary", [])]
        
    def get_tier_1_cases(self) -> List[GoldCase]:
        return self.tier_1

    def get_tier_2_cases(self) -> List[GoldCase]:
        return self.tier_2
        
    def get_case(self, case_id: str) -> Optional[GoldCase]:
        for c in self.tier_1 + self.tier_2:
            if c.id == case_id:
                return c
        return None
