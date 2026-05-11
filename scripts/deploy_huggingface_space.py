"""Deploy Mushir to a Hugging Face Docker Space.

Required environment:
  HF_TOKEN: Hugging Face user access token with write access.
  GEMINI_API_KEY: Gemini key to store as a Space secret.

Example:
  python scripts/deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


ROOT = Path(__file__).resolve().parents[1]


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


SPACE_VARIABLES = {
    "GEMINI_MODEL": "gemini-2.5-flash",
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
    gemini_api_key = require_env("GEMINI_API_KEY")

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

    api.add_space_secret(repo_id=args.repo_id, key="GEMINI_API_KEY", value=gemini_api_key)
    for key, value in SPACE_VARIABLES.items():
        api.add_space_variable(repo_id=args.repo_id, key=key, value=value)

    api.upload_folder(
        repo_id=args.repo_id,
        repo_type="space",
        folder_path=str(ROOT),
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        commit_message=args.commit_message,
    )

    print(f"Uploaded Space: https://huggingface.co/spaces/{args.repo_id}")
    print(f"Public app URL: https://{args.repo_id.replace('/', '-')}.hf.space")


if __name__ == "__main__":
    main()
