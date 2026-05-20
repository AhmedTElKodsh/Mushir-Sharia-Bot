# L6 Egypt Institution Scrape Workstream

This folder documents the public-source evidence corpus planned for Egyptian financial institutions and their financial operations.

The detailed planning source is:

- `.kiro/specs/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md`

## Boundary

This workstream prepares evidence and evaluation data. It does not make Mushir a fatwa engine and does not make scraped labels authoritative.

The scraper should collect:

- regulator-backed institution records;
- official websites and public disclosures;
- tariffs, fees, product pages, terms, contracts, model contracts, annual reports, prospectuses, sukuk documents, fund documents, and policy wordings;
- source URLs, timestamps, content hashes, extraction status, and evidence spans.

The engine may propose AAOIFI mappings and initial risk labels, but those labels remain `machine_proposed` until reviewed by a qualified Sharia scholar.

## Implementation Folders

Planned tracked inputs:

- `data/source_registry/` - small registry seeds and source configuration.
- `data/fixtures/l6_scrape/` - tiny test fixtures only.

Runtime output:

- `artifacts/l6_scrape/` - raw pages, PDFs, extracted text, crawl logs, and errors. This folder is for local/runtime artifacts and should not become a normal source-control dump.

Future code should extend the existing acquisition/governance direction:

- `src/acquisition/` - discovery, crawl, parse, and evidence-store modules.
- `src/governance/` - source catalog, route, concept, and metadata controls.

## Safety Rules

- Use regulator and official sources first.
- Treat third-party search as discovery help only.
- Stop after bounded research attempts and record the gap.
- Respect robots.txt, terms, rate limits, login walls, CAPTCHA, paywalls, and access controls.
- Mark missing contracts as `not_publicly_available`; never infer them.
- Keep user-supplied facts above stored institutional assumptions during future answers.
