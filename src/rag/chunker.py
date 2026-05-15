from typing import List, Dict, Optional
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.models.chunk import SemanticChunk
from src.config.logging_config import setup_logging

logger = setup_logging()

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
MIN_TOKENS = 50
MAX_TOKENS = 512

# Separators supporting both English and Arabic document structures.
# Arabic-specific separators: Arabic comma (،), Arabic semicolon (؛),
# Arabic question mark (؟), and Arabic full stop (۔).
# These are literal string separators — RecursiveCharacterTextSplitter does
# not compile regex by default. For regex-level splitting, use a custom
# split function before the text splitter.
SEPARATORS = ["\n\n## ", "\n\n### ", "\n\n#### ", "\n\n", "\n", "،", "؛", "؟", "۔", ".", "!", "?", " ", ""]

def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars/4)."""
    return len(text) // 4

class SemanticChunker:
    """Semantic text chunker with section awareness."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            length_function=estimate_tokens,
        )

    def chunk_document(self, doc) -> List[SemanticChunk]:
        """Chunk a document into semantic chunks."""
        content = doc.content
        sections = self._extract_sections(content)
        chunks = []
        chunk_index = 0
        for section_num, (section_title, section_text) in enumerate(sections, 1):
            if not section_text.strip():
                continue
            raw_chunks = self.text_splitter.split_text(section_text)
            for i, chunk_text in enumerate(raw_chunks):
                token_count = estimate_tokens(chunk_text)
                if token_count < MIN_TOKENS:
                    continue
                token_count = min(token_count, MAX_TOKENS)
                chunk = SemanticChunk(
                    chunk_id=f"{doc.document_id}_{chunk_index}",
                    document_id=doc.document_id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    token_count=token_count,
                    metadata={
                        "section_number": str(section_num),
                        "section_title": section_title,
                        "source_url": doc.source_url,
                        "standard_number": doc.standard_number,
                    },
                )
                chunks.append(chunk)
                chunk_index += 1
        logger.info(f"Chunked {doc.document_id}: {len(chunks)} chunks")
        return chunks

    def _extract_sections(self, text: str) -> List[tuple]:
        """Extract sections from document text."""
        sections = []
        current_section = "Introduction"
        current_content = []
        for line in text.split("\n"):
            if re.match(r"^(#+\s+|\d+\.\s+|[A-Z]\.\s+)", line.strip()):
                if current_content:
                    sections.append((current_section, "\n".join(current_content)))
                current_section = line.strip()
                current_content = []
            else:
                current_content.append(line)
        if current_content:
            sections.append((current_section, "\n".join(current_content)))
        return sections or [("Full Document", text)]
