# Egypt instalment market discovery

Checked on 2026-09-27. This is a repeatable **evidence map** for deferred and
instalment payment offers in the Egyptian online market. Ordinary card and
wallet payments are recorded only as context where they appear in a supporting
passage. A page match is not proof of live checkout eligibility, an executed
financing contract, an FRA licence, or Sharia compliance.
The companies and pages form a purposive discovery sample, not a census of
Egyptian online merchants. The five marketplace names in the seed were not
validated as the five largest by sales or traffic.

## Population and relationships

Keep these entities separate:

| Entity | Question answered | Example |
| --- | --- | --- |
| Seller or developer | Who offers the product or property? | 2B, Jumia as first-party seller, SODIC |
| Sales channel | Where is the offer displayed? | Jumia marketplace, seller's own website |
| Financing entity | Who is named as providing deferred payment? | valU, bank, seller's own plan |
| Product or project | Which purchase is described? | Phone listing, Noor property project |

The tracked claim seeds are in `data/source_registry/egypt_installment_market.csv`.
Each row names one claim, an exact source URL, terms that must occur near each
other, role, claim scope, commerce mode, payment model, and any named financing
entity. `data/source_registry/egypt_market_candidates.csv` holds discovery
leads; those rows do **not** become verified instalment offers automatically.
The collector is `scripts/scrape_egypt_installment_market.py` and the map
builder is `scripts/summarize_egypt_installment_market.py`.

## Discovery order

1. **Product market:** Find Egyptian retailers and finance providers in
   laptops, mobile phones, and cars. Record category-level offer evidence.
   Brand pages and auto marketplaces retain their distinct roles.
2. **Online marketplaces:** Check platforms' payment pages, then individual
   product listings for seller identity and payment descriptions. A platform
   plan is attributed to a particular seller only when the product/page
   evidence supports that link. Record named lenders separately.
3. **Direct online stores:** Discover stores through relevant merchant lists,
   category searches, and reviewed sites; check the store's own payment or
   product page. Include furniture, clothing, and home goods alongside devices.
4. **Services and property:** Check education/health services and property
   developer plans as their own categories. Developer payment plans are not
   automatically classified as FRA consumer-finance activity.

