"""
L0 CLI Chatbot
Terminal-based AAOIFI compliance chatbot with RAG.
"""
import os
import argparse
import uuid
from dotenv import load_dotenv
from src.rag.pipeline import RAGPipeline
from src.chatbot.clarification_engine import ClarificationEngine
from src.models.session import ClarificationState, SessionState
from src.models.schema import ComplianceRuling

load_dotenv()

# System prompt for AAOIFI adherence
AAOIFI_ADHERENCE_SYSTEM_PROMPT = """You are a Sharia compliance assistant specializing in AAOIFI standards.

CRITICAL RULES:
1. Answer ONLY from the provided AAOIFI excerpts below
2. If the excerpts do not cover the question, reply: "Not addressed in retrieved AAOIFI standards."
3. Always cite the standard_id and section in your answer using format: [standard_id §section]
4. Do not speculate or provide information not present in the excerpts
5. Be precise and reference specific provisions

Your role is to ground all compliance guidance strictly in AAOIFI standards."""

# Prompt template
TEMPLATE = """Excerpts from AAOIFI Standards:

{chunks}

Question: {question}

Answer with citations in format [standard_id §section]:"""


def format_chunks(chunks) -> str:
    """Format retrieved chunks for LLM prompt."""
    formatted = []
    for i, chunk in enumerate(chunks, 1):
        citation = chunk.citation
        formatted.append(
            f"[{citation.standard_id}] (Score: {chunk.score:.2f})\n{chunk.text}\n"
        )
    return "\n---\n".join(formatted)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call Google Gemini API.
    
    Args:
        system_prompt: System instructions
        user_prompt: User query with context
    
    Returns:
        LLM response text
    """
    from src.chatbot.llm_client import GeminiClient

    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    return GeminiClient().generate(full_prompt)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="L1 AAOIFI Compliance Chatbot - Terminal RAG Demo"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Compliance question to ask"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run an L1 clarification loop before generating the ruling"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("L1 AAOIFI Compliance Chatbot")
    print("="*80)
    print()
    
    query = args.query
    if args.interactive:
        query = run_clarification_loop(initial_query=args.query)
    elif not query:
        parser.error("--query is required unless --interactive is used")

    # Initialize RAG pipeline
    print("Initializing RAG pipeline...")
    rag = RAGPipeline()
    print()
    
    # Retrieve relevant chunks
    print(f"Query: {query}")
    print(f"\nRetrieving top-{args.k} relevant chunks...")
    chunks = rag.retrieve(query, k=args.k)
    
    if not chunks:
        print("\n❌ No relevant AAOIFI standards found for this query.")
        print("Try rephrasing or check if the corpus covers this topic.")
        return
    
    print(f"✓ Retrieved {len(chunks)} chunks")
    print()
    
    # Format chunks for prompt
    formatted_chunks = format_chunks(chunks)
    user_prompt = TEMPLATE.format(chunks=formatted_chunks, question=query)
    
    # Call LLM
    print("Generating compliance ruling...")
    try:
        answer = call_llm(AAOIFI_ADHERENCE_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        print(f"\n❌ Error calling LLM: {e}")
        return
    
    # Create ruling
    ruling = ComplianceRuling(
        question=query,
        answer=answer,
        chunks=chunks,
        confidence=sum(c.score for c in chunks) / len(chunks) if chunks else 0.0
    )
    
    # Display result
    print()
    print("="*80)
    print("COMPLIANCE RULING")
    print("="*80)
    print()
    print(ruling.answer)
    print()
    print("-"*80)
    print(f"Retrieved {len(ruling.chunks)} AAOIFI excerpts")
    print(f"Average relevance score: {ruling.confidence:.2f}")
    print()
    print("Sources:")
    for chunk in ruling.chunks:
        print(f"  • {chunk.citation.standard_id} (score: {chunk.score:.2f})")
    print("="*80)


def run_clarification_loop(initial_query: str = None) -> str:
    """Run the L1 interactive clarification flow and return the clarified query."""
    engine = ClarificationEngine()
    session = SessionState(session_id=str(uuid.uuid4()))

    print("Clarification mode. Type 'exit' to quit.")
    query = initial_query or input("\nQuestion: ").strip()

    while True:
        if query.lower() in {"exit", "quit"}:
            raise SystemExit(0)

        result = engine.process_query(session, query)
        if result["status"] == "ready" or session.state == ClarificationState.READY:
            print("\n✓ Clarification complete")
            return engine.build_clarified_query(session)

        for question in result.get("questions", []):
            print(f"\n{question}")
        query = input("> ").strip()


if __name__ == "__main__":
    main()
