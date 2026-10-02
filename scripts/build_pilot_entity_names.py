"""Build data/source_registry/pilot_entity_names.csv from the 2026-10-01 entity-resolution captures.

Every row is a name exactly as one source wrote it (never translated), with source URL, capture date,
evidence sha256 and review_status=pending_client_review. Run from the repo root.
"""
import collections, csv, json, re

base = "data/runtime/artifacts/l6_scrape/entity_resolution/2026-10-01"
man = [json.loads(l) for l in open(f"{base}/manifest.jsonl", encoding="utf-8")]
sha, when = {}, {}
for r in man:
    if r.get("sha256") and r.get("final_url") and r.get("record_type") in (None, "rendered_capture"):
        sha.setdefault(r["final_url"], r["sha256"]); when.setdefault(r["final_url"], r["captured_at"][:10])
fra = {d["licence"] + "|" + d["activity"]: d for d in json.load(open(f"{base}/fra_detail_records.json", encoding="utf-8"))}
TC, MT, FAC = "تمويل استهلاكي", "مقدمي التمويل الاستهلاكي", "تخصيــــــــــم"
rows = []


def add(fin, key, text, kind, url, note="", ident=""):
    ar, la = re.search(r"[؀-ۿ]", text), re.search(r"[A-Za-z]", text)
    script = "mixed" if ar and la else "arabic" if ar else "latin"
    rows.append({"financier": fin, "entity_key": key, "name_text": text, "script": script, "name_kind": kind,
                 "identifier": ident, "source_url": url, "captured_at": when.get(url, "2026-10-01"),
                 "evidence_sha256": sha.get(url, ""), "review_status": "pending_client_review", "note": note})


def fra_rows(fin, lic, act, key, former=()):
    d = fra[f"{lic}|{act}"]; u = d["page_url"]
    ident = f"FRA {act} #{lic}; company no. {d.get('company_number')}"
    add(fin, key, d["name_ar"], "fra_register_name_ar", u, "verbatim FRA Arabic name field", ident)
    if d.get("name_en"):
        add(fin, key, d["name_en"], "fra_register_name_en", u, "verbatim FRA English name field", ident)
    else:
        add(fin, key, "No data exists", "fra_register_name_en_absent", u, "FRA shows no English name; none supplied by us", ident)
    for f in former:
        add(fin, key, f, "former_name_in_fra_text", u, "literal substring of the FRA Arabic name field marked سابقا", ident)


# valU
fra_rows("valU", "13", TC, "fra:consumer_finance:13",
         former=("فاليو للتمويل الاستهلاكي", "VALU CONSUMER FINANCE", "فاليو لخدمات البيع بالتقسيط", "VAIU"))
T, A, P = "https://valugroup.com/terms-and-conditions", "https://valugroup.com/ar/about-us", "https://valugroup.com/privacy-policy"
add("valU", "fra:consumer_finance:13", "U Consumer Finance S.A.E", "legal_name_stated_by_site", A,
    "site: 'الاسم القانوني: (U Consumer Finance S.A.E) كود (EGX: VALU.CA)'", "EGX: VALU.CA")
add("valU", "fra:consumer_finance:13", "يو للتمويل الاستهلاكي", "legal_name_stated_by_site", T,
    "terms: parent company, FRA licence 'رقم 13 لسنة 2020', commercial register 34260", "CR 34260")
add("valU", "app:valu_payments", "فاليو للمدفوعات والحلول التقنية ش.م.م", "app_operator_company", T,
    "terms: app/payments operator, commercial register 119489; NOT the FRA licensee", "CR 119489")
add("valU", "group:efg_holding", "مجموعة اى اف جي القابضة ش.م.م", "parent_group", P,
    "privacy policy: valU payments company is a subsidiary; one occurrence spelled 'لقابضة'")
for b, u, n in [("فاليو", T, "brand spelling (feh), 279 occurrences across valugroup pages"),
                ("ڤاليو", A, "brand spelling (veh), 31 occurrences"),
                ("Valu", "https://valugroup.com", "site copyright 'Copyright © 2026 Valu'"),
                ("ValU", T, "terms: 'ValU (\" شركة فاليو \")'")]:
    add("valU", "brand:valu", b, "brand_name", u, n)
add("valU", "brand:valu", "valugroup.com", "web_presence", "https://valugroup.com",
    "www.valu.com.eg redirected here on 2026-10-01; site also operates in Jordan (separate jurisdiction, entity not captured)")

