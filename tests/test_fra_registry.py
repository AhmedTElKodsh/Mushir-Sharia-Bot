from __future__ import annotations

import csv
import hashlib
import importlib
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest


FIXTURE_DIR = Path("data/fixtures/l6_scrape/fra_consumer_finance")
START_URL = "https://fra.example/registry/?filtered_type=consumer-finance"
PAGE_2_URL = "https://fra.example/registry/page/2/?filtered_type=consumer-finance"


def _fra_registry():
    try:
        return importlib.import_module("src.acquisition.egypt_financial.fra_registry")
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"FRA registry feature is not implemented: {exc}", pytrace=False)


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _allowed(module):
    return module.AccessDecision(allowed=True, state="allowed", reason="fixture policy allows")


def test_current_layout_listing_parser_preserves_arabic_rows_and_next_page():
    fra = _fra_registry()

    page = fra.parse_listing_page(_fixture("listing-page-1.html"), START_URL)

    assert page.next_url == PAGE_2_URL
    assert [entry.company_name_ar for entry in page.entries] == [
        "شركة ألف للتمويل الاستهلاكي",
        "شركة باء للتمويل الاستهلاكي",
    ]
    assert [entry.license_date for entry in page.entries] == ["2024-01-10", "2024-02-11"]
    assert [entry.detail_url for entry in page.entries] == [
        "https://fra.example/company_records/alpha",
        "https://fra.example/company_records/beta",
    ]


def test_four_cell_detail_parser_keeps_unique_activity_date_pairs():
    fra = _fra_registry()

    detail = fra.parse_detail_page(_fixture("detail-alpha.html"))

    assert detail.company_name_ar == "شركة ألف للتمويل الاستهلاكي"
    assert detail.company_name_en == "ALPHA CONSUMER FINANCE"
    assert detail.company_number == "CF-101"
    assert detail.address == "١٠ شارع الاختبار، القاهرة"
    assert detail.license_number == "LIC-101"
    assert [activity.to_dict() for activity in detail.activities] == [
        {"activity_ar": "تمويل استهلاكي", "activity_date": "2024-01-15"},
        {"activity_ar": "وساطة تأمينية رقمية", "activity_date": "2024-06-20"},
    ]


def test_complete_scrape_is_ordered_deduplicated_and_utf8_sig_round_trippable(tmp_path):
    fra = _fra_registry()
    pages = {
        START_URL: _fixture("listing-page-1.html"),
        PAGE_2_URL: _fixture("listing-page-2.html"),
        "https://fra.example/company_records/alpha": _fixture("detail-alpha.html"),
        "https://fra.example/company_records/beta": _fixture("detail-beta.html"),
        "https://fra.example/company_records/gamma": _fixture("detail-alpha.html").replace(
            "شركة ألف", "شركة جيم"
        ).replace("CF-101", "CF-303"),
    }
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        return pages[url].encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=2,
        delay_seconds=0,
        max_pages=5,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    assert result.exit_code == 0
    assert requested == [
        START_URL,
        PAGE_2_URL,
        "https://fra.example/company_records/alpha",
        "https://fra.example/company_records/beta",
        "https://fra.example/company_records/gamma",
    ]
    assert result.csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    with result.csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["company_name_ar"] for row in rows] == [
        "شركة ألف للتمويل الاستهلاكي",
        "شركة باء للتمويل الاستهلاكي",
        "شركة جيم للتمويل الاستهلاكي",
    ]
    assert all(row["regulator"] == "FRA" for row in rows)
    assert all(row["registry_name_ar"] == "سجلات لشركات التمويل" for row in rows)
    assert all(row["fra_type_code"] == "consumer-finance" for row in rows)
    assert all(row["fra_type_ar"] == "تمويل استهلاكي" for row in rows)
    activities = json.loads(rows[0]["activities_json"])
    assert activities[1] == {
        "activity_ar": "وساطة تأمينية رقمية",
        "activity_date": "2024-06-20",
    }
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["listing_pages_fetched"] == 2
    assert manifest["listing_records_seen"] == 4
    assert manifest["unique_company_count"] == 3
    assert manifest["duplicate_listing_count"] == 1
    assert manifest["detail_fetch_succeeded"] == 3
    assert manifest["csv_row_count"] == 3
    assert manifest["raw_capture_count"] == 5
    assert all(item["sha256"].startswith("sha256:") for item in manifest["raw_captures"])
    assert manifest["output_csv_sha256"] == (
        "sha256:" + hashlib.sha256(result.csv_path.read_bytes()).hexdigest()
    )


