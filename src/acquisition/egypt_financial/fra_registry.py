"""Conservative acquisition of typed company registers published by Egypt's FRA.

The records produced here are regulator-source facts, not Sharia rulings and not
runtime-eligible knowledge.  The module intentionally uses only the standard
library and keeps source absence distinct from collection failure.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import uuid
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Optional


NO_DATA = "No data exists"
TECHNICAL_ERROR = "Not scraped due to technical error"
REGULATOR = "FRA"
REGISTRY_NAME_AR = "سجلات لشركات التمويل"
USER_AGENT = "MushirResearchBot/0.1 (+public-source compliance research; contact: local)"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
KNOWN_FRA_TYPE_TITLES = {"consumer-finance": "تمويل استهلاكي"}

CSV_FIELDS = [
    "regulator",
    "registry_name_ar",
    "fra_type_code",
    "fra_type_ar",
    "company_name_ar",
    "company_name_en",
    "company_number",
    "address",
    "license_number",
    "activities_json",
    "license_date",
    "company_detail_url",
    "registry_listing_url",
    "scraped_at",
    "scrape_status",
    "scrape_error",
]


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    state: str
    reason: str


@dataclass(frozen=True)
class RobotsPolicy:
    state: str
    reason: str
    robots_url: str
    payload: Optional[bytes] = None
    parser: Optional[urllib.robotparser.RobotFileParser] = None
    crawl_delay: float = 0.0
    user_agent: str = USER_AGENT

    def decision_for(self, url: str) -> AccessDecision:
        if self.state != "allowed" or self.parser is None:
            return AccessDecision(False, self.state, self.reason)
        if self.parser.can_fetch(self.user_agent, url):
            return AccessDecision(True, "allowed", "robots.txt allows URL")
        return AccessDecision(False, "disallowed", "robots.txt disallows URL")


@dataclass(frozen=True)
class Activity:
    activity_ar: str
    activity_date: Optional[str] = None

    def to_dict(self) -> dict[str, Optional[str]]:
        return {
            "activity_ar": self.activity_ar,
            "activity_date": self.activity_date,
        }


@dataclass(frozen=True)
class ListingEntry:
    company_name_ar: str
    license_date: Optional[str]
    detail_url: str
    listing_url: str = ""


@dataclass(frozen=True)
class ListingPage:
    entries: tuple[ListingEntry, ...]
    next_url: Optional[str]
    unparsed_candidate_rows: int = 0


@dataclass(frozen=True)
class CompanyDetail:
    company_name_ar: Optional[str] = None
    company_name_en: Optional[str] = None
    company_number: Optional[str] = None
    address: Optional[str] = None
    license_number: Optional[str] = None
    license_date: Optional[str] = None
    activities: tuple[Activity, ...] = ()


@dataclass(frozen=True)
class RegistryRunResult:
    csv_path: Path
    manifest_path: Path
    exit_code: int


@dataclass
class _Anchor:
    href: str
    rel: str = ""
    css_class: str = ""
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self.text_parts))


@dataclass
class _Cell:
    text_parts: list[str] = field(default_factory=list)
    anchors: list[_Anchor] = field(default_factory=list)

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self.text_parts))


class _TableParser(HTMLParser):
    """Capture table rows and anchors without adding an HTML dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_Cell]] = []
        self.anchors: list[_Anchor] = []
        self._row: Optional[list[_Cell]] = None
        self._cell: Optional[_Cell] = None
        self._anchor: Optional[_Anchor] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = _Cell()
        elif tag == "a":
            self._anchor = _Anchor(
                href=attributes.get("href", ""),
                rel=attributes.get("rel", ""),
                css_class=attributes.get("class", ""),
            )

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.text_parts.append(data)
        if self._anchor is not None:
            self._anchor.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._anchor is not None:
            self.anchors.append(self._anchor)
            if self._cell is not None:
                self._cell.anchors.append(self._anchor)
            self._anchor = None
        elif tag in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


