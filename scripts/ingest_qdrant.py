"""Ingest AAOIFI markdown documents into Qdrant with provenance metadata."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.models.chunk import SemanticChunk
from src.models.document import AAOIFIDocument
from src.rag.chunker import SemanticChunker
from src.rag.qdrant_store import QdrantVectorStore


def detect_language(path: Path) -> str:
    if "_ar_" in path.name or "_ar." in path.name:
        return "ar"
    if "_en_" in path.name or "_en." in path.name:
        return "en"
    return "unknown"


def markdown_documents(corpus_dir: Path, languages: set[str]) -> Iterable[AAOIFIDocument]:
    for path in sorted(corpus_dir.rglob("*.md")):
        if path.name in {"INDEX.md", "CONVERSION_SUMMARY.md", ".gitkeep"}:
            continue
        language = detect_language(path)
        if language not in languages:
            continue
        document_id = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:16]
        standard_number = path.stem
        yield AAOIFIDocument(
            document_id=document_id,
            title=path.stem,
            content=path.read_text(encoding="utf-8"),
            standard_number=standard_number,
            source_url=str(path),
            metadata={
                "source_file": path.name,
                "document_version": "1.0",
                "language": language,
            },
        )


def embed_chunks(chunks: List[SemanticChunk], model_name: str) -> List[SemanticChunk]:
    model = SentenceTransformer(model_name)
    for chunk in chunks:
        chunk.embedding = model.encode(chunk.content).tolist()
    return chunks


def build_chunks(corpus_dir: Path, model_name: str, languages: set[str]) -> List[SemanticChunk]:
    chunker = SemanticChunker()
    chunks: List[SemanticChunk] = []
    for document in markdown_documents(corpus_dir, languages):
        document_chunks = chunker.chunk_document(document)
        for chunk in document_chunks:
            chunk.metadata = {
                **document.metadata,
                **chunk.metadata,
                "document_id": document.document_id,
                "document_title": document.title,
                "document_version": document.version,
                "standard_type": document.standard_type,
            }
        chunks.extend(document_chunks)
    return embed_chunks(chunks, model_name)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest AAOIFI markdown files into Qdrant.")
    parser.add_argument("--corpus-dir", default="./gemini-gem-prototype/knowledge-base")
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--languages", default="en,ar")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        raise SystemExit(f"Corpus directory not found: {corpus_dir}")

    languages = {language.strip() for language in args.languages.split(",") if language.strip()}
    chunks = build_chunks(corpus_dir, args.model, languages)
    if not chunks:
        raise SystemExit("No chunks generated; check corpus files and language filters.")

    store = QdrantVectorStore(collection_name=args.collection)
    store.store_chunks(chunks)
    print(f"Ingested {len(chunks)} chunks into Qdrant collection {store.collection_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
