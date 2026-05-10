# Party Mode Session — RAG Chatbot Staging & Day-1 Plan

**Date:** 2026-05-07
**Project:** Mushir-Sharia-Bot
**Topic:** Stage RAG chatbot build after Gem prototype success. Simple → complex. Day-1 visible result. Review of `.kiro/specs/sharia-compliance-chatbot/` (requirements.md, design.md, tasks.md).

**Participants (BMAD agents, real subagents):**
- 📋 John — Product Manager
- 🏗️ Winston — System Architect
- 💻 Amelia — Senior Software Engineer
- 🧪 Murat — Master Test Architect
- 🔍 Research Agent — OSS prior-art scan

---

## Round 1 — Staging Proposal

### 📋 John (PM)

The job. Say it back to me: "Ahmed describes a financial operation, gets a Sharia ruling with AAOIFI citations he can trust." That's it. Everything else is scaffolding.

So why are we talking JWT before retrieval works? Why rate-limit tiers before we know the bot answers correctly? Premium tier of *what*? Stop.

Demo on Day 1. Or we're not shipping, we're decorating.

**L0 — Day 1. The Smoke Test.**
Notebook or CLI. 5 hand-picked AAOIFI Markdown chunks already on disk. sentence-transformers + Chroma in-memory. One prompt template: "answer + cite source + page." Ahmed types a Murabaha question, gets a cited answer. Done.
*Phase tasks: a thin slice of Phase 3 (chunking, embeddings, retrieval) — skip ingestion pipeline, skip eval harness.*

**L1 — Week 1. Minimal Web.**
FastAPI single endpoint `/ask`. Static HTML, one textarea, one response box with citations rendered as links. No auth. No sessions. No WebSocket. Persistent Chroma on disk. Ingest the full converted AAOIFI corpus from those merged scripts.
*Phase tasks: rest of Phase 3 + minimum Phase 4 (chat endpoint only).*

**L2 — Week 2-3. Trustworthy Answers.**
Now we earn the right to keep building. Eval set: 30-50 gold Q&A pairs. Retrieval@k metrics. Hallucination check — does every claim have a citation? Reranker if recall is weak. Conversation memory (in-process, not Redis).
*Phase tasks: Phase 1 research formalised retroactively + Phase 3 quality tasks. This is where retrieval-quality dashboard shows up — but as a notebook, not a Grafana stack.*

**L3 — Week 4. Make it Multi-User.**
Now auth matters. JWT, simple user table, conversation history persisted. Streaming responses (SSE before WebSocket — simpler, same UX). Basic logging.
*Phase tasks: Phase 4 remainder + Phase 2 ingestion automation if corpus changes.*

**L4 — Later. Ops.**
Rate tiers, encryption-at-rest, 100-concurrent load tests, observability dashboards. Only when paying users exist or compliance demands it.
*Phase tasks: Phase 5.*

Three pushbacks on the spec:
1. **Phase ordering is wrong.** Research phase as gate-zero stalls momentum. Ship L0, *then* document findings.
2. **WebSocket is premature.** SSE for streaming. Switch later if bidirectional needed.
3. **Three rate tiers before one paying user is fiction.** Cut from MVP.

Open question: gold eval set curator — Ahmed alone or Sharia scholar?

### 🏗️ Winston (Architect)

Specs are comprehensive — finished-state blueprint, not Day-1 build plan. Top-to-bottom = ship in month three with nothing in week one. Stage by what earns its keep.

**L0 — "Does retrieval actually work?" (Day 1-3)**
Jupyter/CLI. Read AAOIFI markdown from existing `scripts/` pipeline. RecursiveCharacterTextSplitter (512/50 per spec). Embed with `all-mpnet-base-v2`. Persist to Chroma on disk. One function: `ask(question)` → retrieve top-k → stuff into prompt → call OpenAI. No FastAPI, no auth, no Docker. *Trade-off:* zero production value, but proves grounding quality on AAOIFI corpus in 48 hours. Iterate chunk size, k, prompt without redeploying. Risk of skipping: build a stack around mediocre retrieval.

**L1 — Conversational shape (Day 4-7)**
Same notebook/CLI + multi-turn history + clarification state machine. Session = Python dict. *Trade-off:* throws away on restart, but discovers dialogue edge cases before committing to schema.

**L2 — One FastAPI endpoint (Week 2)**
`POST /chat`. No WebSocket, no JWT, no rate limiting. Deploy via existing Dockerfile. Postman or tiny HTML page hits it. *Trade-off:* anyone with URL drains OpenAI budget. Mitigate with shared bearer token in env if needed.

