import pytest


@pytest.mark.unit
def test_citation_validator_adds_confidence_and_quote_offsets():
    from src.chatbot.citation_validator import CitationValidator
    from src.models.schema import AAOIFICitation, SemanticChunk

    chunk = SemanticChunk(
        chunk_id="chunk-1",
        text="Short. AAOIFI requires ownership and risk transfer before resale in this structure.",
        citation=AAOIFICitation(
            standard_id="FAS-01",
            section="1",
            page=None,
            source_file="FAS-01.md",
        ),
        score=0.87,
    )

    citation = CitationValidator().validate("Supported by [FAS-01 Â§1].", [chunk])[0]

    assert citation.confidence_score == pytest.approx(0.87)
    assert citation.excerpt.startswith("AAOIFI requires")
    assert citation.quote_start is not None
    assert citation.quote_end is not None
    assert citation.quote_end > citation.quote_start


@pytest.mark.service
def test_application_service_uses_response_cache_for_identical_query():
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import AAOIFICitation, ComplianceStatus
    from src.models.schema import AAOIFICitation as SchemaCitation
    from src.models.schema import SemanticChunk
    from src.storage.cache import InMemoryCacheStore

    class Retriever:
        def __init__(self):
            self.calls = 0

        def retrieve(self, query, k=5, threshold=0.3):
            self.calls += 1
            return [
                SemanticChunk(
                    chunk_id="chunk-1",
                    text="AAOIFI permits the transaction when risk transfer is clear.",
                    citation=SchemaCitation(
                        standard_id="FAS-01",
                        section="1",
                        page=None,
                        source_file="FAS-01.md",
                    ),
                    score=0.9,
                )
            ]

    class LLM:
        model_name = "fake"

        def __init__(self):
            self.calls = 0

        def generate(self, prompt, **kwargs):
            self.calls += 1
            return "COMPLIANT: Supported by AAOIFI [FAS-01 §1]."

    retriever = Retriever()
    llm = LLM()
    service = ApplicationService(
        retriever=retriever,
        llm_client=llm,
        cache_store=InMemoryCacheStore(),
    )

    first = service.answer("Is this compliant?")
    second = service.answer("Is this compliant?")

    assert first.status == ComplianceStatus.COMPLIANT
    assert isinstance(second.citations[0], AAOIFICitation)
    assert second.metadata["cache_hit"] is True
    assert retriever.calls == 1
    assert llm.calls == 1


@pytest.mark.api
def test_disclaimer_endpoint_and_optional_enforcement(monkeypatch):
    from fastapi.testclient import TestClient

    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    monkeypatch.setenv("REQUIRE_DISCLAIMER_ACK", "true")
    app = create_app()

    class Service:
        def answer(self, query, session_id=None, request_id=None, disclaimer_acknowledged=True):
            from src.chatbot.application_service import ApplicationService

            return ApplicationService(retriever=lambda: None).answer(
                query,
                session_id=session_id,
                request_id=request_id,
                disclaimer_acknowledged=disclaimer_acknowledged,
            )

    app.dependency_overrides[get_application_service] = lambda: Service()

    with TestClient(app) as client:
        disclaimer = client.get("/api/v1/compliance/disclaimer")
        blocked = client.post(
            "/api/v1/query",
            json={"query": "Can I invest?", "context": {"disclaimer_acknowledged": False}},
        )

    assert disclaimer.status_code == 200
    assert disclaimer.json()["requires_acknowledgement"] is True
    assert blocked.status_code == 200
    assert blocked.json()["metadata"]["disclaimer_required"] is True
