import pytest

from src.governance import (
    AnswerGateStatus,
    ClarificationPolicy,
    ClarificationTrigger,
    ExternalDatasetName,
    ExternalDatasetReview,
    FeedbackRecord,
    FeedbackStatus,
    L6EntryGate,
    L6Scope,
    ObservabilitySpineSelection,
    ObservabilityTool,
    ReleaseMetricReport,
    RetrievalCandidateExperiment,
    RetrievalEvalCase,
    RetrievalEvaluationReport,
    RetrievalTraceRecord,
    assess_answer_admissibility,
    feedback_to_gold_case,
)
from src.models.commercial import QuestionType, SourceFamily


pytestmark = pytest.mark.service


def test_clarification_policy_asks_one_question_for_missing_transaction_facts():
    decision = ClarificationPolicy().decide(
        question_type=QuestionType.PERMISSIBILITY,
        term_confidence=0.9,
        candidate_standards=[SourceFamily.SHARIA_STANDARD.value],
        evidence_score=0.8,
        source_currentness="current",
        query_language="en",
        evidence_language="en",
        missing_facts=["penalty_beneficiary"],
    )

    assert decision.should_ask is True
    assert decision.question == "Can you clarify the penalty beneficiary?"
    assert ClarificationTrigger.MISSING_TRANSACTION_FACTS in decision.triggers


def test_clarification_policy_bypasses_clear_accounting_questions():
    decision = ClarificationPolicy().decide(
        question_type=QuestionType.ACCOUNTING,
        term_confidence=0.8,
        candidate_standards=["FAS-28"],
        evidence_score=0.7,
        source_currentness="current",
        query_language="en",
        evidence_language="en",
    )

    assert decision.should_ask is False


def test_retrieval_trace_and_metrics_separate_standard_from_source_family():
    trace = RetrievalTraceRecord(
        retrieval_run_id="run-1",
        original_query="How is murabaha profit recognized?",
        normalized_query="murabaha profit recognized",
        candidate_concepts=["murabaha"],
        route_id="murabaha-accounting",
        filters={"source_family": "fas"},
        scores=[0.9],
        parent_chunk_ids=["fas-28:recognition"],
        child_chunk_ids=["fas-28:recognition:0"],
        reranking_rationale="FAS-28 recognition section ranked first.",
    )
    report = RetrievalEvaluationReport(
        [
            RetrievalEvalCase(
                case_id="case-1",
                expected_standard="FAS-28",
                expected_source_family=SourceFamily.FAS,
                actual_standards=["FAS-28"],
                actual_source_families=[SourceFamily.FAS],
            ),
            RetrievalEvalCase(
                case_id="case-2",
                expected_standard="FAS-28",
                expected_source_family=SourceFamily.FAS,
                actual_standards=["FAS-2"],
                actual_source_families=[SourceFamily.FAS],
                is_wrong_standard_trap=True,
            ),
        ]
    )

    assert trace.parent_chunk_ids == ["fas-28:recognition"]
    assert report.metric_summary()["standard_accuracy"] == 0.5
    assert report.metric_summary()["source_family_accuracy"] == 1.0
    assert report.metric_summary()["trap_failure_rate"] == 0.0


def test_answer_admissibility_fails_closed_for_permissibility_without_sharia_source():
    decision = assess_answer_admissibility(
        question_type=QuestionType.PERMISSIBILITY,
        source_family=SourceFamily.FAS,
        currentness="current",
        retrieval_confidence=0.9,
        citation_supported=True,
        ambiguity_cleared=True,
        language_supported=True,
        safety_supported=True,
    )

    assert decision.status == AnswerGateStatus.INSUFFICIENT_DATA
    assert decision.can_generate_final_answer is False
    assert "permissibility requires Shariah-standard evidence" in decision.reasons


def test_answer_admissibility_allows_current_cited_accounting_evidence():
    decision = assess_answer_admissibility(
        question_type=QuestionType.ACCOUNTING,
        source_family=SourceFamily.FAS,
        currentness="current",
        retrieval_confidence=0.9,
        citation_supported=True,
        ambiguity_cleared=True,
        language_supported=True,
        safety_supported=True,
    )

    assert decision.status == AnswerGateStatus.ADMISSIBLE
    assert decision.can_generate_final_answer is True


