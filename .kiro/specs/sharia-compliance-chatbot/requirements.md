# Requirements Document: Sharia Compliance Chatbot

## Introduction

This document specifies the requirements for an AI-powered chatbot system that analyzes financial operations against AAOIFI (Accounting and Auditing Organization for Islamic Financial Institutions) Accounting Standards to determine Sharia compliance. The system uses Retrieval-Augmented Generation (RAG) architecture to ground all compliance rulings strictly in retrieved AAOIFI standards, and implements an interactive clarification loop to gather necessary details before making final determinations.

The system progresses through five implementation layers (L0-L4), with **L0 already complete** as the foundational RAG loop. This document now focuses on requirements for L1-L4 based on L0 implementation learnings.

## L0 Implementation Status (COMPLETE ✅)

**What was built:**
- ✅ Data models (AAOIFICitation, SemanticChunk, ComplianceRuling)
- ✅ RAG pipeline with ChromaDB and sentence-transformers (all-mpnet-base-v2)
- ✅ Gemini 1.5 Pro integration (replacing OpenAI)
- ✅ CLI chatbot with AAOIFI adherence system prompt
- ✅ Ingestion script for markdown corpus
- ✅ Smoke tests (ingestion, retrieval)
- ✅ 512 token chunks with 50 token overlap
- ✅ 26 files created (10 source, 4 tools, 3 samples, 6 docs)
- ✅ ~1,220 lines of code
- ✅ Clean separation: models, rag, chatbot modules
- ✅ All tests passing (2 active, 1 framework)
- ✅ 52 English AAOIFI standards ready to ingest

**Key architectural decisions validated in L0:**
- Gemini 1.5 Pro: 1M context window, cost-effective ($0.011/query) - KEEP
- ChromaDB embedded: Good for L0-L2, will migrate to Qdrant at L3
- all-mpnet-base-v2: 768-dim, English-only, runs locally - KEEP
- 512 token chunks, 50 overlap: Standard for legal text - KEEP
- Temperature 0.1: Consistent, deterministic outputs - KEEP

**What L0 proved:**
- RAG loop works end-to-end on AAOIFI text
- Citations can be extracted and formatted
- Retrieval quality is acceptable (threshold 0.3)
- Gemini follows AAOIFI adherence prompt
- Clean module separation enables L1-L4 extension without refactoring
- Dataclasses provide type safety and IDE support

**What L0 lacks (by design):**
- No clarification loop (single-turn only) → L1
- No conversation history → L1
- No streaming → L2
- No API (terminal only) → L2
- No error handling/retry logic → L1
- No comprehensive tests → L1-L3
- No session management → L1 (in-memory), L3 (Redis)
- No logging (only print statements) → L1
- No observability/monitoring → L3

**Technical Debt from L0 (to address in L1+):**
- LLM call is brittle (no error handling, no retries)
- No structured logging (only print statements)
- Hardcoded prompt templates (should be configurable)
- No session management
- No observability (metrics, tracing)

## Glossary

- **Chatbot_System**: The complete AI-powered application that analyzes financial operations for Sharia compliance
- **Compliance_Analyzer**: The component that evaluates financial operations against AAOIFI standards
- **RAG_Pipeline**: The Retrieval-Augmented Generation system that retrieves relevant AAOIFI standards and augments LLM responses (✅ L0 complete)
- **Document_Acquisition_Module**: The component responsible for acquiring and parsing AAOIFI standards from source URLs
- **Vector_Database**: ChromaDB (L0-L2) or Qdrant (L3+) for storing semantically chunked AAOIFI standards
- **Clarification_Engine**: The LLM-driven component that identifies missing information and prompts users for additional details (L1)
- **LLM**: Gemini 1.5 Pro - generates compliance analysis responses with 1M context window
- **AAOIFI_Standards**: The authoritative Sharia compliance standards published by AAOIFI at https://aaoifi.com/accounting-standards-2/?lang=en
- **Financial_Operation**: A user-described transaction or financial activity requiring Sharia compliance evaluation
- **Compliance_Ruling**: The final determination with citations, confidence scores, and provenance (✅ L0 schema complete)
- **Semantic_Chunk**: A 512-token segment of AAOIFI text with 50-token overlap (✅ L0 complete)
- **User**: The person submitting financial operations for compliance analysis
- **System_Prompt**: AAOIFI adherence instructions that configure Gemini (✅ L0 complete)
- **Session**: A multi-turn conversation with state tracking (L1+)
- **SSE**: Server-Sent Events for streaming LLM responses (L2)

## Requirements

### Requirement 1: Document Acquisition and Parsing

**User Story:** As a system administrator, I want to acquire and parse AAOIFI standards from the official source, so that the system has an authoritative knowledge base for compliance analysis.

#### Acceptance Criteria

1. THE Document_Acquisition_Module SHALL retrieve AAOIFI standards from https://aaoifi.com/accounting-standards-2/?lang=en
2. WHERE automated acquisition is configured, THE Document_Acquisition_Module SHALL use web scraping tools to extract document content
3. WHEN a document is in PDF format, THE Document_Acquisition_Module SHALL parse the PDF into structured text
4. WHEN a document is in HTML format, THE Document_Acquisition_Module SHALL extract the text content while preserving document structure
5. WHEN document acquisition fails, THE Document_Acquisition_Module SHALL log the error with the document identifier and failure reason
6. THE Document_Acquisition_Module SHALL store acquired documents with metadata including source URL, acquisition timestamp, and document version
7. FOR ALL acquired documents, THE Document_Acquisition_Module SHALL validate that the content is non-empty and contains expected AAOIFI standard markers

### Requirement 2: Semantic Chunking for Legal and Financial Texts

**User Story:** As a system architect, I want AAOIFI standards to be semantically chunked, so that the RAG pipeline can retrieve precise and contextually relevant passages.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL segment AAOIFI standards into semantic chunks
2. WHEN chunking a document, THE RAG_Pipeline SHALL preserve logical boundaries such as sections, subsections, and numbered provisions
3. THE RAG_Pipeline SHALL ensure each semantic chunk contains sufficient context to be independently understood
4. WHEN a provision references another section, THE RAG_Pipeline SHALL include the reference information in the chunk metadata
5. THE RAG_Pipeline SHALL limit chunk size to a maximum token count that fits within the LLM context window
6. FOR ALL semantic chunks, THE RAG_Pipeline SHALL generate vector embeddings for similarity search
7. THE RAG_Pipeline SHALL store chunks in the Vector_Database with metadata including source document, section number, and chunk position

### Requirement 3: Vector Database Storage and Retrieval

**User Story:** As a developer, I want a vector database that stores AAOIFI standard chunks, so that the system can efficiently retrieve relevant standards for user queries.

#### Acceptance Criteria

1. THE Vector_Database SHALL store semantic chunks with their vector embeddings
2. WHEN a query is submitted, THE Vector_Database SHALL perform similarity search and return the top-k most relevant chunks
3. THE Vector_Database SHALL support filtering by document metadata such as standard number or publication date
4. WHERE the system is in MVP mode, THE Vector_Database SHALL use a lightweight embedded database solution
5. WHERE the system is in production mode, THE Vector_Database SHALL use a scalable distributed database solution
6. WHEN retrieval is requested, THE Vector_Database SHALL return results within 500 milliseconds for 95% of queries
7. THE Vector_Database SHALL maintain an index that supports efficient similarity search across all stored embeddings

### Requirement 4: Strict AAOIFI Standard Grounding

**User Story:** As a compliance officer, I want all chatbot responses to be grounded strictly in retrieved AAOIFI standards, so that rulings are authoritative and traceable.

#### Acceptance Criteria

1. WHEN generating a compliance ruling, THE Compliance_Analyzer SHALL base the response exclusively on retrieved AAOIFI standard chunks
2. THE Compliance_Analyzer SHALL include citations to specific AAOIFI standard sections in every compliance ruling
3. IF no relevant AAOIFI standard is retrieved, THEN THE Compliance_Analyzer SHALL inform the user that insufficient standards were found and SHALL NOT generate a speculative ruling
4. THE Compliance_Analyzer SHALL provide direct quotations from AAOIFI standards to support each compliance determination
5. WHEN multiple AAOIFI standards apply, THE Compliance_Analyzer SHALL cite all relevant standards and explain how they collectively inform the ruling
6. THE LLM SHALL be configured with a System_Prompt that prohibits generating compliance rulings without retrieved AAOIFI standard support
7. FOR ALL compliance rulings, THE Compliance_Analyzer SHALL include traceability information linking the ruling to specific retrieved chunks