**L3 — Real users (Week 3-4)**
Heavy NFRs start paying rent. JWT auth, Postgres for users + sessions + system-prompt versioning, SSE streaming, TLS at proxy. *Defer-until-here:* auth, encryption-at-rest, session persistence, prompt-version table. Before L3, no users → these protect nothing.

**L4 — Scale and ops (Week 5+)**
Chroma → Qdrant once corpus or QPS justifies it (Chroma fine to a few hundred thousand chunks). Redis rate-limit tiers. Retrieval-quality dashboard. 100-concurrent load tests. 80% coverage gate. *Trade-off:* Qdrant migration is real work — index rebuild, client swap, ops surface. Don't pull forward without measured reason.

**Boring-tech bias throughout:** SQLite before Postgres if one box suffices at L3. SSE before WebSocket. Every upgrade needs a triggering metric, not a calendar date.

### 💻 Amelia (Dev)

ACK. Reviewed `.kiro/specs/sharia-compliance-chatbot/tasks.md`. Day-1 = working CLI on real AAOIFI corpus. No FastAPI, no auth, no Docker theater. Vertical slice.

**Day-1 deliverable (L0):**

Files to create:
- `src/models/schema.py` — `SemanticChunk`, `ComplianceRuling`, `AAOIFICitation` dataclasses (task 9.1)
- `scripts/ingest.py` — walks `data/aaoifi_md/`, `pdfplumber` fallback, `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)`, `sentence-transformers/all-mpnet-base-v2` (`normalize_embeddings=True`), persists to `./chroma_db` cosine collection (tasks 10.1, 10.2, 11.1, 11.2, 11.3)
- `src/rag/pipeline.py` — `RAGPipeline.retrieve(query, k=5, threshold=0.4)` returns `List[SemanticChunk]` with similarity scores (tasks 12.1, 12.2)
- `src/chatbot/cli.py` — argparse REPL: prompt → retrieve → augment system prompt with top-k chunks → OpenAI/Anthropic call → print ruling + AAOIFI citations (tasks 17.1, 17.2, 17.3, 17.4 minus state machine)
- `tests/test_rag_smoke.py` — 5 ground-truth pairs (e.g., `"interest-bearing loan"` → expects FAS-related chunk in top-5; `"murabaha cost disclosure"` → FAS 28; `"ijarah lease"` → FAS 32). Red→green→refactor (task 4.1)

**Day-1 commands:**
```bash
python scripts/ingest.py --src data/aaoifi_md/
python -m src.chatbot.cli "I want to take a $10k loan with 5% interest"
pytest tests/test_rag_smoke.py -v
```

Expected: ruling = non-compliant, cites Riba prohibition + relevant FAS section. 5/5 smoke pass before merge.

**Stage map (tasks.md IDs):**
- **L0 / Day 1:** 1 (env), 4.1 (test infra), 9.1–9.4 (schemas), 10.1–10.2 (ingest), 11.1–11.3 (chunk+embed+persist), 12.1–12.2 (retrieval), 17.1–17.4 (CLI surface)
- **L1:** 15 (prompt eng), 16.1–16.5 (LLM router + citation extractor), 19 conversation state machine inside CLI
- **L2:** 18.1 FastAPI `/chat`, 18.3 SSE stream, 18.4 health — **defer** 18.2/18.6
- **L3:** 18.2 JWT auth, 19.x input sanitization, 22 at-rest encryption
- **L4:** 23 monitoring, 24.6 load tests, 25 Redis cache, 26 ops dashboard

**Premature at L0 — block:** 18.6 WebSocket, 21 rate-limit tiers, 22 encryption, 24.6 load tests. Zero users, zero traffic, zero threat surface.

Acceptance for Day-1 done: smoke suite green + one live query returns cited ruling.

### 🧪 Murat (Test Architect)

Risk-first. Domain risks ranked:
- **R1 (HIGH):** Hallucinated citation — LLM cites FAS section that doesn't exist or doesn't say what claimed. Compliance liability.
- **R2 (HIGH):** Retrieval miss but answer still generated — Req 4.3 violation.
- **R3 (HIGH):** Citation→chunk mismatch — citation refers to retrieved chunk but chunk doesn't support ruling.
- **R4 (MED):** Prompt injection bypassing system prompt grounding.
- **R5 (MED):** Chunking loses context — provision split mid-clause.
- **R6 (LOW pre-launch):** Concurrency/load — only matters once users exist.
- **R7 (MED):** Standards version drift.

