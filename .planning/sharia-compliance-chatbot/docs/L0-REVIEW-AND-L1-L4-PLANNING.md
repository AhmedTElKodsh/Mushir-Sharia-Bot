# L0 Review & L1-L4 Planning Summary

**Date:** May 9, 2026  
**Participants:** Winston (Architect), Amelia (Dev), John (PM), Mary (Analyst)

## Executive Summary

L0 is **COMPLETE** and validated. The team reviewed the implementation and provided comprehensive guidance for L1-L4. This document compiles insights from all four agents into actionable planning for the next layers.

**Key Finding:** L0 architecture is solid. No major refactoring needed. Build on it incrementally.

---

## L0 Implementation Review

### What Was Built (26 files, ~1,220 LOC)

**✅ Core Components:**
- Data models: `AAOIFICitation`, `SemanticChunk`, `ComplianceRuling`
- RAG pipeline: Query embedding → ChromaDB search → top-k retrieval → citation extraction
- Gemini 1.5 Pro integration: 1M context, temperature 0.1, $0.011/query
- CLI chatbot: Terminal interface with AAOIFI adherence system prompt
- Ingestion: Markdown corpus → 512-token chunks (50 overlap) → all-mpnet-base-v2 embeddings → ChromaDB
- Tests: 2 smoke tests (ingestion, retrieval), 1 framework test (gold eval)

**✅ Validated Architectural Decisions:**
1. **Gemini 1.5 Pro**: Proven to follow AAOIFI adherence prompt, 1M context, cost-effective → **KEEP**
2. **ChromaDB embedded**: Works well for L0-L2 (<100K vectors) → **Migrate to Qdrant at L3**
3. **all-mpnet-base-v2**: 768-dim, English-only, good retrieval quality, runs locally → **KEEP**
4. **512 token chunks, 50 overlap**: Standard for legal text, validated → **KEEP unless retrieval quality tanks**
5. **Temperature 0.1**: Consistent, deterministic outputs → **KEEP**

**❌ What L0 Lacks (by design, to be added in L1-L4):**
- No clarification loop (single-turn only) → L1
- No conversation history → L1
- No error handling → L1
- No streaming → L2
- No API (terminal only) → L2
- No session management → L1 (in-memory), L3 (Redis)
- No monitoring → L3
- No production infrastructure → L3

---

## Agent Insights

### 🏗️ Winston (Architect)

**Key Points:**
1. **Gemini 1.5 Pro is the right choice**: 1M context window, cost-effective ($0.011/query), proven to follow AAOIFI adherence prompt
2. **ChromaDB → Qdrant migration at L3**: ChromaDB embedded works for L0-L2, but Qdrant needed for production scale
3. **Clarification loop should be LLM-driven**: Don't hand-code state machines, use LangGraph with Gemini to identify missing info
4. **Streaming is non-negotiable for L2**: Users expect real-time feedback, SSE is sufficient (defer WebSocket)
5. **Citation quality is the moat**: Direct quotes with confidence scores, not just section references
6. **Rate limits must tie to actual costs**: Free ($0) subsidizes $80/month, Standard ($10/month) underwater at 10 queries/day

**Architectural Decisions:**
- **L1**: LangGraph clarification state machine, BM25+dense+RRF retrieval
- **L2**: FastAPI + SSE streaming, JWT auth, in-memory rate limiting
- **L3**: Qdrant + Redis + PostgreSQL, horizontal scaling, Prometheus monitoring
- **L4**: Citation quality (direct quotes), caching (Redis), advanced evaluation (Ragas/DeepEval)

**Cost Model:**
- Gemini input: $0.00125/1K tokens (avg 5K tokens) = $0.00625
- Gemini output: $0.005/1K tokens (avg 1K tokens) = $0.005
- **Total per query: ~$0.011**

**Rate Limit Recommendations:**
- Free: 10 queries/hour ($0.11/hour cost)
- Standard: 100 queries/hour ($1.10/hour cost)
- Premium: 1000 queries/hour ($11/hour cost)

### 👩‍💻 Amelia (Dev)

**Code Quality Assessment:**

**✅ What's Good:**
1. **Clean module separation**: `src/models/`, `src/rag/`, `src/chatbot/` - each module has one job
2. **Dataclasses over dicts**: Type hints, IDE autocomplete, validation
3. **Environment-driven config**: `.env` for secrets, no hardcoded API keys

