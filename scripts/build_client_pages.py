"""Build the client-facing HTML pages from one tracked source.

Sources live in .planning/sharia-compliance-chatbot/docs/client-pages/src/:
a shared stylesheet plus one body file per page. Bodies link to each other
through {{GUIDE_URL}} and {{PACK_URL}} placeholders.

Two outputs are written:

* standalone pages in docs/client-pages/ (tracked; open them from GitHub or
  a download), which link to each other by relative file name;
* publish-ready pages in outputs/client-pages/ (git-ignored), which link to
  the shared claude.ai pages. The publishing host adds the document wrapper
  itself, so these carry no <html>/<head>/<body> tags.

Usage: python scripts/build_client_pages.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / ".planning" / "sharia-compliance-chatbot" / "docs" / "client-pages"
SRC = PAGES_DIR / "src"
PUBLISH_DIR = ROOT / "outputs" / "client-pages"

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;'
    "1,400&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family="
    'Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap">'
)

PAGES = {
    "client-guide": {"title": "Mushir Client Guide", "body": "client-guide.body.html"},
    "scholar-review-pack": {"title": "Mushir Scholar Review Pack", "body": "scholar-review-pack.body.html"},
}

LINKS = {
    "standalone": {"{{GUIDE_URL}}": "client-guide.html", "{{PACK_URL}}": "scholar-review-pack.html"},
    "publish": {
        "{{GUIDE_URL}}": "https://claude.ai/artifact/N5sTGi4S15Kj3A1KdADGtP",
        "{{PACK_URL}}": "https://claude.ai/artifact/4CE8SuwyTbb4vCQK56asMQ",
    },
}

# The base reset the publishing host normally supplies; standalone pages need it themselves.
STANDALONE_RESET = """
img { max-width: 100%; }
[hidden] { display: none !important; }
body { margin: 0; }
"""


def _render(body: str, links: dict[str, str]) -> str:
    for token, target in links.items():
        body = body.replace(token, target)
    leftover = [token for token in ("{{GUIDE_URL}}", "{{PACK_URL}}") if token in body]
    if leftover:
        raise ValueError(f"unreplaced link placeholders: {leftover}")
    return body


def build() -> list[Path]:
    css = (SRC / "client-pages.css").read_text(encoding="utf-8")
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, page in PAGES.items():
        body = (SRC / page["body"]).read_text(encoding="utf-8")

        publish = (
            f"<title>{page['title']}</title>\n{FONTS}\n<style>\n{css}</style>\n\n"
            f"{_render(body, LINKS['publish'])}"
        )
        target = PUBLISH_DIR / f"{name}.html"
        target.write_text(publish, encoding="utf-8")
        written.append(target)

        standalone = (
            "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"<title>{page['title']}</title>\n{FONTS}\n<style>\n{css}{STANDALONE_RESET}</style>\n</head>\n<body>\n"
            f"{_render(body, LINKS['standalone'])}\n</body>\n</html>\n"
        )
        target = PAGES_DIR / f"{name}.html"
        target.write_text(standalone, encoding="utf-8")
        written.append(target)
    return written


if __name__ == "__main__":
    for path in build():
        print(path.relative_to(ROOT))