R6 testing Day 1 = risk-theater. Spec task 24.6 (100 concurrent) at L0 = misallocated.

**Spec's 80% line-coverage gate is wrong primary metric for RAG.** Coverage measures *that code ran*, not *that ruling was correct*. 95%-covered chatbot can still hallucinate FAS section beautifully. Behavioral evaluation dominates structural coverage. Coverage = secondary gate, not headline.

**Staged gates:**

**L0 (Day 1):** Golden eval set: 10–20 hand-curated Q → expected-FAS-section pairs. Two behavioral gates:
- `retrieval-recall@5 ≥ 0.8` (R2, R5)
- `citation-validation pass-rate = 100%` — every section ID LLM cites must appear in retrieved chunks (R1, R3). String-match check, dirt cheap, kills worst hallucination class.

No coverage gate yet.

**L1:** Clarification-loop state-machine tests + explicit refuse-without-context test for Req 4.3 (R2). LLM-as-judge with rubric (groundedness, citation-support, refusal-correctness) for sampled ruling quality — async, nightly not per-PR.

**L2:** API contract tests, golden-set promoted to CI blocking gate, regression set grows with every bug. 80% coverage as secondary signal.

**L3:** Prompt-injection corpus (R4). Authz tests once auth lands. Drift detection (R7): hash standards corpus, alert on FAS publication changes.

**L4:** Load tests (R6 — task 24.6 lives *here*), chaos (LLM provider down → graceful refusal not silent fallback), end-to-end SLO gates.

**Day 1 deliverable = golden set + citation validator running green.** Demo + gate + regression net in one artifact.

---

## Round 1 Decisions (Ahmed)

1. **Sharia scholar curates gold eval set.** Decoupled from build — Amelia scaffolds loader + format, scholar fills.
2. **SSE chosen over WebSocket.** Drop task 18.6. Task 18.3 = SSE.
3. **L0 corpus scope:** full converted AAOIFI corpus from existing `scripts/` (not 5-chunk demo).

---

## Round 2 — L0 Walkthrough & OSS Prior-Art Research

### 💻 Amelia — L0 Walkthrough

L0 = "smallest thing that proves the RAG loop works end-to-end on real AAOIFI text." No API, no streaming, no frontend. Terminal in → cited answer out. Once L0 green, every later layer (SSE, FastAPI, eval harness) plugs onto it.

**1. Pre-flight**

```bash
python -m venv .venv
.venv\Scripts\activate          # PowerShell: .venv\Scripts\Activate.ps1
pip install sentence-transformers chromadb langchain-text-splitters openai anthropic python-dotenv pyyaml pytest
pip freeze > requirements.txt
```

`.env` at repo root:
```
OPENAI_API_KEY=sk-...
# or ANTHROPIC_API_KEY=sk-ant-...
EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
CHROMA_DIR=./chroma_db
CORPUS_DIR=./data/aaoifi_md
```
Add `chroma_db/` and `.env` to `.gitignore`. Failure: forgetting venv activation → deps land in global site-packages.

**2. Verify corpus**

Confirm where `scripts/convert_aaoifi_to_markdown.py` writes. Likely `data/aaoifi_md/*.md`. Spot-check:
```bash
ls data/aaoifi_md | head
```
If empty → re-run converter first. L0 meaningless without real text.

**3. `src/models/schema.py`**

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AAOIFICitation:
    standard_id: str          # e.g. "FAS-28"
    section: Optional[str]    # e.g. "3.2"
    page: Optional[int]
    source_file: str

@dataclass
class SemanticChunk:
    chunk_id: str
    text: str
    citation: AAOIFICitation
    score: float = 0.0

@dataclass
class ComplianceRuling:
    question: str
    answer: str
    chunks: List[SemanticChunk] = field(default_factory=list)
    confidence: float = 0.0
```

**4. `scripts/ingest.py`** (skeleton)

```python
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb, hashlib, os

splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
model = SentenceTransformer(os.getenv("EMBED_MODEL"))
client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR"))
col = client.get_or_create_collection("aaoifi")

