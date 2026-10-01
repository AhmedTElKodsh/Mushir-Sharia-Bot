# Pilot five: proposed financiers for the scholar meeting

Proposed by Mary (analyst), 2026-10-01. Resolves open question O3 once the user confirms. Sources: FRA register export `data/runtime/artifacts/l6_scrape/fra_registry/2026-09-23/all/fra_all_companies.csv` (328 rows) and crawl summary `installment_market/2026-09-27/summary/20260927T024008Z-faabcb` (86 entities, 85 payment relationships, 52 with verified page evidence).

> **Update 2026-10-01:** licence numbers in the table below are ambiguous on their own; FRA numbers repeat across activity registers. See [pilot-entity-resolution.md](pilot-entity-resolution.md) for (activity, licence) keys, literal EN/AR names from FRA and each financier's site, and the draft access decisions. User confirmed the five with Halan as control; scholar meeting about 2026-10-15.

> **Superseded in part, 2026-10-01 (later):** Halan is no longer held back as a control. The user decided to send HALAN-01 now, scoped to Halan Shop (in-app appliances/electronics on 6/12/36-month plans). Halan remains outside evidence-qualified coverage until a legal entity and the arrangement are evidenced. Halan and Aman, both financiers that run their own store, are to be shown side by side at the review. Current state: [provider priorities](acquisition-templates/provider-request-priorities-2026-10-01.md). The text below is kept as written.

## Selection rule

A pilot financier must (1) appear in the FRA register under a matching legal name, (2) have verified page evidence that merchants or the financier itself offer instalments through it, and (3) be crawlable without login, CAPTCHA or a permission we don't hold (spec Constraints).

This is a proposal for four evidence-backed candidates plus one deliberately insufficient-evidence control (Halan). Halan does not satisfy criterion 2 and does not count as evidence-qualified coverage. Even the four candidates still require the licence/detail and dated-page rechecks below before dossier acceptance.

## The five

| # | Financier | FRA register match (licence no.) | Verified merchant/self evidence | Why it's in |
|---|---|---|---|---|
| 1 | **valU** | U Consumer Finance (13) | 8 verified rows: IKEA Egypt, Smart Furniture, RUSHBRUSH, Lazurde, Vienna Dental Clinic, Jumia… | Widest merchant reach; tests the "which merchant, which plan" question |
| 2 | **Contact** | Contact co. (17) and related entities (8, 19) | 6 verified: own laptop, phone and car finance pages; Smart Furniture; Vodafone eShop | Both a self-published offer and merchant links; legal-name ambiguity across several Contact entities tests entity resolution |
| 3 | **Souhoola** | CI Consumer Finance Souhoola co. (10) | 6 verified: IKEA Egypt, Smart Furniture, RUSHBRUSH, Jumia | Overlaps valU at the same merchants, so a "which financier?" clarification is real |
| 4 | **Aman** | Aman Consumer Finance (43) — distinct from Aman for Micro-finance (4) | Aman store pages: electronics and phone instalments | Financier that also runs its own store; tests seller vs financier role split |
| 5 | **Halan — insufficient-evidence control** | Proposed match: Halan for consumer finance co. (23), detail verification pending | 1 merchant claim (Smart Furniture), no verified page yet | Deliberate "unknown, with reason" example; excluded from evidence-qualified coverage |

Anchor merchants for the dossiers' link graph: IKEA Egypt, Smart Furniture and RUSHBRUSH. Each names two or more of the five.

## Left out, and why

- **Mylo (B.TECH):** has evidence (2 verified), but B.TECH automation needs permission (spec Constraints), and no FRA row matches the name "Mylo", so the legal entity is unconfirmed.
- **Sympl, Forsa:** named by one merchant each, with no FRA match found under those names.
- **Banks** (Banque Misr, HSBC, QNB…): regulated by the CBE rather than the FRA consumer-finance register; out of the V1.6 lane.

## Caveats the room insisted on

- Evidence counts come from one crawl (2026-09-27). Each dossier must re-check its page before the meeting and record the capture date.
- Name matching was done by text search over the register. The licence numbers above need a human eye on each `company_detail_url` before the scholar sees them.
- None of this is a Sharia finding. Each dossier shows dated, cited public terms and marks every unobserved field unknown with a reason.
