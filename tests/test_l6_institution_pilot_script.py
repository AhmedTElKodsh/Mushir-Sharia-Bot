import csv
import json
import zipfile
from datetime import date

from scripts.run_l6_institution_pilot import (
    _access_block_reason,
    _candidate_operation_links,
    _fra_detail_fields_from_html,
    _has_useful_evidence_text,
    _load_banksegypt_official_sites,
    _load_legacy_old_scraping_registry,
    run_official_registry_completion,
    run_legacy_sector_scrape,
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


def test_full_scrape_gate_allows_targets_without_human_scholar_review(tmp_path, capsys):
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
    assert exit_code == 0
    assert manifest["allowed_to_scrape"] is True
    assert manifest["bank_discovery_target_count"] == 1
    assert manifest["review_status"]["review_workflow_ready"] is False
    assert manifest["human_scholar_review_required_before_scrape"] is False
    assert manifest["blocked_reasons"] == []
    assert "Allowed to scrape: True" in capsys.readouterr().out


def test_full_scrape_gate_keeps_review_file_optional_metadata(tmp_path, capsys):
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


def test_candidate_operation_links_are_same_domain_and_prioritized():
    html = """
    <a href="/about">About</a>
    <a href="/retail/murabaha-finance">Murabaha Finance</a>
    <a href="/SMEs/islamic banking/Kenana business/Micro Financing Murabaha">Islamic SME</a>
    <a href="https://evil.example/cards">External Cards</a>
    <a href="/fees-and-tariffs">Fees</a>
    """

    links = _candidate_operation_links(
        "https://bank.example/",
        html,
        limit=2,
    )

    assert links == [
        "https://bank.example/SMEs/islamic%20banking/Kenana%20business/Micro%20Financing%20Murabaha",
        "https://bank.example/retail/murabaha-finance",
    ]


def test_useful_evidence_gate_rejects_empty_or_tiny_text():
    assert _has_useful_evidence_text("") is False
    assert _has_useful_evidence_text("Arab African Internationl Bank") is False
    assert _has_useful_evidence_text("Bank product terms " * 40) is True


def test_load_legacy_old_scraping_registry_loads_each_old_sector_workbook(tmp_path):
    old_dir = tmp_path / "old_scraping"
    old_dir.mkdir()
    _write_minimal_xlsx(
        old_dir / "Banks_old.xlsx",
        {"01_CBE_Banks": [["Name", "Name (English)"], ["Arab Investment Bank", "Arab Investment Bank"]]},
    )
    _write_minimal_xlsx(
        old_dir / "Capital_Market_old.xlsx",
        {"02_Capital_Market": [["Name"], ["Pilot Brokerage"]]},
    )
    _write_minimal_xlsx(
        old_dir / "Insurance_old.xlsx",
        {"03_Insurance": [["Name"], ["Delta Insurance"]]},
    )
    _write_minimal_xlsx(
        old_dir / "Non_Categorized_old.xlsx",
        {"04_NonBank_Financial": [["Name", "Sector"], ["Hard Case Finance", "consumer finance"]]},
    )

    registry = _load_legacy_old_scraping_registry(old_dir)

    assert len(registry.records()) == 4
    assert {record.sector.value for record in registry.records()} == {
        "bank",
        "capital_market",
        "insurance",
        "consumer_finance",
    }
    assert any(record.name_en == "Arab Investment Bank" for record in registry.records())


def test_legacy_sector_scrape_writes_gap_rows_and_review_outputs(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    old_dir = tmp_path / "old_scraping"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    seed_sites = tmp_path / "seed_sites.csv"
    old_dir.mkdir()
    _write_minimal_xlsx(
        old_dir / "Banks_old.xlsx",
        {"01_CBE_Banks": [["Name", "Name (English)"], ["Arab Investment Bank", "Arab Investment Bank"]]},
    )
    _write_minimal_xlsx(
        old_dir / "Capital_Market_old.xlsx",
        {"02_Capital_Market": [["Name"], ["Pilot Brokerage"]]},
    )
    seed_sites.write_text(
        "\n".join(
            [
                "name_en,official_website,source_url,notes",
                "Arab Investment Bank,https://aib.example,manual-reviewed seed,missing-bank proof",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_robots(url, timeout_seconds):
        return {"allowed": True, "reason": "fixture robots allow URL"}

    def fake_fetch(url, timeout_seconds):
        if url.endswith("/murabaha"):
            body = (
                "<html><body><h1>SME Murabaha Finance</h1>"
                + "Murabaha deferred payment fees ownership late payment charity "
                * 45
                + "</body></html>"
            ).encode("utf-8")
        else:
            body = (
                '<html><body><h1>aiBANK Products</h1>'
                '<a href="/murabaha">SME Murabaha Finance</a>'
                + "fees finance product " * 80
                + "</body></html>"
            ).encode("utf-8")
        return pilot.FetchResponse(
            status_code=200,
            content_type="text/html",
            body=body,
            final_url=url,
        )

    monkeypatch.setattr(pilot, "_check_robots", fake_robots)
    monkeypatch.setattr(pilot, "_urlopen_fetch", fake_fetch)
    monkeypatch.setattr(pilot, "_load_banksegypt_official_sites", lambda timeout_seconds: {})

    exit_code = run_legacy_sector_scrape(
        old_scraping_dir=old_dir,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 21),
        seed_sites_file=seed_sites,
        timeout_seconds=1.0,
        delay_seconds=0.0,
        max_targets=0,
        max_pages_per_target=2,
        sectors=None,
    )

    output_dir = artifact_root / "legacy_sector_scrape" / "2026-05-21"
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output_dir / "legacy_scrape_results.csv").open(encoding="utf-8")))

    assert exit_code == 0
    assert manifest["candidate_count"] == 2
    assert manifest["operations_extracted"] >= 1
    assert manifest["gap_count"] == 1
    assert {row["status"] for row in rows} == {"extracted", "official_site_not_found"}
    assert (output_dir / "engine_assessment_rows.csv").exists()
    assert (output_dir / "scholar_review_list_bilingual.csv").exists()


def test_official_registry_completion_records_cbe_pdf_hash_and_dedupe(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {
            "01_CBE_Banks": [
                ["Institution Name", "Source URL"],
                ["Arab Investment Bank", "https://workbook.example/cbe-row"],
            ]
        },
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    cbe_body = _minimal_text_pdf(
        "Banks Registered with the Central Bank of Egypt\n"
        "Arab Investment Bank | 1974-08-08 | 8 Abdel Khalek Tharwat"
    )

    monkeypatch.setattr(
        pilot,
        "_urlopen_fetch",
        lambda url, timeout_seconds: pilot.FetchResponse(
            status_code=200,
            content_type="application/pdf",
            body=cbe_body,
            final_url=url,
        ),
    )

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="https://cbe.example/banks.pdf",
        fra_register_urls={},
    )

    rows = list(csv.DictReader((output_dir / "normalized_institution_registry.csv").open(encoding="utf-8")))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["cbe"]["parse_status"] == "parsed"
    assert rows[0]["raw_artifact_sha256"].startswith("sha256:")
    assert rows[0]["source_url"] == "https://workbook.example/cbe-row | https://cbe.example/banks.pdf"
    assert rows[0]["source_type"] == "cbe_bank_pdf"
    assert rows[0]["duplicate_score"] == "1.00"
    assert rows[0]["ready_for_product_crawl"] == "false"
    assert rows[0]["gap_reason"] == "official website or reviewed official-source candidate required before product crawl"


def test_official_registry_completion_fra_pagination_stops_deterministically(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {"02_Capital_Market": [["Institution Name"], ["Existing Brokerage"]]},
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    pages = {
        "https://fra.example/register": """
        <table>
          <tr><th>Name</th><th>License Date</th></tr>
          <tr><td><a href="/detail/a">First Brokerage</a></td><td>2026-01-01</td></tr>
        </table>
        <a rel="next" href="/register?page=2">Next</a>
        """,
        "https://fra.example/register?page=2": """
        <table>
          <tr><th>Name</th><th>License Date</th></tr>
          <tr><td><a href="/detail/b">Second Brokerage</a></td><td>2026-01-02</td></tr>
        </table>
        """,
        "https://fra.example/detail/a": "<table><tr><th>English Name</th><td>First Brokerage</td></tr></table>",
        "https://fra.example/detail/b": "<table><tr><th>English Name</th><td>Second Brokerage</td></tr></table>",
    }
    requested_urls = []

    def fake_read(url, timeout_seconds):
        requested_urls.append(url)
        return pages[url]

    monkeypatch.setattr(pilot, "_read_text_url", fake_read)

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="",
        fra_register_urls={"capital_market": "https://fra.example/register"},
    )

    rows = list(csv.DictReader((output_dir / "normalized_institution_registry.csv").open(encoding="utf-8")))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["fra"]["capital_market"]["page_count"] == 2
    assert manifest["fra"]["capital_market"]["parsed_row_count"] == 2
    assert requested_urls == [
        "https://fra.example/register",
        "https://fra.example/detail/a",
        "https://fra.example/register?page=2",
        "https://fra.example/detail/b",
    ]
    assert {row["name_en"] for row in rows} >= {"First Brokerage", "Second Brokerage"}


def test_official_registry_completion_records_cbe_security_page_as_blocked(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {"01_CBE_Banks": [["Institution Name"], ["Arab Investment Bank"]]},
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    blocked_body = b"<html><title>Request Rejected</title>The requested URL was rejected.</html>"

    def blocked_fetch(url, timeout_seconds):
        raise pilot.AccessBlockedError("access blocked by upstream security page", blocked_body)

    monkeypatch.setattr(pilot, "_urlopen_fetch", blocked_fetch)

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="https://cbe.example/banks.pdf",
        fra_register_urls={},
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["cbe"]["parse_status"] == "blocked_by_security"
    assert manifest["cbe"]["raw_artifact_sha256"].startswith("sha256:")
    assert manifest["normalized_row_count"] == 1


def test_fra_detail_fields_parse_visible_arabic_and_english_labels():
    detail_html = """
    <table>
      <tr><th>اسم الشركة</th><td>الأهلي كابيتال للتمويل متناهي الصغر</td></tr>
      <tr><th>English Name</th><td>Al Ahly Capital Microfinance</td></tr>
      <tr><th>License Number</th><td>MF-123</td></tr>
      <tr><th>تاريخ الترخيص</th><td>2026-01-08</td></tr>
      <tr><th>Licensed Activity</th><td>Microfinance</td></tr>
      <tr><th>Website</th><td>https://alahly.example</td></tr>
    </table>
    """

    fields = _fra_detail_fields_from_html(detail_html)

    assert fields["name_ar"] == "الأهلي كابيتال للتمويل متناهي الصغر"
    assert fields["name_en"] == "Al Ahly Capital Microfinance"
    assert fields["license_id"] == "MF-123"
    assert fields["license_date"] == "2026-01-08"
    assert fields["official_website"] == "https://alahly.example"


def test_official_registry_completion_exports_fra_rows_and_fail_closed_readiness(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {"02_Capital_Market": [["Institution Name"], ["Pilot Brokerage"]]},
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    register_html = """
    <table>
      <tr><th>Name</th><th>License Date</th></tr>
      <tr><td><a href="/en/company_records/pilot">Pilot Brokerage</a></td><td>2026-01-08</td></tr>
    </table>
    """
    detail_html = """
    <table>
      <tr><th>Arabic Name</th><td>بايلوت للسمسرة</td></tr>
      <tr><th>English Name</th><td>Pilot Brokerage</td></tr>
      <tr><th>License Number</th><td>CM-77</td></tr>
      <tr><th>License Date</th><td>2026-01-08</td></tr>
    </table>
    """

    def fake_read(url, timeout_seconds):
        return detail_html if "company_records" in url else register_html

    monkeypatch.setattr(pilot, "_read_text_url", fake_read)
    monkeypatch.setattr(
        pilot,
        "_urlopen_fetch",
        lambda url, timeout_seconds: pilot.FetchResponse(
            status_code=200,
            content_type="text/plain",
            body=b"",
            final_url=url,
        ),
    )

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="",
        fra_register_urls={"capital_market": "https://fra.example/register"},
    )

    rows = list(csv.DictReader((output_dir / "normalized_institution_registry.csv").open(encoding="utf-8")))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["fra"]["capital_market"]["parse_status"] == "parsed"
    assert rows[0]["name_en"] == "Pilot Brokerage"
    assert rows[0]["name_ar"] == "بايلوت للسمسرة"
    assert rows[0]["license_id"] == "CM-77"
    assert rows[0]["duplicate_score"] == "1.00"
    assert rows[0]["ready_for_product_crawl"] == "false"
    assert rows[0]["source_type"] == "fra_register_detail"


def test_official_registry_completion_records_fra_linked_pdf_artifacts(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {"03_Insurance": [["Institution Name"], ["Delta Insurance"]]},
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    register_html = """
    <p>Last modified: 2026-04-23</p>
    <table>
      <tr><th>Name</th><th>License Date</th></tr>
      <tr><td><a href="/en/company_records/delta">Delta Insurance</a></td><td>2026-04-23</td></tr>
    </table>
    """
    detail_html = """
    <table>
      <tr><th>English Name</th><td>Delta Insurance</td></tr>
      <tr><th>License Number</th><td>INS-44</td></tr>
    </table>
    <a href="/media/delta-license.pdf">Official license PDF</a>
    """

    def fake_read(url, timeout_seconds):
        return detail_html if "company_records" in url else register_html

    monkeypatch.setattr(pilot, "_read_text_url", fake_read)
    monkeypatch.setattr(
        pilot,
        "_urlopen_fetch",
        lambda url, timeout_seconds: pilot.FetchResponse(
            status_code=200,
            content_type="application/pdf",
            body=b"%PDF-1.7 official fra artifact",
            final_url=url,
        ),
    )

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="",
        fra_register_urls={"insurance": "https://fra.example/register"},
    )

    rows = list(csv.DictReader((output_dir / "normalized_institution_registry.csv").open(encoding="utf-8")))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["fra"]["insurance"]["linked_official_pdf_count"] == 1
    assert rows[0]["source_last_modified"] == "2026-04-23"
    assert rows[0]["source_type"] == "fra_register_detail_with_linked_pdf"
    assert rows[0]["linked_official_pdf_urls"] == "https://fra.example/media/delta-license.pdf"
    assert rows[0]["linked_official_pdf_hashes"].startswith("sha256:")
    assert (output_dir / "raw" / "fra_insurance_detail_1_pdf_1.pdf").exists()


def test_official_registry_completion_uses_same_fra_parser_for_finance_and_fintech(tmp_path, monkeypatch):
    import scripts.run_l6_institution_pilot as pilot

    workbook = tmp_path / "institutions.xlsx"
    artifact_root = tmp_path / "artifacts" / "l6_scrape"
    _write_minimal_xlsx(
        workbook,
        {
            "04_NonBank_Financial": [
                ["Institution Name", "Sector"],
                ["Micro Pilot Finance", "microfinance"],
                ["Pay Pilot", "fintech"],
            ]
        },
    )
    baseline = WorkbookRegistryLoader().load_xlsx(workbook)
    pages = {
        "https://fra.example/finance": """
        <table><tr><th>Name</th></tr><tr><td><a href="/detail/finance">Micro Pilot Finance</a></td></tr></table>
        """,
        "https://fra.example/detail/finance": """
        <table><tr><th>English Name</th><td>Micro Pilot Finance</td></tr></table>
        """,
        "https://fra.example/fintech": """
        <table><tr><th>Name</th></tr><tr><td><a href="/detail/fintech">Pay Pilot</a></td></tr></table>
        """,
        "https://fra.example/detail/fintech": """
        <table><tr><th>English Name</th><td>Pay Pilot</td></tr></table>
        """,
    }

    monkeypatch.setattr(pilot, "_read_text_url", lambda url, timeout_seconds: pages[url])

    output_dir = run_official_registry_completion(
        baseline_registry=baseline,
        artifact_root=artifact_root,
        run_date=date(2026, 5, 22),
        timeout_seconds=1.0,
        cbe_pdf_url="",
        fra_register_urls={
            "finance": "https://fra.example/finance",
            "fintech": "https://fra.example/fintech",
        },
    )

    rows = list(csv.DictReader((output_dir / "normalized_institution_registry.csv").open(encoding="utf-8")))
    sectors_by_name = {row["name_en"]: row["sector"] for row in rows}

    assert sectors_by_name["Micro Pilot Finance"] == "non_bank_finance"
    assert sectors_by_name["Pay Pilot"] == "fintech"


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


def _minimal_text_pdf(text):
    escaped = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", ") Tj\n(")
    )
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        + f"4 0 obj << /Length {len(escaped) + 20} >> stream\nBT\n({escaped}) Tj\nET\nendstream\nendobj\n".encode("utf-8")
        + b"%%EOF\n"
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