def test_source_absence_and_detail_failure_use_distinct_exact_sentinels(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html")
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        if url == START_URL:
            return listing.replace(
                '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
                "",
            ).encode("utf-8")
        if url.endswith("/alpha"):
            return _fixture("detail-beta.html").replace("شركة باء", "شركة ألف").encode("utf-8")
        raise TimeoutError("token=secret-value registry timed out")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=0.1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    with result.csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["address"] == "No data exists"
    assert rows[0]["activities_json"] == '[{"activity_ar":"تمويل استهلاكي","activity_date":"No data exists"}]'
    assert rows[0]["scrape_status"] == "complete"
    assert rows[0]["scrape_error"] == ""
    assert rows[1]["company_name_ar"] == "شركة باء للتمويل الاستهلاكي"
    assert rows[1]["license_date"] == "2024-02-11"
    assert rows[1]["company_number"] == "Not scraped due to technical error"
    assert rows[1]["address"] == "Not scraped due to technical error"
    assert rows[1]["activities_json"] == "Not scraped due to technical error"
    assert rows[1]["scrape_status"] == "technical_error"
    assert rows[1]["scrape_error"] == "TimeoutError: request timed out"
    assert "secret-value" not in result.csv_path.read_text(encoding="utf-8-sig")
    assert result.exit_code != 0


def test_unparseable_detail_is_a_technical_error_not_source_absence(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    )

    def fetch(url: str, timeout_seconds: float) -> bytes:
        if url == START_URL:
            return listing.encode("utf-8")
        if url.endswith("/alpha"):
            return b"<html><body>Temporarily unavailable</body></html>"
        return _fixture("detail-beta.html").encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    with result.csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["company_number"] == "Not scraped due to technical error"
    assert rows[0]["scrape_status"] == "technical_error"
    assert rows[0]["scrape_error"] == "ValueError: response could not be parsed"
    assert rows[1]["address"] == "No data exists"
    assert result.exit_code != 0


def test_off_host_detail_is_not_fetched_and_manifest_reports_partial_run(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        "/company_records/alpha", "https://outside.example/company/alpha"
    ).replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    )
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        if url == START_URL:
            return listing.encode("utf-8")
        if url.endswith("/beta"):
            return _fixture("detail-beta.html").encode("utf-8")
        raise AssertionError(f"prohibited fetch: {url}")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    assert "https://outside.example/company/alpha" not in requested
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "partial"
    assert manifest["off_host_detail_count"] == 1
    assert manifest["detail_fetch_attempted"] == 1
    assert manifest["detail_fetch_failed"] == 1
    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("state", "acknowledge", "expect_fetch"),
    [("disallowed", True, False), ("unavailable", False, False), ("unavailable", True, True)],
)
def test_access_policy_never_overrides_disallow_and_requires_ack_for_unavailable_robots(
    tmp_path, state, acknowledge, expect_fetch
):
    fra = _fra_registry()
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        return _fixture("listing-page-1.html").replace(
            '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
            "",
        ).replace("/company_records/alpha", "").replace("/company_records/beta", "").encode("utf-8")

    decision = fra.AccessDecision(
        allowed=False,
        state=state,
        reason="fixture robots policy",
    )
    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: decision,
        acknowledge_unavailable_robots=acknowledge,
    )

    assert bool(requested) is expect_fetch
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["robots_unavailable_acknowledged"] is acknowledge
    if not expect_fetch:
        assert manifest["status"] == "blocked"
        assert manifest["csv_row_count"] == 0
        assert result.exit_code != 0


def test_security_blocker_stops_before_later_pages_or_details(tmp_path):
    fra = _fra_registry()
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        return b"<html><title>Access denied</title><p>CAPTCHA verification required</p></html>"

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    assert requested == [START_URL]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "blocked"
    assert manifest["blocker"] == "blocked_by_security"
    assert manifest["csv_row_count"] == 0
    assert result.exit_code != 0


def test_visited_pagination_url_stops_without_refetching(tmp_path):
    fra = _fra_registry()
    looping = _fixture("listing-page-1.html").replace(
        "/registry/page/2/?filtered_type=consumer-finance",
        "/registry/?filtered_type=consumer-finance",
    )
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        return looping.encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        timeout_seconds=1,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    assert requested.count(START_URL) == 1
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "partial"
    assert manifest["pagination_stop_reason"] == "visited_url"
    assert result.exit_code != 0


