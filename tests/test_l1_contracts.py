import pytest

from src.models.ruling import ComplianceStatus
from src.models.schema import AAOIFICitation, SemanticChunk
from src.models.session import SessionState


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.queries = []

    def retrieve(self, query, k=5, threshold=0.3):
        self.queries.append((query, k, threshold))
        return self.chunks


class RecordingRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def retrieve(self, query, k=5, threshold=0.3, **kwargs):
        self.calls.append({"query": query, "k": k, "threshold": threshold, **kwargs})
        return self.chunks


class HistoryPromptBuilder:
    prompt_version = "history-prompt"

    def __init__(self):
        self.history = None

    def build_messages(self, query, chunks, history=None, response_language="en"):
        self.history = history
        return "SYSTEM", f"USER: {query}"


class MemorySessionStore:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id):
        state = SessionState(session_id=session_id)
        self.sessions[session_id] = state
        return state

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def update_session(self, state):
        self.sessions[state.session_id] = state


class FakeLLM:
    model_name = "fake-gemini"

    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.answer


class FakePromptBuilder:
    prompt_version = "test-prompt"

    def build(self, query, chunks, history=None):
        return f"PROMPT: {query} :: {len(chunks)} chunks"


def _chunk(chunk_id="chunk-1", standard_id="FAS-01", section="1", score=0.91, source_file=None, metadata=None):
    return SemanticChunk(
        chunk_id=chunk_id,
        text="AAOIFI permits the transaction when ownership and risk transfer are clear.",
        citation=AAOIFICitation(
            standard_id=standard_id,
            section=section,
            page=None,
            source_file=source_file or f"{standard_id}.md",
        ),
        score=score,
        metadata=metadata or {},
    )


