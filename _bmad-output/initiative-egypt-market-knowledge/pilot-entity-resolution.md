# Pilot entity resolution: who each financier legally is (worksheet)

Prepared 2026-10-01 for epic-pilot-dossiers ticket 2 (person sign-off). Status: **resolutions accepted by the user on 2026-10-01; robots unavailability acknowledged for fra.gov.eg and souhoola.com.** All names found stay in [`data/source_registry/pilot_entity_names.csv`](../../data/source_registry/pilot_entity_names.csv) (61 rows) as `pending_client_review`. Acquisition rules: [evidence-acquisition-playbook.md](evidence-acquisition-playbook.md). Nothing here is a Sharia finding.

## How this was built

Two independent source families were compared. Names are copied **literally** from each source; no English or Arabic name was produced by translating or transliterating the other.

1. **Regulator (FRA):** the 2026-09-23 register export (`fra_registry/2026-09-23/all/fra_all_companies.csv`, 328 rows), plus a fresh capture of each candidate's FRA detail page on 2026-10-01. The detail pages also show **phone and email**, which the export lacks. All 12 detail pages matched the 09-23 export field for field.
2. **The financiers' own websites** (home page in both languages, and about/terms/privacy pages where linked), captured 2026-10-01.

Raw captures, sha256 hashes and a JSONL manifest are in ignored `data/runtime/artifacts/l6_scrape/entity_resolution/2026-10-01/`. Parsed FRA records are in `fra_detail_records.json` there. The reusable capture script is `scripts/capture_entity_identity_pages.py`.

## Rules learned (apply to all future entity work)

- **An FRA licence number is not an identity.** Numbers are unique only within an activity register: 328 rows share 253 numbers, and 45 numbers repeat. "Licence 1" is four different companies (factoring, consumer finance, mortgage, microfinance). The key is **(activity, licence number)**, or the detail URL.
- **There are two consumer-finance activity labels:** "تمويل استهلاكي" and "مقدمي التمويل الاستهلاكي". Both are kept verbatim.
- **Arabic and English names can disagree inside one FRA row.** For example, Souhoola's Arabic name shows a rebrand (BM, formerly CI) that its English column does not.
- **Brand spelling varies within one company.** valU's own site spells the Arabic brand both **فاليو** (279 times) and **ڤاليو** (31 times, with veh). Both are recorded as observed spellings. ڤ is not folded into ف.
- **A brand can sit across several legal entities.** For valU, the consumer-facing app company and the FRA-licensed financier are different companies (see below).

## Per-financier evidence

Each cell gives the text exactly as written in that source.

### 1. valU

| Source (captured) | English name | Arabic name | Identifiers |
|---|---|---|---|
| FRA detail, تمويل استهلاكي #13 (2026-10-01) | U Consumer Finance | يو للتمويل الاستهلاكي ( فاليو للتمويل الاستهلاكي(سايقا)) VALU CONSUMER FINANCE فاليو لخدمات البيع بالتقسيط VAIU سابقا | company no. 5501163; licensed 2020-10-21; email contact_us@valu.com.eg |
| valugroup.com/terms-and-conditions (2026-10-01) | ValU ("شركة فاليو") / U Consumer Finance (ش.م.م) | فاليو للمدفوعات والحلول التقنية ش.م.م; parent: يو للتمويل الاستهلاكي (فاليو للتمويل الاستهلاكي سابقا) | app company: commercial register 119489. Parent: FRA consumer-finance licence "رقم 13 لسنة 2020", commercial register 34260 |
| valugroup.com/privacy-policy | n/a | فاليو للمدفوعات والحلول التقنية ش.م.م, a subsidiary of مجموعة اى اف جي القابضة ش.م.م | Group link to EFG Holding |
| valugroup.com (home) | Valu ("Copyright © 2026 Valu") | ڤاليو / فاليو (brand) | www.valu.com.eg redirected to valugroup.com during this capture |

**Resolution (proposed):** the financing party is **U Consumer Finance / يو للتمويل الاستهلاكي**, FRA (تمويل استهلاكي, 13). The app and payments operator **فاليو للمدفوعات والحلول التقنية ش.م.م** is a *different* company that does not appear in the FRA rows checked. Any dossier must keep these two apart. The site's own terms state this relationship, so we are not inferring it.

### 2. Contact

