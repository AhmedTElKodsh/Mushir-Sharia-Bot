#!/usr/bin/env python3
"""Check a reviewed list of Egyptian instalment offers against public source pages.

This is an evidence collector, not a sales ranking or a Sharia classifier.  Each
input row names one claim and one exact public page.  A claim is verified only
when that page can be fetched and its required terms occur in visible text.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.acquisition.egypt_financial.fra_registry import USER_AGENT, load_robots_policy


DEFAULT_SEED = ROOT / "data/source_registry/egypt_installment_market.csv"
MAX_BYTES = 3 * 1024 * 1024
STAGES = ("product_market", "online_vendor", "direct_store", "services", "real_estate")
INPUT_FIELDS = (
    "stage", "category", "entity", "role", "vendor", "source_url",
    "required_terms", "claim", "ranking_metric", "ranking_period",
    "ranking_source_url",
)
OPTIONAL_INPUT_FIELDS = (
    "claim_scope", "commerce_mode", "payment_model", "financing_entity",
    "discovery_source_url", "offer_start", "offer_end",
)
OUTPUT_FIELDS = INPUT_FIELDS + OPTIONAL_INPUT_FIELDS + (
    "checked_at", "captured_at", "status", "availability_status", "evidence_snippet",
    "source_final_url", "raw_sha256", "raw_path", "access_note",
)


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.main_parts: list[str] = []
        self.main_depth = 0
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "script", "style", "noscript", "svg", "nav", "header", "footer"}:
            self.hidden += 1
        elif tag == "main" and not self.hidden:
            self.main_depth += 1
        elif tag == "img" and not self.hidden:
            alt = dict(attrs).get("alt")
            if alt and alt.strip():
                self.parts.append(alt.strip())
                if self.main_depth:
                    self.main_parts.append(alt.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "script", "style", "noscript", "svg", "nav", "header", "footer"} and self.hidden:
            self.hidden -= 1
        elif tag == "main" and self.main_depth:
            self.main_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.parts.append(data)
            if self.main_depth:
                self.main_parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.main_parts or self.parts)).strip()


def _safe_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ""
        if not host or host == "localhost" or host.endswith((".local", ".internal")):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass
        return parsed.scheme == "https" and parsed.username is None and parsed.password is None and parsed.port in (None, 443)
    except ValueError:
        return False


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme, (parsed.hostname or "").lower(), parsed.port or 443


def _fetch(url: str, timeout: float, policy_for=None) -> tuple[bytes, str]:
    """Follow only reviewed HTTPS redirects, checking robots at every target."""
    class NoRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirects())
    current = url
    for _ in range(6):
        request = urllib.request.Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            location = exc.headers.get("Location")
            if not location:
                raise ValueError("redirect without Location") from exc
            target = urllib.parse.urljoin(current, location)
            if not _safe_url(target) or _host(target) != _host(url):
                raise ValueError("cross-host or unsafe redirect") from exc
            if policy_for is None or not policy_for(target).allowed:
                raise ValueError("redirect target not allowed by robots policy") from exc
            current = target
            continue
        with response:
            if not _safe_url(response.url) or _host(response.url) != _host(url):
                raise ValueError("cross-host or unsafe response URL")
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise ValueError("non-HTML response")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("response exceeds byte limit")
            return body, response.url
    raise ValueError("too many redirects")


def _find_evidence(text: str, terms: str) -> str:
    """All groups must appear in one short passage; | gives alternatives."""
    max_span = 400
    folded = text.casefold()
    hits: list[tuple[int, int, int]] = []
    groups = terms.split(";")
    for group_index, group in enumerate(groups):
        alternatives = [part.strip().casefold() for part in group.split("|") if part.strip()]
        if not alternatives:
            return ""
        group_hits = 0
        for part in alternatives:
            start = 0
            while (pos := folded.find(part, start)) >= 0:
                hits.append((pos, pos + len(part), group_index))
                group_hits += 1
                start = pos + len(part)
        if not group_hits:
            return ""
    hits.sort()
    counts = [0] * len(groups)
    covered = left = 0
    for right, (_, _, group_index) in enumerate(hits):
        if counts[group_index] == 0:
            covered += 1
        counts[group_index] += 1
        while covered == len(groups):
            start = hits[left][0]
            if hits[right][0] - start <= max_span:
                end = max(hit[1] for hit in hits[left:right + 1])
                if end - start <= max_span:
                    return text[max(0, start - 80):min(len(text), end + 120)].strip()
            old_group = hits[left][2]
            counts[old_group] -= 1
            if counts[old_group] == 0:
                covered -= 1
            left += 1
    return ""


def _page_error(text: str) -> bool:
    head = text[:1000].casefold()
    return any(marker in head for marker in (
        "an error has occurred. please try again.",
        "access denied",
        "verify you are human",
        "captcha",
    ))


def _check_seed(row: dict[str, str]) -> None:
    if row["stage"] not in STAGES:
        raise ValueError(f"unknown stage: {row['stage']}")
    if not row["entity"].strip():
        raise ValueError("entity is required")
    if not row["source_url"]:
        if row["stage"] == "online_vendor" and row["role"] == "marketplace" and row["vendor"] == row["entity"] and not row["required_terms"]:
            return
        raise ValueError("only marketplace source gaps may omit a URL")
    if not row["required_terms"].strip():
        raise ValueError("required_terms are required for source URLs")
    if not _safe_url(row["source_url"]):
        raise ValueError(f"unsafe source URL: {row['source_url']}")
    if row["ranking_source_url"] and not _safe_url(row["ranking_source_url"]):
        raise ValueError("unsafe ranking source URL")


def run(
    seed_file: Path,
    output_dir: Path,
    checked_at: str,
    *,
    timeout: float = 15.0,
    delay: float = 1.0,
    stage: str | None = None,
    max_urls: int = 100,
    fetcher=_fetch,
    robots_loader=load_robots_policy,
) -> dict:
    with seed_file.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not set(INPUT_FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("seed CSV is missing required columns")
        seeds = [
            {field: row.get(field, "") or "" for field in INPUT_FIELDS + OPTIONAL_INPUT_FIELDS}
            for row in reader
        ]
    for row in seeds:
        _check_seed(row)
    if stage:
        seeds = [row for row in seeds if row["stage"] == stage]
    total_claims = len(seeds)
    # Page fetches are shared across claims, including across stages.
    urls = list(dict.fromkeys(row["source_url"] for row in seeds if row["source_url"]))[:max_urls]
    selected = [row for row in seeds if not row["source_url"] or row["source_url"] in urls]
    if (output_dir / "installment_evidence.csv").exists() or (output_dir / "manifest.json").exists():
        raise FileExistsError(f"refusing to overwrite an existing crawl: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    policies: dict[tuple[str, str, int], object] = {}
    pages: dict[str, dict[str, str]] = {}

    def policy_for(url: str):
        origin = _origin(url)
        if origin not in policies:
            policies[origin] = robots_loader(url, timeout, user_agent=USER_AGENT)
        return policies[origin].decision_for(url)

    for index, url in enumerate(urls, 1):
        decision = policy_for(url)
        policy = policies[_origin(url)]
        page = {
            "status": "", "text": "", "raw_sha256": "", "raw_path": "",
            "access_note": "", "source_final_url": "", "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if not decision.allowed:
            page.update(status="robots_" + decision.state, access_note=decision.reason)
            pages[url] = page
            continue
        try:
            fetched = fetcher(url, timeout, policy_for) if fetcher is _fetch else fetcher(url, timeout)
            body, final_url = fetched if isinstance(fetched, tuple) else (fetched, url)
            parser = VisibleText()
            parser.feed(body.decode("utf-8", errors="replace"))
            digest = hashlib.sha256(body).hexdigest()
            raw_path = raw_dir / f"{index:03d}-{digest[:16]}.html"
            raw_path.write_bytes(body)
            page.update(status="fetched", text=parser.text(), raw_sha256="sha256:" + digest,
                        raw_path=str(raw_path), source_final_url=final_url)
        except urllib.error.HTTPError as exc:
            state = "blocked_by_security" if exc.code in {401, 403, 429} else "http_error"
            page.update(status=state, access_note=f"HTTP {exc.code}")
        except ValueError as exc:
            page.update(status="fetch_error", access_note=str(exc))
        except Exception as exc:
            # Do not emit URL-bearing exception strings, which can include tokens.
            page.update(status="fetch_error", access_note=type(exc).__name__)
        pages[url] = page
        if delay and index < len(urls):
            time.sleep(max(delay, getattr(policy, "crawl_delay", 0.0)))
    results: list[dict[str, str]] = []
    for row in selected:
        if row["source_url"]:
            page = pages[row["source_url"]]
            if page["status"] == "fetched":
                if _page_error(page["text"]):
                    status, snippet = "page_error", ""
                else:
                    snippet = _find_evidence(page["text"], row["required_terms"])
                    status = "verified_page_evidence" if snippet else "claim_not_found"
            else:
                status, snippet = page["status"], ""
        else:
            status, snippet = "no_public_source_identified", ""
            page = {"captured_at": "", "source_final_url": "", "raw_sha256": "", "raw_path": "",
                    "access_note": "No reviewed Egypt-specific public instalment page identified"}
        results.append({
            **row,
            "checked_at": checked_at,
            "captured_at": page["captured_at"],
            "status": status,
            "availability_status": (
                "out_of_stock"
                if row["claim_scope"] == "seller_product" and re.search(r"currently unavailable|out of stock|sold out", snippet, re.I)
                else "not_checked"
            ),
            "evidence_snippet": snippet,
            "source_final_url": page["source_final_url"],
            "raw_sha256": page["raw_sha256"],
            "raw_path": page["raw_path"],
            "access_note": page["access_note"],
        })
    captures_path = output_dir / "page_captures.jsonl"
    with captures_path.open("w", encoding="utf-8") as handle:
        for url, page in pages.items():
            handle.write(json.dumps({"source_url": url, **{key: value for key, value in page.items() if key != "text"}}, ensure_ascii=False) + "\n")
    csv_path = output_dir / "installment_evidence.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    counts = {name: sum(row["status"] == name for row in results) for name in sorted({r["status"] for r in results})}
    coverage = {
        category: {
            "requested_top_n": 20,
            "distinct_entities_with_page_evidence": len({r["entity"] for r in results if r["stage"] == "product_market" and r["category"] == category and r["status"] == "verified_page_evidence"}),
            "ranked_top_20_verified": False,
            "reason": "Comparable Egypt category sales and company financial metrics were not established for 20 entities.",
        }
        for category in ("laptops", "mobile_phones", "cars")
    }
    manifest = {
        "checked_at": checked_at,
        "stage_filter": stage or "all",
        "claim_count": len(results),
        "omitted_claim_count_due_to_url_limit": total_claims - len(results),
        "distinct_page_count": len(urls),
        "status_counts": counts,
        "output_csv": str(csv_path),
        "output_csv_sha256": "sha256:" + hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "page_captures_jsonl": str(captures_path),
        "scope_note": "Page evidence does not establish market rank, lender identity, contract terms, or Sharia compliance.",
    }
    if stage in {None, "product_market"}:
        manifest["product_market_coverage"] = coverage
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-urls", type=int, default=100)
    args = parser.parse_args()
    date.fromisoformat(args.today)
    if args.timeout_seconds <= 0 or args.delay_seconds < 0 or args.max_urls <= 0:
        parser.error("timeout and max-urls must be positive; delay must be nonnegative")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    output = args.output_dir or ROOT / "data/runtime/artifacts/l6_scrape/installment_market" / args.today / (args.stage or "all") / run_id
    manifest = run(args.seed_file, output, args.today, timeout=args.timeout_seconds, delay=args.delay_seconds, stage=args.stage, max_urls=args.max_urls)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