@pytest.mark.service
def test_application_service_returns_canonical_answer_contract():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    service = ApplicationService(
        retriever=FakeRetriever([_chunk()]),
        llm_client=FakeLLM("COMPLIANT: Supported by AAOIFI [FAS-01 §1]."),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer("How should murabaha profit be recognized for accounting?", session_id="s-1")

    assert result.status == ComplianceStatus.COMPLIANT
    assert result.answer == "COMPLIANT: Supported by AAOIFI [FAS-01 §1]."
    assert result.citations[0].standard_number == "FAS-01"
    assert result.citations[0].section_number == "1"
    assert result.reasoning_summary
    assert result.limitations
    assert result.clarification_question is None
    assert result.metadata["model_name"] == "fake-gemini"
    assert result.metadata["prompt_version"] == "test-prompt"
    assert result.metadata["response_language"] == "en"
    assert result.metadata["retrieved_chunk_ids"] == ["chunk-1"]
    assert result.metadata["confidence"] == pytest.approx(0.91)


@pytest.mark.service
def test_application_service_returns_insufficient_data_without_retrieved_chunks():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    service = ApplicationService(
        retriever=FakeRetriever([]),
        llm_client=FakeLLM("this should not be called"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer("Does AAOIFI cover this unrelated topic?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert "retrieved AAOIFI" in result.answer


@pytest.mark.service
def test_application_service_fails_closed_for_late_penalty_without_sharia_evidence():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class FailingLLM(FakeLLM):
        def generate(self, prompt, **kwargs):
            raise AssertionError("late-payment source-family gaps should fail before LLM generation")

    service = ApplicationService(
        retriever=FakeRetriever([_chunk(standard_id="FAS-28", section=None)]),
        llm_client=FailingLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer(
        "Is a murabaha car installment sale with a 5% late payment penalty permissible?"
    )

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert "permissibility or contract validity" in result.answer
    assert result.metadata["transaction_scenario"]["late_payment_terms"]
    assert result.metadata["standards_route"]["primary"] == ["sharia_standard"]
    assert result.metadata["source_families"] == ["fas"]
    assert result.metadata["verdict_contract"]["verdict"] == "refer_to_scholar"
    assert result.metadata["verdict_contract"]["requires_scholar_review"] is True


@pytest.mark.service
def test_application_service_passes_source_family_filter_and_strict_metadata_gate(monkeypatch):
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    retriever = RecordingRetriever([
        _chunk(
            standard_id="SS-08",
            source_file="AAOIFI_Sharia_Standard_08_Murabaha.md",
            metadata={},
        )
    ])
    monkeypatch.setenv("REQUIRE_GOVERNED_SOURCE_METADATA", "1")
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")

    result = ApplicationService(
        retriever=retriever,
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer("Is a murabaha car installment sale with a late payment penalty permissible?")

    assert retriever.calls[0]["filters"] == {"source_family": "sharia_standard"}
    assert retriever.calls[0]["mode"] == "hybrid"
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["source_families"] == []


@pytest.mark.service
def test_application_service_fails_closed_for_plain_installment_permissibility_without_sharia_evidence():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class FailingLLM(FakeLLM):
        def generate(self, prompt, **kwargs):
            raise AssertionError("source-family gaps should fail before LLM generation")

    service = ApplicationService(
        retriever=FakeRetriever([_chunk(standard_id="FAS-28", section=None)]),
        llm_client=FailingLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer(
        "I bought a car from the bank in installments with a 20% markup. Is it halal?"
    )

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert result.metadata["transaction_scenario"]["contract_family"] == "murabaha"
    assert result.metadata["standards_route"]["primary"] == ["sharia_standard"]
    assert result.metadata["verdict_contract"]["requires_scholar_review"] is True


@pytest.mark.service
def test_application_service_source_gap_verdict_survives_empty_sharia_filter_result():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    service = ApplicationService(
        retriever=FakeRetriever([]),
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer(
        "Is a murabaha car installment sale with a late payment penalty permissible?"
    )

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["standards_route"]["primary"] == ["sharia_standard"]
    assert result.metadata["source_families"] == []
    assert result.metadata["verdict_contract"]["requires_scholar_review"] is True


@pytest.mark.service
def test_application_service_still_requires_rule_review_when_sharia_evidence_is_retrieved():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    llm = FakeLLM("INSUFFICIENT_DATA: More contract facts are needed.")
    service = ApplicationService(
        retriever=FakeRetriever([
            _chunk(
                standard_id="SS-08",
                section="1",
                source_file="AAOIFI_Sharia_Standard_08_Murabaha.md",
            )
        ]),
        llm_client=llm,
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer("Is this murabaha car installment structure halal?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert len(llm.prompts) == 0
    assert result.citations[0].standard_number == "SS-08"
    assert "verdict_contract" not in result.metadata
    assert result.metadata["rule_evaluation"]["human_review_flags"]
    assert result.metadata["scholar_review_workflow"]["path"] == "scholar_review_enhancement"
    assert result.metadata["scholar_review_workflow"]["blocks_main_app"] is False
    assert result.metadata["scholar_review_workflow"]["runtime_governance_update_allowed"] is False


@pytest.mark.service
def test_application_service_asks_targeted_arabic_penalty_clarification_before_retrieval():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class FailingRetriever:
        def retrieve(self, query, k=5, threshold=0.3, **kwargs):
            raise AssertionError("ambiguous penalty routing should clarify before retrieval")

    result = ApplicationService(
        retriever=FailingRetriever(),
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer(
        "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0622\u062e\u064a\u0631 \u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0634\u0631\u0637 \u0631\u0628\u0648\u064a\u061f"
    )

    expected = "\u0647\u0644 \u0627\u0644\u063a\u0631\u0627\u0645\u0629 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0642\u0627\u0648\u0644 \u0641\u064a \u0627\u0644\u062a\u0633\u0644\u064a\u0645 \u0623\u0645 \u0628\u0633\u0628\u0628 \u062a\u0623\u062e\u0631 \u0627\u0644\u0639\u0645\u064a\u0644 \u0641\u064a \u0627\u0644\u0633\u062f\u0627\u062f\u061f"
    assert result.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert result.clarification_question == expected
    assert result.answer == expected
    assert result.metadata["transaction_scenario"]["contract_family"] == "istisna"


@pytest.mark.service
def test_application_service_rejects_wrong_sharia_standard_for_candidate_route():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class FailingLLM(FakeLLM):
        def generate(self, prompt, **kwargs):
            raise AssertionError("wrong Shari'ah standard must fail before LLM generation")

    result = ApplicationService(
        retriever=FakeRetriever([
            _chunk(
                chunk_id="ss-03-debt",
                standard_id="SS-03",
                section="1",
                source_file="AAOIFI_Sharia_Standard_03_Debt.md",
                metadata={
                    "source_family": "sharia_standard",
                    "standard_number": "SS-03",
                    "metadata_status": "cataloged",
                },
            )
        ]),
        llm_client=FailingLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer("Can we impose a liquidated damages clause if the contractor is late delivering the project?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert result.metadata["standards_route"]["route_id"] == "istisna-penalty-clause"
    assert result.metadata["standards_route"]["candidate_standards"] == ["SS-10"]
    assert result.metadata["candidate_standard_filter"]["required"] == ["SS-10"]
    assert result.metadata["candidate_standard_filter"]["retrieved"] == ["SS-03"]
    assert result.metadata["source_families"] == ["sharia_standard"]


@pytest.mark.service
def test_application_service_allows_matching_candidate_sharia_standard_for_review_path():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    result = ApplicationService(
        retriever=FakeRetriever([
            _chunk(
                chunk_id="ss-10-istisna",
                standard_id="SS-10",
                section="2",
                source_file="AAOIFI_Sharia_Standard_10_Salam_Istisna.md",
                metadata={
                    "source_family": "sharia_standard",
                    "standard_number": "SS-10",
                    "metadata_status": "cataloged",
                },
            )
        ]),
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer("Can we impose liquidated damages if the contractor is late delivering the project?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations[0].standard_number == "SS-10"
    assert result.metadata["candidate_standard_filter"]["matched"] == ["SS-10"]
    assert result.metadata["scholar_review_workflow"]["runtime_governance_update_allowed"] is False


@pytest.mark.service
def test_application_service_uses_session_clarification_answer_for_next_turn():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    session_store = MemorySessionStore()
    retriever = RecordingRetriever([
        _chunk(
            chunk_id="ss-10-istisna",
            standard_id="SS-10",
            section="2",
            source_file="AAOIFI_Sharia_Standard_10_Salam_Istisna.md",
            metadata={
                "source_family": "sharia_standard",
                "standard_number": "SS-10",
                "metadata_status": "cataloged",
            },
        )
    ])
    service = ApplicationService(
        retriever=retriever,
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
        session_store=session_store,
    )

    first = service.answer(
        "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 \u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0634\u0631\u0637 \u0631\u0628\u0648\u064a\u061f",
        session_id="s-clarify",
    )
    second = service.answer("The contractor was late delivering the project.", session_id="s-clarify")

    assert first.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert second.status == ComplianceStatus.INSUFFICIENT_DATA
    assert second.citations[0].standard_number == "SS-10"
    assert second.metadata["transaction_scenario"]["contract_family"] == "istisna"
    assert "clarification_answer" in retriever.calls[0]["query"]


@pytest.mark.service
def test_application_service_passes_role_content_history_to_prompt_builder():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    prompt_builder = HistoryPromptBuilder()
    service = ApplicationService(
        retriever=FakeRetriever([_chunk()]),
        llm_client=FakeLLM("COMPLIANT: Supported by AAOIFI [FAS-01 \u00a71]."),
        prompt_builder=prompt_builder,
        citation_validator=CitationValidator(),
    )

    service.answer(
        "How should murabaha profit be recognized for accounting?",
        conversation_history=[
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ],
    )

    assert prompt_builder.history == [
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
    ]


@pytest.mark.service
def test_application_service_arabic_rule_review_response_is_not_mojibake():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    result = ApplicationService(
        retriever=FakeRetriever([
            _chunk(
                standard_id="SS-08",
                section="1",
                source_file="AAOIFI_Sharia_Standard_08_Murabaha.md",
            )
        ]),
        llm_client=FakeLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer("هل يجوز عقد مرابحة مع غرامة تأخير؟")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["response_language"] == "ar"
    assert "مراجعة قواعد شرعية" in result.answer
    assert "Ã" not in result.answer
    assert "Â" not in result.answer


@pytest.mark.service
def test_application_service_converts_llm_uncertainty_to_one_followup_question():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    uncertain_answer = """
PHASE 1: I need more information.
1. What is the company activity?
2. What percentage of revenue is non-compliant?
"""
    service = ApplicationService(
        retriever=FakeRetriever([_chunk()]),
        llm_client=FakeLLM(uncertain_answer),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer("How should investment income be disclosed for accounting?")

    assert result.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert result.clarification_question == "What is the company activity?"
    assert result.answer == "I need one detail before checking the AAOIFI evidence: What is the company activity?"
    assert "PHASE" not in result.answer
    assert "2." not in result.answer


@pytest.mark.service
def test_application_service_detects_arabic_and_localizes_insufficient_data():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    service = ApplicationService(
        retriever=FakeRetriever([]),
        llm_client=FakeLLM("this should not be called"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    )

    result = service.answer("هل يمكنني الاستثمار إذا لم أعرف نشاط الشركة؟")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["response_language"] == "ar"
    assert "أيوفي" in result.answer
    assert "عالما شرعيا مؤهلا" in result.limitations


@pytest.mark.unit
def test_prompt_builder_renders_history_chunks_and_query_deterministically():
    from src.chatbot.prompt_builder import PromptBuilder

    builder = PromptBuilder(system_prompt="SYSTEM", max_history_turns=1)
    prompt = builder.build(
        "Current question?",
        [_chunk()],
        history=[
            {"user": "old question", "assistant": "old answer"},
            {"user": "recent question", "assistant": "recent answer"},
        ],
    )

    assert prompt.startswith("SYSTEM")
    assert "old question" not in prompt
    assert "recent question" in prompt
    assert "[1] FAS-01 §1 (score: 0.91)" in prompt
    assert "Current question?" in prompt


@pytest.mark.unit
def test_prompt_builder_adds_arabic_response_instruction():
    from src.chatbot.prompt_builder import PromptBuilder

    prompt = PromptBuilder(system_prompt="SYSTEM").build(
        "هل هذه المعاملة متوافقة؟",
        [_chunk()],
        response_language="ar",
    )

    assert "Respond in clear Modern Standard Arabic" in prompt
    assert "[1] FAS-01 §1 (score: 0.91)" in prompt


@pytest.mark.unit
def test_prompt_builder_uses_single_clarification_guard_without_hidden_reasoning_labels():
    from src.chatbot.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build(
        "Can I invest?",
        [_chunk()],
        response_language="en",
    )

    assert "ask exactly ONE targeted follow-up question" in prompt
    assert "Clarification guard:" in prompt
    assert "CLARIFICATION_NEEDED" in prompt
    assert "chain-of-thought" not in prompt.lower()
    assert "## Reasoning" not in prompt
    assert "PHASE 1" not in prompt
    assert "1. [Specific question" not in prompt
    assert "2. [Specific question" not in prompt


@pytest.mark.unit
def test_prompt_builder_is_aaoifi_source_family_aware_not_fas_only():
    from src.chatbot.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build(
        "Is this construction penalty permissible?",
        [
            _chunk(
                standard_id="SS-10",
                section="2",
                source_file="AAOIFI_Sharia_Standard_10_Salam_Istisna.md",
                metadata={"standard_number": "SS-10", "source_family": "sharia_standard"},
            )
        ],
        response_language="en",
    )

    assert "sole function is to analyze financial operations against the AAOIFI" in prompt
    assert "source-family" in prompt
    assert "Financial Accounting Standards (FAS) documents provided to you" not in prompt
    assert "[1] SS-10 §2 (score: 0.91)" in prompt


@pytest.mark.unit
def test_prompt_builder_arabic_clarification_template_stays_single_question():
    from src.chatbot.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build(
        "هل يجوز الاستثمار؟",
        [_chunk()],
        response_language="ar",
    )

    assert "CLARIFICATION_NEEDED" in prompt
    assert "Exactly one specific Arabic question" in prompt
    assert "1. [" not in prompt
    assert "2. [" not in prompt


@pytest.mark.unit
def test_citation_validator_keeps_only_citations_backed_by_retrieved_chunks():
    from src.chatbot.citation_validator import CitationValidator

    validator = CitationValidator()

    citations = validator.validate(
        "Supported by [FAS-01 §1] and [FAS-99 §9].",
        [_chunk()],
    )

    assert [citation.standard_number for citation in citations] == ["FAS-01"]


@pytest.mark.unit
def test_citation_validator_accepts_arabic_aaoifi_citation_format():
    from src.chatbot.citation_validator import CitationValidator

    validator = CitationValidator()

    citations = validator.validate(
        "التعريف مستند إلى [معيار أيوفي FAS-28، القسم 8، صفحة 8].",
        [_chunk(standard_id="FAS-28", section=None)],
    )

    assert len(citations) == 1
    assert citations[0].standard_number == "FAS-28"
    assert citations[0].excerpt


@pytest.mark.service
def test_application_service_answers_arabic_definition_with_validator_backed_citation():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class FailingLLM(FakeLLM):
        def generate(self, prompt, **kwargs):
            raise AssertionError("definition questions should be answered from retrieved citations")

    chunks = [
        _chunk(
            chunk_id="murabaha-detail",
            standard_id="FAS-28",
            section=None,
            score=0.89,
        ),
        SemanticChunk(
            chunk_id="murabaha-definition",
            text=(
                "Murabaha - is sale of goods with an agreed upon profit mark-up on the cost. "
                "This could be on a spot basis or deferred payment basis."
            ),
            citation=AAOIFICitation(
                standard_id="FAS-28",
                section=None,
                page=8,
                source_file="AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md",
            ),
            score=0.84,
        ),
    ]

    result = ApplicationService(
        retriever=FakeRetriever(chunks),
        llm_client=FailingLLM("unused"),
        prompt_builder=FakePromptBuilder(),
        citation_validator=CitationValidator(),
    ).answer("ما هي المرابحة؟")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["response_language"] == "ar"
    assert len(result.citations) == 1
    assert result.citations[0].standard_number == "FAS-28"
    assert "Murabaha - is sale of goods" in result.answer
    assert "[FAS-28]" in result.answer


@pytest.mark.service
def test_application_service_expands_definition_retrieval_before_llm():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator

    class ExpandingRetriever:
        def __init__(self):
            self.calls = []

        def retrieve(self, query, k=5, threshold=0.3):
            self.calls.append((query, k, threshold))
            if len(self.calls) == 1:
                return [_chunk(chunk_id="murabaha-accounting", standard_id="FAS-28", section=None)]
            return [
                SemanticChunk(
                    chunk_id="murabaha-definition",
                    text="Murabaha - is sale of goods with an agreed upon profit mark-up on the cost.",
                    citation=AAOIFICitation(
                        standard_id="FAS-28",
                        section=None,
                        page=8,
                        source_file="AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md",
                    ),
                    score=0.78,
                )
            ]

    class FailingLLM(FakeLLM):
        def generate(self, prompt, **kwargs):
            raise AssertionError("wider retrieval should find the definition before LLM generation")

    retriever = ExpandingRetriever()
    result = ApplicationService(
        retriever=retriever,
        llm_client=FailingLLM("unused"),
        citation_validator=CitationValidator(),
    ).answer("ما هي المرابحة؟")

    assert len(retriever.calls) == 2
    assert retriever.calls[1][1] == 40
    assert retriever.calls[1][2] == 0.0
    assert len(result.citations) == 1
    assert "Murabaha - is sale of goods" in result.answer


@pytest.mark.unit
def test_gemini_client_raises_clear_error_for_empty_response():
    """OpenRouterClient (aliased as GeminiClient) raises LLMResponseError on empty response."""
    from src.chatbot.llm_client import GeminiClient, LLMResponseError

    class _EmptyChoice:
        message = type("Msg", (), {"content": ""})()  # content is empty string

    class _EmptyResponse:
        choices = [_EmptyChoice()]

    class FakeOpenAIClient:
        def __init__(self):
            self.chat = self
            self.completions = self
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return _EmptyResponse()

    fake_client = FakeOpenAIClient()
    client = GeminiClient(api_key="test-key", client=fake_client, sleep=lambda _: None)

    with pytest.raises(LLMResponseError, match="empty response"):
        client.generate("hello")
    assert fake_client.kwargs["max_tokens"] == 1024


@pytest.mark.unit
def test_openrouter_client_maps_payment_required_to_rate_limit_error():
    from src.chatbot.llm_client import GeminiClient, LLMRateLimitError

    class FakeOpenAIClient:
        def __init__(self):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            raise RuntimeError("Error code: 402 - insufficient credits")

    client = GeminiClient(api_key="test-key", client=FakeOpenAIClient(), sleep=lambda _: None)

    with pytest.raises(LLMRateLimitError, match="quota or rate limit"):
        client.generate("hello")


@pytest.mark.unit
def test_openrouter_client_defaults_to_correct_model(monkeypatch):
    """GeminiClient alias defaults to the OpenRouter model when OPENROUTER_MODEL is not set."""
    from src.chatbot.llm_client import GeminiClient

    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    client = GeminiClient(api_key="test-key")

    assert client.model_name == "openrouter/free"


@pytest.mark.unit
def test_openrouter_client_accepts_configurable_max_tokens(monkeypatch):
    from src.chatbot.llm_client import GeminiClient

    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "768")

    client = GeminiClient(api_key="test-key")

    assert client.max_tokens == 768
