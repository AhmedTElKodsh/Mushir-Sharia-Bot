"""Lightweight helpers for bilingual parity checks."""


def ruling_matches(ruling_a: str, ruling_b: str) -> bool:
    return ruling_a == ruling_b


def confidence_gap(conf_a: float, conf_b: float) -> float:
    return abs(conf_a - conf_b)
