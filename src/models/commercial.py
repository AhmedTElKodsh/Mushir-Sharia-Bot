"""Structured commercial-process models for the L6 planning direction.

These models are intentionally conservative. They provide an auditable shape
for scenario extraction, standards routing, rule traces, and non-fatwa verdicts
without claiming that the full rules-first evaluator is implemented.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QuestionType(str, Enum):
    PERMISSIBILITY = "permissibility"
    ACCOUNTING = "accounting"
    GOVERNANCE = "governance"
    EXPLANATION = "explanation"
    UNKNOWN = "unknown"


class ContractFamily(str, Enum):
    MURABAHA = "murabaha"
    IJARAH = "ijarah"
    SALAM = "salam"
    ISTISNA = "istisna"
    TAWARRUQ = "tawarruq"
    QARD = "qard"
    KAFALA = "kafala"
    WAKALA = "wakala"
    SUKUK = "sukuk"
    MUSHARAKA = "musharaka"
    MUDARABA = "mudaraba"
    UNKNOWN = "unknown"


class SourceFamily(str, Enum):
    SHARIA_STANDARD = "sharia_standard"
    FAS = "fas"
    GOVERNANCE = "governance"
    ETHICS = "ethics"
    AUDITING = "auditing"
    FATWA = "fatwa"
    LOCAL_OVERLAY = "local_overlay"
    UNKNOWN = "unknown"


class VerdictStatus(str, Enum):
    LIKELY_PERMISSIBLE = "likely_permissible"
    LIKELY_IMPERMISSIBLE = "likely_impermissible"
    CONDITIONALLY_PERMISSIBLE = "conditionally_permissible"
    REQUIRES_CLARIFICATION = "requires_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFER_TO_SCHOLAR = "refer_to_scholar"


@dataclass
class TransactionScenario:
    """Structured facts extracted from a user commercial-process question."""

    question_type: QuestionType = QuestionType.UNKNOWN
    contract_family: ContractFamily = ContractFamily.UNKNOWN
    parties: List[str] = field(default_factory=list)
    asset: Optional[str] = None
    cash_flows: List[Dict[str, Any]] = field(default_factory=list)
    asset_flows: List[Dict[str, Any]] = field(default_factory=list)
    ownership_sequence: Optional[str] = None
    possession_sequence: Optional[str] = None
    risk_bearing: Optional[str] = None
    profit_basis: Optional[str] = None
    payment_terms: Optional[str] = None
    late_payment_terms: Optional[str] = None
    penalty_beneficiary: Optional[str] = None
    agency_roles: List[str] = field(default_factory=list)
    guarantees: List[str] = field(default_factory=list)
    collateral: List[str] = field(default_factory=list)
    jurisdiction: Optional[str] = None
    madhhab_or_board_context: Optional[str] = None
    missing_facts: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_type": self.question_type.value,
            "contract_family": self.contract_family.value,
            "parties": self.parties,
            "asset": self.asset,
            "cash_flows": self.cash_flows,
            "asset_flows": self.asset_flows,
            "ownership_sequence": self.ownership_sequence,
            "possession_sequence": self.possession_sequence,
            "risk_bearing": self.risk_bearing,
            "profit_basis": self.profit_basis,
            "payment_terms": self.payment_terms,
            "late_payment_terms": self.late_payment_terms,
            "penalty_beneficiary": self.penalty_beneficiary,
            "agency_roles": self.agency_roles,
            "guarantees": self.guarantees,
            "collateral": self.collateral,
            "jurisdiction": self.jurisdiction,
            "madhhab_or_board_context": self.madhhab_or_board_context,
            "missing_facts": self.missing_facts,
            "uncertainties": self.uncertainties,
        }


@dataclass
class StandardsRoute:
    """Source-family route selected before answer generation."""

    primary: List[SourceFamily]
    secondary: List[SourceFamily] = field(default_factory=list)
    candidate_standards: List[str] = field(default_factory=list)
    route_id: Optional[str] = None
    rationale: str = ""
    requires_rule_evaluation: bool = False
    unsupported_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": [family.value for family in self.primary],
            "secondary": [family.value for family in self.secondary],
            "candidate_standards": self.candidate_standards,
            "route_id": self.route_id,
            "rationale": self.rationale,
            "requires_rule_evaluation": self.requires_rule_evaluation,
            "unsupported_reason": self.unsupported_reason,
        }


@dataclass
class RuleEvaluation:
    """Deterministic rule-trace placeholder for supported future domains."""

    rule_id: Optional[str] = None
    rule_version: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)
    required_facts: List[str] = field(default_factory=list)
    missing_facts: List[str] = field(default_factory=list)
    evidence_requirements: List[str] = field(default_factory=list)
    outcome: str = "unknown"
    source_ids: List[str] = field(default_factory=list)
    conflict_flags: List[str] = field(default_factory=list)
    human_review_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "matched_rules": self.matched_rules,
            "required_facts": self.required_facts,
            "missing_facts": self.missing_facts,
            "evidence_requirements": self.evidence_requirements,
            "outcome": self.outcome,
            "source_ids": self.source_ids,
            "conflict_flags": self.conflict_flags,
            "human_review_flags": self.human_review_flags,
        }


@dataclass
class VerdictContract:
    """Non-fatwa assessment contract for L6-style outputs."""

    verdict: VerdictStatus
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    standards_used: List[str] = field(default_factory=list)
    rule_path: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    requires_scholar_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "standards_used": self.standards_used,
            "rule_path": self.rule_path,
            "limitations": self.limitations,
            "requires_scholar_review": self.requires_scholar_review,
        }