**❌ What Needs Work:**
1. **LLM call is brittle**: No error handling, assumes `response.text` always exists
2. **No logging**: L0 has `print()` statements, need structured logging for L2+
3. **Hardcoded prompt templates**: Should be in config file for A/B testing

**OSS Library Recommendations:**

**L1: Clarification Loop**
- **Adopt: LangGraph** (from GiovanniPasq/agentic-rag-for-dummies)
  - Explicit state machine (nodes = states, edges = transitions)
  - Built-in human-in-the-loop support
  - Checkpointing for session persistence
  - Works with any LLM (Gemini, OpenAI, Anthropic)

**L2: API Layer**
- **Adopt: FastAPI + SSE** (from lawglance/lawglance)
  - Clean API structure: `src/api/routes/`, `src/api/middleware/`, `src/api/schemas/`
  - SSE streaming for real-time LLM responses
  - Redis cache pattern for LLM responses

**L3: Evaluation**
- **Adopt: Ragas + DeepEval** (from sougaaat/RAG-based-Legal-Assistant)
  - Ragas for nightly eval: faithfulness, answer_relevancy
  - DeepEval for CI gates: pytest-style, blocks grounding regressions

**Testing Strategy:**
- **L1**: Add integration tests for clarification loop (60% coverage target)
- **L2**: Add API tests for endpoints (70% coverage target)
- **L3**: Add eval tests for gold set (80% coverage target)

**Development Workflow:**
1. **Feature branches**: `main` (L0 stable) → `feature/l1-clarification`, `feature/l2-api`, etc.
2. **Backward compatibility**: Keep CLI working when adding API
3. **Integration tests as contracts**: L0 tests must pass in L1-L4

**Technical Debt from L0:**
1. **No session management**: L1 needs in-memory sessions, L3 needs Redis
2. **No error handling**: Add retry logic, graceful degradation, user-friendly errors
3. **No observability**: L3 needs Prometheus metrics, OpenTelemetry tracing, structured logging

### 📋 John (PM)

**L1-L4 Roadmap (9 weeks total):**

| Layer | Timeline | Dev Time | Scholar Time | DevOps Time | MVP Scope |
|-------|----------|----------|--------------|-------------|-----------|
| **L1** | 2 weeks | 10 days | 2 days | 0 days | Clarification loop (2-turn max), in-memory sessions, LangGraph, error handling |
| **L2** | 2 weeks | 8 days | 0 days | 2 days | FastAPI + SSE streaming, JWT auth, in-memory rate limiting |
| **L3** | 3 weeks | 10 days | 3 days | 5 days | Qdrant + Redis + PostgreSQL, horizontal scaling, monitoring |
| **L4** | 2 weeks | 5 days | 0 days | 5 days | Citation quality, caching, Ragas/DeepEval, compliance features |
| **Total** | **9 weeks** | **33 days** | **5 days** | **12 days** | **2.25 months** |

**Cost Estimates (excluding salaries):**

| Layer | Infrastructure | LLM API | Total/Month |
|-------|----------------|---------|-------------|
| L1 | $0 (local) | $50 (testing) | $50 |
| L2 | $0 (local) | $100 (testing) | $100 |
| L3 | $200 (Redis+Postgres+Qdrant) | $200 (eval+testing) | $400 |
| L4 | $300 (production) | $500 (production) | $800 |
| **Total** | | | **~$1,350 over 9 weeks** |

**Scope Management: The "No" List**

**L1 - DON'T ADD:**
- ❌ Conversation history across sessions (just current clarification)
- ❌ Smart variable extraction (let the LLM figure it out)
- ❌ Multi-language support (English only until L4)

**L2 - DON'T ADD:**
- ❌ WebSocket (SSE is enough)
- ❌ GraphQL (REST is enough)
- ❌ Batch endpoints (one query at a time)

**L3 - DON'T ADD:**
- ❌ Authentication (defer to L4)
- ❌ Multi-tenancy (single tenant for now)
- ❌ Advanced analytics (basic metrics only)

**L4 - DON'T ADD:**
- ❌ OAuth/SSO (API keys are enough)
- ❌ Multi-region (single region)
- ❌ Custom dashboards (Grafana is enough)

**Success Metrics:**

**L1:**
- ✅ 80% of test queries complete within 2 turns
- ✅ 0 infinite loops in 100 test queries
- ✅ Clarification questions are relevant (manual review of 20 queries)

**L2:**
- ✅ API response time <5s for 95% of queries
- ✅ Streaming works (tokens arrive incrementally)
- ✅ Rate limiting blocks >100 requests/hour from same IP

