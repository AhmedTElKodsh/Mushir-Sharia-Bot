import pytest


def _embedding(first_value: float):
    return [first_value] + [0.0] * 767


class _FakeChromaCollection:
    def __init__(self, metadatas):
        self._metadatas = metadatas

    def get(self, where=None, limit=None, include=None):
        where = where or {}
        metadatas = [
            metadata
            for metadata in self._metadatas
            if all(metadata.get(key) == value for key, value in where.items())
        ]
        if limit is not None:
            metadatas = metadatas[:limit]
        return {"metadatas": metadatas}


@pytest.mark.unit
def test_citation_validator_fails_closed_for_unsupported_citation():
    from src.chatbot.citation_validator import CitationValidator
    from src.models.schema import AAOIFICitation, SemanticChunk

    chunk = SemanticChunk(
        chunk_id="chunk-1",
        text="AAOIFI requires ownership and risk transfer before resale.",
        citation=AAOIFICitation(
            standard_id="FAS-01",
            section="1",
            page=None,
            source_file="FAS-01.md",
        ),
        score=0.9,
    )

    citations = CitationValidator().validate("COMPLIANT: See [FAS-99 §9].", [chunk])

    assert citations == []


@pytest.mark.unit
def test_citation_validator_rejects_wrong_section_in_supported_standard():
    from src.chatbot.citation_validator import CitationValidator
    from src.models.schema import AAOIFICitation, SemanticChunk

    chunk = SemanticChunk(
        chunk_id="chunk-1",
        text="AAOIFI requires ownership and risk transfer before resale.",
        citation=AAOIFICitation(
            standard_id="FAS-28",
            section="3.1",
            page=47,
            source_file="FAS-28.md",
        ),
        score=0.9,
    )

    citations = CitationValidator().validate("COMPLIANT: See [FAS-28 §999.9, p.1].", [chunk])

    assert citations == []


@pytest.mark.unit
def test_citation_validator_matches_unpadded_fas_number_to_padded_standard():
    from src.chatbot.citation_validator import CitationValidator
    from src.models.schema import AAOIFICitation, SemanticChunk

    chunk = SemanticChunk(
        chunk_id="chunk-1",
        text="AAOIFI requires ownership and risk transfer before resale.",
        citation=AAOIFICitation(
            standard_id="FAS-01",
            section="1",
            page=None,
            source_file="FAS-01.md",
        ),
        score=0.9,
    )

    citations = CitationValidator().validate("COMPLIANT: See [FAS-1 section 1].", [chunk])

    assert len(citations) == 1
    assert citations[0].standard_number == "FAS-01"
    assert citations[0].section_number == "1"


