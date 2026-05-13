#!/usr/bin/env python3
"""
Deploy Mushir Sharia Bot to Hugging Face Space.

This script:
1. Validates local setup (vector DB, corpus, API key)
2. Uploads application code, vector DB, and corpus to HF Space
3. Configures Space secrets and environment variables
4. Triggers Space rebuild

Usage:
    python scripts/deploy_to_hf.py

Requirements:
    - huggingface_hub installed: pip install huggingface_hub
    - HF_TOKEN environment variable set
    - Local vector database populated (chroma_db_multilingual/)
    - Corpus files present (gemini-gem-prototype/knowledge-base/)
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_prerequisites() -> Tuple[bool, List[str]]:
    """Check if all prerequisites are met for deployment."""
    errors = []
    
    # Check HF token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        errors.append("❌ HF_TOKEN not set. Get it from https://huggingface.co/settings/tokens")
    
    # Check OpenRouter API key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        errors.append("❌ OPENROUTER_API_KEY not set in .env")
    
    # Check vector database
    chroma_dir = PROJECT_ROOT / "chroma_db_multilingual"
    if not chroma_dir.exists():
        errors.append(f"❌ Vector database not found: {chroma_dir}")
    elif not list(chroma_dir.glob("**/*.parquet")):
        errors.append(f"❌ Vector database is empty. Run: python scripts/ingest.py")
    
    # Check corpus
    corpus_dir = PROJECT_ROOT / "gemini-gem-prototype" / "knowledge-base"
    if not corpus_dir.exists():
        errors.append(f"❌ Corpus directory not found: {corpus_dir}")
    else:
        md_files = list(corpus_dir.glob("*.md"))
        if len(md_files) < 5:
            errors.append(f"❌ Insufficient corpus files ({len(md_files)} found, need at least 5)")
    
    # Check required files
    required_files = [
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "src/api/main.py",
        "src/chatbot/llm_client.py",
    ]
    for file_path in required_files:
        if not (PROJECT_ROOT / file_path).exists():
            errors.append(f"❌ Required file missing: {file_path}")
    
    return len(errors) == 0, errors


def deploy_to_huggingface(space_id: str = "AElKodsh/mushir-sharia-bot"):
    """Deploy application to Hugging Face Space."""
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("❌ huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)
    
    print("🚀 Deploying Mushir Sharia Bot to Hugging Face Space")
    print(f"   Space: {space_id}")
    print()
    
    # Check prerequisites
    print("📋 Checking prerequisites...")
    success, errors = check_prerequisites()
    if not success:
        print("\n❌ Prerequisites check failed:\n")
        for error in errors:
            print(f"   {error}")
        print("\n💡 Fix the issues above and try again.")
        sys.exit(1)
    print("✅ All prerequisites met\n")
    
    # Initialize HF API
    api = HfApi()
    hf_token = os.getenv("HF_TOKEN")
    
    # Ensure Space exists
    print(f"📦 Ensuring Space exists: {space_id}")
    try:
        create_repo(
            repo_id=space_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            token=hf_token,
        )
        print("✅ Space ready\n")
    except Exception as e:
        print(f"❌ Failed to create/access Space: {e}")
        sys.exit(1)
    
    # Upload files
    files_to_upload = [
        # Core application
        ("Dockerfile", "Dockerfile"),
        ("requirements.txt", "requirements.txt"),
        ("README.md", "README.md"),
        
        # Source code
        ("src/", "src/"),
        
        # Configuration
        ("config/", "config/"),
        
        # Scripts (for reference)
        ("scripts/ingest.py", "scripts/ingest.py"),
        ("scripts/check_corpus.py", "scripts/check_corpus.py"),
    ]
    
    print("📤 Uploading application files...")
    for local_path, remote_path in files_to_upload:
        full_local_path = PROJECT_ROOT / local_path
        if not full_local_path.exists():
            print(f"⚠️  Skipping missing file: {local_path}")
            continue
        
        try:
            if full_local_path.is_dir():
                api.upload_folder(
                    folder_path=str(full_local_path),
                    path_in_repo=remote_path,
                    repo_id=space_id,
                    repo_type="space",
                    token=hf_token,
                )
                print(f"   ✅ {local_path}/ → {remote_path}/")
            else:
                api.upload_file(
                    path_or_fileobj=str(full_local_path),
                    path_in_repo=remote_path,
                    repo_id=space_id,
                    repo_type="space",
                    token=hf_token,
                )
                print(f"   ✅ {local_path} → {remote_path}")
        except Exception as e:
            print(f"   ❌ Failed to upload {local_path}: {e}")
    
    # Upload vector database
    print("\n📤 Uploading vector database (this may take a while)...")
    chroma_dir = PROJECT_ROOT / "chroma_db_multilingual"
    try:
        api.upload_folder(
            folder_path=str(chroma_dir),
            path_in_repo="chroma_db_multilingual",
            repo_id=space_id,
            repo_type="space",
            token=hf_token,
        )
        print("   ✅ Vector database uploaded")
    except Exception as e:
        print(f"   ❌ Failed to upload vector database: {e}")
    
    # Upload corpus
    print("\n📤 Uploading knowledge base corpus...")
    corpus_dir = PROJECT_ROOT / "gemini-gem-prototype" / "knowledge-base"
    try:
        api.upload_folder(
            folder_path=str(corpus_dir),
            path_in_repo="gemini-gem-prototype/knowledge-base",
            repo_id=space_id,
            repo_type="space",
            token=hf_token,
        )
        print("   ✅ Corpus uploaded")
    except Exception as e:
        print(f"   ❌ Failed to upload corpus: {e}")
    
    # Configure secrets
    print("\n🔐 Configuring Space secrets...")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            api.add_space_secret(
                repo_id=space_id,
                key="OPENROUTER_API_KEY",
                value=openrouter_key,
                token=hf_token,
            )
            print("   ✅ OPENROUTER_API_KEY configured")
        except Exception as e:
            print(f"   ⚠️  Failed to set OPENROUTER_API_KEY: {e}")
            print("   💡 Set it manually in Space Settings → Repository Secrets")
    
    # Configure environment variables
    print("\n⚙️  Configuring environment variables...")
    env_vars = {
        "OPENROUTER_MODEL": "google/gemini-2.0-flash-exp:free",
        "VECTOR_DB_TYPE": "chroma",
        "EMBED_MODEL": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "REQUIRE_ARABIC_RETRIEVAL": "true",
        "APP_ENV": "dev",
        "LOG_LEVEL": "INFO",
    }
    
    for key, value in env_vars.items():
        try:
            api.add_space_variable(
                repo_id=space_id,
                key=key,
                value=value,
                token=hf_token,
            )
            print(f"   ✅ {key}={value}")
        except Exception as e:
            print(f"   ⚠️  Failed to set {key}: {e}")
    
    print("\n" + "="*60)
    print("✅ Deployment complete!")
    print("="*60)
    print()
    print(f"🌐 Space URL: https://huggingface.co/spaces/{space_id}")
    print(f"🔗 App URL: https://{space_id.replace('/', '-')}.hf.space")
    print()
    print("📝 Next steps:")
    print("   1. Wait for Space to build (check logs in Space UI)")
    print("   2. Verify /health endpoint returns 200")
    print("   3. Test /chat interface")
    print("   4. Check Space logs for any errors")
    print()
    print("💡 If Space shows 'Refused to connect':")
    print("   - Verify OPENROUTER_API_KEY is set in Space Settings → Repository Secrets")
    print("   - Check Space logs for build/runtime errors")
    print("   - Ensure vector database and corpus were uploaded successfully")
    print()


if __name__ == "__main__":
    deploy_to_huggingface()
