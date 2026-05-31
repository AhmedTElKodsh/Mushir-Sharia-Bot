from pathlib import Path

import yaml


MATRIX_PATH = Path(__file__).resolve().parent / "fixtures" / "hard_case_routing_matrix.yaml"


def routing_case(matrix_id: str) -> dict:
    cases = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8")) or []
    for case in cases:
        if case.get("matrix_id") == matrix_id:
            return case
    raise AssertionError(f"routing matrix case not found: {matrix_id}")