### Requirement 5: Interactive Clarification Loop

**User Story:** As a user, I want the system to identify missing information and ask clarifying questions, so that I receive accurate compliance rulings based on complete information.

#### Acceptance Criteria

1. WHEN a user submits a Financial_Operation description, THE Clarification_Engine SHALL analyze the input to identify required variables for compliance analysis
2. IF required variables are missing, THEN THE Clarification_Engine SHALL generate specific questions to elicit the missing information
3. THE Clarification_Engine SHALL present clarifying questions to the user before generating a final compliance ruling
4. WHEN the user provides additional information, THE Clarification_Engine SHALL update the Financial_Operation context and re-evaluate completeness
5. THE Clarification_Engine SHALL iterate the clarification process until all required variables are obtained or the user indicates they cannot provide further information
6. WHEN all required information is gathered, THE Clarification_Engine SHALL pass the complete Financial_Operation description to the Compliance_Analyzer
7. THE Clarification_Engine SHALL maintain conversation state across multiple clarification exchanges within a single session

### Requirement 6: User Input Processing

**User Story:** As a user, I want to describe financial operations in natural language, so that I can easily request compliance analysis without technical knowledge.

#### Acceptance Criteria

1. THE Chatbot_System SHALL accept natural language descriptions of financial operations as input
2. WHEN a user submits input, THE Chatbot_System SHALL parse the description to extract key financial operation attributes
3. THE Chatbot_System SHALL support descriptions of common financial operations including purchases, loans, investments, and contracts
4. WHEN input contains ambiguous terms, THE Chatbot_System SHALL request clarification before proceeding with analysis
5. THE Chatbot_System SHALL handle multi-sentence descriptions and extract relevant details from complex narratives
6. THE Chatbot_System SHALL preserve the original user input for audit and traceability purposes
7. WHEN input is received, THE Chatbot_System SHALL acknowledge receipt and indicate that analysis is in progress

### Requirement 7: Compliance Ruling Generation

**User Story:** As a user, I want to receive clear compliance rulings with supporting evidence, so that I understand whether my financial operation is Sharia compliant and why.

#### Acceptance Criteria

1. WHEN all required information is available, THE Compliance_Analyzer SHALL generate a Compliance_Ruling
2. THE Compliance_Ruling SHALL explicitly state whether the Financial_Operation is compliant, non-compliant, or requires additional conditions for compliance
3. THE Compliance_Ruling SHALL include specific AAOIFI standard citations with section numbers
4. THE Compliance_Ruling SHALL provide reasoning that connects the Financial_Operation details to the applicable AAOIFI standards
5. WHEN a Financial_Operation is non-compliant, THE Compliance_Ruling SHALL explain which aspects violate Sharia principles
6. WHEN a Financial_Operation could be made compliant with modifications, THE Compliance_Ruling SHALL suggest specific changes
7. THE Compliance_Ruling SHALL be presented in clear, accessible language suitable for users without specialized Islamic finance knowledge

### Requirement 8: System Prompt Configuration for AAOIFI Adherence

**User Story:** As a system architect, I want the LLM to be configured with strict instructions for AAOIFI adherence, so that the system maintains compliance authority and accuracy.

#### Acceptance Criteria

1. THE Chatbot_System SHALL configure the LLM with a System_Prompt that mandates strict adherence to AAOIFI standards
2. THE System_Prompt SHALL instruct the LLM to refuse generating compliance rulings without retrieved AAOIFI standard support
3. THE System_Prompt SHALL instruct the LLM to cite specific AAOIFI standard sections in all compliance determinations
4. THE System_Prompt SHALL instruct the LLM to identify missing information and request clarification rather than making assumptions
5. THE System_Prompt SHALL instruct the LLM to distinguish between definitive rulings based on clear standards and tentative guidance requiring expert review
6. THE System_Prompt SHALL be version-controlled and auditable for compliance verification
7. WHEN the System_Prompt is updated, THE Chatbot_System SHALL log the change with timestamp and rationale

### Requirement 9: RAG Pipeline Integration

**User Story:** As a developer, I want a fully integrated RAG pipeline, so that user queries automatically trigger retrieval and augmented generation.

#### Acceptance Criteria

1. WHEN a user query is processed, THE RAG_Pipeline SHALL generate a query embedding
2. THE RAG_Pipeline SHALL retrieve the top-k most relevant semantic chunks from the Vector_Database
3. THE RAG_Pipeline SHALL construct an augmented prompt that includes the user query and retrieved AAOIFI standard chunks
4. THE RAG_Pipeline SHALL pass the augmented prompt to the LLM for response generation
5. WHEN retrieval returns no relevant chunks above a similarity threshold, THE RAG_Pipeline SHALL inform the Compliance_Analyzer that insufficient standards were found
6. THE RAG_Pipeline SHALL log all retrieval operations including query, retrieved chunks, and similarity scores for debugging and audit
7. THE RAG_Pipeline SHALL support configurable retrieval parameters including number of chunks (k) and similarity threshold

### Requirement 10: MVP to Production Progression

**User Story:** As a product manager, I want the system to progress from MVP to production through defined phases, so that we can validate the approach early and scale systematically.

#### Acceptance Criteria

1. THE Chatbot_System SHALL support a configuration flag that distinguishes MVP mode from production mode
2. WHERE the system is in MVP mode, THE Chatbot_System SHALL use lightweight components including embedded vector database and simplified document acquisition
3. WHERE the system is in production mode, THE Chatbot_System SHALL use scalable components including distributed vector database and automated document acquisition
4. THE Chatbot_System SHALL implement Phase 1 (research) by documenting existing open-source projects, RAG implementations, and Islamic finance AI repositories
5. THE Chatbot_System SHALL implement Phase 2 (data acquisition) by supporting both manual and automated AAOIFI standard acquisition strategies
6. THE Chatbot_System SHALL implement Phase 3 (RAG pipeline) by integrating semantic chunking, vector database, and retrieval mechanisms
7. THE Chatbot_System SHALL implement Phase 4 (chatbot logic) by implementing the clarification loop state machine and system prompting

### Requirement 11: Python-Based Implementation

**User Story:** As a developer, I want the system implemented in Python, so that we can leverage the rich ecosystem of AI, NLP, and web scraping libraries.

#### Acceptance Criteria

1. THE Chatbot_System SHALL be implemented using Python 3.9 or higher (Python 3.11+ recommended for better performance)
2. THE Document_Acquisition_Module SHALL use Python web scraping libraries such as Playwright or Crawl4AI
3. THE RAG_Pipeline SHALL use Python libraries for embeddings generation and vector operations
4. THE Chatbot_System SHALL use Python libraries for LLM integration
5. THE Chatbot_System SHALL follow Python best practices including type hints, docstrings, and PEP 8 style guidelines
6. THE Chatbot_System SHALL use virtual environments for dependency management
7. THE Chatbot_System SHALL provide a requirements.txt file listing all Python dependencies with pinned versions

### Requirement 12: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error handling and logging, so that I can diagnose issues and maintain system reliability.

#### Acceptance Criteria

1. WHEN an error occurs in any component, THE Chatbot_System SHALL log the error with timestamp, component name, error type, and stack trace
2. WHEN document acquisition fails, THE Chatbot_System SHALL continue operating with existing documents and SHALL notify administrators
3. WHEN the Vector_Database is unavailable, THE Chatbot_System SHALL return an error message to the user and SHALL log the outage
4. WHEN the LLM API fails, THE Chatbot_System SHALL retry the request up to 3 times with exponential backoff
5. IF all retry attempts fail, THEN THE Chatbot_System SHALL inform the user that the service is temporarily unavailable
6. THE Chatbot_System SHALL maintain separate log files for different severity levels including DEBUG, INFO, WARNING, ERROR, and CRITICAL
7. THE Chatbot_System SHALL support configurable log retention policies to manage storage

### Requirement 13: Session Management

**User Story:** As a user, I want my conversation context to be maintained across multiple exchanges, so that I can have a natural multi-turn conversation without repeating information.

#### Acceptance Criteria

