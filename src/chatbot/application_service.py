import copy
import json
import os
import random
import re
import threading
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any, Dict, List, Optional

import yaml

from src.chatbot.commercial_assessment import (
    CommercialRuleEvaluator,
    EvidenceFamilyDetector,
    ScenarioExtractor,
    StandardsRouter,
    should_fail_closed_for_source_gap,
    source_gap_verdict,
)
from src.chatbot.citation_validator import CitationValidator
from src.chatbot.constants import AUTHORITY_REQUEST_TERMS
from src.chatbot.prompt_builder import PromptBuilder
from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus
from src.models.commercial import ContractFamily, SourceFamily, StandardsRoute
from src.models.session import ClarificationState
from src.governance.source_catalog import is_answer_admissible_metadata
from src.governance.scholar_review import (
    ScholarReviewQueue,
    ScholarReviewQueueItem,
    ScholarReviewQueueStore,
)
from src.rag.pipeline import RAGPipeline
from src.rag.query_preprocessor import QueryPreprocessor
from src.rag.standard_resolver import resolve_bulk
from src.storage.cache import CacheStore

# ---------------------------------------------------------------------------
# Arabic transliteration normalization map: common English misspellings
# that users type when searching for Islamic finance terms.
# ---------------------------------------------------------------------------
_TRANSLITERATION_MAP = {
    r'\bmurabah\b': 'murabahah',
    r'\bmurabahat\b': 'murabahah',
    r'\bmurabaha\b': 'murabahah',
    r'\bmudaraba\b': 'mudarabah',
    r'\bmudharaba\b': 'mudarabah',
    r'\bmudarabat\b': 'mudarabah',
    r'\bijara\b': 'ijarah',
    r'\bijarat\b': 'ijarah',
    r'\bsukuks\b': 'sukuk',
    r'\bzakah\b': 'zakat',
    r'\bghrar\b': 'gharar',
    r'\bribah\b': 'riba',
    r'\bmusharakah\b': 'musharakah',  # keep but map variant
    r'\bmusharaka\b': 'musharakah',
    r'\bwakala\b': 'wakalah',
    r'\bqard hasan\b': 'qard al-hasan',
}

# Arabic diacritic (tashkeel) + tatweel stripping pattern
_ARABIC_DIACRITICS = re.compile(r'[\u064b-\u065f\u0670\u0640]')
# Hamza normalization: various alef forms → plain alef
_HAMZA_NORM = re.compile(r'[\u0622\u0623\u0625\u0671]')  # آ أ إ ٱ → ا


