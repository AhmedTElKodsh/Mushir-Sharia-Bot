"""RAG package exports.

Keep heavyweight retrieval dependencies lazy so importing chunking utilities does
not load embedding or ChromaDB modules.
"""

__all__ = ["RAGPipeline"]


def __getattr__(name):
    if name == "RAGPipeline":
        from src.rag.pipeline import RAGPipeline

        return RAGPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
