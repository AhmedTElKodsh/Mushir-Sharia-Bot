"""Terminal adapter for the same evidence-gated service used by the API."""
import argparse
import os
import uuid

from dotenv import load_dotenv
from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager


def create_service():
    load_dotenv()
    from src.storage.decision_review_store import configured_decision_store
    return ApplicationService(session_store=SessionManager(), decision_store=configured_decision_store())


def display_answer(answer):
    result = answer.to_dict()
    print(result["answer"])
    evidence = result["metadata"]["evidence"]
    print(f"Evidence status: {evidence['status']}")
    if not evidence["sources"]:
        print("Source capture date and age: unknown")
    for source in evidence["sources"]:
        date = source["captured_at"] or "unknown"
        age = f"{source['age_days']} days" if source["age_days"] is not None else "unknown"
        print(f"Source: {source['document_id']} | captured: {date} | age: {age}")
    print(result["limitations"])


def main():
    parser = argparse.ArgumentParser(description="Mushir evidence-based finance assistant")
    parser.add_argument("--query")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--acknowledge-disclaimer", action="store_true",
                        help="Acknowledge that answers are informational and not binding rulings")
    args = parser.parse_args()
    if not args.query and not args.interactive:
        parser.error("--query is required unless --interactive is used")
    service = create_service()
    acknowledged = args.acknowledge_disclaimer
    if args.interactive and not acknowledged and os.getenv("REQUIRE_DISCLAIMER_ACK", "false").lower() == "true":
        print("Answers are informational; consult a qualified Sharia scholar for a binding ruling.")
        acknowledged = input("Type 'I acknowledge' to continue: ").strip().lower() == "i acknowledge"
        if not acknowledged:
            return
    service.k = args.k
    session_id = str(uuid.uuid4())
    query = args.query
    while True:
        if query is None:
            query = input("Question (exit to quit): ").strip()
        if query.lower() in {"exit", "quit"}:
            return
        display_answer(service.answer(query, session_id=session_id, request_id=str(uuid.uuid4()),
                                      disclaimer_acknowledged=acknowledged))
        if not args.interactive:
            return
        query = None


if __name__ == "__main__":
    main()