def test_feedback_requires_review_before_gold_case_update():
    feedback = FeedbackRecord(
        feedback_id="fb-1",
        answer_id="answer-1",
        retrieval_run_id="run-1",
        citation_ids=["citation-1"],
        source_ids=["aaoifi-fas-28-en"],
        language="en",
        status=FeedbackStatus.WRONG_STANDARD,
        reviewer="reviewer-1",
        reviewed=False,
    )

    with pytest.raises(ValueError, match="reviewed"):
        feedback_to_gold_case(feedback, "FAS-28", "How should murabaha profit be recognized?")

    reviewed = FeedbackRecord(
        feedback_id="fb-1",
        answer_id="answer-1",
        retrieval_run_id="run-1",
        citation_ids=["citation-1"],
        source_ids=["aaoifi-fas-28-en"],
        language="en",
        status=FeedbackStatus.WRONG_STANDARD,
        reviewer="reviewer-1",
        reviewed=True,
    )

    assert feedback_to_gold_case(
        reviewed,
        "FAS-28",
        "How should murabaha profit be recognized?",
    ).case_id == "gold-fb-1"


def test_release_report_caps_live_llm_smokes_and_tracks_required_metrics():
    report = ReleaseMetricReport(
        source_family_accuracy=1.0,
        expected_standard_hit_rate=0.9,
        citation_support_rate=0.95,
        clarification_precision=0.8,
        clarification_recall=0.75,
        arabic_robustness=0.7,
        refusal_correctness=1.0,
        latency_p95_ms=1200,
        unresolved_feedback_count=2,
        live_llm_smoke_count=3,
    )

    assert report.unresolved_feedback_count == 2

    with pytest.raises(ValueError, match="live LLM smoke tests"):
        ReleaseMetricReport(
            source_family_accuracy=1.0,
            expected_standard_hit_rate=0.9,
            citation_support_rate=0.95,
            clarification_precision=0.8,
            clarification_recall=0.75,
            arabic_robustness=0.7,
            refusal_correctness=1.0,
            latency_p95_ms=1200,
            unresolved_feedback_count=0,
            live_llm_smoke_count=20,
        )


def test_external_dataset_reviews_are_supplemental_and_license_gated():
    review = ExternalDatasetReview(
        dataset=ExternalDatasetName.ARBANKING77,
        license_reviewed=True,
        relevance_reviewed=True,
    )
    missing_license = ExternalDatasetReview(
        dataset=ExternalDatasetName.SAHM,
        license_reviewed=False,
        relevance_reviewed=True,
    )

    assert review.can_use_for_robustness_probe is True
    assert missing_license.can_use_for_robustness_probe is False


def test_observability_spine_requires_comparison_and_single_primary_tool():
    selection = ObservabilitySpineSelection(
        primary_tool=ObservabilityTool.RAGAS,
        compared_tools=[ObservabilityTool.RAGAS, ObservabilityTool.DEEPEVAL],
        rationale="Ragas better matches retrieval-grounded citation metrics for the current gate.",
    )

    assert selection.primary_tool == ObservabilityTool.RAGAS

    with pytest.raises(ValueError, match="at least two tools"):
        ObservabilitySpineSelection(
            primary_tool=ObservabilityTool.PROMPTFOO,
            compared_tools=[ObservabilityTool.PROMPTFOO],
            rationale="No comparison.",
        )


def test_retrieval_candidate_adoption_requires_catalog_and_same_gold_set_measurement():
    RetrievalCandidateExperiment(
        candidate_name="qdrant-bge-m3",
        gold_set_ready=True,
        catalog_ready=True,
        measured_against_same_gold_set=True,
        adopted=True,
    )

    with pytest.raises(ValueError, match="catalog and gold-set measurement"):
        RetrievalCandidateExperiment(
            candidate_name="pgvector-fts",
            gold_set_ready=False,
            catalog_ready=True,
            measured_against_same_gold_set=False,
            adopted=True,
        )


def test_l6_entry_gate_blocks_rules_domain_until_sources_and_review_are_ready():
    gate = L6EntryGate(
        scope=L6Scope.ACCOUNTING_PLUS_SHARIAH,
        permissibility_assessment_allowed=True,
        shariah_sources_cataloged=False,
        scenario_schema_ready=True,
        rule_table_ready=False,
        gold_cases_ready=True,
        red_line_refusals_ready=True,
        human_review_ready=True,
    )

    assert gate.can_start_domain_implementation is False
    assert "shariah_sources_cataloged" in gate.unmet_requirements()
    assert "rule_table_ready" in gate.unmet_requirements()
