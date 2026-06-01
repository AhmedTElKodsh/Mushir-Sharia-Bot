# Official-Source Financial Institution and Product Crawler Research

Generated: 2026-05-22 Africa/Cairo

## Tool Run Status

### Tavily Research

- `tvly` is available at `C:\Users\Admin\.local\bin\tvly.exe`.
- The CLI shape has changed to `tvly research run|status|poll`.
- `tvly research run ... --model pro --citation-format numbered` still fails because the backend rejects `citation_format`.
- `tvly research run ... --model pro` still fails because the current Tavily plan exceeds its usage limit.
- `tvly research run "Egypt CBE FRA financial institutions crawler official-source-first design" --model mini` succeeded and wrote:
  `data/runtime/artifacts/l6_scrape/research/2026-05-22/tavily_mini_retry.md`

The mini report is useful as a rough checklist, but it should not be treated as authoritative for this repo. It over-focuses on fintech sandbox and open-banking topics, includes weak or generic legal claims, and cites only one visible source in the saved output.

### Deep Research

The requested `deep-research` skill file exists at `C:\Users\Admin\.agents\skills\deep-research\SKILL.md`. It calls for Firecrawl or Exa. Firecrawl was not exposed in this session, but Exa was available and used for current multi-source search and full-page reads.

Tavily MCP crawl was also checked, but it failed because `TAVILY_API_KEY` is not exposed to the MCP server. That is separate from the CLI, which is authenticated but quota-limited.

## Executive Summary

The right next layer is not a single "scrape everything" job. It should be a governed evidence acquisition system with two denominators:

1. A regulator-complete institution registry from CBE and FRA.
2. A product/service/contract evidence layer under each reviewed institution.

CBE and FRA official sources are strong enough to build the institution denominator. CBE publishes a licensed-bank directory through its licensing page and bank PDF. FRA publishes server-rendered register pages for capital-market and insurance records, with detail pages under `company_records` and official PDF links for reinsurance lists.

Product crawling needs a second mode. Official institution pages often expose enough product facts to create operation records, as Faisal Bank's Murabaha page does for new cars, electric cars, used cars, durable goods, solar energy, real-estate purchases, clinic equipment, scooters, and automotive maintenance. But where a page is only title-level, the crawler should generate bounded search-expansion queries and treat search results as discovery leads, not compliance evidence.

## Primary Source Map

