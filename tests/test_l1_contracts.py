import pytest

from src.models.ruling import ComplianceStatus
from src.models.schema import AAOIFICitation, SemanticChunk


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.queries = []

    def retrieve(self, query, k=5, threshold=0.3):
        self.queries.append((query, k, threshold))
        return self.chunks


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


def _chunk(chunk_id="chunk-1", standard_id="FAS-01", section="1", score=0.91):
    return SemanticChunk(
        chunk_id=chunk_id,
        text="AAOIFI permits the transaction when ownership and risk transfer are clear.",
        citation=AAOIFICitation(
            standard_id=standard_id,
            section=section,
            page=None,
            source_file=f"{standard_id}.md",
        ),
        score=score,
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

    result = service.answer("Is this murabaha structure compliant?", session_id="s-1")

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

    result = service.answer("Can I invest in this company?")

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
