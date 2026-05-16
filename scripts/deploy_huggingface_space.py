"""Deploy Mushir to a Hugging Face Docker Space.

Required environment:
  HF_TOKEN: Hugging Face user access token with write access.
  OPENROUTER_API_KEY: OpenRouter API key to store as a Space secret.

Example:
  python scripts/deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import CommitOperationAdd, HfApi


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


IGNORE_PATTERNS = [
    ".git/*",
    ".venv/*",
    "__pycache__/*",
    ".pytest_cache/*",
    ".mypy_cache/*",
    ".ruff_cache/*",
    ".pytest-tmp/*",
    ".env",
    "*.log",
    "*.png",
    "logs/*",
    "data/*",
    "chroma_db/*",
    ".agent/*",
    ".agents/*",
    ".bob/*",
    ".claude/*",
    ".codex/*",
    ".kiro/*",
    ".playwright-mcp/*",
    ".trae/*",
    "superpowers/*",
    "_bmad/*",
    "_bmad-output/*",
    "gemini-gem-prototype/**/*.pdf",
]


ALLOW_PATTERNS = [
    "Dockerfile",
    "README.md",
    "requirements.txt",
    "src/**",
    "config/**",
    "gemini-gem-prototype/knowledge-base/**",
    "chroma_db_multilingual/**",
]


UPLOAD_PATHS = [
    Path("Dockerfile"),
    Path("README.md"),
    Path("requirements.txt"),
    Path("src"),
    Path("config"),
    Path("gemini-gem-prototype") / "knowledge-base",
    Path("chroma_db_multilingual"),
]

BATCH_SIZE_BYTES = 25 * 1024 * 1024


SPACE_VARIABLES = {
    "OPENROUTER_MODEL": "anthropic/claude-3-haiku",
    "OPENROUTER_MAX_TOKENS": "1024",
    "VECTOR_DB_TYPE": "chroma",
    "CHROMA_DIR": "/app/chroma_db_multilingual",
    "EMBED_MODEL": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "REQUIRE_ARABIC_RETRIEVAL": "true",
    "CORPUS_DIR": "/app/gemini-gem-prototype/knowledge-base",
    "SESSION_STORE_TYPE": "memory",
    "RATE_LIMIT_STORE_TYPE": "memory",
    "CACHE_STORE_TYPE": "memory",
    "REQUIRE_DISCLAIMER_ACK": "false",
    "LOG_LEVEL": "INFO",
    "API_HOST": "0.0.0.0",
    "API_PORT": "8000",
}


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def iter_upload_files() -> list[Path]:
    files: list[Path] = []
    for upload_path in UPLOAD_PATHS:
        full_path = ROOT / upload_path
        if full_path.is_file():
            files.append(full_path)
        elif full_path.is_dir():
            files.extend(path for path in full_path.rglob("*") if path.is_file())
    return files


def upload_in_batches(api: HfApi, repo_id: str, commit_message: str) -> None:
    batch: list[Path] = []
    batch_size = 0
    batch_index = 1

    def flush() -> None:
        nonlocal batch, batch_size, batch_index
        if not batch:
            return
        operations = [
            CommitOperationAdd(
                path_in_repo=path.relative_to(ROOT).as_posix(),
                path_or_fileobj=str(path),
            )
            for path in batch
        ]
        print(
            f"Uploading batch {batch_index}: {len(batch)} files, "
            f"{batch_size / 1024 / 1024:.1f} MB",
            flush=True,
        )
        api.create_commit(
            repo_id=repo_id,
            repo_type="space",
            operations=operations,
            commit_message=f"{commit_message} ({batch_index})",
            num_threads=8,
        )
        batch = []
        batch_size = 0
        batch_index += 1

    for path in iter_upload_files():
        size = path.stat().st_size
        if batch and batch_size + size > BATCH_SIZE_BYTES:
            flush()
        batch.append(path)
        batch_size += size
        if size >= BATCH_SIZE_BYTES:
            flush()
    flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True, help="Space repo id, for example user/mushir-sharia-bot")
    parser.add_argument("--private", action="store_true", help="Create the Space as private")
    parser.add_argument(
        "--commit-message",
        default="Deploy Mushir Sharia Bot Docker Space",
        help="Commit message for the Space upload",
    )
    args = parser.parse_args()

    token = require_env("HF_TOKEN")
    openrouter_api_key = require_env("OPENROUTER_API_KEY")

    index_path = ROOT / "chroma_db_multilingual" / "chroma.sqlite3"
    if not index_path.exists():
        raise SystemExit(
            "Missing chroma_db_multilingual/chroma.sqlite3. "
            "Run bilingual ingest before deploying."
        )

    api = HfApi(token=token)
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
    )

    api.add_space_secret(repo_id=args.repo_id, key="OPENROUTER_API_KEY", value=openrouter_api_key)
    for key, value in SPACE_VARIABLES.items():
        api.add_space_variable(repo_id=args.repo_id, key=key, value=value)

    upload_in_batches(api, args.repo_id, args.commit_message)

    print(f"Uploaded Space: https://huggingface.co/spaces/{args.repo_id}")
    print(f"Public app URL: https://{args.repo_id.replace('/', '-')}.hf.space")


if __name__ == "__main__":
    main()
