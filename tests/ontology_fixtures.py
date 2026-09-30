"""Synthetic routing inputs only; never runtime seeds or approved Sharia rules."""


def late_penalty_payload():
    return {
        "concept_id": "late_penalty",
        "labels_en": ["late payment penalty"],
        "labels_ar": ["غرامة التأخير"],
        "conditional_rulings": [
            {"context": {"contract_type": "istisna", "party_role": "contractor"},
             "ruling": "CONDITIONAL",
             "conditions": ["contractor is the delaying party", "penalty represents actual damage"],
             "applicable_standards": ["SS-11", "SS-05"],
             "scholar_notes": "SYNTHETIC TEST INPUT: no approval or substantive ruling authority"},
            {"context": {"contract_type": "murabaha", "party_role": "unknown"},
             "ruling": "INSUFFICIENT_DATA", "conditions": [],
             "applicable_standards": ["SS-19", "SS-28"],
             "scholar_notes": "SYNTHETIC TEST INPUT: verifies route union only"},
        ],
    }
