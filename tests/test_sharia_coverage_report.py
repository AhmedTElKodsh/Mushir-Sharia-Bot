import pytest

from scripts.report_sharia_corpus_coverage import build_sharia_coverage_matrix, sharia_coverage_report


pytestmark = pytest.mark.service


def test_sharia_coverage_report_marks_currentness_and_supersession():
    records = [
        {
            "source_id": "ss-01-en-old",
            "source_family": "sharia_standard",
            "standard_number": "SS-01",
            "language": "en",
            "currentness": "superseded",
            "review_status": "machine_checked",
            "superseded_by": ["ss-01-en-current"],
        },
        {
            "source_id": "ss-01-ar-current",
            "source_family": "sharia_standard",
            "standard_number": "SS-01",
            "language": "ar",
            "currentness": "current",
            "review_status": "machine_checked",
        },
    ]

    report = sharia_coverage_report(records, target_sharia_standard_count=1)
    matrix = build_sharia_coverage_matrix(records, target_sharia_standard_count=1)

    assert report["currentness_counts"] == {"current": 1, "superseded": 1}
    assert report["superseded_sharia_standards"] == ["SS-01"]
    assert report["supersession_map"] == {"SS-01": ["ss-01-en-current"]}
    assert report["release_gate"] == "fail"
    assert matrix[0]["source_coverage_gate"] == "fail"
    assert "Currentness/supersession state blocks answer admissibility." in matrix[0]["gate_reasons"]


def test_sharia_coverage_report_surfaces_blocked_acquisition_manifest():
    records = [
        {
            "source_id": "ss-01-en",
            "source_family": "sharia_standard",
            "standard_number": "SS-01",
            "language": "en",
            "currentness": "current",
        }
    ]
    manifest = {
        "blocked_sources": [
            {
                "standard_number": "SS-02",
                "status": "missing_full_official_or_licensed_text",
                "required_next_action": "Acquire full official/licensed AAOIFI source text before answer admission.",
            }
        ]
    }

    report = sharia_coverage_report(records, target_sharia_standard_count=2, acquisition_manifest=manifest)
    matrix = build_sharia_coverage_matrix(records, target_sharia_standard_count=2, acquisition_manifest=manifest)

    assert report["blocked_source_count"] == 1
    assert report["blocked_source_standards"] == ["SS-02"]
    assert report["blocked_source_details"] == [
        {
            "standard_number": "SS-02",
            "status": "missing_full_official_or_licensed_text",
            "required_next_action": "Acquire full official/licensed AAOIFI source text before answer admission.",
        }
    ]
    assert matrix[1]["acquisition_status"] == "missing_full_official_or_licensed_text"
    assert matrix[1]["required_next_action"] == (
        "Acquire full official/licensed AAOIFI source text before answer admission."
    )
    assert "Source acquisition is blocked" in " ".join(matrix[1]["gate_reasons"])
