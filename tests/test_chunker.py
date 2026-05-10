import pytest
from src.models.chunk import SemanticChunk
from src.rag.chunker import SemanticChunker, estimate_tokens

def test_estimate_tokens():
    text = "This is a test sentence with ten words here."
    tokens = estimate_tokens(text)
    assert tokens > 0
    assert tokens < 20

def test_semantic_chunk_creation():
    chunk = SemanticChunk(
        chunk_id="doc1_0",
        document_id="doc1",
        content="This is test content for chunking.",
        chunk_index=0,
        token_count=100,
    )
    assert chunk.chunk_id == "doc1_0"
    assert chunk.token_count == 100

def test_chunker_invalid_token_count():
    with pytest.raises(ValueError):
        SemanticChunk(
            chunk_id="doc1_0",
            document_id="doc1",
            content="short",
            chunk_index=0,
            token_count=10,  # Too low
        )

def test_chunker_document():
    from src.models.document import AAOIFIDocument
    from datetime import datetime
    doc = AAOIFIDocument(
        document_id="fas-1",
        title="FAS 1 Test",
        content="Section 1\nThis is the first section with enough content to pass the minimum token threshold for testing purposes.\n\nSection 2\nThis is the second section with adequate content for testing the chunking functionality properly.",
    )
    chunker = SemanticChunker(chunk_size=512, chunk_overlap=50)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.token_count >= 50
