"""OCR the FRA PDFs that have no text layer (offline; no FRA requests).

Engine: the Windows built-in OCR (Windows.Media.Ocr, language ar-SA), driven by
winocr.ps1. EasyOCR was tried first but needs several GB of free RAM for its
detector and ran ~80 s/page here; Windows OCR runs ~2-4 s/page.

For each catalogue row whose text_layer starts with "none": render every page
with PyMuPDF at DPI, OCR the images, then fix reading order. Windows OCR lists
the words of a line left to right, so Arabic-dominant lines are reversed word
by word while runs of Latin-script words keep their own order. Output per
document under .../fra_documents/2026-10-02/derived/ocr/:

  <sha>.json  per-page lines (text + position), engine, dpi, timings
  <sha>.txt   page-separated reading text

Page images are deleted after OCR (re-render from the PDF to verify a quote).
Existing outputs are skipped, so the run resumes. OCR text is a reading aid:
check the page image before quoting.

    python ocr_fra_documents.py --priority   # decrees, Sharia decisions, circulars, guides, templates
    python ocr_fra_documents.py              # everything still missing
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02/derived/ocr"
CATALOGUE = ROOT / "data/source_registry/fra_documents_catalogue.csv"
PRIORITY_KINDS = ("sharia_committee_decision", "board_decree", "circular", "guide", "law", "sharia_model_contract")
DPI = 250
ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")


def reading_order(text: str) -> str:
    """Reverse word order of an Arabic-dominant line, keeping Latin runs intact."""
    if len(ARABIC.findall(text)) <= len(LATIN.findall(text)):
        return text
    words = text.split()[::-1]
    out: list[str] = []
    run: list[str] = []
    for word in words:
        if LATIN.search(word) and not ARABIC.search(word):
            run.append(word)
            continue
        if run:
            out.extend(reversed(run))
            run = []
        out.append(word)
    out.extend(reversed(run))
    return " ".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="stop after N documents (0 = all)")
    args = parser.parse_args(argv)

    import pymupdf

    rows = [r for r in csv.DictReader(CATALOGUE.open(encoding="utf-8-sig")) if r["text_layer"].startswith("none")]
    if args.priority:
        rows = [r for r in rows if r["kind_hint"] in PRIORITY_KINDS or "استرشاد" in r["url"]]
    rows.sort(key=lambda r: (r["kind_hint"] not in PRIORITY_KINDS, int(r["pages"] or 0)))
    OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    for row in rows:
        target = OUT / f"{row['sha256']}.json"
        if target.exists():
            continue
        started = time.monotonic()
        pages_dir = OUT / "pages" / row["sha256"]
        pages_dir.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(ROOT / row["raw_path"])
        count = doc.page_count
        for number, page in enumerate(doc, start=1):
            png = pages_dir / f"p{number:04d}.png"
            if not png.exists():
                page.get_pixmap(dpi=DPI).save(png)
        doc.close()
        # winocr.ps1 skips pages that already have output, so a retry resumes;
        # transient WinRT failures were seen under low free memory.
        for attempt in range(3):
            proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                   str(HERE / "winocr.ps1"), "-InputDir", str(pages_dir), "-Language", "ar-SA"],
                                  capture_output=True)
            if proc.returncode == 0:
                break
        else:
            err = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()[-1:] or [""]
            print(f"FAILED {row['sha256'][:12]} after 3 attempts: {err[0][:160]}", flush=True)
            continue
        pages = []
        for number in range(1, count + 1):
            raw = json.loads((pages_dir / f"p{number:04d}.json").read_text(encoding="utf-8-sig"))
            lines = raw.get("lines") or []
            if isinstance(lines, dict):  # ConvertTo-Json collapses a single-item array
                lines = [lines]
            fixed = [{**line, "text": reading_order(line.get("text", ""))} for line in lines]
            pages.append({"page": number, "angle": raw.get("angle"), "lines": fixed,
                          "text": "\n".join(line["text"] for line in fixed)})
        record = {"source_sha256": row["sha256"], "source_url": row["url"], "fra_link_text": row["fra_link_text"],
                  "kind_hint": row["kind_hint"], "engine": "Windows.Media.Ocr (ar-SA)",
                  "renderer": f"pymupdf {pymupdf.VersionBind}", "dpi": DPI,
                  "reading_order": "Arabic-dominant lines word-reversed; Latin runs kept",
                  "ocr_at": datetime.now(timezone.utc).isoformat(), "seconds": round(time.monotonic() - started, 1),
                  "pages": pages, "note": "OCR reading aid; verify against the page image before quoting"}
        target.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        (OUT / f"{row['sha256']}.txt").write_text(
            "\n\n".join(f"--- page {p['page']} ---\n{p['text']}" for p in pages), encoding="utf-8")
        shutil.rmtree(pages_dir)
        chars = sum(len(p["text"]) for p in pages)
        print(f"{row['kind_hint']:26} {count:>4}p {record['seconds']:>6}s {chars:>7} chars  "
              f"{(row['fra_link_text'] or row['url'][-50:])[:60]}", flush=True)
        done += 1
        if args.limit and done >= args.limit:
            break
    print(f"done: {done} documents", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
