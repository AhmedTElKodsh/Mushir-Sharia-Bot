from typing import List, Dict
from src.models.document import AAOIFIDocument
from src.config.logging_config import setup_logging

logger = setup_logging()

MIN_CONTENT_LENGTH = 500
AAOIFI_MARKERS = ["AAOIFI", "FAS", "Financial Accounting Standard", "SS", "Shariah Standard"]

def validate_document(doc: AAOIFIDocument) -> Dict[str, any]:
    """Validate acquired document quality."""
    issues = []
    if not doc.content or len(doc.content) < MIN_CONTENT_LENGTH:
        issues.append(f"Content too short: {len(doc.content) if doc.content else 0} chars (min {MIN_CONTENT_LENGTH})")
    markers_found = [m for m in AAOIFI_MARKERS if m.lower() in doc.content.lower()]
    if not markers_found:
        issues.append("No AAOIFI standard markers found in content")
    if not doc.title or doc.title == "Unknown":
        issues.append("Missing or unknown title")
    return {
        "document_id": doc.document_id,
        "valid": len(issues) == 0,
        "issues": issues,
        "content_length": len(doc.content) if doc.content else 0,
        "markers_found": markers_found if 'markers_found' in locals() else [],
    }

def validate_all_documents(store) -> List[Dict[str, any]]:
    """Validate all documents in store."""
    docs = store.get_all_documents()
    results = []
    for doc in docs:
        result = validate_document(doc)
        results.append(result)
        if not result["valid"]:
            logger.warning(f"Validation failed for {doc.document_id}: {result['issues']}")
    return results

def generate_validation_report(results: List[Dict[str, any]]) -> str:
    """Generate validation report."""
    total = len(results)
    valid = sum(1 for r in results if r["valid"])
    report = [f"\n=== Validation Report ===", f"Total documents: {total}", f"Valid: {valid}", f"Issues: {total - valid}"]
    for r in results:
        if not r["valid"]:
            report.append(f"  - {r['document_id']}: {', '.join(r['issues'])}")
    return "\n".join(report)
