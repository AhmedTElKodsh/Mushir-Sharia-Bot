# FRA-first company database: build and review, 2026-10-02

Requested by the user after the party-mode double review: run the offline fixes, scrape FRA fully, make FRA the starting point for company discovery, fix the dedupe bug and the "no FRA match" notes, apply the regulator's own taxonomy, add B.TECH/Mylo and Drive/Forsa to the pilot, and keep valU as an established financier. This file is the "review after".

## What the FRA capture now holds

| Run (2026-10-02) | Rows | Status |
|---|---|---|
| `consumer-finance-providers` (مقدمي التمويل الاستهلاكي) | 13 | complete; first typed capture of this register |
| `consumer-finance` (تمويل استهلاكي) | 39 | complete; +1 since 2026-09-23 (Corplease #56, licensed 2026-08-24) |
| `all` (every financing register) | 389 licences | complete; 47 companies hold more than one licence |

The 2026-09-23 "all" export wrote **328 rows from 388 licence pages**. It silently dropped 60 licences that shared a company number with an earlier row, among them Drive Finance's consumer-finance #26 (Forsa) and MLF's #29. Re-parsing the saved pages offline recovered all 388 (0 missing, 0 identity mismatches). Today's live run then matched that, plus #56. Nothing disappeared between the two dates.

FRA answers `/robots.txt` with a "Request Rejected" security page but serves the public register normally to our identified research bot. That state is now recorded as `security_response` and needs its own acknowledgement. The user authorized this capture; see the [access decision](acquisition-templates/fra-first-2026-10-02/fra-access-decision.md). No security response came from any register page.

## The regulator's taxonomy, in its own words

FRA's consolidated consumer-finance guide (September 2026, 123 pages, captured) defines the category on p.11:

> مقدمي التمويل الاستهلاكي: منتجو السلع أو موزعوها الذين يزاولون نشاط التمويل الاستهلاكي

Consumer-finance providers are *producers or distributors of goods who practise consumer finance*. That is the seller-finances-own-goods category. Licensed consumer-finance companies (تمويل استهلاكي) are a separate register. Every entity row carries `fra_register_role`. The register is a lead about the holder; each arrangement is still classified from its own contract.

## FRA's model contracts: the baseline for "what the customer signs"

The same guide, p.91: licensed companies **must comply with the provisions of the attached model contracts as a minimum**, with Law 18/2020 and its decrees supplementing them. It contains:

- **Model (1):** guiding contract for a single consumer-finance transaction (pp. 91–96)
- **Model (2):** multi-transaction contract through payment cards (pp. 97–101)
- **Model (3):** group life-insurance contract covering consumer-finance customers (p. 102 onward)
- References to **Circular 6/2024** on transferring credit portfolios to another licensee, bank or securitization company: the receivable-assignment question

These are the strongest public source yet for the scholar's third question. They give the minimum skeleton of every licensed customer contract, without touching any provider's website. Text layers are saved under `data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02/derived/`. Verify the Arabic against page images before quoting. Also captured: FRA's customer-protection guide (120 pp.) and the Law 18/2020 PDF, whose text layer did not yield key terms and needs page-image or OCR reading.

## FRA contract templates and Sharia material (added on request, same day)

A bounded crawl of named FRA publication pages (see the extended [access decision](acquisition-templates/fra-first-2026-10-02/fra-access-decision.md)) captured **111 documents**. They are indexed in `data/source_registry/fra_documents_catalogue.csv`, with link text, source page, page count, text-layer quality, and the pages where contract and Sharia terms occur. Raw files stay in `data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02/` (not committed).

**Sharia model contracts** (FRA page *Islamic Products and Contracts*; Arabic, readable text):

| Template | Pages |
|---|---|
| Model Murabaha and service-Murabaha agreement for consumer finance (Law 18/2020) | 6 |
| Ijarah Muntahia Bittamleek (lease-to-own) | 7 |
| Micro-Murabaha purchase-order contract | 4 |
| Diminishing Musharaka (micro) | 6 |
| Wakala bil-Istithmar (investment agency, micro) | 3 |

The English page links the Wakala template to the Ijarah file; the Arabic page links the correct file.

**What the scholar should see in the Murabaha consumer-finance template.** These are flagged, not ruled on:
- The party fields are blank, but the preamble (p.1) and the definition of Murabaha (p.2) name **Aman**: Murabaha is Aman buying goods from suppliers and reselling them to consumers. This looks like a model derived from Aman's Islamic product. It is a lead for AMAN-01's Islamic pack, not proof of Aman's current operative contract.
- p.3: the company authorizes the supplier/merchant to deliver the goods to the customer **and issue the invoice directly in the customer's name**. That sits in tension with the template's own buy-then-resell definition. Ownership and possession before resale is a test the scholar applies under AAOIFI's Murabaha standard.
- p.4: late payment is handled under a *غرامة الضرر* (damages penalty) clause. Its beneficiary and use are a further point for the scholar.

**Conventional contract models:** consumer-finance Models (1) and (2) (guide pp. 91–101), the factoring guide (contract-model references p.78), and the real-estate finance guide (Murabaha clauses pp. 47–49, a Sharia committee reference p.40).

**Sharia governance:**
- The Central Sharia Supervisory Committee's decrees, and four of its published rulings on sukuk: direct issuance by the beneficiary, distressed companies, early redemption, and redemption at market value.
- Board Decree 310/2025, which reconstitutes the committee for sukuk *and non-bank financial products*.
- The Takaful controls (Decree 23/2019) and the Islamic-finance overview page (Arabic and English). Its stated principles include the prohibitions on combining loan and sale and on selling what one does not own.

**Sub-Sharia committee rule.** Any non-bank financial company offering products described as Sharia-compliant must have its contracts reviewed by a sub-Sharia committee of 3–5 registered members. FRA's register lists **48 individual members (17 not renewed)**. It does not say which company each serves. Member emails were removed from derived text, in line with the no-personal-data scope.

**OCR (2026-10-03).** All 51 scanned documents (812 pages) were OCR'd offline with the Windows built-in engine (ar-SA). Arabic-dominant lines were word-reversed to restore reading order, and no page came out empty. Output is in `.../fra_documents/2026-10-02/derived/ocr/<sha>.json|.txt`, and the catalogue's `text_layer` now reads `ocr (...)`, with `ocr_path`. EasyOCR was tried first: on this machine (about 2 GB free RAM) its detector crashed at full page size and ran about 80 s/page at a reduced size, so it was removed. OCR text is a reading aid with typical slips (الشيئة for الهيئة, dropped digits); check the page image before quoting. What the OCR made readable:

- **Chairman's Decree 457/2020** (8 Apr 2020): the consumer-finance contract model. Its Article 1 binds **both consumer-finance companies and licensed consumer-finance providers** (seller-financiers) to a minimum list of contract contents. The same baseline therefore applies to B.TECH's minicash or Raya's Takseety as to valU or Contact.
- **Chairman's Decree 869/2021** (1 Jun 2021, Official Gazette no. 135): "on consumer-finance contract models", 11 pages, issuing the models. It cites Board Decree 56/2020 on licensing companies and providers.
- **Central Sharia Supervisory Committee rulings 1–4 on sukuk (2019).** Ruling 4 holds that the legal requirement to redeem sukuk at *nominal* value conflicts with Sharia; redemption must be at *market* value, on the principle of sharing in gain and loss (الغنم والغرم). This is the regulator's own Sharia body reasoning that a guaranteed principal breaks risk-sharing, a precedent the scholar may want next to consumer-finance guarantees.
- Board Decree 23/2019 (Takaful controls), Decrees 42/2019, 176–177/2022 and 310/2025 (Sharia committee mandates), the model sukuk prospectus, and the fund and sukuk information memoranda.

**Gaps:**
- ~~51 documents need OCR~~ Done (above).
- 14 sukuk/fund prospectuses exceeded the 10 MB cap.
- One sukuk study PDF drew FRA's "Request Rejected" page, apparently a URL-length rule; it was not retried.
- One old PDF timed out.

## Company table and brand resolution

`data/source_registry/fra_consumer_finance_entities.csv`: 52 rows (39 + 13).

| Link status | Rows | Meaning |
|---|---|---|
| established | 4 | first-party document names the licensee: valU #13, Contact Credit Tech #33, Drive Finance #26, B.TECH #7 |
| verified | 6 | FRA register name or first-party parent statement |
| lead | 41 | web search or press, or a first-party page that does not name the entity |
| unlinked | 1 | Fine Stone (providers register) |

Market financier labels now resolve as follows (`fra_market_label_resolution.csv`): valU (all spellings), Contact, Souhoola, Aman, Halan, Mylo and Forsa resolve to FRA licences; the 10 bank labels read `bank_outside_fra_register`. Only **Sympl** remains `not_found_by_name`.

## Pilot: seven financiers, two contrast pairs

| Financier | Licence | Link | Note |
|---|---|---|---|
| valU | CF #13 | established | kept as established financier (user decision) |
| Contact | CF #1, #33, #49; providers #17, #19, #24; factoring #8 | #33 established | appendix names Contact Credit Tech |
| Souhoola | CF #10 | verified | three legal names still unresolved |
| Aman | CF #43 / providers #2 | verified / lead | contrast pair |
| Halan | CF #23 (+ factoring #50 under another company) | verified | Halan Shop vs external vendors |
| **B.TECH / Mylo** | CF #48 / providers #7 | verified | contrast pair; Mylo terms gated behind Google sign-in |
| **Drive / Forsa** | CF #26 + factoring #3 | **established** | Forsa privacy page: CR 164123, FRA factoring 3 and consumer finance 26 |

## Seller-financier pass (providers register, 13 entities)

The user chose to work these first: they are the regulator's own answer to "does the company sell and finance the goods itself". Each was checked against first-party pages read in an ordinary browser (manual public-page review).

| Provider | Status | What the company's own pages say |
|---|---|---|
| B.TECH #7 | **established** | Terms: "خدمات الميني كاش تقدم تحت ترخيص الهيئة العامة للرقابة المالية رقم 7/2020". B.TECH's credit department approves instalments and computes the interest. Mylo runs separately through B.TECH Finance (#48). |
| Raya #3 | verified | Takseety is "برنامج تمويل مباشر حصري مملوك لشركة راية" (an exclusive direct financing programme owned by Raya). **But** the shop's terms contract party is شركة راية للتجارة (Raya Trade), while FRA registers رايه للالكترونيات (Raya Electronics). Which entity extends the credit is open. |
| Rizkalla (RIZ Group) #11 | lead | riz.shop: "RizPay direct installment program"; legal entity not named on the page |
| Aman Financial Services #2 | lead | Press (2020-04-28) reports the provider licence. Aman's pages sell through its store, merchants and branches under one brand; none names #2. |
| Orange Egypt #41 | lead | e-shop offers "cash or instalment"; also distributes Contact Creditech financing. Both routes, terms not located. |
| Abou Ghaly #35 | lead | Search: "Abou Ghaly Finance" is a partnership with **Contact** Finance |
| Contact family #17, #19, #24; SMG #18 | lead | Contact-linked car dealers (SMG launched with Contact) |
| Mashroey #21, Star #25 | lead | instalment sellers of motorbikes/tuk-tuks and cars; third-party sources only |
| Fine Stone #38 | unlinked | no web presence found |

**Two findings for the scholar.**
1. The register's "seller finances its own goods" category hides a second layer. A dealer-branded plan (Abou Ghaly, SMG, Ezz Elarab) can carry a Contact company as the real creditor, and Raya's seller and registered provider are different legal entities. The contract, not the brand or the register, decides who sells and who lends.
2. Law 18/2020 requires sellers to register only above an annual financing threshold set by FRA (at least EGP 25m, per press). Smaller shops that finance their own goods can operate without appearing in the register. The register is complete for large sellers only.

## Corrections made during this work

- **Mylo → #48 downgraded to `verified`.** Search-index text says Mylo's terms name B.TECH Finance, but the page required a Google sign-in, so it was not read. B.TECH's public page says only "powered by B.TECH".
- **Pilot-five row 2:** "Contact co. (17)" is on the providers register, not the consumer-finance register.
- **Unnumbered licensees:** Telda, ADVA and Manzel have no published licence number. They are keyed by company number so they do not collide.

## Review: what is still weak

1. 40 of 52 links are leads. The next step for each is one first-party page that names the legal entity (terms, privacy policy or footer). Forsa shows how much that single page settles.
2. Press reported **48** licensed consumer-finance companies at end-2025; the register shows **39**. Unexplained. Candidates are revocations, mergers, or a register that lists only active licences. FRA Decision 43/2026 suspended new applications.
3. "Sharia-compliant" marketing claims (Mylo, ADI/Takka, Aman's Islamic product) are recorded as marketing only.
4. The double review's other open findings are untouched (summarizer negation, redirect path policy, CrawlerEngine): deferred item 11.
5. Arabic text from PDFs is unreviewed; human-review marks apply before anything reaches the scholar.

## How to reproduce

```powershell
.\.venv\Scripts\python.exe scripts/scrape_fra_registry.py --fra-type consumer-finance-providers --fra-type-ar "مقدمي التمويل الاستهلاكي" --output-dir <new dir> --delay-seconds 2 --site-terms-review-state no-separate-terms-found --acknowledge-robots-security-response
.\.venv\Scripts\python.exe scripts/rebuild_fra_licence_register.py <run>/manifest.json <new dir>
.\.venv\Scripts\python.exe _bmad-output/initiative-egypt-market-knowledge/acquisition-templates/fra-first-2026-10-02/build_brand_links.py
.\.venv\Scripts\python.exe scripts/build_fra_entity_table.py --licences <all-licences csv> <cf csv> <providers csv>
```
