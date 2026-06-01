"""Ingest AAOIFI markdown documents into Qdrant with provenance metadata."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import yaml

from src.governance.source_catalog import (
    MetadataStatus,
    SourceCatalog,
    SourceCatalogRecord,
)
from src.models.chunk import SemanticChunk
from src.models.document import AAOIFIDocument
from src.rag.chunker import SemanticChunker
from src.rag.qdrant_store import QdrantVectorStore


DEFAULT_BATCH_SIZE = 128
DEFAULT_SOURCE_CATALOG = "data/source_registry/aaoifi-source-catalog.yaml"


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
                "source_path": path.as_posix(),
                "document_version": "1.0",
                "language": language,
            },
        )


def embed_chunks(
    chunks: List[SemanticChunk],
    model: SentenceTransformer,
    batch_size: int,
) -> List[SemanticChunk]:
    embeddings = model.encode(
        [chunk.content for chunk in chunks],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
    return chunks


def load_source_catalog(path: str | Path | None) -> SourceCatalog | None:
    if not path:
        return None
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise SystemExit(f"Source catalog file not found: {catalog_path}")
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    return SourceCatalog.from_payload(
        records=payload.get("records", ()),
        document_versions=payload.get("document_versions", ()),
        relationships=payload.get("relationships", ()),
    )


def catalog_record_for_document(
    source_catalog: SourceCatalog | None,
    document: AAOIFIDocument,
    corpus_dir: Path,
) -> SourceCatalogRecord | None:
    if source_catalog is None:
        return None
    source_path = Path(str(document.metadata.get("source_path") or ""))
    candidates = [str(document.metadata.get("source_file") or "")]
    if source_path:
        candidates.append(source_path.as_posix())
        try:
            candidates.insert(0, source_path.relative_to(corpus_dir).as_posix())
        except ValueError:
            pass
    for candidate in dict.fromkeys(candidate for candidate in candidates if candidate):
        try:
            return source_catalog.find_by_path(candidate)
        except KeyError:
            continue
    return None


def governed_chunk_metadata(
    document: AAOIFIDocument,
    chunk: SemanticChunk,
    chunk_index: int,
    total_chunks: int,
    catalog_record: SourceCatalogRecord | None,
) -> dict:
    if catalog_record is None:
        return {
            **document.metadata,
            **chunk.metadata,
            "document_id": document.document_id,
            "document_title": document.title,
            "document_version": document.version,
            "standard_type": document.standard_type,
            "metadata_status": MetadataStatus.QUARANTINED_MISSING_CATALOG.value,
        }
    return {
        **chunk.metadata,
        **catalog_record.to_chunk_metadata(
            source_file=str(document.metadata.get("source_file") or document.title),
            chunk_index=chunk_index,
            total_chunks=total_chunks,
        ),
        "document_id": document.document_id,
        "document_title": document.title,
        "document_version": document.version,
        "standard_type": document.standard_type,
        "metadata_status": (
            MetadataStatus.CATALOGED.value
            if catalog_record.is_answer_admissible
            else MetadataStatus.CATALOGED_NOT_ANSWER_ADMISSIBLE.value
        ),
        "section_path": chunk.metadata.get("section_path") or f"{catalog_record.standard_number}#chunk-{chunk_index:04d}",
        "citation_anchor": f"{catalog_record.official_url}#chunk-{chunk_index:04d}",
    }


def build_chunks(
    corpus_dir: Path,
    languages: set[str],
    source_catalog: SourceCatalog | None = None,
) -> List[SemanticChunk]:
    chunker = SemanticChunker()
    chunks: List[SemanticChunk] = []
    for document in markdown_documents(corpus_dir, languages):
        document_chunks = chunker.chunk_document(document)
        catalog_record = catalog_record_for_document(source_catalog, document, corpus_dir)
        for index, chunk in enumerate(document_chunks):
            chunk.metadata = governed_chunk_metadata(
                document,
                chunk,
                index,
                len(document_chunks),
                catalog_record,
            )
        chunks.extend(document_chunks)
    return chunks


def chunk_batches(chunks: List[SemanticChunk], batch_size: int) -> Iterable[List[SemanticChunk]]:
    for start in range(0, len(chunks), batch_size):
        yield chunks[start : start + batch_size]


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest AAOIFI markdown files into Qdrant.")
    parser.add_argument("--corpus-dir", default=os.getenv("CORPUS_DIR", "./data/aaoifi_md"))
    parser.add_argument("--source-catalog", default=os.getenv("SOURCE_CATALOG_FILE", DEFAULT_SOURCE_CATALOG))
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--languages", default="en,ar")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--start-offset",
        type=int,
        default=0,
        help="Skip this many generated chunks before embedding/uploading. Useful for resuming large ingests.",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        raise SystemExit(f"Corpus directory not found: {corpus_dir}")

    languages = {language.strip() for language in args.languages.split(",") if language.strip()}
    source_catalog = load_source_catalog(args.source_catalog)
    chunks = build_chunks(corpus_dir, languages, source_catalog)
    if not chunks:
        raise SystemExit("No chunks generated; check corpus files and language filters.")
    if args.start_offset:
        chunks = chunks[args.start_offset :]
        if not chunks:
            print("No chunks remain after --start-offset; nothing to ingest.")
            return 0

    store = QdrantVectorStore(collection_name=args.collection)
    model = SentenceTransformer(args.model)
    total = 0
    for batch_number, batch in enumerate(chunk_batches(chunks, args.batch_size), start=1):
        embedded = embed_chunks(batch, model, args.batch_size)
        store.store_chunks(embedded)
        total += len(embedded)
        print(
            f"Ingested batch {batch_number}: {total}/{len(chunks)} chunks into "
            f"Qdrant collection {store.collection_name}",
            flush=True,
        )
    print(f"Ingested {total} chunks into Qdrant collection {store.collection_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