| Source | What it proves | Implementation use |
|---|---|---|
| [CBE Licensing](https://www.cbe.org.eg/en/financial-stability/licensing) | CBE grants bank licenses and publishes a "Directory of Licensed Units" with a "Banks list" entry. | Seed CBE official-source inventory and fallback route when direct PDF download changes. |
| [CBE bank PDF](https://www.cbe.org.eg/-/media/project/cbe/page-content/rich-text/financial-stability/english/headoffices-eng(2)-(2).pdf) | The current bank list contains 36 registered banks, registration dates, and head-office addresses. | Parse with PDF table/text extraction; compare against `Banks_old.xlsx`. |
| [FRA capital-market register](https://fra.gov.eg/en/%d8%aa%d8%b3%d8%ac%d9%8a%d9%84-%d9%88-%d8%aa%d8%ad%d8%af%d9%8a%d8%ab-%d8%b3%d8%ac%d9%84%d8%a7%d8%aa-%d9%84%d8%b4%d8%b1%d9%83%d8%a7%d8%aa-%d8%b3%d9%88%d9%82-%d8%a7%d9%84%d9%85%d8%a7%d9%84/) | FRA publishes capital-market company rows with Arabic-only names, types, categories, and licensing dates. Page last modified: 2026-01-08 in the fetched content. | Crawl paginated `/page/N/` and detail links; dedupe against `Capital_Market_old.xlsx`. |
| [FRA insurance register](https://fra.gov.eg/en/%D8%B3%D8%AC%D9%84%D8%A7%D8%AA-%D9%81%D9%8A-%D9%85%D8%AC%D8%A7%D9%84-%D8%A7%D9%84%D8%AA%D8%A3%D9%85%D9%8A%D9%86/) | FRA publishes insurance-sector rows and links to reinsurers and foreign reinsurance broker lists. Page last modified: 2026-04-23 in the fetched content. | Crawl register rows and linked PDFs; dedupe against `Insurance_old.xlsx`. |
| [Faisal Bank Murabha](https://www.faisalbank.com.eg/en/Retail/Retail-Funds-Murabha) | Official product page exposes operation families, eligibility, financing caps, repayment periods, fees, required documents, and Sharia financing labels. | Use as the first product-discovery fixture and schema example. |

## Useful OSS Choices

| Tool | Fit for Mushir | Source |
|---|---|---|
| Scrapy | Best for repeatable official-source crawls, per-domain throttling, queues, pause/resume, feed exports, downloader middleware, and robots handling. | [Scrapy docs](https://docs.scrapy.org/en/stable/), [downloader middleware](https://docs.scrapy.org/en/2.10/topics/downloader-middleware.html) |
| Playwright | Best fallback for CBE/browser downloads and JS-heavy bank pages. Use only where static HTTP fails. | Existing repo/browser workflow plus current CBE blocker evidence. |
| Crawl4AI | Strong candidate for LLM-ready Markdown and browser-backed extraction when building RAG-ready document text. Useful as an adapter, not as the core source-of-truth model. | [Crawl4AI docs](https://docs.crawl4ai.com/) |
| Trafilatura | Good lightweight extractor for article/page main text, metadata, sitemaps, feeds, and corpus-style text extraction. | [Trafilatura docs](https://trafilatura.readthedocs.org/) |
| pdfplumber | Best current fit for CBE/FRA PDF tables because it supports text extraction, table extraction, layout tuning, and visual debugging. | [pdfplumber README](https://github.com/jsvine/pdfplumber/blob/stable/README.md) |
| OpenLineage-style model | Useful pattern for audit provenance: job, run, input dataset, output dataset, facets. Do not add the full stack yet; copy the concepts first. | [OpenLineage docs](https://openlineage.io/docs/) |

## Recommended Data Layers

1. `regulator_registry_snapshot`
   - Raw CBE/FRA source rows and PDFs.
   - Fields: regulator, source_url, source_type, source_last_modified, retrieved_at, row_hash, parse_status.

2. `institution_identity`
   - Canonical institution records.
   - Fields: institution_id, name_en, name_ar, aliases, regulator, sector, license_id, registration_date, address, official_website, confidence, review_status.

3. `source_discovery_candidate`
   - Every candidate URL discovered from official sites, sitemaps, PDFs, search queries, and directories.
   - Fields: institution_id, url, discovery_method, source_rank, query, title, snippet, status, reason, needs_review.

4. `evidence_document`
   - Downloaded pages/PDFs with provenance.
   - Fields: artifact_id, institution_id, url, artifact_type, language, content_hash, raw_path, text_path, extraction_status, quality_score, source_rank.

5. `financial_operation`
   - Structured products/services/contracts.
   - Fields: operation_id, institution_id, operation_name, operation_type, evidence_artifact_id, eligibility, fees, repayment_terms, required_documents, application_process, contract_url, confidence, evidence_status.

6. `sharia_aaoifi_evaluation`
   - Evaluation outputs only after evidence gates pass.
   - Fields: operation_id, question_type, candidate_standards, route_id, verdict_status, citation_ids, missing_facts, scholar_review_status.

## Crawler Strategy

### Phase A: Complete Institution Registry

- Parse the CBE bank PDF from the official licensing page.
- Treat CBE request-rejection or non-PDF responses as `blocked_requires_browser_fallback`, not as "no banks found".
- Crawl FRA capital-market, insurance, finance, fintech, leasing, mortgage, microfinance, factoring, and consumer-finance registers via paginated pages and `company_records` detail URLs.
- Parse official FRA PDFs as first-class regulator sources.
- Dedupe with Arabic/English normalization, alias splitting, and fuzzy score thresholds.
- Export coverage counters:
  - baseline rows
  - regulator rows
  - matched rows
  - confirmed new rows
  - manual-review rows
  - blocked source rows

### Phase B: Official-Site Product Inventory

- Start only with institutions that have reviewed official websites.
- Crawl official domain root, sitemap, product/service paths, PDF links, fees/tariff/KFS paths, terms and conditions paths.
- Score URLs using finance terms:
  - English: product, finance, loan, murabaha, ijara, tawarruq, cards, deposit, fees, tariff, terms, contract, insurance, takaful, policy, prospectus, sukuk, fund, leasing, mortgage, factoring, microfinance, consumer finance.
  - Arabic: تمويل, مرابحة, إجارة, تورق, بطاقة, وديعة, رسوم, تعريفة, شروط, عقد, تأمين, تكافل, وثيقة, صكوك, صندوق, تأجير, عقاري, تخصيم.

### Phase C: Search Expansion for Thin Pages

If official crawling extracts only a title or teaser, generate bounded query plans:

- `site:{official_domain} "{operation_title}"`
- `site:{official_domain} "{operation_title}" filetype:pdf`
- `"{institution_name}" "{operation_title}" terms`
- `"{institution_name_ar}" "{operation_title_ar}" شروط`
- `"{institution_name}" "{operation_title}" tariff OR fees`
- `"{institution_name}" "{operation_title}" key facts statement`

Search expansion rules:

- Official domain hits can become evidence after fetch and extraction.
- Regulator domain hits can become evidence after fetch and extraction.
- Third-party hits are discovery-only unless explicitly reviewed and labeled lower-trust.
- No compliance verdict may be generated from title-only evidence.

## Evidence Gates Before Sharia Evaluation

An operation is `ready_for_machine_mapping` only when it has at least one useful official or regulator artifact with more than a title. Preferred minimum evidence:

- product/service page plus fee/tariff/KFS/terms document; or
- product/service page with enough structured terms: eligibility, amount cap, financing percent, tenor, fee, required documents, process; or
- official PDF/prospectus/policy wording.

If the crawler has only a product name, the correct evaluation state is:

`insufficient_evidence_for_sharia_assessment`

This is not a failure. It is a safety gate.

## Implementation Implications for the Current Repo

The existing uncommitted `legacy-sector-scrape` mode is moving in the right direction, but it should be treated as a bridge, not the final architecture.

Recommended next implementation slice:

1. Keep the existing four-workbook loader and legacy-sector ledger.
2. Add a normalized `source_discovery_candidate` export before crawling.
3. Add a query-plan generator for thin official pages.
4. Do not run wide search automatically in the first code slice; write deterministic query plans and tests first.
5. Add fixtures from Faisal Bank's Murabha page to prove multi-operation extraction from one page.
6. Add an evidence status flag to every extracted operation:
   - `contract_grade`
   - `product_disclosure`
   - `title_only`
   - `insufficient_text`
   - `blocked`

## Acceptance Gates

- CBE direct PDF failure records a fallback status and does not fail open.
- FRA pagination stops deterministically when a page has no new rows or reaches a configured max page.
- Rows without a source URL never enter `ready_for_crawl`.
- Product records with only a title never enter `ready_for_machine_mapping`.
- Every operation row carries source URL, retrieval date, artifact hash/path, extraction method, and evidence status.
- Scholar review export excludes `insufficient_text` and `title_only` rows from AAOIFI assessment queues.

## Source Notes

Sources were searched and read with Exa on 2026-05-22. Tavily mini research succeeded but was used only as a secondary checklist because its saved output lacked sufficient source coverage for this domain.
