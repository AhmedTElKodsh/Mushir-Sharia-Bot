# Agent Roundtable Summary: L0 Review & L1-L4 Planning

**Date:** Context Transfer Session  
**Participants:** Winston (Architect), Amelia (Dev), John (PM), Mary (Analyst)  
**Purpose:** Review L0 implementation and plan L1-L4 with OSS library integration

---

## Executive Summary

The BMAD agent team conducted a comprehensive roundtable review of the completed L0 implementation and collaboratively planned L1-L4 layers. Key findings:

✅ **L0 is solid** - Clean architecture, no refactoring needed  
✅ **9-week timeline to L4** - Aggressive but achievable with disciplined scope management  
✅ **$1,350 total cost** - Infrastructure + LLM API costs over 9 weeks  
✅ **OSS leverage strategy** - Adopt LangGraph (L1), FastAPI+SSE (L2), Ragas+DeepEval (L3)  
⚠️ **Cost model needs adjustment** - Current pricing underwater for Standard/Premium tiers  

---

## L0 Implementation Review

### What Was Built (26 files, ~1,220 LOC)

**Core Components:**
- ✅ Data models (AAOIFICitation, SemanticChunk, ComplianceRuling)
- ✅ RAG pipeline (ChromaDB + all-mpnet-base-v2)
- ✅ Gemini 1.5 Pro integration ($0.011/query)
- ✅ CLI chatbot with AAOIFI adherence prompt
- ✅ Ingestion script (512-token chunks, 50 overlap)
- ✅ 52 English AAOIFI standards ready
- ✅ Smoke tests (2 active, 1 framework)

**Validated Architectural Decisions:**
1. **Gemini 1.5 Pro** - 1M context, cost-effective → **KEEP**
2. **ChromaDB embedded** - Good for L0-L2 → **Migrate to Qdrant at L3**
3. **all-mpnet-base-v2** - 768-dim, runs locally → **KEEP**
4. **512 token chunks, 50 overlap** - Standard for legal text → **KEEP**
5. **Temperature 0.1** - Consistent outputs → **KEEP**
6. **Clean module separation** - models, rag, chatbot → **No refactoring needed**

### Technical Debt Identified

1. **LLM call is brittle** - No error handling, no retries, assumes response.text exists
2. **No structured logging** - Only print() statements
3. **Hardcoded prompts** - Should be configurable for A/B testing
4. **No session management** - Need Session dataclass
5. **No observability** - Need metrics, tracing, monitoring

---

## Agent Perspectives

### 👨‍💼 Winston (Architect) - Strategic Decisions

**Key Insights:**
1. **Clarification loop must be LLM-driven** - Not hand-coded state machine, use LangGraph
2. **Streaming is non-negotiable for L2** - User experience requires incremental delivery
3. **Citation quality is the moat** - Not the RAG tech itself
4. **Rate limits must tie to actual costs** - Free tier subsidizes, Standard underwater
5. **ChromaDB → Qdrant at L3** - ChromaDB works for L1-L2, Qdrant for production scale

**Cost Analysis:**
- Base cost: $0.011/query (Gemini input + output)
- Free tier (10 queries/day): $3.30/month (subsidized at $0)
- Standard tier (100 queries/day): $33/month (underwater at $10/month)
- Premium tier (1000 queries/day): $330/month (underwater at $80/month)
- **Recommendation**: Lower rate limits OR increase pricing

### 👩‍💻 Amelia (Dev) - Implementation Strategy

**Code Quality Assessment:**
- ✅ Clean module separation - no refactoring needed
- ✅ Dataclasses - converts cleanly to Pydantic for FastAPI
- ✅ Environment-driven config - carries through L4
- ❌ LLM call needs error handling, retries, exponential backoff
- ❌ Add structured logging in L1
- ❌ Move prompts to config for A/B testing

**OSS Libraries to Adopt:**

**L1: LangGraph for Clarification**
- **Source**: GiovanniPasq/agentic-rag-for-dummies
- **Pattern**: Explicit state machine with human-in-loop
- **Action**: Clone and adapt to Gemini

**L2: FastAPI + SSE for Streaming**
- **Source**: lawglance/lawglance
- **Pattern**: API structure + Redis cache
- **Action**: Lift API layout, keep CLI working (backward compatibility)

**L3: Ragas + DeepEval for Evaluation**
- **Source**: sougaaat/RAG-based-Legal-Assistant
- **Pattern**: Ragas for nightly eval, DeepEval for CI gates
- **Action**: Copy eval setup verbatim

**Testing Strategy:**
- L1: Integration tests for clarification loop (60% coverage)
- L2: API tests for endpoints (70% coverage)
- L3: Eval tests for gold set (80% coverage)

**Development Workflow:**
- Feature branches for each layer
- Keep CLI working (backward compatibility)
- Integration tests as contracts - must pass in all layers

