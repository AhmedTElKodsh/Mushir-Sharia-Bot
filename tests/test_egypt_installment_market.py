from __future__ import annotations

import csv
import hashlib
import json
import urllib.error

import pytest

from scripts import scrape_egypt_installment_market as market
from scripts import summarize_egypt_installment_market as summary


def _seed(path):
    rows = [
        {
            "stage": "product_market", "category": "laptops", "entity": "Shop A",
            "role": "retailer", "vendor": "", "source_url": "https://shop.example/offer",
            "required_terms": "laptop;installments|instalments", "claim": "laptop plan",
            "ranking_metric": "", "ranking_period": "", "ranking_source_url": "",
        },
        {
            "stage": "online_vendor", "category": "mixed", "entity": "Finance A",
            "role": "finance_provider", "vendor": "Shop A", "source_url": "https://shop.example/offer",
            "required_terms": "instalments;Finance A", "claim": "partner",
            "ranking_metric": "", "ranking_period": "", "ranking_source_url": "",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=market.INPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_verified_claims_share_one_fetch_and_preserve_evidence(tmp_path):
    seed = tmp_path / "seed.csv"
    _seed(seed)
    calls = []

    body = b"<html><script>ignore</script><body>Laptop instalments from Finance A</body></html>"

    def fetch(url, timeout):
        calls.append(url)
        return body

    class Decision:
        allowed = True
        state = "allowed"
        reason = "allowed"

    class Policy:
        crawl_delay = 0

        def decision_for(self, url):
            return Decision()

    manifest = market.run(
        seed, tmp_path / "out", "2026-09-24", delay=0, fetcher=fetch,
        robots_loader=lambda *args, **kwargs: Policy(),
    )
    assert calls == ["https://shop.example/offer"]
    assert manifest["status_counts"] == {"verified_page_evidence": 2}
    assert manifest["product_market_coverage"]["laptops"]["ranked_top_20_verified"] is False
    with (tmp_path / "out/installment_evidence.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert "Finance A" in rows[1]["evidence_snippet"]
    assert rows[0]["raw_sha256"] == "sha256:" + hashlib.sha256(body).hexdigest()
    assert json.loads((tmp_path / "out/manifest.json").read_text())["claim_count"] == 2


def test_robots_disallow_stops_fetch(tmp_path):
    seed = tmp_path / "seed.csv"
    _seed(seed)

    class Decision:
        allowed = False
        state = "disallowed"
        reason = "robots.txt disallows URL"

    class Policy:
        def decision_for(self, url):
            return Decision()

    manifest = market.run(
        seed, tmp_path / "out", "2026-09-24", delay=0,
        fetcher=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        robots_loader=lambda *args, **kwargs: Policy(),
    )
    assert manifest["status_counts"] == {"robots_disallowed": 2}


def test_marketplace_without_public_source_is_recorded_as_gap(tmp_path):
    seed = tmp_path / "seed.csv"
    with seed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=market.INPUT_FIELDS)
        writer.writeheader()
        writer.writerow({
            "stage": "online_vendor", "category": "mixed", "entity": "Marketplace X",
            "role": "marketplace", "vendor": "Marketplace X", "source_url": "",
            "required_terms": "", "claim": "No reviewed source found",
            "ranking_metric": "", "ranking_period": "", "ranking_source_url": "",
        })
    manifest = market.run(
        seed, tmp_path / "out", "2026-09-24", delay=0,
        fetcher=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        robots_loader=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not check robots")),
    )
    assert manifest["status_counts"] == {"no_public_source_identified": 1}
    assert manifest["distinct_page_count"] == 0


def test_error_shell_is_not_treated_as_source_absence(tmp_path):
    seed = tmp_path / "seed.csv"
    _seed(seed)

    class Decision:
        allowed = True
        state = "allowed"
        reason = "allowed"

    class Policy:
        crawl_delay = 0

        def decision_for(self, url):
            return Decision()

    manifest = market.run(
        seed, tmp_path / "out", "2026-09-24", delay=0,
        fetcher=lambda *args: b"<html><body>An error has occurred. Please try again.</body></html>",
        robots_loader=lambda *args, **kwargs: Policy(),
    )
    assert manifest["status_counts"] == {"page_error": 2}


def test_matching_terms_must_describe_one_passage():
    assert not market._find_evidence(
        "Installments are available. " + "Unrelated catalogue text. " * 40 + "Laptops",
        "installments;laptops",
    )
    assert market._find_evidence("Laptops can be bought in installments.", "laptops;installments")


def test_navigation_words_do_not_verify_an_offer():
    parser = market.VisibleText()
    parser.feed("<nav>Laptops</nav><main>Installments on washing machines only</main>")
    assert not market._find_evidence(parser.text(), "laptops;installments")


def test_error_shell_with_offer_words_is_still_page_error(tmp_path):
    seed = tmp_path / "seed.csv"
    _seed(seed)

    class Policy:
        crawl_delay = 0

        def decision_for(self, url):
            return type("Decision", (), {"allowed": True, "state": "allowed", "reason": "allowed"})()

    manifest = market.run(
        seed, tmp_path / "out", "2026-09-27", delay=0,
        fetcher=lambda *args: b"<body>An error has occurred. Please try again. Laptop instalments from Finance A</body>",
        robots_loader=lambda *args, **kwargs: Policy(),
    )
    assert manifest["status_counts"] == {"page_error": 2}


def test_run_preserves_prior_capture_instead_of_overwriting(tmp_path):
    seed = tmp_path / "seed.csv"
    _seed(seed)

    class Policy:
        crawl_delay = 0

        def decision_for(self, url):
            return type("Decision", (), {"allowed": True, "state": "allowed", "reason": "allowed"})()

    kwargs = {"delay": 0, "fetcher": lambda *args: b"<body>Laptop instalments from Finance A</body>",
              "robots_loader": lambda *args, **kw: Policy()}
    market.run(seed, tmp_path / "out", "2026-09-27", **kwargs)
    assert (tmp_path / "out/page_captures.jsonl").exists()
    with pytest.raises(FileExistsError):
        market.run(seed, tmp_path / "out", "2026-09-27", **kwargs)


def test_redirect_target_must_pass_robots_before_fetch(monkeypatch):
    visited = []

    class Opener:
        def open(self, request, timeout):
            visited.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "/private"}, None)

    monkeypatch.setattr(market.urllib.request, "build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="redirect target not allowed"):
        market._fetch(
            "https://example.com/public", 1,
            lambda url: type("Decision", (), {"allowed": False})(),
        )
    assert visited == ["https://example.com/public"]


def test_summary_selects_latest_run_and_keeps_seller_separate_from_channel(tmp_path):
    stage_root = tmp_path / "2026-09-27/online_vendor"

    def write_run(run_id, status):
        run_dir = stage_root / run_id
        run_dir.mkdir(parents=True)
        with (run_dir / "installment_evidence.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=market.OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerow({
                "stage": "online_vendor", "category": "furniture", "entity": "Seller A",
                "role": "marketplace_seller", "vendor": "Market A",
                "source_url": "https://example.com/product", "claim": "seller and plan",
                "status": status, "payment_model": "deferred_or_instalments",
                "evidence_snippet": "Seller A accepts Visa and Mobile Wallets with installments",
            })
        (run_dir / "manifest.json").write_text("{}")

    write_run("20260927T010000Z-old", "claim_not_found")
    write_run("20260927T020000Z-new", "verified_page_evidence")
    candidates = tmp_path / "candidates.csv"
    with candidates.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["entity", "role", "category", "discovery_source_url"])
        writer.writeheader()
        writer.writerow({"entity": "Seller A", "role": "marketplace_seller", "category": "furniture",
                         "discovery_source_url": "https://example.com/lead"})

    manifest = summary.summarize(tmp_path / "2026-09-27", candidates, tmp_path / "output")
    assert manifest["claim_count"] == 1
    assert manifest["distinct_selling_entities_with_page_evidence"] == 1
    with (tmp_path / "output/payment_relationships.csv").open(encoding="utf-8-sig") as handle:
        row = next(csv.DictReader(handle))
    assert (row["seller"], row["sales_channel"]) == ("Seller A", "Market A")
    assert row["ordinary_payment_context"] == "card | mobile_wallet"
