# Pilot five: proposed financiers for the scholar meeting

Proposed by Mary (analyst), 2026-10-01. Resolves open question O3 once the user confirms. Sources: FRA register export `data/runtime/artifacts/l6_scrape/fra_registry/2026-09-23/all/fra_all_companies.csv` (328 rows) and crawl summary `installment_market/2026-09-27/summary/20260927T024008Z-faabcb` (86 entities, 85 payment relationships, 52 with verified page evidence).

## Selection rule

A pilot financier must (1) appear in the FRA register under a matching legal name, (2) have verified page evidence that merchants or the financier itself offer instalments through it, and (3) be crawlable without login, CAPTCHA or a permission we don't hold (spec Constraints).

## The five

| # | Financier | FRA register match (licence no.) | Verified merchant/self evidence | Why it's in |
|---|---|---|---|---|
| 1 | **valU** | U Consumer Finance (13) | 8 verified rows: IKEA Egypt, Smart Furniture, RUSHBRUSH, Lazurde, Vienna Dental Clinic, Jumia… | Widest merchant reach; tests the "which merchant, which plan" question |
| 2 | **Contact** | Contact co. (17) and related entities (8, 19) | 6 verified: own laptop, phone and car finance pages; Smart Furniture; Vodafone eShop | Both a self-published offer and merchant links; legal-name ambiguity across several Contact entities tests entity resolution |
| 3 | **Souhoola** | CI Consumer Finance Souhoola co. (10) | 6 verified: IKEA Egypt, Smart Furniture, RUSHBRUSH, Jumia | Overlaps valU at the same merchants, so a "which financier?" clarification is real |
| 4 | **Aman** | Aman Consumer Finance (43) — distinct from Aman for Micro-finance (4) | Aman store pages: electronics and phone instalments | Financier that also runs its own store; tests seller vs financier role split |
| 5 | **Halan** | Halan for consumer finance co. (23) | 1 merchant claim (Smart Furniture), no verified page yet | Licensed and named by a merchant; the thin evidence is deliberate: it shows the scholar what an "unknown, with reason" dossier looks like |

Anchor merchants for the dossiers' link graph: IKEA Egypt, Smart Furniture and RUSHBRUSH. Each names two or more of the five.

## Left out, and why

- **Mylo (B.TECH):** has evidence (2 verified), but B.TECH automation needs permission (spec Constraints), and no FRA row matches the name "Mylo", so the legal entity is unconfirmed.
- **Sympl, Forsa:** named by one merchant each, with no FRA match found under those names.
- **Banks** (Banque Misr, HSBC, QNB…): regulated by the CBE rather than the FRA consumer-finance register; out of the V1.6 lane.

## Caveats the room insisted on

- Evidence counts come from one crawl (2026-09-27). Each dossier must re-check its page before the meeting and record the capture date.
- Name matching was done by text search over the register. The licence numbers above need a human eye on each `company_detail_url` before the scholar sees them.
- None of this is a Sharia finding. Each dossier shows dated, cited public terms and marks every unobserved field unknown with a reason.
