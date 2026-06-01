"""Deploy Mushir to a Hugging Face Docker Space.

Required environment:
  HF_TOKEN: Hugging Face user access token with write access.
  OPENROUTER_API_KEY: OpenRouter API key to store as a Space secret.
    Optional when using --ui-only.

Example:
  python scripts/deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot
  python scripts/deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot --ui-only
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
]


ALLOW_PATTERNS = [
    "Dockerfile",
    "README.md",
    "requirements.txt",
    "src/**",
    "config/**",
    "scripts/report_sharia_corpus_coverage.py",
    "data/source_registry/**",
    "chroma_db_multilingual/**",
]


UPLOAD_PATHS = [
    Path("Dockerfile"),
    Path("README.md"),
    Path("requirements.txt"),
    Path("src"),
    Path("config"),
    Path("scripts") / "report_sharia_corpus_coverage.py",
    Path("data") / "source_registry",
    Path("chroma_db_multilingual"),
]

BATCH_SIZE_BYTES = 25 * 1024 * 1024


SPACE_VARIABLES = {
    "OPENROUTER_MODEL": "openrouter/free",
    "OPENROUTER_MAX_TOKENS": "1024",
    "EMBED_MODEL": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "REQUIRE_ARABIC_RETRIEVAL": "true",
    "REQUIRE_GOVERNED_SOURCE_METADATA": "true",
    "APP_ENV": "public-demo",
    "RELEASE_TIER": "public-demo",
    "SESSION_STORE_TYPE": "memory",
    "RATE_LIMIT_STORE_TYPE": "memory",
    "CACHE_STORE_TYPE": "memory",
    "REQUIRE_DISCLAIMER_ACK": "false",
    "LOG_LEVEL": "INFO",
    "API_HOST": "0.0.0.0",
    "API_PORT": "8000",
}

SECRET_ENV_KEYS = [
    "OPENROUTER_API_KEY",
    "QDRANT_API_KEY",
    "AUTH_TOKEN",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL",
    "AUDIT_DATABASE_URL",
]

OPTIONAL_VARIABLE_ENV_KEYS = [
    "QDRANT_URL",
    "QDRANT_COLLECTION",
    "QDRANT_VECTOR_SIZE",
    "QDRANT_TIMEOUT_SECONDS",
    "SUPABASE_PROJECT_REF",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "APP_ENV",
    "CORS_ORIGINS",
]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def require_real_env(name: str) -> str:
    value = require_env(name)
    lowered = value.strip().lower()
    if "your-" in lowered or "example" in lowered or lowered.endswith("localhost:6333"):
        raise SystemExit(f"Environment variable {name} still looks like a placeholder/local value")
    return value


def iter_upload_files(upload_paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for upload_path in upload_paths:
        full_path = ROOT / upload_path
        if full_path.is_file():
            files.append(full_path)
        elif full_path.is_dir():
            files.extend(path for path in full_path.rglob("*") if path.is_file())
    return files


def upload_in_batches(api: HfApi, repo_id: str, commit_message: str, upload_paths: list[Path]) -> None:
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

    for path in iter_upload_files(upload_paths):
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
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Do not upload chroma_db_multilingual. Use for app/runtime-only deploys.",
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Upload only src/static UI assets. Implies --skip-index.",
    )
    parser.add_argument(
        "--vector-store",
        choices=["chroma", "qdrant"],
        default=os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        help="Vector store backend for the deployed Space.",
    )
    args = parser.parse_args()

    token = require_env("HF_TOKEN")
    ui_only = bool(args.ui_only)
    vector_store = args.vector_store
    skip_index = bool(args.skip_index or ui_only or vector_store == "qdrant")
    upload_paths = [Path("src") / "static"] if ui_only else list(UPLOAD_PATHS)
    if skip_index:
        upload_paths = [path for path in upload_paths if path != Path("chroma_db_multilingual")]

    index_path = ROOT / "chroma_db_multilingual" / "chroma.sqlite3"
    if not skip_index and not index_path.exists():
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

    if not os.getenv("OPENROUTER_API_KEY") and not ui_only:
        raise SystemExit("Missing required environment variable: OPENROUTER_API_KEY")
    if vector_store == "qdrant":
        require_real_env("QDRANT_URL")
        require_real_env("QDRANT_API_KEY")

    if not ui_only:
        variables = {
            **SPACE_VARIABLES,
            "VECTOR_DB_TYPE": vector_store,
        }
        if vector_store == "chroma":
            variables["CHROMA_DIR"] = "/app/chroma_db_multilingual"
        for key in OPTIONAL_VARIABLE_ENV_KEYS:
            value = os.getenv(key)
            if value:
                variables[key] = value
        for key, value in variables.items():
            api.add_space_variable(repo_id=args.repo_id, key=key, value=value)
        for key in SECRET_ENV_KEYS:
            value = os.getenv(key)
            if value:
                api.add_space_secret(repo_id=args.repo_id, key=key, value=value)

    if skip_index:
        print("Skipping chroma_db_multilingual upload; existing Space index will be reused.", flush=True)
    if ui_only:
        print("UI-only deploy: uploading src/static assets only.", flush=True)

    upload_in_batches(api, args.repo_id, args.commit_message, upload_paths)

    print(f"Uploaded Space: https://huggingface.co/spaces/{args.repo_id}")
    print(f"Public app URL: https://{args.repo_id.replace('/', '-')}.hf.space")


if __name__ == "__main__":
    main()
