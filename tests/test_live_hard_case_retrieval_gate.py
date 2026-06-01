from pathlib import Path

import pytest

from tests.routing_matrix import routing_case


pytestmark = pytest.mark.service


def test_live_hard_case_gate_uses_live_pipeline_and_candidate_standard_filter(tmp_path):
    from scripts.run_live_hard_case_retrieval_gate import run_live_hard_case_retrieval_gate
    matrix = routing_case("HCRM-ISTISNA-PENALTY-CONTRACTOR")
    query = matrix["queries"][0]
    standards = matrix["candidate_standards"]
    standards_yaml = str(standards).replace("'", '"')

    cases = tmp_path / "cases.yaml"
    cases.write_text(
        f"""
- case_id: t1
  query: "{query}"
  expected_behavior: "retrieval"
  expected_source_family: "sharia_standard"
  expected_candidate_standards: {standards_yaml}
""".strip(),
        encoding="utf-8",
    )

    class FakePipeline:
        def retrieve(self, query, k=8, threshold=0.0, filters=None, mode="dense"):
            assert filters == {"source_family": "sharia_standard", "standard_number": standards}
            return [
                {
                    "chunk_id": "right-ss-11",
                    "content": "Istisna penalty evidence",
                    "metadata": {
                        "source_family": "sharia_standard",
                        "standard_number": "SS-11",
                        "metadata_status": "cataloged",
                    },
                    "similarity": 0.93,
                },
                {
                    "chunk_id": "right-ss-05",
                    "content": "Penalty condition evidence",
                    "metadata": {
                        "source_family": "sharia_standard",
                        "standard_number": "SS-05",
                        "metadata_status": "cataloged",
                    },
                    "similarity": 0.91,
                },
            ]

    report = run_live_hard_case_retrieval_gate(
        cases_path=cases,
        output=tmp_path / "report.json",
        pipeline_factory=FakePipeline,
    )

    if not report["passed"]:
        print("FAILURES:", report["results"][0]["failures"])
    assert report["passed"] is True
    assert report["live_vector_index_used"] is True
    assert report["live_llm_used"] is False
    assert report["application_answer_used"] is True
    result = report["results"][0]
    assert result["answer_status"] == "insufficient_data"
    assert result["application_metadata"]["standards_route"]["candidate_standards"] == standards
    assert set(result["retrieved_standards"]) == set(standards)
    assert set(result["matched_standards"]) == set(standards)
    assert result["candidate_standard_filter"]["required"] == standards
    assert Path(tmp_path / "report.json").exists()


def test_live_hard_case_gate_fails_when_only_wrong_sharia_standard_is_retrieved(tmp_path):
    from scripts.run_live_hard_case_retrieval_gate import run_live_hard_case_retrieval_gate
    matrix = routing_case("HCRM-ISTISNA-PENALTY-CONTRACTOR")
    query = matrix["queries"][0]
    standards = matrix["candidate_standards"]
    standards_yaml = str(standards).replace("'", '"')

    cases = tmp_path / "cases.yaml"
    cases.write_text(
        f"""
- case_id: t1
  query: "{query}"
  expected_behavior: "retrieval"
  expected_source_family: "sharia_standard"
  expected_candidate_standards: {standards_yaml}
""".strip(),
        encoding="utf-8",
    )

    class FakePipeline:
        def retrieve(self, query, k=8, threshold=0.0, filters=None, mode="dense"):
            return [
                {
                    "chunk_id": "wrong-ss-03",
                    "content": "Debt penalty evidence",
                    "metadata": {
                        "source_family": "sharia_standard",
                        "standard_number": "SS-03",
                        "metadata_status": "cataloged",
                    },
                    "similarity": 0.95,
                },
            ]

    report = run_live_hard_case_retrieval_gate(
        cases_path=cases,
        output=tmp_path / "report.json",
        pipeline_factory=FakePipeline,
    )

    assert report["passed"] is False
    assert "missing expected standards: SS-05, SS-11" in report["results"][0]["failures"]
    assert report["results"][0]["matched_standards"] == []
    assert report["results"][0]["answer_status"] == "insufficient_data"


def test_live_hard_case_gate_writes_failure_report_when_pipeline_initialization_fails(tmp_path):
    from scripts.run_live_hard_case_retrieval_gate import run_live_hard_case_retrieval_gate

    cases = tmp_path / "cases.yaml"
    cases.write_text(
        """
- case_id: t1
  query: "Is a contractor delay penalty valid in istisna?"
  expected_behavior: "retrieval"
  expected_source_family: "sharia_standard"
  expected_candidate_standards: ["SS-05", "SS-11"]
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"

    def failing_pipeline_factory():
        raise RuntimeError("Qdrant unavailable")

    report = run_live_hard_case_retrieval_gate(
        cases_path=cases,
        output=output,
        pipeline_factory=failing_pipeline_factory,
    )

    assert report["passed"] is False
    assert report["application_answer_used"] is False
    assert report["infrastructure_failure"]["stage"] == "pipeline_initialization"
    assert output.exists()
