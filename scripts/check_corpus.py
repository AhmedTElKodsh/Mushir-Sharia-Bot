"""
Check if AAOIFI corpus exists and is ready for ingestion.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CORPUS_DIR = os.getenv("CORPUS_DIR", "./data/aaoifi_md")

def check_corpus():
    """Verify AAOIFI markdown corpus exists."""
    corpus_path = Path(CORPUS_DIR)
    
    print("="*60)
    print("L0 Corpus Check")
    print("="*60)
    print()
    
    # Check if directory exists
    if not corpus_path.exists():
        print(f"❌ Corpus directory not found: {CORPUS_DIR}")
        print()
        print("Action required:")
        print(f"  1. Create directory: mkdir -p {CORPUS_DIR}")
        print("  2. Add AAOIFI markdown files")
        return False
    
    print(f"✓ Corpus directory exists: {CORPUS_DIR}")
    
    # Check for markdown files
    md_files = [
        f for f in corpus_path.rglob("*.md") 
        if f.name not in ["INDEX.md", "CONVERSION_SUMMARY.md", ".gitkeep"]
    ]
    
    if not md_files:
        print(f"❌ No markdown files found in {CORPUS_DIR}")
        print()
        print("Action required:")
        print("  Add AAOIFI markdown files to the corpus directory")
        return False
    
    # Check for English files
    en_files = [f for f in md_files if "_en_" in f.name or "_en." in f.name]
    ar_files = [f for f in md_files if "_ar_" in f.name or "_ar." in f.name]
    other_files = [f for f in md_files if f not in en_files and f not in ar_files]
    
    print(f"✓ Found {len(md_files)} total markdown files")
    print(f"  • English: {len(en_files)} files")
    print(f"  • Arabic: {len(ar_files)} files")
    if other_files:
        print(f"  • Other: {len(other_files)} files")
    print()
    
    if not en_files:
        print("⚠ No English files found (looking for '_en_' in filename)")
        print("  L0 uses English-only embedding model")
        print("  Add English AAOIFI files or use multilingual model")
        return False
    
    print("Sample English files:")
    for md_file in en_files[:5]:
        size_kb = md_file.stat().st_size / 1024
        print(f"  • {md_file.name[:60]}... ({size_kb:.1f} KB)")
    
    if len(en_files) > 5:
        print(f"  ... and {len(en_files) - 5} more")
    
    print()
    
    # Estimate chunks and storage
    total_size_mb = sum(f.stat().st_size for f in en_files) / (1024 * 1024)
    estimated_chunks = int(total_size_mb * 5)  # Rough estimate: 5 chunks per KB
    estimated_storage_mb = estimated_chunks * 0.1  # Rough estimate: 100KB per chunk
    
    print("Estimated ingestion:")
    print(f"  • Total corpus size: {total_size_mb:.1f} MB")
    print(f"  • Estimated chunks: ~{estimated_chunks:,}")
    print(f"  • Estimated ChromaDB size: ~{estimated_storage_mb:.0f} MB")
    print(f"  • Estimated time: ~{max(1, int(len(en_files) / 10))} minutes")
    
    print()
    print("="*60)
    print("✓ Corpus is ready for ingestion!")
    print("="*60)
    print()
    print("Next step: python scripts/ingest.py")
    return True

if __name__ == "__main__":
    check_corpus()