### 📋 John (PM) - Scope Management

**MVP Definitions:**

**L1 MVP (2 weeks):**
- 2-turn clarification maximum
- Session expiry: 30 minutes
- In-memory session store (no Redis yet)
- LangGraph for state machine
- No conversation history beyond current clarification

**L2 MVP (2 weeks):**
- FastAPI with POST /query endpoint
- SSE streaming only (no WebSocket)
- Same clarification loop, now over HTTP
- CORS enabled
- Basic rate limiting (in-memory counter)

**L3 MVP (3 weeks):**
- Redis for sessions and rate limits
- PostgreSQL for audit logs
- Qdrant for vector storage
- Ragas eval harness (nightly run)
- Basic monitoring (Prometheus + Grafana)

**L4 MVP (2 weeks):**
- Authentication (API keys)
- Rate limiting tied to tiers (Free/Standard/Premium)
- Deployment automation (Docker + CI/CD)
- Alerting (PagerDuty or Opsgenie)

**The "No" List (Scope Creep Prevention):**
- ❌ L1: Conversation history across sessions, smart variable extraction, multi-language
- ❌ L2: WebSocket, GraphQL, batch endpoints
- ❌ L3: Authentication (defer to L4), multi-tenancy, advanced analytics
- ❌ L4: OAuth/SSO, multi-region, custom dashboards

**Success Metrics:**
- L1: 80% of queries complete within 2 turns, 0 infinite loops
- L2: API response <5s for 95% of queries, streaming works
- L3: 100 concurrent users, Ragas faithfulness >0.8, <5% error rate
- L4: Users get API key in <5min, deployment <10min, alerts fire within 5min

**Risk Mitigation:**
- **L1 Risk**: Clarification loop is clunky → Test with 20 real users, add "skip clarification" button
- **L2 Risk**: Streaming breaks on slow connections → Test on 3G, add timeout handling
- **L3 Risk**: Qdrant migration breaks retrieval → Run ChromaDB and Qdrant in parallel for 1 week
- **L4 Risk**: Rate limiting too strict/loose → Start generous, monitor 2 weeks, adjust based on data

### 📊 Mary (Analyst) - Evaluation & Metrics

**Evaluation Strategy:**

**L1 Metrics:**
- Clarification effectiveness: % queries completing within 2 turns
- Question relevance: Manual review of 20 queries
- Loop stability: 0 infinite loops in 100 test queries

**L2 Metrics:**
- API latency: p50, p95, p99 response times
- Streaming performance: Time to first token, tokens/second
- Rate limit effectiveness: % blocked requests

**L3 Metrics:**
- Retrieval quality: Precision@k, Recall@k, MRR
- Faithfulness: Ragas faithfulness score >0.8
- Answer relevance: Ragas answer-relevance score >0.7
- System health: Error rate, uptime, concurrent users

**L4 Metrics:**
- Citation accuracy: Claim-level grounding analysis
- Cost per query: Track actual vs. target ($0.011)
- User satisfaction: NPS, query success rate

**Cost Modeling:**
- Base cost: $0.011/query (Gemini input + output)
- Free tier: 10 queries/day = $0.11/day = $3.30/month (subsidized)
- Standard tier: 100 queries/day = $1.10/day = $33/month (at $10/month = underwater)
- Premium tier: 1000 queries/day = $11/day = $330/month (at $80/month = underwater)
- **Conclusion**: Rate limits must be lower OR pricing must be higher

**Data Requirements:**
- L1: Session logs (query, clarifications, completion status)
- L2: API logs (latency, status codes, rate limit hits)
- L3: Retrieval logs (chunks, scores, relevance), eval results
- L4: Cost tracking, citation validation results

**Reporting:**
- L3: Grafana dashboard (latency, error rate, cache hit rate)
- L3: Nightly eval report (faithfulness, answer-relevance)
- L4: Cost dashboard (queries/day, cost/query, tier distribution)

---

## L1-L4 Roadmap

**Total Timeline: 9 weeks (2.25 months)**

| Layer | Focus | Duration | Dev Time | Scholar Time | DevOps Time |
|-------|-------|----------|----------|--------------|-------------|
| L1 | Clarification Loop | 2 weeks | 10 days | 2 days | 0 days |
| L2 | API + Streaming | 2 weeks | 8 days | 0 days | 2 days |
| L3 | Production Ready | 3 weeks | 10 days | 3 days | 5 days |
| L4 | Scale + Ops | 2 weeks | 5 days | 0 days | 5 days |
| **Total** | | **9 weeks** | **33 days** | **5 days** | **12 days** |

**Cost Estimates (excluding salaries):**