# Contact
for lic, act, key in [("1", TC, "fra:consumer_finance:1"), ("17", MT, "fra:consumer_finance_providers:17"),
                      ("19", MT, "fra:consumer_finance_providers:19"), ("24", MT, "fra:consumer_finance_providers:24"),
                      ("33", TC, "fra:consumer_finance:33"), ("49", TC, "fra:consumer_finance:49"), ("8", FAC, "fra:factoring:8")]:
    former = {"19": ("كونتكت المصريه العالميه لتقسيط السيارات",), "8": ("بلس للتخصيم",)}.get(lic, ())
    fra_rows("Contact", lic, act, key, former=former)
add("Contact", "group:contact_financial_holding", "Contact Financial Holding", "holding_company_on_site",
    "https://contact.eg/en/about", "site: 'About Contact Financial Holding'")
add("Contact", "group:contact_financial_holding", "كونتكت المالية القابضة", "holding_company_on_site",
    "https://contact.eg/about", "site: 'نبذه عن كونتكت المالية القابضة'")
add("Contact", "brand:contact", "كونتكت", "brand_name", "https://contact.eg/", "site title 'كونتكت | أول شركة تمويل استهلاكي في مصر'")
add("Contact", "brand:contact", "Contact", "brand_name", "https://contact.eg/en", "also an everyday English word")
add("Contact", "brand:contact_cars", "Contact Cars", "brand_name", "https://www.contactcars.com/en", "related car marketplace brand")
add("Contact", "brand:contact_cars", "كونتكت كارز", "brand_name", "https://www.contactcars.com/ar", "site title")
add("Contact", "related:sarwa", "Sarwa Insurance", "related_entity_on_site", "https://contact.eg/en/about",
    "management list: 'MD of Sarwa Insurance'; FRA #1 and #8 list sarwa.capital emails")
add("Contact", "related:contact_credit", "Contact Credit", "related_entity_on_site", "https://contact.eg/en/about",
    "management list: 'CEO of Contact Credit'; not matched to an FRA name yet")

# Souhoola
fra_rows("Souhoola", "10", TC, "fra:consumer_finance:10", former=("سي اي للتمويل الاستهلاكي سهوله",))
add("Souhoola", "fra:consumer_finance:10", "Souhoola, CI Consumer Finance", "site_title", "https://souhoola.com/", "page title, identical on /ar")
add("Souhoola", "fra:consumer_finance:10", "Contact Investment for Consumer Finance", "legal_name_stated_by_site",
    "https://souhoola.com/terms-conditions",
    "terms (Last Updated: February 2026): 'provided by Contact Investment for Consumer Finance (\"Souhoola\"...)'; "
    "address matches FRA #10; no FRA row with this English name found")
add("Souhoola", "brand:souhoola", "Souhoola", "brand_name", "https://souhoola.com/", "site copyright '© 2026 Souhoola'")
add("Souhoola", "brand:souhoola", "سهوله", "brand_name_in_fra_text", fra[f"10|{TC}"]["page_url"],
    "Arabic brand only observed inside the FRA name; no Arabic text on the site")

# Aman
fra_rows("Aman", "43", TC, "fra:consumer_finance:43")
add("Aman", "group:aman_holding", "Aman Holding corp", "holding_company_on_site", "https://aman.eg/en/", "footer 'All rights reserved@Aman Holding corp'")
add("Aman", "group:aman_holding", "شركة أمان القابضة", "holding_company_on_site",
    "https://aman.eg/ar/home-%d8%a7%d9%84%d8%b9%d8%b1%d8%a8%d9%8a%d8%a9/", "footer 'جميع الحقوق محفوظة @شركة أمان القابضة'")
add("Aman", "group:raya", "Raya For Financial Investments", "parent_group", "https://aman.eg/en/about-aman/",
    "EN: 'A subsidiary Company of Raya For Financial Investments'; differs from the Arabic parent name")
add("Aman", "group:raya", "راية للخدمات المالية", "parent_group", "https://aman.eg/ar/%d8%b9%d9%86-%d8%a3%d9%85%d8%a7%d9%86/",
    "AR: 'إحدى شركات راية للخدمات المالية'; differs from the English parent name")
add("Aman", "brand:aman", "أمان", "brand_name", "https://aman.eg/ar/%d8%b9%d9%86-%d8%a3%d9%85%d8%a7%d9%86/", "also an everyday word ('safety')")
add("Aman", "brand:aman", "Aman", "brand_name", "https://aman.eg/en/", "")

