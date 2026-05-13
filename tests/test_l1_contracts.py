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

    def generate(self, prompt):
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
def test_citation_validator_keeps_only_citations_backed_by_retrieved_chunks():
    from src.chatbot.citation_validator import CitationValidator

    validator = CitationValidator()

    citations = validator.validate(
        "Supported by [FAS-01 §1] and [FAS-99 §9].",
        [_chunk()],
    )

    assert [citation.standard_number for citation in citations] == ["FAS-01"]


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

        def create(self, **kwargs):
            return _EmptyResponse()

    client = GeminiClient(api_key="test-key", client=FakeOpenAIClient(), sleep=lambda _: None)

    with pytest.raises(LLMResponseError, match="empty response"):
        client.generate("hello")


@pytest.mark.unit
def test_openrouter_client_defaults_to_correct_model(monkeypatch):
    """GeminiClient alias defaults to the OpenRouter model when OPENROUTER_MODEL is not set."""
    from src.chatbot.llm_client import GeminiClient

    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    client = GeminiClient(api_key="test-key")

    assert client.model_name == "google/gemini-2.0-flash-exp:free"
