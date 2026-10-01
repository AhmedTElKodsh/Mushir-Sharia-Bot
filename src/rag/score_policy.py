"""Numeric retrieval gates. Scores measure retrieval relevance, never verdict accuracy."""
import math
from numbers import Real


def finite_score(value):
    """Return a genuine finite numeric score; missing/coerced values are not evidence."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def validated_threshold(value):
    number = finite_score(value)
    if number is None or not 0.0 <= number <= 1.0:
        raise ValueError("Retrieval threshold must be finite and between zero and one")
    return number


def meets_threshold(value, threshold):
    number = finite_score(value)
    return number is not None and number >= threshold
