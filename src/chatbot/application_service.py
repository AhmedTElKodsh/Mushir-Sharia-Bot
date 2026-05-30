import json
import os
import random
import re
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any, Dict, List, Optional

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
from src.rag.standard_resolver import all_standards_for_family, resolve_bulk
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
        self.session_store = session_store
        self.audit_store = audit_store
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

    def answer(
        self,
        query: Optional[str],
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        disclaimer_acknowledged: bool = True,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AnswerContract:
        if not query or not query.strip():
            return self._empty_query_response()
        cleaned_query = self._normalize_query(query.strip())
        response_language = self._detect_language(cleaned_query)
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
                metadata=self._metadata([], confidence=0.0, response_language=response_language),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        # Stage 1 & 2: Routing and Standard Resolution
        pending_scenario_clarification = self._consume_pending_scenario_clarification(session_id)
        session_family = pending_scenario_clarification.get("family") if pending_scenario_clarification else None
        session_turns = pending_scenario_clarification.get("turns", 0) if pending_scenario_clarification else 0
        family_result, target_standards, standards_route = self._handle_routing_stage(
            cleaned_query, session_family, session_turns
        )
        if cached := self._cached_answer(cleaned_query, standards_route):
            return cached
            
        from src.chatbot.contract_family_router import RetrievalMode
        known_family = None
        if family_result.mode in (RetrievalMode.SINGLE_PATH, RetrievalMode.MULTI_PATH):
            known_family = family_result.primary_family

        # Stage 3: Clarification Validation
        clarification_contract = self._handle_clarification_stage(
            cleaned_query,
            family_result,
            known_family,
            session_id,
            request_id,
            response_language
        )
        if clarification_contract:
            return clarification_contract

        # Stubbed legacy dependencies
        from src.chatbot.commercial_assessment import TransactionScenario, QuestionType
        analysis_query = self._query_with_pending_clarification(
            cleaned_query,
            pending_scenario_clarification,
        )
        scenario = TransactionScenario(question_type=QuestionType.PERMISSIBILITY)
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
                    metadata=self._metadata(
                        [],
                        confidence=0.0,
                        response_language=response_language,
                        scenario=scenario,
                        standards_route=standards_route,
                        rule_evaluation=rule_evaluation,
                    ),
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
                metadata=self._metadata(
                    [],
                    confidence=0.0,
                    response_language=response_language,
                    scenario=scenario,
                    standards_route=standards_route,
                    rule_evaluation=rule_evaluation,
                ),
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
                        confidence=0.0,
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
                    confidence=0.0,
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
                    confidence=self._confidence(chunks),
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
                    confidence=self._confidence(chunks),
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
                    confidence=self._confidence(chunks),
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
        if status == ComplianceStatus.INSUFFICIENT_DATA and not citations:
            answer = self._insufficient_data_message(response_language)
        contract = AnswerContract(
            answer=answer,
            status=status,
            citations=citations,
            reasoning_summary=self._reasoning_summary(answer),
            limitations=self._limitations(response_language),
            metadata=self._metadata(
                chunks,
                confidence=self._confidence(chunks),
                response_language=response_language,
                scenario=scenario,
                standards_route=standards_route,
                rule_evaluation=rule_evaluation,
                candidate_standard_filter=candidate_standard_filter,
            ),
        )
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
        # Auto-flag Q1 for low-confidence RAG
        elif self._confidence(chunks) < 0.5 or status == ComplianceStatus.INSUFFICIENT_DATA:
            self._append_scholar_review_queue(
                query=cleaned_query,
                answer=contract,
                queue=ScholarReviewQueue.AUTO_FLAGGED,
                flag_reason="low_confidence_or_insufficient_data",
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
        try:
            return self.retriever.retrieve(
                query,
                k=k,
                threshold=threshold,
                filters=filters,
                mode=mode,
            )
        except TypeError as exc:
            if not self._legacy_retriever_signature_error(exc):
                raise
            return self.retriever.retrieve(query, k=k, threshold=threshold)

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
        admissible = []
        for chunk in chunks:
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
    def _scenario_clarification_question(scenario: Any, response_language: str) -> Optional[str]:
        missing_facts = set(getattr(scenario, "missing_facts", []) or [])
        if (
            getattr(scenario, "contract_family", None) == ContractFamily.ISTISNA
            and getattr(scenario, "late_payment_terms", None)
            and "delay_responsible_party" in missing_facts
        ):
            if response_language == "ar":
                return "\u0647\u0644 \u0627\u0644\u063a\u0631\u0627\u0645\u0629 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0642\u0627\u0648\u0644 \u0641\u064a \u0627\u0644\u062a\u0633\u0644\u064a\u0645 \u0623\u0645 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0639\u0645\u064a\u0644 \u0641\u064a \u0627\u0644\u0633\u062f\u0627\u062f\u061f"
            return "Is the penalty because the contractor was late delivering, or because the customer was late paying?"
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
            answer.to_dict(),
            self.response_cache_ttl,
        )

    def _cache_key(self, query: str, standards_route: Any = None) -> str:
        payload = {
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
                    confidence_score=citation.get("confidence_score"),
                    quote_start=citation.get("quote_start"),
                    quote_end=citation.get("quote_end"),
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
        confidence: float,
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
            "confidence": confidence,
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
            metadata={"response_language": "en", "cache_hit": False},
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
    def _confidence(chunks: List[Any]) -> float:
        if not chunks:
            return 0.0
        scores = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                scores.append(float(chunk.get("similarity") or chunk.get("score") or 0.0))
            else:
                scores.append(float(getattr(chunk, "score", 0.0) or 0.0))
        return sum(scores) / len(scores)

    def _definition_answer_if_supported(
        self,
        query: str,
        chunks: List[Any],
        response_language: str,
    ) -> Optional[AnswerContract]:
        if not self._is_definition_query(query):
            return None
        chunk = self._best_definition_chunk(query, chunks)
        if chunk is None:
            return None
        citation = self.citation_validator.citation_for_chunk(chunk)
        if citation is None:
            return None
        marker = self._inline_citation_marker(citation)
        answer = self._definition_answer_text(citation.excerpt or "", marker, response_language)
        return AnswerContract(
            answer=answer,
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[citation],
            reasoning_summary=self._reasoning_summary(answer),
            limitations=self._limitations(response_language),
            metadata=self._metadata(
                chunks,
                confidence=self._confidence(chunks),
                response_language=response_language,
            ),
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

    def _best_definition_chunk(self, query: str, chunks: List[Any]) -> Optional[Any]:
        expanded_terms = {
            term.lower()
            for term in QueryPreprocessor.expand_terms(query)
            if len(term) >= 4
        }
        definition_indicators = (
            " is sale",
            " is a sale",
            " - is ",
            " – is ",
            " refers to ",
            " means ",
            "defined as",
            "definition",
            "هي ",
            "يقصد",
            "تعني",
            "تعريف",
        )

        best_chunk = None
        best_score = -1.0
        for chunk in chunks:
            text = self._chunk_text(chunk)
            lowered = text.lower()
            term_hit = any(term in lowered for term in expanded_terms)
            definition_hit = any(indicator in lowered for indicator in definition_indicators)
            if not term_hit or not definition_hit:
                continue
            score = float(getattr(chunk, "score", 0.0) or 0.0)
            if isinstance(chunk, dict):
                score = float(chunk.get("similarity") or chunk.get("score") or 0.0)
            score += 0.25
            if score > best_score:
                best_score = score
                best_chunk = chunk
        return best_chunk if best_score >= 0 else None

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
        excerpt = " ".join((excerpt or "").split())
        if len(excerpt) > 420:
            excerpt = f"{excerpt[:417].rstrip()}..."
        if response_language == "ar":
            return (
                "INSUFFICIENT_DATA: هذا سؤال تعريفي وليس تقييما لحالة امتثال محددة.\n\n"
                f"بناء على المقطع المسترجع من أيوفي: {excerpt} {marker}\n\n"
                "لإصدار تقييم امتثال، أحتاج تفاصيل المعاملة نفسها مثل الأصل، وتسلسل التملك، "
                "والثمن، والربح، وشروط الدفع."
            )
        return (
            "INSUFFICIENT_DATA: This is a definition question, not a compliance assessment for a specific transaction.\n\n"
            f"Based on the retrieved AAOIFI excerpt: {excerpt} {marker}\n\n"
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
        if not target_standards:
            target_standards = all_standards_for_family(family_result.primary_family)
            
        if family_result.mode and family_result.mode.value == "multi_path":
            for adj_fam in (getattr(family_result, "adjacent_families", []) or []):
                adj_standards = resolve_bulk(concept_ids, adj_fam)
                if not adj_standards:
                    adj_standards = all_standards_for_family(adj_fam)
                target_standards.extend(adj_standards)
            target_standards = list(dict.fromkeys(target_standards))

        standards_route = StandardsRoute(
            primary=[SourceFamily.SHARIA_STANDARD],
            candidate_standards=target_standards,
            requires_rule_evaluation=(family_result.primary_family != ContractFamily.UNKNOWN)
        )
        return family_result, target_standards, standards_route

    def _handle_clarification_stage(
        self,
        cleaned_query: str,
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

        if self.clarification_service:
            # Pass the known_family so ask_if_needed can apply the bypass
            # ONLY when the router is confident.
            clarification = self.clarification_service.ask_if_needed(
                cleaned_query,
                session_id=session_id,
                known_contract_family=known_family,
            )
        elif family_result.mode and family_result.mode.value == "clarification":
            # No clarification service at all — fall back to router hint
            clarification = getattr(family_result, "clarification_hint", None)

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
                    confidence=0.0,
                    response_language=response_language,
                ),
            )
            if hasattr(contract, "metadata"):
                contract.metadata["router_signals"] = getattr(family_result, "signals", {})
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract
        return None