1. WHEN a user initiates a conversation, THE Chatbot_System SHALL create a session with a unique session identifier
2. THE Chatbot_System SHALL maintain conversation history within a session including all user inputs and system responses
3. WHEN generating responses, THE Chatbot_System SHALL consider the full conversation history to maintain context
4. THE Chatbot_System SHALL maintain session state for the Clarification_Engine including identified variables and pending questions
5. WHEN a session is inactive for 30 minutes, THE Chatbot_System SHALL expire the session and clear associated data
6. THE Chatbot_System SHALL support session resumption if the user returns within the expiration window
7. THE Chatbot_System SHALL store session data securely and SHALL NOT persist sensitive financial information beyond the session lifetime

### Requirement 14: Performance and Scalability

**User Story:** As a system architect, I want the system to meet performance targets and scale to handle increasing load, so that users receive timely responses as adoption grows.

#### Acceptance Criteria

1. WHEN a user submits a query, THE Chatbot_System SHALL return an initial response within 5 seconds for 95% of requests
2. THE Vector_Database SHALL support at least 1000 queries per minute in production mode
3. THE RAG_Pipeline SHALL process retrieval and augmentation within 2 seconds for 95% of requests
4. THE Chatbot_System SHALL support at least 100 concurrent user sessions in production mode
5. WHEN load increases, THE Chatbot_System SHALL scale horizontally by adding additional service instances
6. THE Chatbot_System SHALL implement caching for frequently retrieved AAOIFI standard chunks to reduce database load
7. THE Chatbot_System SHALL monitor performance metrics including response time, throughput, and error rate

### Requirement 15: Security and Data Privacy

**User Story:** As a compliance officer, I want user data to be handled securely and privately, so that sensitive financial information is protected.

#### Acceptance Criteria

1. THE Chatbot_System SHALL encrypt all data in transit using TLS 1.3 or higher
2. THE Chatbot_System SHALL encrypt sensitive data at rest including user financial operation descriptions
3. THE Chatbot_System SHALL implement authentication to verify user identity before processing requests
4. THE Chatbot_System SHALL implement authorization to ensure users can only access their own session data
5. THE Chatbot_System SHALL sanitize all user inputs to prevent injection attacks
6. THE Chatbot_System SHALL comply with data privacy regulations by not storing personal financial information beyond the session lifetime unless explicitly consented
7. THE Chatbot_System SHALL provide audit logs of all compliance rulings for regulatory review

### Requirement 16: Testing and Validation

**User Story:** As a quality assurance engineer, I want comprehensive testing coverage, so that the system is reliable and produces accurate compliance rulings.

#### Acceptance Criteria

1. THE Chatbot_System SHALL include unit tests for all core components with minimum 80% code coverage
2. THE Chatbot_System SHALL include integration tests that verify end-to-end RAG pipeline functionality
3. THE Chatbot_System SHALL include test cases that verify compliance rulings against known AAOIFI standard interpretations
4. THE Chatbot_System SHALL include tests that verify the Clarification_Engine correctly identifies missing information
5. THE Chatbot_System SHALL include performance tests that validate response time requirements under load, including tests that simulate at least 100 concurrent users to validate the target defined in Requirement 14.4
6. THE Chatbot_System SHALL include security tests that verify input sanitization and authentication mechanisms
7. THE Chatbot_System SHALL maintain a test suite that can be executed automatically in a continuous integration pipeline

### Requirement 17: Documentation and User Guidance

**User Story:** As a user, I want clear documentation and guidance, so that I can effectively use the system and understand its capabilities and limitations.

#### Acceptance Criteria

1. THE Chatbot_System SHALL provide user documentation that explains how to describe financial operations
2. THE Chatbot_System SHALL provide examples of well-formed financial operation descriptions
3. THE Chatbot_System SHALL provide documentation that explains the scope of AAOIFI standards covered
4. THE Chatbot_System SHALL provide documentation that clarifies the system provides guidance based on AAOIFI standards but does not replace qualified Islamic finance scholars
5. THE Chatbot_System SHALL provide developer documentation including architecture diagrams, API specifications, and deployment instructions
6. THE Chatbot_System SHALL provide inline help within the chat interface explaining how to interact with the system
7. THE Chatbot_System SHALL display a disclaimer that compliance rulings should be verified by qualified Islamic finance professionals for critical decisions

### Requirement 18: AAOIFI Standard Updates and Versioning

**User Story:** As a system administrator, I want to update AAOIFI standards when new versions are published, so that the system remains current with the latest compliance guidance.

#### Acceptance Criteria

1. THE Document_Acquisition_Module SHALL support re-acquisition of AAOIFI standards to capture updates
2. WHEN new standards are acquired, THE Document_Acquisition_Module SHALL version the standards with acquisition timestamp
3. THE Vector_Database SHALL support storing multiple versions of AAOIFI standards
4. THE Chatbot_System SHALL allow configuration to specify which AAOIFI standard version to use for compliance analysis
5. WHEN standards are updated, THE Chatbot_System SHALL re-chunk and re-embed the new content
6. THE Chatbot_System SHALL maintain a changelog documenting which AAOIFI standards were updated and when
7. THE Chatbot_System SHALL notify administrators when the AAOIFI standard source URL structure changes and automated acquisition fails

### Requirement 19: Clarification Loop State Machine

**User Story:** As a developer, I want a well-defined state machine for the clarification loop, so that the conversation flow is predictable and maintainable.

#### Acceptance Criteria

1. THE Clarification_Engine SHALL implement a state machine with states including INITIAL, ANALYZING, CLARIFYING, READY, and COMPLETE
2. WHEN a user submits input in INITIAL state, THE Clarification_Engine SHALL transition to ANALYZING state
3. WHEN required information is missing in ANALYZING state, THE Clarification_Engine SHALL transition to CLARIFYING state and prompt the user
4. WHEN the user provides clarification in CLARIFYING state, THE Clarification_Engine SHALL transition back to ANALYZING state
5. WHEN all required information is gathered in ANALYZING state, THE Clarification_Engine SHALL transition to READY state and invoke the Compliance_Analyzer
6. WHEN a compliance ruling is generated in READY state, THE Clarification_Engine SHALL transition to COMPLETE state
7. THE Clarification_Engine SHALL log all state transitions for debugging and audit purposes

### Requirement 21: Rate Limiting and Usage Tiers

**User Story:** As a system operator, I want to enforce per-user rate limits across configurable usage tiers, so that the system remains available and costs are controlled.

#### Acceptance Criteria

1. THE Chatbot_System SHALL enforce per-user query rate limits based on the user's assigned usage tier
2. THE Chatbot_System SHALL support at minimum three tiers: Free (10 queries/hour), Standard (100 queries/hour), and Premium (1000 queries/hour)
3. WHEN a user exceeds their rate limit, THE Chatbot_System SHALL return HTTP 429 with a Retry-After header indicating when the limit resets
4. THE Chatbot_System SHALL include rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset) in all API responses
5. THE Chatbot_System SHALL persist rate limit counters in a shared store so limits are enforced correctly across multiple service instances
6. WHEN a user's tier changes, THE Chatbot_System SHALL apply the new limit at the next rate limit window
7. THE Chatbot_System SHALL log all rate limit violations with user ID, timestamp, and tier

### Requirement 22: Standards Scope and Coverage

**User Story:** As a compliance officer, I want the system's knowledge base scope to be clearly defined, so that users understand which AAOIFI standards are covered and what limitations exist.

#### Acceptance Criteria

1. THE Chatbot_System SHALL explicitly scope its knowledge base to AAOIFI Accounting Standards (FAS series) from https://aaoifi.com/accounting-standards-2/?lang=en
2. THE Chatbot_System SHALL clearly document that AAOIFI Sharia Standards, Governance Standards, and Ethics Standards are outside the current scope
3. WHEN a user query requires standards outside the defined scope, THE Chatbot_System SHALL inform the user that the relevant standard type is not covered
4. THE Chatbot_System SHALL provide documentation listing which specific FAS standards have been acquired and indexed
5. WHEN AAOIFI standards are provided in Arabic and English, THE Document_Acquisition_Module SHALL prioritize the English version for ingestion unless Arabic-capable embedding models are configured
6. THE Chatbot_System SHALL note in all compliance rulings which AAOIFI standard series was used as the basis for the determination
7. WHEN the user asks about a topic covered by a non-FAS AAOIFI standard, THE Chatbot_System SHALL acknowledge the limitation and recommend consulting the relevant AAOIFI standard directly

