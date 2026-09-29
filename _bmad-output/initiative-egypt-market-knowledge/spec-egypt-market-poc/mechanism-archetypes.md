# Financing Mechanism Archetypes (draft, pending analyst and scholar review)

These labels are descriptive only and carry no Sharia judgment. A product stays `unknown` until a template or disclosure establishes its archetype.

| Code | Mechanism |
| --- | --- |
| ARC-CF | FRA consumer-finance company pays the merchant; the buyer repays the company with a disclosed return |
| ARC-BANK-LOAN | Bank personal loan or card instalment conversion |
| ARC-BANK-ISL | Bank Islamic window or Islamic bank sale-based product (e.g. Murabaha) |
| ARC-SUBSIDISED | 0% plan in which the merchant bears the financing cost |
| ARC-SELLER | Seller's own deferred-price instalment sale |
| ARC-DEV | Property developer payment plan, often before delivery |
| ARC-LEASE | Lease-to-own structure |
| ARC-BNPL | Short-tenor split payment |

## Knowledge-base tiers

| Tier | Population | Coverage target |
| --- | --- | --- |
| A | Regulated financiers (FRA licensees, CBE banks; Islamic windows flagged) | Full census from registers |
| B | Concrete financing products per financier | Template-level dossier each |
| C | Merchants and channels | Link graph to Tier B; not a census |
| D | Seller own-plans (developers, furniture/jewellery, schools, clinics) | Own dossier each, prioritised by exposure |

## Archetype prior features (CAP-13)

FRA licence type; bank vs non-bank; Islamic-window flag; page vocabulary (`عائد`, `فائدة`, `ربح`, `مرابحة`, `مصاريف إدارية`, `بدون فوائد`, `0%`); lender named on the page; seller-own-plan wording; down-payment and tenor phrasing; presence of an insurance clause.

Labels come from products with a fully observed template, labeled by an analyst and confirmed by the scholar. Evaluation holds out whole entities (e.g. `GroupKFold(groups=entity_id)`) and reports calibration. UI wording: "typical for this provider type, not verified for your contract."

## Queue prioritisation (per queue: financiers, marketplaces, direct retailers, services/property)

| Factor | Weight | Admissible evidence |
| --- | ---: | --- |
| Egyptian user exposure | 30% | Dated Egypt traffic, or financed volume with entity and period named |
| Relevance of instalment terms | 25% | Material financing questions exposed to buyers |
| Primary-document yield | 20% | FAQ, terms, agreement appendix, disclosure, calculator |
| Relationship coverage | 15% | Evidenced seller/financier/product/channel links |
| Refresh feasibility | 10% | Stable, permitted sources |

Unknown reach stays unknown, never zero. Traffic never ranks financing use.
