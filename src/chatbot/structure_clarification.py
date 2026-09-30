"""Bounded structural questions; user replies never authorize a ruling."""
from datetime import UTC, datetime, timedelta
import re

from src.chatbot.clarification_engine import ClarificationEngine
from src.models.ruling import AnswerContract, ComplianceStatus


SLOTS = ("resale_arranger", "underlying_sukuk_contract")
PENDING_TTL = timedelta(minutes=30)


def _live_pending(pending):
    """Drop malformed or stale stored state instead of failing every later turn."""
    if not isinstance(pending, dict) or pending.get("slot") not in SLOTS:
        return None
    if pending.get("language") not in {"ar", "en"} or not isinstance(pending.get("asked_count"), int):
        return None
    try:
        created = datetime.fromisoformat(pending["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return pending if datetime.now(UTC) - created <= PENDING_TTL else None
    except (KeyError, TypeError, ValueError):
        return pending  # States stored before expiry existed stay usable.


def structure_slot(normalized):
    """Identify an explicitly requested assessment with a material variant."""
    text = normalized.lower()
    judgment = ClarificationEngine._is_judgment_query(text)
    slot = None
    if judgment and re.search(r"tawarruq|تورق", text):
        slot = "resale_arranger"
    elif judgment and re.search(r"sukuk|صكوك", text) and re.search(r"fixed|ثابت", text):
        slot = "underlying_sukuk_contract"
    return slot


def clarify_structure(query, normalized, language, pending=None):
    """Return (answer, pending state), or (None, None) for an independent query."""
    text = normalized.lower()
    slot = structure_slot(normalized)
    pending = _live_pending(pending)
    independent = bool(re.search(r"^(what\b|how\b|why\b|is\b|are\b|can\b|does\b|define\b|tell me about\b|هل\b|ما |اشرح|عرف |explain\b)", text))
    if pending and slot != pending["slot"] and (slot or independent):
        pending = None
    if not slot and not pending:
        return None, None
    current = dict(pending or {"slot": slot, "original_query": query, "asked_count": 0, "language": language,
                                    "created_at": datetime.now(UTC).isoformat()})
    arabic = current["language"] == "ar"
    reply = query if pending else None
    if pending:
        current["reply"] = reply
    unanswered = bool(re.fullmatch(r"(?:please )?continue[.!]?|تابع[.!]?|اكمل[.!]?", text.strip()))
    terminal = bool(pending and ((not unanswered and slot is None) or current["asked_count"] >= 2))
    if terminal:
        current["reply"] = reply
        documents = ["transaction agreement and sale arrangements" if current["slot"] == "resale_arranger" else "Sukuk terms and underlying contract", "applicable approved scholar rule and supporting evidence"]
        answer = "أحتاج إلى مستندات المعاملة ومراجعة القاعدة المعتمدة قبل تقييمها؛ إجابتك وحدها لا تكفي لإصدار حكم." if arabic else "I need the transaction documents and an applicable approved rule before assessing this arrangement; your reply alone does not establish a ruling."
        return AnswerContract(answer=answer, status=ComplianceStatus.INSUFFICIENT_DATA,
            metadata={"structure_clarification": current, "needed_documents_or_reviews": documents,
                      "requires_scholar_review": True, "response_language": current["language"]}), None
    current["asked_count"] += 1
    question = ({"resale_arranger": "من يرتب إعادة بيع السلعة للمشتري النهائي؟", "underlying_sukuk_contract": "ما العقد الذي تقوم عليه توزيعات الصكوك؟"} if arabic else
                {"resale_arranger": "Who arranges the onward sale to the final buyer?", "underlying_sukuk_contract": "What underlying contract generates the Sukuk distributions?"})[current["slot"]]
    return AnswerContract(answer=question, clarification_question=question,
        status=ComplianceStatus.CLARIFICATION_NEEDED,
        metadata={"structure_clarification": dict(current), "response_language": current["language"]}), current
