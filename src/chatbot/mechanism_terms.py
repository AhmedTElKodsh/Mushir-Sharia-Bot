"""Identify generic plan wording without promoting ancillary terms to contracts.

Explicit contract names remain retrieval topics only. Neither function supplies
evidenced mechanisms to the approved evaluator.
"""
import re

from src.rag.query_preprocessor import QueryPreprocessor


_GENERIC = re.compile(
    r"\b(?:instal+ments?|bnpl|financ(?:e|ed|ing)|ta2seet|taqseet|2osoot|aqsat)\b"
    r"|buy now pay later|deferred (?:sale|payment)|pay in (?:\d+|three|four)"
    r"|تقسيط|اقساط|تمويل", re.I)
_NAMED_TOPIC = re.compile(
    r"\b(?:murabahah?|ijarah?|istisna(?:['’]a)?|muqawala|musharakah?|mudarabah?|mudharabah?"
    r"|wakalah?|kafalah?|qard|loan|lease|salam|tawarruq|sukuk)\b"
    r"|(?<!\w)[وبفلك]?(?:ال)?(?:مرابحه|اجاره|ايجار|استصناع|مقاوله|مقاولات|مشاركه|مضاربه|وكاله|كفاله|قرض|سلم|تورق|صكوك)(?!\w)", re.I)
_NEGATED = re.compile(r"\b(?:not|without|isn't|isnt|aren't|never)\b|(?<!\w)(?:ليس|ليست|مش|بدون|غير|لا)(?!\w)", re.I)


def _topic_matches(text):
    for match in _NAMED_TOPIC.finditer(text):
        # Negated labels cannot supply the family. A contrast starts a new clause.
        prefix = re.split(r"[.!?؟;,\n]|\b(?:but|however)\b|لكن|بل|انما", text[:match.start()], flags=re.I)[-1]
        yield match, not _NEGATED.search(prefix)


def generic_mechanism_unknown(query: str) -> bool:
    text = QueryPreprocessor.normalize(query or "")
    return bool(_GENERIC.search(text) and not any(affirmed for _, affirmed in _topic_matches(text)))


def mechanism_routing_text(query: str) -> str:
    """Keep raw user evidence elsewhere; remove negated plan names for routing."""
    text = QueryPreprocessor.normalize(query or "")
    if _GENERIC.search(text):
        for match, affirmed in reversed(list(_topic_matches(text))):
            if not affirmed:
                text = text[:match.start()] + " " * (match.end() - match.start()) + text[match.end():]
    return text
