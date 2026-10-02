"""Retrieve named FRA consumer-finance publications (manual route, logged).

Scope: the access decision in fra-access-decision.md. One request at a time,
identified research user agent, >=3 s apart, stop on any security/login page.
Seed pages may link PDFs; only same-host wp-content PDFs whose link text or
filename mentions consumer finance, contracts or customer protection are
followed, capped at MAX_PDFS.  Raw bytes are stored by SHA-256; nothing is
overwritten.  Run from the repository root.
"""

from __future__ import annotations

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
SEEDS = [
    ("consumer_finance_rules_guide_page",
     "https://fra.gov.eg/%D8%AF%D9%84%D9%8A%D9%84-%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF-%D9%88%D8%A7%D9%84%D8%B6%D9%88%D8%A7%D8%A8%D8%B7-%D9%88%D8%A7%D9%84%D9%85%D8%B9%D8%A7%D9%8A%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D9%86/"),
    ("customer_protection_guide_pdf",
     "https://fra.gov.eg/wp-content/uploads/2025/09/%D8%AF%D9%84%D9%8A%D9%84-%D8%AD%D9%85%D8%A7%D9%8A%D8%A9-%D8%A7%D9%84%D8%B9%D9%85%D9%84%D8%A7%D8%A1-2020-7.pdf"),
    ("consumer_finance_safe_dealing_guide_page",
     "https://fra.gov.eg/en/consumers_awareness/%D8%AF%D9%84%D9%8A%D9%84-%D8%A7%D9%84%D8%AA%D8%B9%D8%A7%D9%85%D9%84-%D8%A7%D9%84%D8%A3%D9%85%D9%86-%D9%81%D9%89-%D9%86%D8%B4%D8%A7%D8%B7-%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84-%D8%A7%D9%84%D8%A7/"),
    ("non_bank_legislation_index_page",
     "https://fra.gov.eg/en/%D8%AA%D8%B4%D8%B1%D9%8A%D8%B9%D8%A7%D8%AA-%D8%A3%D9%86%D8%B4%D8%B7%D8%A9-%D8%A7%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84%D9%8A-%D8%BA%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D8%B5%D8%B1%D9%81%D9%8A-2/"),
]
PDF_HINTS = ("استهلاك", "عقد", "عقود", "نموذج", "حماية", "consumer", "contract", "18-لسنة-2020", "18 لسنة 2020")
MAX_PDFS = 8
DELAY = 3.0


def _ascii_url(url: str) -> str:
    """Percent-encode raw Arabic paths so the request is valid ASCII."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        parts._replace(path=urllib.parse.quote(parts.path, safe="/%"),
                       query=urllib.parse.quote(parts.query, safe="=&%"))
    )


def main(argv: list[str] | None = None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "fra-documents-manifest.jsonl"
    extra = list(argv if argv is not None else sys.argv[1:])
    queue = [(f"named:{i}", _ascii_url(url)) for i, url in enumerate(extra, 1)] if extra else list(SEEDS)
    seen: set[str] = set()
    pdfs_followed = 0
    with manifest_path.open("a", encoding="utf-8") as log:
        while queue:
            label, url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            record = {"label": label, "url": url, "requested_at": datetime.now(timezone.utc).isoformat(),
                      "user_agent": USER_AGENT, "route": "manual public-document retrieval"}
            try:
                payload = fetch_url(url, 30)
            except Exception as exc:  # recorded, never retried under another identity
                record.update(outcome="failed", error=f"{type(exc).__name__}: {str(exc)[:120]}")
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                time.sleep(DELAY)
                continue
            digest = hashlib.sha256(payload).hexdigest()
            is_pdf = payload[:5] == b"%PDF-"
            path = OUT / "raw" / f"{digest}.{'pdf' if is_pdf else 'html'}"
            path.parent.mkdir(exist_ok=True)
            if not path.exists():
                path.write_bytes(payload)
            record.update(outcome="captured", bytes=len(payload), sha256=digest, kind="pdf" if is_pdf else "html",
                          raw=str(path.relative_to(ROOT)).replace("\\", "/"))
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
                for href, inner in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', text, re.S | re.I):
                    absolute = _ascii_url(urllib.parse.urljoin(url, href))
                    host = urllib.parse.urlparse(absolute).hostname or ""
                    readable = urllib.parse.unquote(absolute) + " " + re.sub(r"<[^>]+>", " ", inner)
                    if host.removeprefix("www.") == "fra.gov.eg" and any(h in readable for h in PDF_HINTS):
                        links.append({"href": absolute, "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip()[:160]})
                record["candidate_pdfs"] = links
                for link in links:
                    if pdfs_followed < MAX_PDFS and link["href"] not in seen:
                        queue.append((f"{label}:pdf", link["href"]))
                        pdfs_followed += 1
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{record['outcome']:8} {label:45} {record.get('kind','')} {record.get('bytes','')} {record.get('title','')[:60]}")
            time.sleep(DELAY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
