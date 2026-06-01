import json
import os

import pytest

from src.institution_db.schema import (
    ComplianceCrossReferencer,
    FinancialOperation,
    InstitutionScraper,
)


pytestmark = pytest.mark.unit


def test_institution_scraper_reads_latest_chunk_ready_spans(tmp_path):
    first = tmp_path / "metadata" / "old"
    latest = tmp_path / "full_scrape" / "2026-06-01"
    first.mkdir(parents=True)
    latest.mkdir(parents=True)
    (first / "chunk_ready_spans.jsonl").write_text(
        json.dumps(
            {
                "operation_id": "op-old",
                "institution_id": "old-bank",
                "institution_name": "Old Bank",
                "operation_name": "Old Murabaha",
                "candidate_standards": ["SS-08"],
                "mapping_status": "machine_proposed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    latest_file = latest / "chunk_ready_spans.jsonl"
    latest_file.write_text(
        json.dumps(
            {
                "operation_id": "op-faisal-car-murabaha",
                "institution_id": "cbe-bank-faisal-islamic-bank-of-egypt",
                "institution_name": "Faisal Islamic Bank of Egypt",
                "operation_name": "New Car Murabaha",
                "candidate_standards": ["FAS-28", "SS-08"],
                "mapping_status": "machine_proposed",
                "sector": "bank",
                "regulator": "cbe",
                "artifact_url": "https://www.faisalbank.com.eg/car-murabaha",
                "evidence_snippet": "The bank purchases the asset before deferred sale.",
                "confidence": 0.91,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    os.utime(latest_file, (first.stat().st_mtime + 10, first.stat().st_mtime + 10))

    operations = InstitutionScraper(tmp_path).scrape_operations()

    assert len(operations) == 1
    assert operations[0].operation_id == "op-faisal-car-murabaha"
    assert operations[0].institution_name == "Faisal Islamic Bank of Egypt"
    assert operations[0].operation_title == "New Car Murabaha"
    assert operations[0].mapped_aaoifi_contract == "FAS-28|SS-08"
    assert operations[0].compliance_status == "PENDING_SCHOLAR_REVIEW"
    assert operations[0].source_url == "https://www.faisalbank.com.eg/car-murabaha"
    assert operations[0].confidence == 0.91


def test_institution_scraper_returns_empty_when_no_evidence_exports(tmp_path):
    assert InstitutionScraper(tmp_path).scrape_operations() == []


def test_compliance_cross_referencer_mutates_status_for_mapped_operation(tmp_path):
    operation = InstitutionScraper(tmp_path).scrape_operations()
    assert operation == []

    mapped = FinancialOperation(
        operation_id="op-1",
        institution_name="Example Bank",
        operation_title="Murabaha",
        mapped_aaoifi_contract="SS-08",
    )
    reviewed = FinancialOperation(
        operation_id="op-2",
        institution_name="Example Bank",
        operation_title="Ijarah",
        mapped_aaoifi_contract="SS-09",
        human_scholar_review="scholar_accepted",
    )

    assert ComplianceCrossReferencer().assess_compliance(mapped).compliance_status == (
        "PENDING_SCHOLAR_REVIEW"
    )
    assert ComplianceCrossReferencer().assess_compliance(reviewed).compliance_status == (
        "SCHOLAR_REVIEWED"
    )
