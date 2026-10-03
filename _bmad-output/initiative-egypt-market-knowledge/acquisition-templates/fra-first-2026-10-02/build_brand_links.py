"""Write data/source_registry/fra_brand_links.csv (offline; no network).

Each row links a market brand to one FRA licence with the evidence used.
Status: established = first-party document names the licensee;
verified = regulator register name or first-party parent statement;
lead = third-party report or web search, page not captured.
Run from the repository root.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.acquisition.egypt_financial.fra_entities import BRAND_LINK_FIELDS, write_csv  # noqa: E402

D = "2026-10-02"
SEARCH = "located by web search 2026-10-02; page not captured; legal-name clause not checked"
LINKS: list[dict[str, str]] = []


def add(brand, script, key, relation, basis, status, site="", contact="", ev="", obs="", note="", checked=D):
    LINKS.append(dict(brand=brand, brand_script=script, licence_key=key, relation=relation,
                      link_basis=basis, status=status, website_url=site, corporate_contact=contact,
                      evidence_url=ev, observed_text=obs, checked_on=checked, note=note))


# --- pilot seven ------------------------------------------------------------
add("valU", "latin", "fra:consumer_finance:13", "brand_of_licensee", "first_party_terms_legal_name",
    "established", "https://valugroup.com", "", "https://valugroup.com/terms-and-conditions",
    "terms name يو للتمويل الاستهلاكي (CR 34260)",
    "Established financier (user decision 2026-10-02). App operator is a separate company "
    "(فاليو للمدفوعات والحلول التقنية). Terms restrict automated collection: manual review only.",
    "2026-10-01")
add("فاليو", "arabic", "fra:consumer_finance:13", "brand_of_licensee", "first_party_terms_legal_name",
    "established", "https://valugroup.com", "", "https://valugroup.com/terms-and-conditions",
    "brand spelling on valugroup pages (also ڤاليو)", "Same licensee as valU.", "2026-10-01")
add("Contact", "latin", "fra:consumer_finance:33", "brand_of_licensee", "first_party_terms_appendix",
    "established", "https://contact.eg", "Info@contact.eg; 16177",
    "https://contact.eg/terms-and-conditions-en.pdf", "English terms appendix names Contact Credit Tech",
    "Appendix scope: goods/services, Fatorty, club finance. Main agreement still missing.")
add("Contact", "latin", "fra:consumer_finance:1", "brand_of_licensee", "fra_register_name", "verified",
    "https://contact.eg", "Info@contact.eg; 16177", "https://fra.gov.eg/company_records/company-record-1n-4/",
    "FRA name كونتكت للتمويل; EN CONTACT CAR TRADING",
    "Which Contact licensee signs which product is unresolved.", "2026-10-01")
add("Contact", "latin", "fra:consumer_finance:49", "group_affiliate", "fra_register_name", "lead", "", "",
    "https://fra.gov.eg/company_records/company-record-49n/", "FRA name جلوبال كونتكت للتمويل الاستهلاكي",
    "Name match only; group membership unconfirmed.", "2026-10-01")
for number, name in (("17", "عز العرب كونتكت فايننشال"), ("19", "كونتكت لتقسيط السيارات"),
                     ("24", "بافاريان كونتكت لتجاره السيارات")):
    add("Contact", "latin", f"fra:consumer_finance_providers:{number}", "group_affiliate_provider",
        "fra_register_name", "lead", "", "", "", f"FRA providers register: {name}",
        "Car-sales provider in the Contact name family; seller-finances-own-goods route is a lead "
        "per arrangement.", "2026-10-01")
add("Contact", "latin", "fra:factoring:8", "group_factoring_affiliate", "fra_register_name", "lead", "", "",
    "https://fra.gov.eg/company_records/company-record-8n-3/",
    "FRA name كونتكت للتخصيم; EN Contact Factoring S.A.E",
    "Relevant to receivable sale/assignment questions.", "2026-10-01")
add("Souhoola", "latin", "fra:consumer_finance:10", "brand_of_licensee", "fra_register_name", "verified",
    "https://souhoola.com", "help@souhoola.com; 15227", "https://souhoola.com/terms-conditions",
    "FRA name contains سهوله; Feb-2026 terms name Contact Investment for Consumer Finance",
    "Legal-name conflict (CI / BM / Contact Investment) unresolved. Automated route unknown; "
    "terms restrict reproduction.")
add("سهولة", "arabic", "fra:consumer_finance:10", "brand_of_licensee", "fra_register_name", "verified",
    "https://souhoola.com", "", "", "FRA name contains سهوله", "Same licensee as Souhoola.")
add("Aman", "latin", "fra:consumer_finance:43", "brand_of_licensee", "fra_register_name", "verified",
    "https://aman.eg", "19910", "https://aman.eg/en/service/get-aman-installment-limit/",
    "FRA name امان للتمويل الاستهلاكي; EN Aman Consumer Finance (S.A.M)",
    "Own store + merchant network + branches; Islamic product is a separate document task.")
add("Aman", "latin", "fra:consumer_finance_providers:2", "group_affiliate_provider", "fra_register_name",
    "lead", "https://aman.eg/ar/", "",
    "https://amwalalghad.com/2020/04/28/%D8%A3%D9%85%D8%A7%D9%86-%D8%AA%D8%AD%D8%B5%D9%84-%D8%B9%D9%84%D9%89-%D8%AA%D8%B1%D8%AE%D9%8A%D8%B5-%D9%85%D9%8F%D9%82%D8%AF%D9%85-%D8%AE%D8%AF%D9%85%D8%A9-%D8%AA%D9%85%D9%88%D9%8A/",
    "FRA providers register: امان للخدمات الماليه (licence date 2020-04-16); press 2020-04-28: Aman obtained a "
    "consumer-finance provider licence",
    "Contrast pair with #43. Aman's own instalment page (manual review 2026-10-02) sells through its online store, "
    "merchant network and branches under one brand, footer شركة أمان القابضة; no first-party page names the "
    "provider entity, so which channel uses #2 vs #43 is unresolved.")
add("Raya", "latin", "fra:consumer_finance_providers:3", "brand_of_provider", "fra_register_name", "verified",
    "https://www.rayashop.com/ar/installments", "support@rayashop.com", "https://www.rayashop.com/ar/installments",
    "Takseety page: برنامج تمويل مباشر حصري مملوك لشركة راية ... تخضع الموافقة النهائية لسياسة الائتمان بشركة راية; "
    "shop terms: contract with شركة راية للتجارة، التي تمارس الأعمال التجارية بصفتها متجر راية",
    "Manual review 2026-10-02. Seller finances its own goods in Raya's own words, but the shop's contracting party "
    "is Raya Trade while the FRA-registered provider is رايه للالكترونيات (Raya Electronics): which entity extends "
    "the credit is an open question. Aman's parent-group name is also Raya.")
add("Takseety", "latin", "fra:consumer_finance_providers:3", "programme_of_provider", "first_party_programme_page",
    "verified", "https://www.rayashop.com/en/installments", "", "https://www.rayashop.com/en/installments",
    "Takseety is an exclusive direct financing program by Raya", "Same open question as the Raya row.")
add("Halan", "latin", "fra:consumer_finance:23", "brand_of_licensee", "fra_register_name", "verified",
    "https://halan.com", "Info@halan.com; 16303", "https://halan.com/personal-lending/",
    "FRA name حالا للتمويل الاستهلاكي; EN Halan for consumer finance co.",
    "Halan Shop (own goods) and external-vendor financing are separate arrangements.")
add("Halan", "latin", "fra:factoring:50", "group_factoring_affiliate", "fra_register_name", "lead", "", "",
    "", "FRA name حالا لخدمات التمويل غير المصرفيه (also mortgage #32)",
    "Same company number holds factoring #50 and mortgage #32.")
GATED = ("Search-index text of B.TECH's Mylo terms (sites.google.com/btech.com/mylo-terms-and-conditions-en) "
         "names B.TECH Finance operating as مايلو under Law 18/2020, but on 2026-10-02 that page required a "
         "Google sign-in, so it was not read. Upgrade to established once a readable copy is obtained.")
add("mylo", "latin", "fra:consumer_finance:48", "brand_of_licensee", "first_party_parent_statement_plus_register_name",
    "verified", "https://btech.com/en/mylo-explore", "", "https://btech.com/en/mylo-explore",
    "B.TECH page: mylo is 'powered by B.TECH' and marketed as Sharia-compliant; FRA #48 is بي تك للتمويل BTECH FINANCE SAE",
    GATED + " B.TECH site terms restrict scraping: manual review only. 'Sharia-compliant' is marketing, not a "
    "scholar finding. Mylo also finances other merchants (e.g. 2B offer terms).")
add("مايلو", "arabic", "fra:consumer_finance:48", "brand_of_licensee", "first_party_parent_statement_plus_register_name",
    "verified", "https://btech.com/en/mylo-explore", "", "https://btech.com/en/mylo-explore",
    "Arabic brand name (search-index text of gated terms)", "Same licensee as mylo. " + GATED)
add("B.TECH", "latin", "fra:consumer_finance_providers:7", "brand_of_provider", "first_party_terms_licence_number",
    "established", "https://btech.com", "", "https://btech.com/ar/terms-and-conditions",
    "terms: خدمات الميني كاش تقدم تحت ترخيص الهيئة العامة للرقابة المالية رقم 7/2020; instalment requests approved "
    "by B.TECH's credit department, which computes the interest (احتساب الفوائد)",
    "Manual review 2026-10-02 (B.TECH terms restrict scraping). Seller financing its own goods via minicash under "
    "provider licence #7; Mylo runs through B.TECH Finance (#48). Contrast pair #7 vs #48.")
add("minicash", "latin", "fra:consumer_finance_providers:7", "programme_of_provider", "first_party_terms_licence_number",
    "established", "https://btech.com", "", "https://btech.com/ar/terms-and-conditions",
    "خدمات الميني كاش تقدم تحت ترخيص الهيئة العامة للرقابة المالية رقم 7/2020", "B.TECH's in-house instalment programme.")
add("ميني كاش", "arabic", "fra:consumer_finance_providers:7", "programme_of_provider", "first_party_terms_licence_number",
    "established", "https://btech.com", "", "https://btech.com/ar/terms-and-conditions",
    "خدمات الميني كاش تقدم تحت ترخيص الهيئة العامة للرقابة المالية رقم 7/2020", "Same as minicash.")
add("B.TECH", "latin", "fra:consumer_finance:48", "group_financier", "fra_register_name",
    "verified", "https://btech.com/en/mylo-explore", "", "", "FRA name بي تك للتمويل BTECH FINANCE SAE",
    "Group finance company; Mylo link per the mylo rows. " + GATED)
add("Forsa", "latin", "fra:consumer_finance:26", "brand_of_licensee", "first_party_privacy_policy_legal_name",
    "established", "https://www.forsaegypt.com", "ask@forsaegypt.com; drive-info@drive-finance.com",
    "https://www.forsaegypt.com/ar/privacy",
    "privacy policy: درايف للتمويل والخدمات المالية غير المصرفية ش.م.م. (Drive Finance and Non-Banking "
    "Services Co. S.A.E.), CR 164123, FRA factoring licence 3 and consumer-finance licence 26",
    "Manual public-page review in an ordinary browser (JS-rendered). Parent GB Corp also states Forsa is "
    "powered by Drive Finance. The page itself confirms both licences the old dedupe collapsed.")
add("Forsa", "latin", "fra:factoring:3", "same_company_factoring_licence", "first_party_privacy_policy_legal_name",
    "established", "https://www.forsaegypt.com", "", "https://www.forsaegypt.com/ar/privacy",
    "privacy policy names FRA factoring licence 3 for the same company",
    "Receivable sale/assignment questions belong to the scholar's contract review.")
add("Drive Finance", "latin", "fra:consumer_finance:26", "brand_of_licensee", "fra_register_name",
    "established", "", "", "", "FRA EN name Drive Finance",
    "Licence #26 was dropped by the old dedupe in the all-register export.")

# --- widened market: leads ---------------------------------------------------
WIDE = [
    ("Telda", "fra:consumer_finance:company-67654", "https://telda.app",
     "https://egyptinnovate.com/en/news/fra-approves-teldas-license-to-operate-in-consumer-finance",
     "FRA name تيلدا للتمويل الاستهلاكي", "No licence number published on FRA."),
    ("Klivvr", "fra:consumer_finance:53", "https://klivvr.com",
     "https://www.zawya.com/en/economy/north-africa/egypt-sahl-klivvr-partner-to-enable-installment-payments-through-mobile-app-412357",
     "FRA name كليفر للتمويل الاستهلاكي KLIVVR", "BNPL with in-app shop and merchant instalments."),
    ("Khazna", "fra:consumer_finance:37", "https://www.khazna.app",
     "https://techcrunch.com/2022/03/31/egyptian-financial-super-app-khazna-raises-38m-from-quona-capital-and-lendable/",
     "FRA name خزنه للتمويل الاستهلاكي (فاروس سابقا)", "Earned-wage access plus BNPL."),
    ("Shahry", "fra:consumer_finance:36", "https://shahry.app",
     "https://www.paymentsjournal.com/will-carbon-and-shahry-usher-in-a-wave-of-buy-now-pay-later-services-in-africa/",
     "FRA name شهري للتمويل الاستهلاكي", "Merchant-network BNPL."),
    ("Blnk", "fra:consumer_finance:22", "",
     "https://techcrunch.com/2022/11/10/blnk-a-fintech-that-provides-instant-consumer-credit-in-egypt-raises-32m-in-debt-and-equity/",
     "FRA name بلنك للتمويل الاستهلاكي", "Point-of-sale financing at third-party merchants; website not confirmed."),
    ("Lime", "fra:consumer_finance:51", "",
     "https://www.wamda.com/2025/07/fab-lime-app-enters-egypt-fintech-scene-9-4-million-investment-arabic",
     "FRA EN name Lime Consumer Finance", "FAB-owned; education and retail; website not confirmed."),
    ("Bravo", "fra:consumer_finance:52", "",
     "https://fra.gov.eg/en/company_records/%D8%A8%D8%B1%D8%A7%D9%81%D9%88-%D9%84%D9%84%D8%AA%D9%85%D9%88%D9%8A%D9%84-%D8%A7%D9%84%D8%A7%D8%B3%D8%AA%D9%87%D9%84%D8%A7%D9%83%D9%8A-bravo-finance/",
     "FRA name برافو للتمويل الاستهلاكي BRAVO FINANCE", "Brand/website not found; everyday-word brand."),
    ("algo", "fra:consumer_finance:54", "",
     "https://amwalalghad.com/2026/01/19/%D8%A7%D9%84%D8%B1%D9%82%D8%A7%D8%A8%D8%A9-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%8A%D8%A9-%D8%AA%D9%85%D9%86%D8%AD-%D8%B4%D8%B1%D9%83%D8%A9-%D8%A3%D9%88%D8%B1%D8%A7%D9%8A%D9%88%D9%86-algo/",
     "FRA name الجو للتمويل الاستهلاكي (اورايون سابقا)", "Talaat Moustafa Group and AUR partnership (press)."),
    ("ADVA", "fra:consumer_finance:company-67650", "",
     "https://www.forbesmiddleeast.com/money/fintech/maseera-holding-acquires-egypt-based-consumer-finance-firm-adva-for-undisclosed-amount",
     "FRA name ادفا للتمويل الاستهلاكي", "Services instalments; IHC/Maseera owned. No licence number on FRA."),
    ("Manzel Fin", "fra:consumer_finance:company-67653", "", "",
     "FRA name منزل للتمويل الاستهلاكي والتمويل العقاري", "No web presence found; CF and mortgage under one company number."),
    ("Malaz", "fra:consumer_finance:55", "",
     "https://arabic.cnn.com/middle-east/article/2026/09/06/egypt-economy-cairo-education",
     "FRA name ملاذ للتمويل الاستهلاكي",
     "Press: licence approved before FRA Decision 43/2026 suspended new applications."),
    ("Buy and Go", "fra:consumer_finance:50", "",
     "https://amwalalghad.com/2024/12/19/%D8%A8%D8%A7%D9%8A-%D8%A7%D9%86%D8%AF-%D8%AC%D9%88-%D8%AA%D9%82%D8%AA%D8%B1%D8%A8-%D9%85%D9%86-%D8%A7%D9%84%D8%AD%D8%B5%D9%88%D9%84-%D8%B9%D9%84%D9%89-%D8%B1%D8%AE%D8%B5%D8%A9-%D9%85%D8%B2/",
     "FRA name باي اند جو للتمويل الاستهلاكي", "Converted from a commercial-agencies company (FRA decision 3040/2024)."),
    ("معاك", "fra:consumer_finance:47", "", "", "FRA name معاك للتمويل الاستهلاكي",
     "Search found Maak MICROFINANCE (different company number 67423); CF brand unconfirmed."),
    ("O2 Finance", "fra:consumer_finance:46", "https://o2-finance.com", "https://o2-finance.com/about-us/",
     "FRA name اوتو للتمويل الاستهلاكي; EN O2 FINANCE", "Auto financing focus."),
    ("Just Finance", "fra:consumer_finance:45", "https://justfinance-eg.com",
     "https://www.linkedin.com/company/just-finance-egypt",
     "FRA name جاست للتمويل الاستهلاكي (وان للتمويل الاستهلاكي سابقا)",
     "Reported owned via Credit Agricole Egypt real-estate finance arm."),
    ("AUR Consumer Finance", "fra:consumer_finance:40", "",
     "https://www.dailynewsegypt.com/2023/10/15/aur-consumer-finance-to-launch-egp-300m-securitization-bond-issuance-soon/",
     "FRA name اور للتمويل الاستهلاكي", "Brand reported as Waseela; website not confirmed."),
    ("Alkan Finance", "fra:consumer_finance:39", "https://alkanholding.com", "https://cbonds.com/company/601817/",
     "FRA name الكان فاينانس للخدمات الماليه ALKAN FINANCE", "Group site only."),
    ("One Finance", "fra:consumer_finance:34", "https://onefinance.com.eg", "https://onefinance.com.eg/",
     "FRA name وان فاينانس لخدمات التمويل الاستهلاكي",
     "Not the same as Just Finance's former name وان للتمويل الاستهلاكي."),
    ("MOGO", "fra:consumer_finance:32", "https://midtakseet.com",
     "https://www.dailynewsegypt.com/2024/12/04/mid-takseet-rebrands-as-mogo-increases-capital-to-egp-225m/",
     "FRA name ميد بنك للتمويل الاستهلاكي موجو", "Rebranded from Mid Takseet."),
    ("Bedayti", "fra:consumer_finance:31", "https://bedayti.com/en",
     "https://www.zawya.com/en/business/egypts-ekh-ready-to-enter-nbfs-through-launching-bedayti-l5df3f66",
     "FRA name بدايتي للتمويل الاستهلاكي", "Website found is the microfinance sister; CF site unconfirmed."),
    ("myfawry taqseet", "fra:consumer_finance:30", "https://www.fawry.com/bnplbuy-now-pay-later/",
     "https://www.fawry.com/bnplbuy-now-pay-later/", "FRA name فوري للتمويل الاستهلاكي; EN Fawry Consumer Finance",
     "Fawry microfinance/SME licences sit under another company number."),
    ("MLF Finance", "fra:consumer_finance:29", "https://mlf-finance.com", "https://mlf-finance.com/about-us/",
     "FRA name ام ال اف ...", "One company with four licences (CF, leasing, factoring, mortgage)."),
    ("Ollin", "fra:consumer_finance:28", "https://ollin.com.eg", "https://ollin.com.eg/about",
     "FRA name جلوبال كورب للتمويل الاستهلاكي والعقاري(اولين)", "GlobalCorp lifestyle finance; also mortgage #21."),
    ("Takka", "fra:consumer_finance:27", "https://www.adib.eg/Subsidiaries/adiconsumerfinance",
     "https://www.adib.eg/Subsidiaries/adiconsumerfinance", "FRA name ابو ظبي الاسلامي للتمويل الاستهلاكي",
     "ADIB subsidiary marketed as Sharia-compliant (Murabaha). Marketing claim is not a scholar finding."),
    ("ALJ Finance", "fra:consumer_finance:16", "https://www.aljfinance.com.eg", "https://www.aljfinance.com.eg/",
     "FRA name جميل للتمويل (عبد اللطيف جميل للتمويل سابقا)", ""),
    ("Premium Card", "fra:consumer_finance:15", "https://premiumcard.net",
     "https://www.dailynewsegypt.com/2023/10/23/premium-international-to-offer-egp-2-3bn-financing-during-2024/",
     "FRA name بريميوم انترناشيونال لخدمات التمويل", "Card instalments across a merchant network."),
    ("Rawaj", "fra:consumer_finance:14", "https://rawaj-egypt.com", "https://rawaj-egypt.com/about-us/",
     "FRA name رواج للتمويل الاستهلاكي (رواج لتجاره السيارات سابقا)", "Press also cites rawaj-finance.com."),
    ("Sky Finance", "fra:consumer_finance:8", "https://sf.sky.eg/", "https://sf.sky.eg/",
     "FRA name سكاي فاينانس للتمويل الاستهلاكي", "Auto-led."),
    ("seven", "fra:consumer_finance:6", "https://www.beltoneholding.com/NBFIs/consumer-finance",
     "https://www.dailynewsegypt.com/2023/09/25/beltone-rebrands-its-consumer-finance-subsidiary-belcash-to-seven/",
     "FRA name بلتون للتمويل الاستهلاكي (سفن) بل كاش سابقا", "EGX-listed parent Beltone (BTFH)."),
    ("Corplease", "fra:consumer_finance:56", "", "", "FRA name كوربليس للتاجير التمويلي مصر كورب ليس",
     "New CF licence dated 2026-08-24, same company number as Corplease leasing/factoring."),
    ("Orange Egypt", "fra:consumer_finance_providers:41", "",
     "https://www.telecompaper.com/news/orange-egypt-signs-cooperation-agreement-with-contact-creditech--1461894",
     "FRA providers register: اورنج مصر للاتصالات",
     "Registered provider AND distributes Contact Creditech financing in MyOrange: both routes. Orange e-shop "
     "(manual review 2026-10-02) offers 'cash or instalment' (كاش أو قسط); no instalment terms page located."),
    ("SMG", "fra:consumer_finance_providers:18", "", "https://www.alborsaanews.com/2019/07/14/1224834",
     "FRA providers register: اس ام جي لخدمات التقسيط", "Launched by Contact with SMG."),
    ("Abu Ghaly Motors", "fra:consumer_finance_providers:35", "", "",
     "FRA providers register: ابو غالي لخدمات التقسيط",
     "Geely agent. Search shows 'Abou Ghaly Finance' as a partnership with Contact Finance "
     "(geelyautoegypt.com/en/after-sales-services/abou-ghaly-finance; page redirected and was not read): the "
     "creditor in a dealer-branded plan may be Contact, not the provider."),
    ("Rizkalla", "fra:consumer_finance_providers:11", "https://riz.shop",
     "https://riz.shop/en/pages/customer-individual-installment",
     "FRA providers register: ار اي زد جروب للتجاره RIZ GROUP FOR TRADING; riz.shop: 'RizPay direct installment program'",
     "Electronics retailer financing its own sales (manual review 2026-10-02); page does not name the legal entity."),
    ("Mashroey", "fra:consumer_finance_providers:21", "https://mashroey.com",
     "https://mashroey.com/%D8%AA%D9%82%D8%AF%D9%8A%D9%85-%D8%B7%D9%84%D8%A8-%D8%B4%D8%B1%D8%A7%D8%A1/",
     "FRA providers register: مشروعي للتجاره (خدمات استشارات الميكروتمويل مشروعي سابقا)",
     "Motorbikes, tuk-tuks and cars on instalments; hotline 16148 per third-party sites. mashro3y-eg.com looks unofficial."),
    ("Star", "fra:consumer_finance_providers:25", "", "", "FRA providers register: ستار لتقسيط السيارات",
     "Reported Thara Capital subsidiary (third-party directory)."),
]
for brand, key, site, evidence, observed, note in WIDE:
    script = "arabic" if any("؀" <= ch <= "ۿ" for ch in brand) else "latin"
    relation = "brand_of_provider" if "providers" in key else "brand_of_licensee"
    add(brand, script, key, relation, "third_party_report_or_search", "lead", site, "", evidence,
        observed, (note + " " if note else "") + SEARCH)


def apply_lead_confirmation(links, path=Path(__file__).with_name("lead-confirmation-2026-10-03.json")):
    """Overlay the 2026-10-03 one-page-per-company review onto rows still marked lead.

    The JSON is the evidence record; a row keeps its search history in `note` and
    takes the reviewed page as its evidence. Rows that stay lead get the reason.
    """
    import json
    results = {r["licence_key"]: r for r in json.loads(path.read_text(encoding="utf-8"))["results"]}
    for link in links:
        r = results.get(link["licence_key"])
        if r is None or link["status"] not in ("lead", "established") or link["checked_on"] == "2026-10-03":
            continue
        if link["status"] == "established" and r["status"] == "established":
            continue
        reviewed = f"one-page review 2026-10-03: {r['observed']}" + (f" ({r['note']})" if r["note"] else "")
        if r["status"] == "lead":
            link["note"] = f"{link['note']} | still lead after {reviewed}".strip(" |")
        else:
            link.update(status=r["status"], link_basis=r["basis"], evidence_url=r["url"],
                        observed_text=r["observed"], note=(r["note"] + " | earlier: " + link["note"]).strip(" |"))
            if r["url"] and not link["website_url"]:
                link["website_url"] = r["url"].split("/", 3)[0] + "//" + r["url"].split("/", 3)[2]
            if r.get("contact") and not link["corporate_contact"]:
                link["corporate_contact"] = r["contact"]
        link["checked_on"] = "2026-10-03"


apply_lead_confirmation(LINKS)

if __name__ == "__main__":
    write_csv(ROOT / "data/source_registry/fra_brand_links.csv", BRAND_LINK_FIELDS, LINKS)
    print(f"{len(LINKS)} links written")