**L3:**
- ✅ System handles 100 concurrent users without crashing
- ✅ Ragas faithfulness score >0.8 on gold set
- ✅ Monitoring dashboard shows <5% error rate

**L4:**
- ✅ Users can sign up and get API key in <5 minutes
- ✅ Deployment takes <10 minutes from git push to live
- ✅ Alerts fire within 5 minutes of incident

**Risk Mitigation:**

**L1 Risk: Clarification loop is clunky**
- **Mitigation**: Test with 20 real users, add "skip clarification" button, simplify if >30% say "just answer"

**L2 Risk: Streaming breaks on slow connections**
- **Mitigation**: Test on 3G network, add timeout handling, fallback to non-streaming

**L3 Risk: Qdrant migration breaks retrieval**
- **Mitigation**: Run ChromaDB and Qdrant in parallel for 1 week, compare results, only cut over when 100% match

**L4 Risk: Rate limiting is too strict or too loose**
- **Mitigation**: Start generous (100/hour Free, 1000/hour Standard), monitor for 2 weeks, adjust based on data

**Leveraging OSS: What to Clone, What to Study**

**Clone (copy code directly):**
- GiovanniPasq/agentic-rag-for-dummies → L1 clarification state machine
- lawglance/lawglance → L2 API structure + Redis cache
- sougaaat/RAG-based-Legal-Assistant → L3 Ragas eval setup