def test_cli_forwards_options_and_returns_scrape_exit_code(tmp_path):
    fra = _fra_registry()
    script = importlib.import_module("scripts.scrape_fra_registry")
    captured = {}

    def fake_scrape(**kwargs):
        captured.update(kwargs)
        return fra.RegistryRunResult(
            csv_path=tmp_path / "companies.csv",
            manifest_path=tmp_path / "manifest.json",
            exit_code=2,
        )

    exit_code = script.main(
        [
            "--fra-type",
            "consumer-finance",
            "--fra-type-ar",
            "تمويل استهلاكي",
            "--today",
            "2026-08-31",
            "--output-dir",
            str(tmp_path),
            "--timeout-seconds",
            "7",
            "--delay-seconds",
            "1.5",
            "--max-pages",
            "3",
            "--site-terms-review-state",
            "no-separate-terms-found",
            "--acknowledge-unavailable-robots",
        ],
        scrape=fake_scrape,
    )

    assert exit_code == 2
    assert captured["fra_type_code"] == "consumer-finance"
    assert captured["fra_type_ar"] == "تمويل استهلاكي"
    assert captured["run_date"] == "2026-08-31"
    assert captured["output_dir"] == tmp_path
    assert captured["timeout_seconds"] == 7
    assert captured["delay_seconds"] == 1.5
    assert captured["max_pages"] == 3
    assert captured["acknowledge_unavailable_robots"] is True
    assert captured["user_agent"] == fra.USER_AGENT
    assert captured["site_terms_review_state"] == "no-separate-terms-found"


def test_unrecognized_zero_entry_listing_fails_closed(tmp_path):
    fra = _fra_registry()

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=lambda url, timeout: b"<html><body><table><tr><td>layout drift</td></tr></table></body></html>",
        access_checker=lambda url, timeout: _allowed(fra),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.exit_code != 0
    assert manifest["status"] == "partial"
    assert manifest["listing_error"] == "ValueError: response could not be parsed"
    assert manifest["csv_row_count"] == 0


def test_robots_policy_is_checked_before_each_new_path(tmp_path):
    fra = _fra_registry()
    checked: list[str] = []
    requested: list[str] = []

    def check(url: str, timeout_seconds: float):
        checked.append(url)
        if url == PAGE_2_URL:
            return fra.AccessDecision(False, "disallowed", "page path disallowed")
        return _allowed(fra)

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        return _fixture("listing-page-1.html").encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=check,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert checked == [START_URL, PAGE_2_URL]
    assert requested == [START_URL]
    assert result.exit_code == 2
    assert manifest["status"] == "blocked"
    assert manifest["blocker"] == "robots_disallowed"


def test_robots_404_is_unavailable_and_requires_acknowledgement(monkeypatch):
    fra = _fra_registry()

    def missing(url: str, timeout_seconds: float, **kwargs) -> bytes:
        raise urllib.error.HTTPError(url, 404, "missing", {}, None)

    monkeypatch.setattr(fra, "fetch_url", missing)
    decision = fra.check_robots_access(START_URL, 1)

    assert decision.allowed is False
    assert decision.state == "unavailable"


def test_http_403_detail_stops_all_later_detail_requests(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    )
    requested: list[str] = []

    def fetch(url: str, timeout_seconds: float) -> bytes:
        requested.append(url)
        if url == START_URL:
            return listing.encode("utf-8")
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert requested == [START_URL, "https://fra.example/company_records/alpha"]
    assert result.exit_code == 2
    assert manifest["status"] == "blocked"
    assert manifest["blocker"] == "blocked_by_security"
    assert manifest["detail_fetch_attempted"] == 1
    assert manifest["detail_fetch_failed"] == 1
    assert manifest["detail_skipped_after_blocker"] == 1


def test_duplicate_company_number_reconciles_manifest_counters(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    )
    alpha = _fixture("detail-alpha.html")
    beta_same_number = _fixture("detail-beta.html").replace("CF-202", "CF-101")

    def fetch(url: str, timeout_seconds: float) -> bytes:
        if url == START_URL:
            return listing.encode("utf-8")
        if url.endswith("/alpha"):
            return alpha.encode("utf-8")
        return beta_same_number.encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["detail_fetch_attempted"] == 2
    assert manifest["detail_fetch_succeeded"] == 2
    assert manifest["detail_fetch_failed"] == 0
    assert manifest["duplicate_company_number_count"] == 1
    assert manifest["csv_row_count"] == 1


def test_license_date_is_not_attached_to_an_undated_activity():
    fra = _fra_registry()
    detail = fra.parse_detail_page(
        """
        <table>
          <tr><td>اسم الشركة</td><td>شركة ألف</td><td>رقم الشركة</td><td>1</td></tr>
          <tr><td>اسم النشاط</td><td>تمويل استهلاكي</td></tr>
          <tr><td>تاريخ الترخيص</td><td>2026-01-02</td></tr>
        </table>
        """
    )

    assert detail.license_date == "2026-01-02"
    assert detail.activities[0].activity_date is None


