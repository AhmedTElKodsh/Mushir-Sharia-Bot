from __future__ import annotations

import json

import pytest

from src.acquisition.egypt_financial import fra_entities as fe


def _row(name_ar, number, licence, activity, *, name_en="No data exists"):
    return {
        "company_name_ar": name_ar,
        "company_name_en": name_en,
        "company_number": number,
        "license_number": licence,
        "activities_json": json.dumps([{"activity_ar": activity}], ensure_ascii=False),
        "license_date": "2026-01-01",
        "address": "القاهرة",
        "company_detail_url": f"https://fra.example/{number}-{licence}",
        "scraped_at": "2026-10-02",
        "scrape_status": "complete",
        # Deliberately stale: the module must recompute keys from the row.
        "licence_key": "fra:consumer_finance:no_licence_number",
    }


DRIVE_CF = _row("درايف للتمويل والخدمات الماليه (درايف للتخصيم DRIVE FINANCE سابقا)", "7721179", "26",
                "تمويل استهلاكي", name_en="Drive Finance")
DRIVE_FACTORING = _row("درايف للتمويل والخدمات الماليه", "7721179", "3", "تخصيــــــــــم")
BTECH_CF = _row("بي تك للتمويل BTECH FINANCE SAE", "67648", "48", "تمويل استهلاكي",
                name_en="B.TECH Finance S.A.E")
BTECH_PROVIDER = _row("بي تك للتجاره والتوزيع", "552038", "7", "مقدمي التمويل الاستهلاكي")
TELDA = _row("تيلدا للتمويل الاستهلاكي", "67654", "No data exists", "تمويل استهلاكي")
ADVA = _row("ادفا للتمويل الاستهلاكي", "67650", "No data exists", "تمويل استهلاكي")
ROWS = [DRIVE_CF, DRIVE_FACTORING, BTECH_CF, BTECH_PROVIDER, TELDA, ADVA]

FORSA_LINK = {
    "brand": "Forsa", "brand_script": "latin", "licence_key": "fra:consumer_finance:26",
    "relation": "brand_of_licensee", "link_basis": "parent_group_first_party_statement",
    "status": "verified", "website_url": "https://forsa.example", "corporate_contact": "",
    "evidence_url": "https://parent.example/forsa", "observed_text": "powered by Drive Finance",
    "checked_on": "2026-10-02", "note": "",
}


def test_shared_company_number_becomes_sibling_licence_not_a_dropped_row():
    entities = {e["licence_key"]: e for e in fe.build_entity_rows(ROWS, [FORSA_LINK])}

    drive = entities["fra:consumer_finance:26"]
    assert drive["other_licences_same_company"] == "fra:factoring:3"
    assert drive["former_names_ar"] == "درايف للتخصيم DRIVE FINANCE"
    assert drive["brands"] == "Forsa"
    assert drive["brand_link_status"] == "verified"
    # Factoring is outside consumer scope, so it is a sibling, not an entity row.
    assert "fra:factoring:3" not in entities


def test_unnumbered_licences_keep_distinct_identities():
    keys = {e["licence_key"] for e in fe.build_entity_rows(ROWS)}

    assert "fra:consumer_finance:company-67654" in keys
    assert "fra:consumer_finance:company-67650" in keys


def test_provider_register_rows_carry_the_regulator_role_and_question():
    entities = {e["licence_key"]: e for e in fe.build_entity_rows(ROWS)}
    provider = entities["fra:consumer_finance_providers:7"]

    assert provider["fra_register_role"] == (
        "registered_seller_or_service_provider_financing_own_sales"
    )
    assert "sells and finances its own goods" in provider["open_questions"]
    assert provider["brand_link_status"] == "unlinked"


def test_brand_resolution_prefers_evidence_link_over_name_search():
    result = fe.resolve_brand("forsa", ROWS, [FORSA_LINK])

    assert result.outcome == "evidence_link"
    assert result.licence_keys == ("fra:consumer_finance:26",)
    assert result.link_statuses == ("verified",)


def test_brand_found_only_in_register_name_is_a_lead_by_name():
    result = fe.resolve_brand("BTECH", ROWS)

    assert result.outcome == "register_name"
    assert result.licence_keys == ("fra:consumer_finance:48",)
    assert "lead" in result.note


def test_former_name_match_is_reported_separately():
    result = fe.resolve_brand("درايف للتخصيم", ROWS)

    assert result.outcome == "former_name"
    assert result.licence_keys == ("fra:consumer_finance:26",)


def test_unknown_brand_is_not_found_by_name_never_no_fra_match():
    result = fe.resolve_brand("Mylo", ROWS)

    assert result.outcome == "not_found_by_name"
    assert "no FRA match" not in result.note
    assert "parent" in result.note


def test_whole_word_matching_does_not_hit_inside_other_words():
    rows = [_row("الامان للتجاره", "1", "1", "تمويل استهلاكي")]

    assert fe.resolve_brand("امان", rows).outcome == "not_found_by_name"


@pytest.mark.parametrize(
    ("first", "second"),
    [("ڤاليو", "فاليو"), ("ValU", "valu"), ("سهولة", "سهوله"), ("إمان", "امان")],
)
def test_normalize_name_folds_spelling_variants(first, second):
    assert fe.normalize_name(first) == fe.normalize_name(second)


def test_latin_segments_are_kept_verbatim():
    assert fe.latin_segments("كليفر للتمويل الاستهلاكي KLIVVR FOR CONSUMER FINANCE") == (
        "KLIVVR FOR CONSUMER FINANCE",
    )
