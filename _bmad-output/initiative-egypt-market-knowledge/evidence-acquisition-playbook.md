# Evidence acquisition playbook: getting accurate "inside" data without breaking access controls

Written 2026-10-01 for epic-pilot-dossiers. It answers: when robots.txt, a firewall, client-side rendering, a login or an app-only flow stands between us and the facts, how do we still get accurate, citable data?

## The line we hold, and why it helps us

We **do not evade** access controls. That means: no user-agent spoofing to look like a browser or Googlebot, no proxy or IP rotation to get past a firewall (WAF) block, no CAPTCHA solving, no headless-browser fingerprint masking, no crawling paths that robots.txt disallows, and no use of credentials that aren't ours.

This isn't only caution. It protects the product:
- **Evidence value.** The scholar and the client will ask "where did this come from?" A capture made by getting around a block is weak provenance and can't be shown. A dated capture of a public page, an official filing or an operator's own saved copy can be shown.
- **Legal exposure.** Egypt's cybercrime law (Law 175 of 2018) addresses unauthorised access to information systems, and the FRA itself regulates these companies. A legal opinion is outside our scope; we stay well clear of the grey zone.
- **Project constraint.** The spec forbids crossing robots, terms, login, CAPTCHA or gated steps (epic Done-when #4).

**"Unavailable" is not "disallowed."** When robots.txt returns no directives (fra.gov.eg's firewall page, souhoola.com's app shell), an operator may acknowledge it, as you did on 2026-10-01. A robots.txt that *explicitly disallows* a path is a hard stop for automated fetching.

## The toolbox, best evidence first

Every technique below was used or tested on 2026-10-01. The results are in [pilot-entity-resolution.md](pilot-entity-resolution.md).

| # | Technique | What it gets us | Example from 2026-10-01 |
|---|---|---|---|
| 1 | **Regulator records** (FRA register and detail pages) | Legal name in Arabic and English, licence (activity + number), company number, address, phone, **email domain** | Email domains tied the companies to their sites: contact_us@valu.com.eg, info@souhoola.com, info@sarwa.capital |
| 2 | **First-party legal pages found through sitemaps** (terms, privacy, about, board) | The legal entity the company itself names, parent groups, commercial register numbers | valU terms name the app company (CR 119489) separately from the FRA licensee (CR 34260, FRA "13 لسنة 2020") |
| 3 | **Rendering client-side pages** in the in-app browser, the same as a person viewing a public page | Text that plain HTTP fetches can't see | Souhoola terms: "provided by **Contact Investment for Consumer Finance**", a third name for FRA #10 |
| 4 | **Public archives** (Wayback Machine CDX and snapshots, Common Crawl) | Name and rebrand history; pages that later disappeared | souhoola.com has been titled "CI Consumer Finance" from 2022 to 2026, so the site never adopted the FRA "BM" name |
| 5 | **Stock-exchange and corporate disclosures** (EGX disclosures, annual reports, prospectuses) | Group structure, subsidiaries, official bilingual names | valU states "U Consumer Finance S.A.E, EGX: VALU.CA". Next step: pull its EGX disclosures; check whether Contact Financial Holding is also listed |
| 6 | **Legal gazettes and registries** (commercial register extracts, the companies gazette) | Name changes with dates and the reason (rebrand vs acquisition) | Planned for Souhoola (CI → BM → "Contact Investment"?) and Contact's group links |
| 7 | **App-store listings** (Google Play / App Store developer and legal name), where the store's robots rules allow | The legal entity that publishes the app, often different from the brand | Planned for valU, Souhoola, Contact, Halan, Aman |
| 8 | **Product documents** (key-facts statements, standard contracts, fee schedules: the PDFs under consumer-finance Law 18 of 2020) | The actual mechanism and terms, which are what the scholar needs | Planned; found through sitemaps and merchant pages |
| 9 | **Operator manual capture**: you or the client open the page in your own browser and save it as PDF or MHTML with the URL and time | Pages behind a firewall, consent walls, app screens you are entitled to see | Ingested with `source_type=operator_manual_capture`; never presented as an automated capture |
| 10 | **Ask the source**: email the address on the FRA record, the merchant, or the FRA public inquiry desk; request an API or allowlisting | Standard contracts, fee schedules, written confirmation of which legal entity finances a merchant plan | Recommended for Contact (which of six entities funds a given plan?) and for B.TECH, Amazon and noon (permission queue) |
| 11 | **Customer-supplied documents** (the user's own agreement or schedule, with consent) | The real contract a user signed | V1.7 private document locators (deferred-work item 3) |

## Decision rules when something blocks us

| Obstacle | Automated fetch | What we do instead |
|---|---|---|
| robots.txt **unavailable** (no directives) | Only after operator acknowledgement, polite spacing (at least 2 s) | Record the acknowledgement in the manifest (done for fra.gov.eg and souhoola.com) |
| robots.txt **disallows** the path | Stop | Archives (#4), official sources (#1, #5, #6), operator manual capture (#9), ask the source (#10) |
| Firewall or security block page | Stop; record `blocked_by_security` | Same as above. Never retry with spoofed identity or rotated IPs |
| Client-side rendered page | In-app browser render (#3) | Store the rendered text with its hash and `method` |
| CAPTCHA | Never solve | Operator manual capture or ask the source |
| Login or app-only flow | Never with credentials that aren't ours | Customer-supplied documents with consent (#11), or the operator's own account captures with their consent |
| Terms of use forbid scraping | Stop automated capture for that host | Official sources, ask for permission, operator capture of single pages for review |

## Name handling (standing rule)

Every name found for a company is kept as its own row in `data/source_registry/pilot_entity_names.csv`, exactly as written, with the script (Arabic, Latin or mixed), the kind (FRA legal name, former name, name stated by the site, brand, holding company, parent group, app operator), source URL, capture date, evidence hash and `review_status=pending_client_review`. We never produce an English name from an Arabic one or the reverse, never merge spelling variants (فاليو and ڤاليو are separate rows), and never settle a disagreement between sources. The client decides.

## Provenance fields every capture carries

`requested_url`, `final_url`, `captured_at` (UTC), `sha256`, `content_type`, `method` (http_fetch / browser_render / archive_snapshot / operator_manual_capture / customer_document), robots state and acknowledgement, and an append-only correction record whenever an earlier capture's status changes. Nothing is deleted.
