"""
L0 Smoke Tests
Basic tests to verify RAG pipeline works end-to-end.
"""
import os
from pathlib import Path

import pytest
import yaml

from src.rag.pipeline import RAGPipeline

pytestmark = [pytest.mark.integration, pytest.mark.smoke]

# Path to gold evaluation set (created by scholar later)
GOLD_EVAL_PATH = Path("tests/fixtures/gold_eval.yaml")

# Load gold set if it exists
gold_cases = []
if GOLD_EVAL_PATH.exists() and GOLD_EVAL_PATH.stat().st_size > 0:
    with open(GOLD_EVAL_PATH, "r", encoding="utf-8") as f:
        gold_cases = yaml.safe_load(f) or []


def test_ingest_nonempty():
    """Verify ChromaDB was populated by ingestion script."""
    from chromadb import PersistentClient

    chroma_dir = os.getenv("CHROMA_DIR", "./chroma_db")

    # Check directory exists
    assert Path(chroma_dir).exists(), f"ChromaDB directory not found: {chroma_dir}"

    # Check collection has documents
    client = PersistentClient(path=chroma_dir)
    collection = client.get_collection("aaoifi")
    count = collection.count()

    assert count > 0, "ChromaDB collection is empty. Run scripts/ingest.py first."
    print(f"OK ChromaDB contains {count} chunks")


def test_retrieval_smoke():
    """Verify retrieval returns relevant chunks for a sample query."""
    pipeline = RAGPipeline(
        persist_dir=os.getenv("CHROMA_DIR", "./chroma_db"),
        model_name=os.getenv("EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2"),
    )

    # Sample query about murabaha (common Islamic finance contract)
    query = "murabaha cost disclosure"
    chunks = pipeline.retrieve(query, k=3)

    assert len(chunks) > 0, "Retrieval returned no chunks"
    assert all(chunk.score > 0 for chunk in chunks), "Chunks have invalid scores"
    assert all(chunk.citation.source_file for chunk in chunks), "Chunks missing source citations"

    print(f"OK Retrieved {len(chunks)} chunks for query: '{query}'")
    for chunk in chunks:
        print(f"  - {chunk.citation.standard_id} (score: {chunk.score:.2f})")


@pytest.mark.skipif(not gold_cases, reason="Gold evaluation set is empty")
@pytest.mark.parametrize("case", gold_cases)
def test_gold_evaluation(case):
    """
    Test against scholar-validated gold set.

    Gold set format (tests/fixtures/gold_eval.yaml):
    - query: "What does AAOIFI require for murabaha cost disclosure?"
      expected_standards: ["FAS-XX"]
      expected_answer_contains: ["keyword1", "keyword2"]
    """
    pipeline = RAGPipeline()

    query = case["query"]
    expected_standards = case.get("expected_standards", [])

    # Retrieve chunks
    chunks = pipeline.retrieve(query, k=5)

    # Verify expected standards are retrieved
    retrieved_standards = {chunk.citation.standard_id for chunk in chunks}

    for expected in expected_standards:
        assert any(
            expected in std for std in retrieved_standards
        ), f"Expected standard {expected} not retrieved for query: {query}"

    print(f"OK Gold case passed: {query}")