The 43 tracked leads consist of 40 names transcribed from a public
[Emirates NBD merchant PDF](https://www.emiratesnbd.com.eg/-/media/enbd/Egypt/PDFs/Easy-Installment-Plan/egypt_epp_paymob_merchants_ar.pdf)
and three marketplace seller names found in indexed product pages. The bank
PDF could not be retrieved by the direct collector because its robots policy
was unavailable; the PDF rows have `lead_only` discovery status and need
independent page evidence. Several names have since gained that evidence from
their own sites; the summary overlays claims without altering the original
discovery status. The three indexed seller leads are marked
`search_indexed_unverified_current`. Neither lead type establishes a current
merchant offer.
The bank-list URL is mutable and no copy of the version used to compile the
40 names was retained. A later review of the same URL did not reproduce all
names in the lead CSV (for example, Zammit and Cherry Berry). The original
merchant names and `online` hints therefore require reconfirmation against a
dated bank list or the merchant's own site before use.
For example, [Zammit's own site](https://www.zammit.shop/en) describes a
platform that helps merchants build online stores. The workbook therefore
shows its source role separately from a reviewed merchant-platform role.

## Sales rankings

The originally requested top 20 in each product category means retailers and
financing providers, not manufacturers. A valid ranking would need a comparable
Egypt-specific measure such as category sales, financed transaction volume, or
category revenue over the same reporting period and entity boundary. No
public dataset reviewed here supports such a ranking for 20 companies in each
of laptops, phones, and cars. [Similarweb's Egypt shopping list](https://www.similarweb.com/top-websites/egypt/e-commerce-and-shopping/)
is traffic data; it is useful for discovering platforms, not for asserting
sales rank. Any available company financial figures remain source-linked
context only. The product manifest explicitly sets `ranked_top_20_verified`
to `false`.

## Latest live run

The 2026-09-27 crawl selected the latest immutable run for each stage and
wrote its combined map under
`data/runtime/artifacts/l6_scrape/installment_market/2026-09-27/summary/20260927T024008Z-faabcb/`.
Runtime artifacts are ignored by Git. The summary manifest lists the exact
input CSV paths; each selected stage manifest records the corresponding CSV
SHA-256. The client workbook's Run Audit sheet brings those paths and hashes
together, so another reader can audit every count.

| Stage | Claims | Page matches | Other outcomes |
| --- | ---: | ---: | --- |
| Product market | 28 | 13 | 6 claim not found; 9 robots access gaps |
| Online vendor | 23 | 12 | 2 no source; 9 robots access gaps |
| Direct store | 25 | 20 | 1 claim not found; 1 HTTP 404; 3 robots access gaps |
| Services | 4 | 3 | 1 robots disallowed |
| Real estate | 5 | 4 | 1 claim not found |
| **Total** | **85** | **52** | **33 other claim outcomes** |

The combined map has 86 distinct named entities, including platforms,
financing partners, sellers, developers, and lead-only names. Thirty
entities have at least one page-matched claim; 19 are listed selling entities
or developers with page evidence. Thirty-nine entities are lead-only. These are
counts of **claims and entity names**, not market coverage or offer prevalence.
Of the 52 page-matched checks, one verifies seller identity rather than a
payment option; the Nissan Egypt check finds an invitation to discuss dealer
financing, not a specific instalment plan. Both remain in the audit with
explicit review notes rather than being promoted into confirmed offers.
The product pass finds page evidence for four laptop, six phone, and three car
entities. Those are not ranked lists.

Examples of the supported distinctions:

- [Jumia's instalment page](https://www.jumia.com.eg/mlp-installments/)
  names valU, Souhoola, and banks as options on the platform. The
  [sample refrigerator page](https://www.jumia.com.eg/unionaire-rd-320vva-dash-310l-defrost-refrigerator-2-doors-silver-128950095.html)
  says the seller is Jumia and its product description mentions instalment
  plans. The latter is **seller identity plus product description**, not a
  verified checkout offer or lender for that order.
- [2B](https://2b.com.eg/en/installment_offers),
  [IKEA Egypt](https://www.ikea.com/eg/en/customer-service/services/finance-options/),
  [Smart Furniture](https://smartfurniture.com.eg/installments/),
  [Activ Abou Alaa](https://activaboualaa.com/pages/payment-methods), and
  [Town Team](https://townteam.com/policies/terms-of-service) expose
  instalment or deferred-payment wording on their own pages. Activ's and Town
  Team's supporting passages also mention ordinary cards, wallets, or cash on
  delivery; those appear only in `ordinary_payment_context`.
- [RUSHBRUSH](https://www.rushbrush.com/eg-en/payment/installment)
  names Valu and Souhoola on its own instalment page.
  [Jawhara](https://jawharaegypt.com/pages/payment-installments) and
  [L'azurde Egypt](https://www.lazurde.com/en-eg) describe jewellery
  instalments. These widen the goods sample beyond everyday electronics.
- A [Vodafone eShop iPhone page](https://eshop.vodafone.com.eg/en/prod/i-phone-17?Color=White&Storage=256)
  mentions instalments but says the selected variant is out of stock. Its
  claim has `availability_status=out_of_stock`.
- [Contact education](https://contact.eg/en/products/education) covers a
  service. [Vienna Dental Clinic](https://viennadentalclinic.com/en/insurance-financing)
  describes third-party treatment finance, with approval and terms set by the
  provider. [Noor](https://talaatmostafa.com/noor-ra04/),
  [Evia](https://www.mountainviewegypt.com/projects/evia),
  [June](https://www.sodic.com/our-developments/june/june/june), and
  [Touba](https://madinetmasr.com/en/innovation-labs/touba) are property
  project plans. They remain separate from retail goods.

Amazon product pages were robots-disallowed and Noon robots was unavailable
in the direct crawl. The statuses mean **unverified**, even when search
indexing shows an instalment mention. Temu and AliExpress have no reviewed
Egypt-specific instalment source in this seed and are `no_public_source_identified`,
not classified as negative. Jumia sometimes returns an error page; the later
successful capture is selected by the summary, while earlier runs remain
preserved. An inaccessible or unmatched page is never a negative finding for
the underlying business. Dubai Phone's direct crawl was stopped by a robots
HTTP 429; Jewels by Galla's captured HTML did not contain the expected
instalment wording. Those remain unresolved leads despite indexed page text.

## Reproduce and interpret

Run the five passes, then summarize the same date:

```powershell
python scripts/scrape_egypt_installment_market.py --stage product_market --today 2026-09-27
python scripts/scrape_egypt_installment_market.py --stage online_vendor --today 2026-09-27
python scripts/scrape_egypt_installment_market.py --stage direct_store --today 2026-09-27
python scripts/scrape_egypt_installment_market.py --stage services --today 2026-09-27
python scripts/scrape_egypt_installment_market.py --stage real_estate --today 2026-09-27
python scripts/summarize_egypt_installment_market.py --today 2026-09-27
```

Each crawl uses a unique run directory and refuses to overwrite an existing
CSV or manifest. It checks robots policy before fetching, including redirect
targets, and keeps raw HTML, final URL, capture time, and SHA-256 hash. Terms
must occur together in a short visible-text passage; navigation, footers,
scripts, and known error pages are excluded from claim matching.
The seed terms are mainly English and the collector reads server-returned HTML,
so Arabic-only wording and payment options rendered later by JavaScript can be
missed. A page match still needs human review for claim meaning and scope.

`verified_page_evidence` means the required wording appeared on the captured
page. `claim_not_found` means the wording was absent in the fetched HTML;
dynamic rendering remains a possible explanation. `robots_disallowed`,
`robots_unavailable`, `http_error`, `page_error`, and `fetch_error` describe
access or page failures. `no_public_source_identified` means no reviewed page
was seeded. Check `claim_scope`, `commerce_mode`, `financing_entity`,
`availability_status`, and the original URL before using a row. The seller and
financing columns are deliberately blank where the source does not establish
those parties. No row is automatically promoted into a compliant-financing
finding.

Next discovery should work through the 40 merchant leads, verify direct store
sites and product-level checkout cases, and then widen services and developer
categories. Maintain a dated source and explicit access status for every new
claim. If comparable Egypt sales data becomes available, add the exact metric,
period, legal entity boundary, and source before calculating ranks.
