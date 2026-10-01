"""Robots-respecting capture of entity-identity pages (FRA detail + financier sites).

Usage: .venv/Scripts/python scripts/capture_entity_identity_pages.py URLS_FILE  (lines: "<label> <url>")

Stores raw bytes with sha256 and a JSONL manifest. Extracts only literal name
strings as they appear (title, og:site_name, legal-name lines); never translates.
"""
import hashlib, json, re, sys, time, urllib.robotparser
from datetime import datetime, UTC
from html import unescape
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
sys.path.insert(0, ".")
from src.acquisition.url_safety import ensure_public_url

UA = "MushirResearchBot/0.1 (+public-source compliance research; contact: local)"
OUT = Path("data/runtime/artifacts/l6_scrape/entity_resolution/2026-10-01")
RAW = OUT / "raw"; RAW.mkdir(parents=True, exist_ok=True)
robots_cache = {}


def robots_ok(url):
    p = urlparse(url); base = f"{p.scheme}://{p.netloc}"
    if base not in robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=15)
            if r.status_code >= 500:
                robots_cache[base] = ("robots_unavailable", None)
            elif r.status_code == 200 and not re.search(r"(?im)^\s*(?:user-agent|allow|disallow|crawl-delay)\s*:", r.text):
                robots_cache[base] = ("robots_unavailable", None)  # project rule: no directives = unavailable
            else:
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                robots_cache[base] = ("ok", rp)
        except requests.RequestException as e:
            robots_cache[base] = ("robots_unavailable", None)
    state, rp = robots_cache[base]
    if state != "ok":
        return False, state
    return (True, "allowed") if rp.can_fetch(UA, url) else (False, "robots_disallowed")


def fetch(url, hops=5):
    for _ in range(hops + 1):
        ok, why = robots_ok(url)
        if not ok:
            return None, url, why
        ensure_public_url(url)
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"}, timeout=25, allow_redirects=False)
        if r.is_redirect and r.headers.get("Location"):
            url = urljoin(url, r.headers["Location"]); continue
        return r, url, f"http_{r.status_code}"
    return None, url, "too_many_redirects"


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
    return {"title": unescape(title.group(1)).strip() if title else None, "html_lang": lang.group(1) if lang else None,
            "og_site_name": meta("og:site_name"), "og_title": meta("og:title"), "hreflang": alt[:6],
            "legal_name_lines": uniq(LEGAL.findall(txt)), "licence_lines": uniq(LICENCE.findall(txt))}


def main(urls_file):
    manifest = (OUT / "manifest.jsonl").open("a", encoding="utf-8")
    for line in Path(urls_file).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        label, url = line.split(None, 1)
        rec = {"label": label, "requested_url": url, "captured_at": datetime.now(UTC).isoformat()}
        try:
            r, final, status = fetch(url)
            rec.update(final_url=final, status=status)
            if r is not None and r.content:
                sha = hashlib.sha256(r.content).hexdigest()
                (RAW / f"{sha}.html").write_bytes(r.content)
                html = r.content.decode(r.encoding or "utf-8", errors="replace") if not r.apparent_encoding else r.content.decode("utf-8", errors="replace")
                rec.update(sha256=sha, content_type=r.headers.get("Content-Type"), bytes=len(r.content), extracted=extract(html))
        except Exception as e:  # recorded, never silently dropped
            rec.update(status="fetch_error", error=f"{type(e).__name__}: {str(e)[:160]}")
        manifest.write(json.dumps(rec, ensure_ascii=False) + "\n"); manifest.flush()
        print(json.dumps({k: rec.get(k) for k in ("label", "status", "final_url")}, ensure_ascii=False))
        time.sleep(2)


if __name__ == "__main__":
    main(sys.argv[1])
