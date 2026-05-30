"""
CalibrationBucket: accumulates (predicted_confidence, is_correct) pairs
for Expected Calibration Error (ECE) calculation across the full gold suite.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from helpers.ece import calculate_ece

REPORTS_DIR = Path(__file__).parent.parent / "reports"


@dataclass
class CalibrationEntry:
    case_id: str
    predicted_confidence: float
    actual_correct: bool   # True if ruling matches expected_ruling


class CalibrationBucket:
    def __init__(self) -> None:
        self.entries: list[CalibrationEntry] = []

    def record(
        self,
        case_id: str,
        predicted_confidence: float,
        actual_correct: bool,
    ) -> None:
        self.entries.append(
            CalibrationEntry(case_id, predicted_confidence, actual_correct)
        )

    def compute_ece(self) -> float:
        if not self.entries:
            return 0.0
        confidences = [e.predicted_confidence for e in self.entries]
        actuals = [e.actual_correct for e in self.entries]
        return calculate_ece(confidences, actuals, assert_threshold=1.0)

    def write_report(self) -> None:
        REPORTS_DIR.mkdir(exist_ok=True)
        ece = self.compute_ece()
        report = {
            "timestamp": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            "total_cases": len(self.entries),
            "ece": ece,
            "ece_pass": ece <= 0.10,
            "entries": [
                {
                    "case_id": e.case_id,
                    "confidence": e.predicted_confidence,
                    "correct": e.actual_correct,
                }
                for e in self.entries
            ],
        }
        report_path = REPORTS_DIR / f"ece_report_{report['timestamp']}.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n[ECE] Report written: {report_path}")
        print(f"   ECE = {ece:.4f} ({'PASS' if ece <= 0.10 else 'FAIL'})")
