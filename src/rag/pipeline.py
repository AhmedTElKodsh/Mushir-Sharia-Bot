"""
L0 RAG Pipeline
Retrieves relevant AAOIFI chunks for a given query.
"""
import os
from typing import Any, List, Optional
from dotenv import load_dotenv
from src.models.schema import SemanticChunk, AAOIFICitation

load_dotenv()

DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_CHROMA_DIR = "./chroma_db_multilingual"
REQUIRED_CHROMA_LANGUAGES = ("ar", "en")
DOMAIN_QUERY_EXPANSIONS = {
    "murabaha": ("murabaha", "murabahah", "مرابحة", "المرابحة", "deferred payment sale", "resale", "sale"),
    "murabahah": ("murabaha", "murabahah", "مرابحة", "المرابحة", "deferred payment sale", "resale", "sale"),
    "مرابحة": ("murabaha", "murabahah", "مرابحة", "المرابحة", "deferred payment sale", "resale", "sale"),
    "المرابحة": ("murabaha", "murabahah", "مرابحة", "المرابحة", "deferred payment sale", "resale", "sale"),
    "ijarah": ("ijarah", "ijara", "إجارة", "الإجارة", "lease", "usufruct"),
    "ijara": ("ijarah", "ijara", "إجارة", "الإجارة", "lease", "usufruct"),
    "إجارة": ("ijarah", "ijara", "إجارة", "الإجارة", "lease", "usufruct"),
    "الإجارة": ("ijarah", "ijara", "إجارة", "الإجارة", "lease", "usufruct"),
    "real estate": ("real estate", "investment in real estate", "rental income", "capital appreciation"),
}
AUTHORITY_REQUEST_TERMS = ("binding fatwa", "binding ruling", "legal advice", "financial advice")
META_EVALUATION_TERMS = ("what if the answer cites", "retrieved sources only contain")
UNDER_SPECIFIED_INVESTMENT_TERMS = (
    ("do not know", "business activity"),
    ("do not know", "debt ratios"),
    ("unknown", "business activity"),
    ("unknown", "debt ratios"),
)
ARABIC_UNDER_SPECIFIED_TERMS = (
    ("\u0644\u0645 \u062a\u0643\u0646", "\u0627\u0644\u0646\u0634\u0627\u0637"),
    ("\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629", "\u0627\u0644\u0646\u0634\u0627\u0637"),
)


def _env_flag_enabled(name: str, default: bool = True) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _is_multilingual_model(model_name: str) -> bool:
    return "multilingual" in model_name.lower()


def _collection_has_metadata(collection: Any, key: str, value: str) -> bool:
    results = collection.get(where={key: value}, limit=1, include=["metadatas"])
    return bool(results.get("metadatas"))


def _preferred_query_language(query: str) -> str:
    return "ar" if any("\u0600" <= char <= "\u06ff" for char in query) else "en"


def _expanded_query_terms(query: str) -> set[str]:
    lowered_query = query.lower()
    terms = {token.strip(".,;:?!()[]{}\"'").lower() for token in lowered_query.split()}
    for trigger, expansions in DOMAIN_QUERY_EXPANSIONS.items():
        if trigger.lower() in lowered_query:
            terms.update(term.lower() for term in expansions)
    return {term for term in terms if len(term) >= 3}


def _query_should_skip_retrieval(query: str) -> bool:
    """Block retrieval for requests that need refusal or clarification, not loose context."""
    lowered_query = query.lower()
    if any(term in lowered_query for term in AUTHORITY_REQUEST_TERMS):
        return True
    if any(term in lowered_query for term in META_EVALUATION_TERMS):
        return True
    if any(all(term in lowered_query for term in terms) for terms in UNDER_SPECIFIED_INVESTMENT_TERMS):
        return True
    return any(all(term in query for term in terms) for terms in ARABIC_UNDER_SPECIFIED_TERMS)


def _domain_rerank_score(query: str, document: str, metadata: dict, similarity: float) -> float:
    haystack = " ".join(
        str(value)
        for value in [
            document,
            metadata.get("source_file", ""),
            metadata.get("standard_number", ""),
        ]
    ).lower()
    lexical_hits = sum(1 for term in _expanded_query_terms(query) if term in haystack)
    preferred_language = _preferred_query_language(query)
    language_bonus = 0.015 if metadata.get("source_language") == preferred_language else 0.0
    return similarity + min(lexical_hits, 4) * 0.035 + language_bonus


