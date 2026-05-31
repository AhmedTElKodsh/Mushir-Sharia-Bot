"""
Expected Calibration Error (ECE) calculation.

ECE measures the difference between predicted confidence and actual accuracy.
A well-calibrated model that says "I'm 80% confident" should be correct 80% of the time.

For Sharia fatwa systems, ECE > 0.10 means the model's confidence signals
cannot be trusted for human review routing decisions — a critical operational risk.

Bucket strategy: 10 equal-width bins [0.0, 0.1), [0.1, 0.2), ..., [0.9, 1.0]
ECE = Σ (|bin| / N) × |avg_confidence(bin) - avg_accuracy(bin)|
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ECEBucket:
    bucket_id: int          # 0 = [0.0, 0.1), 9 = [0.9, 1.0]
    confidences: list[float]
    actuals: list[bool]     # True = correct prediction

    @property
    def avg_confidence(self) -> float:
        if not self.confidences:
            return 0.0
        return sum(self.confidences) / len(self.confidences)

    @property
    def avg_accuracy(self) -> float:
        if not self.actuals:
            return 0.0
        return sum(1 for a in self.actuals if a) / len(self.actuals)

    @property
    def calibration_error(self) -> float:
        return abs(self.avg_confidence - self.avg_accuracy)

    @property
    def count(self) -> int:
        return len(self.confidences)


def calculate_ece(
    confidences: list[float],
    actuals: list[bool],
    n_bins: int = 10,
    assert_threshold: float = 0.10,
) -> float:
    """
    Calculate Expected Calibration Error.

    Args:
        confidences: List of predicted confidence scores [0.0, 1.0]
        actuals: List of booleans (True = model was correct)
        n_bins: Number of equal-width buckets (default 10)
        assert_threshold: If > 0, asserts ECE <= threshold after calculation

    Returns:
        ECE as float [0.0, 1.0]

    Raises:
        AssertionError: if ECE > assert_threshold
        ValueError: if inputs are mismatched or empty
    """
    if len(confidences) != len(actuals):
        raise ValueError(
            f"Length mismatch: {len(confidences)} confidences vs {len(actuals)} actuals"
        )
    if not confidences:
        raise ValueError("Cannot compute ECE on empty input")

    # Validate confidence range
    for i, c in enumerate(confidences):
        if not (0.0 <= c <= 1.0):
            raise ValueError(f"confidence[{i}]={c} is outside [0.0, 1.0]")

    # Initialize buckets
    buckets: list[ECEBucket] = [
        ECEBucket(bucket_id=i, confidences=[], actuals=[])
        for i in range(n_bins)
    ]

    # Assign each prediction to a bucket
    for conf, actual in zip(confidences, actuals):
        bucket_idx = min(int(conf * n_bins), n_bins - 1)  # handles conf=1.0
        buckets[bucket_idx].confidences.append(conf)
        buckets[bucket_idx].actuals.append(actual)

    total_n = len(confidences)
    ece = sum(
        (bucket.count / total_n) * bucket.calibration_error
        for bucket in buckets
        if bucket.count > 0
    )

    # Round to 4 decimal places for stable comparison
    ece = round(ece, 4)

    if assert_threshold > 0:
        assert ece <= assert_threshold, (
            f"ECE FAIL: {ece:.4f} > threshold {assert_threshold:.2f}\n"
            f"Bucket breakdown:\n"
            + "\n".join(
                f"  [{b.bucket_id/n_bins:.1f}-{(b.bucket_id+1)/n_bins:.1f}): "
                f"n={b.count}, avg_conf={b.avg_confidence:.3f}, "
                f"avg_acc={b.avg_accuracy:.3f}, err={b.calibration_error:.3f}"
                for b in buckets if b.count > 0
            )
        )

    return ece


def calculate_precision_at_k(
    retrieved_standards: list[list[str]],
    relevant_standards: list[list[str]],
    k: int = 3,
) -> float:
    """
    Precision@K for standard retrieval.
    retrieved_standards[i] = top-K standards retrieved for case i
    relevant_standards[i] = ground-truth standards for case i
    """
    if not retrieved_standards:
        raise ValueError("Empty input")

    precisions = []
    for retrieved, relevant in zip(retrieved_standards, relevant_standards):
        top_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for s in top_k if s in relevant_set)
        precisions.append(hits / k)

    return round(sum(precisions) / len(precisions), 4)
