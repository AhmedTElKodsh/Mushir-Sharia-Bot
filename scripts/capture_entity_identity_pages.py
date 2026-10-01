"""Capture explicitly approved public identity/documents into an immutable run.

Usage: python scripts/capture_entity_identity_pages.py URLS_FILE --decisions JSON
       --output-root DIRECTORY [--run-id UNIQUE_ID]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.acquisition.public_capture import PublicCollector, load_decisions

LEGAL = re.compile(r"[^<>\n]{0,80}(?:S\.?A\.?E|S\.A\.M|ش\.?\s?م\.?\s?م|ش\.?\s?م\.?\s?م\.?\s?م|للتمويل الاستهلاكي|Consumer Finance|©|Copyright|حقوق)[^<>\n]{0,80}", re.I)
LICENCE = re.compile(r"[^<>\n]{0,60}(?:ترخيص|رخصة|licen[cs]e|FRA|الهيئة العامة للرقابة المالية|Financial Regulatory Authority)[^<>\n]{0,60}", re.I)


def text_of(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"[ \t\r\f\v]+", " ", unescape(re.sub(r"(?s)<[^>]+>", "\n", html)))


def extract(html):
    def meta(prop):
        m = re.search(rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]*content=["\']([^"\']*)', html, re.I)
        return unescape(m.group(1)).strip() if m else None
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    lang = re.search(r'(?i)<html[^>]*\blang=["\']([^"\']+)', html)
    alt = re.findall(r'(?i)<link[^>]+hreflang=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)', html)
    txt = text_of(html)
    uniq = lambda xs: list(dict.fromkeys(x.strip() for x in xs if x.strip()))[:12]
    observations, truncated = [], False
    for kind, pattern in (("legal_name_candidate", LEGAL), ("licence_candidate", LICENCE)):
        seen = set()
        for match in pattern.finditer(txt):
            literal = match.group().strip()
            if not literal or literal in seen:
                continue
            if len(seen) >= 12:
                truncated = True
                break
            seen.add(literal)
            start = match.start() + len(match.group()) - len(match.group().lstrip())
            observations.append({"kind": kind, "text": literal, "start": start, "end": start + len(literal),
                                 "source_pointer": "/literal_identity/source_text"})
    return {"title": unescape(title.group(1)).strip() if title else None, "html_lang": lang.group(1) if lang else None,
            "og_site_name": meta("og:site_name"), "og_title": meta("og:title"), "hreflang": alt[:6],
            "legal_name_lines": uniq(LEGAL.findall(txt)), "licence_lines": uniq(LICENCE.findall(txt)),
            "source_text": txt, "source_text_sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest(),
            "offset_unit": "unicode_code_points", "observations": observations,
            "observations_truncated": truncated, "candidate_limit_per_kind": 12}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls_file", type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-requests", type=int, default=100)
    args = parser.parse_args(argv)
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", run_id):
        parser.error("run-id must be a simple unique name without path components")
    try:
        decisions = load_decisions(args.decisions)
        inputs = []
        for line in args.urls_file.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            label, url = line.split(None, 1)
            inputs.append((label, url.strip()))
        collector = PublicCollector(args.output_root / run_id, decisions, max_requests=args.max_requests)
        results = [collector.capture(label, url, extractor=extract) for label, url in inputs]
        summary = collector.finish(results)
        print(json.dumps({"output": str(collector.output), **summary}, ensure_ascii=False))
        return 0 if all(result["state"] == "captured" for result in results) else 2
    except (ValueError, TypeError, OSError) as exc:
        parser.exit(1, f"Capture configuration/output error: {type(exc).__name__}\n")


if __name__ == "__main__":
    raise SystemExit(main())
