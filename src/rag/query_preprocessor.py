"""Query preprocessing and normalization."""
import re
from functools import lru_cache
from typing import FrozenSet

# Arabic transliteration normalization map
_TRANSLITERATION_MAP = {
    r'\bmurabah\b': 'murabahah',
    r'\bmurabahat\b': 'murabahah',
    r'\bmurabaha\b': 'murabahah',
    r'\bmudaraba\b': 'mudarabah',
    r'\bmudharaba\b': 'mudarabah',
    r'\bmudarabat\b': 'mudarabah',
    r'\bijara\b': 'ijarah',
    r'\bijarat\b': 'ijarah',
    r'\bsukuks\b': 'sukuk',
    r'\bzakah\b': 'zakat',
    r'\bghrar\b': 'gharar',
    r'\bribah\b': 'riba',
    r'\bmusharakah\b': 'musharakah',
    r'\bmusharaka\b': 'musharakah',
    r'\bwakala\b': 'wakalah',
    r'\bqard hasan\b': 'qard al-hasan',
}

# Precompile regex patterns for performance
_TRANSLITERATION_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in _TRANSLITERATION_MAP.items()
]

# Arabic diacritic (tashkeel) + tatweel stripping pattern
_ARABIC_DIACRITICS = re.compile(r'[\u064b-\u065f\u0670\u0640]')
# Hamza normalization: various alef forms → plain alef
_HAMZA_NORM = re.compile(r'[\u0622\u0623\u0625\u0671]')  # آ أ إ ٱ → ا
# Alif maqsura (ى) → alif (ا)
_ALIF_MAQSURA = re.compile(r'\u0649')  # ى → ا
# Teh marbuta (ة) → ha (ه) for search normalization
_TEH_MARBUTA = re.compile(r'\u0629')  # ة → ه

# Domain query expansions
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


class QueryPreprocessor:
    """Handles query normalization, expansion, and language detection."""

    @staticmethod
    def normalize(query: str) -> str:
        """Normalize user input for better retrieval:
        1. Strip Arabic diacritics (tashkeel) that cause embedding mismatches.
        2. Normalize Arabic hamza variants to plain alef.
        3. Normalize alif maqsura (ى) to plain alif (ا).
        4. Normalize teh marbuta (ة) to ha (ه) for search robustness.
        5. Map common English transliteration misspellings to canonical forms.
        """
        if not query:
            return ""
        
        # Arabic normalization
        result = _ARABIC_DIACRITICS.sub('', query)
        result = _HAMZA_NORM.sub('\u0627', result)  # → ا
        result = _ALIF_MAQSURA.sub('\u0627', result)  # ى → ا
        result = _TEH_MARBUTA.sub('\u0647', result)  # ة → ه
        
        # English transliteration normalization (case-insensitive)
        for pattern, replacement in _TRANSLITERATION_PATTERNS:
            result = pattern.sub(replacement, result)
        
        return result

    @staticmethod
    @lru_cache(maxsize=1000)
    def expand_terms(query: str) -> FrozenSet[str]:
        """Extract and expand domain-specific terms from query.
        
        Cached to avoid recomputing for repeated queries.
        """
        lowered = query.lower()
        terms = {
            token.strip('.,;:?!()[]{}"\'\u061f\u060c')
            for token in lowered.split()
        }
        
        for trigger, expansions in DOMAIN_QUERY_EXPANSIONS.items():
            # Token-level matching prevents false-positives like "lease" inside "please"
            if any(token == trigger or token.startswith(trigger + "/") for token in terms):
                terms.update(term.lower() for term in expansions)
        
        return frozenset(term for term in terms if len(term) >= 3)

    @staticmethod
    def detect_language(query: str) -> str:
        """Detect query language using character ratio (>50% Arabic = ar).

        Ratio-based approach avoids false positives from code-mixed queries
        like 'What is مرابحة?' which contain only a single Arabic word.
        """
        if not query:
            return "en"
        arabic_chars = sum(1 for c in query if '\u0600' <= c <= '\u06ff')
        ratio = arabic_chars / len(query)
        return "ar" if ratio > 0.50 else "en"

    @staticmethod
    def contains_arabic(text: str) -> bool:
        """Check if text contains any Arabic Unicode characters."""
        return any('\u0600' <= char <= '\u06ff' for char in text)

    @staticmethod
    def preferred_language(query: str) -> str:
        """Get preferred language for retrieval."""
        return "ar" if QueryPreprocessor.contains_arabic(query) else "en"

    @staticmethod
    def expand_for_embedding(query: str) -> str:
        """Build an embedding-oriented query that merges Arabic with English synonyms.

        Supports bidirectional expansion:
        - Arabic queries: append English synonyms → "ما هي المرابحة؟" → "ما هي المرابحة؟ murabaha sale"
        - English queries: append Arabic synonyms → "What is murabaha?" → "What is murabaha? مرابحة المرابحة"
        """
        expanded = QueryPreprocessor.expand_terms(query)
        has_arabic = QueryPreprocessor.contains_arabic(query)
        english_terms = [t for t in expanded if not QueryPreprocessor.contains_arabic(t)]
        arabic_terms = [t for t in expanded if QueryPreprocessor.contains_arabic(t)]

        # Arabic query → find English expansions
        if has_arabic and not english_terms:
            for term in expanded:
                for trigger, expansions in DOMAIN_QUERY_EXPANSIONS.items():
                    if trigger.lower() == term.lower() or term.lower() in trigger.lower():
                        english_terms = [t for t in expansions if not QueryPreprocessor.contains_arabic(t)]
                        if english_terms:
                            break
                if english_terms:
                    break

        # English query → find Arabic expansions for richer multilingual embedding
        if not has_arabic and not arabic_terms:
            for trigger, expansions in DOMAIN_QUERY_EXPANSIONS.items():
                if trigger in query.lower() and not QueryPreprocessor.contains_arabic(trigger):
                    arabic_terms = [t for t in expansions if QueryPreprocessor.contains_arabic(t)]
                    if arabic_terms:
                        break

        parts = [query]
        if english_terms:
            parts.append(' '.join(english_terms))
        if arabic_terms:
            parts.append(' '.join(arabic_terms))
        return ' '.join(parts) if len(parts) > 1 else query
