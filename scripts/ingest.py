"""Ingest AAOIFI markdown files into ChromaDB."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import chromadb
import yaml
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from src.governance.chunk_metadata import ParentChildChunkMetadataBuilder
from src.governance.source_catalog import SourceCatalog, SourceCatalogRecord

DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_CHROMA_DIR = "./chroma_db_multilingual"
DEFAULT_CORPUS_DIR = "./gemini-gem-prototype/knowledge-base"
SUPPORTED_LANGUAGES = {"en", "ar"}
EXCLUDED_MARKDOWN = {"INDEX.md", "CONVERSION_SUMMARY.md", ".gitkeep"}


def detect_language(path: Path) -> str:
    name = path.name
    if "_ar_" in name or "_ar." in name:
        return "ar"
    if "_en_" in name or "_en." in name:
        return "en"
    return "unknown"


def detect_text_language(text: str, fallback: str) -> str:
    sample = text[:5000]
    arabic_chars = sum(1 for char in sample if "\u0600" <= char <= "\u06ff")
    latin_chars = sum(1 for char in sample if "A" <= char <= "Z" or "a" <= char <= "z")
    if arabic_chars >= 40 and arabic_chars > latin_chars:
        return "ar"
    if latin_chars >= 40 and latin_chars >= arabic_chars:
        return "en"
    return fallback


def markdown_files(corpus_dir: Path, languages: Sequence[str]) -> List[Path]:
    selected_languages = set(languages)
    return [
        path
        for path in sorted(corpus_dir.rglob("*.md"))
        if path.name not in EXCLUDED_MARKDOWN and detect_language(path) in selected_languages
    ]


def normalize_standard_selector(value: str) -> str:
    text = (value or "").strip().upper()
    match = re.search(r"\b(SS|FAS)[-_\s]*0*(\d{1,3})\b", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    return text


def fallback_standard_number_for_file(path: Path) -> str:
    name = path.name
    match = re.search(r"AAOIFI_Standard_0*(\d{1,3})_", name, flags=re.IGNORECASE)
    if not match:
        return ""
    prefix = "SS" if "Sharia_Standard" in name or "Shari'ah_Standard" in name else "FAS"
    return f"{prefix}-{int(match.group(1)):02d}"


def filter_files_by_standards(
    files: Iterable[Path],
    standards: Sequence[str],
    source_catalog: Optional[SourceCatalog] = None,
    corpus_dir: Optional[Path] = None,
) -> List[Path]:
    selected = {normalize_standard_selector(standard) for standard in standards if standard.strip()}
    if not selected:
        return list(files)
    matched = []
    for md_file in files:
        catalog_record = catalog_record_for_file(source_catalog, md_file, corpus_dir=corpus_dir)
        standard = (
            normalize_standard_selector(catalog_record.standard_number)
            if catalog_record is not None
            else fallback_standard_number_for_file(md_file)
        )
        if standard in selected:
            matched.append(md_file)
    return matched


def standard_number(path: Path) -> str:
    return path.stem


def build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def section_path_for_chunk(text: str, standard: str) -> List[str]:
    """Infer a lightweight structural path for metadata lineage."""
    headings = [
        line.strip().lstrip("#").strip()
        for line in text.splitlines()
        if line.strip().startswith("#")
    ]
    return [standard] + headings[:3] if headings else [standard]


def citation_anchor_for_chunk(catalog_record: Optional[SourceCatalogRecord], chunk_index: int) -> str:
    if catalog_record is None:
        return ""
    return f"{catalog_record.official_url}#chunk-{chunk_index:04d}"


def reset_collection(client, collection_name: str) -> None:
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def load_source_catalog(path: str | Path | None) -> Optional[SourceCatalog]:
    """Load a source catalog YAML file for answer-admissible ingestion metadata."""
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


def catalog_record_for_file(
    source_catalog: Optional[SourceCatalog],
    md_file: Path,
    corpus_dir: Optional[Path] = None,
) -> Optional[SourceCatalogRecord]:
    """Find catalog metadata by path, falling back to the markdown filename."""
    if source_catalog is None:
        return None
    candidates = [md_file.as_posix(), md_file.name]
    if corpus_dir:
        try:
            candidates.insert(0, md_file.relative_to(corpus_dir).as_posix())
        except ValueError:
            pass
    try:
        candidates.append(md_file.resolve().as_posix())
    except OSError:
        pass
    for candidate in dict.fromkeys(candidates):
        try:
            return source_catalog.find_by_path(candidate)
        except KeyError:
            continue
    return None


def unmatched_catalog_files(
    files: Iterable[Path],
    source_catalog: Optional[SourceCatalog],
    corpus_dir: Optional[Path] = None,
) -> List[Path]:
    if source_catalog is None:
        return []
    return [
        md_file
        for md_file in files
        if catalog_record_for_file(source_catalog, md_file, corpus_dir=corpus_dir) is None
    ]


def ingest_files(
    files: Iterable[Path],
    model: SentenceTransformer,
    collection,
    splitter: RecursiveCharacterTextSplitter,
    model_name: str,
    source_catalog: Optional[SourceCatalog] = None,
    corpus_dir: Optional[Path] = None,
) -> tuple[int, list]:
    total_chunks = 0
    bm25_docs = []
    for md_file in files:
        source_language = detect_language(md_file)
        try:
            text = md_file.read_text(encoding="utf-8")
            language = detect_text_language(text, fallback=source_language)
            print(f"\nProcessing: {md_file.name} ({source_language} file, {language} text)")
            chunks = splitter.split_text(text)
            print(f"  Generated {len(chunks)} chunks")

            if not chunks:
                continue

            embeddings = model.encode(chunks, normalize_embeddings=True).tolist()
            ids = [
                hashlib.md5(f"{md_file.name}:{index}".encode("utf-8")).hexdigest()
                for index, _ in enumerate(chunks)
            ]
            standard = standard_number(md_file)
            catalog_record = catalog_record_for_file(source_catalog, md_file, corpus_dir=corpus_dir)
            metadata_builder = ParentChildChunkMetadataBuilder(
                source_file=md_file.name,
                source_path=md_file.as_posix(),
                standard_number=standard,
                language=language,
                source_language=source_language,
                embedding_model=model_name,
                embedding_normalized=True,
                total_chunks=len(chunks),
                catalog_record=catalog_record,
            )
            metadatas = [
                metadata_builder.child_metadata(
                    chunk_index=index,
                    section_path=section_path_for_chunk(chunk_text, standard),
                    citation_anchor=citation_anchor_for_chunk(catalog_record, index),
                )
                for index, chunk_text in enumerate(chunks)
            ]
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
            for i, chunk_text in enumerate(chunks):
                bm25_docs.append({"doc_id": ids[i], "text": chunk_text, "metadata": metadatas[i]})
            total_chunks += len(chunks)
            print(f"  Stored {len(chunks)} chunks")
        except Exception as exc:
            print(f"  Error processing {md_file.name}: {exc}")
            continue
    return total_chunks, bm25_docs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest AAOIFI markdown files into ChromaDB.")
    parser.add_argument("--corpus-dir", default=os.getenv("CORPUS_DIR", DEFAULT_CORPUS_DIR))
    parser.add_argument("--chroma-dir", default=os.getenv("CHROMA_DIR", DEFAULT_CHROMA_DIR))
    parser.add_argument("--model", default=os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL))
    parser.add_argument("--collection", default="aaoifi")
    parser.add_argument(
        "--languages",
        default=os.getenv("INGEST_LANGUAGES", "en,ar"),
        help="Comma-separated language codes to ingest, for example: en,ar",
    )
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the target collection first.")
    parser.add_argument(
        "--source-catalog",
        default=os.getenv("SOURCE_CATALOG_FILE"),
        help="Optional YAML source catalog. Matching records mark chunks as cataloged instead of quarantined.",
    )
    parser.add_argument(
        "--standards",
        default=os.getenv("INGEST_STANDARDS", ""),
        help="Optional comma-separated standard IDs to ingest, for example: SS-03,SS-19.",
    )
    parser.add_argument(
        "--allow-uncataloged",
        action="store_true",
        help=(
            "Allow ingestion without a source catalog. Chunks will be quarantined "
            "and will not support answers."
        ),
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    args = parse_args()
    languages = [language.strip() for language in args.languages.split(",") if language.strip()]
    unsupported = sorted(set(languages) - SUPPORTED_LANGUAGES)
    if unsupported:
        raise SystemExit(f"Unsupported languages: {', '.join(unsupported)}")

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        raise SystemExit(f"Corpus directory not found: {corpus_dir}")

    source_catalog = load_source_catalog(args.source_catalog)

    files = markdown_files(corpus_dir, languages)
    standards = [standard.strip() for standard in args.standards.split(",") if standard.strip()]
    if standards:
        files = filter_files_by_standards(files, standards, source_catalog, corpus_dir=corpus_dir)
    if not files:
        scope = f" and standards {', '.join(standards)}" if standards else ""
        raise SystemExit(f"No markdown files found for languages {languages}{scope} in {corpus_dir}")

    if source_catalog:
        print(f"Loaded source catalog: {args.source_catalog}")
        unmatched = unmatched_catalog_files(files, source_catalog, corpus_dir=corpus_dir)
        if unmatched and not args.allow_uncataloged:
            preview = ", ".join(path.name for path in unmatched[:5])
            more = f" and {len(unmatched) - 5} more" if len(unmatched) > 5 else ""
            raise SystemExit(
                "Source catalog did not match all selected markdown files; refusing "
                f"to build a partially quarantined answer index. Unmatched: {preview}{more}. "
                "Update derived_path entries or pass --allow-uncataloged for a diagnostic index."
            )
    elif not args.allow_uncataloged:
        raise SystemExit(
            "Refusing to ingest without --source-catalog because uncataloged chunks "
            "are quarantined and cannot support answers. Pass --allow-uncataloged "
            "only for explicit diagnostic indexes."
        )

    print(f"Loading embedding model: {args.model}")
    model = SentenceTransformer(args.model)

    print(f"Initializing ChromaDB at: {args.chroma_dir}")
    client = chromadb.PersistentClient(path=args.chroma_dir)
    if args.reset:
        reset_collection(client, args.collection)
    collection = client.get_or_create_collection(
        args.collection,
        metadata={"hnsw:space": "cosine"},
    )

    scope = f" and standards: {', '.join(standards)}" if standards else ""
    print(f"Found {len(files)} AAOIFI standards to process for languages: {', '.join(languages)}{scope}")
    total_chunks, bm25_docs = ingest_files(
        files,
        model,
        collection,
        build_splitter(),
        args.model,
        source_catalog=source_catalog,
        corpus_dir=corpus_dir,
    )

    if bm25_docs:
        from src.rag.pipeline import BM25Retriever
        print(f"Building BM25 index for {len(bm25_docs)} chunks...")
        bm25_retriever = BM25Retriever(bm25_docs)
        bm25_path = Path(args.chroma_dir) / "bm25_index.pkl"
        bm25_retriever.save(bm25_path)
        print(f"BM25 index saved to: {bm25_path}")

    print(f"\n{'=' * 60}")
    print("Ingestion complete!")
    print(f"Total chunks stored: {total_chunks}")
    print(f"ChromaDB location: {args.chroma_dir}")
    print(f"Collection: {args.collection}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
