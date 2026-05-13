#!/usr/bin/env python3
"""
Check Hugging Face Space status and diagnose issues.

Usage:
    python scripts/check_hf_space.py
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_space_status(space_id: str = "AElKodsh/mushir-sharia-bot"):
    """Check Space status and diagnose issues."""
    space_url = f"https://{space_id.replace('/', '-')}.hf.space"
    
    print("🔍 Checking Hugging Face Space Status")
    print(f"   Space: {space_id}")
    print(f"   URL: {space_url}")
    print()
    
    # Check health endpoint
    print("📊 Checking /health endpoint...")
    try:
        response = requests.get(f"{space_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Health check passed: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            print(f"      Response: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection refused - Space may be down or building")
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout - Space may be overloaded")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Check ready endpoint
    print("📊 Checking /ready endpoint...")
    try:
        response = requests.get(f"{space_url}/ready", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Readiness check passed")
            print(f"      Status: {data.get('status')}")
            print(f"      Infrastructure: {data.get('infrastructure')}")
            print(f"      Checks: {data.get('checks')}")
        else:
            print(f"   ⚠️  Readiness check degraded: {response.status_code}")
            print(f"      Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection refused - Space may be down or building")
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout - Space may be overloaded")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Check chat page
    print("📊 Checking /chat page...")
    try:
        response = requests.get(f"{space_url}/chat", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Chat page accessible")
        else:
            print(f"   ❌ Chat page failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection refused - Space may be down or building")
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout - Space may be overloaded")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Check local prerequisites
    print("📋 Checking local prerequisites...")
    
    # Check .env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print("   ✅ .env file exists")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            print(f"   ✅ OPENROUTER_API_KEY set (length: {len(openrouter_key)})")
        else:
            print("   ❌ OPENROUTER_API_KEY not set in .env")
    else:
        print("   ❌ .env file not found")
    
    # Check vector database
    chroma_dir = PROJECT_ROOT / "chroma_db_multilingual"
    if chroma_dir.exists():
        parquet_files = list(chroma_dir.glob("**/*.parquet"))
        print(f"   ✅ Vector database exists ({len(parquet_files)} parquet files)")
    else:
        print("   ❌ Vector database not found")
    
    # Check corpus
    corpus_dir = PROJECT_ROOT / "gemini-gem-prototype" / "knowledge-base"
    if corpus_dir.exists():
        md_files = list(corpus_dir.glob("*.md"))
        print(f"   ✅ Corpus exists ({len(md_files)} markdown files)")
    else:
        print("   ❌ Corpus not found")
    
    print()
    print("="*60)
    print("💡 Troubleshooting Tips:")
    print("="*60)
    print()
    print("If Space shows 'Refused to connect':")
    print("   1. Check Space logs: https://huggingface.co/spaces/{}/logs".format(space_id))
    print("   2. Verify OPENROUTER_API_KEY in Space Settings → Repository Secrets")
    print("   3. Ensure Docker build completed successfully")
    print("   4. Check if vector database and corpus were uploaded")
    print()
    print("If health check fails:")
    print("   1. Check Space is running (not building or sleeping)")
    print("   2. Verify Dockerfile is valid")
    print("   3. Check requirements.txt has all dependencies")
    print()
    print("If ready check is degraded:")
    print("   1. Check OPENROUTER_API_KEY is valid")
    print("   2. Verify vector database is accessible")
    print("   3. Check Space environment variables")
    print()


if __name__ == "__main__":
    # Load .env
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    
    check_space_status()