def test_partial_detail_without_identity_is_a_parser_failure():
    fra = _fra_registry()

    with pytest.raises(ValueError):
        fra.parse_detail_page("<table><tr><td>العنوان</td><td>القاهرة</td></tr></table>")


def test_detail_identity_mismatch_is_a_technical_error(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    ).replace(
        '<tr>\n        <td>-</td>\n        <td><a href="/company_records/beta">شركة باء للتمويل الاستهلاكي</a></td>\n        <td>2024-02-11</td>\n      </tr>',
        "",
    )

    def fetch(url: str, timeout_seconds: float) -> bytes:
        if url == START_URL:
            return listing.encode("utf-8")
        return _fixture("detail-beta.html").encode("utf-8")

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=fetch,
        access_checker=lambda url, timeout: _allowed(fra),
    )

    with result.csv_path.open(newline="", encoding="utf-8-sig") as handle:
        row = next(csv.DictReader(handle))
    assert row["company_name_ar"] == "شركة ألف للتمويل الاستهلاكي"
    assert row["company_number"] == "Not scraped due to technical error"
    assert row["scrape_status"] == "technical_error"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--timeout-seconds", "0"],
        ["--timeout-seconds", "nan"],
        ["--delay-seconds", "-1"],
        ["--delay-seconds", "nan"],
        ["--max-pages", "0"],
        ["--fra-type", ""],
        ["--start-url", "http://fra.gov.eg/registry"],
        ["--start-url", "https://outside.example/registry"],
    ],
)
def test_cli_rejects_unsafe_or_unbounded_inputs(arguments):
    script = importlib.import_module("scripts.scrape_fra_registry")

    with pytest.raises(SystemExit) as exc_info:
        script.main(arguments, scrape=lambda **kwargs: pytest.fail("scrape must not run"))

    assert exc_info.value.code == 2


def test_listing_with_one_dropped_candidate_row_fails_closed(tmp_path):
    fra = _fra_registry()
    listing = _fixture("listing-page-1.html").replace(
        'href="/company_records/beta"', 'href=""'
    ).replace(
        '<a class="next page-numbers" rel="next" href="/registry/page/2/?filtered_type=consumer-finance">التالي</a>',
        "",
    )

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=lambda url, timeout: listing.encode("utf-8"),
        access_checker=lambda url, timeout: _allowed(fra),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.exit_code == 1
    assert manifest["listing_error"] == "ValueError: response could not be parsed"
    assert manifest["csv_row_count"] == 0


def test_redirect_handler_rejects_cross_origin_before_following():
    fra = _fra_registry()
    handler = fra._SameOriginRedirectHandler()
    request = urllib.request.Request("https://fra.gov.eg/company_records/1")

    with pytest.raises(PermissionError):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://outside.example/collect",
        )

    assert fra._same_origin("https://fra.gov.eg/a", "http://fra.gov.eg/b") is False
    assert fra._same_origin("https://fra.gov.eg/a", "https://fra.gov.eg:444/b") is False


def test_raw_robots_response_is_hashed_and_isolated_per_run(tmp_path, monkeypatch):
    fra = _fra_registry()
    robots_payload = b"<html><body>Authorization required</body></html>"
    policy = fra.RobotsPolicy(
        state="unavailable",
        reason="robots.txt did not return robots directives",
        robots_url="https://fra.example/robots.txt",
        payload=robots_payload,
    )
    monkeypatch.setattr(fra, "load_robots_policy", lambda *args, **kwargs: policy)

    result = fra.scrape_registry(
        start_url=START_URL,
        fra_type_code="consumer-finance",
        fra_type_ar="تمويل استهلاكي",
        run_date="2026-08-31",
        output_dir=tmp_path,
        delay_seconds=0,
        fetcher=lambda url, timeout: "<p>لا توجد نتائج</p>".encode("utf-8"),
        acknowledge_unavailable_robots=True,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0
    assert manifest["raw_capture_count"] == 2
    assert manifest["raw_captures"][0]["kind"] == "robots"
    assert manifest["raw_captures"][0]["sha256"].startswith("sha256:")
    assert f"raw/{manifest['run_id']}/" in manifest["raw_captures"][0]["path"]


def test_csv_escapes_formula_triggering_source_text(tmp_path):
    fra = _fra_registry()
    row = {field: "safe" for field in fra.CSV_FIELDS}
    row["company_name_ar"] = "=HYPERLINK(\"https://example.invalid\")"
    path = tmp_path / "safe.csv"

    fra._write_csv(path, [row])

    with path.open(newline="", encoding="utf-8-sig") as handle:
        exported = next(csv.DictReader(handle))
    assert exported["company_name_ar"].startswith("'=")
