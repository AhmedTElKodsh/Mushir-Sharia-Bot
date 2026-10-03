# FRA consumer-finance model contracts: 2021 vs 2026

Prepared 2026-10-03 for the scholar file. It compares FRA's guiding model contracts as issued by Chairman's Decree 869/2021 with the versions in FRA's September 2026 consumer-finance rulebook, and checks both against the minimum list in Chairman's Decree 457/2020. It is a regulatory document comparison. **It makes no Sharia finding**; the questions at the end are for the scholar.

## Sources

| Document | Date | Pages used | Text basis |
|---|---|---|---|
| Chairman's Decree 457/2020, "on the consumer-finance contract model" | 8 Apr 2020 | 2 | OCR (Windows, ar-SA), checked against page images |
| Chairman's Decree 869/2021, "on consumer-finance contract models", Official Gazette no. 135 | 1 Jun 2021 (published 17 Jun 2021) | 11 (Model 1: pp. 2–6, Model 2: pp. 7–11) | OCR, with every reported difference checked against the page image |
| FRA rulebook (دليل القواعد والضوابط والمعايير المنظمة لعمل شركات التمويل الاستهلاكي), Part 6 | Sep 2026 | pp. 91–101 | PDF text layer; table placement checked against the page image |

Files and hashes are listed in `data/source_registry/fra_documents_catalogue.csv` (Decree 869: `652b14f7…`, Decree 457: `af8e53a3…`). OCR text is in `data/runtime/artifacts/l6_scrape/fra_documents/2026-10-02/derived/ocr/`.

**Method note.** A first pass on OCR text alone produced three apparent "changes" that the page images disproved:
- the financing table "moving" from Clause 4 to Clause 6 (a text-extraction artifact in 2026);
- a "new" admin-fee sentence in Clause 9 (present in 2021; the OCR missed it);
- a "new" percent sign in Clause 10 (present in 2021).

Only differences confirmed on the page images are reported below.

## Bottom line

1. **The model contracts did not change in substance between 2021 and 2026.** Both models keep the same 15 clauses in the same order with the same obligations. The 2026 rulebook republishes them under the same binding sentence: licensed companies must follow them **as a minimum**, with Law 18/2020 and its decrees supplementing them.
2. **One wording change, in both models:** the promissory notes, bills of exchange and cheques that the financier may require are called **"commercial papers"** (الأوراق التجارية) in 2021, and **"guarantees"** (الضمانات) in 2026. The financier hands back each "commercial paper" (2021) or "guarantee" (2026) as the corresponding instalment is paid.
3. **The 2026 rulebook lists 869/2021 as an in-force decree but does not list 457/2020.** Whether 457's minimum list, its application to sellers that finance their own goods, and its rule that each company's own contract must be FRA-approved before use still apply is **a legal question to confirm**.
4. **Several terms the scholar will look for are in neither model:** late payment and default, ownership and delivery of the goods, defects and returns, insurance (a separate model in 2026), and any Sharia structure. Companies write these into their own contracts, which is why the company contracts, not the FRA model, settle the scholar's questions.

## Model (1): single financing transaction, clause by clause

| # | Clause | 2021 (Decree 869) | 2026 rulebook | Change |
|---|---|---|---|---|
| — | Parties and preamble | Company (CR no., FRA licence no.) and customer (ID); company is licensed to practise consumer finance | Same | None |
| 1 | Definitions | Company, customer, FRA, "the law" (Law 18/2020, executive regulations, FRA board decrees) | Same | None |
| 2 | Status of preamble, annexes, correspondence | Law 18/2020 and FRA decrees form part of the contract and **prevail over conflicting contract terms** | Same | None |
| 3 | Subject | "The company **provides the financing needed to purchase** consumer goods or services" eligible under the law, at the customer's request | Same | None |
| 4 | Financing amount and return rate | Table: financing type, amount, term, number of instalments, financing costs, **annual/monthly return**, admin fees, other fees, monthly instalment, first and last dates, total payable. Financier may require promissory notes/bills/cheques, called **"commercial papers"** | Same table, same place. The notes/bills/cheques are now called **"guarantees"** | **Wording** |
| 5 | Term | Term = repayment period in Clause 4; contract ends only after the debt is settled, and the company then issues a final clearance | Same | None |
| 6 | Subject of financing | Goods/service described "without ambiguity"; price; customer's down payment; remaining amount financed | Same | None |
| 7 | Amendment | Only by written agreement of both parties | Same | None |
| 8 | Security | Company may register its rights over the financed **movables** in the movable-collateral register (Law 115/2015); customer may not dispose of them until all instalments are paid and a clearance is issued | Same | None |
| 9 | Administrative fees | "The customer bears all the following admin fees" + list | Same | None |
| 10 | Early settlement | From the **second** instalment's due date, with 30 days' written notice; balance per the schedule **plus an early-settlement commission of …% on the remaining balance** | Same | None |
| 11 | Sale or discounting of debts | Company may **securitize or discount** its debt portfolio with third parties under FRA rules, **without objection from the customer** | Same | None |
| 12 | Confidentiality | Company keeps transactions confidential except as law requires; customer discloses income and guarantees; company may report the financing to FRA and credit bureaus | Same | None |
| 13 | Notices | Addresses in the contract are valid for service; company may send promotional messages to the contact details given | Same | None |
| 14 | Governing law and disputes | Egyptian law, especially Law 18/2020 and FRA instruments; economic court, or arbitration by a separate agreement | Same | None |
| 15 | Copies | Two originals, one each | Same | None |