**Study (understand patterns, don't copy):**
- NirDiamant/Controllable-RAG-Agent → Self-RAG verification (L3+)
- onyx-dot-app/onyx → Multi-tenant architecture (L4+)
- Stanford Legal RAG Hallucinations paper → Citation validation (L3+)

**Ignore (not relevant or too complex):**
- dannycahyo/fin-islam (TypeScript, different stack)
- oshoura/IslamAI (stale, Quran/Hadith only)
- weaviate/Verba (unmaintained, Weaviate-coupled)

**Time allocation:**
- 20% of L1 time: Study GiovanniPasq's clarification agent
- 20% of L2 time: Study lawglance's API structure
- 20% of L3 time: Study sougaaat's eval setup

**Don't spend more than 20% of your time studying OSS.** The goal is to ship, not to read code.

---

## Open-Source Library Integration Plan

### Top 5 Repositories to Clone and Study

1. **NirDiamant/Controllable-RAG-Agent** (1.6k⭐, Apache-2.0)
   - **Use in**: L1 (clarification), L3 (evaluation), L4 (citation quality)
   - **Pattern**: Self-RAG verification, three-tier vector stores, RAGAS integration
   - **Action**: Clone first, study architecture

2. **sougaaat/RAG-based-Legal-Assistant** (8⭐)
   - **Use in**: L1 (advanced retrieval), L3 (evaluation)
   - **Pattern**: BM25+FAISS+RRF+multi-hop+multi-query for cross-standard queries
   - **Action**: Copy retrieval pattern verbatim

3. **lawglance/lawglance** (250⭐, Apache-2.0)
   - **Use in**: L2 (API structure), L3 (Redis caching)
   - **Pattern**: End-to-end production layout, Redis LLM cache, legal-codes corpus pattern
   - **Action**: Lift L2 API + L3 ops layout

4. **GiovanniPasq/agentic-rag-for-dummies** (LangGraph)
   - **Use in**: L1 (clarification loop)
   - **Pattern**: Explicit LangGraph clarification state machine with human-in-loop pause
   - **Action**: Drop-in pattern for L1

5. **onyx-dot-app/onyx** (29.1k⭐, MIT)
   - **Use in**: L3+ (multi-tenant, audit, eval dashboards)
   - **Pattern**: Hybrid search (BM25+embed+rerank), 50+ connectors, RBAC, agents framework
   - **Action**: Study at L3+ for enterprise features

**Bonus Dependencies:**
- **Ragas** (13.8k⭐, Apache-2.0): Nightly faithfulness golden eval
- **DeepEval**: Pytest CI gates blocking grounding regressions

---

## L1-L4 Implementation Plan

### L1: Clarification Loop & Error Handling (2 weeks)

**MVP Scope:**
- 2-turn clarification maximum (ask twice, then answer with what you have)
- Session expiry: 30 minutes
- In-memory session store (dict, no Redis yet)
- LangGraph for state machine (adopt GiovanniPasq's pattern)
- No conversation history beyond current clarification

**Technical Tasks:**
1. **Adopt LangGraph for clarification**
   - Clone GiovanniPasq/agentic-rag-for-dummies
   - Study their clarification agent
   - Adapt to Gemini (they use OpenAI)
   - Implement state machine: INITIAL → ANALYZING → CLARIFYING → READY → COMPLETE

2. **Add error handling and retry logic**
   - Wrap LLM calls with try/except and exponential backoff
   - Add custom exceptions: `GeminiAPIError`, `RetrievalError`, `SessionExpiredError`
   - Add graceful degradation (if ChromaDB down, return cached results)

3. **Add structured logging**
   - Replace `print()` with `logging` module
   - JSON logs for easy parsing
   - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

4. **Add session management (in-memory)**
   - Create `Session` dataclass with `session_id`, `user_id`, `created_at`, `expires_at`, `conversation_history`, `clarification_state`
   - Store sessions in dict: `sessions: Dict[str, Session] = {}`
   - Implement session expiry (30 minutes)

5. **Add integration tests**
   - Test clarification loop completes within 2 turns
   - Test clarification loop doesn't exceed max turns
   - Test session expiry
   - Test error handling (LLM API failure, ChromaDB failure)

**Defer to L2+:**
- Multi-session management
- Conversation history across queries
- Smart variable extraction

**Success Criteria:**
- ✅ 80% of test queries complete within 2 turns
- ✅ 0 infinite loops in 100 test queries
- ✅ Clarification questions are relevant (manual review of 20 queries)
- ✅ 60% code coverage

### L2: API + Streaming (2 weeks)

**MVP Scope:**
- FastAPI with POST /query endpoint
- SSE streaming only (no WebSocket)
- Same clarification loop as L1, now over HTTP
- CORS enabled for web clients
- Basic rate limiting (in-memory counter)

**Technical Tasks:**
1. **Adopt FastAPI + SSE**
   - Clone lawglance/lawglance API structure
   - Create `src/api/main.py` (FastAPI app)
   - Create `src/api/routes/query.py` (POST /query)
   - Create `src/api/routes/stream.py` (GET /stream for SSE)
   - Create `src/api/middleware/auth.py` (JWT authentication)
   - Create `src/api/middleware/rate_limit.py` (in-memory rate limiting)
   - Create `src/api/schemas/request.py` (Pydantic models)

2. **Implement SSE streaming**
   - Use `StreamingResponse` from FastAPI
   - Yield SSE events: `thinking`, `retrieved`, `token`, `done`
   - Handle client disconnects gracefully

3. **Add JWT authentication**
   - Use `python-jose` for JWT tokens
   - Create `/auth/login` endpoint
   - Create `/auth/register` endpoint
   - Protect `/query` and `/stream` endpoints

4. **Add in-memory rate limiting**
   - Track requests per user per hour
   - Return HTTP 429 when limit exceeded
   - Include rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

5. **Add API tests**
   - Test `/query` endpoint
   - Test `/stream` endpoint (SSE)
   - Test authentication (valid/invalid tokens)
   - Test rate limiting (exceed limit)

**Defer to L3+:**
- WebSocket support
- Redis rate limiting
- Batch endpoints

**Success Criteria:**
- ✅ API response time <5s for 95% of queries
- ✅ Streaming works (tokens arrive incrementally)
- ✅ Rate limiting blocks >100 requests/hour from same IP
- ✅ 70% code coverage

### L3: Production Infrastructure (3 weeks)

**MVP Scope:**
- Redis for sessions and rate limits
- PostgreSQL for audit logs
- Qdrant for vector storage (swap from ChromaDB)
- Ragas eval harness (nightly run)
- Basic monitoring (Prometheus + Grafana)

**Technical Tasks:**
1. **Migrate to Qdrant**
   - Run ChromaDB and Qdrant in parallel for 1 week
   - Compare retrieval results (should be identical)
   - Only cut over when results match 100%
   - Update `src/rag/pipeline.py` to use Qdrant client

2. **Migrate to Redis sessions**
   - Replace in-memory dict with Redis
   - Use Redis TTL for automatic session expiration
   - Serialize session data as JSON
   - Handle Redis connection failures gracefully

3. **Add PostgreSQL audit logs**
   - Create tables: `aaoifi_documents`, `semantic_chunks`, `compliance_rulings`, `users`, `audit_logs`
   - Log all compliance rulings with full provenance
   - Support data export for regulatory review

4. **Add Ragas eval harness**
   - Clone sougaaat/RAG-based-Legal-Assistant eval setup
   - Create gold evaluation set (50 cases, with Islamic finance scholar)
   - Run nightly eval: faithfulness, answer_relevancy, context_precision
   - Generate evaluation reports

5. **Add monitoring**
   - Expose `/metrics` endpoint in Prometheus format
   - Collect metrics: `request_count`, `latency_p95`, `error_rate`, `active_sessions`
   - Set up Grafana dashboards
   - Set up alerting (email + Slack)

6. **Add horizontal scaling**
   - Deploy multiple FastAPI instances behind nginx load balancer
   - Use Redis for shared session state
   - Use PostgreSQL connection pooling
   - Support graceful shutdown

**Defer to L4:**
- Authentication (still open API)
- Multi-tenancy
- Kubernetes
- Advanced monitoring (tracing, alerting)

**Success Criteria:**
- ✅ System handles 100 concurrent users without crashing
- ✅ Ragas faithfulness score >0.8 on gold set
- ✅ Monitoring dashboard shows <5% error rate
- ✅ 80% code coverage

### L4: Advanced Features (2 weeks)

**MVP Scope:**
- Authentication (API keys)
- Rate limiting tied to tiers (Free/Standard/Premium)
- Deployment automation (Docker + CI/CD)
- Alerting (PagerDuty or Opsgenie)

**Technical Tasks:**
1. **Add citation quality enhancement**
   - Extract direct quotes from retrieved chunks
   - Include quote in `AAOIFICitation` with character offsets
   - Calculate confidence score based on similarity scores
   - Rank citations by relevance

2. **Add caching**
   - Cache frequently retrieved chunks in Redis (TTL 1 hour)
   - Cache LLM responses for identical queries (TTL 24 hours)
   - Cache embeddings (TTL 1 hour)

3. **Add advanced evaluation**
   - Integrate Ragas for RAG evaluation (faithfulness, answer_relevancy, context_precision)
   - Integrate DeepEval for LLM evaluation (hallucination, bias, toxicity)
   - Fail CI/CD if faithfulness <0.8 or hallucination >0.1

4. **Add compliance features**
   - Display disclaimer on first interaction
   - Require user acknowledgment of disclaimer
   - Log all compliance rulings with full audit trail
   - Support data export for regulatory review
   - Support data deletion requests (GDPR compliance)

5. **Add deployment automation**
   - Create Dockerfile
   - Create docker-compose.yml
   - Create CI/CD pipeline (GitHub Actions)
   - Deploy to production with one command

**Defer to future:**
- OAuth/SSO
- Multi-region deployment
- Advanced analytics
- Custom dashboards

**Success Criteria:**
- ✅ Users can sign up and get API key in <5 minutes
- ✅ Deployment takes <10 minutes from git push to live
- ✅ Alerts fire within 5 minutes of incident
- ✅ Citation quality: direct quotes with confidence scores in 100% of rulings
- ✅ Evaluation: Ragas faithfulness >0.8, DeepEval hallucination <0.1
- ✅ Performance: p95 latency <2 seconds with caching

---

## Key Takeaways

1. **L0 architecture is solid**: No major refactoring needed, build on it incrementally
2. **Gemini 1.5 Pro is the right choice**: 1M context, cost-effective, proven to follow AAOIFI adherence prompt
3. **ChromaDB → Qdrant at L3**: ChromaDB works for L0-L2, Qdrant needed for production scale
4. **LangGraph for clarification**: Don't hand-code state machines, use LangGraph with Gemini
5. **Streaming is non-negotiable for L2**: Users expect real-time feedback, SSE is sufficient
6. **Citation quality is the moat**: Direct quotes with confidence scores, not just section references
7. **Leverage OSS patterns**: Clone GiovanniPasq, lawglance, sougaaat - don't reinvent the wheel
8. **Stay disciplined about scope**: Stick to MVP list, defer everything else
9. **Test early and often**: 60% coverage L1, 70% L2, 80% L3+
10. **Ship each layer before moving to next**: Don't start L2 until L1 is complete and tested

---

## Next Steps

1. **Update requirements.md and design.md** with L1-L4 details
2. **Create L1 epic and stories** in sprint planning
3. **Clone top 5 OSS repos** and study patterns (20% of L1 time)
4. **Start L1 implementation** with LangGraph clarification loop

---

*This document compiles insights from Winston (Architect), Amelia (Dev), John (PM), and Mary (Analyst) following L0 completion review.*