| Source | English name | Arabic name | Activity, licence no. | Licence date | Email on FRA page |
|---|---|---|---|---|---|
| FRA | CONTACT CAR TRADING | كونتكت للتمويل | تمويل استهلاكي, 1 | 2020-04-16 | info@sarwa.capital.com |
| FRA | Contact co. | عز العرب كونتكت فايننشال | مقدمي التمويل الاستهلاكي, 17 | 2021-01-31 | www.contact.eg |
| FRA | contact | كونتكت لتقسيط السيارات ( كونتكت المصريه العالميه لتقسيط السيارات سابقا ) | مقدمي التمويل الاستهلاكي, 19 | 2021-03-07 | www.contact.eg |
| FRA | *(No data exists)* | بافاريان كونتكت لتجاره السيارات | مقدمي التمويل الاستهلاكي, 24 | 2021-05-30 | none |
| FRA | Contact Credi Tech S.A.E | كونتكت كريدي تك للتمويل الاستهلاكي CONTACT CREDITECH | تمويل استهلاكي, 33 | 2022-04-28 | info@contact.eg |
| FRA | *(No data exists)* | جلوبال كونتكت للتمويل الاستهلاكي GLOBAL CONTACT FINANCE | تمويل استهلاكي, 49 | 2024-08-06 | none |
| FRA (not consumer finance) | Contact Factoring S.A.E | كونتكت للتخصيم ( بلس للتخصيم سابقا ) | تخصيم, 8 | 2017-07-06 | info@sarwa.capital |
| contact.eg/en (title) | Contact Financial Holding | n/a | | | |
| contact.eg (Arabic title) | n/a | كونتكت \| أول شركة تمويل استهلاكي في مصر | | | |
| contactcars.com | Contact Cars (EN page) | كونتكت كارز (AR title) | | | |

**Resolution (proposed):** **unresolved by design.** Six consumer-finance entities carry the brand. The consumer site names the holding company, not a licensed entity. The **sarwa.capital** emails on #1 and #8 suggest a group link that we have not verified. For any merchant claim ("instalments with Contact"), the financing entity stays `contact_brand_unresolved` until a merchant page or an agreement names the legal entity. This is exactly the clarification the bot asks for. Strongest consumer-instalment candidates, by email domain only and not established: #33 (info@contact.eg), then #17 and #19.

### 3. Souhoola

| Source | English name | Arabic name | Identifiers |
|---|---|---|---|
| FRA detail, تمويل استهلاكي #10 | CI Consumer Finance Souhoola co. | بي ام للتمويل الاستهلاكي سهوله SAE(سي اي للتمويل الاستهلاكي سهوله سابقا) | company no. 5501167; licensed 2020-09-24; email info@souhoola.com |
| souhoola.com and souhoola.com/ar (title, both languages) | Souhoola, CI Consumer Finance | *(Arabic page title is in English; no Arabic legal name found)* | |

**Resolution (proposed):** FRA (تمويل استهلاكي, 10). There is a **recorded mismatch**: the FRA Arabic name shows the rebrand to **بي ام** (formerly **سي اي**), while the FRA English name and the website still say **CI**. Both are kept. We did not reconcile them, and we did not invent an English "BM …" name. The Arabic brand spelling on the site still needs a deeper capture, because the Arabic page is client-rendered.

### 4. Aman

| Source | English name | Arabic name | Identifiers |
|---|---|---|---|
| FRA detail, تمويل استهلاكي #43 | Aman Consumer Finance (S.A.M) | امان للتمويل الاستهلاكي | company no. 67639; licensed 2023-02-05; phone 38276000; no email |
| aman.eg/en (footer) | Aman Holding corp ("All rights reserved@Aman Holding corp") | n/a | |
| aman.eg/ar (footer) | n/a | شركة أمان القابضة ("جميع الحقوق محفوظة @شركة أمان القابضة") | |

**Resolution (proposed):** FRA (تمويل استهلاكي, 43). The site is published by the **holding company**, not the licensee. Aman for Micro-finance is a separate register entity and is excluded. Note that أمان is also an everyday Arabic word meaning "safety", so passage matching needs review (flagged by the summarizer).

### 5. Halan (insufficient-evidence control)

| Source | English name | Arabic name | Identifiers |
|---|---|---|---|
| FRA detail, تمويل استهلاكي #23 | Halan for consumer finance co. | حالا للتمويل الاستهلاكي | company no. 676006; licensed 2021-05-31; email info@halan.com |
| FRA detail, تخصيم #50 | *(No data exists)* | حالا لخدمات التمويل غير المصرفيه | licensed **2026-07-06**; factoring, not consumer finance |
| halan.com (EN) | Halan ("© 2026, Halan All right reserved") | n/a | |
| halan.com/ar | n/a | حالا (in body text, e.g. "مشروعك مع حالا") | |

**Resolution (proposed):** FRA (تمويل استهلاكي, 23) is the consumer-finance match. #50 is a new factoring licence and is recorded so nobody mistakes it for the consumer licensee. The site names no legal entity. Halan stays the **insufficient-evidence control**: the register match exists, but no verified passage establishes a merchant financing relationship (see the summarizer finding below).

## Cross-check with the 2026-09-27 market crawl (ticket 5 re-run)

