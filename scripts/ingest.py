"""
L0 Ingestion Script
Chunks AAOIFI markdown files and embeds them into ChromaDB.
"""
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

# Load environment variables
load_dotenv()

# Configuration
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
CORPUS_DIR = os.getenv("CORPUS_DIR", "./data/aaoifi_md")

# Initialize components
print(f"Loading embedding model: {EMBED_MODEL}")
model = SentenceTransformer(EMBED_MODEL)

print(f"Initializing ChromaDB at: {CHROMA_DIR}")
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection("aaoifi")

# Text splitter for semantic chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Process corpus
corpus_path = Path(CORPUS_DIR)
if not corpus_path.exists():
    print(f"ERROR: Corpus directory not found: {CORPUS_DIR}")
    print("Please ensure AAOIFI markdown files exist in data/aaoifi_md/")
    exit(1)

# Process corpus
corpus_path = Path(CORPUS_DIR)
if not corpus_path.exists():
    print(f"ERROR: Corpus directory not found: {CORPUS_DIR}")
    print("Please ensure AAOIFI markdown files exist in the corpus directory")
    exit(1)

# Find all markdown files (excluding INDEX and CONVERSION_SUMMARY)
md_files = [
    f for f in corpus_path.rglob("*.md") 
    if f.name not in ["INDEX.md", "CONVERSION_SUMMARY.md", ".gitkeep"]
]

# Filter to English files only for L0 (all-mpnet-base-v2 is English-only)
# Files ending with _en_ are English versions
en_files = [f for f in md_files if "_en_" in f.name or "_en." in f.name]

if not en_files:
    print(f"ERROR: No English markdown files found in {CORPUS_DIR}")
    print("Looking for files with '_en_' or '_en.' in filename")
    exit(1)

print(f"Found {len(en_files)} English AAOIFI standards to process")
print(f"(Skipping {len(md_files) - len(en_files)} Arabic files - use multilingual model for Arabic support)")
print()

total_chunks = 0
for md_file in en_files:
    print(f"\nProcessing: {md_file.name}")
    
    try:
        text = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)
        
        print(f"  Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            # Generate unique chunk ID
            chunk_id = hashlib.md5(f"{md_file.name}:{i}".encode()).hexdigest()
            
            # Generate embedding
            embedding = model.encode(chunk).tolist()
            
            # Store in ChromaDB
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source_file": md_file.name,
                    "chunk_idx": i,
                    "total_chunks": len(chunks)
                }]
            )
            
            total_chunks += 1
        
        print(f"  ✓ Stored {len(chunks)} chunks")
        
    except Exception as e:
        print(f"  ✗ Error processing {md_file.name}: {e}")
        continue

print(f"\n{'='*60}")
print(f"Ingestion complete!")
print(f"Total chunks stored: {total_chunks}")
print(f"ChromaDB location: {CHROMA_DIR}")
print(f"{'='*60}")
