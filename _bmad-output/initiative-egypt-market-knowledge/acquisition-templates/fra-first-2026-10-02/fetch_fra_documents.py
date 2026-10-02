"""Retrieve FRA publications: guides, contract models, legislation, Sharia material.

Scope: fra-access-decision.md. One request at a time, identified research user
agent, >=3 s apart, stop on any security/login page. From each seed page the
crawler follows (a) same-host pagination of that page (``/page/N/``) and
(b) same-host PDF links, either all of them (``--all-pdfs``) or only those whose
URL/link text matches HINTS. No other HTML pages are followed. Raw bytes are
stored by SHA-256; the manifest is append-only. Run from the repository root.

    python fetch_fra_documents.py --set sharia --all-pdfs
    python fetch_fra_documents.py <url> [<url> ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.acquisition.egypt_financial.fra_registry import (  # noqa: E402
    USER_AGENT,
    _security_block_reason,
    fetch_url,
)

OUT = ROOT / "data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02"
LEGISLATION = (
    "https://fra.gov.eg/en/%D8%AA%D8%B4%D8%B1%D9%8A%D8%B9%D8%A7%D8%AA-%D8%A3%D9%86%D8%B4%D8%B7%D8%A9-"
    "%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84%D9%8A-%D8%BA%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D8%B5%D8%B1%D9%81%D9%8A-2/"
)
SEED_SETS = {
    "consumer": [
        ("consumer_finance_rules_guide_page",
         "https://fra.gov.eg/%D8%AF%D9%84%D9%8A%D9%84-%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF-%D9%88%D8%A7%D9%84%D8%B6%D9%88%D8%A7%D8%A8%D8%B7-%D9%88%D8%A7%D9%84%D9%85%D8%B9%D8%A7%D9%8A%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D9%86/"),
        ("customer_protection_guide_pdf",
         "https://fra.gov.eg/wp-content/uploads/2025/09/%D8%AF%D9%84%D9%8A%D9%84-%D8%AD%D9%85%D8%A7%D9%8A%D8%A9-%D8%A7%D9%84%D8%B9%D9%85%D9%84%D8%A7%D8%A1-2020-7.pdf"),
        ("consumer_finance_safe_dealing_guide_page",
         "https://fra.gov.eg/en/consumers_awareness/%D8%AF%D9%84%D9%8A%D9%84-%D8%A7%D9%84%D8%AA%D8%B9%D8%A7%D9%85%D9%84-%D8%A7%D9%84%D8%A3%D9%85%D9%86-%D9%81%D9%89-%D9%86%D8%B4%D8%A7%D8%B7-%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84-%D8%A7%D9%84%D8%A7/"),
        ("non_bank_legislation_index_page", LEGISLATION),
    ],
    # Contract models live inside each activity's rules guide and in the
    # activity's legislation listing (decrees fixing minimum contract terms).
    "templates": [
        ("factoring_rules_guide_2021", "https://fra.gov.eg/wp-content/uploads/2021/12/Takhseem2021.pdf"),
        ("mortgage_rules_guide",
         "https://fra.gov.eg/wp-content/uploads/2021/06/%D8%AF%D9%84%D9%8A%D9%84-%D8%A7%D9%84%D8%B6%D9%88%D8%A7%D8%A8%D8%B7-%D9%88%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF-%D9%88%D8%A7%D9%84%D9%85%D8%B9%D8%A7%D9%8A%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9-%D9%84%D8%B9%D9%85%D9%84-%D8%B4%D8%B1%D9%83%D8%A7%D8%AA-%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84-%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1%D9%8A-mmt2.pdf"),
        ("legislation_consumer_finance", "filter:consumer"),
        ("legislation_factoring", "filter:factoring"),
        ("legislation_leasing", "filter:leasing"),
        ("legislation_real_estate_finance", "filter:mortgage"),
        ("legislation_sme_micro", "filter:sme"),
    ],
    "sharia": [
        ("islamic_finance_non_bank_page",
         "https://fra.gov.eg/en/%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84-%D8%A7%D9%84%D8%A5%D8%B3%D9%84%D8%A7%D9%85%D9%8A-%D9%84%D9%84%D8%A3%D9%86%D8%B4%D8%B7%D8%A9-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%8A%D8%A9-%D8%BA%D9%8A%D8%B1/"),
        ("central_sharia_committee_decisions_page",
         "https://fra.gov.eg/en/%D9%82%D8%B1%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D8%AC%D9%86%D8%A9-%D8%A7%D9%84%D8%B1%D9%82%D8%A7%D8%A8%D9%87-%D8%A7%D9%84%D8%B4%D8%B1%D8%B9%D9%8A%D8%A9-%D8%A7%D9%84%D9%85%D8%B1%D9%83%D8%B2%D9%8A%D8%A9/"),
        ("sukuk_page", "https://fra.gov.eg/en/%D8%A7%D9%84%D8%B5%D9%83%D9%88%D9%83/"),
        ("islamic_investment_funds_page",
         "https://fra.gov.eg/en/%D8%B5%D9%86%D8%A7%D8%AF%D9%8A%D9%82-%D8%A7%D9%84%D8%A7%D8%B3%D8%AA%D8%AB%D9%85%D8%A7%D8%B1-%D8%A7%D9%84%D8%A5%D8%B3%D9%84%D8%A7%D9%85%D9%8A%D8%A9/"),
        ("islamic_products_and_contracts_page_en",
         "https://fra.gov.eg/en/المنتجات-الإسلامية-للأنشطة-المالية-غ/"),
        ("islamic_products_and_contracts_page_ar", "https://fra.gov.eg/المنتجات-الإسلامية-للأنشطة-المالية-غ/"),
        ("islamic_finance_non_bank_page_ar", "https://fra.gov.eg/التمويل-الإسلامي-للأنشطة-المالية-غير/"),
        ("sub_sharia_committees_registry_page", "https://fra.gov.eg/en/سجل-لجنه-الرقابة-الشرعية-الفرعية/"),
        ("sub_sharia_committees_registry_page_ar", "https://fra.gov.eg/سجل-لجنه-الرقابة-الشرعية-الفرعية/"),
        ("takaful_page", "https://fra.gov.eg/en/التأمين-التكافلي/"),
        ("egyptian_sukuk_experience_pdf",
         "https://fra.gov.eg/wp-content/uploads/2024/10/%D8%A7%D9%84%D8%AA%D8%AC%D8%B1%D8%A8%D9%87-%D8%A7%D9%84%D9%85%D8%B5%D8%B1%D9%8A%D8%A9-%D9%81%D9%8A-%D8%A7%D9%84%D8%B5%D9%83%D9%88%D9%83.pdf"),
    ],
}
# Legislation-listing filters are discovered from the saved legislation page
# (link text "Consumer Finance Legislation", etc.) rather than guessed.
FILTER_TEXT = {
    "consumer": "Consumer Finance Legislation",
    "factoring": "Factoring Legislation",
    "leasing": "Leasing Legislation",
    "mortgage": "Real Estate Finance Legislation",
    "sme": "Legislation for Small, Medium, and Micro Enterprises",
}
HINTS = ("استهلاك", "عقد", "عقود", "نموذج", "نماذج", "حماية", "دليل", "شرع", "إسلام", "اسلام", "صكوك",
         "مرابح", "إجار", "اجار", "مشارك", "مضارب", "تكافل", "consumer", "contract", "model", "guide",
         "sharia", "shariah", "islamic", "sukuk", "takaful", "18-لسنة-2020")
DELAY = 3.0


def ascii_url(url: str) -> str:
    """Percent-encode raw Arabic paths so the request is valid ASCII."""
    parts = urllib.parse.urlsplit(url.replace("&#038;", "&"))
    return urllib.parse.urlunsplit(
        parts._replace(path=urllib.parse.quote(parts.path, safe="/%"),
                       query=urllib.parse.quote(parts.query, safe="=&%"))
    )


def same_host(url: str) -> bool:
    return (urllib.parse.urlparse(url).hostname or "").removeprefix("www.") == "fra.gov.eg"


def resolve_filter(name: str) -> str:
    recs = [json.loads(line) for line in (OUT / "fra-documents-manifest.jsonl").open(encoding="utf-8")]
    page = next(r for r in recs if r["label"] == "non_bank_legislation_index_page" and r.get("raw"))
    html = (ROOT / page["raw"]).read_text(encoding="utf-8", errors="replace")
    for href, inner in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        if re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip() == FILTER_TEXT[name]:
            return ascii_url(urllib.parse.urljoin(LEGISLATION, href))
    raise LookupError(f"legislation filter not found: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--set", choices=sorted(SEED_SETS), action="append", default=[])
    parser.add_argument("--all-pdfs", action="store_true", help="follow every same-host PDF on seed pages")
    parser.add_argument("--max-pdfs", type=int, default=60)
    parser.add_argument("--max-pages", type=int, default=8, help="pagination pages per seed")
    args = parser.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "fra-documents-manifest.jsonl"
    done: dict[str, dict] = {}
    never_again: set[str] = set()  # drew a security page or exceeded the size cap
    if manifest_path.exists():
        for line in manifest_path.open(encoding="utf-8"):
            rec = json.loads(line)
            if rec.get("outcome") == "captured":
                done[rec["url"]] = rec
            elif rec.get("outcome") == "stopped" or "maximum allowed size" in rec.get("error", ""):
                never_again.add(rec["url"])
    queue: list[tuple[str, str, int]] = []
    for name in args.set:
        for label, url in SEED_SETS[name]:
            url = resolve_filter(url.split(":", 1)[1]) if url.startswith("filter:") else ascii_url(url)
            queue.append((label, url, 0))
    queue += [(f"named:{i}", ascii_url(url), 0) for i, url in enumerate(args.urls, 1)]
    seen: set[str] = set()
    pdfs_followed = 0
    counts = {"captured": 0, "skipped_already_captured": 0, "failed": 0}
    with manifest_path.open("a", encoding="utf-8") as log:
        while queue:
            label, url, depth = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if url in never_again:
                counts["skipped_gap_recorded"] = counts.get("skipped_gap_recorded", 0) + 1
                continue
            if url in done:
                counts["skipped_already_captured"] += 1
                saved = done[url]
                if saved.get("kind") == "html":  # re-read from disk, no request, to queue its links
                    for link in saved.get("linked_pdfs") or []:
                        if pdfs_followed < args.max_pdfs and link["href"] not in seen:
                            queue.append((f"{label}:pdf|{link['text'][:80]}", link["href"], depth))
                            pdfs_followed += 1
                continue
            record = {"label": label, "url": url, "requested_at": datetime.now(timezone.utc).isoformat(),
                      "user_agent": USER_AGENT, "route": "bounded FRA publication retrieval"}
            try:
                payload = fetch_url(url, 40)
            except Exception as exc:  # recorded, never retried under another identity
                record.update(outcome="failed", error=f"{type(exc).__name__}: {str(exc)[:120]}")
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                counts["failed"] += 1
                print(f"failed   {label}: {record['error']}")
                time.sleep(DELAY)
                continue
            digest = hashlib.sha256(payload).hexdigest()
            is_pdf = payload[:5] == b"%PDF-"
            path = OUT / "raw" / f"{digest}.{'pdf' if is_pdf else 'html'}"
            path.parent.mkdir(exist_ok=True)
            if not path.exists():
                path.write_bytes(payload)
            record.update(outcome="captured", bytes=len(payload), sha256=digest, kind="pdf" if is_pdf else "html",
                          raw=path.relative_to(ROOT).as_posix())
            if not is_pdf:
                text = payload.decode("utf-8", errors="replace")
                blocker = _security_block_reason(text)
                if blocker:
                    record.update(outcome="stopped", blocker=blocker)
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    print(f"STOP {label}: {blocker}")
                    return 2
                title = re.search(r"<title>(.*?)</title>", text, re.S)
                record["title"] = (title.group(1).strip() if title else "")[:200]
                links = []
                for href, inner in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S | re.I):
                    absolute = ascii_url(urllib.parse.urljoin(url, href))
                    link_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip()[:200]
                    if not same_host(absolute):
                        continue
                    path_l = urllib.parse.urlparse(absolute).path.lower()
                    if path_l.endswith(".pdf"):
                        readable = urllib.parse.unquote(absolute) + " " + link_text
                        if args.all_pdfs or any(h in readable for h in HINTS):
                            links.append({"href": absolute, "text": link_text})
                    elif depth < args.max_pages and re.search(r"/page/\d+/?$", path_l) and \
                            urllib.parse.urlparse(absolute).path.rsplit("/page/", 1)[0].rstrip("/") == \
                            urllib.parse.urlparse(url).path.split("/page/")[0].rstrip("/"):
                        queue.append((f"{label}:page", absolute, depth + 1))
                record["linked_pdfs"] = links
                for link in links:
                    if pdfs_followed < args.max_pdfs and link["href"] not in seen:
                        queue.append((f"{label}:pdf|{link['text'][:80]}", link["href"], depth))
                        pdfs_followed += 1
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts["captured"] += 1
            print(f"captured {record['kind']:4} {record['bytes']:>9} {label[:90]}")
            time.sleep(DELAY)
    print(json.dumps({**counts, "pdfs_queued": pdfs_followed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