With the passage-must-name-the-financier rule, financier links fell from **46 to 29**. Relevant drops and checks for the pilot five:
- **Smart Furniture → Contact / Souhoola:** the stored passages quote "(ValU)", not Contact or Souhoola. A passage naming one financier must not credit another.
- **Vodafone eShop → Contact:** the passage never names Contact (dropped).
- **Contact's own car-finance page:** the passage never repeats "Contact". It was dropped by the rule. **Decision for you:** should a provider's own host count as naming it?
- **Carrefour → valU, Vezeeta → valU:** no passage (robots unavailable or disallowed), so dropped.
- All four "Contact" matches that were kept are flagged as everyday-word matches for review.

## Draft access decisions (ticket 2, needs your sign-off)

| Host | robots.txt (2026-10-01) | Captures so far | Proposed decision |
|---|---|---|---|
| fra.gov.eg | **Unavailable:** returns a firewall "Request Rejected" page, no directives. The 2026-09-23 register run recorded `robots_unavailable_acknowledged: true` | 12 detail pages, **captured before the project robots rule was applied**; correction records appended to the manifest | Acknowledge again for read-only register detail pages at about 2 s spacing, or reject the 10-01 captures |
| valugroup.com (www.valu.com.eg redirects here) | `Allow: /` | home, about, privacy, terms (EN/AR) | Allow public pages; nothing behind the app or login |
| contact.eg | `Allow: /` | home EN/AR | Allow public pages; stop at application forms |
| www.contactcars.com | Blocks a list of named bad bots; for `*` only `/…/account/dealer-profile` is disallowed | home EN/AR | Allow public pages; stop at account and finance-application steps |
| souhoola.com | **Unavailable:** robots.txt returns the app's HTML page, no directives | home EN/AR, **captured before the rule was applied**; correction appended | Needs your acknowledgement, or treat as unavailable and use merchant pages only |
| aman.eg | Only `/wp-admin/` disallowed | home EN/AR | Allow public pages |
| halan.com | Only `/cdn-cgi/` disallowed | home EN/AR, about | Allow public pages; stop at app/loan application |

Site terms of use have **not** been read for any host yet. That human check is part of ticket 2. B.TECH, Amazon and noon stay in the permission queue (epic Done-when #4).

## Open items for sign-off

1. Accept the resolutions above (valU = #13 consumer finance, separate from the app company; Contact = brand unresolved across six entities; Souhoola = #10 with the CI/BM mismatch kept; Aman = #43; Halan = #23, control).
2. Acknowledge, or not, the unavailable robots for fra.gov.eg and souhoola.com, and say what happens to the 10-01 captures from those hosts.
3. Should a provider's own host count as naming the provider in passages (the Contact car-finance case)?
4. Deeper digging still to do: Contact's group structure (the sarwa.capital link), Souhoola's Arabic brand spelling on the client-rendered pages, and the FRA licensee names on merchant terms pages (IKEA, Smart Furniture, RUSHBRUSH).

## Second pass, 2026-10-01 (after sign-off): more names found

Using sitemaps, about, board and terms pages, a browser render and the Wayback archive:

- **valU:** the Arabic about page states the legal name outright: "الاسم القانوني: (U Consumer Finance S.A.E) كود (EGX: VALU.CA)". The privacy policy names the parent group **مجموعة اى اف جي القابضة ش.م.م**. valU also operates in **Jordan** (a separate jurisdiction; that entity is not captured; `/jo/about-us` redirected to the Egyptian page).
- **Contact:** the holding company is named **كونتكت المالية القابضة** (AR) / **Contact Financial Holding** (EN). The management list also names **Sarwa Insurance**, **Contact Credit** and "Contact Mortgage, Leasing, and Factoring". "Contact Credit" does not match any FRA name we have checked.
- **Souhoola:** the terms (rendered in the browser; "Last Updated: February 2026") say the services are "provided by **Contact Investment for Consumer Finance** ("Souhoola")". That is a **third name** for FRA #10, alongside "CI Consumer Finance Souhoola co." (FRA English) and "بي ام للتمويل الاستهلاكي سهوله" (FRA Arabic). The address matches FRA #10, which links the name to the licence. No FRA row carries this English name. Whether Souhoola now belongs to the Contact group is **not established**; that needs official sources (playbook #5, #6). The Wayback archive shows the site title "Souhoola, CI Consumer Finance" unchanged from 2022 to 2026.
- **Aman:** the parent company is named differently in each language. EN: "A subsidiary Company of **Raya For Financial Investments**". AR: "إحدى شركات **راية للخدمات المالية**". Both are kept, unreconciled.
- **Halan:** "Halan Consumer Finance" (product page) and "شركة حالا في عام 2017" (Arabic about page). No legal entity named on the site.