for md in Path(os.getenv("CORPUS_DIR")).rglob("*.md"):
    text = md.read_text(encoding="utf-8")
    for i, chunk in enumerate(splitter.split_text(text)):
        cid = hashlib.md5(f"{md.name}:{i}".encode()).hexdigest()
        emb = model.encode(chunk).tolist()
        col.upsert(ids=[cid], embeddings=[emb], documents=[chunk],
                   metadatas=[{"source_file": md.name, "chunk_idx": i}])
```

Success: `chroma_db/` directory exists with sqlite + parquet. Failure: silent zero-doc upsert when `CORPUS_DIR` wrong.

**5. `src/rag/pipeline.py`**

```python
class RAGPipeline:
    def __init__(self, persist_dir, model_name):
        self.model = SentenceTransformer(model_name)
        self.col = chromadb.PersistentClient(path=persist_dir).get_collection("aaoifi")

    def embed_query(self, q: str) -> list[float]:
        return self.model.encode(q).tolist()

    def retrieve(self, query: str, k: int = 5, threshold: float = 0.3) -> list[SemanticChunk]:
        res = self.col.query(query_embeddings=[self.embed_query(query)], n_results=k)
        # zip docs+metas+distances → filter by (1 - dist) >= threshold → SemanticChunk[]
```

**6. `src/chatbot/cli.py`**

```python
AAOIFI_ADHERENCE_SYSTEM_PROMPT = (
  "You are a Sharia compliance assistant. Answer ONLY from the provided AAOIFI "
  "excerpts. If the excerpts do not cover the question, reply: "
  "'Not addressed in retrieved AAOIFI standards.' Cite standard_id and section."
)
TEMPLATE = "Excerpts:\n{chunks}\n\nQuestion: {q}\n\nAnswer with citations."
```

argparse `--query`, retrieve top-5, format chunks `[{standard_id} §{section}] {text}`, call LLM, print `ComplianceRuling`.

**7. `tests/test_rag_smoke.py`**

```python
import pytest, yaml
from pathlib import Path
GOLD = Path("tests/fixtures/gold_eval.yaml")
gold = yaml.safe_load(GOLD.read_text()) if GOLD.exists() and GOLD.stat().st_size else []

def test_ingest_nonempty():
    from chromadb import PersistentClient
    assert PersistentClient(path="./chroma_db").get_collection("aaoifi").count() > 0

def test_retrieval_smoke():
    from src.rag.pipeline import RAGPipeline
    p = RAGPipeline("./chroma_db", "sentence-transformers/all-mpnet-base-v2")
    assert len(p.retrieve("murabaha cost disclosure", k=3)) > 0

