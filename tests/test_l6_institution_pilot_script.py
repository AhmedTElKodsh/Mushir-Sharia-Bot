import json
import zipfile
from datetime import date

from scripts.run_l6_institution_pilot import (
    _access_block_reason,
    _has_useful_evidence_text,
    _load_banksegypt_official_sites,
    run_fixture_pilot,
    run_full_scrape_gate,
    write_manifest,
)
from src.governance import CorpusPilotGate, CorpusPilotPlan, WorkbookRegistryLoader


def test_fixture_pilot_loads_registry_writes_artifacts_and_passes_gate(tmp_path):
    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {
            "01_CBE_Banks": [
                ["Institution Name", "Website"],
                ["Faisal Islamic Bank of Egypt", "https://www.faisalbank.com.eg/"],
            ],
            "02_Capital_Market": [
                ["Institution Name"],
                ["Pilot Brokerage"],
            ],
            "03_Insurance": [
                ["Company Name"],
                ["Delta Insurance"],
            ],
            "04_NonBank_Financial": [
                ["Company Name", "Sector"],
                ["Hard Case Finance", "consumer finance"],
            ],
        },
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)

    registry = run_fixture_pilot(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        pilot_id="test-pilot",
        run_date=date(2026, 5, 20),
    )
    manifest_path = write_manifest(
        baseline_registry=baseline,
        pilot_registry=registry,
        artifact_root=artifact_root,
        pilot_id="test-pilot",
        workbook_path=workbook,
        run_date=date(2026, 5, 20),
    )
    plan = CorpusPilotPlan(
        pilot_id="test-pilot",
        institution_ids=[record.institution_id for record in registry.records()],
        includes_no_details_case=True,
    )
    report = CorpusPilotGate().evaluate(plan, registry)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report.passed is True
    assert manifest["mode"] == "fixture_pilot_no_live_crawl"
    assert manifest["baseline_record_count"] == 4
    assert manifest["artifact_count"] == 2
    assert manifest["operation_count"] == 2
    assert (artifact_root / "review" / "test-pilot" / "machine_mapping_candidates.csv").exists()
    assert (artifact_root / "review" / "test-pilot" / "accepted_gold_cases.fixture.csv").exists()


def test_full_scrape_gate_blocks_without_real_scholar_review_before_discovery(tmp_path, capsys):
    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {
            "01_CBE_Banks": [["Institution Name"], ["Faisal Islamic Bank of Egypt"]],
            "03_Insurance": [["Company Name"], ["Delta Insurance"]],
            "04_NonBank_Financial": [["Company Name"], ["Hard Case Finance"]],
        },
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)

    exit_code = run_full_scrape_gate(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 20),
        review_file=None,
        bank_discovery_targets=[{"record": baseline.records()[0], "official_website": "https://example.com"}],
    )

    manifest = json.loads(
        (artifact_root / "full_scrape_gate" / "2026-05-20" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 2
    assert manifest["allowed_to_scrape"] is False
    assert manifest["bank_discovery_target_count"] == 1
    assert manifest["review_status"]["review_workflow_ready"] is False
    assert "full scrape requires a non-fixture accepted scholar-review file" in manifest["blocked_reasons"]
    assert "Allowed to scrape: False" in capsys.readouterr().out


def test_full_scrape_gate_allows_injected_targets_after_real_scholar_review(tmp_path, capsys):
    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    review_file = tmp_path / "reviews.csv"
    _write_minimal_xlsx(
        workbook,
        {
            "01_CBE_Banks": [["Institution Name"], ["Faisal Islamic Bank of Egypt"]],
            "03_Insurance": [["Company Name"], ["Delta Insurance"]],
            "04_NonBank_Financial": [["Company Name"], ["Hard Case Finance"]],
        },
    )
    _write_review_csv(review_file)
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)

    exit_code = run_full_scrape_gate(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 20),
        review_file=review_file,
        bank_discovery_targets=[{"record": baseline.records()[0], "official_website": "https://example.com"}],
    )

    manifest = json.loads(
        (artifact_root / "full_scrape_gate" / "2026-05-20" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert manifest["allowed_to_scrape"] is True
    assert manifest["bank_discovery_target_count"] == 1
    assert manifest["review_status"]["has_real_accepted_review"] is True
    assert "Allowed to scrape: True" in capsys.readouterr().out


def test_full_scrape_gate_blocks_when_no_targets_can_be_discovered(tmp_path):
    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {
            "03_Insurance": [["Company Name"], ["Delta Insurance"]],
            "04_NonBank_Financial": [["Company Name"], ["Hard Case Finance"]],
        },
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)

    exit_code = run_full_scrape_gate(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 20),
        review_file=None,
    )

    manifest = json.loads(
        (artifact_root / "full_scrape_gate" / "2026-05-20" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 2
    assert manifest["allowed_to_scrape"] is False
    assert any(
        "no official institution website URLs" in reason
        for reason in manifest["blocked_reasons"]
    )


def test_access_block_reason_detects_security_rejection_body():
    body = (
        "<html><head><title>Request Rejected</title></head>"
        "<body>The requested URL was rejected.<br/>Your support ID is abc</body></html>"
    )

    assert _access_block_reason(body) == "access blocked by upstream security page"


def test_bank_directory_discovery_respects_robots_before_reading(monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    calls = []

    def blocked_robots(url, timeout_seconds):
        return {"allowed": False, "reason": "robots.txt disallows URL"}

    def forbidden_read(url, timeout_seconds):
        calls.append(url)
        raise AssertionError("directory should not be read when robots disallows it")

    monkeypatch.setattr(pilot, "_check_robots", blocked_robots)
    monkeypatch.setattr(pilot, "_read_text_url", forbidden_read)

    assert _load_banksegypt_official_sites(timeout_seconds=1.0) == {}
    assert calls == []


def test_useful_evidence_gate_rejects_empty_or_tiny_text():
    assert _has_useful_evidence_text("") is False
    assert _has_useful_evidence_text("Arab African Internationl Bank") is False
    assert _has_useful_evidence_text("Bank product terms " * 40) is True


def _write_minimal_xlsx(path, sheets):
    workbook_sheets = "\n".join(
        f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheets, start=1)
    )
    relationships = "\n".join(
        '<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet{index}.xml"/>'.format(index=index)
        for index, _ in enumerate(sheets, start=1)
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            "</Types>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{workbook_sheets}</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{relationships}</Relationships>",
        )
        for index, rows in enumerate(sheets.values(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))


def _sheet_xml(rows):
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            column = chr(ord("A") + column_index)
            cells.append(
                f'<c r="{column}{row_index}" t="inlineStr"><is><t>{value}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )


def _write_review_csv(path):
    path.write_text(
        "\n".join(
            [
                "review_id,mapping_id,reviewer,decision,aaoifi_references,rationale,uncertainty_flags,correction_type,accepted_gold_case",
                "review-real-1,map-op-real,scholar-1,scholar_accepted,FAS-28,Accepted from reviewed pilot evidence,,,true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
