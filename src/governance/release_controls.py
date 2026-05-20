"""Release governance contracts for source-grounded Mushir behavior."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional

from src.models.commercial import QuestionType, SourceFamily


class ClarificationTrigger(str, Enum):
    LOW_TERM_CONFIDENCE = "low_term_confidence"
    CROSS_STANDARD_TIE = "cross_standard_tie"
    WEAK_EVIDENCE = "weak_evidence"
    SUPERSEDED_REFERENCE = "superseded_reference"
    LANGUAGE_MISMATCH = "language_mismatch"
    MISSING_TRANSACTION_FACTS = "missing_transaction_facts"
    UNSUPPORTED_PERMISSIBILITY_SCOPE = "unsupported_permissibility_scope"


@dataclass(frozen=True)
class ClarificationDecision:
    should_ask: bool
    question: str = ""
    triggers: List[ClarificationTrigger] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.should_ask and not self.question.strip():
            raise ValueError("question is required when clarification is needed")
        if self.should_ask and len([line for line in self.question.splitlines() if line.strip()]) != 1:
            raise ValueError("clarification must be one user-visible question")


class ClarificationPolicy:
    """Small deterministic policy for when the assistant should ask once."""

    def decide(
        self,
        *,
        question_type: QuestionType,
        term_confidence: float,
        candidate_standards: Iterable[str],
        evidence_score: float,
        source_currentness: str,
        query_language: str,
        evidence_language: str,
        missing_facts: Iterable[str] = (),
    ) -> ClarificationDecision:
        if question_type in {QuestionType.EXPLANATION, QuestionType.ACCOUNTING} and evidence_score >= 0.5:
            return ClarificationDecision(False)
        triggers: List[ClarificationTrigger] = []
        if term_confidence < 0.45:
            triggers.append(ClarificationTrigger.LOW_TERM_CONFIDENCE)
        if len(set(candidate_standards)) > 1 and evidence_score < 0.7:
            triggers.append(ClarificationTrigger.CROSS_STANDARD_TIE)
        if evidence_score < 0.35:
            triggers.append(ClarificationTrigger.WEAK_EVIDENCE)
        if source_currentness == "superseded":
            triggers.append(ClarificationTrigger.SUPERSEDED_REFERENCE)
        if query_language != "unknown" and evidence_language != "unknown" and query_language != evidence_language:
            triggers.append(ClarificationTrigger.LANGUAGE_MISMATCH)
        missing = list(missing_facts)
        if missing:
            triggers.append(ClarificationTrigger.MISSING_TRANSACTION_FACTS)
        if question_type == QuestionType.PERMISSIBILITY and SourceFamily.SHARIA_STANDARD.value not in candidate_standards:
            triggers.append(ClarificationTrigger.UNSUPPORTED_PERMISSIBILITY_SCOPE)
        if not triggers:
            return ClarificationDecision(False)
        if ClarificationTrigger.MISSING_TRANSACTION_FACTS in triggers:
            fact = missing[0]
            return ClarificationDecision(True, f"Can you clarify the {fact.replace('_', ' ')}?", triggers)
        return ClarificationDecision(True, "Which exact product, standard, or transaction detail should I use?", triggers)


@dataclass(frozen=True)
class RetrievalTraceRecord:
    retrieval_run_id: str
    original_query: str
    normalized_query: str
    candidate_concepts: List[str]
    route_id: str
    filters: Dict[str, str]
    scores: List[float]
    parent_chunk_ids: List[str]
    child_chunk_ids: List[str]
    reranking_rationale: str = ""

    def __post_init__(self) -> None:
        if not self.retrieval_run_id.strip():
            raise ValueError("retrieval_run_id is required")
        if not self.original_query.strip():
            raise ValueError("original_query is required")
        if len(self.scores) != len(self.child_chunk_ids):
            raise ValueError("scores must align with child_chunk_ids")


@dataclass(frozen=True)
class RetrievalEvalCase:
    case_id: str
    expected_standard: str
    expected_source_family: SourceFamily
    actual_standards: List[str]
    actual_source_families: List[SourceFamily]
    is_superseded_trap: bool = False
    is_wrong_standard_trap: bool = False

    def standard_hit(self) -> bool:
        return self.expected_standard in self.actual_standards

    def source_family_hit(self) -> bool:
        return self.expected_source_family in self.actual_source_families


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    cases: List[RetrievalEvalCase]

    def metric_summary(self) -> Dict[str, float]:
        total = len(self.cases)
        if total == 0:
            return {"standard_accuracy": 0.0, "source_family_accuracy": 0.0, "trap_failure_rate": 0.0}
        standard_hits = sum(case.standard_hit() for case in self.cases)
        family_hits = sum(case.source_family_hit() for case in self.cases)
        trap_cases = [case for case in self.cases if case.is_superseded_trap or case.is_wrong_standard_trap]
        trap_failures = sum(case.standard_hit() for case in trap_cases)
        return {
            "standard_accuracy": standard_hits / total,
            "source_family_accuracy": family_hits / total,
            "trap_failure_rate": trap_failures / len(trap_cases) if trap_cases else 0.0,
        }


class AnswerGateStatus(str, Enum):
    ADMISSIBLE = "admissible"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class AnswerAdmissibilityDecision:
    status: AnswerGateStatus
    reasons: List[str] = field(default_factory=list)

    @property
    def can_generate_final_answer(self) -> bool:
        return self.status == AnswerGateStatus.ADMISSIBLE


def assess_answer_admissibility(
    *,
    question_type: QuestionType,
    source_family: SourceFamily,
    currentness: str,
    retrieval_confidence: float,
    citation_supported: bool,
    ambiguity_cleared: bool,
    language_supported: bool,
    safety_supported: bool,
) -> AnswerAdmissibilityDecision:
    reasons: List[str] = []
    if currentness != "current":
        reasons.append("source is not current")
    if retrieval_confidence < 0.35:
        reasons.append("retrieval confidence is too low")
    if not citation_supported:
        reasons.append("citation support is missing")
    if not ambiguity_cleared:
        reasons.append("ambiguity policy is not cleared")
    if not language_supported:
        reasons.append("language policy is not cleared")
    if not safety_supported:
        reasons.append("safety policy is not cleared")
    if question_type == QuestionType.PERMISSIBILITY and source_family != SourceFamily.SHARIA_STANDARD:
        reasons.append("permissibility requires Shariah-standard evidence")
    if question_type == QuestionType.ACCOUNTING and source_family not in {SourceFamily.FAS, SourceFamily.GOVERNANCE}:
        reasons.append("accounting answers require accounting or governance source family")
    if reasons:
        return AnswerAdmissibilityDecision(AnswerGateStatus.INSUFFICIENT_DATA, reasons)
    return AnswerAdmissibilityDecision(AnswerGateStatus.ADMISSIBLE)


class FeedbackStatus(str, Enum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    UNSUPPORTED = "unsupported"
    WRONG_STANDARD = "wrong_standard"
    STALE_SOURCE = "stale_source"
    TRANSLATION_ISSUE = "translation_issue"
    UNSAFE_ANSWER = "unsafe_answer"
    NEEDS_SCHOLAR_REVIEW = "needs_scholar_review"


class ExternalDatasetName(str, Enum):
    ARBANKING77 = "arbanking77"
    DARIJABANKING = "darijabanking"
    ARABICAQA = "arabicaqa"
    SAHM = "sahm"


@dataclass(frozen=True)
class ExternalDatasetReview:
    dataset: ExternalDatasetName
    license_reviewed: bool
    relevance_reviewed: bool
    supplemental_only: bool = True

    @property
    def can_use_for_robustness_probe(self) -> bool:
        return self.license_reviewed and self.relevance_reviewed and self.supplemental_only


class ObservabilityTool(str, Enum):
    RAGAS = "ragas"
    DEEPEVAL = "deepeval"
    PROMPTFOO = "promptfoo"
    LANGFUSE = "langfuse"
    PHOENIX = "phoenix"
    TRULENS = "trulens"


@dataclass(frozen=True)
class ObservabilitySpineSelection:
    primary_tool: ObservabilityTool
    compared_tools: List[ObservabilityTool]
    rationale: str

    def __post_init__(self) -> None:
        if self.primary_tool not in self.compared_tools:
            raise ValueError("primary_tool must be included in compared_tools")
        if len(set(self.compared_tools)) < 2:
            raise ValueError("select the primary spine only after comparing at least two tools")
        if not self.rationale.strip():
            raise ValueError("rationale is required")


@dataclass(frozen=True)
class RetrievalCandidateExperiment:
    candidate_name: str
    gold_set_ready: bool
    catalog_ready: bool
    measured_against_same_gold_set: bool
    adopted: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_name.strip():
            raise ValueError("candidate_name is required")
        if self.adopted and not (
            self.gold_set_ready and self.catalog_ready and self.measured_against_same_gold_set
        ):
            raise ValueError("retrieval candidates cannot be adopted before catalog and gold-set measurement")


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    answer_id: str
    retrieval_run_id: str
    citation_ids: List[str]
    source_ids: List[str]
    language: str
    status: FeedbackStatus
    reviewer: str
    reviewed: bool = False

    def __post_init__(self) -> None:
        if not self.feedback_id.strip() or not self.answer_id.strip() or not self.retrieval_run_id.strip():
            raise ValueError("feedback_id, answer_id, and retrieval_run_id are required")
        if not self.citation_ids or not self.source_ids:
            raise ValueError("citation_ids and source_ids are required")
        if not self.reviewer.strip():
            raise ValueError("reviewer is required")

    @property
    def can_update_governance(self) -> bool:
        return self.reviewed and self.status in {
            FeedbackStatus.CORRECT,
            FeedbackStatus.PARTIALLY_CORRECT,
            FeedbackStatus.UNSUPPORTED,
            FeedbackStatus.WRONG_STANDARD,
            FeedbackStatus.STALE_SOURCE,
            FeedbackStatus.TRANSLATION_ISSUE,
            FeedbackStatus.UNSAFE_ANSWER,
            FeedbackStatus.NEEDS_SCHOLAR_REVIEW,
        }


@dataclass(frozen=True)
class GoldSetCase:
    case_id: str
    question: str
    expected_standard: str
    expected_source_family: SourceFamily
    source_feedback_id: str


def feedback_to_gold_case(feedback: FeedbackRecord, expected_standard: str, question: str) -> GoldSetCase:
    if not feedback.can_update_governance:
        raise ValueError("feedback must be reviewed before becoming a gold case")
    return GoldSetCase(
        case_id=f"gold-{feedback.feedback_id}",
        question=question,
        expected_standard=expected_standard,
        expected_source_family=SourceFamily.FAS,
        source_feedback_id=feedback.feedback_id,
    )


@dataclass(frozen=True)
class ReleaseMetricReport:
    source_family_accuracy: float
    expected_standard_hit_rate: float
    citation_support_rate: float
    clarification_precision: float
    clarification_recall: float
    arabic_robustness: float
    refusal_correctness: float
    latency_p95_ms: float
    unresolved_feedback_count: int
    live_llm_smoke_count: int = 0

    def __post_init__(self) -> None:
        bounded = [
            self.source_family_accuracy,
            self.expected_standard_hit_rate,
            self.citation_support_rate,
            self.clarification_precision,
            self.clarification_recall,
            self.arabic_robustness,
            self.refusal_correctness,
        ]
        if any(value < 0.0 or value > 1.0 for value in bounded):
            raise ValueError("rate metrics must be between 0 and 1")
        if self.live_llm_smoke_count > 5:
            raise ValueError("live LLM smoke tests must stay small")


class L6Scope(str, Enum):
    ACCOUNTING_ONLY = "accounting_only"
    ACCOUNTING_PLUS_SHARIAH = "accounting_plus_shariah"


@dataclass(frozen=True)
class L6EntryGate:
    scope: L6Scope
    permissibility_assessment_allowed: bool
    shariah_sources_cataloged: bool
    scenario_schema_ready: bool
    rule_table_ready: bool
    gold_cases_ready: bool
    red_line_refusals_ready: bool
    human_review_ready: bool

    def unmet_requirements(self) -> List[str]:
        missing: List[str] = []
        if self.scope == L6Scope.ACCOUNTING_PLUS_SHARIAH and not self.shariah_sources_cataloged:
            missing.append("shariah_sources_cataloged")
        if self.permissibility_assessment_allowed and not self.shariah_sources_cataloged:
            missing.append("permissibility_requires_shariah_sources")
        for field_name in (
            "scenario_schema_ready",
            "rule_table_ready",
            "gold_cases_ready",
            "red_line_refusals_ready",
            "human_review_ready",
        ):
            if not getattr(self, field_name):
                missing.append(field_name)
        return missing

    @property
    def can_start_domain_implementation(self) -> bool:
        return not self.unmet_requirements()
