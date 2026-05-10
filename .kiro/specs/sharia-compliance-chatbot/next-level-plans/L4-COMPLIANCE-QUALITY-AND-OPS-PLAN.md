# L4 Trust, Access, Caching, and Operations Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Do not start L4 until the L3 verification gate passes.

**Goal:** Harden the deployed app for real users by improving citation trust, enforcing disclaimers, controlling API access, adding safe caching, and documenting operations.

**Architecture:** Build on L3 adapters and quality gates. Citation validation runs before caching. Access control sits at the API boundary. Operational automation supports the actual deployment target, not a hypothetical enterprise platform.

**Tech Stack:** FastAPI, Redis, audit store from L3, pytest, GitHub Actions or selected CI, Docker, optional Prometheus/Grafana alerts.

---

## Scope

In scope:
- Direct quote citations and citation validation.
- Corpus, prompt, and config version traceability.
- Required disclaimer behavior.
- API keys if the API is exposed outside trusted local use.
- Tier limits if external usage exists.
- Redis caching after validation.
- CI/CD and rollback docs.
- Minimal alerts and runbooks tied to real deployment paths.

Out of scope:
- OAuth/SSO.
- Multi-region deployment.
- Admin console.
- SOC2-style controls.
- Analytics warehouse.
- Full enterprise RBAC.

---

## Test Rules

- Citation and disclaimer tests are required before any cache tests.
- Cache tests must prove cached answers do not bypass citation validation or disclaimer policy.
- Auth tests use fake keys and fake storage by default.
- Alert tests verify rule/config shape; they do not depend on real external alert delivery.

Default command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration and not eval and not slow" --timeout=60
```

---

## Task 1: Citation Quality Upgrade

**Files:**
- Modify: `src/models/ruling.py`
- Modify: `src/chatbot/compliance_analyzer.py`
- Create: `src/chatbot/citation_validator.py`
- Test: `tests/test_citation_validator.py`

- [ ] Extend citations with `quote`, `quote_start`, `quote_end`, `similarity_score`, `document_version`, `corpus_version`, and `chunk_id`.
- [ ] Extract direct quotes only from retrieved chunks.
- [ ] Validate every final citation against retrieved context.
- [ ] Add a grounding warning when the LLM cites a standard not present in retrieved context.
- [ ] Block `COMPLIANT`, `NON_COMPLIANT`, and `PARTIALLY_COMPLIANT` if no valid citation exists; return `INSUFFICIENT_DATA`.
- [ ] Add tests for unsupported claims, invalid citations, missing citations, and valid quote extraction.

Acceptance:
- Every non-insufficient answer has at least one validated quote citation.
- High-risk overclaiming cases fail tests.

---

## Task 2: Disclaimer and Corpus Version Policy

**Files:**
- Create: `src/compliance/disclaimer.py`
- Modify: `src/chatbot/application_service.py`
- Modify: `src/api/routes.py`
- Modify: `src/storage/audit_store.py`
- Test: `tests/test_disclaimer_flow.py`

- [ ] Define concise disclaimer text:
  - informational AAOIFI-based guidance only
  - not a binding Sharia ruling
  - consult qualified scholars/advisors for final decisions
- [ ] Include disclaimer or disclaimer reference consistently in CLI/API responses.
- [ ] Require acknowledgment before final rulings only if the app is exposed to real external users.
- [ ] Include disclaimer version, corpus version, prompt version, and config version in audit metadata.
- [ ] Add endpoint to fetch current disclaimer text if API is public.

Acceptance:
- Every production answer is traceable to source corpus version and disclaimer version.

---

## Task 3: API Keys and Tier Limits

**Files:**
- Create: `src/auth/api_keys.py`
- Modify: `src/api/dependencies.py`
- Modify: `src/api/rate_limit.py`
- Create: `src/storage/users.py`
- Test: `tests/test_api_keys.py`

- [ ] Start this task only if API access is external or untrusted.
- [ ] Add API key creation, hashing, display-once behavior, revocation, and rotation.
- [ ] Add tests for missing key, invalid key, revoked key, valid key, and rotated key.
- [ ] Add tiers only after API keys work:
  - Free: 10 queries/hour
  - Standard: 100 queries/hour
  - Premium: 1000 queries/hour
- [ ] Track estimated Gemini cost per query for later billing analysis.

Acceptance:
- Protected endpoints reject missing/invalid/revoked keys.
- Tier limits are enforced from the configured backend.

---

## Task 4: Safe Redis Caching

**Files:**
- Create: `src/cache/response_cache.py`
- Create: `src/cache/retrieval_cache.py`
- Modify: `src/rag/pipeline.py`
- Modify: `src/chatbot/llm_client.py`
- Test: `tests/test_cache_behavior.py`

- [ ] Start after citation validation and disclaimer policy tests pass.
- [ ] Cache retrieval by normalized query and corpus version.
- [ ] Cache final responses only when query, retrieved chunk IDs, prompt version, corpus version, model, temperature, disclaimer version, and citation validation version match.
- [ ] Use Redis TTLs:
  - retrieval cache: 1 hour
  - response cache: 24 hours
- [ ] Add tests for key stability, hit/miss, stale entry, expired entry, prompt-version invalidation, and corpus-version invalidation.

Acceptance:
- Cached identical queries skip retrieval/LLM calls only when validation and version keys match.

---

## Task 5: CI/CD and Release Checklist

**Files:**
- Create: `.github/workflows/ci.yml`
- Optional: `.github/workflows/deploy.yml`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Create: `docs/ops/deployment.md`
- Create: `docs/ops/release-checklist.md`

- [ ] CI should begin with compileall, lint/type checks if configured, unit/service/api tests, and smoke tests.
- [ ] Integration and eval suites can run scheduled or as release gates.
- [ ] Deployment pipeline should match the real deployment target and remain configurable.
- [ ] Document deploy, rollback, corpus update, failed eval response, and secret setup.
- [ ] Add post-deploy smoke checks: health endpoint, minimal query, and streaming endpoint if SSE exists.

Acceptance:
- Clean checkout can run tests and build the production image.
- Release checklist covers deploy and rollback.

---

## Task 6: Alerts and Runbooks

**Files:**
- Create: `docs/ops/runbook.md`
- Modify: `src/observability/metrics.py`
- Create: `docs/ops/alerts.md`

- [ ] Add only alerts tied to actual deployment risks:
  - API error rate
  - LLM failure rate
  - retrieval failure rate
  - Redis/audit/vector backend connectivity
  - eval regression
  - cost spike
- [ ] Document triage steps for each alert.
- [ ] Add an incident log template.
- [ ] Test alert rule shape/config without requiring external alert delivery.

Acceptance:
- Forced staging failures trigger or simulate alerts within 5 minutes.
- Runbook tells an engineer what to check first.

---

## L4 Verification Gate

- [ ] `.\.venv\Scripts\python.exe -m pytest -m "not integration and not eval and not slow" --timeout=60`
- [ ] `.\.venv\Scripts\python.exe -m pytest -m integration` for auth/cache/storage if services are enabled.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m eval` for full quality gate.
- [ ] Build Docker image and run staging smoke test.

L4 is done when:
- Rulings include validated quote-backed citations or clearly refuse.
- Disclaimer/corpus/prompt versions are consistently traceable.
- API keys and quotas are enforced only where external access exists.
- Cache cannot bypass validation.
- CI/CD and runbooks cover the real deployment path.

