# Fact and Evidence Model

## Fact slots (both lanes)

Each slot records: value, source (span or user turn), scope, date/version, and status (`observed` | `user_reported` | `conflicting` | `unknown`).

| Slot | Notes |
| --- | --- |
| asset | Goods, service, or property |
| seller | Separate from channel and financier |
| sales_channel | Marketplace or the seller's own site |
| financing_party | Store itself, consumer-finance company, bank, developer |
| contract_family | Only when evidence establishes it (see `mechanism-archetypes.md`) |
| cash_price | Never assumed from the first EGP figure |
| financed_or_final_price | `deposit + instalments` flags a contradiction; it does not prove the total payable |
| down_payment | |
| instalment_count, instalment_amount | |
| additional_fees | Admin fees and similar |
| late_payment_clause, late_fee_beneficiary | |
| insurance_leg | Mandatory death/disability cover up to age 65 under the FRA 2026-09-06 rulebook; conventional insurance vs takaful |
| ownership_risk_sequence | Only where the selected rule requires it |
| early_settlement, refund_terms | Where relevant |

Slots are not all required: the requested answer and the approved rule decide which facts are material. Unobserved reasons: `not_publicly_found`, `login_gated`, `access_blocked`, `in_customer_schedule`.

## Template and schedule

- **Template** (public or requestable): ownership/possession, late payment and beneficiary, early settlement, insurance leg, default and collection.
- **Schedule** (per customer): price, down payment, tenor, instalment, return rate, fees; sometimes the late-fee amount and the premium.
- Material facts that live only in the schedule are asked of the user, never inferred. Bank products fall under the CBE; FRA's form is not assumed to cover them.

## Document / evidence classes

`marketing`, `faq`, `provider_standard_terms`, `regulator_model`, `transaction_specific_disclosure`, `user_supplied_schedule`, `donated_agreement`, `synthetic_counterfactual` (never observed evidence), `provider_claim` (Sharia self-label).

## Dossier contents (per entity × product × seller × financier × channel × document version)

Entity and aliases; official domain; roles, each with its own evidence; product/operation id and any published offer period; link graph and ordered public buyer journey; capture manifest (URL, timestamp, hash, content type, language, access status); field observations for the slots above; document scope; conflicting and older versions kept visible; analyst verification and separate scholar review of the rule mapping.

## Acquisition channels (priority order)

| # | Channel | Gate | Version |
| --- | --- | --- | --- |
| 1 | Public provider terms + FRA standard form | Robots, terms, no login bypass | V1.6 |
| 2 | Direct provider request | Written permission recorded | V1.6+ |
| 3 | User schedule screenshot | Redaction, ephemeral, opt-in donation, PDPL | V1.7 |
| 4 | Staff own agreements from real small purchases | Scholar approval (O2), own documents and consent | V1.7 if approved |
| 5 | One-clause counterfactual twins | Marked synthetic, isolated store | V1.7, eval/extractor only |

## Access boundary

Stop before registration, OTP, credit inquiry, agreement acceptance, card entry, payment or order submission; record the first gated step as a result. Search results are leads, not evidence. Amazon (robots disallowed), noon (robots unavailable) and B.TECH (terms forbid scraping) stay in a permission queue.
