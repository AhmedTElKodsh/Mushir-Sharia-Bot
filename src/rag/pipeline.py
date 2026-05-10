"""
L0 RAG Pipeline
Retrieves relevant AAOIFI chunks for a given query.
"""
import os
from typing import Any, List, Optional
from dotenv import load_dotenv
from src.models.schema import SemanticChunk, AAOIFICitation

load_dotenv()


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

        self.persist_dir = persist_dir or os.getenv("CHROMA_DIR", "./chroma_db")
        self.model_name = model_name or os.getenv("EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2")

        from sentence_transformers import SentenceTransformer
        import chromadb

        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        print(f"Connecting to ChromaDB: {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_collection("aaoifi")
        
        print(f"Collection contains {self.collection.count()} chunks")
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string."""
        if self.embedding_generator is not None:
            return self.embedding_generator.embed_text(query)
        return self.model.encode(query).tolist()
    
    def retrieve(self, query: str, k: int = 5, threshold: float = 0.3) -> List[Any]:
        """
        Retrieve top-k relevant chunks for a query.
        
        Args:
            query: User question
            k: Number of chunks to retrieve
            threshold: Minimum similarity score (1 - distance)
        
        Returns:
            List of SemanticChunk objects with citations
        """
        query_embedding = self.embed_query(query)

        if self.vector_store is not None:
            return self.vector_store.similarity_search(query_embedding, k=k, threshold=threshold)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        # Convert to SemanticChunk objects
        chunks = []
        fallback_chunks = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                similarity = 1 - distance  # Convert distance to similarity

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
                    score=similarity
                )
                fallback_chunks.append(chunk)

                # Filter by threshold
                if similarity >= threshold:
                    chunks.append(chunk)
        
        return chunks or fallback_chunks[:k]

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