@pytest.mark.service
def test_application_service_rewrites_unsupported_answer_to_insufficient_data():
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import ComplianceStatus
    from src.models.schema import AAOIFICitation, SemanticChunk

    class Retriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return [
                SemanticChunk(
                    chunk_id="chunk-1",
                    text="AAOIFI requires ownership and risk transfer before resale.",
                    citation=AAOIFICitation(
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

        def generate(self, prompt, **kwargs):
            return "COMPLIANT: This is allowed under [FAS-99]."

    result = ApplicationService(retriever=Retriever(), llm_client=LLM()).answer("Is this allowed?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert result.answer.startswith("INSUFFICIENT_DATA")


@pytest.mark.unit
def test_chroma_index_validation_rejects_english_only_embedding_model():
    from src.rag.pipeline import validate_chroma_index_for_arabic_retrieval

    collection = _FakeChromaCollection(
        [
            {
                "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                "embedding_normalized": True,
                "language": "en",
                "source_language": "en",
            }
        ]
    )

    with pytest.raises(RuntimeError, match="multilingual embedding model"):
        validate_chroma_index_for_arabic_retrieval(
            collection,
            "sentence-transformers/all-mpnet-base-v2",
        )


@pytest.mark.unit
def test_chroma_index_validation_requires_matching_model_metadata():
    from src.rag.pipeline import validate_chroma_index_for_arabic_retrieval

    collection = _FakeChromaCollection(
        [
            {
                "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                "embedding_normalized": True,
                "language": "en",
                "source_language": "en",
            }
        ]
    )

    with pytest.raises(RuntimeError, match="embedding metadata"):
        validate_chroma_index_for_arabic_retrieval(
            collection,
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        )


@pytest.mark.unit
def test_chroma_index_validation_requires_normalized_embeddings():
    from src.rag.pipeline import validate_chroma_index_for_arabic_retrieval

    model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    collection = _FakeChromaCollection(
        [
            {
                "embedding_model": model,
                "language": "en",
                "source_language": "en",
            },
            {
                "embedding_model": model,
                "language": "ar",
                "source_language": "ar",
            },
        ]
    )

    with pytest.raises(RuntimeError, match="normalized embeddings"):
        validate_chroma_index_for_arabic_retrieval(collection, model)


@pytest.mark.unit
def test_chroma_index_validation_requires_arabic_and_english_chunks():
    from src.rag.pipeline import validate_chroma_index_for_arabic_retrieval

    model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    collection = _FakeChromaCollection(
        [
            {
                "embedding_model": model,
                "embedding_normalized": True,
                "language": "en",
                "source_language": "en",
            }
        ]
    )

    with pytest.raises(RuntimeError, match="missing required Arabic/English"):
        validate_chroma_index_for_arabic_retrieval(collection, model)


@pytest.mark.unit
def test_chroma_index_validation_accepts_bilingual_multilingual_index():
    from src.rag.pipeline import validate_chroma_index_for_arabic_retrieval

    model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    collection = _FakeChromaCollection(
        [
            {
                "embedding_model": model,
                "embedding_normalized": True,
                "language": "en",
                "source_language": "en",
            },
            {
                "embedding_model": model,
                "embedding_normalized": True,
                "language": "ar",
                "source_language": "ar",
            },
        ]
    )

    validate_chroma_index_for_arabic_retrieval(collection, model)


@pytest.mark.unit
def test_chroma_governed_metadata_validation_quarantines_legacy_chunks():
    from src.rag.pipeline import validate_chroma_index_for_governed_metadata

    collection = _FakeChromaCollection(
        [
            {
                "standard_number": "SS-05",
                "source_file": "AAOIFI_Sharia_Standard_05.md",
                "source_language": "ar",
            }
        ]
    )

    with pytest.raises(RuntimeError, match="governed source metadata"):
        validate_chroma_index_for_governed_metadata(collection)


@pytest.mark.unit
def test_chroma_governed_metadata_validation_accepts_source_governed_chunks():
    from src.rag.pipeline import validate_chroma_index_for_governed_metadata

    collection = _FakeChromaCollection(
        [
            {
                "source_family": "sharia_standard",
                "metadata_status": "governed",
                "source_id": "iifa-resolution-109",
                "section_path": "Resolution 109 > Fourth",
                "citation_anchor": "https://iifa-aifi.org/en/32587.html#L118-L124",
            }
        ]
    )

    validate_chroma_index_for_governed_metadata(collection)


@pytest.mark.service
def test_application_service_bypasses_response_cache_in_eval_mode(monkeypatch):
    from src.chatbot.application_service import ApplicationService
    from src.models.schema import AAOIFICitation, SemanticChunk
    from src.storage.cache import InMemoryCacheStore

    class Retriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return [
                SemanticChunk(
                    chunk_id="chunk-1",
                    text="AAOIFI requires ownership and risk transfer before resale.",
                    citation=AAOIFICitation(
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
            return "COMPLIANT: Supported by [FAS-01]."

    llm = LLM()
    service = ApplicationService(
        retriever=Retriever(),
        llm_client=llm,
        cache_store=InMemoryCacheStore(),
    )

    service.answer("Is this compliant?")
    service.answer("Is this compliant?")
    monkeypatch.setenv("RAG_EVAL_MODE", "true")
    service.answer("Is this compliant?")

    assert llm.calls == 2


@pytest.mark.service
def test_cached_answer_preserves_validated_citation_metadata():
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus
    from src.storage.cache import InMemoryCacheStore

    cached = AnswerContract(
        answer="COMPLIANT: Supported by [FAS-01 §1].",
        status=ComplianceStatus.COMPLIANT,
        citations=[
            AAOIFICitation(
                document_id="FAS-01.md",
                standard_number="FAS-01",
                section_number="1",
                excerpt="AAOIFI requires ownership and risk transfer before resale.",
                confidence_score=0.91,
                quote_start=0,
                quote_end=62,
            )
        ],
        reasoning_summary="Grounded in FAS-01.",
        metadata={"confidence": 0.91},
    )
    cache = InMemoryCacheStore()
    service = ApplicationService(cache_store=cache)
    scenario = service.scenario_extractor.extract("Is this compliant?")
    standards_route = service.standards_router.route(scenario, "Is this compliant?")
    cache.set_json("response", service._cache_key("Is this compliant?", standards_route), cached.to_dict(), 60)

    answer = service.answer("Is this compliant?")

    assert answer.metadata["cache_hit"] is True
    assert answer.citations[0].excerpt == "AAOIFI requires ownership and risk transfer before resale."
    assert answer.citations[0].confidence_score == pytest.approx(0.91)
    assert answer.citations[0].quote_start == 0
    assert answer.citations[0].quote_end == 62


@pytest.mark.integration
def test_qdrant_vector_store_round_trips_chunks_in_memory():
    from src.models.chunk import SemanticChunk
    from src.rag.qdrant_store import QdrantVectorStore

    try:
        store = QdrantVectorStore(location=":memory:", collection_name="test_aaoifi", vector_size=768)
    except RuntimeError as exc:
        if "qdrant-client is required" not in str(exc):
            raise
        pytest.skip("qdrant-client is not installed in this environment.")
    chunks = [
        SemanticChunk(
            chunk_id="murabaha-ownership",
            document_id="doc-1",
            content="AAOIFI murabaha text requires ownership and risk transfer before resale.",
            chunk_index=0,
            token_count=80,
            embedding=_embedding(1.0),
            metadata={"standard_number": "FAS-01", "section_number": "1"},
        ),
        SemanticChunk(
            chunk_id="ijara-lease",
            document_id="doc-2",
            content="AAOIFI ijara text discusses usufruct and lease responsibilities.",
            chunk_index=0,
            token_count=80,
            embedding=[0.0, 1.0] + [0.0] * 766,
            metadata={"standard_number": "FAS-02", "section_number": "2"},
        ),
    ]

    store.store_chunks(chunks)
    results = store.similarity_search(_embedding(1.0), k=2, threshold=0.0)

    assert results[0]["chunk_id"] == "murabaha-ownership"
    assert results[0]["metadata"]["standard_number"] == "FAS-01"
    assert store.get_collection_stats()["chunk_count"] == 2


@pytest.mark.unit
def test_evaluate_retrieval_reports_hit_recall_and_mrr():
    from scripts.evaluate_rag import evaluate_retrieval

    class Pipeline:
        def retrieve(self, query, k=5, threshold=0.0):
            return [
                {"chunk_id": "wrong", "metadata": {}, "content": "", "similarity": 0.8},
                {
                    "chunk_id": "hashed-chunk-id",
                    "metadata": {"standard_number": "FAS-01"},
                    "content": "",
                    "similarity": 0.7,
                },
            ]

    report = evaluate_retrieval(
        [
            {
                "query": "murabaha ownership",
                "answerable": True,
                "required_source_ids": ["FAS-01"],
            }
        ],
        k=2,
        pipeline=Pipeline(),
    )

    assert report["hit_at_k"] == 1.0
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] == 0.5
    assert report["answerable_case_count"] == 1


@pytest.mark.unit
def test_evaluate_retrieval_applies_explicit_thresholds():
    from scripts.evaluate_rag import apply_thresholds

    report = apply_thresholds(
        {"hit_at_k": 0.75, "recall_at_k": 0.50, "mrr": 0.25},
        min_hit_at_k=0.70,
        min_recall_at_k=0.60,
        min_mrr=0.20,
    )

    assert report["passed"] is False
    assert report["thresholds"]["hit_at_k"]["passed"] is True
    assert report["thresholds"]["recall_at_k"]["passed"] is False
    assert report["thresholds"]["mrr"]["minimum"] == 0.20
    assert report["thresholds"]["answerable_case_count"]["minimum"] == 1


@pytest.mark.unit
def test_evaluate_retrieval_rejects_invalid_thresholds():
    from scripts.evaluate_rag import apply_thresholds

    with pytest.raises(ValueError, match="min_mrr"):
        apply_thresholds(
            {"hit_at_k": 1.0, "recall_at_k": 1.0, "mrr": 1.0},
            min_hit_at_k=0.0,
            min_recall_at_k=0.0,
            min_mrr=2.0,
        )


@pytest.mark.unit
def test_evaluate_retrieval_thresholds_ignore_unanswerable_cases_for_recall():
    from scripts.evaluate_rag import evaluate_retrieval

    class Pipeline:
        def retrieve(self, query, k=5, threshold=0.0):
            if threshold >= 0.3 and query == "unanswerable":
                return []
            return [{"chunk_id": "any", "metadata": {"standard_number": "FAS-01"}, "content": ""}]

    report = evaluate_retrieval(
        [
            {"query": "answerable", "answerable": True, "required_source_ids": ["FAS-01"]},
            {"query": "unanswerable", "answerable": False, "required_source_ids": []},
        ],
        k=1,
        threshold=0.3,
        pipeline=Pipeline(),
    )

    assert report["answerable_case_count"] == 1
    assert report["unanswerable_case_count"] == 1
    assert report["unanswerable_with_retrieval_count"] == 0
    assert report["hit_at_k"] == 1.0
    assert report["recall_at_k"] == 1.0
    assert report["unanswerable_retrieval_rate"] == 0.0


@pytest.mark.unit
def test_evaluate_retrieval_thresholds_can_fail_unanswerable_retrieval_rate():
    from scripts.evaluate_rag import apply_thresholds

    report = apply_thresholds(
        {
            "hit_at_k": 1.0,
            "recall_at_k": 1.0,
            "mrr": 1.0,
            "answerable_case_count": 3,
            "unanswerable_retrieval_rate": 0.75,
        },
        min_hit_at_k=0.8,
        min_recall_at_k=0.8,
        min_mrr=0.5,
        min_answerable_cases=3,
        max_unanswerable_retrieval_rate=0.5,
    )

    assert report["passed"] is False
    assert report["thresholds"]["unanswerable_retrieval_rate"]["passed"] is False


@pytest.mark.unit
def test_evaluate_retrieval_reports_research_gated_baseline_metrics():
    from scripts.evaluate_rag import evaluate_retrieval

    class Pipeline:
        def classify(self, query):
            if query == "needs clarification":
                return {"behavior": "clarification"}
            if query == "unsupported":
                return {"behavior": "refusal"}
            return {"behavior": "answer"}

        def retrieve(self, query, k=5, threshold=0.0):
            if query == "needs clarification":
                return []
            if query == "unsupported":
                return []
            return [
                {
                    "chunk_id": "murabaha-1",
                    "metadata": {
                        "standard_number": "FAS-28",
                        "source_family": "FAS",
                        "citation_supported": True,
                    },
                    "content": "",
                    "similarity": 0.9,
                }
            ]

    report = evaluate_retrieval(
        [
            {
                "query": "murabaha ownership",
                "answerable": True,
                "required_source_ids": ["FAS-28"],
                "expected_source_family": "FAS",
                "language": "en",
            },
            {
                "query": "needs clarification",
                "answerable": False,
                "expected_behavior": "clarification",
                "language": "mixed",
            },
            {
                "query": "unsupported",
                "answerable": False,
                "expected_behavior": "refusal",
                "language": "ar",
            },
        ],
        k=1,
        pipeline=Pipeline(),
    )

    assert report["expected_standard_hit_rate"] == 1.0
    assert report["source_family_accuracy"] == 1.0
    assert report["citation_support_rate"] == 1.0
    assert report["unsupported_answer_rate"] == 0.0
    assert report["refusal_correctness"] == 1.0
    assert report["clarification_precision"] == 1.0
    assert report["arabic_mixed_language_pass_rate"] == 1.0
    assert report["latency"]["average_ms"] >= 0.0


@pytest.mark.unit
def test_evaluate_retrieval_counts_answer_without_citation_support_as_unsupported():
    from scripts.evaluate_rag import evaluate_retrieval

    class Pipeline:
        def classify(self, query):
            return {"behavior": "answer"}

        def retrieve(self, query, k=5, threshold=0.0):
            return [
                {
                    "chunk_id": "murabaha-1",
                    "metadata": {
                        "standard_number": "FAS-28",
                        "source_family": "FAS",
                        "citation_supported": False,
                    },
                    "content": "",
                    "similarity": 0.9,
                }
            ]

    report = evaluate_retrieval(
        [
            {
                "query": "murabaha ownership",
                "answerable": True,
                "required_source_ids": ["FAS-28"],
                "expected_source_family": "FAS",
            }
        ],
        k=1,
        pipeline=Pipeline(),
    )

    assert report["expected_standard_hit_rate"] == 1.0
    assert report["citation_support_rate"] == 0.0
    assert report["unsupported_answer_rate"] == 1.0
    assert report["results"][0]["case_passed"] is False


@pytest.mark.unit
def test_fixture_retrieval_pipeline_runs_without_live_vector_index():
    from scripts.evaluate_rag import FixtureRetrievalPipeline, evaluate_retrieval

    cases = [
        {
            "query": "fixture murabaha",
            "answerable": True,
            "required_source_ids": ["FAS-28"],
            "expected_source_family": "FAS",
            "fixture_retrieved_chunks": [
                {
                    "chunk_id": "fixture-1",
                    "metadata": {
                        "standard_number": "FAS-28",
                        "source_family": "FAS",
                        "citation_supported": True,
                    },
                }
            ],
        },
        {
            "query": "fixture refusal",
            "answerable": False,
            "expected_behavior": "refusal",
            "fixture_behavior": "refusal",
            "fixture_retrieved_chunks": [],
        },
    ]

    report = evaluate_retrieval(cases, k=1, pipeline=FixtureRetrievalPipeline(cases))

    assert report["case_count"] == 2
    assert report["expected_standard_hit_rate"] == 1.0
    assert report["refusal_correctness"] == 1.0
    assert report["baseline_mode"] == "fixture_backed_retrieval_only"


@pytest.mark.unit
def test_retrieval_baseline_command_uses_fixture_safe_defaults(tmp_path):
    from scripts.run_retrieval_baseline import run_retrieval_baseline

    output = tmp_path / "retrieval-baseline-report.json"

    report = run_retrieval_baseline(output=output)

    assert output.exists()
    assert report["baseline_mode"] == "fixture_backed_retrieval_only"
    assert report["gold_file"].endswith("tests/fixtures/gold_eval_fixture_baseline.yaml")
    assert report["live_vector_index_used"] is False
    assert report["live_llm_used"] is False
    assert "expected_standard_hit_rate" in report
    assert "source_family_accuracy" in report
    assert "citation_support_rate" in report
    assert "refusal_correctness" in report
    assert "arabic_mixed_language_pass_rate" in report
    assert "latency" in report
    assert report["scholar_review_gold_gate"]["tuning_allowed"] is False


@pytest.mark.unit
def test_retrieval_baseline_blocks_tuning_on_pending_scholar_review(tmp_path):
    from scripts.run_retrieval_baseline import run_retrieval_baseline

    gold = tmp_path / "gold.yaml"
    gold.write_text(
        """
- query: "pending hard case"
  answerable: true
  required_source_ids: ["HC-SS-11"]
  expected_source_family: "sharia_standard"
  fixture_behavior: "answer"
  scholar_review_status: "pending"
  fixture_retrieved_chunks:
    - chunk_id: "HC-SS-11"
      metadata:
        standard_number: "SS-11"
        source_family: "sharia_standard"
        citation_supported: true
""".strip(),
        encoding="utf-8",
    )

    report = run_retrieval_baseline(
        gold=gold,
        output=tmp_path / "report.json",
        require_scholar_reviewed_gold=True,
    )

    assert report["passed"] is False
    assert report["scholar_review_gold_gate"]["tuning_allowed"] is False
    assert report["scholar_review_gold_gate"]["pending_or_unreviewed_case_count"] == 1
    assert "scholar-reviewed accepted gold cases" in report["failure_reasons"][0]


@pytest.mark.unit
def test_retrieval_baseline_allows_tuning_on_accepted_scholar_gold(tmp_path):
    from scripts.run_retrieval_baseline import run_retrieval_baseline

    gold = tmp_path / "gold.yaml"
    gold.write_text(
        """
- query: "accepted hard case"
  answerable: true
  required_source_ids: ["HC-SS-11"]
  expected_source_family: "sharia_standard"
  fixture_behavior: "answer"
  scholar_review_status: "accepted_for_gold_set"
  fixture_retrieved_chunks:
    - chunk_id: "HC-SS-11"
      metadata:
        standard_number: "SS-11"
        source_family: "sharia_standard"
        citation_supported: true
""".strip(),
        encoding="utf-8",
    )

    report = run_retrieval_baseline(
        gold=gold,
        output=tmp_path / "report.json",
        require_scholar_reviewed_gold=True,
    )

    assert report["passed"] is True
    assert report["scholar_review_gold_gate"]["tuning_allowed"] is True
    assert report["scholar_review_gold_gate"]["accepted_gold_case_count"] == 1


@pytest.mark.unit
def test_sharia_corpus_coverage_report_marks_partial_catalog():
    from scripts.report_sharia_corpus_coverage import build_sharia_coverage_matrix, sharia_coverage_report

    records = [
        {"source_family": "sharia_standard", "standard_number": "SS-02", "language": "ar", "source_id": "ss-02-ar"},
        {"source_family": "sharia_standard", "standard_number": "SS-02", "language": "en", "source_id": "ss-02-en"},
        {"source_family": "sharia_standard", "standard_number": "SS-05", "language": "en", "source_id": "ss-05-en"},
        {"source_family": "fas", "standard_number": "FAS-28", "language": "en"},
    ]

    report = sharia_coverage_report(records, target_sharia_standard_count=60)
    matrix = build_sharia_coverage_matrix(records, target_sharia_standard_count=5)

    assert report["status"] == "partial"
    assert report["covered_sharia_standard_count"] == 2
    assert report["missing_sharia_standard_count"] == 58
    assert report["hard_sharia_ready"] is False
    assert report["release_gate"] == "fail"
    assert report["release_gate_fail_count"] == 60
    assert report["bilingual_sharia_standards"] == ["SS-02"]
    assert report["missing_bilingual_sharia_standards"] == ["SS-05"]
    assert report["target_inventory_sources"]
    assert matrix[0]["standard_number"] == "SS-01"
    assert matrix[0]["ingestion_status"] == "missing_source"
    assert matrix[1]["standard_number"] == "SS-02"
    assert matrix[1]["source_coverage_gate"] == "pass"
    assert matrix[1]["release_gate"] == "fail"
    assert matrix[4]["standard_number"] == "SS-05"
    assert matrix[4]["missing_languages"] == ["ar"]
    assert report["no_go_reasons"]


@pytest.mark.unit
def test_current_machine_catalog_is_not_complete_sharia_evidence_base():
    from pathlib import Path
    from scripts.report_sharia_corpus_coverage import load_acquisition_manifest, load_catalog, sharia_coverage_report

    report = sharia_coverage_report(
        load_catalog(Path("data/source_registry/aaoifi-source-catalog.yaml")),
        acquisition_manifest=load_acquisition_manifest(
            Path("data/source_registry/aaoifi-sharia-acquisition-manifest.yaml")
        ),
    )

    assert report["status"] == "partial"
    assert report["covered_sharia_standard_count"] == 55
    assert report["covered_sharia_standards"][:5] == ["SS-01", "SS-02", "SS-03", "SS-04", "SS-05"]
    assert report["covered_sharia_standards"][-1] == "SS-60"
    assert report["covered_sharia_standard_count"] < report["target_sharia_standard_count"]
    assert report["target_sharia_standard_count"] == 60
    assert report["missing_sharia_standards"] == ["SS-55", "SS-56", "SS-57", "SS-58", "SS-59"]
    assert report["missing_sharia_standard_count"] == 5
    assert report["blocked_source_count"] == 5
    assert report["blocked_source_standards"] == ["SS-55", "SS-56", "SS-57", "SS-58", "SS-59"]
    assert report["release_gate_fail_count"] == 60
    assert report["hard_sharia_ready"] is False


@pytest.mark.unit
def test_bm25_fixture_retriever_ranks_lexical_standard_match():
    from scripts.evaluate_rag import BM25FixtureRetriever

    retriever = BM25FixtureRetriever(
        [
            {
                "chunk_id": "fas-28",
                "content": "Murabaha resale requires ownership and risk transfer before sale.",
                "metadata": {"standard_number": "FAS-28", "source_family": "FAS"},
            },
            {
                "chunk_id": "fas-40",
                "content": "Investment real estate is held for rental income.",
                "metadata": {"standard_number": "FAS-40", "source_family": "FAS"},
            },
        ]
    )

    results = retriever.retrieve("murabaha ownership before resale", k=1)

    assert results[0]["chunk_id"] == "fas-28"
    assert results[0]["metadata"]["retrieval_method"] == "bm25_fixture"
    assert results[0]["similarity"] > 0


@pytest.mark.unit
def test_hybrid_fixture_pipeline_can_measure_bm25_plus_dense_improvement():
    from scripts.evaluate_rag import HybridFixtureRetrievalPipeline, compare_hybrid_fixture_spike, evaluate_retrieval

    class DenseMissPipeline:
        baseline_mode = "dense_fixture"

        def retrieve(self, query, k=5, threshold=0.0):
            return [
                {
                    "chunk_id": "wrong",
                    "content": "Unrelated leasing text.",
                    "metadata": {"standard_number": "FAS-02", "source_family": "FAS"},
                    "similarity": 0.95,
                }
            ]

    cases = [
        {
            "query": "murabaha ownership before resale",
            "answerable": True,
            "required_source_ids": ["FAS-28"],
            "expected_source_family": "FAS",
            "fixture_corpus_chunks": [
                {
                    "chunk_id": "fas-28",
                    "content": "Murabaha resale requires ownership and risk transfer before sale.",
                    "metadata": {
                        "standard_number": "FAS-28",
                        "source_family": "FAS",
                        "citation_supported": True,
                    },
                }
            ],
        }
    ]

    dense_report = evaluate_retrieval(cases, k=1, pipeline=DenseMissPipeline())
    hybrid_report = evaluate_retrieval(
        cases,
        k=1,
        pipeline=HybridFixtureRetrievalPipeline(DenseMissPipeline(), cases),
    )

    assert dense_report["expected_standard_hit_rate"] == 0.0
    assert hybrid_report["expected_standard_hit_rate"] == 1.0
    assert hybrid_report["baseline_mode"] == "hybrid_fixture_bm25_plus_dense"
    assert hybrid_report["results"][0]["retrieved_ids"] == ["fas-28"]

    comparison = compare_hybrid_fixture_spike(cases, DenseMissPipeline(), k=1)
    assert comparison["adopt_next"] is True
    assert comparison["dense"]["expected_standard_hit_rate"] == 0.0
    assert comparison["hybrid"]["expected_standard_hit_rate"] == 1.0


@pytest.mark.unit
def test_embedding_candidate_fixture_comparison_uses_separate_temp_index_and_safety_gate():
    from scripts.evaluate_rag import compare_embedding_candidate_fixture_spike, evaluate_retrieval

    class CurrentMpnetBaseline:
        baseline_mode = "current_mpnet_fixture"

        def classify(self, query):
            return {"behavior": "answer"}

        def retrieve(self, query, k=5, threshold=0.0):
            return [
                {
                    "chunk_id": "wrong",
                    "content": "Unrelated leasing text.",
                    "metadata": {
                        "standard_number": "FAS-02",
                        "source_family": "FAS",
                        "citation_supported": True,
                    },
                    "similarity": 0.95,
                }
            ]

    cases = [
        {
            "query": "Arabic murabaha ownership before resale",
            "answerable": True,
            "required_source_ids": ["FAS-28"],
            "expected_source_family": "FAS",
            "language": "mixed",
            "candidate_retrieved_chunks_by_model": {
                "bge-m3": [
                    {
                        "chunk_id": "fas-28",
                        "content": "Murabaha resale requires ownership before sale.",
                        "metadata": {
                            "standard_number": "FAS-28",
                            "source_family": "FAS",
                            "citation_supported": True,
                        },
                    }
                ],
                "bge-reranker": [
                    {
                        "chunk_id": "wrong",
                        "content": "Unrelated text.",
                        "metadata": {
                            "standard_number": "FAS-02",
                            "source_family": "FAS",
                            "citation_supported": True,
                            "rerank_score": 0.1,
                        },
                    },
                    {
                        "chunk_id": "fas-28",
                        "content": "Murabaha resale requires ownership before sale.",
                        "metadata": {
                            "standard_number": "FAS-28",
                            "source_family": "FAS",
                            "citation_supported": True,
                            "rerank_score": 0.9,
                        },
                    },
                ],
            },
        }
    ]

    baseline_report = evaluate_retrieval(cases, k=1, pipeline=CurrentMpnetBaseline())
    comparison = compare_embedding_candidate_fixture_spike(
        cases,
        baseline_pipeline=CurrentMpnetBaseline(),
        k=1,
        temp_index_id="tmp-test-bge-index",
    )

    assert baseline_report["expected_standard_hit_rate"] == 0.0
    assert comparison["runtime_index_modified"] is False
    assert comparison["live_model_downloads"] is False
    assert comparison["temporary_index_id"] == "tmp-test-bge-index"
    assert comparison["candidates"]["bge-m3"]["expected_standard_hit_rate"] == 1.0
    assert comparison["candidates"]["bge-reranker"]["results"][0]["retrieved_ids"] == ["fas-28"]
    assert comparison["candidates"]["bge-reranker"]["results"][0]["case_passed"] is True
    assert comparison["recommendation"]["adopt_candidate"] in {"bge-m3", "bge-reranker"}


@pytest.mark.unit
def test_ingestion_candidate_probe_blocks_license_gated_pdf_candidates():
    from scripts.evaluate_ingestion_candidates import evaluate_ingestion_candidates, ProbeStatus

    report = evaluate_ingestion_candidates()

    assert report["runtime_ingestion_modified"] is False
    assert report["candidates"]["pdfplumber"]["status"] in {ProbeStatus.PROBE_PASSED.value, ProbeStatus.MISSING_OPTIONAL_DEPENDENCY.value}
    if report["candidates"]["pdfplumber"]["status"] == ProbeStatus.PROBE_PASSED.value:
        assert "Arab Investment Bank" in report["candidates"]["pdfplumber"]["extracted_text_preview"]
    assert report["candidates"]["pymupdf"]["status"] == ProbeStatus.BLOCKED_PENDING_LICENSE_REVIEW.value
    assert report["candidates"]["marker"]["status"] == ProbeStatus.BLOCKED_PENDING_LICENSE_REVIEW.value
    assert report["summary"]["license_blocked_candidates"] == ["pymupdf", "marker"]
    assert report["candidates"]["pymupdf"]["adopt_next"] is False
    assert report["candidates"]["marker"]["adopt_next"] is False


@pytest.mark.unit
def test_retrieval_coordinator_skips_for_authority_and_underspecified_queries():
    from src.chatbot.retrieval_coordinator import RetrievalCoordinator

    class UncallableRetriever:
        def retrieve(self, query, k=5, threshold=0.3):
            raise AssertionError("blocked queries should not be retrieved")

    coordinator = RetrievalCoordinator(retriever=UncallableRetriever())

    assert coordinator.retrieve("Can Mushir give me a binding fatwa for this investment?") == []
    assert coordinator.retrieve("Can I invest if I do not know the business activity?") == []
    assert coordinator.retrieve("What if the answer cites FAS-99 but the retrieved sources only contain FAS-01?") == []