class ApplicationService:
    """Coordinates retrieval, prompt building, LLM generation, and citation validation."""

    def __init__(
        self,
        retriever=None,
        llm_client=None,
        prompt_builder=None,
        citation_validator=None,
        clarification_service=None,
        session_store=None,
        audit_store=None,
        cache_store=None,
        scholar_review_queue_store: Optional[ScholarReviewQueueStore] = None,
        scholar_sampling_rate: float = 0.05,
        scholar_sampler=None,
        k: int = 5,
        threshold: float = 0.3,
        approved_rule_cards=(),
        decision_store=None,
    ):
        self.retriever = retriever
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_validator = citation_validator or CitationValidator()
        # ClarificationEngine is the authoritative gate for pre-retrieval clarification.
        # Always instantiate a default so the judgment bypass, informational bypass,
        # and transaction-structure bypass all fire regardless of caller injection.
        from src.chatbot.clarification_engine import ClarificationEngine
        self.clarification_service = clarification_service or ClarificationEngine()
        self._clarification_service_injected = clarification_service is not None
        self.session_store = session_store
        self.audit_store = audit_store
        self.decision_store = decision_store
        # Striped locks keep one session's snapshot/answer/commit/restore from interleaving with another request's.
        self._session_locks = tuple(threading.RLock() for _ in range(64))
        self.cache_store = cache_store
        self.scholar_review_queue_store = scholar_review_queue_store
        self.scholar_sampling_rate = max(0.0, min(float(scholar_sampling_rate), 1.0))
        self.scholar_sampler = scholar_sampler or random.random
        self.k = k
        self.threshold = threshold
        self.response_cache_ttl = int(os.getenv("RESPONSE_CACHE_TTL_SECONDS", "86400"))
        self.scenario_extractor = ScenarioExtractor()
        from src.chatbot.contract_family_router import ContractFamilyRouter
        self.family_router = ContractFamilyRouter()
        self.standards_router = StandardsRouter()
        self.rule_evaluator = CommercialRuleEvaluator()
        from src.ontology.concept_ontology import ConceptOntology
        self.ontology = ConceptOntology.load()
        from src.chatbot.described_operation import DescribedOperationService
        from src.governance.rule_cards import load_rule_cards
        card_path = os.getenv("APPROVED_RULE_CARDS_PATH")
        cards = tuple(approved_rule_cards)  # An explicit argument outranks the environment.
        if not cards and card_path:
            try:
                cards = load_rule_cards(card_path)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                # Silently running without cards would abstain on everything unnoticed.
                raise RuntimeError(f"APPROVED_RULE_CARDS_PATH could not be loaded: {exc}") from exc
        self.described_operations = DescribedOperationService(cards)

    def answer(
        self, query: Optional[str], session_id: Optional[str] = None,
        request_id: Optional[str] = None, disclaimer_acknowledged: bool = True,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AnswerContract:
        if self.decision_store is None:
            result = self._answer(query, session_id, request_id, disclaimer_acknowledged, conversation_history)
            result = self._add_requested_definition(query, result)
            result = self._enforce_verdict_authority(result)
            return self._attach_decision_trace(result)
        from uuid import uuid4
        from src.models.decision_audit import prepare_decision_record
        effective_session = session_id or str(uuid4())
        effective_request = request_id or str(uuid4())
        # The decision record is the commit point: an answer that could not be
        # recorded is never delivered, so the conversation must not advance either.
        # Append-only audit/queue writes made by _answer cannot be withdrawn.
        with self._session_locks[hash(effective_session) % len(self._session_locks)]:
            return self._answer_and_commit(query, session_id, effective_session, effective_request,
                                           disclaimer_acknowledged, conversation_history)

    def _answer_and_commit(self, query, session_id, effective_session, effective_request,
                           disclaimer_acknowledged, conversation_history) -> AnswerContract:
        from src.models.decision_audit import prepare_decision_record
        snapshot = self._snapshot_session(effective_session)
        try:
            # Anonymous requests share one id with their audit record but never leave session state behind.
            answer = self._answer(query, effective_session, effective_request, disclaimer_acknowledged,
                                  conversation_history, keep_session=bool(session_id))
            answer = self._add_requested_definition(query, answer)
            answer = self._enforce_verdict_authority(answer)
            answer = self._attach_decision_trace(answer)
            record = prepare_decision_record(query, answer, session_id=effective_session, request_id=effective_request)
            if self.decision_store.append(record) != record.review_id:
                raise RuntimeError("decision review storage did not acknowledge the record")
        except Exception:
            try:
                self._restore_session(effective_session, snapshot)
            except Exception:
                pass  # The original storage failure is the error the caller must see.
            raise
        if not session_id:
            self._restore_session(effective_session, None)  # No caller handle exists, so no state may outlive the call.
        return answer

    _VERDICT_STATUSES = frozenset({ComplianceStatus.COMPLIANT, ComplianceStatus.NON_COMPLIANT,
                                   ComplianceStatus.PARTIALLY_COMPLIANT})

    @classmethod
    def _enforce_verdict_authority(cls, answer):
        """Final invariant: only an evaluated, scholar-approved rule may carry a verdict.

        Independent of routing, cache and claim-support checks, so a misrouted
        question or a cached legacy answer cannot deliver a generated verdict.
        """
        if not isinstance(answer, AnswerContract) or answer.status not in cls._VERDICT_STATUSES:
            return answer
        evaluation = answer.metadata.get("approved_rule_evaluation")
        if isinstance(evaluation, dict) and evaluation.get("status") == "evaluated":
            return answer
        language = answer.metadata.get("response_language") if answer.metadata.get("response_language") in {"en", "ar"} else "en"
        answer.status = ComplianceStatus.INSUFFICIENT_DATA
        answer.answer = cls._rule_review_required_message(language)
        answer.citations = []
        answer.metadata.pop("decision_basis", None)
        answer.metadata["requires_scholar_review"] = True
        answer.metadata["approved_rule_gate"] = {"status": "blocked", "reason": "verdict_without_approved_rule"}
        return answer

    @staticmethod
    def _attach_decision_trace(answer):
        """Attach only typed, public-safe decision facts before the audit commit."""
        if isinstance(answer, AnswerContract):
            from src.models.decision_trace import build_decision_trace
            answer.metadata["decision_trace"] = build_decision_trace(answer)
        return answer

    MAX_SESSION_REVIEW_ROWS = 20

    @classmethod
    def _append_review_row(cls, state: Any, key: str, row: Any) -> None:
        """Session copies are a bounded working set; the decision store holds the full record."""
        rows = state.metadata.get(key)
        if not isinstance(rows, list):
            rows = state.metadata[key] = []
        rows.append(row)
        del rows[:-cls.MAX_SESSION_REVIEW_ROWS]

    def _snapshot_session(self, session_id: str) -> Any:
        state = self._session_state(session_id)
        return copy.deepcopy(state) if state is not None else None

    def _restore_session(self, session_id: str, snapshot: Any) -> None:
        if not self.session_store:
            return
        if snapshot is None:
            if hasattr(self.session_store, "delete_session"):
                self.session_store.delete_session(session_id)
        elif hasattr(self.session_store, "update_session"):
            self.session_store.update_session(snapshot)

    def _answer(
        self,
        query: Optional[str],
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        disclaimer_acknowledged: bool = True,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        keep_session: bool = True,
    ) -> AnswerContract:
        if not query or not query.strip():
            return self._empty_query_response()
        cleaned_query = self._normalize_query(query.strip())
        response_language = self._detect_language(cleaned_query)
        if re.search(r"chain[- ]of[- ]thought|(?:hidden|private|internal)\s+(?:thoughts?|reasoning)|"
                     r"سلسلة التفكير|(?:الأفكار|الافكار|التفكير)\s+(?:الداخلية|الخفي|الخفية)", cleaned_query, re.I):
            text = ("أستطيع عرض شرح موجز للأدلة والمعلومات الناقصة وسبب الرد، دون عرض التفكير الداخلي الخاص."
                    if response_language == "ar" else
                    "I can show a brief explanation of the evidence, missing information and response basis. Private internal reasoning is unavailable.")
            contract = AnswerContract(answer=text, status=ComplianceStatus.INSUFFICIENT_DATA,
                metadata={"response_language": response_language, "decision_basis": "private_reasoning_requested"})
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract
        if self._requires_disclaimer(disclaimer_acknowledged):
            question = self._disclaimer_acknowledgement_question(response_language)
            contract = AnswerContract(
                answer=question,
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                clarification_question=question,
                reasoning_summary="Mushir needs explicit acknowledgement of its informational-only scope before analysis.",
                limitations=self._limitations(response_language),
                metadata={"disclaimer_required": True, "response_language": response_language},
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        # Authority check runs BEFORE cache so that tightening the gate always
        # takes effect immediately — a cached answer never bypasses compliance.
        if self._is_authority_request(cleaned_query):
            contract = AnswerContract(
                answer=self._authority_refusal_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="User requested a binding ruling or legal advice, which exceeds Mushir's scope.",
                limitations=self._limitations(response_language),
                metadata={**self._metadata([], response_language=response_language), "decision_basis": "scope_refusal"},
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        # Personal descriptions use typed session evidence before legacy family
        # heuristics, caches, retrieval, or generation can supply missing facts.
        from src.chatbot.described_operation import OperationConversation
        from src.chatbot.structure_clarification import clarify_structure, structure_slot
        from uuid import uuid4
        state = self._session_state(session_id)
        saved_operation = state.metadata.get("described_operation") if state else None
        operation = None
        if saved_operation:
            try:
                operation = OperationConversation.model_validate(saved_operation)
            except ValueError:
                state.metadata.pop("described_operation", None)  # Stale schema: start the description afresh.
        pending_structure = state.metadata.get("pending_structure_clarification") if state else None
        # A suspended transaction must not capture facts from the active topic.
        # Only a fresh personal description may switch out of that topic.
        personal_context = None if pending_structure else operation
        operation_query = self._without_language_instruction(query)
        purpose_answer = self._purpose_clarification(operation_query, response_language, session_id, keep_session)
        if purpose_answer:
            self._audit(query, purpose_answer, session_id, request_id)
            return purpose_answer
        if not structure_slot(cleaned_query) and self.described_operations.accepts(operation_query, personal_context):
            effective_session = session_id or str(uuid4())
            contract, updated_operation = self.described_operations.answer(
                operation_query, session_id=effective_session, request_id=request_id or str(uuid4()),
                previous=personal_context, language=response_language,
            )
            state = state or self._session_state(session_id, create=keep_session)
            if state:
                state.metadata.pop("pending_structure_clarification", None)
                state.metadata.pop("pending_scenario_clarification", None)
                state.metadata["described_operation"] = updated_operation.model_dump(mode="json")
                self._append_review_row(state, "operation_review_rows", contract.metadata["decision_review"])
                state.add_message("user", query)
                state.add_message("assistant", contract.answer)
                self._update_session_state(state)
            self._audit(query, contract, effective_session, request_id)
            if contract.status == ComplianceStatus.INSUFFICIENT_DATA:
                self._append_scholar_review_queue(query=query, answer=contract, queue=ScholarReviewQueue.AUTO_FLAGGED,
                    flag_reason="typed_operation_evidence_incomplete", session_id=effective_session, request_id=request_id)
            return contract

        structure_answer, next_structure = clarify_structure(query, cleaned_query, response_language, pending_structure)
        if structure_answer or pending_structure:
            state = state or self._session_state(session_id, create=keep_session)
            if state:
                state.metadata.pop("pending_structure_clarification", None)
                if next_structure:
                    state.metadata["pending_structure_clarification"] = next_structure
                if structure_answer:
                    state.metadata.pop("pending_scenario_clarification", None)
                    if operation:
                        state.metadata["described_operation"] = operation.model_copy(update={"pending_slot": None}).model_dump(mode="json")
                    self._append_review_row(state, "structure_review_rows", structure_answer.metadata["structure_clarification"])
                    state.add_message("user", query)
                    state.add_message("assistant", structure_answer.answer)
                self._update_session_state(state)
            if structure_answer:
                self._audit(query, structure_answer, session_id, request_id)
                if structure_answer.status == ComplianceStatus.INSUFFICIENT_DATA:
                    self._append_scholar_review_queue(query=query, answer=structure_answer, queue=ScholarReviewQueue.AUTO_FLAGGED,
                        flag_reason="structure_evidence_incomplete", session_id=session_id, request_id=request_id)
                return structure_answer

        # Extract scenario first so it's available for routing
        pending_scenario_clarification = self._consume_pending_scenario_clarification(session_id)
        analysis_query = self._query_with_pending_clarification(
            cleaned_query,
            pending_scenario_clarification,
        )
        from src.chatbot.commercial_assessment import TransactionScenario, QuestionType
        try:
            scenario = self.scenario_extractor.extract(analysis_query)
        except Exception as exc:
            print(f"Scenario extraction failed: {type(exc).__name__}")
            scenario = TransactionScenario(question_type=QuestionType.PERMISSIBILITY)

        # Stage 1 & 2: Routing and Standard Resolution
        session_family = pending_scenario_clarification.get("family") if pending_scenario_clarification else None
        session_turns = pending_scenario_clarification.get("turns", 0) if pending_scenario_clarification else 0

        family_result, target_standards = self._handle_routing_stage(
            analysis_query, session_family, session_turns
        )

        # Build authoritative standards_route
        standards_route = self.standards_router.route(scenario, analysis_query)
        if target_standards:
            standards_route.candidate_standards = sorted(set(standards_route.candidate_standards) | set(target_standards))

        from src.chatbot.contract_family_router import RetrievalMode
        known_family = None
        if family_result.mode in (RetrievalMode.SINGLE_PATH, RetrievalMode.MULTI_PATH):
            known_family = family_result.primary_family

        # Stage 3: Clarification Validation
        clarification_contract = self._handle_clarification_stage(
            cleaned_query,
            scenario,
            standards_route,
            family_result,
            known_family,
            session_id,
            request_id,
            response_language
        )
        if clarification_contract:
            return clarification_contract

        # Legacy routing labels and retrieved standards are not approved rule
        # evaluations. Until this path has a reconciled typed snapshot and an
        # approved-card result, judgment requests must not reach cache or LLM.
        # Productive clarification remains available above this boundary.
        from src.chatbot.clarification_engine import ClarificationEngine
        judgment_requires_approved_evidence = (
            scenario.question_type == QuestionType.PERMISSIBILITY
            or ClarificationEngine._is_judgment_query(analysis_query)
        )
        if not judgment_requires_approved_evidence:
            if cached := self._cached_answer(cleaned_query, standards_route):
                return cached

        rule_evaluation = self.rule_evaluator.evaluate(scenario, standards_route)

        if self.retriever is None:
            try:
                self.retriever = RAGPipeline()
            except Exception as exc:
                print(f"RAG retriever init failed: {type(exc).__name__}")
                return AnswerContract(
                    answer=self._retrieval_unavailable_message(response_language),
                    status=ComplianceStatus.INSUFFICIENT_DATA,
                    citations=[],
                    reasoning_summary="Retrieval backend is not available.",
                    limitations=self._limitations(response_language),
                    metadata={**self._metadata(
                        [],
                        response_language=response_language,
                        scenario=scenario,
                        standards_route=standards_route,
                        rule_evaluation=rule_evaluation,
                    ), "retrieval_status": "unavailable"},
                )

        try:
            chunks = self._retrieve(
                analysis_query,
                k=self.k,
                threshold=self.threshold,
                standards_route=standards_route,
            )
        except Exception as exc:
            print(f"RAG retrieval failed: {type(exc).__name__}")
            return AnswerContract(
                answer=self._retrieval_unavailable_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="Retrieval backend is not available.",
                limitations=self._limitations(response_language),
                metadata={**self._metadata(
                    [],
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                ), "retrieval_status": "unavailable"},
            )
        chunks = self._answer_admissible_chunks(chunks)
        retrieved_source_families = EvidenceFamilyDetector.families(chunks)
        candidate_matched_chunks = self._candidate_standard_chunks(chunks, standards_route)
        candidate_standard_filter = self._candidate_standard_trace(
            chunks,
            candidate_matched_chunks,
            standards_route,
        )
        chunks = candidate_matched_chunks
        source_limit = self._source_limit_contract(cleaned_query, chunks, response_language)
        if source_limit:
            self._audit(cleaned_query, source_limit, session_id, request_id)
            return source_limit
        if not chunks:
            empty_families: set[SourceFamily] = set()
            if should_fail_closed_for_source_gap(scenario, standards_route, empty_families):
                verdict = source_gap_verdict(scenario, standards_route, empty_families)
                contract = AnswerContract(
                    answer=self._source_family_gap_message(response_language),
                    status=ComplianceStatus.INSUFFICIENT_DATA,
                    citations=[],
                    reasoning_summary=(
                        "The query asks about permissibility or contract validity, "
                        "but no admissible Shari'ah-standard evidence was retrieved."
                    ),
                    limitations=self._limitations(response_language),
                    metadata=self._metadata(
                        [],
                        response_language=response_language,
                        scenario=scenario,
                        standards_route=standards_route,
                        rule_evaluation=rule_evaluation,
                        verdict_contract=verdict,
                        source_families=retrieved_source_families or empty_families,
                        candidate_standard_filter=candidate_standard_filter,
                    ),
                )
                self._audit(cleaned_query, contract, session_id, request_id)
                return contract
            contract = AnswerContract(
                answer=self._not_addressed_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="No retrieved AAOIFI excerpts were available to ground an answer.",
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    [],
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                    candidate_standard_filter=candidate_standard_filter,
                ),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        evidence_families = EvidenceFamilyDetector.families(chunks)
        if should_fail_closed_for_source_gap(scenario, standards_route, evidence_families):
            verdict = source_gap_verdict(scenario, standards_route, evidence_families)
            contract = AnswerContract(
                answer=self._source_family_gap_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary=(
                    "The query asks about permissibility or contract validity, "
                    "but retrieved evidence does not include Shari'ah-standard support."
                ),
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    chunks,
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                    verdict_contract=verdict,
                    source_families=evidence_families,
                    candidate_standard_filter=candidate_standard_filter,
                ),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        if rule_evaluation.human_review_flags or rule_evaluation.evidence_requirements:
            review_citations = self._citations_for_chunks(chunks)
            contract = AnswerContract(
                answer=self._rule_review_required_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=review_citations,
                reasoning_summary=(
                    "The deterministic rule trace is exported for scholar review; "
                    "Mushir is not issuing a verdict from this path."
                ),
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    chunks,
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                    source_families=evidence_families,
                    candidate_standard_filter=candidate_standard_filter,
                    scholar_review_workflow=self._scholar_review_workflow(
                        rule_evaluation=rule_evaluation,
                        citation_count=len(review_citations),
                    ),
                ),
            )
            contract.metadata["decision_basis"] = "scholar_review_required"
            self._audit(cleaned_query, contract, session_id, request_id)
            self._append_scholar_review_queue(
                query=cleaned_query,
                answer=contract,
                queue=ScholarReviewQueue.AUTO_FLAGGED,
                flag_reason="rule_evaluation_requires_scholar_review",
                session_id=session_id,
                request_id=request_id,
            )
            return contract

        definition_contract = self._definition_answer_if_supported(
            cleaned_query,
            chunks,
            response_language,
        )
        if definition_contract is None and self._is_definition_query(cleaned_query):
            try:
                wider_chunks = self._retrieve(
                    analysis_query,
                    k=max(self.k * 8, 40),
                    threshold=0.0,
                    standards_route=standards_route,
                )
            except Exception as exc:
                print(f"Definition retrieval expansion failed: {type(exc).__name__}")
                wider_chunks = []
            if wider_chunks:
                wider_chunks = self._answer_admissible_chunks(wider_chunks)
                wider_chunks = self._candidate_standard_chunks(wider_chunks, standards_route)
                definition_contract = self._definition_answer_if_supported(
                    cleaned_query,
                    wider_chunks,
                    response_language,
                )
        if definition_contract:
            self._audit(cleaned_query, definition_contract, session_id, request_id)
            self._cache_answer(cleaned_query, definition_contract, standards_route)
            return definition_contract
        if self._is_definition_query(cleaned_query):
            contract = AnswerContract(answer=("لم أعثر على مقطع يعرّف المفهوم المطلوب؛ لا أستطيع اختراع شرح أو مرجع."
                if response_language == "ar" else "I found no passage defining the requested concept; I cannot invent an explanation or reference."),
                status=ComplianceStatus.INSUFFICIENT_DATA, metadata={"response_language": response_language,
                "answer_kind": "definition", "decision_basis": "definition_support_unavailable"})
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        unsupported_modern_asset_contract = self._unsupported_modern_asset_contract(
            cleaned_query,
            response_language,
            chunks,
            scenario,
            standards_route,
            rule_evaluation,
            candidate_standard_filter,
        )
        if unsupported_modern_asset_contract:
            unsupported_modern_asset_contract.metadata["decision_basis"] = "unsupported_asset"
            self._audit(cleaned_query, unsupported_modern_asset_contract, session_id, request_id)
            self._append_scholar_review_queue(
                query=cleaned_query,
                answer=unsupported_modern_asset_contract,
                queue=ScholarReviewQueue.AUTO_FLAGGED,
                flag_reason="unsupported_modern_asset_source_gap",
                session_id=session_id,
                request_id=request_id,
            )
            return unsupported_modern_asset_contract

        if judgment_requires_approved_evidence:
            contract = AnswerContract(
                answer=self._rule_review_required_message(response_language),
                status=ComplianceStatus.INSUFFICIENT_DATA,
                reasoning_summary="No approved rule evaluation backed by a reconciled fact snapshot is available.",
                limitations=self._limitations(response_language),
                citations=self._citations_for_chunks(chunks),
                metadata={"response_language": response_language,
                          "transaction_scenario": scenario.to_dict(),
                          "standards_route": standards_route.to_dict(),
                          "rule_evaluation": rule_evaluation.to_dict(),
                          "retrieved_chunk_ids": [self._chunk_id(chunk) for chunk in chunks],
                          "requires_scholar_review": True,
                          "approved_rule_gate": {"status": "blocked", "reason": "approved_evidence_not_available",
                                                 "needed_review": "versioned scholar-approved rule and scoped material facts"}},
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            self._append_scholar_review_queue(query=cleaned_query, answer=contract, queue=ScholarReviewQueue.AUTO_FLAGGED,
                flag_reason="approved_rule_evidence_unavailable", session_id=session_id, request_id=request_id)
            return contract

        if self.llm_client is None:
            from src.chatbot.llm_client import GeminiClient

            self.llm_client = GeminiClient()
        
        if hasattr(self.prompt_builder, 'build_messages'):
            system_prompt, user_prompt = self.prompt_builder.build_messages(
                analysis_query,
                chunks,
                history=self._history(session_id, conversation_history),
                response_language=response_language,
            )
            answer = self.llm_client.generate(user_prompt, system_prompt=system_prompt)
        else:
            prompt = self._build_prompt(
                analysis_query,
                chunks,
                history=self._history(session_id, conversation_history),
                response_language=response_language,
            )
            answer = self.llm_client.generate(prompt)
        citations = self.citation_validator.validate(answer, chunks)
        llm_clarification = self._llm_clarification_question(answer, citations)
        if llm_clarification:
            contract = AnswerContract(
                answer=self._clarification_answer(llm_clarification, response_language),
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                citations=[],
                clarification_question=llm_clarification,
                reasoning_summary=self._clarification_reason(llm_clarification, response_language),
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    chunks,
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                    candidate_standard_filter=candidate_standard_filter,
                ),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract
        status = self._status_from_answer(answer, citations)
        # Reference resolution is not claim support. The early POC admits only
        # a literal cited passage here; arbitrary generated assertions are withheld.
        literal = self.citation_validator.citation_pattern.sub("", answer).strip()
        literal = re.sub(r"^(?:NON[_ -]?COMPLIANT|PARTIALLY[_ -]?COMPLIANT|COMPLIANT|INSUFFICIENT_DATA)\s*:\s*", "", literal, flags=re.I)
        literal = literal.strip(' \n\r\t"“”«»')
        supported = next((c for c in citations if literal and c.excerpt and literal in c.excerpt), None)
        status = ComplianceStatus.INSUFFICIENT_DATA
        if supported is not None:
            answer = self._definition_answer_text(literal, self._inline_citation_marker(supported), response_language)
            citations = [supported]
            # Link the exact displayed proposition, rather than the whole excerpt.
            offset = supported.excerpt.index(literal)
            supported.quote_start = (supported.quote_start or 0) + offset
            supported.quote_end = supported.quote_start + len(literal)
            supported.excerpt = literal
        else:
            answer = self._insufficient_data_message(response_language)
            citations = []
        contract = AnswerContract(
            answer=answer,
            status=status,
            citations=citations,
            reasoning_summary="Literal source support checked; unverified generated claims withheld.",
            limitations=self._limitations(response_language),
            metadata=self._metadata(
                chunks,
                response_language=response_language,
                scenario=scenario,
                standards_route=standards_route,
                rule_evaluation=rule_evaluation,
                candidate_standard_filter=candidate_standard_filter,
            ),
        )
        contract.metadata["claim_support"] = "literal_quote_only" if supported else "unverified_withheld"
        contract.metadata["decision_basis"] = "literal_passage_cited" if supported else "generated_claim_unverified"
        self._audit(cleaned_query, contract, session_id, request_id)
        
        # User-flag Q3 (if user feedback indicates issue)
        user_feedback = "flagged" if (conversation_history and len(conversation_history) > 0 and "flag" in str(conversation_history[-1].get("content", "")).lower()) else ""
        if user_feedback:
            self._append_scholar_review_queue(
                query=cleaned_query,
                answer=contract,
                queue=ScholarReviewQueue.USER_REPORTED,
                flag_reason="user_feedback_flag",
                session_id=session_id,
                request_id=request_id,
            )
        # Incomplete answers need review independently of retrieval similarity.
        elif status == ComplianceStatus.INSUFFICIENT_DATA:
            self._append_scholar_review_queue(
                query=cleaned_query,
                answer=contract,
                queue=ScholarReviewQueue.AUTO_FLAGGED,
                flag_reason="insufficient_evidence",
                session_id=session_id,
                request_id=request_id,
            )
        else:
            self._maybe_append_random_scholar_sample(
                query=cleaned_query,
                answer=contract,
                session_id=session_id,
                request_id=request_id,
            )
            
        self._cache_answer(cleaned_query, contract, standards_route)
        return contract

    def _retrieve(
        self,
        query: str,
        k: int,
        threshold: float,
        standards_route: Any = None,
    ) -> List[Any]:
        filters = self._retrieval_filters(standards_route)
        mode = os.getenv("RETRIEVAL_MODE", "dense")
        from src.rag.score_policy import meets_threshold, validated_threshold
        threshold = validated_threshold(threshold)
        try:
            chunks = self.retriever.retrieve(
                query,
                k=k,
                threshold=threshold,
                filters=filters,
                mode=mode,
            )
        except TypeError as exc:
            if not self._legacy_retriever_signature_error(exc):
                raise
            chunks = self.retriever.retrieve(query, k=k, threshold=threshold)
        return [chunk for chunk in chunks if meets_threshold(
            chunk.get("similarity", chunk.get("score")) if isinstance(chunk, dict) else getattr(chunk, "score", None), threshold)]

    @staticmethod
    def _retrieval_filters(standards_route: Any = None) -> Optional[Dict[str, Any]]:
        if not standards_route or not getattr(standards_route, "primary", None):
            return None
        primary = standards_route.primary[0]
        value = getattr(primary, "value", primary)
        if not value:
            return None
        filters: Dict[str, Any] = {"source_family": value}
        if ApplicationService._should_enforce_candidate_standards(standards_route):
            filters["standard_number"] = ApplicationService._route_candidate_standard_ids(standards_route)
        return filters

    @staticmethod
    def _answer_admissible_chunks(chunks: List[Any]) -> List[Any]:
        import math
        admissible = []
        for chunk in chunks:
            signal = (chunk.get("similarity", chunk.get("score")) if isinstance(chunk, dict)
                      else getattr(chunk, "score", None))
            if signal is not None and (type(signal) not in {int, float} or not math.isfinite(signal)):
                continue
            if CitationValidator.has_source_instructions(ApplicationService._chunk_text(chunk)):
                continue
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else getattr(chunk, "metadata", {}) or {}
            if not is_answer_admissible_metadata(
                metadata,
                require_governed_metadata=ApplicationService._governed_metadata_required(),
            ):
                continue
            admissible.append(chunk)
        return admissible

    @classmethod
    def _candidate_standard_chunks(cls, chunks: List[Any], standards_route: Any = None) -> List[Any]:
        """Keep only route-specific Shari'ah standards when the route names them.

        Source-family filtering is necessary but not sufficient: an SS-11
        Istisna route must not be satisfied by generic SS-03 debt evidence.
        """
        if not cls._should_enforce_candidate_standards(standards_route):
            return chunks
        required = set(cls._route_candidate_standard_ids(standards_route))
        return [
            chunk
            for chunk in chunks
            if cls._chunk_standard_id(chunk) in required
        ]

    @classmethod
    def _candidate_standard_trace(
        cls,
        retrieved_chunks: List[Any],
        matched_chunks: List[Any],
        standards_route: Any = None,
    ) -> Optional[Dict[str, Any]]:
        if not cls._should_enforce_candidate_standards(standards_route):
            return None
        return {
            "enforced": True,
            "required": cls._route_candidate_standard_ids(standards_route),
            "retrieved": sorted({
                standard
                for chunk in retrieved_chunks
                for standard in [cls._chunk_standard_id(chunk)]
                if standard
            }),
            "matched": sorted({
                standard
                for chunk in matched_chunks
                for standard in [cls._chunk_standard_id(chunk)]
                if standard
            }),
        }

    @staticmethod
    def _should_enforce_candidate_standards(standards_route: Any = None) -> bool:
        if not standards_route or not getattr(standards_route, "candidate_standards", None):
            return False
        primary_values = {
            getattr(family, "value", family)
            for family in (getattr(standards_route, "primary", []) or [])
        }
        return SourceFamily.SHARIA_STANDARD.value in primary_values

    @classmethod
    def _route_candidate_standard_ids(cls, standards_route: Any = None) -> List[str]:
        values = getattr(standards_route, "candidate_standards", []) or []
        return sorted({
            normalised
            for value in values
            for normalised in [cls._normalize_standard_id(str(value))]
            if normalised
        })

    @classmethod
    def _chunk_standard_id(cls, chunk: Any) -> Optional[str]:
        metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else getattr(chunk, "metadata", {}) or {}
        candidates = [
            metadata.get("standard_number"),
            metadata.get("standard_id"),
            metadata.get("source_id"),
            metadata.get("document_id"),
            metadata.get("source_file"),
        ]
        citation = None if isinstance(chunk, dict) else getattr(chunk, "citation", None)
        if citation is not None:
            candidates.extend(
                [
                    getattr(citation, "standard_id", None),
                    getattr(citation, "source_file", None),
                ]
            )
        for candidate in candidates:
            standard = cls._normalize_standard_id(str(candidate or ""))
            if standard:
                return standard
        return None

    @staticmethod
    def _normalize_standard_id(value: str) -> str:
        text = (value or "").strip().upper()
        if not text:
            return ""
        match = re.search(r"\b(SS|FAS)[-_\s]*0*(\d{1,3})\b", text)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}"
        sharia_match = re.search(r"SHARIA[_\s-]*STANDARD[_\s-]*0*(\d{1,3})", text)
        if sharia_match:
            return f"SS-{int(sharia_match.group(1)):02d}"
        return ""

    def _citations_for_chunks(self, chunks: List[Any]) -> List[AAOIFICitation]:
        citations: List[AAOIFICitation] = []
        seen: set[tuple[str, Optional[str]]] = set()
        for chunk in chunks:
            citation = self.citation_validator.citation_for_chunk(chunk)
            if citation is None:
                continue
            key = (citation.standard_number, citation.section_number)
            if key in seen:
                continue
            seen.add(key)
            citations.append(citation)
        return citations

    @staticmethod
    def _governed_metadata_required() -> bool:
        raw_value = os.getenv("REQUIRE_GOVERNED_SOURCE_METADATA")
        if raw_value is not None:
            return raw_value.strip().lower() in {"1", "true", "yes", "on"}
        return (os.getenv("APP_ENV", "dev").strip().lower() or "dev") == "production"

    @staticmethod
    def _legacy_retriever_signature_error(exc: TypeError) -> bool:
        message = str(exc)
        return "unexpected keyword argument" in message and (
            "filters" in message or "mode" in message
        )

    def _clarification_question(self, query: str, session_id: Optional[str]) -> Optional[str]:
        if not self.clarification_service:
            return None
        return self.clarification_service.ask_if_needed(query, session_id=session_id)

    def _remember_scenario_clarification(
        self,
        *,
        session_id: Optional[str],
        original_query: str,
        clarification_question: str,
        scenario: Any,
        standards_route: Any,
    ) -> None:
        state = self._session_state(session_id, create=True)
        if state is None:
            return
        state.metadata["pending_scenario_clarification"] = {
            "original_query": original_query,
            "clarification_question": clarification_question,
            "scenario": scenario.to_dict() if hasattr(scenario, "to_dict") else {},
            "standards_route": standards_route.to_dict() if hasattr(standards_route, "to_dict") else {},
        }
        state.state = ClarificationState.CLARIFYING
        self._update_session_state(state)

    def _consume_pending_scenario_clarification(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        state = self._session_state(session_id, create=False)
        if state is None:
            return None
        pending = state.metadata.pop("pending_scenario_clarification", None)
        if pending:
            state.state = ClarificationState.ANALYZING
            self._update_session_state(state)
        return pending if isinstance(pending, dict) else None

    @staticmethod
    def _query_with_pending_clarification(query: str, pending: Optional[Dict[str, Any]]) -> str:
        if not pending:
            return query
        original_query = str(pending.get("original_query") or "").strip()
        if not original_query:
            return query
        return f"{original_query} | clarification_answer: {query}"

    def _session_state(self, session_id: Optional[str], *, create: bool = False) -> Any:
        if not self.session_store or not session_id:
            return None
        state = None
        if hasattr(self.session_store, "get_session"):
            state = self.session_store.get_session(session_id)
        if state is None and create and hasattr(self.session_store, "create_session"):
            state = self.session_store.create_session(session_id)
        return state

    def _update_session_state(self, state: Any) -> None:
        if self.session_store and hasattr(self.session_store, "update_session"):
            self.session_store.update_session(state)

    @staticmethod
    def _scenario_clarification_question(
        scenario: Any,
        response_language: str,
        standards_route: Any = None,
    ) -> Optional[str]:
        if getattr(standards_route, "route_id", None) == "bay-al-wafa":
            if response_language == "ar":
                return "\u0628\u064a\u0639 \u0627\u0644\u0648\u0641\u0627\u0621 \u0645\u0633\u0623\u0644\u0629 \u062e\u0644\u0627\u0641\u064a\u0629. \u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u0631\u062c\u064a\u062d \u062c\u0647\u0629 \u0631\u0642\u0627\u0628\u0629 \u0634\u0631\u0639\u064a\u0629 \u0645\u0639\u064a\u0646\u0629 \u0623\u0645 \u0639\u0631\u0636 \u0627\u0644\u0623\u062f\u0644\u0629 \u0648\u0623\u0648\u062c\u0647 \u0627\u0644\u062e\u0644\u0627\u0641\u061f"
            return "Bay al-Wafa is disputed. Should I ground the answer in a specific Sharia board or present the evidence and areas of disagreement?"
        missing_facts = set(getattr(scenario, "missing_facts", []) or [])
        if (
            getattr(scenario, "contract_family", None) == ContractFamily.ISTISNA
            and getattr(scenario, "late_payment_terms", None)
            and "delay_responsible_party" in missing_facts
        ):
            if response_language == "ar":
                return "\u0647\u0644 \u0627\u0644\u063a\u0631\u0627\u0645\u0629 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0642\u0627\u0648\u0644 \u0641\u064a \u0627\u0644\u062a\u0633\u0644\u064a\u0645 \u0623\u0645 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0639\u0645\u064a\u0644 \u0641\u064a \u0627\u0644\u0633\u062f\u0627\u062f\u061f"
            return "Is the penalty because the contractor was late delivering, or because the customer was late paying?"
        if (
            getattr(scenario, "contract_family", None) == ContractFamily.MURABAHA
            and {"ownership_sequence", "possession_or_risk_bearing"} & missing_facts
            and getattr(scenario, "asset", None)
            and not getattr(scenario, "payment_terms", None)
            and not getattr(scenario, "profit_basis", None)
            and not getattr(scenario, "late_payment_terms", None)
        ):
            if response_language == "ar":
                return "\u0647\u0644 \u062a\u0645\u0644\u0643 \u0627\u0644\u0628\u0646\u0643 \u0627\u0644\u0633\u064a\u0627\u0631\u0629 \u0648\u0642\u0628\u0636\u0647\u0627 \u0623\u0648 \u062a\u062d\u0645\u0644 \u0645\u062e\u0627\u0637\u0631\u0647\u0627 \u0642\u0628\u0644 \u0628\u064a\u0639\u0647\u0627 \u0644\u0643\u061f"
            return "Did the bank own, take possession of, or bear the risk of the car before selling it to you?"
        if (
            getattr(scenario, "contract_family", None) == ContractFamily.IJARAH
            and "maintenance_type" in missing_facts
        ):
            if response_language == "ar":
                return "\u0647\u0644 \u062a\u0642\u0635\u062f \u0627\u0644\u0635\u064a\u0627\u0646\u0629 \u0627\u0644\u0625\u0646\u0634\u0627\u0626\u064a\u0629 \u0623\u0648 \u0627\u0644\u062c\u0648\u0647\u0631\u064a\u0629\u060c \u0623\u0645 \u0627\u0644\u0635\u064a\u0627\u0646\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644\u064a\u0629 \u0623\u0648 \u0627\u0644\u0628\u0633\u064a\u0637\u0629\u061f"
            return "Do you mean structural or major maintenance, or operational or routine maintenance?"
        return None

    def _history(
        self,
        session_id: Optional[str],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        if conversation_history:
            return [
                {
                    "role": str(message.get("role", ""))[:20],
                    "content": str(message.get("content", ""))[:2000],
                }
                for message in conversation_history[-10:]
                if isinstance(message, dict) and message.get("role") and message.get("content")
            ]
        if not self.session_store:
            return []
        if hasattr(self.session_store, "history_for"):
            return self.session_store.history_for(session_id)
        state = self._session_state(session_id, create=False)
        if state is None:
            return []
        return [
            {
                "role": str(getattr(message, "role", ""))[:20],
                "content": str(getattr(message, "content", ""))[:2000],
            }
            for message in getattr(state, "conversation_history", [])[-10:]
            if getattr(message, "role", None) and getattr(message, "content", None)
        ]

    def _build_prompt(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
        response_language: str = "en",
    ) -> str:
        """Build a single-string prompt for callers without build_messages() support."""
        build_signature = signature(self.prompt_builder.build)
        params = build_signature.parameters
        accepts_kwargs = any(param.kind == Parameter.VAR_KEYWORD for param in params.values())
        kwargs = {"history": history, "response_language": response_language}
        supported_kwargs = {
            key: value
            for key, value in kwargs.items()
            if accepts_kwargs or key in params
        }
        return self.prompt_builder.build(query, chunks, **supported_kwargs)


    def _audit(
        self,
        query: str,
        answer: AnswerContract,
        session_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        if not self.audit_store:
            return
        self.audit_store.log_answer(
            query=query,
            answer=answer,
            session_id=session_id,
            request_id=request_id,
        )

    def _append_scholar_review_queue(
        self,
        *,
        query: str,
        answer: AnswerContract,
        queue: ScholarReviewQueue,
        flag_reason: str,
        session_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        if not self.scholar_review_queue_store:
            return
        item = ScholarReviewQueueItem.from_answer(
            queue=queue,
            query=query,
            answer=answer,
            flag_reason=flag_reason,
            query_id=request_id,
            request_id=request_id,
            session_id=session_id,
        )
        self.scholar_review_queue_store.append(item)

    def _maybe_append_random_scholar_sample(
        self,
        *,
        query: str,
        answer: AnswerContract,
        session_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        if (
            not self.scholar_review_queue_store
            or answer.status == ComplianceStatus.CLARIFICATION_NEEDED
            or self.scholar_sampling_rate <= 0.0
            or self.scholar_sampler() >= self.scholar_sampling_rate
        ):
            return
        self._append_scholar_review_queue(
            query=query,
            answer=answer,
            queue=ScholarReviewQueue.RANDOM_SAMPLE,
            flag_reason="random_post_launch_sample",
            session_id=session_id,
            request_id=request_id,
        )

    def _cached_answer(self, query: str, standards_route: Any = None) -> Optional[AnswerContract]:
        if not self.cache_store or self._eval_mode():
            return None
        cached = self.cache_store.get_json("response", self._cache_key(query, standards_route))
        if not cached:
            return None
        answer = self._contract_from_dict(cached)
        answer.metadata = {**answer.metadata, "cache_hit": True}
        if "decision_trace" not in answer.metadata:
            answer.metadata["trace_unavailable"] = True
        return answer

    def _cache_answer(self, query: str, answer: AnswerContract, standards_route: Any = None) -> None:
        if (
            not self.cache_store
            or self._eval_mode()
            or answer.status == ComplianceStatus.CLARIFICATION_NEEDED
        ):
            return
        self.cache_store.set_json(
            "response",
            self._cache_key(query, standards_route),
            self._attach_decision_trace(answer).to_dict(),
            self.response_cache_ttl,
        )

    def _cache_key(self, query: str, standards_route: Any = None) -> str:
        payload = {
            "public_answer_policy": "literal-support-v2",
            "query": query.strip().lower(),
            "prompt_version": getattr(self.prompt_builder, "prompt_version", None),
            "model_name": getattr(self.llm_client, "model_name", None),
            "corpus_version": os.getenv("AAOIFI_CORPUS_VERSION", "unknown"),
            "index_version": os.getenv("AAOIFI_INDEX_VERSION", "unknown"),
            "source_catalog_file": os.getenv("SOURCE_CATALOG_FILE", ""),
            "source_governance_required": os.getenv("REQUIRE_GOVERNED_SOURCE_METADATA", ""),
            "retrieval_mode": os.getenv("RETRIEVAL_MODE", "dense"),
            "embedding_model": os.getenv("EMBED_MODEL", ""),
            "retriever": type(self.retriever).__name__ if self.retriever else "lazy",
            "route_id": getattr(standards_route, "route_id", None),
            "source_family_filter": self._retrieval_filters(standards_route),
            "k": self.k,
            "threshold": self.threshold,
        }
        return CacheStore.stable_key(json.dumps(payload, sort_keys=True))

    @staticmethod
    def _eval_mode() -> bool:
        return os.getenv("RAG_EVAL_MODE", "false").lower() == "true"

    @staticmethod
    def _requires_disclaimer(disclaimer_acknowledged: bool) -> bool:
        return os.getenv("REQUIRE_DISCLAIMER_ACK", "false").lower() == "true" and not disclaimer_acknowledged

    @staticmethod
    def _contract_from_dict(data: Dict[str, Any]) -> AnswerContract:
        return AnswerContract(
            answer=data["answer"],
            status=ComplianceStatus(data["status"]),
            citations=[
                AAOIFICitation(
                    document_id=citation["document_id"],
                    standard_number=citation["standard_number"],
                    section_number=citation.get("section_number"),
                    section_title=citation.get("section_title"),
                    excerpt=citation.get("excerpt"),
                    captured_at=citation.get("captured_at"),
                    quote_start=citation.get("quote_start"),
                    quote_end=citation.get("quote_end"),
                    source_version=citation.get("source_version"),
                )
                for citation in data.get("citations", [])
            ],
            reasoning_summary=data.get("reasoning_summary", ""),
            limitations=data.get("limitations")
            or "Informational guidance only; consult a qualified Sharia scholar for a binding ruling.",
            clarification_question=data.get("clarification_question"),
            metadata=data.get("metadata", {}),
        )

    def _metadata(
        self,
        chunks: List[Any],
        response_language: str = "en",
        scenario: Any = None,
        standards_route: Any = None,
        rule_evaluation: Any = None,
        verdict_contract: Any = None,
        source_families: Optional[set] = None,
        candidate_standard_filter: Optional[Dict[str, Any]] = None,
        scholar_review_workflow: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "model_name": getattr(self.llm_client, "model_name", None),
            "prompt_version": getattr(self.prompt_builder, "prompt_version", None),
            "response_language": response_language,
            "retrieved_chunk_ids": [self._chunk_id(chunk) for chunk in chunks],
        }
        if scenario is not None:
            metadata["transaction_scenario"] = scenario.to_dict()
        if standards_route is not None:
            metadata["standards_route"] = standards_route.to_dict()
        if rule_evaluation is not None:
            metadata["rule_evaluation"] = rule_evaluation.to_dict()
        if verdict_contract is not None:
            metadata["verdict_contract"] = verdict_contract.to_dict()
        if source_families is not None:
            metadata["source_families"] = sorted(family.value for family in source_families)
        if candidate_standard_filter is not None:
            metadata["candidate_standard_filter"] = candidate_standard_filter
        if scholar_review_workflow is not None:
            metadata["scholar_review_workflow"] = scholar_review_workflow
        return metadata

    def _unsupported_modern_asset_contract(
        self,
        query: str,
        response_language: str,
        chunks: List[Any],
        scenario: Any,
        standards_route: Any,
        rule_evaluation: Any,
        candidate_standard_filter: Optional[Dict[str, Any]],
    ) -> Optional[AnswerContract]:
        if not self._is_unsupported_modern_asset_query(query):
            return None
        if response_language == "ar":
            answer = (
                "\u0644\u0627 \u062a\u062a\u0646\u0627\u0648\u0644 \u0627\u0644\u0645\u0642\u0627\u0637\u0639 "
                "\u0627\u0644\u0645\u0633\u062a\u0631\u062c\u0639\u0629 \u0645\u0646 \u0645\u0639\u0627\u064a\u064a\u0631 "
                "\u0623\u064a\u0648\u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u0623\u0635\u0644 \u0623\u0648 "
                "\u0647\u0630\u0647 \u0627\u0644\u0645\u0636\u0627\u0631\u0628\u0629 \u0628\u0634\u0643\u0644 "
                "\u0643\u0627\u0641\u060c \u0641\u0644\u0627 \u064a\u0645\u0643\u0646 \u062a\u0642\u062f\u064a\u0645 "
                "\u062a\u0642\u064a\u064a\u0645 \u0622\u0645\u0646 \u062f\u0648\u0646 \u062f\u0644\u064a\u0644 "
                "\u0634\u0631\u0639\u064a \u0645\u062d\u062f\u062f \u0648\u0645\u0631\u0627\u062c\u0639\u0629 "
                "\u0645\u0624\u0647\u0644\u0629."
            )
        else:
            answer = (
                "The retrieved AAOIFI excerpts do not address this modern asset or speculation scenario "
                "well enough for a safe assessment. A qualified Sharia reviewer should evaluate the specific "
                "asset, trading purpose, custody, gharar, and counterparty terms."
            )
        return AnswerContract(
            answer=answer,
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[],
            reasoning_summary=(
                "The query concerns a modern/unsupported asset class outside the currently grounded source coverage."
            ),
            limitations=self._limitations(response_language),
            metadata=self._metadata(
                chunks,
                response_language=response_language,
                scenario=scenario,
                standards_route=standards_route,
                rule_evaluation=rule_evaluation,
                candidate_standard_filter=candidate_standard_filter,
            ),
        )

    @staticmethod
    def _is_unsupported_modern_asset_query(query: str) -> bool:
        lowered = (query or "").lower()
        crypto_terms = (
            "crypto",
            "cryptocurrency",
            "bitcoin",
            "btc",
            "token",
            "\u0639\u0645\u0644\u0629 \u0645\u0634\u0641\u0631\u0629",
            "\u0639\u0645\u0644\u0627\u062a \u0645\u0634\u0641\u0631\u0629",
            "\u0643\u0631\u064a\u0628\u062a\u0648",
            "\u0628\u062a\u0643\u0648\u064a\u0646",
        )
        speculation_terms = (
            "speculation",
            "trade quickly",
            "quick profit",
            "\u0645\u0636\u0627\u0631\u0628\u0629",
            "\u0627\u0644\u0645\u0636\u0627\u0631\u0628\u0629",
            "\u0627\u0644\u0633\u0631\u064a\u0639\u0629",
        )
        ruling_terms = ("halal", "haram", "\u062d\u0644\u0627\u0644", "\u062d\u0631\u0627\u0645", "\u064a\u062c\u0648\u0632")
        return any(term in lowered for term in crypto_terms) and (
            any(term in lowered for term in speculation_terms)
            or any(term in lowered for term in ruling_terms)
        )

    @staticmethod
    def _scholar_review_workflow(
        *,
        rule_evaluation: Any,
        citation_count: int,
    ) -> Dict[str, Any]:
        return {
            "required": True,
            "path": "scholar_review_enhancement",
            "blocks_main_app": False,
            "human_review_status": "pending",
            "runtime_governance_update_allowed": False,
            "export_ready": citation_count > 0,
            "citation_count": citation_count,
            "review_fields": [
                "human_scholar_review",
                "human_scholar_review_references",
                "human_scholar_review_notes",
            ],
            "reason": (
                "Rule evaluation requires scholar review before any verdict; "
                "the app may still return the evaluation trace and AAOIFI references."
            ),
        }

    @staticmethod
    def _detect_language(query: str) -> str:
        """Detect query language using character ratio (>50% Arabic = ar).

        Ratio-based approach avoids false positives from code-mixed queries
        like 'What is مرابحة?' which contain only a single Arabic word.
        """
        if not query:
            return "en"
        requested = list(re.finditer(r"(?:answer|respond|reply|explain)\s+(?:to me\s+)?in\s+(English|Arabic)|"
            r"(?:اجب|أجب|رد|اشرح|جاوب)\s*(?:ب|بال)(العربية|عربية|الانجليزية|الإنجليزية|انجليزي|انجليزى|انجليزيه)", query, re.I))
        if requested:
            value = requested[-1][1] or requested[-1][2]
            return "ar" if value.lower() == "arabic" or "عرب" in value else "en"
        arabic_chars = sum(1 for c in query if '\u0600' <= c <= '\u06ff')
        ratio = arabic_chars / len(query)
        return "ar" if arabic_chars >= 12 or ratio > 0.35 else "en"

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize user input for better retrieval:
        1. Strip Arabic diacritics (tashkeel) that cause embedding mismatches.
        2. Normalize Arabic hamza variants to plain alef.
        3. Map common English transliteration misspellings to canonical forms.
        """
        # Arabic normalization
        result = _ARABIC_DIACRITICS.sub('', query)
        result = _HAMZA_NORM.sub('\u0627', result)  # → ا
        # English transliteration normalization (case-insensitive)
        for pattern, replacement in _TRANSLITERATION_MAP.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def _limitations(response_language: str) -> str:
        if response_language == "ar":
            return "إرشاد معلوماتي فقط؛ استشر عالما شرعيا مؤهلا للحصول على حكم ملزم."
        return "Informational guidance only; consult a qualified Sharia scholar for a binding ruling."

    @staticmethod
    def _disclaimer_acknowledgement_message(response_language: str) -> str:
        if response_language == "ar":
            return "يرجى الإقرار بتنبيه الإرشاد الشرعي قبل المتابعة."
        return ApplicationService._disclaimer_acknowledgement_question(response_language)

    @staticmethod
    def _disclaimer_acknowledgement_question(response_language: str) -> str:
        if response_language == "ar":
            return "هل تقر بأن مشير يقدم إرشادا معلوماتيا فقط وليس حكما شرعيا ملزما؟"
        return "Do you acknowledge that Mushir provides informational guidance only and not a binding Sharia ruling?"

    @staticmethod
    def _clarification_answer(clarification: str, response_language: str) -> str:
        if response_language == "ar":
            return f"أحتاج إلى تفصيل واحد قبل مراجعة مقاطع أيوفي: {clarification}"
        return f"I need one detail before checking the AAOIFI evidence: {clarification}"

    @staticmethod
    def _clarification_reason(clarification: str, response_language: str) -> str:
        if response_language == "ar":
            return "السؤال غير مكتمل؛ هذا التفصيل مطلوب قبل تقديم إجابة مستندة إلى مقاطع أيوفي."
        return f"The question is missing a material fact needed for a grounded AAOIFI answer: {clarification}"

    @staticmethod
    def _not_addressed_message(response_language: str) -> str:
        if response_language == "ar":
            return "لا تتناول المقاطع المسترجعة من معايير أيوفي هذا السؤال بشكل كاف."
        return "Not addressed in retrieved AAOIFI standards."

    @staticmethod
    def _retrieval_unavailable_message(response_language: str) -> str:
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: \u062a\u0639\u0630\u0631 \u0627\u0644\u0648\u0635\u0648\u0644 "
                "\u0625\u0644\u0649 \u0641\u0647\u0631\u0633 \u0623\u062f\u0644\u0629 \u0623\u064a\u0648\u0641\u064a "
                "\u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u0646\u0634\u0631. "
                "\u0644\u0630\u0644\u0643 \u0644\u0627 \u064a\u0633\u062a\u0637\u064a\u0639 \u0645\u0634\u064a\u0631 "
                "\u062a\u0642\u062f\u064a\u0645 \u0625\u062c\u0627\u0628\u0629 \u0645\u0633\u062a\u0646\u062f\u0629 "
                "\u0622\u0645\u0646\u0629 \u0627\u0644\u0622\u0646. \u064a\u0631\u062c\u0649 \u0625\u0639\u0627\u062f\u0629 "
                "\u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629 \u0644\u0627\u062d\u0642\u0627 \u0623\u0648 "
                "\u0625\u0628\u0644\u0627\u063a \u0627\u0644\u0645\u0634\u063a\u0644 \u0628\u0623\u0646 "
                "\u062e\u062f\u0645\u0629 \u0627\u0644\u0627\u0633\u062a\u0631\u062c\u0627\u0639 \u063a\u064a\u0631 "
                "\u062c\u0627\u0647\u0632\u0629."
            )
        return (
            "INSUFFICIENT_DATA: Mushir could not reach the AAOIFI evidence index in this deployment, "
            "so it cannot provide a safely cited answer right now. Please try again later or ask the "
            "operator to check the retriever/index readiness."
        )

    @staticmethod
    def _is_authority_request(query: str) -> bool:
        """Check if the user is requesting a binding ruling, fatwa, or legal advice.

        Uses simple substring match because regex word-boundary assertions
        would fail on Arabic terms.
        Simple substring is safe here because the term list is specific enough
        that false positives (refusing a query that should be answered) are
        unlikely, and are strictly safer than false negatives.
        """
        if not query:
            return False
        lowered = query.lower()
        for term in AUTHORITY_REQUEST_TERMS:
            if term in lowered:
                return True
        return False

    @staticmethod
    def _empty_query_response() -> AnswerContract:
        return AnswerContract(
            answer="Please provide a question about Sharia compliance.",
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[],
            reasoning_summary="Empty or whitespace-only query.",
            limitations="Informational guidance only; consult a qualified Sharia scholar for a binding ruling.",
            metadata={"response_language": "en", "cache_hit": False, "decision_basis": "empty_request"},
        )

    @staticmethod
    def _authority_refusal_message(response_language: str) -> str:
        if response_language == "ar":
            return (
                "مشير يقدم إرشادا معلوماتيا فقط بناء على مقاطع معايير أيوفي المسترجعة. "
                "لا يصدر فتاوى ملزمة أو آراء قانونية أو نصائح مالية. "
                "استشر عالما شرعيا مؤهلا للحصول على حكم شرعي ملزم."
            )
        return (
            "Mushir provides informational guidance only, grounded in retrieved AAOIFI excerpts. "
            "It does not issue binding fatwas, legal opinions, or financial advice. "
            "Consult a qualified Sharia scholar for a binding religious ruling."
        )

    @staticmethod
    def _insufficient_data_message(response_language: str) -> str:
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: لا توفر المقاطع المسترجعة من معايير أيوفي أساسا "
                "قابلا للاستشهاد بأمان لهذه الإجابة. يرجى تقديم تفاصيل إضافية أو "
                "استشارة عالم شرعي مؤهل."
            )
        return (
            "INSUFFICIENT_DATA: The retrieved AAOIFI excerpts did not provide "
            "a safely citable basis for this answer. Please provide more details "
            "or consult a qualified Sharia scholar."
        )

    @staticmethod
    def _source_family_gap_message(response_language: str) -> str:
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: هذا السؤال يتعلق بجواز أو صحة معاملة تجارية، "
                "وهذا يحتاج إلى دليل من معايير شرعية وقواعد تقييم صريحة. "
                "المقاطع المسترجعة حاليا لا تكفي لإصدار تقييم آمن؛ يرجى عرض العقد على عالم شرعي أو مراجع امتثال مؤهل."
            )
        return (
            "INSUFFICIENT_DATA: This question asks about permissibility or contract validity. "
            "Mushir needs Shari'ah-standard evidence and explicit rule checks before giving even a non-binding assessment. "
            "The retrieved evidence is not enough; refer the contract to a qualified Sharia scholar or compliance reviewer."
        )

    @staticmethod
    def _rule_review_required_message(response_language: str) -> str:
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: تتطلب هذه المعاملة مراجعة قواعد شرعية وأدلة "
                "مصدرية إضافية قبل تقديم تقييم آمن؛ يرجى إحالتها إلى مراجع شرعي مؤهل."
            )
        return (
            "INSUFFICIENT_DATA: This scenario requires explicit rule evidence and "
            "human review before Mushir can provide a safe non-binding assessment."
        )

    @staticmethod
    def _chunk_id(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("chunk_id") or chunk.get("id") or "")
        return str(getattr(chunk, "chunk_id", ""))

    @staticmethod
    def _without_language_instruction(query):
        stripped = re.sub(r"(?:please\s+)?(?:answer|respond|reply|explain)\s+(?:to me\s+)?in\s+(?:English|Arabic)|"
            r"(?:اجب|أجب|رد|اشرح|جاوب)\s*(?:ب|بال)(?:العربية|عربية|الانجليزية|الإنجليزية|انجليزي|انجليزى|انجليزيه)",
            "", query or "", flags=re.I)
        return stripped.strip(" .,:،") if stripped != query else query

    def _purpose_clarification(self, query, language, session_id, keep_session):
        broad = bool(re.fullmatch(r"\s*(?:please )?(?:help(?: me)?(?: with)?|I need help(?: with)?)\s+(?:financ(?:e|ing)|instal+ments?|BNPL)[.!?]?\s*|"
            r"\s*(?:ساعدني|عايز مساعدة|أريد مساعدة|اريد مساعدة)\s*(?:في|بخصوص)?\s*(?:التمويل|التقسيط)[.!؟]?\s*", query, re.I))
        state = self._session_state(session_id)
        pending = bool(state and state.metadata.pop("purpose_clarification", None))
        if pending:
            self._update_session_state(state)
        if not broad and not pending:
            return None
        if pending and not broad:
            if self._is_definition_query(self._normalize_query(query)):
                return None
            if re.search(r"\b(?:my|a) (?:purchase|transaction|agreement|contract)\b|شراء|معاملة|عقدي", query, re.I):
                question = ("مين مقدم خطة التقسيط: المحل نفسه ولا بنك أو شركة تمويل؟" if language == "ar" else
                            "Who provides the instalment plan—the store itself, or a bank or finance company?")
                # Purpose alone is not a transaction fact. A full description on
                # this turn continues through the typed operation lane normally.
                if self.described_operations.accepts(query):
                    return None
                reason = "financing_party_unknown"
            elif re.search(r"definition|meaning|تعريف|معنى", query, re.I):
                question = ("أي مفهوم تريد تعريفه؟" if language == "ar" else "Which concept would you like defined?")
                reason = "purpose_needed"
            else:
                return AnswerContract(answer=("حدد المفهوم أو أرسل وصف المعاملة وجهة التمويل؛ لا تتوافر معلومات لتقييمها."
                    if language == "ar" else "Name the concept or describe the transaction and financing party; an assessment is unavailable without those details."),
                    status=ComplianceStatus.INSUFFICIENT_DATA, metadata={"response_language": language,
                    "decision_basis": "purpose_unavailable"})
        else:
            question = ("هل تريد تعريف مفهوم، أم فهم شروط معاملة تخصك، أم شرحًا محاسبيًا؟" if language == "ar" else
                        "Would you like a concept definition, help understanding your transaction terms, or an accounting explanation?")
            reason = "purpose_needed"
            state = state or self._session_state(session_id, create=keep_session)
            if state:
                state.metadata["purpose_clarification"] = True
        if state:
            state.add_message("user", query)
            state.add_message("assistant", question)
            self._update_session_state(state)
        return AnswerContract(answer=question, status=ComplianceStatus.CLARIFICATION_NEEDED,
            clarification_question=question, metadata={"response_language": language,
            "decision_basis": reason if reason == "purpose_needed" else None, "question_origin": "deterministic"})

    @staticmethod
    def _definition_terms(query):
        groups = (("murabaha", "murabahah", "المرابحة", "مرابحة"),
                  ("ijara", "ijarah", "الإجارة", "إجارة", "الاجارة", "اجارة"),
                  ("mudaraba", "mudarabah", "المضاربة", "مضاربة"),
                  ("musharaka", "musharakah", "المشاركة", "مشاركة"),
                  ("tawarruq", "التورق", "تورق"), ("sukuk", "الصكوك", "صكوك"),
                  ("salam", "السلم"), ("istisna", "istisna'a", "الاستصناع", "استصناع"),
                  ("riba", "الربا", "ربا"), ("zakat", "الزكاة", "زكاة"))
        return next((group for group in groups if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", query, re.I)
                                                    for term in group)), ())

    def _add_requested_definition(self, query, answer):
        """Supplement a withheld mixed request with a separately supported quotation."""
        if not isinstance(answer, AnswerContract) or not query or answer.metadata.get("answer_kind") == "definition":
            return answer
        if answer.metadata.get("decision_basis") in {"scope_refusal", "current_offer_unverified"} or answer.metadata.get("disclaimer_required"):
            return answer
        match = re.search(r"(?:what (?:is|are)|define|explain|ما هي|ما هو|ما معنى|اشرح|عرف)\s+"
            r"(murabaha[h]?|ijara[h]?|mudaraba[h]?|musharaka[h]?|tawarruq|sukuk|riba|zakat|المرابحة|مرابحة|الإجارة|الاجارة|المضاربة|المشاركة|التورق|الصكوك|الربا|الزكاة)", query, re.I)
        if not match or self._is_definition_query(self._normalize_query(query)):
            return answer
        definition_query = "What is " + match[1] + "?"
        try:
            if self.retriever is None:
                return answer
            chunks = self._answer_admissible_chunks(self._retrieve(definition_query, k=max(self.k * 8, 40), threshold=self.threshold))
            limit = self._source_limit_contract(definition_query, chunks, answer.metadata.get("response_language", "en"))
            definition = None if limit else self._definition_answer_if_supported(definition_query, chunks, answer.metadata.get("response_language", "en"))
        except Exception:
            definition = None
        if definition:
            answer.answer = definition.answer + "\n\n" + answer.answer
            answer.citations = definition.citations
            answer.metadata["supported_definition"] = {"claim_support": "literal_quote_only", "assessment": "withheld"}
        return answer

    def _source_limit_contract(self, query, chunks, language):
        """An unresolved document identity or current-offer request cannot authorize claims."""
        current_offer = bool(re.search(r"\b(?:current|today|latest|offer|BNPL provider)\b|العرض|عروض|حاليا|الحالي|النهارده", query, re.I))
        grouped = {}
        for chunk in chunks:
            terms = self._definition_terms(query) if self._is_definition_query(query) else ()
            citation = (self.citation_validator.definition_citation(chunk, terms) if terms else
                        self.citation_validator.citation_for_chunk(chunk))
            if citation:
                grouped.setdefault((citation.standard_number, citation.section_number), []).append(citation)
        conflicting = any(len({c.source_version for c in items if c.source_version}) > 1
                          and len({c.excerpt for c in items}) > 1 for items in grouped.values())
        if not current_offer and not conflicting:
            return None
        reason = "current_offer_unverified" if current_offer else "source_versions_conflict"
        text = (("لا تتوافر مستندات عرض حالي موثقة؛ تاريخ المقطع أو اسم الشركة لا يثبت شروط عقدك. اطلب نسخة العقد وبيان العرض من جهة التمويل."
                 if language == "ar" else "Verified current-offer documents are unavailable; a passage date or company name does not establish your contract terms. Request the agreement and offer disclosure from the financier.")
                if current_offer else ("نسخ المصادر تختلف ولم تُحسم هوية النسخة المناسبة؛ سأحجب الشرح المعتمد عليها إلى أن تُراجع الوثائق."
                 if language == "ar" else "Source versions differ and the applicable version is unresolved; I am withholding the explanation that depends on them until the documents are reviewed."))
        return AnswerContract(answer=text, status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[c for items in grouped.values() for c in items], metadata={"response_language": language,
            "decision_basis": reason, "source_limitation": reason})

    def _definition_answer_if_supported(
        self,
        query: str,
        chunks: List[Any],
        response_language: str,
    ) -> Optional[AnswerContract]:
        if not self._is_definition_query(query):
            return None
        if self.citation_validator.citation_pattern.search(query):
            resolved = {(c.document_id, c.section_number, c.source_version) for c in
                        self.citation_validator.validate(query, chunks)}
            chunks = [chunk for chunk in chunks if (c := self.citation_validator.citation_for_chunk(chunk))
                      and (c.document_id, c.section_number, c.source_version) in resolved]
        terms = self._definition_terms(query)
        import math
        def valid_signal(chunk):
            raw = (chunk.get("similarity", chunk.get("score")) if isinstance(chunk, dict)
                   else getattr(chunk, "score", None))
            return type(raw) in {int, float} and math.isfinite(raw) and 0 <= raw <= 1
        citation = next((citation for chunk in chunks if valid_signal(chunk)
                         if (citation := self.citation_validator.definition_citation(chunk, terms))), None) if terms else None
        if citation is None:
            return None
        marker = self._inline_citation_marker(citation)
        answer = self._definition_answer_text(citation.excerpt or "", marker, response_language)
        return AnswerContract(
            answer=answer,
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[citation],
            reasoning_summary="Extractive definition from the identified source passage; transaction assessment withheld.",
            limitations=self._limitations(response_language),
            metadata={**self._metadata(
                chunks,
                response_language=response_language,
            ), "answer_kind": "definition", "claim_support": "literal_quote_only"},
        )

    @classmethod
    def _is_definition_query(cls, query: str) -> bool:
        if not query:
            return False
        lowered = query.strip().lower()
        blocking_terms = (
            "compliant",
            "allowed",
            "permissible",
            "requirements",
            "requirement",
            "conditions",
            "is it halal",
            "halal",
            "haram",
            "is my agreement",
            "is my contract",
            "حكم",
            "يجوز",
            "حلال",
            "شروط",
            "متطلبات",
        )
        if any(term in lowered for term in blocking_terms):
            return False
        english_starters = (
            "what is ",
            "what are ",
            "define ",
            "explain ",
            "tell me about ",
        )
        arabic_starters = (
            "ما هي ",
            "ما هو ",
            "ما معنى ",
            "عرف ",
            "اشرح ",
        )
        arabic_starters = arabic_starters + ("ما هي ", "ما هو ", "ما معنى ", "عرف ", "اشرح ")
        return lowered.startswith(english_starters) or lowered.startswith(arabic_starters)

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("content") or chunk.get("text") or "")
        return str(getattr(chunk, "text", ""))

    @staticmethod
    def _inline_citation_marker(citation: AAOIFICitation) -> str:
        if citation.section_number:
            return f"[{citation.standard_number} §{citation.section_number}]"
        return f"[{citation.standard_number}]"

    @staticmethod
    def _definition_answer_text(excerpt: str, marker: str, response_language: str) -> str:
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: هذا سؤال تعريفي وليس تقييما لحالة امتثال محددة.\n\n"
                f"اقتباس حرفي باللغة الأصلية من المقطع المسترجع من أيوفي: {excerpt} {marker}\n\n"
                "هذا المقطع لا يثبت انطباق التعريف على عقدك؛ نسخة المصدر أو تاريخها قد يكونان غير معلومين.\n\n"
                "لإصدار تقييم امتثال، أحتاج تفاصيل المعاملة نفسها مثل الأصل، وتسلسل التملك، "
                "والثمن، والربح، وشروط الدفع."
            )
        return (
            "INSUFFICIENT_DATA: This is a definition question, not a compliance assessment for a specific transaction.\n\n"
            f"Literal quotation in the source's original language: {excerpt} {marker}\n\n"
            "This passage does not establish applicability to your contract; the source version or date may be unknown.\n\n"
            "For a compliance assessment, provide the transaction facts, including the asset, ownership sequence, "
            "price, profit, and payment terms."
        )

    @staticmethod
    def _status_from_answer(answer: str, citations) -> ComplianceStatus:
        """Derive compliance status. Delegates to shared function."""
        from src.chatbot.compliance_analyzer import derive_compliance_status
        return derive_compliance_status(answer, citations)

    @classmethod
    def _llm_clarification_question(cls, answer: str, citations) -> Optional[str]:
        if citations:
            return None
        text = (answer or "").strip()
        if not text:
            return None
        lowered = text.lower()
        if not any(token in lowered for token in ["clarification_needed", "need more information", "need additional information", "missing"]):
            return None
        return cls._single_question_from_text(text)

    @staticmethod
    def _single_question_from_text(text: str) -> str:
        cleaned_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            stripped = re.sub(r"^(?:[-*]|\d+[.)])\s*", "", stripped)
            if stripped.lower().startswith(("phase ", "reasoning", "analysis")):
                continue
            cleaned_lines.append(stripped)
        for line in cleaned_lines:
            if line.lower().startswith("question:"):
                question = line.split(":", 1)[1].strip()
                return question if question.endswith(("?", "\u061f")) else f"{question}?"
            if "?" in line or "\u061f" in line:
                question = re.split(r"[?\u061f]", line, maxsplit=1)[0].strip()
                return f"{question}?"
        return "What is the single most important transaction detail needed to assess this against AAOIFI?"

    @staticmethod
    def _reasoning_summary(answer: str) -> str:
        return answer.strip().splitlines()[0][:300]


    def _handle_routing_stage(self, cleaned_query: str, session_family: "Any", session_turns: int):
        
        family_result = getattr(self, "family_router").classify(
            cleaned_query, 
            session_family=session_family, 
            session_confirmation_turns=session_turns
        )

        matched_concepts = self.ontology.match(cleaned_query)
        concept_ids = [entry.concept_id for entry in matched_concepts]

        target_standards = resolve_bulk(concept_ids, family_result.primary_family)
            
        if family_result.mode and family_result.mode.value == "multi_path":
            for adj_fam in (getattr(family_result, "adjacent_families", []) or []):
                adj_standards = resolve_bulk(concept_ids, adj_fam)
                target_standards.extend(adj_standards)
            target_standards = list(dict.fromkeys(target_standards))

        return family_result, target_standards

    def _handle_clarification_stage(
        self,
        cleaned_query: str,
        scenario: "Any",
        standards_route: "Any",
        family_result: "Any",
        known_family: "Optional[ContractFamily]",
        session_id: "Optional[str]",
        request_id: "Optional[str]",
        response_language: str
    ) -> "Optional[AnswerContract]":
        """
        Determine whether clarification is needed before retrieval.

        Architecture decision: the ClarificationEngine's ask_if_needed() is the
        authoritative gate. The ContractFamilyRouter's mode=CLARIFICATION is an
        advisory signal only — it means "low routing confidence" but not
        necessarily "must ask the user a question".

        Concretely:
          - If the router gives a high-confidence primary family → ask_if_needed
            decides (judgment bypass fires → None → proceed).
          - If the router gives AMBIGUOUS/CLARIFICATION mode → still route through
            ask_if_needed; for self-contained judgment queries (يجوز, حكم, etc.)
            the judgment bypass fires because primary_family is not None → proceed.
          - Only if ask_if_needed returns an actual question do we surface CLARIFY.
        """
        clarification: Optional[str] = None

        scenario_clarification = self._scenario_clarification_question(
            scenario,
            response_language,
            standards_route,
        )
        if scenario_clarification:
            self._remember_scenario_clarification(
                session_id=session_id,
                original_query=cleaned_query,
                clarification_question=scenario_clarification,
                scenario=scenario,
                standards_route=standards_route,
            )
            contract = AnswerContract(
                answer=scenario_clarification,
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                clarification_question=scenario_clarification,
                reasoning_summary=self._clarification_reason(scenario_clarification, response_language),
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    [],
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                ),
            )
            contract.internal_signals["router_signals"] = getattr(family_result, "signals", {})
            contract.metadata["question_origin"] = "deterministic"
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        if self.clarification_service and (
            getattr(self, "_clarification_service_injected", False)
            or (
                getattr(getattr(family_result, "mode", None), "value", None) == "clarification"
                and known_family is not None
            )
        ):
            # Pass the known_family so ask_if_needed can apply the bypass
            # ONLY when the router is confident.
            clarification = self.clarification_service.ask_if_needed(
                cleaned_query,
                session_id=session_id,
                known_contract_family=known_family,
            )

        if clarification:
            clarification_answer = self._clarification_answer(clarification, response_language)
            contract = AnswerContract(
                answer=clarification_answer,
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                clarification_question=clarification,
                reasoning_summary=self._clarification_reason(clarification, response_language),
                limitations=self._limitations(response_language),
                metadata=self._metadata(
                    [],
                    response_language=response_language,
                ),
            )
            contract.internal_signals["router_signals"] = getattr(family_result, "signals", {})
            from src.chatbot.clarification_engine import ClarificationEngine
            if not self._clarification_service_injected or type(self.clarification_service) is ClarificationEngine:
                contract.metadata["question_origin"] = "deterministic"
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract
        return None