### Requirement 20: Retrieval Quality Metrics

**User Story:** As a system architect, I want to measure retrieval quality, so that I can optimize the RAG pipeline for accuracy.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL calculate relevance scores for all retrieved chunks
2. THE RAG_Pipeline SHALL log retrieval metrics including number of chunks retrieved, average similarity score, and retrieval latency
3. THE Chatbot_System SHALL support evaluation mode where retrieved chunks are compared against ground truth relevant passages
4. THE Chatbot_System SHALL calculate precision and recall metrics for retrieval in evaluation mode
5. THE Chatbot_System SHALL support A/B testing of different chunking strategies by comparing retrieval quality metrics
6. THE Chatbot_System SHALL provide a dashboard or report showing retrieval quality trends over time
7. WHEN retrieval quality falls below a threshold, THE Chatbot_System SHALL alert administrators to investigate potential issues

---

## L1-L4 Roadmap & Timeline

**Total Timeline: 9 weeks (2.25 months)**

| Layer | Focus | Duration | Dev Time | Scholar Time | DevOps Time |
|-------|-------|----------|----------|--------------|-------------|
| L1 | Clarification Loop | 2 weeks | 10 days | 2 days | 0 days |
| L2 | API + Streaming | 2 weeks | 8 days | 0 days | 2 days |
| L3 | Production Ready | 3 weeks | 10 days | 3 days | 5 days |
| L4 | Scale + Ops | 2 weeks | 5 days | 0 days | 5 days |

**Cost Estimates (excluding salaries):**

| Layer | Infrastructure | LLM API | Total/Month |
|-------|----------------|---------|-------------|
| L1 | $0 (local) | $50 (testing) | $50 |
| L2 | $0 (local) | $100 (testing) | $100 |
| L3 | $200 (Redis+Postgres+Qdrant) | $200 (eval+testing) | $400 |
| L4 | $300 (production) | $500 (production) | $800 |

**Total cost to reach L4: ~$1,350 over 9 weeks**

## Agent Roundtable Insights

### Winston (Architect) - Key Decisions

1. **Gemini 1.5 Pro is the right choice** - 1M context, cost-effective ($0.011/query)
2. **ChromaDB → Qdrant migration at L3** - ChromaDB works for L1-L2, swap to Qdrant for production scale
3. **Clarification loop must be LLM-driven** - Not hand-coded state machine, use LangGraph
4. **Streaming is non-negotiable for L2** - User experience requires incremental token delivery
5. **Citation quality is the moat** - Not the RAG tech, but the grounding accuracy
6. **Rate limits must tie to actual costs** - Free tier ($0) subsidizes $80/month, Standard ($10/month) underwater at 10 queries/day

### Amelia (Dev) - Implementation Strategy

**Code Quality Assessment:**
- ✅ Clean module separation (models, rag, chatbot) - no refactoring needed for L1-L4
- ✅ Dataclasses over dicts - converts cleanly to Pydantic for FastAPI
- ✅ Environment-driven config - carries through L4
- ❌ LLM call is brittle - needs error handling, retries, exponential backoff
- ❌ No logging - add structured logging in L1
- ❌ Hardcoded prompts - move to config for A/B testing

**OSS Libraries to Adopt:**
- **L1**: LangGraph for clarification state machine (study GiovanniPasq/agentic-rag-for-dummies)
- **L2**: FastAPI + SSE for streaming (study lawglance/lawglance API structure)
- **L3**: Ragas for nightly eval, DeepEval for CI gates (study sougaaat/RAG-based-Legal-Assistant)

**Testing Strategy:**
- L1: Add integration tests for clarification loop (60% coverage target)
- L2: Add API tests for endpoints (70% coverage target)
- L3: Add eval tests for gold set (80% coverage target)

**Development Workflow:**
- Feature branches for each layer
- Keep CLI working (backward compatibility)
- Integration tests as contracts - must pass in all layers

### John (PM) - Scope Management

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

### Mary (Analyst) - Evaluation & Metrics

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

## L1 Requirements: Clarification Loop & Error Handling

**Timeline:** 2 weeks | **Dev Time:** 10 days | **Scholar Time:** 2 days

