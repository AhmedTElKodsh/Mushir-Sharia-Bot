from __future__ import annotations

import csv
import json

from scripts import scrape_egypt_installment_market as market
from scripts import summarize_egypt_installment_market as summary


def _summarize(tmp_path, rows, candidate_rows=()):
    run_dir = tmp_path / "2026-09-27/direct_store/20260927T010000Z-run"
    run_dir.mkdir(parents=True)
    with (run_dir / "installment_evidence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=market.OUTPUT_FIELDS)
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow({
                "stage": "direct_store", "category": "furniture", "entity": f"Shop {index}",
                "role": "retailer", "source_url": f"https://shop{index}.example/pay",
                "claim": "names a financier", "status": "verified_page_evidence", **row,
            })
    (run_dir / "manifest.json").write_text("{}")
    candidates = tmp_path / "candidates.csv"
    with candidates.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["entity", "role", "category", "discovery_source_url", "aliases"])
        writer.writeheader()
        writer.writerows(candidate_rows)
    manifest = summary.summarize(tmp_path / "2026-09-27", candidates, tmp_path / "output")
    with (tmp_path / "output/payment_relationships.csv").open(encoding="utf-8-sig") as handle:
        return manifest, list(csv.DictReader(handle))


def test_financier_named_in_english_is_kept(tmp_path):
    _, [row] = _summarize(tmp_path, [{"financing_entity": "valU",
                                      "evidence_snippet": "Pay over 12 months with VALU at checkout"}])
    assert (row["financing_entity"], row["seeded_not_established"]) == ("valU", "")
    assert row["financing_alias_matched"] == "valU:valU"


def test_financier_named_only_in_arabic_is_kept_through_observed_alias(tmp_path):
    _, [row] = _summarize(tmp_path, [{"financing_entity": "valU",
                                      "evidence_snippet": "قسط مشترياتك مع فاليو حتى 60 شهر"}])
    assert row["financing_entity"] == "valU"
    assert row["financing_alias_matched"] == "valU:فاليو"


def test_observed_veh_spelling_matches_but_is_not_folded_into_feh(tmp_path):
    # valU's own site spells the brand both فاليو and ڤاليو; both are listed as observed strings.
    _, [row] = _summarize(tmp_path, [{"financing_entity": "valU",
                                      "evidence_snippet": "ادفع على أقساط مع ڤاليو"}])
    assert row["financing_alias_matched"] == "valU:ڤاليو"
    assert summary._normalize("ڤ") == "ڤ"  # No letter substitution beyond the documented folds.


def test_seeded_financier_absent_from_passage_is_dropped_and_counted(tmp_path):
    manifest, [row] = _summarize(tmp_path, [{"financing_entity": "Contact",
                                             "evidence_snippet": "Buy now and pay in installments up to 24 months"}])
    assert row["financing_entity"] == ""
    assert row["seeded_not_established"] == "Contact"
    assert (manifest["seeded_financing_links"], manifest["established_financing_links"],
            manifest["seeded_not_established_links"]) == (1, 0, 1)
    entities = (tmp_path / "output/market_entities.csv").read_text(encoding="utf-8-sig")
    assert "Contact" not in entities


def test_arabic_orthographic_variants_match_by_normalization(tmp_path):
    rows = [
        {"financing_entity": "Souhoola", "evidence_snippet": "اشتر بالتقسيط مع سُهولة على 36 شهر"},  # damma + taa marbuta
        {"financing_entity": "Aman", "evidence_snippet": "التقسيط من أمـان بدون مقدم"},    # hamza alef + tatweel
    ]
    manifest, found = _summarize(tmp_path, rows)
    assert [r["financing_entity"] for r in found] == ["Souhoola", "Aman"]
    assert [r["financing_alias_matched"] for r in found] == ["Souhoola:سهوله", "Aman:امان"]
    assert manifest["established_by_common_word_alias"] == 2


def test_other_financier_in_passage_is_not_attributed_to_seeded_one(tmp_path):
    rows = [{"financing_entity": "Halan|Forsa",
             "evidence_snippet": "Installments with Forsa, Souhoola and Sympl; Halankar is a product name"}]
    _, [row] = _summarize(tmp_path, rows)
    assert row["financing_entity"] == "Forsa"
    assert row["seeded_not_established"] == "Halan"


def test_unverified_status_establishes_nothing(tmp_path):
    rows = [{"financing_entity": "valU", "status": "robots_unavailable", "evidence_snippet": "valU"}]
    _, [row] = _summarize(tmp_path, rows)
    assert (row["financing_entity"], row["seeded_not_established"]) == ("", "valU")


def test_spacing_variant_and_candidate_alias_column(tmp_path):
    rows = [{"financing_entity": "FAB Misr", "evidence_snippet": "Choose Your Bank FABMISR ALEXBANK"},
            {"financing_entity": "Lender X", "evidence_snippet": "قسط مع لندر اكس"}]
    candidates = [{"entity": "Lender X", "role": "finance_provider", "category": "mixed",
                   "discovery_source_url": "", "aliases": "لندر اكس"}]
    _, found = _summarize(tmp_path, rows, candidates)
    assert [r["financing_entity"] for r in found] == ["FAB Misr", "Lender X"]


def test_sharia_self_label_is_a_provider_claim_not_a_finding(tmp_path):
    rows = [{"financing_entity": "valU",
             "evidence_snippet": "valU instalments are Sharia-compliant and متوافقة مع الشريعة الإسلامية"}]
    manifest, [row] = _summarize(tmp_path, rows)
    assert row["provider_claim"] == "sharia_self_label:sharia-compliant | sharia_self_label:الشريعه الاسلاميه"
    assert row["status"] == "verified_page_evidence"
    assert "provider_claim" in manifest["scope_note"] and manifest["rows_with_provider_claim"] == 1
    assert not any("sharia" in json.dumps(v).casefold() for k, v in row.items()
                   if k not in {"provider_claim", "evidence_snippet"})
