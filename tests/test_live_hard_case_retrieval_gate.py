from pathlib import Path

import pytest


pytestmark = pytest.mark.service


def test_live_hard_case_gate_uses_live_pipeline_and_candidate_standard_filter(tmp_path):
    from scripts.run_live_hard_case_retrieval_gate import run_live_hard_case_retrieval_gate

    cases = tmp_path / "cases.yaml"
    cases.write_text(
        """
- case_id: t1
  query: "Can we impose liquidated damages if the contractor is late delivering the project?"
  expected_behavior: "retrieval"
  expected_source_family: "sharia_standard"
  expected_candidate_standards: ["SS-11"]
""".strip(),
        encoding="utf-8",
    )

    class FakePipeline:
        def retrieve(self, query, k=8, threshold=0.0, filters=None, mode="dense"):
            assert filters == {"source_family": "sharia_standard"}
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
            ]

    report = run_live_hard_case_retrieval_gate(
        cases_path=cases,
        output=tmp_path / "report.json",
        pipeline_factory=FakePipeline,
    )

    assert report["passed"] is True
    assert report["live_vector_index_used"] is True
    assert report["live_llm_used"] is False
    assert report["application_answer_used"] is True
    result = report["results"][0]
    assert result["answer_status"] == "insufficient_data"
    assert result["application_metadata"]["standards_route"]["candidate_standards"] == ["SS-11"]
    assert result["retrieved_standards"] == ["SS-03", "SS-11"]
    assert result["matched_standards"] == ["SS-11"]
    assert result["candidate_standard_filter"]["required"] == ["SS-11"]
    assert Path(tmp_path / "report.json").exists()


def test_live_hard_case_gate_fails_when_only_wrong_sharia_standard_is_retrieved(tmp_path):
    from scripts.run_live_hard_case_retrieval_gate import run_live_hard_case_retrieval_gate

    cases = tmp_path / "cases.yaml"
    cases.write_text(
        """
- case_id: t1
  query: "Can we impose an LD clause if the contractor is late delivering the project?"
  expected_behavior: "retrieval"
  expected_source_family: "sharia_standard"
  expected_candidate_standards: ["SS-11"]
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
    assert "missing expected standards: SS-11" in report["results"][0]["failures"]
    assert report["results"][0]["matched_standards"] == []
    assert report["results"][0]["answer_status"] == "insufficient_data"
