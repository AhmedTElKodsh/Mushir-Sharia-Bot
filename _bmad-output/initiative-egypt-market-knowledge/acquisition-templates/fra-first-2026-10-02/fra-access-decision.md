# FRA register access decision: 2026-10-02

**Decision owner:** the user (project owner). In chat on 2026-10-02 they directed that FRA data be collected "either automatic or manual, whatever possible". Operator: Claude (BMad). This is a project decision. It is not permission issued by FRA and not a legal clearance.

## What was observed

| Request | Result |
|---|---|
| `https://fra.gov.eg/robots.txt` | HTTP 200, `text/html`, 166 bytes: a "Request Rejected" security page. No robots directives. |
| Financing-register listing (`filtered_type=consumer-finance-providers`), same honest user agent | HTTP 200, normal register page, 21 company-record links |

FRA's security layer answers the robots file itself while serving the public register normally. The legacy collector recorded this as `unavailable`. It is now a separate state, `security_response`, and needs its own acknowledgement (`--acknowledge-robots-security-response`). The broad "unavailable" acknowledgement no longer covers it.

## Scope of the decision

- **Host and paths:** `fra.gov.eg` financing register listing pages (`/سجلات-لشركات-التمويل/` with `filtered_type` in `consumer-finance-providers`, `consumer-finance`, `all`) and the `company_records/...` detail pages they link to.
- **Manner:** identified research user agent (`MushirResearchBot/0.1`), one serial worker, ≥2 s between requests, TLS verification on, no cookies, no credentials, no proxy, no browser fingerprinting.
- **Stop rule:** any security, login or rate-limit response on a register page stops the run (unchanged collector behaviour). No retry under a different identity.
- **Data:** official licensee identity facts only (names, company/licence numbers, licence dates, registered addresses, activity). No personal or customer data.
- **FRA publications** (consumer-finance guide, customer-protection guide, legislation): retrieved individually by the manual route. Each is logged with URL, UTC time, status and SHA-256 in `fra-documents-manifest.json`.

## Runs under this decision

`data/runtime/artifacts/l6_scrape/fra_registry/2026-10-02/<type>/` holds one immutable run per register type, each with its manifest and raw captures. The 2026-09-23 captures were re-parsed offline (`all-licences-rebuilt-20261002/`; zero network requests) and left unmodified.

## Expiry

The decision covers this capture cycle. A later re-run needs a fresh look at `/robots.txt` and the register pages. If FRA starts serving a real robots policy, that policy governs.