# Halan
fra_rows("Halan", "23", TC, "fra:consumer_finance:23")
fra_rows("Halan", "50", FAC, "fra:factoring:50")
add("Halan", "brand:halan", "Halan", "brand_name", "https://halan.com/", "'© 2026, Halan All right reserved'")
add("Halan", "brand:halan", "Halan Consumer Finance", "brand_product_name", "https://halan.com/personal-lending/", "'Why Choose Halan Consumer Finance?'")
add("Halan", "brand:halan", "حالا", "brand_name", "https://halan.com/ar/about-us-2/", "'شركة حالا في عام 2017'; also an everyday word ('right away')")

# B.TECH/Mylo and Drive/Forsa (pilot widened 2026-10-02), from that day's FRA typed-register captures.
base2 = "data/runtime/artifacts/l6_scrape/fra_registry/2026-10-02"
for typ, slug in (("consumer-finance", "consumer_finance"), ("consumer-finance-providers", "consumer_finance_providers")):
    m2 = json.load(open(f"{base2}/{typ}/manifest.json", encoding="utf-8"))
    for c in m2["raw_captures"]:
        sha.setdefault(c["url"], c["sha256"].split(":", 1)[1]); when.setdefault(c["url"], m2["run_date"])
    for r in csv.DictReader(open(f"{base2}/{typ}/fra_{slug}_companies.csv", encoding="utf-8-sig")):
        fin = {"67648": "B.TECH/Mylo", "552038": "B.TECH/Mylo", "7721179": "Drive/Forsa"}.get(r["company_number"])
        if not fin or (typ, r["company_number"]) == ("consumer-finance-providers", "7721179"):
            continue
        key, u = f"fra:{slug}:{r['license_number']}", r["company_detail_url"]
        ident = f"FRA {r['fra_type_ar']} #{r['license_number']}; company no. {r['company_number']}"
        add(fin, key, r["company_name_ar"], "fra_register_name_ar", u, "verbatim FRA Arabic name field", ident)
        if r["company_name_en"] in ("No data exists", "."):
            add(fin, key, r["company_name_en"], "fra_register_name_en_absent", u, "FRA English field holds no name", ident)
        else:
            add(fin, key, r["company_name_en"], "fra_register_name_en", u, "verbatim FRA English name field", ident)
        if r["company_number"] == "7721179":
            add(fin, key, "درايف للتخصيم DRIVE FINANCE", "former_name_in_fra_text", u,
                "literal substring of the FRA Arabic name field marked سابقا", ident)
M = "https://sites.google.com/btech.com/mylo-terms-and-conditions-en"
add("B.TECH/Mylo", "fra:consumer_finance:48", "mylo", "brand_name", M,
    "search-index text of Mylo terms: B.TECH Finance operating as مايلو; page behind Google sign-in on 2026-10-02, not read")
add("B.TECH/Mylo", "fra:consumer_finance:48", "مايلو", "brand_name", M, "Arabic brand name (search-index text of gated terms)")
add("B.TECH/Mylo", "fra:consumer_finance:48", "B.TECH Finance", "legal_name_stated_by_site", M,
    "search-index text only (page gated); FRA English field says SAE")
add("B.TECH/Mylo", "fra:consumer_finance:48", "mylo", "brand_name", "https://btech.com/en/mylo-explore",
    "B.TECH page (manual review): 'powered by B.TECH'; marketed as Sharia-compliant (marketing, not a finding)")
add("Drive/Forsa", "fra:consumer_finance:26", "Forsa", "brand_name",
    "https://gb-corporation.com/forsa-application-is-a-consumer-financing-systems-and-flexible-installment-methods-in-a-several-major-malls-and-hypermarkets/",
    "parent GB Corp: Forsa powered by Drive Finance (web research; page not captured)")
add("Drive/Forsa", "fra:consumer_finance:26", "درايف للتمويل والخدمات المالية غير المصرفية ش.م.م.", "legal_name_stated_by_site",
    "https://www.forsaegypt.com/ar/privacy",
    "privacy policy (browser-rendered, manual review 2026-10-02): CR 164123; FRA factoring licence 3 and consumer-finance licence 26",
    "CR 164123")
add("Drive/Forsa", "fra:consumer_finance:26", "Drive Finance and Non-Banking Services Co. S.A.E.", "legal_name_stated_by_site",
    "https://www.forsaegypt.com/ar/privacy", "English legal name quoted inside the Arabic privacy policy", "CR 164123")

out = "data/source_registry/pilot_entity_names.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as h:
    w = csv.DictWriter(h, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", dict(collections.Counter(r["financier"] for r in rows)))
print("missing sha:", sorted({r["source_url"] for r in rows if not r["evidence_sha256"]}))
