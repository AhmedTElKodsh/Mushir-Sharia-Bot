"""Catalogue captured FRA publications (offline; no network).

Writes data/source_registry/fra_documents_catalogue.csv: one row per distinct
PDF (by SHA-256) with its FRA link text, source page, page count, text-layer
quality and the pages where contract-model and Sharia terms occur, plus one row
per captured Sharia/Islamic HTML page, whose text is saved under derived/. Term
hits are search aids for a human reader, not classifications. Run from the repo
root.
"""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02"
TERMS = {
    "model_contract": ("نموذج عقد", "نماذج عقود", "نماذج العقود", "عقد استرشادي", "النموذج المرفق"),
    "consumer_finance": ("التمويل الاستهلاكي",),
    "sharia_committee": ("لجنة الرقابة الشرعية", "هيئة الرقابة الشرعية", "الرقابة الشرعية"),
    "sharia_rulings": ("أحكام الشريعة", "مبادئ الشريعة", "الشريعة الإسلامية", "متوافق مع الشريعة"),
    "murabaha": ("مرابحة", "المرابحة", "Murabaha", "murabaha"),
    "ijara": ("إجارة", "الإجارة", "اجارة", "Ijara"),
    "musharaka_mudaraba": ("مشاركة", "مضاربة", "Musharaka", "Mudaraba", "mudarabah"),
    "sukuk": ("صكوك", "Sukuk", "sukuk"),
    "takaful": ("تكافل", "Takaful", "takaful"),
    "receivable_transfer": ("حوالة", "بيع المديونية", "التخصيم", "توريق"),
    "aaoifi": ("AAOIFI", "أيوفي", "المحاسبة والمراجعة للمؤسسات المالية الإسلامية"),
}
FIELDS = ["sha256", "kind_hint", "fra_link_text", "url", "found_on", "pages", "text_chars",
          "text_layer", "terms_by_page", "raw_path", "ocr_path"]
HTML_PAGE = re.compile(r"islamic|sharia|sukuk|takaful")


def kind_hint(text: str, url: str) -> str:
    s = urllib.parse.unquote(url) + " " + text
    for key, words in (("sharia_model_contract", ("استرشادي", "Model Murabaha", "Contract", "Template")),
                       ("sharia_committee_decision", ("لجنة الرقابة الشرعية", "الرقابة-الشرعية", "Sharia")),
                       ("guide", ("دليل", "guide", "Takhseem", "mmt")),
                       ("circular", ("كتاب دوري", "كتاب دورى", "كتاب-دور")),
                       ("board_decree", ("قرار", "Decree")),
                       ("law", ("قانون", "Law"))):
        if any(w in s for w in words):
            return key
    return "other"


def html_text(html: str) -> str:
    html = re.sub(r"<(script|style|header|footer|nav)\b.*?</\1>", " ", html, flags=re.S | re.I)
    main = re.search(r"<main\b.*?</main>|<article\b.*?</article>", html, re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", main.group(0) if main else html)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def main() -> int:
    recs = [json.loads(line) for line in (OUT / "fra-documents-manifest.jsonl").open(encoding="utf-8")]
    link_text: dict[str, tuple[str, str]] = {}
    for page in recs:
        if page.get("outcome") == "captured" and page.get("kind") == "html":
            for link in page.get("linked_pdfs") or page.get("candidate_pdfs") or []:
                link_text.setdefault(link["href"], (link.get("text", ""), page["url"]))
    rows: list[dict] = []
    seen: set[str] = set()
    for r in recs:
        if r.get("outcome") != "captured" or r.get("kind") != "pdf" or r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        text, found_on = link_text.get(r["url"], ("", ""))
        if not text and "|" in r["label"]:
            text = r["label"].split("|", 1)[1]
        text_layer = ""
        ocr_path = ""
        try:
            reader = pypdf.PdfReader(str(ROOT / r["raw"]))
            page_texts = [(page.extract_text() or "") for page in reader.pages]
        except Exception as exc:  # malformed/encrypted files keep a row with the gap
            page_texts, text_layer = [], f"unreadable: {type(exc).__name__}"
        chars = sum(len(t) for t in page_texts)
        arabic = sum(len(re.findall(r"[؀-ۿ]", t)) for t in page_texts)
        ocr_file = OUT / "derived" / "ocr" / f"{r['sha256']}.json"
        if page_texts and chars < 50 * len(page_texts) and ocr_file.exists():
            ocr = json.loads(ocr_file.read_text(encoding="utf-8"))
            page_texts = [p["text"] for p in ocr["pages"]]
            chars = sum(len(t) for t in page_texts)
            text_layer = f"ocr ({ocr['engine']}; verify against page image)"
            ocr_path = ocr_file.with_suffix(".txt").relative_to(ROOT).as_posix()
        if page_texts and not text_layer:
            if chars < 50 * len(page_texts):
                text_layer = "none_or_thin (scanned? OCR needed)"
            elif arabic > chars * 0.3:
                text_layer = "arabic_text"
            else:
                text_layer = "mostly_latin_or_garbled (check page images)"
        hits = []
        for name, words in TERMS.items():
            found = [i + 1 for i, t in enumerate(page_texts) if any(w in t for w in words)]
            if found:
                shown = ",".join(map(str, found[:12])) + ("…" if len(found) > 12 else "")
                hits.append(f"{name}:p{shown}")
        rows.append({"sha256": r["sha256"], "kind_hint": kind_hint(text, r["url"]), "fra_link_text": text,
                     "url": urllib.parse.unquote(r["url"]), "found_on": urllib.parse.unquote(found_on),
                     "pages": len(page_texts), "text_chars": chars, "text_layer": text_layer,
                     "terms_by_page": "; ".join(hits), "raw_path": r["raw"], "ocr_path": ocr_path})

    derived = OUT / "derived"
    derived.mkdir(exist_ok=True)
    for r in recs:
        if (r.get("outcome") != "captured" or r.get("kind") != "html" or r["sha256"] in seen
                or not HTML_PAGE.search(r["label"]) or ":pdf" in r["label"]):
            continue
        seen.add(r["sha256"])
        text = html_text((ROOT / r["raw"]).read_text(encoding="utf-8", errors="replace"))
        out = derived / f"page-{r['label']}.txt"
        out.write_text(text, encoding="utf-8")
        hits = [name for name, words in TERMS.items() if any(w in text for w in words)]
        rows.append({"sha256": r["sha256"], "kind_hint": "sharia_html_page", "fra_link_text": r.get("title", ""),
                     "url": urllib.parse.unquote(r["url"]), "found_on": "", "pages": 1, "text_chars": len(text),
                     "text_layer": "html_text", "terms_by_page": "; ".join(hits),
                     "raw_path": out.relative_to(ROOT).as_posix()})

    rows.sort(key=lambda row: (row["kind_hint"], row["fra_link_text"]))
    target = ROOT / "data/source_registry/fra_documents_catalogue.csv"
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} documents catalogued -> {target.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