## Model (2): several transactions via payment cards

Same structure. Points that differ from Model (1), identical in 2021 and 2026 except where noted:
- **Clause 4:** a maximum financing limit; the return rate marked **fixed or variable**; a statement to the customer for each transaction (amount, number and value of instalments, due dates); payment through commercial cards or CBE-approved payment means. The notes/bills/cheques changed from "commercial papers" (2021) to "guarantees" (2026), as in Model (1).
- **Clause 5:** one-year term, renewing automatically unless either party gives one month's notice.
- **Clause 6:** a statement per transaction describing the goods, price and down payment; the company must notify changes to its network of sellers and service providers.
- **Clause 7: the company may amend the terms unilaterally.** The customer is deemed to accept unless they object within 15 days of a registered letter. An objection stops new transactions; existing ones run to term.

## Check against Decree 457/2020's minimum list

Decree 457 (Article 1) required consumer-finance companies **and licensed consumer-finance providers** (sellers financing their own goods) to include at least the items below.

| 457 item | In Model (1)? | Note |
|---|---|---|
| 1. Goods/services identified without ambiguity | Yes, Clause 6-1 | |
| 2. Price at purchase and the customer's down payment | Yes, 6-2 and 6-3 | |
| 3. Financing amount, period, number/terms/value of instalments, return rate used, **and whether it is fixed or variable** | Partly, Clause 4 table | **Model (1) has no fixed/variable field** (both years, confirmed on the 2026 page image). Model (2) has one. |
| 4. Guarantees, including the bar on disposing of the goods until paid | Yes, Clauses 4 and 8 | |
| 5. Customer's authorization to disclose to FRA and credit bureaus | Yes, 12-3 | |
| 6. Customer's right to settle early, and its conditions | Yes, Clause 10 | |
| 7. Company's right to sell or discount its receivables | Yes, Clause 11 | 457 says "sell or discount"; the model says "securitize or discount" |
| 8. The company's licence number and a statement that it is under FRA supervision | Licence number yes; supervision statement only implied (preamble, Clause 14) | |

Decree 457 also required (Article 2) **each company to draft its own model contract and have it approved by FRA before use**. If that rule still applies, every licensed company's standard contract is on file with FRA: a possible route for the scholar's documents, through the companies or FRA.

## What none of the models contains

These are left to each company's own contract (or, for insurance, to a separate 2026 model). They are therefore the points to look for in the pilot companies' agreements:

| Topic | Status in the FRA models |
|---|---|
| Late payment, penalties, default, acceleration | **Absent** from both models and both years |
| Who sells the goods, title and delivery, risk before delivery | **Absent.** The model frames the company as *financing the purchase*, not selling. Clause 8's bar on the customer disposing of the goods implies the customer owns them |
| Defects and returns | Absent |
| Insurance | Absent from Models 1 and 2. The 2026 rulebook adds **Model (3)**, a group life and total-disability insurance contract, and requires companies to insure customers against death and total permanent disability (Board Decree 28/2026, which also sets the insurance contract model) |
| Sharia structure (Murabaha, Ijarah and so on) | Absent. FRA publishes separate Sharia model contracts (e.g. *Murabaha for consumer finance*), compared separately |

## Questions this raises for the scholar

These are for the scholar. Mushir only flags them:

1. **Financing versus sale.** The model is a *financing-for-purchase* contract with a stated "return rate" on the amount financed (Clauses 3–4); the financier is not the seller. How should this structure be classified under the applicable AAOIFI standards? Does a seller that finances its own goods (FRA's providers register) change the analysis when it uses the same model?
2. **"Guarantees" taken as promissory notes and cheques** (Clause 4) and a security interest over the goods (Clause 8).
3. **Early-settlement commission** on the remaining balance (Clause 10).
4. **Securitizing or discounting the debt portfolio** without the customer's objection (Clause 11): sale of receivables.
5. **Unilateral amendment by deemed acceptance** in the card model (Model 2, Clause 7).
6. **What is absent:** late-payment and default terms, and title/delivery, appear only in company contracts. The scholar's rulings on those depend on the company documents requested in the pilot.

## Follow-ups

- **Legal:** confirm whether Decree 457/2020 still applies (minimum list, sellers' obligations, per-company FRA approval). The 2026 rulebook does not list it.
- **Separate comparison:** compare FRA's Sharia model *Murabaha for consumer finance* against conventional Model (1), especially Clauses 3, 4, 8 and 11 and the supplier-invoices-customer clause noted earlier.
- **Mapping:** map the pilot companies' contract evidence (the Contact appendix, the Souhoola terms) onto this clause table. Absent clauses become document requests.