@pytest.mark.skipif(not gold, reason="scholar gold set empty")
@pytest.mark.parametrize("case", gold)
def test_gold(case): ...
```

`tests/fixtures/gold_eval.yaml` = empty file. Scholar fills later. CI stays green.

**8. Run order**

```bash
pip install -r requirements.txt
python scripts/ingest.py
pytest -v
python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
```

**Definition of Done (L0):**
- [ ] `chroma_db/` populated from full converted AAOIFI corpus
- [ ] `pytest -v` passes (2 active + N skipped)
- [ ] CLI returns answer with at least one `[FAS-XX §Y]` citation
- [ ] No imports broken across `src/{models,rag,chatbot}/`
- [ ] `.env`, `chroma_db/`, `data/` gitignored

---

## OSS Prior-Art Research Report

### A. Islamic-finance / Sharia / Quran-Hadith RAG chatbots

**Honest finding: no production-grade open-source AAOIFI/Sharia-finance RAG project exists.** Net-new domain. Mushir = first.

- **[dannycahyo/fin-islam](https://github.com/dannycahyo/fin-islam)** — 1⭐, recent, MIT. TS/Hono/React + pgvector, Ollama Llama 3.1 8B, MCP. **Reusable:** architecture pattern — routing agent → knowledge (RAG) agent → calculation agent (Musharakah/Mudharabah) → Sharia-compliance agent. Closest mental model. **Skip:** TS, ~30 docs, no AAOIFI.
- **[oshoura/IslamAI](https://github.com/oshoura/IslamAI)** — 8⭐. Next.js + Pinecone + LangChain + GPT-3.5. Citation pattern reference. Stale.
- **[hammadali1805/Quran-Hadith-Chatbot](https://github.com/hammadali1805/Quran-Hadith-Chatbot)** — 6⭐. Streamlit + Chroma + MiniLM + Gemini. Direct stack mirror; query-expansion code worth reading.
- **[Shaheer66/Islam-GPT](https://github.com/Shaheer66/Islam-GPT)** — 2⭐, Apache-2.0. Tiny.
- **arxiv 2512.16644** + LangChain fiqh-muamalah paper (88.8% acc) — citation/eval methodology, no public repos.

### B. Legal/regulatory RAG (steal from here)

- **[lawglance/lawglance](https://github.com/lawglance/lawglance)** — 250⭐, Apache-2.0, active. LangChain + ChromaDB + Django + OpenAI + Streamlit + Redis. End-to-end production layout, Redis LLM cache, Indian-legal-codes corpus pattern → maps to FAS-1..FAS-N. **Best legal reference for Mushir.**
- **[sougaaat/RAG-based-Legal-Assistant](https://github.com/sougaaat/RAG-based-Legal-Assistant)** — 8⭐. BM25 + FAISS dense + multi-query + multi-hop fused via **Reciprocal Rank Fusion**, query-complexity classifier, RAGAS eval. **Single most valuable retrieval pattern for AAOIFI cross-standard queries.**
- **[kyouens/raven_public](https://github.com/kyouens/raven_public)** — LangChain + Qdrant. Refuse-without-context prompt scaffolding.
- **[krun02/Policy-Compliance-FAQ-Chatbot](https://github.com/krun02/Policy-Compliance-FAQ-Chatbot)** — LangChain + FAISS + Mistral/Ollama for SOC2/HIPAA/NIST. Structured policy-clause chunking.
- **Stanford Legal RAG Hallucinations paper** ([PDF](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf)) — required reading on Lexis+/Westlaw RAG hallucination rates.

### C. Production-grade RAG references

- **[onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx)** (formerly Danswer) — **29.1k⭐**, MIT, active. Hybrid search (BM25+embed+rerank), 50+ connectors, RBAC, agents framework. Study `backend/onyx/search/` and `backend/onyx/agents/`.
- **[NirDiamant/Controllable-RAG-Agent](https://github.com/NirDiamant/Controllable-RAG-Agent)** — 1.6k⭐, Apache-2.0. Deterministic LangGraph: question-anonymization, multi-step decomposition, Self-RAG verification, three-tier vector stores (chunks + summaries + quotes), RAGAS faithfulness/context-recall built-in. **Closest match to L0+L1.**
- **[GiovanniPasq/agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies)** — LangGraph with explicit Query Clarification stage (resolves references, splits multi-part Qs, pauses for human input). Direct fit for **L1 clarification**.
- **[FareedKhan-dev/agentic-rag](https://github.com/FareedKhan-dev/agentic-rag)** — "Gatekeeper" pattern that refuses vague Qs. Refuse-without-context reference.
- **[aryanmahawar205/conversational-rag-chatbot](https://github.com/aryanmahawar205/conversational-rag-chatbot)** + **[Zlash65/rag-bot-fastapi](https://github.com/Zlash65/rag-bot-fastapi)** — FastAPI + LangChain + Chroma + Streamlit. Exact stack-match boilerplate. Clone for L2 API skeleton.
- **[mazzasaverio/fastapi-langchain-rag](https://github.com/mazzasaverio/fastapi-langchain-rag)** — FastAPI + LCEL + PGVector + GCP + Terraform. L3+ infra/IaC pattern.
- **[faerber-lab/RAGentA](https://github.com/faerber-lab/RAGentA)** — SIGIR LiveRAG Multi-Agent attributed-QA with **Claim Judge** doing claim-by-claim grounding analysis + follow-ups for unanswered claims. Strong citation-validation reference.
- **[langchain-ai/rag-research-agent-template](https://github.com/langchain-ai/rag-research-agent-template)** — 304⭐, archived 2026-03-11. Canonical LangGraph routing graph (route → clarify → research → answer). Copy patterns, don't depend.
- **[weaviate/Verba](https://github.com/weaviate/Verba)** — 7.7k⭐, BSD-3, last commit 2025-07. Modular reader/chunker/embedder/generator interfaces. Skip — Weaviate-coupled + unmaintained.

### D. Tooling — eval, citation validation, refusal

- **[explodinggradients/ragas](https://github.com/explodinggradients/ragas)** — 13.8k⭐, Apache-2.0, v0.4.3 (Jan 2026). Faithfulness, answer-relevance, context-precision/recall. **Adopt as primary eval harness.**
- **[confident-ai/deepeval](https://github.com/confident-ai/deepeval)** — pytest-style, CI/CD-friendly. Use for golden-eval CI gates.
- **TruLens** — RAG triad (context relevance, groundedness, answer relevance). Dashboard option.
- **[YHPeter/Awesome-RAG-Evaluation](https://github.com/YHPeter/Awesome-RAG-Evaluation)** — survey index of metrics/datasets.
- **RQ-RAG** ([arxiv 2404.00610](https://arxiv.org/html/2404.00610v1)) + **Tree of Clarifications** — query rewriting/decomposition methods for L1 clarification design.
- No standalone citation-validator library. Roll using Ragas faithfulness or DeepEval `FaithfulnessMetric` + LLM-judge claim extractor. RAGentA's Claim Judge = closest open implementation.

### Top 5 to clone and study

1. **[NirDiamant/Controllable-RAG-Agent](https://github.com/NirDiamant/Controllable-RAG-Agent)** — closest end-to-end blueprint for grounded, hallucination-resistant RAG. Mirrors L0+L1+L3 eval. **Clone first.**
2. **[sougaaat/RAG-based-Legal-Assistant](https://github.com/sougaaat/RAG-based-Legal-Assistant)** — copy BM25+dense+RRF+multi-hop+multi-query verbatim into **L0 retrieval**.
3. **[lawglance/lawglance](https://github.com/lawglance/lawglance)** — best legal-domain analog with exact stack (LangChain+Chroma) + Redis cache. Lift **L2 API + L3 ops** layout.
4. **[GiovanniPasq/agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies)** — explicit LangGraph **L1 clarification** state machine with human-in-loop pause.
5. **[onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx)** — study at L3+ (multi-tenant, audit, eval dashboards).

Bonus deps: **Ragas** for nightly faithfulness golden eval, **DeepEval** for pytest CI gates blocking grounding regressions.

---

## Consolidated Decisions

| # | Decision | Owner | Status |
|---|----------|-------|--------|
| 1 | Stage build L0→L1→L2→L3→L4 | Ahmed | ✅ |
| 2 | L0 = CLI only, no FastAPI | Amelia | ✅ |
| 3 | Sharia scholar curates gold eval set | Scholar | Pending — needs brief |
| 4 | SSE over WebSocket; drop task 18.6 | — | ✅ |
| 5 | L0 corpus = full converted AAOIFI from `scripts/` | Amelia | ✅ |
| 6 | Defer auth/encryption/rate-tiers/load-tests until L3+ | — | ✅ |
| 7 | Adopt Ragas + DeepEval as eval stack | Murat | ✅ |
| 8 | Steal retrieval recipe from `sougaaat/RAG-based-Legal-Assistant` | Amelia | At L1+ |
| 9 | Steal clarification state machine from `agentic-rag-for-dummies` | Amelia | At L1 |
| 10 | 80% coverage NOT a Day-1 gate; behavioral eval is | Murat | ✅ |

## Stage Map (final)

| Level | Goal | Tech | Tasks (tasks.md) | Quality Gate |
|-------|------|------|------------------|--------------|
| **L0** | CLI returns cited ruling | Chroma+sentence-transformers+OpenAI/Anthropic | 1, 4.1, 9.1-9.4, 10.1-10.2, 11.1-11.3, 12.1-12.2, 17.1-17.4 | retrieval-recall@5≥0.8, citation-validation=100% |
| **L1** | Multi-turn + clarification state machine | + python-statemachine, in-mem session | 15, 16.1-16.5, 19 | + state-machine tests, refuse-without-context, LLM-judge nightly |
| **L2** | FastAPI `/chat` + SSE | + FastAPI, SSE | 18.1, 18.3, 18.4 | + API contract tests, golden-set CI blocker |
| **L3** | Multi-user | + JWT, Postgres, TLS, prompt-version table | 18.2, 19.x, 21, 22 | + injection corpus, authz, drift detection |
| **L4** | Production ops | + Qdrant, Redis, dashboards | 23, 24.6, 25, 26, 27 | + load tests, chaos, SLO gates |

## Open Items / Next Steps

1. **Scholar brief** — define gold-eval-set yaml schema, target count (10-20 for L0, grow to 50+ by L2), FAS coverage matrix
2. **Repo hygiene** — confirm `data/aaoifi_md/` location matches converter output; add `chroma_db/` to `.gitignore`
3. **Decide L0 LLM provider** — OpenAI vs Anthropic (existing Gem prototype experience may inform)
4. **Clone reference repos** — start with `NirDiamant/Controllable-RAG-Agent`
