"""Ingest AAOIFI markdown files into ChromaDB."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import chromadb
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

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


def standard_number(path: Path) -> str:
    return path.stem


def build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def reset_collection(client, collection_name: str) -> None:
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def ingest_files(
    files: Iterable[Path],
    model: SentenceTransformer,
    collection,
    splitter: RecursiveCharacterTextSplitter,
    model_name: str,
) -> int:
    total_chunks = 0
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
            metadatas = [
                {
                    "source_file": md_file.name,
                    "standard_number": standard_number(md_file),
                    "language": language,
                    "source_language": source_language,
                    "embedding_model": model_name,
                    "embedding_normalized": True,
                    "chunk_idx": index,
                    "total_chunks": len(chunks),
                }
                for index, _ in enumerate(chunks)
            ]
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
            total_chunks += len(chunks)
            print(f"  Stored {len(chunks)} chunks")
        except Exception as exc:
            print(f"  Error processing {md_file.name}: {exc}")
            continue
    return total_chunks


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

    files = markdown_files(corpus_dir, languages)
    if not files:
        raise SystemExit(f"No markdown files found for languages {languages} in {corpus_dir}")

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

    print(f"Found {len(files)} AAOIFI standards to process for languages: {', '.join(languages)}")
    total_chunks = ingest_files(files, model, collection, build_splitter(), args.model)

    print(f"\n{'=' * 60}")
    print("Ingestion complete!")
    print(f"Total chunks stored: {total_chunks}")
    print(f"ChromaDB location: {args.chroma_dir}")
    print(f"Collection: {args.collection}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