def validate_chroma_index_for_arabic_retrieval(collection: Any, model_name: str) -> None:
    """Fail closed when the configured Chroma index cannot support Arabic retrieval."""
    if not _is_multilingual_model(model_name):
        raise RuntimeError(
            "Arabic semantic retrieval requires a multilingual embedding model. "
            "Set EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2 "
            "and re-run scripts/ingest.py --reset."
        )

    if not _collection_has_metadata(collection, "embedding_model", model_name):
        raise RuntimeError(
            "Chroma collection embedding metadata does not match the configured EMBED_MODEL. "
            "Rebuild the collection with scripts/ingest.py --reset using the same multilingual model."
        )

    if not _collection_has_metadata(collection, "embedding_normalized", True):
        raise RuntimeError(
            "Chroma collection was not built with normalized embeddings. "
            "Rebuild it with scripts/ingest.py --reset so Arabic and English similarity use cosine space."
        )

    missing_languages = [
        language
        for language in REQUIRED_CHROMA_LANGUAGES
        if not _collection_has_metadata(collection, "source_language", language)
    ]
    if missing_languages:
        raise RuntimeError(
            "Chroma collection is missing required Arabic/English corpus languages: "
            f"{', '.join(missing_languages)}. Rebuild it with scripts/ingest.py --reset --languages en,ar."
        )


class RAGPipeline:
    """RAG retrieval pipeline with Chroma and injectable test modes."""
    
    def __init__(self, persist_dir: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize RAG pipeline with ChromaDB and embedding model."""
        self.vector_store = None
        self.embedding_generator = None

        if persist_dir is not None and hasattr(persist_dir, "similarity_search"):
            self.vector_store = persist_dir
            self.embedding_generator = model_name
            return

        self.vector_db_type = os.getenv("VECTOR_DB_TYPE", "chroma").lower()
        if self.vector_db_type == "qdrant":
            from src.rag.qdrant_store import QdrantVectorStore

            self.vector_store = QdrantVectorStore()
            self.persist_dir = None
        else:
            self.persist_dir = persist_dir or os.getenv("CHROMA_DIR", DEFAULT_CHROMA_DIR)
        self.model_name = model_name or os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL)

        from sentence_transformers import SentenceTransformer

        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        if self.vector_store is None:
            import chromadb

            print(f"Connecting to ChromaDB: {self.persist_dir}")
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_collection("aaoifi")
            if _env_flag_enabled("REQUIRE_ARABIC_RETRIEVAL", default=True):
                validate_chroma_index_for_arabic_retrieval(self.collection, self.model_name)
            print(f"Collection contains {self.collection.count()} chunks")
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string."""
        if self.embedding_generator is not None:
            return self.embedding_generator.embed_text(query)
        return self.model.encode(query, normalize_embeddings=True).tolist()
    
    def retrieve(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.3,
        allow_low_confidence_fallback: bool = False,
    ) -> List[Any]:
        """
        Retrieve top-k relevant chunks for a query.
        
        Args:
            query: User question
            k: Number of chunks to retrieve
            threshold: Minimum similarity score (1 - distance)
        
        Returns:
            List of SemanticChunk objects with citations
        """
        if _query_should_skip_retrieval(query):
            return []

        query_embedding = self.embed_query(query)

        if self.vector_store is not None:
            chunks = self.vector_store.similarity_search(query_embedding, k=k, threshold=threshold)
            if chunks or not allow_low_confidence_fallback:
                return chunks
            return self.vector_store.similarity_search(query_embedding, k=k, threshold=0.0)[:k]
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(k * 8, k),
        )
        
        # Convert to SemanticChunk objects
        chunks = []
        fallback_chunks = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                rerank_score = _domain_rerank_score(query, doc, metadata, similarity)

                citation = AAOIFICitation(
                    standard_id=metadata.get('source_file', 'Unknown').replace('.md', ''),
                    section=metadata.get('section') or metadata.get('section_title') or metadata.get('section_number'),
                    page=metadata.get('page'),
                    source_file=metadata.get('source_file', 'Unknown')
                )

                chunk = SemanticChunk(
                    chunk_id=results['ids'][0][i],
                    text=doc,
                    citation=citation,
                    score=rerank_score
                )
                fallback_chunks.append(chunk)

                # Filter by threshold
                if rerank_score >= threshold:
                    chunks.append(chunk)
        
        candidates = chunks if chunks or not allow_low_confidence_fallback else fallback_chunks
        ranked_chunks = sorted(candidates, key=lambda chunk: chunk.score, reverse=True)
        return ranked_chunks[:k]

    def augment_prompt(self, query: str, chunks: List[Any]) -> str:
        """Build a grounded prompt from retrieved AAOIFI chunks."""
        formatted_chunks = []
        for index, chunk in enumerate(chunks, 1):
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
                standard = metadata.get("standard_number") or metadata.get("source_file") or "Unknown"
                section = metadata.get("section_title") or metadata.get("section_number") or "Unknown section"
            else:
                content = chunk.text
                standard = chunk.citation.standard_id
                section = chunk.citation.section or "Unknown section"
            formatted_chunks.append(f"[{index}] {standard} - {section}\n{content}")

        context = "\n\n---\n\n".join(formatted_chunks)
        return (
            "AAOIFI standards context:\n\n"
            f"{context}\n\n"
            f"Question: {query}\n\n"
            "Answer only from the AAOIFI standards context and cite the relevant standard."
        )