**MVP Scope:**
- 2-turn clarification maximum (ask twice, then answer with what you have)
- Session expiry: 30 minutes
- In-memory session store (dict, no Redis yet)
- LangGraph for state machine (adopt GiovanniPasq's pattern)
- No conversation history beyond current clarification

**Defer to L2+:**
- Multi-session management
- Conversation history across queries
- Smart variable extraction (just ask the LLM "what's missing?")

### Requirement 23: Open-Source Library Research and Integration

**User Story:** As a developer, I want to study and leverage proven open-source RAG patterns, so that I don't reinvent the wheel and benefit from production-tested approaches.

**Layer:** L1-L4 (ongoing)

#### Acceptance Criteria

1. THE Development_Team SHALL study top 5 repositories before implementing each layer
2. THE Development_Team SHALL document reusable patterns from each studied repository
3. THE Development_Team SHALL integrate Ragas for evaluation (L3+)
4. THE Development_Team SHALL integrate DeepEval for CI/CD gates (L3+)
5. THE Development_Team SHALL adopt BM25+dense+RRF retrieval pattern from sougaaat/RAG-based-Legal-Assistant (L1)
6. THE Development_Team SHALL adopt clarification state machine pattern from GiovanniPasq/agentic-rag-for-dummies (L1)
7. THE Development_Team SHALL adopt production architecture patterns from lawglance/lawglance (L2-L3)

**Top 5 Repositories to Study:**

1. **NirDiamant/Controllable-RAG-Agent** (1.6k⭐, Apache-2.0)
   - **Use in**: L1 (clarification), L3 (evaluation), L4 (citation quality)
   - **Pattern**: Self-RAG verification, three-tier vector stores, RAGAS integration
   - **Action**: Clone first, study architecture

2. **sougaaat/RAG-based-Legal-Assistant** (8⭐)
   - **Use in**: L1 (advanced retrieval), L3 (evaluation)
   - **Pattern**: BM25+FAISS+RRF+multi-hop+multi-query for cross-standard queries
   - **Action**: Copy retrieval pattern verbatim

3. **lawglance/lawglance** (250⭐, Apache-2.0)
   - **Use in**: L2 (API structure), L3 (Redis caching, ops layout)
   - **Pattern**: LangChain+ChromaDB+Redis, legal corpus structure
   - **Action**: Lift API and ops patterns

4. **GiovanniPasq/agentic-rag-for-dummies**
   - **Use in**: L1 (clarification loop)
   - **Pattern**: LangGraph clarification with human-in-loop pause
   - **Action**: Drop-in pattern for clarification

5. **onyx-dot-app/onyx** (29.1k⭐, MIT)
   - **Use in**: L3+ (multi-tenant, audit, dashboards)
   - **Pattern**: Hybrid search, RBAC, agents framework
   - **Action**: Study backend/onyx/search/ and backend/onyx/agents/

**Key Findings:**
- No production-grade AAOIFI/Sharia-finance RAG exists (net-new domain = moat)
- Legal RAG is closest analog (lawglance, sougaaat)
- Islamic finance RAG projects are student/portfolio grade (study patterns only)
- Production RAG patterns are mature and reusable (Controllable-RAG-Agent, onyx)

**Integration Plan:**
- **L1**: BM25+RRF retrieval, LangGraph clarification, query expansion from hammadali1805/Quran-Hadith-Chatbot
- **L2**: FastAPI structure from Zlash65/rag-bot-fastapi, Redis cache from lawglance
- **L3**: Ragas evaluation, DeepEval CI gates, Qdrant migration, monitoring from onyx
- **L4**: Citation validation from RAGentA, hallucination prevention from Stanford Legal RAG paper

### Requirement 25: LLM-Driven Clarification Loop

**User Story:** As a user, I want the system to intelligently identify missing information using the LLM, so that I receive accurate compliance rulings without hand-coded state machines.

**Layer:** L1

#### Acceptance Criteria

1. THE Clarification_Engine SHALL use Gemini to analyze query completeness rather than hand-coded rules
2. WHEN a query is incomplete, THE Clarification_Engine SHALL generate 2-3 specific questions maximum per turn
3. THE Clarification_Engine SHALL return JSON with status "complete" or "clarifying" and questions array
4. THE Clarification_Engine SHALL NOT ask for information already provided in conversation history
5. THE Clarification_Engine SHALL mark query as complete if 80% confident it can answer
6. THE Clarification_Engine SHALL reformulate the query when marking as complete
7. THE Clarification_Engine SHALL maintain conversation history across clarification turns

**Implementation Notes:**
- Use dedicated clarification system prompt (see design.md)
- LLM returns structured JSON: `{"status": "complete|clarifying", "query": "...", "questions": [...]}`
- No state machine - LLM decides when to proceed
- Fallback: If LLM returns invalid JSON, assume complete

### Requirement 26: Session Management with Conversation History

**User Story:** As a user, I want my conversation context maintained across multiple turns, so that I don't repeat information.

**Layer:** L1

#### Acceptance Criteria

1. THE Session_Manager SHALL create unique session IDs (UUID) for new conversations
2. THE Session_Manager SHALL store conversation history (user inputs + assistant responses + timestamps)
3. THE Session_Manager SHALL maintain session state including clarification status and identified variables
4. THE Session_Manager SHALL expire sessions after 30 minutes of inactivity
5. THE Session_Manager SHALL use in-memory storage (Python dict) for L1-L2
6. THE Session_Manager SHALL support session resumption within expiration window
7. THE Session_Manager SHALL include last 3 conversation turns in LLM context

**Implementation Notes:**
- L1-L2: In-memory dict with threading locks
- L3+: Migrate to Redis with TTL-based expiration
- Session schema: `{session_id, created_at, last_activity, history[], status, identified_variables{}}`

### Requirement 26: Comprehensive Error Handling

**User Story:** As a developer, I want comprehensive error handling with custom exceptions, so that failures are graceful and debuggable.

**Layer:** L1

#### Acceptance Criteria

1. THE Chatbot_System SHALL define custom exception hierarchy (MushirError base class)
2. THE RAG_Pipeline SHALL catch and wrap ChromaDB connection failures as RetrievalError
3. THE RAG_Pipeline SHALL catch and wrap embedding generation failures as RetrievalError
4. THE Chatbot_System SHALL catch and wrap LLM API failures as LLMError
5. THE Chatbot_System SHALL retry LLM calls up to 3 times with exponential backoff
6. THE Chatbot_System SHALL log all errors with timestamp, component, error type, and stack trace
7. WHEN retrieval returns no chunks, THE Chatbot_System SHALL return user-friendly message

**Exception Hierarchy:**
```python
MushirError (base)
├── RetrievalError (vector search, embedding failures)
├── LLMError (API call failures)
├── ClarificationError (clarification loop failures)
└── RateLimitError (rate limit exceeded)
```

### Requirement 27: Structured Logging and Observability

**User Story:** As a system operator, I want structured JSON logging, so that I can monitor and debug the system effectively.

**Layer:** L1

#### Acceptance Criteria

1. THE Chatbot_System SHALL use Python logging module with JSON formatter
2. THE Chatbot_System SHALL log query events with: query, user_id, session_id, chunks_retrieved, latency_ms, timestamp
3. THE Chatbot_System SHALL log retrieval events with: query_embedding_time, search_time, chunks_found, avg_score
4. THE Chatbot_System SHALL log LLM events with: model, temperature, prompt_tokens, completion_tokens, latency_ms
5. THE Chatbot_System SHALL log error events with: error_type, error_message, stack_trace, component
6. THE Chatbot_System SHALL support configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
7. THE Chatbot_System SHALL write logs to both console and file (logs/mushir.log)

**Log Format:**
```json
{
  "event": "query",
  "query": "What does AAOIFI require...",
  "user_id": "user_123",
  "session_id": "550e8400-...",
  "chunks_retrieved": 5,
  "latency_ms": 2340,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Requirement 28: Enhanced Data Models for L1

**User Story:** As a developer, I want enhanced data models with provenance and confidence, so that rulings are traceable and trustworthy.

**Layer:** L1

#### Acceptance Criteria

1. THE AAOIFICitation model SHALL add document_version field for audit trail
2. THE AAOIFICitation model SHALL add chunk_id field for provenance
3. THE AAOIFICitation model SHALL add similarity_score field for confidence
4. THE AAOIFICitation model SHALL add quote field for direct quotations
5. THE Session model SHALL track created_at, last_activity, expires_at timestamps
6. THE Session model SHALL store conversation_history as list of {role, content, timestamp} dicts
7. THE ComplianceRuling model SHALL add ruling_id (UUID) and timestamp fields

**Updated AAOIFICitation:**
```python
@dataclass
class AAOIFICitation:
    standard_id: str
    section: Optional[str]
    page: Optional[int]
    source_file: str
    document_version: str       # NEW: "2023-v1.2"
    chunk_id: str              # NEW: Provenance
    similarity_score: float    # NEW: Confidence
    quote: Optional[str]       # NEW: Direct quote
```

### Requirement 29: Prompt Builder for Conversation History

**User Story:** As a developer, I want a PromptBuilder class that handles conversation history, so that multi-turn conversations work correctly.

**Layer:** L1

#### Acceptance Criteria

1. THE PromptBuilder SHALL accept system_prompt in constructor
2. THE PromptBuilder SHALL maintain conversation history as list of turns
3. THE PromptBuilder SHALL include last 3 turns in prompt (configurable)
4. THE PromptBuilder SHALL format retrieved chunks with citations and scores
5. THE PromptBuilder SHALL build final prompt with: system → history → chunks → current query
6. THE PromptBuilder SHALL handle empty history gracefully
7. THE PromptBuilder SHALL truncate history if token limit exceeded

**Interface:**
```python
class PromptBuilder:
    def __init__(self, system_prompt: str)
    def add_turn(self, role: str, content: str)
    def build(self, query: str, chunks: List[SemanticChunk]) -> str
    def clear_history()
```

### Requirement 30: Integration Tests for L1

**User Story:** As a QA engineer, I want comprehensive integration tests, so that L1 features work end-to-end.

**Layer:** L1

#### Acceptance Criteria

1. THE Test_Suite SHALL include end-to-end test (query → retrieval → LLM → ruling)
2. THE Test_Suite SHALL include clarification loop test (incomplete query → questions → complete query → ruling)
3. THE Test_Suite SHALL include conversation history test (multi-turn conversation with context)
4. THE Test_Suite SHALL include error handling tests (ChromaDB down, LLM timeout, invalid query)
5. THE Test_Suite SHALL include edge case tests (empty query, no results, malformed chunks)
6. THE Test_Suite SHALL mock LLM calls to avoid API costs in tests
7. THE Test_Suite SHALL achieve minimum 80% code coverage

**Test Cases:**
- `test_end_to_end_query()` - Full pipeline
- `test_clarification_loop()` - Multi-turn clarification
- `test_conversation_history()` - Context preservation
- `test_retrieval_with_no_results()` - Empty results
- `test_chromadb_connection_failure()` - DB failure
- `test_llm_timeout()` - API timeout

### Requirement 31: Retrieval Quality Baseline for L1

**User Story:** As a system architect, I want to establish retrieval quality baseline, so that L1 changes don't degrade performance.

**Layer:** L1

#### Acceptance Criteria

1. THE Test_Suite SHALL measure precision@5 and recall@5 on gold evaluation set
2. THE Test_Suite SHALL measure Mean Reciprocal Rank (MRR) on gold evaluation set
3. THE Test_Suite SHALL establish L0 baseline metrics before L1 changes
4. THE Test_Suite SHALL verify L1 maintains or improves retrieval quality vs L0
5. THE Test_Suite SHALL fail CI/CD if retrieval quality drops >5% from baseline
6. THE Test_Suite SHALL require minimum 10 gold evaluation cases for L1
7. THE Test_Suite SHALL report retrieval metrics in test output

**Metrics:**
- Precision@5: % of retrieved chunks that are relevant
- Recall@5: % of relevant chunks that were retrieved
- MRR: 1 / rank of first relevant chunk

---

## L2 Requirements: FastAPI + Streaming

### Requirement 32: FastAPI REST API

**User Story:** As a frontend developer, I want a REST API with clear endpoints, so that I can build web/mobile interfaces.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL use FastAPI framework with automatic OpenAPI documentation
2. THE API SHALL expose POST /api/v1/sessions endpoint to create sessions
3. THE API SHALL expose POST /api/v1/sessions/{session_id}/query endpoint for queries
4. THE API SHALL expose GET /api/v1/sessions/{session_id}/history endpoint for conversation history
5. THE API SHALL expose GET /api/v1/rulings/{ruling_id} endpoint for ruling details
6. THE API SHALL expose GET /api/v1/health endpoint for health checks
7. THE API SHALL return structured JSON responses with consistent error format

**Endpoints:**
- `POST /api/v1/sessions` → Create session
- `POST /api/v1/sessions/{id}/query` → Submit query
- `GET /api/v1/sessions/{id}/history` → Get history
- `GET /api/v1/rulings/{id}` → Get ruling
- `GET /api/v1/health` → Health check

### Requirement 33: Server-Sent Events (SSE) Streaming

**User Story:** As a user, I want to see the LLM response stream in real-time, so that I know the system is working and don't wait for full response.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL expose POST /api/v1/sessions/{session_id}/query/stream endpoint for streaming
2. THE API SHALL use Server-Sent Events (SSE) protocol for streaming
3. THE API SHALL stream events: thinking, retrieving, retrieved, generating, chunk, complete
4. THE API SHALL stream LLM response chunks as they are generated
5. THE API SHALL use Gemini streaming API (generate_content with stream=True)
6. THE API SHALL handle client disconnection gracefully
7. THE API SHALL include event types in SSE data field as JSON

**SSE Event Types:**
```
data: {"type": "thinking"}
data: {"type": "retrieving"}
data: {"type": "retrieved", "count": 5}
data: {"type": "generating"}
data: {"type": "chunk", "text": "According to..."}
data: {"type": "chunk", "text": "AAOIFI FAS-28..."}
data: {"type": "complete", "ruling_id": "..."}
```

### Requirement 34: API Authentication and Authorization

**User Story:** As a system operator, I want API authentication, so that only authorized users can access the system.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL use JWT (JSON Web Token) for authentication
2. THE API SHALL require Authorization: Bearer {token} header for protected endpoints
3. THE API SHALL validate JWT signature and expiration
4. THE API SHALL extract user_id from JWT claims
5. THE API SHALL return 401 Unauthorized for invalid/missing tokens
6. THE API SHALL return 403 Forbidden for insufficient permissions
7. THE API SHALL support API key authentication for service-to-service calls

**JWT Structure:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "user",
  "iat": 1705315800,
  "exp": 1705319400
}
```

### Requirement 35: Rate Limiting with Tiered Access

**User Story:** As a system operator, I want per-user rate limits with usage tiers, so that costs are controlled and system remains available.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL enforce per-user query rate limits based on user tier
2. THE API SHALL support three tiers: Free (10 queries/hour), Standard (100 queries/hour), Premium (1000 queries/hour)
3. THE API SHALL return HTTP 429 Too Many Requests when limit exceeded
4. THE API SHALL include rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
5. THE API SHALL use in-memory rate limit counters for L2
6. THE API SHALL reset rate limits hourly
7. THE API SHALL log all rate limit violations with user_id and timestamp

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705319400
```

### Requirement 36: API Error Handling and Responses

**User Story:** As a frontend developer, I want consistent error responses, so that I can handle errors gracefully in the UI.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL return structured error responses with code, message, details, request_id, timestamp
2. THE API SHALL use standard HTTP status codes (400, 401, 403, 404, 429, 500)
3. THE API SHALL return 400 Bad Request for invalid request payloads
4. THE API SHALL return 404 Not Found for non-existent sessions/rulings
5. THE API SHALL return 500 Internal Server Error for unexpected failures
6. THE API SHALL include request_id in all responses for tracing
7. THE API SHALL log all errors with request_id for debugging

**Error Response Format:**
```json
{
  "error": {
    "code": "session_not_found",
    "message": "Session ID does not exist",
    "details": {"session_id": "550e8400-..."},
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Requirement 37: CORS and Security Headers

**User Story:** As a frontend developer, I want CORS configured, so that I can call the API from web applications.

**Layer:** L2

#### Acceptance Criteria

1. THE API SHALL configure CORS to allow requests from specified origins
2. THE API SHALL support preflight OPTIONS requests
3. THE API SHALL include security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
4. THE API SHALL use HTTPS in production (TLS 1.3)
5. THE API SHALL validate Content-Type header (application/json)
6. THE API SHALL sanitize all user inputs to prevent injection attacks
7. THE API SHALL set appropriate Cache-Control headers

**Security Headers:**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

---

## L3 Requirements: Production Infrastructure

### Requirement 38: Migration to Qdrant Vector Database

**User Story:** As a system architect, I want to migrate from ChromaDB to Qdrant, so that the system scales to production workloads.

**Layer:** L3

#### Acceptance Criteria

1. THE Vector_Database SHALL migrate from ChromaDB embedded to Qdrant server
2. THE Vector_Database SHALL support distributed deployment with replication
3. THE Vector_Database SHALL maintain same embedding model (all-mpnet-base-v2, 768-dim)
4. THE Vector_Database SHALL support filtering by metadata (document_id, section, version)
5. THE Vector_Database SHALL achieve <100ms p95 latency for similarity search
6. THE Vector_Database SHALL support incremental updates without full re-indexing
7. THE Vector_Database SHALL provide backup and restore capabilities

**Migration Path:**
- L0-L2: ChromaDB embedded (good for <100K vectors)
- L3+: Qdrant server (scales to millions of vectors)
- Keep same embedding model and chunk strategy

### Requirement 39: Redis Session Store

**User Story:** As a system operator, I want Redis for session storage, so that sessions persist across API server restarts.

**Layer:** L3

#### Acceptance Criteria

1. THE Session_Manager SHALL migrate from in-memory dict to Redis
2. THE Session_Manager SHALL use Redis TTL for automatic session expiration
3. THE Session_Manager SHALL serialize session data as JSON
4. THE Session_Manager SHALL support session resumption across API server instances
5. THE Session_Manager SHALL handle Redis connection failures gracefully
6. THE Session_Manager SHALL use Redis connection pooling for performance
7. THE Session_Manager SHALL support Redis Sentinel for high availability

**Redis Schema:**
```
Key: session:{session_id}
Value: JSON serialized session data
TTL: 1800 seconds (30 minutes)
```

### Requirement 40: PostgreSQL Document and Audit Store

**User Story:** As a compliance officer, I want persistent storage for documents and audit logs, so that all rulings are traceable.

**Layer:** L3

#### Acceptance Criteria

1. THE Document_Store SHALL use PostgreSQL for AAOIFI documents and metadata
2. THE Document_Store SHALL store compliance rulings in audit log table
3. THE Document_Store SHALL store semantic chunks with references to documents
4. THE Document_Store SHALL support full-text search on document content
5. THE Document_Store SHALL maintain referential integrity with foreign keys
6. THE Document_Store SHALL support point-in-time recovery with WAL archiving
7. THE Document_Store SHALL encrypt sensitive data at rest (AES-256)

**Tables:**
- `aaoifi_documents` - AAOIFI standards with metadata
- `semantic_chunks` - Chunks with document references
- `compliance_rulings` - Audit log of all rulings
- `users` - User accounts and tier information
- `audit_logs` - System audit trail

### Requirement 41: User Management and Tiered Access

**User Story:** As a system operator, I want user accounts with tiered access, so that I can manage subscriptions and permissions.

**Layer:** L3

#### Acceptance Criteria

1. THE User_Management SHALL store user accounts in PostgreSQL
2. THE User_Management SHALL support three tiers: Free, Standard, Premium
3. THE User_Management SHALL track rate limit counters per user
4. THE User_Management SHALL support tier upgrades/downgrades
5. THE User_Management SHALL hash passwords with bcrypt (min 12 rounds)
6. THE User_Management SHALL support email verification
7. THE User_Management SHALL support password reset flow

**User Schema:**
```python
@dataclass
class User:
    user_id: str
    email: str
    password_hash: str
    tier: str  # "free" | "standard" | "premium"
    created_at: datetime
    rate_limit: int
    rate_limit_reset: datetime
```

### Requirement 42: Monitoring and Alerting

**User Story:** As a system operator, I want monitoring and alerting, so that I can detect and respond to issues proactively.

**Layer:** L3

#### Acceptance Criteria

1. THE Monitoring_System SHALL collect metrics: request_count, latency_p95, error_rate, active_sessions
2. THE Monitoring_System SHALL expose /metrics endpoint in Prometheus format
3. THE Monitoring_System SHALL alert when error_rate > 5% for 5 minutes
4. THE Monitoring_System SHALL alert when latency_p95 > 5 seconds for 5 minutes
5. THE Monitoring_System SHALL alert when Qdrant/Redis/PostgreSQL is down
6. THE Monitoring_System SHALL send alerts via email and Slack
7. THE Monitoring_System SHALL provide Grafana dashboards for visualization

**Key Metrics:**
- `mushir_requests_total` - Total requests by endpoint
- `mushir_request_duration_seconds` - Request latency histogram
- `mushir_errors_total` - Total errors by type
- `mushir_active_sessions` - Current active sessions
- `mushir_qdrant_query_duration_seconds` - Vector search latency

### Requirement 43: Horizontal Scaling and Load Balancing

**User Story:** As a system architect, I want horizontal scaling, so that the system handles increasing load.

**Layer:** L3

#### Acceptance Criteria

1. THE API SHALL support multiple FastAPI instances behind load balancer
2. THE API SHALL use Redis for shared session state across instances
3. THE API SHALL use PostgreSQL connection pooling (max 20 connections per instance)
4. THE API SHALL support graceful shutdown (finish in-flight requests)
5. THE API SHALL support health checks for load balancer routing
6. THE API SHALL distribute load evenly across instances
7. THE API SHALL support auto-scaling based on CPU/memory metrics

**Architecture:**
```
Load Balancer (nginx)
├── FastAPI Instance 1
├── FastAPI Instance 2
└── FastAPI Instance 3
    ↓
Redis (sessions)
Qdrant (vectors)
PostgreSQL (documents/audit)
```

---

## L4 Requirements: Advanced Features

### Requirement 44: Citation Quality Enhancement

**User Story:** As a compliance officer, I want high-quality citations with direct quotes and confidence scores, so that rulings are trustworthy.

**Layer:** L4

#### Acceptance Criteria

1. THE Compliance_Analyzer SHALL extract direct quotes from retrieved chunks
2. THE Compliance_Analyzer SHALL include quote in AAOIFICitation with character offsets
3. THE Compliance_Analyzer SHALL calculate confidence score based on similarity scores
4. THE Compliance_Analyzer SHALL rank citations by relevance
5. THE Compliance_Analyzer SHALL highlight quote in chunk text for display
6. THE Compliance_Analyzer SHALL validate quote exists in source chunk
7. THE Compliance_Analyzer SHALL include provenance chain (chunk_id → document_id → version)

**Enhanced Citation:**
```python
@dataclass
class AAOIFICitation:
    standard_id: str
    section: str
    quote: str                    # Direct quote
    quote_start: int             # Character offset
    quote_end: int               # Character offset
    confidence: float            # 0.0-1.0
    provenance: ProvenanceChain  # Full audit trail
```

### Requirement 45: Disclaimer and Legal Compliance

**User Story:** As a compliance officer, I want disclaimers and audit logs, so that the system meets regulatory requirements.

**Layer:** L4

#### Acceptance Criteria

1. THE Chatbot_System SHALL display disclaimer on first interaction: "This system provides guidance based on AAOIFI standards but does not replace qualified Islamic finance professionals"
2. THE Chatbot_System SHALL require user acknowledgment of disclaimer before proceeding
3. THE Chatbot_System SHALL log all compliance rulings with full audit trail
4. THE Chatbot_System SHALL include disclaimer in all API responses
5. THE Chatbot_System SHALL support data export for regulatory review
6. THE Chatbot_System SHALL support data deletion requests (GDPR compliance)
7. THE Chatbot_System SHALL maintain audit logs for minimum 7 years

**Audit Log Schema:**
```python
@dataclass
class AuditLog:
    log_id: str
    user_id: str
    session_id: str
    query: str
    ruling: ComplianceRuling
    timestamp: datetime
    latency_ms: float
    chunks_retrieved: int
    llm_model: str
    llm_tokens: int
```

### Requirement 46: AAOIFI Standard Versioning

**User Story:** As a system administrator, I want AAOIFI standard versioning, so that rulings reference specific standard versions.

**Layer:** L4

#### Acceptance Criteria

1. THE Document_Store SHALL store multiple versions of each AAOIFI standard
2. THE Document_Store SHALL tag each version with acquisition_date and version_string
3. THE Chatbot_System SHALL allow configuration to specify which version to use
4. THE Chatbot_System SHALL default to latest version unless specified
5. THE Chatbot_System SHALL include version in all citations
6. THE Chatbot_System SHALL support querying specific versions via API
7. THE Chatbot_System SHALL maintain changelog of standard updates

**Version Schema:**
```python
@dataclass
class AAOIFIDocument:
    document_id: str
    version: str              # "2023-v1.2"
    acquisition_date: datetime
    supersedes: Optional[str] # Previous version
    status: str              # "active" | "superseded"
```

### Requirement 47: Performance Optimization

**User Story:** As a system architect, I want performance optimizations, so that the system meets latency targets at scale.

**Layer:** L4

#### Acceptance Criteria

1. THE Chatbot_System SHALL cache frequently retrieved chunks in Redis (TTL 1 hour)
2. THE Chatbot_System SHALL cache LLM responses for identical queries (TTL 24 hours)
3. THE Chatbot_System SHALL use connection pooling for all database connections
4. THE Chatbot_System SHALL batch embedding generation for multiple queries
5. THE Chatbot_System SHALL achieve p95 latency <2 seconds for retrieval
6. THE Chatbot_System SHALL achieve p95 latency <5 seconds end-to-end
7. THE Chatbot_System SHALL support 1000 queries per minute in production

**Caching Strategy:**
- Chunk cache: Redis, key=`chunk:{chunk_id}`, TTL=1h
- Query cache: Redis, key=`query:{hash(query)}`, TTL=24h
- Embedding cache: Redis, key=`embed:{hash(text)}`, TTL=1h

### Requirement 48: Advanced Testing and Evaluation

**User Story:** As a QA engineer, I want advanced testing with Ragas and DeepEval, so that quality is continuously validated.

**Layer:** L4

#### Acceptance Criteria

1. THE Test_Suite SHALL integrate Ragas for RAG evaluation (faithfulness, answer_relevancy, context_precision)
2. THE Test_Suite SHALL integrate DeepEval for LLM evaluation (hallucination, bias, toxicity)
3. THE Test_Suite SHALL run nightly evaluation on gold test set (minimum 50 cases)
4. THE Test_Suite SHALL fail CI/CD if faithfulness score <0.8
5. THE Test_Suite SHALL fail CI/CD if hallucination score >0.1
6. THE Test_Suite SHALL generate evaluation reports with metrics trends
7. THE Test_Suite SHALL support A/B testing of prompt variations

**Evaluation Metrics:**
- Faithfulness: Answer grounded in retrieved chunks
- Answer Relevancy: Answer addresses the question
- Context Precision: Retrieved chunks are relevant
- Hallucination: LLM invents information not in chunks

### Requirement 7: Research and Benchmarking of Open-Source RAG Patterns

**User Story:** As a system architect, I want to study and integrate proven open-source RAG patterns and libraries, so that the system benefits from production-grade architectures and specialized retrieval techniques.

#### Acceptance Criteria

1. THE System_Architect SHALL study and benchmark the following open-source projects for architectural patterns:
   - **NirDiamant/Controllable-RAG-Agent**: For grounded, hallucination-resistant RAG and self-verification logic (L1/L3).
   - **sougaaat/RAG-based-Legal-Assistant**: For BM25 + Dense + RRF + Multi-hop retrieval strategies (L1).
   - **lawglance/lawglance**: For production-grade legal RAG layout and Redis caching (L2/L3).
   - **GiovanniPasq/agentic-rag-for-dummies**: For explicit LangGraph clarification state machines (L1).
   - **onyx-dot-app/onyx**: For hybrid search and enterprise RAG features (L3+).
2. THE RAG_Pipeline SHALL implement advanced retrieval patterns inspired by legal RAG benchmarks, specifically multi-query expansion and reciprocal rank fusion (RRF).
3. THE Evaluation_Framework SHALL integrate **Ragas** for faithfulness and relevance metrics and **DeepEval** for CI/CD regression testing.
4. THE Clarification_Engine SHALL implement a "Gatekeeper" pattern inspired by **FareedKhan-dev/agentic-rag** to refuse vague queries and demand clarification.
5. THE System_Architect SHALL review the **Stanford Legal RAG Hallucinations paper** and integrate its findings into the system's grounding and refusal prompts.

## Non-Functional Requirements

### Performance
- Response time: 95% of queries return initial response within 5 seconds
- Throughput: Support 1000 queries per minute in production mode
- Concurrent sessions: Support at least 100 concurrent users in production mode

### Scalability
- Horizontal scaling: System components can scale by adding instances
- Data growth: Vector database can scale to millions of semantic chunks
- User growth: Architecture supports growth from MVP to thousands of users

### Reliability
- Availability: 99.5% uptime during business hours
- Error recovery: Graceful degradation when components fail
- Data durability: No loss of AAOIFI standard data or audit logs

### Security
- Encryption: TLS 1.3 for data in transit, AES-256 for data at rest
- Authentication: Verify user identity before processing requests
- Authorization: Users can only access their own session data
- Input validation: Sanitize all inputs to prevent injection attacks

### Maintainability
- Code quality: Follow Python best practices, 80% test coverage
- Documentation: Comprehensive developer and user documentation
- Monitoring: Log all operations with appropriate severity levels
- Versioning: Track AAOIFI standard versions and system component versions

### Usability
- Natural language: Accept conversational financial operation descriptions
- Clear feedback: Provide understandable compliance rulings with citations
- Guidance: Offer inline help and examples
- Transparency: Explain reasoning and cite sources

### Compliance
- Auditability: Log all compliance rulings with traceability to AAOIFI standards
- Data privacy: Comply with data protection regulations
- Disclaimer: Clarify that system provides guidance, not professional advice
- Standard adherence: Ground all rulings strictly in AAOIFI standards

## Success Criteria

The Sharia Compliance Chatbot system will be considered successful when:

### L0 Success (COMPLETE ✅)
1. **RAG Loop Works**: Terminal query → retrieval → LLM → cited answer
2. **ChromaDB Populated**: Corpus ingested with 512-token chunks
3. **Tests Pass**: 2 smoke tests passing
4. **Citations Present**: Answers include `[FAS-XX]` format citations
5. **No Import Errors**: All modules load correctly

### L1 Success Criteria
1. **Clarification Loop**: LLM-driven clarification identifies missing info in 90% of incomplete queries
2. **Conversation History**: Multi-turn conversations maintain context correctly
3. **Error Handling**: All errors caught and logged with custom exceptions
4. **Retrieval Quality**: Maintains or improves L0 baseline (precision@5, recall@5, MRR)
5. **Test Coverage**: 80% code coverage with integration tests

### L2 Success Criteria
1. **API Functional**: All REST endpoints working with OpenAPI docs
2. **Streaming Works**: SSE streaming delivers LLM chunks in real-time
3. **Authentication**: JWT authentication enforces access control
4. **Rate Limiting**: Per-user rate limits enforced across tiers
5. **Performance**: p95 latency <5 seconds end-to-end

### L3 Success Criteria
1. **Qdrant Migration**: Vector search on Qdrant with <100ms p95 latency
2. **Redis Sessions**: Sessions persist across API server restarts
3. **PostgreSQL Audit**: All rulings logged with full provenance
4. **Horizontal Scaling**: System handles 1000 queries/minute across multiple instances
5. **Monitoring**: Prometheus metrics + Grafana dashboards + alerting

### L4 Success Criteria
1. **Citation Quality**: Direct quotes with confidence scores in 100% of rulings
2. **Evaluation**: Ragas faithfulness >0.8, DeepEval hallucination <0.1
3. **Performance**: p95 latency <2 seconds with caching
4. **Compliance**: Disclaimers, audit logs, GDPR compliance
5. **Versioning**: AAOIFI standard versions tracked and cited

### Overall Success
1. **Accuracy**: Compliance rulings grounded in AAOIFI standards with proper citations in 100% of cases
2. **User Satisfaction**: Users rate system as helpful and easy to use (target: 4.0/5.0 or higher)
3. **Coverage**: All 52 AAOIFI accounting standards indexed
4. **Reliability**: 99.5% uptime during business hours
5. **Progression**: Successful transition from L0 → L1 → L2 → L3 → L4
2. **Completeness**: The clarification loop successfully identifies and requests missing information in 90% of incomplete queries
3. **Performance**: 95% of queries receive initial response within 5 seconds
4. **User Satisfaction**: Users rate the system as helpful and easy to use (target: 4.0/5.0 or higher)
5. **Coverage**: The system has acquired and indexed all publicly available AAOIFI accounting standards from the source URL
6. **Reliability**: The system maintains 99.5% uptime during business hours
7. **Progression**: The system successfully transitions from MVP to production with all four phases implemented

## Assumptions and Constraints

### Assumptions
- AAOIFI standards are publicly accessible at the specified URL
- Users can describe financial operations in English
- Users have basic understanding of financial terminology
- Gemini 1.5 Pro API is available and reliable (validated in L0)
- 512-token chunks with 50-token overlap are optimal for legal text (validated in L0)
- all-mpnet-base-v2 embeddings provide sufficient retrieval quality (validated in L0)
- ChromaDB is sufficient for L0-L2, Qdrant needed for L3+ scale
- Users accept that system provides guidance, not professional advice

### Constraints
- **Budget**: Target $0.011/query with Gemini 1.5 Pro (1M context, cost-effective)
- **Latency**: p95 <5 seconds end-to-end (L2+), <2 seconds with caching (L4)
- **Scale**: Support 1000 queries/minute in production (L3+)
- **Language**: English-only for L0-L4 (Arabic support future enhancement)
- **Embedding Model**: all-mpnet-base-v2 (768-dim, English-only, runs locally)
- **Vector DB**: ChromaDB (L0-L2), Qdrant (L3+)
- **LLM**: Gemini 1.5 Pro (1M context window, temperature 0.1)
- **Chunk Strategy**: 512 tokens, 50 overlap (validated in L0, don't change unless retrieval quality tanks)

### Technical Constraints
- Python 3.9+ (3.11+ recommended for performance)
- sentence-transformers for embeddings (no API costs)
- FastAPI for API layer (L2+)
- Redis for sessions (L3+)
- PostgreSQL for documents/audit (L3+)
- Qdrant for vectors (L3+)

### L0 Validated Decisions (DO NOT CHANGE without strong justification)
1. **Gemini 1.5 Pro**: 1M context + cost-effective → KEEP
2. **all-mpnet-base-v2**: 768-dim, English-only, good quality → KEEP
3. **512 token chunks, 50 overlap**: Standard for legal text → KEEP
4. **Temperature 0.1**: Consistent, deterministic outputs → KEEP
5. **ChromaDB embedded**: Good for L0-L2 → Migrate to Qdrant at L3

### L1-L4 Evolution Path
- **L1**: Add clarification loop, error handling, conversation history (in-memory sessions)
- **L2**: Add FastAPI + SSE streaming, authentication, rate limiting (still in-memory)
- **L3**: Migrate to Qdrant + Redis + PostgreSQL, horizontal scaling, monitoring
- **L4**: Add citation quality, caching, advanced evaluation, compliance features reliable

### Constraints
- Must use Python for implementation
- Must ground all rulings in AAOIFI standards (no speculative advice)
- Must progress through four defined phases (research, acquisition, RAG, chatbot logic)
- Must start with lightweight MVP before scaling to production
- Must comply with data privacy regulations
- System provides guidance only, not professional Islamic finance advice

## Future Enhancements (Out of Scope for Initial Release)

- Multi-language support (Arabic, Urdu, Malay)
- Integration with other Islamic finance standard bodies (IFSB, ISRA)
- Mobile application interface
- Voice input and output
- Integration with financial software systems
- Expert review workflow for complex cases
- Machine learning model fine-tuning on Islamic finance corpus
- Comparative analysis across different Islamic finance schools of thought