class _VisibleTextParser(HTMLParser):
    """Collect user-visible text while excluding scripts and styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self.parts))


def parse_listing_page(html_text: str, base_url: str) -> ListingPage:
    parser = _TableParser()
    parser.feed(html_text)
    entries: list[ListingEntry] = []
    unparsed_candidate_rows = 0
    for row in parser.rows:
        row_has_date = any(_is_date(cell.text) for cell in row)
        detail_anchor = next(
            (
                anchor
                for cell in row
                for anchor in cell.anchors
                if _is_company_detail_href(anchor.href)
            ),
            None,
        )
        if detail_anchor is None and row_has_date:
            detail_anchor = next(
                (anchor for cell in row for anchor in cell.anchors if anchor.href),
                None,
            )
        if detail_anchor is None:
            if row_has_date:
                unparsed_candidate_rows += 1
            continue
        company_name = detail_anchor.text
        if not _has_letter(company_name) or company_name in {"عرض", "التفاصيل", "Details"}:
            company_name = _company_name_from_row(row)
        if not _has_letter(company_name):
            if row_has_date:
                unparsed_candidate_rows += 1
            continue
        license_date = next(
            (cell.text for cell in row if _is_date(cell.text)),
            None,
        )
        detail_url = _canonical_url(urllib.parse.urljoin(base_url, detail_anchor.href))
        entries.append(
            ListingEntry(
                company_name_ar=company_name,
                license_date=license_date,
                detail_url=detail_url,
                listing_url=_canonical_url(base_url),
            )
        )

    next_url: Optional[str] = None
    for anchor in parser.anchors:
        rel_tokens = {part.lower() for part in anchor.rel.split()}
        label = anchor.text.strip().lower()
        if "next" in rel_tokens or label in {"next", ">", "»", "التالي", "التالي »"}:
            if anchor.href:
                next_url = _canonical_url(urllib.parse.urljoin(base_url, anchor.href))
                break
    return ListingPage(
        entries=tuple(entries),
        next_url=next_url,
        unparsed_candidate_rows=unparsed_candidate_rows,
    )


def parse_detail_page(html_text: str) -> CompanyDetail:
    parser = _TableParser()
    parser.feed(html_text)
    values: dict[str, str] = {}
    activities: list[Activity] = []

    for row in parser.rows:
        texts = [cell.text for cell in row]
        for index in range(0, len(texts) - 1, 2):
            label = _normalize_label(texts[index])
            value = _clean_text(texts[index + 1]) or None
            if not label:
                continue
            if _is_english_name_label(label):
                if value:
                    values.setdefault("company_name_en", value)
            elif _is_company_name_label(label):
                if value:
                    values.setdefault("company_name_ar", value)
            elif _is_company_number_label(label):
                if value:
                    values.setdefault("company_number", value)
            elif _is_address_label(label):
                if value:
                    values.setdefault("address", value)
            elif _is_license_number_label(label):
                if value:
                    values.setdefault("license_number", value)
            elif _is_activity_label(label):
                if value:
                    activities.append(Activity(activity_ar=value))
            elif _is_activity_date_label(label):
                if activities and activities[-1].activity_date is None:
                    last = activities[-1]
                    activities[-1] = Activity(last.activity_ar, value)
                elif value:
                    raise ValueError("activity date had no matching activity")
            elif _is_license_date_label(label):
                if value:
                    values.setdefault("license_date", value)

    unique_activities: list[Activity] = []
    seen_activities: set[tuple[str, Optional[str]]] = set()
    for activity in activities:
        key = (activity.activity_ar, activity.activity_date)
        if key not in seen_activities:
            unique_activities.append(activity)
            seen_activities.add(key)
    if not values.get("company_name_ar") or not values.get("company_number"):
        raise ValueError("detail page did not contain required FRA identity fields")
    return CompanyDetail(
        company_name_ar=values.get("company_name_ar"),
        company_name_en=values.get("company_name_en"),
        company_number=values.get("company_number"),
        address=values.get("address"),
        license_number=values.get("license_number"),
        license_date=values.get("license_date"),
        activities=tuple(unique_activities),
    )


def scrape_registry(
    *,
    start_url: str,
    fra_type_code: str,
    fra_type_ar: str,
    run_date: str,
    output_dir: str | Path,
    timeout_seconds: float = 20.0,
    delay_seconds: float = 1.0,
    max_pages: int = 25,
    fetcher: Optional[Callable[[str, float], bytes]] = None,
    access_checker: Optional[Callable[[str, float], AccessDecision]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    acknowledge_unavailable_robots: bool = False,
    user_agent: str = USER_AGENT,
    site_terms_review_state: str = "not_recorded",
) -> RegistryRunResult:
    """Scrape one typed FRA register into one row per company."""
    if timeout_seconds <= 0 or delay_seconds < 0 or max_pages <= 0:
        raise ValueError("timeout, delay, and pagination bounds must be positive")
    if not fra_type_code.strip() or not fra_type_ar.strip():
        raise ValueError("FRA type code and Arabic title are required")
    expected_title = KNOWN_FRA_TYPE_TITLES.get(fra_type_code)
    if expected_title and fra_type_ar.strip() != expected_title:
        raise ValueError("FRA type code and Arabic title do not match")
    start_query = dict(
        urllib.parse.parse_qsl(urllib.parse.urlparse(start_url).query, keep_blank_values=True)
    )
    if start_query.get("filtered_type") not in {None, "", fra_type_code}:
        raise ValueError("start URL filter does not match the requested FRA type")
    if not user_agent.strip() or "\r" in user_agent or "\n" in user_agent:
        raise ValueError("a safe configured user agent is required")
    target = Path(output_dir)
    run_id = uuid.uuid4().hex
    raw_dir = target / "raw" / run_id
    target.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = target / f"fra_{_safe_slug(fra_type_code)}_companies.csv"
    manifest_path = target / "manifest.json"
    fetch = fetcher or (lambda url, timeout: fetch_url(url, timeout, user_agent=user_agent))
    raw_captures: list[dict[str, str]] = []
    request_count = 0

    def capture(payload: bytes, url: str, kind: str, index: int) -> None:
        path = raw_dir / f"{kind}-{index:03d}.html"
        path.write_bytes(payload)
        raw_captures.append(
            {
                "kind": kind,
                "url": url,
                "path": str(path).replace("\\", "/"),
                "sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
            }
        )

    policy: Optional[RobotsPolicy] = None
    if access_checker is None:
        policy = load_robots_policy(start_url, timeout_seconds, user_agent=user_agent)
        request_count = 1
        if policy.payload is not None:
            capture(policy.payload, policy.robots_url, "robots", 1)
        access = policy.decision_for(start_url)
        delay_seconds = max(delay_seconds, policy.crawl_delay)
    else:
        access = access_checker(start_url, timeout_seconds)

    access_cache: dict[str, AccessDecision] = {_canonical_url(start_url): access}

    def access_for(url: str) -> AccessDecision:
        key = _canonical_url(url)
        if key in access_cache:
            return access_cache[key]
        decision = (
            policy.decision_for(url)
            if policy is not None
            else access_checker(url, timeout_seconds)  # type: ignore[misc]
        )
        access_cache[key] = decision
        return decision

    def is_authorized(decision: AccessDecision) -> bool:
        return decision.allowed or (
            decision.state == "unavailable" and acknowledge_unavailable_robots
        )

    base_manifest = _manifest_base(
        start_url=start_url,
        fra_type_code=fra_type_code,
        fra_type_ar=fra_type_ar,
        run_date=run_date,
        csv_path=csv_path,
        access=access,
        acknowledged=acknowledge_unavailable_robots,
        site_terms_review_state=site_terms_review_state,
    )
    base_manifest["run_id"] = run_id
    if not is_authorized(access):
        _write_csv(csv_path, [])
        base_manifest["output_csv_sha256"] = _sha256_file(csv_path)
        base_manifest.update(
            status="blocked",
            blocker=("robots_disallowed" if access.state == "disallowed" else "robots_unavailable"),
            raw_capture_count=len(raw_captures),
            raw_captures=raw_captures,
        )
        _write_manifest(manifest_path, base_manifest)
        return RegistryRunResult(csv_path, manifest_path, 2)

    def retrieve(url: str, kind: str, index: int) -> tuple[bytes, str]:
        nonlocal request_count
        if request_count and delay_seconds > 0:
            sleeper(delay_seconds)
        request_count += 1
        payload = fetch(url, timeout_seconds)
        capture(payload, url, kind, index)
        return payload, _decode_html(payload)

    listing_entries: list[ListingEntry] = []
    visited: set[str] = set()
    current_url: Optional[str] = _canonical_url(start_url)
    pages_fetched = 0
    pagination_stop_reason = "end_of_results"
    blocker = ""
    listing_error = ""

    while current_url:
        if current_url in visited:
            pagination_stop_reason = "visited_url"
            break
        if pages_fetched >= max_pages:
            pagination_stop_reason = "max_pages"
            break
        if not _same_origin(start_url, current_url):
            pagination_stop_reason = "off_host_next_url"
            break
        decision = access_for(current_url)
        if not is_authorized(decision):
            blocker = (
                "robots_disallowed" if decision.state == "disallowed" else "robots_unavailable"
            )
            pagination_stop_reason = blocker
            break
        visited.add(current_url)
        try:
            _payload, text = retrieve(current_url, "listing", pages_fetched + 1)
        except Exception as exc:  # network details are serialized safely below
            listing_error = _sanitize_exception(exc)
            pagination_stop_reason = "listing_fetch_error"
            break
        pages_fetched += 1
        page_blocker = _security_block_reason(text)
        if page_blocker:
            blocker = page_blocker
            pagination_stop_reason = page_blocker
            break
        try:
            page = parse_listing_page(text, current_url)
            if page.unparsed_candidate_rows:
                raise ValueError("listing page contained unparsed candidate rows")
            if not page.entries and not _has_explicit_empty_state(text):
                raise ValueError("listing page contained no recognized rows")
            if page.next_url and not _same_registry_scope(
                start_url, page.next_url, fra_type_code
            ):
                raise ValueError("pagination left the requested registry scope")
        except Exception as exc:
            listing_error = _sanitize_exception(exc)
            pagination_stop_reason = "listing_parse_error"
            break
        listing_entries.extend(page.entries)
        current_url = page.next_url

    if blocker or listing_error or (pages_fetched == 0):
        _write_csv(csv_path, [])
        base_manifest["output_csv_sha256"] = _sha256_file(csv_path)
        base_manifest.update(
            status="blocked" if blocker else "partial",
            blocker=blocker,
            listing_error=listing_error,
            listing_pages_fetched=pages_fetched,
            listing_records_seen=len(listing_entries),
            pagination_stop_reason=pagination_stop_reason,
            raw_capture_count=len(raw_captures),
            raw_captures=raw_captures,
        )
        _write_manifest(manifest_path, base_manifest)
        return RegistryRunResult(csv_path, manifest_path, 2 if blocker else 1)

    unique_entries: list[ListingEntry] = []
    seen_urls: set[str] = set()
    duplicate_listing_count = 0
    for entry in listing_entries:
        key = _canonical_url(entry.detail_url)
        if key and key in seen_urls:
            duplicate_listing_count += 1
            continue
        if key:
            seen_urls.add(key)
        unique_entries.append(entry)

    rows: list[dict[str, str]] = []
    seen_company_numbers: set[str] = set()
    detail_attempted = 0
    detail_succeeded = 0
    detail_failed = 0
    detail_skipped = 0
    off_host_count = 0
    duplicate_company_number_count = 0
    stop_details = False

    for index, entry in enumerate(unique_entries, start=1):
        if stop_details:
            detail_skipped += 1
            rows.append(
                _technical_row(
                    entry,
                    start_url,
                    fra_type_code,
                    fra_type_ar,
                    run_date,
                    "AccessControlError: not attempted after security control",
                )
            )
            continue
        if not entry.detail_url or not _same_origin(start_url, entry.detail_url):
            off_host_count += 1
            detail_failed += 1
            rows.append(
                _technical_row(
                    entry,
                    start_url,
                    fra_type_code,
                    fra_type_ar,
                    run_date,
                    "AccessControlError: off-host detail URL",
                )
            )
            continue
        decision = access_for(entry.detail_url)
        if not is_authorized(decision):
            blocker = (
                "robots_disallowed" if decision.state == "disallowed" else "robots_unavailable"
            )
            stop_details = True
            detail_skipped += 1
            rows.append(
                _technical_row(
                    entry,
                    start_url,
                    fra_type_code,
                    fra_type_ar,
                    run_date,
                    "AccessControlError: path not authorized by robots policy",
                )
            )
            continue
        detail_attempted += 1
        try:
            _payload, text = retrieve(entry.detail_url, "detail", index)
            page_blocker = _security_block_reason(text)
            if page_blocker:
                blocker = page_blocker
                stop_details = True
                raise PermissionError("security control detected")
            detail = parse_detail_page(text)
            if not _same_identity(entry.company_name_ar, detail.company_name_ar):
                raise ValueError("detail identity did not match listing identity")
        except Exception as exc:
            exception_blocker = _access_exception_blocker(exc)
            if exception_blocker:
                blocker = exception_blocker
                stop_details = True
            detail_failed += 1
            rows.append(
                _technical_row(
                    entry,
                    start_url,
                    fra_type_code,
                    fra_type_ar,
                    run_date,
                    _sanitize_exception(exc),
                )
            )
            continue
        detail_succeeded += 1
        if detail.company_number and detail.company_number in seen_company_numbers:
            duplicate_company_number_count += 1
            continue
        if detail.company_number:
            seen_company_numbers.add(detail.company_number)
        rows.append(
            _complete_row(
                entry,
                detail,
                start_url,
                fra_type_code,
                fra_type_ar,
                run_date,
            )
        )

    incomplete_pagination = pagination_stop_reason != "end_of_results"
    status = "complete"
    if blocker:
        status = "blocked"
    elif detail_failed or incomplete_pagination:
        status = "partial"
    _write_csv(csv_path, rows)
    manifest = {
        **base_manifest,
        "status": status,
        "blocker": blocker,
        "listing_pages_fetched": pages_fetched,
        "listing_records_seen": len(listing_entries),
        "unique_company_count": len(rows),
        "duplicate_listing_count": duplicate_listing_count,
        "duplicate_company_number_count": duplicate_company_number_count,
        "detail_fetch_attempted": detail_attempted,
        "detail_fetch_succeeded": detail_succeeded,
        "detail_fetch_failed": detail_failed,
        "detail_skipped_after_blocker": detail_skipped,
        "off_host_detail_count": off_host_count,
        "complete_row_count": sum(row["scrape_status"] == "complete" for row in rows),
        "technical_error_row_count": sum(
            row["scrape_status"] == "technical_error" for row in rows
        ),
        "csv_row_count": len(rows),
        "pagination_stop_reason": pagination_stop_reason,
        "raw_capture_count": len(raw_captures),
        "raw_captures": raw_captures,
        "robots_checked_url_count": len(access_cache),
        "manual_review_required": bool(blocker),
        "output_csv_sha256": _sha256_file(csv_path),
    }
    _write_manifest(manifest_path, manifest)
    exit_code = 0 if status == "complete" else (2 if status == "blocked" else 1)
    return RegistryRunResult(csv_path, manifest_path, exit_code)


class _SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        resolved = urllib.parse.urljoin(req.full_url, newurl)
        if not _same_origin(req.full_url, resolved):
            raise PermissionError("redirect left the authorized origin")
        return super().redirect_request(req, fp, code, msg, headers, resolved)


def fetch_url(url: str, timeout_seconds: float, *, user_agent: str = USER_AGENT) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    opener = urllib.request.build_opener(_SameOriginRedirectHandler())
    with opener.open(request, timeout=timeout_seconds) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("response exceeded maximum allowed size")
    return payload


def check_robots_access(url: str, timeout_seconds: float) -> AccessDecision:
    return load_robots_policy(url, timeout_seconds).decision_for(url)


def load_robots_policy(
    url: str, timeout_seconds: float, *, user_agent: str = USER_AGENT
) -> RobotsPolicy:
    parsed = urllib.parse.urlparse(url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    try:
        payload = fetch_url(robots_url, timeout_seconds, user_agent=user_agent)
    except urllib.error.HTTPError as exc:
        return RobotsPolicy("unavailable", f"robots.txt HTTP {exc.code}", robots_url)
    except Exception as exc:
        return RobotsPolicy("unavailable", _sanitize_exception(exc), robots_url)
    text = _decode_html(payload)
    if _security_block_reason(text) or not re.search(
        r"(?im)^\s*(?:user-agent|allow|disallow|crawl-delay)\s*:", text
    ):
        return RobotsPolicy(
            "unavailable",
            "robots.txt did not return robots directives",
            robots_url,
            payload=payload,
        )
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(text.splitlines())
    crawl_delay = parser.crawl_delay(user_agent) or parser.crawl_delay("*") or 0
    return RobotsPolicy(
        "allowed",
        "robots.txt directives loaded",
        robots_url,
        payload=payload,
        parser=parser,
        crawl_delay=float(crawl_delay),
        user_agent=user_agent,
    )


def _complete_row(
    entry: ListingEntry,
    detail: CompanyDetail,
    start_url: str,
    fra_type_code: str,
    fra_type_ar: str,
    run_date: str,
) -> dict[str, str]:
    activities: str
    if detail.activities:
        activities = json.dumps(
            [
                {
                    "activity_ar": activity.activity_ar,
                    "activity_date": activity.activity_date or NO_DATA,
                }
                for activity in detail.activities
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    else:
        activities = NO_DATA
    return {
        "regulator": REGULATOR,
        "registry_name_ar": REGISTRY_NAME_AR,
        "fra_type_code": fra_type_code,
        "fra_type_ar": fra_type_ar,
        "company_name_ar": detail.company_name_ar or entry.company_name_ar,
        "company_name_en": detail.company_name_en or NO_DATA,
        "company_number": detail.company_number or NO_DATA,
        "address": detail.address or NO_DATA,
        "license_number": detail.license_number or NO_DATA,
        "activities_json": activities,
        "license_date": detail.license_date or entry.license_date or NO_DATA,
        "company_detail_url": entry.detail_url or NO_DATA,
        "registry_listing_url": entry.listing_url or start_url,
        "scraped_at": run_date,
        "scrape_status": "complete",
        "scrape_error": "",
    }


def _technical_row(
    entry: ListingEntry,
    start_url: str,
    fra_type_code: str,
    fra_type_ar: str,
    run_date: str,
    error: str,
) -> dict[str, str]:
    return {
        "regulator": REGULATOR,
        "registry_name_ar": REGISTRY_NAME_AR,
        "fra_type_code": fra_type_code,
        "fra_type_ar": fra_type_ar,
        "company_name_ar": entry.company_name_ar,
        "company_name_en": TECHNICAL_ERROR,
        "company_number": TECHNICAL_ERROR,
        "address": TECHNICAL_ERROR,
        "license_number": TECHNICAL_ERROR,
        "activities_json": TECHNICAL_ERROR,
        "license_date": entry.license_date or TECHNICAL_ERROR,
        "company_detail_url": entry.detail_url or TECHNICAL_ERROR,
        "registry_listing_url": entry.listing_url or start_url,
        "scraped_at": run_date,
        "scrape_status": "technical_error",
        "scrape_error": error,
    }


def _write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(
                {
                    field: _excel_safe_cell(str(row.get(field, "")))
                    for field in CSV_FIELDS
                }
                for row in rows
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _manifest_base(
    *,
    start_url: str,
    fra_type_code: str,
    fra_type_ar: str,
    run_date: str,
    csv_path: Path,
    access: AccessDecision,
    acknowledged: bool,
    site_terms_review_state: str,
) -> dict[str, object]:
    return {
        "mode": "fra_typed_registry",
        "status": "pending",
        "run_date": run_date,
        "regulator": REGULATOR,
        "registry_name_ar": REGISTRY_NAME_AR,
        "fra_type_code": fra_type_code,
        "fra_type_ar": fra_type_ar,
        "registry_listing_url": start_url,
        "robots_state": access.state,
        "robots_reason": access.reason,
        "robots_unavailable_acknowledged": acknowledged,
        "site_terms_review_state": site_terms_review_state,
        "listing_pages_fetched": 0,
        "listing_records_seen": 0,
        "unique_company_count": 0,
        "duplicate_listing_count": 0,
        "duplicate_company_number_count": 0,
        "detail_fetch_attempted": 0,
        "detail_fetch_succeeded": 0,
        "detail_fetch_failed": 0,
        "detail_skipped_after_blocker": 0,
        "off_host_detail_count": 0,
        "complete_row_count": 0,
        "technical_error_row_count": 0,
        "csv_row_count": 0,
        "pagination_stop_reason": "not_started",
        "raw_capture_count": 0,
        "raw_captures": [],
        "robots_checked_url_count": 0,
        "manual_review_required": False,
        "access_status_taxonomy": (
            "allowed|robots_unavailable|robots_disallowed|blocked_by_security|"
            "requires_login|document_not_public|rate_limited"
        ),
        "output_csv": str(csv_path).replace("\\", "/"),
        "output_csv_sha256": "",
        "scope_boundary": (
            "Official FRA registry identity facts only; no Sharia compliance decision "
            "or runtime eligibility is created by this export."
        ),
    }


def _company_name_from_row(row: list[_Cell]) -> str:
    for cell in row:
        value = cell.text
        if (
            _has_letter(value)
            and not _is_date(value)
            and value not in {"اسم الشركة", "تاريخ الترخيص", "عرض", "التفاصيل"}
        ):
            return value
    return ""


def _is_company_detail_href(href: str) -> bool:
    path = urllib.parse.urlparse(href).path.lower()
    return "/company_records/" in path or "/company-records/" in path


def _same_origin(first: str, second: str) -> bool:
    first_parsed = urllib.parse.urlparse(first)
    second_parsed = urllib.parse.urlparse(second)
    first_host = (first_parsed.hostname or "").lower().removeprefix("www.")
    second_host = (second_parsed.hostname or "").lower().removeprefix("www.")
    first_port = first_parsed.port or (443 if first_parsed.scheme.lower() == "https" else 80)
    second_port = second_parsed.port or (443 if second_parsed.scheme.lower() == "https" else 80)
    return bool(
        first_host
        and first_host == second_host
        and first_parsed.scheme.lower() == second_parsed.scheme.lower() == "https"
        and first_port == second_port == 443
        and first_parsed.username is None
        and first_parsed.password is None
        and second_parsed.username is None
        and second_parsed.password is None
    )


def _same_registry_scope(start_url: str, candidate_url: str, fra_type_code: str) -> bool:
    if not _same_origin(start_url, candidate_url):
        return False
    start = urllib.parse.urlparse(start_url)
    candidate = urllib.parse.urlparse(candidate_url)
    start_path = start.path.rstrip("/")
    if start_path and not candidate.path.rstrip("/").startswith(start_path):
        return False
    candidate_query = dict(
        urllib.parse.parse_qsl(candidate.query, keep_blank_values=True)
    )
    candidate_type = candidate_query.get("filtered_type")
    return candidate_type in {None, "", fra_type_code}


def _canonical_url(url: str) -> str:
    parsed = urllib.parse.urlparse(urllib.parse.urldefrag(url)[0])
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    query = urllib.parse.urlencode(
        sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)), doseq=True
    )
    return urllib.parse.urlunparse(
        (scheme, netloc, parsed.path or "/", parsed.params, query, "")
    )


def _decode_html(payload: bytes) -> str:
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        header = payload[:4096].decode("latin-1", errors="ignore")
        match = re.search(r"(?i)charset\s*=\s*['\"]?([a-z0-9._-]+)", header)
        if not match:
            raise
        encoding = match.group(1).lower()
        if encoding not in {"windows-1256", "cp1256", "iso-8859-6"}:
            raise
        return payload.decode(encoding)


def _security_block_reason(text: str) -> Optional[str]:
    parser = _VisibleTextParser()
    parser.feed(text)
    lowered = parser.text.lower()
    categories = (
        ("requires_login", ("login required", "log in to continue", "sign in to continue")),
        ("document_not_public", ("paywall", "subscription required")),
        (
            "blocked_by_security",
            (
                "captcha",
                "access denied",
                "request rejected",
                "requested url was rejected",
                "verify you are human",
                "just a moment",
                "forbidden",
            ),
        ),
    )
    for category, markers in categories:
        if any(marker in lowered for marker in markers):
            return category
    return None


def _has_explicit_empty_state(text: str) -> bool:
    parser = _VisibleTextParser()
    parser.feed(text)
    normalized = parser.text.lower()
    return any(
        marker in normalized
        for marker in (
            "no results found",
            "no records found",
            "لا توجد نتائج",
            "لا توجد بيانات",
            "لا يوجد بيانات",
        )
    )


def _access_exception_blocker(exc: Exception) -> Optional[str]:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 401:
            return "requires_login"
        if exc.code == 403:
            return "blocked_by_security"
        if exc.code == 429:
            return "rate_limited"
    if isinstance(exc, PermissionError):
        return "blocked_by_security"
    return None


def _sanitize_exception(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "TimeoutError: request timed out"
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTPError: HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return "URLError: request failed"
    if isinstance(exc, PermissionError):
        return "PermissionError: security control detected"
    if isinstance(exc, ValueError):
        return "ValueError: response could not be parsed"
    return f"{type(exc).__name__}: request failed"


def _same_identity(listing_name: str, detail_name: Optional[str]) -> bool:
    if not detail_name:
        return False
    return _identity_key(listing_name) == _identity_key(detail_name)


def _identity_key(value: str) -> str:
    return re.sub(r"[^\w\u0600-\u06ff]+", "", _clean_text(value).casefold())


def _excel_safe_cell(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _normalize_label(value: str) -> str:
    value = value.replace("ـ", "")
    return re.sub(r"\s+", " ", value).strip().lower()


def _is_english_name_label(label: str) -> bool:
    return any(
        marker in label
        for marker in (
            "english name",
            "name in english",
            "اسم الشركة بالانجليزية",
            "اسم الشركة باللغة الإنجليزية",
            "الاسم باللغة الإنجليزية",
        )
    )


def _is_company_name_label(label: str) -> bool:
    return label in {"اسم الشركة", "اسم الشركه", "الاسم باللغة العربية", "arabic name"}


def _is_company_number_label(label: str) -> bool:
    return label in {"رقم الشركة", "رقم الشركه", "company number"}


def _is_address_label(label: str) -> bool:
    return label in {"العنوان", "address"}


def _is_license_number_label(label: str) -> bool:
    return label in {"رقم الترخيص", "license number", "licence number"}


def _is_activity_label(label: str) -> bool:
    return label in {"النشاط", "اسم النشاط", "licensed activity", "activity"}


def _is_activity_date_label(label: str) -> bool:
    return label in {"تاريخ مزاولة النشاط", "activity date", "licensed activity date"}


def _is_license_date_label(label: str) -> bool:
    return label in {"تاريخ الترخيص", "license date", "licence date"}


def _is_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value.strip()))


def _has_letter(value: str) -> bool:
    return any(character.isalpha() for character in value)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "registry"
