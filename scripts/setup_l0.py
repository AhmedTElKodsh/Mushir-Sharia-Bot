"""
L0 Setup Script
Quick setup verification for L0 environment.
"""
import os
import sys
from pathlib import Path

def check_python_version():
    """Verify Python 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. Found: {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    if not in_venv:
        print("⚠ Not running in virtual environment")
        print("  Recommended: python -m venv .venv && activate")
        return False
    print("✓ Virtual environment active")
    return True

def check_env_file():
    """Check if .env exists"""
    if not Path(".env").exists():
        print("❌ .env file not found")
        print("  Action: cp .env.example .env")
        print("  Then add your OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return False
    print("✓ .env file exists")
    return True

def check_api_key():
    """Check if API key is configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    
    if openrouter_key and len(openrouter_key) > 20:
        print("✓ OpenRouter API key configured")
        return True
    else:
        print("❌ No valid OpenRouter API key found in .env")
        print("  Set OPENROUTER_API_KEY=your-key-here")
        print("  Get your key from: https://openrouter.ai/keys")
        return False

def check_dependencies():
    """Check if key dependencies are installed"""
    try:
        import sentence_transformers
        import chromadb
        import langchain_text_splitters
        import google.generativeai
        print("✓ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("  Action: pip install -r requirements.txt")
        return False

def check_corpus():
    """Check if corpus directory exists"""
    corpus_dir = Path("data/aaoifi_md")
    if not corpus_dir.exists():
        print("❌ Corpus directory not found: data/aaoifi_md")
        return False
    
    md_files = list(corpus_dir.rglob("*.md"))
    if not md_files:
        print("⚠ No markdown files in data/aaoifi_md")
        print("  Action: Run AAOIFI converter to populate corpus")
        return False
    
    print(f"✓ Corpus ready ({len(md_files)} files)")
    return True

def main():
    """Run all checks"""
    print("="*60)
    print("L0 Setup Verification")
    print("="*60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_venv),
        ("Environment File", check_env_file),
        ("API Key", check_api_key),
        ("Dependencies", check_dependencies),
        ("AAOIFI Corpus", check_corpus),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n{name}:")
        try:
            result = check_fn()
            results.append(result)
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    print()
    print("="*60)
    
    if all(results):
        print("✓ All checks passed! Ready to run L0")
        print()
        print("Next steps:")
        print("  1. python scripts/ingest.py")
        print("  2. pytest -v")
        print('  3. python -m src.chatbot.cli --query "your question"')
    else:
        print("⚠ Some checks failed. Fix issues above before proceeding.")
        print()
        print("Quick setup:")
        print("  1. python -m venv .venv")
        print("  2. .venv\\Scripts\\activate  (Windows)")
        print("  3. pip install -r requirements.txt")
        print("  4. cp .env.example .env")
        print("  5. Edit .env and add API key")
        print("  6. Add AAOIFI markdown files to data/aaoifi_md/")
    
    print("="*60)

if __name__ == "__main__":
    main()