| Layer | Infrastructure | LLM API | Total/Month |
|-------|----------------|---------|-------------|
| L1 | $0 (local) | $50 (testing) | $50 |
| L2 | $0 (local) | $100 (testing) | $100 |
| L3 | $200 (Redis+Postgres+Qdrant) | $200 (eval+testing) | $400 |
| L4 | $300 (production) | $500 (production) | $800 |

**Total cost to reach L4: ~$1,350 over 9 weeks**

---

## Open-Source Library Integration Strategy

### Top 5 Repositories to Study

1. **NirDiamant/Controllable-RAG-Agent** ⭐⭐⭐ (1.6k⭐, Apache-2.0)
   - **Use in**: L1 (clarification), L3 (evaluation), L4 (citation quality)
   - **Pattern**: Self-RAG verification, three-tier vector stores, RAGAS integration
   - **Action**: Clone first, study architecture

2. **sougaaat/RAG-based-Legal-Assistant** ⭐⭐⭐ (8⭐)
   - **Use in**: L1 (advanced retrieval), L3 (evaluation)
   - **Pattern**: BM25+FAISS+RRF+multi-hop+multi-query for cross-standard queries
   - **Action**: Copy retrieval pattern verbatim

3. **lawglance/lawglance** ⭐⭐⭐ (250⭐, Apache-2.0)
   - **Use in**: L2 (API structure), L3 (Redis caching)
   - **Pattern**: End-to-end production layout, Redis LLM cache
   - **Action**: Lift L2 API + L3 ops layout

4. **GiovanniPasq/agentic-rag-for-dummies** ⭐⭐ (LangGraph)
   - **Use in**: L1 (clarification loop)
   - **Pattern**: Explicit LangGraph clarification state machine with human-in-loop
   - **Action**: Drop-in pattern for L1

5. **onyx-dot-app/onyx** ⭐ (29.1k⭐, MIT)
   - **Use in**: L3+ (multi-tenant, audit dashboards)
   - **Pattern**: Hybrid search, RBAC, agents framework
   - **Action**: Study at L3+ for enterprise features

### Time Allocation for OSS Study

- 20% of L1 time: Study GiovanniPasq's clarification agent
- 20% of L2 time: Study lawglance's API structure
- 20% of L3 time: Study sougaaat's eval setup

**Rule**: Don't spend more than 20% of time studying OSS. Goal is to ship, not to read code.

---

## Key Decisions & Action Items

### Immediate Actions (L1)

1. ✅ **Adopt LangGraph** - Clone GiovanniPasq/agentic-rag-for-dummies, adapt to Gemini
2. ✅ **Add error handling** - Retry logic, exponential backoff, graceful degradation
3. ✅ **Add structured logging** - Replace print() with logging framework
4. ✅ **Add session management** - Session dataclass with state tracking
5. ✅ **Add integration tests** - Clarification loop tests, 60% coverage target

### L2 Actions

1. ✅ **Adopt FastAPI + SSE** - Clone lawglance/lawglance API structure
2. ✅ **Keep CLI working** - Backward compatibility, both interfaces coexist
3. ✅ **Add API tests** - Endpoint tests, streaming tests, 70% coverage target

### L3 Actions

1. ✅ **Migrate to Qdrant** - Run ChromaDB and Qdrant in parallel for 1 week
2. ✅ **Add Redis** - Sessions, rate limits, LLM cache
3. ✅ **Add PostgreSQL** - Audit logs, user data
4. ✅ **Integrate Ragas** - Nightly eval harness
5. ✅ **Add monitoring** - Prometheus + Grafana dashboard

### L4 Actions

1. ✅ **Add authentication** - API key-based
2. ✅ **Add tier-based rate limiting** - Free/Standard/Premium
3. ✅ **Add deployment automation** - Docker + CI/CD
4. ✅ **Add alerting** - PagerDuty or Opsgenie

---

## Consensus & Alignment

**All agents agree:**
1. L0 is solid - no refactoring needed
2. 9-week timeline is aggressive but achievable
3. Scope discipline is critical - stick to MVP, defer everything else
4. OSS leverage is key - don't reinvent, adopt proven patterns
5. Cost model needs adjustment - current pricing underwater

**Key trade-offs accepted:**
1. In-memory sessions (L1-L2) → Redis (L3) - simplicity over scale early
2. SSE only (L2) → defer WebSocket - good enough for MVP
3. No auth (L1-L3) → API keys (L4) - open API for early testing
4. ChromaDB (L0-L2) → Qdrant (L3) - avoid premature optimization

**Next steps:**
1. Update requirements.md and design.md with agent insights ✅ DONE
2. Begin L1 implementation - LangGraph clarification loop
3. Study GiovanniPasq/agentic-rag-for-dummies (20% of L1 time)
4. Add error handling, logging, session management
5. Write integration tests for clarification loop

---

**Document Status:** ✅ Complete  
**Planning Documents Updated:** ✅ requirements.md, design.md  
**Ready for L1 Implementation:** ✅ Yes
