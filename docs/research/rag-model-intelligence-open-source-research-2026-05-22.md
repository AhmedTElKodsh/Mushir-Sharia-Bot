# Mushir RAG and Model Intelligence OSS Research Refresh

Generated: 2026-05-22
Scope: open-source libraries, GitHub repositories, and model/tooling options that can improve Mushir's source-governed AAOIFI RAG engine without weakening fail-closed behavior.

## Executive Summary

The safest path is not to replace Mushir with a larger RAG framework. The best path is to add measurable intelligence around the current `ApplicationService -> retrieval -> prompt -> LLM -> CitationValidator` contract.

Top recommendations:

1. Build a repeatable RAG evaluation harness before adopting any new library.
2. Spike hybrid retrieval with BM25 plus current dense retrieval, then compare against Qdrant hybrid search.
3. Test BGE-M3 plus BGE reranker against the current multilingual MPNet baseline.
4. Improve source ingestion with Docling first, PyMuPDF4LLM as a lightweight fallback, and Marker only after license review.
5. Add OpenTelemetry-style tracing with Phoenix/OpenInference or a lighter custom trace schema before broad observability platforms.
6. Use Instructor or Pydantic validation for scenario extraction and answer-schema enforcement, but keep `CitationValidator` as the authority gate.
7. Treat OPA and Catala as future rules-first evaluator candidates, not near-term RAG replacements.

The high-level rule is simple: every candidate must improve at least one measurable gate: expected-standard hit rate, source-family accuracy, citation support, refusal correctness, Arabic robustness, or traceability.

## Current Mushir Baseline

Repo evidence reviewed:

- `project-context.md` describes Mushir as a source-governed AAOIFI assistant, not a generic RAG bot.
- `src/chatbot/application_service.py` is already the central orchestration boundary.
- `src/rag/pipeline.py` already supports Chroma and optional Qdrant, multilingual embeddings, query expansion, thresholding, and domain reranking.
- `src/governance/concept_map.py` and `src/governance/router_seed.py` already hold the first governed concept and source-routing seeds.
- `.kiro/specs/sharia-compliance-chatbot/tasks.md` already requires correct-standard/source-family metrics, superseded-source traps, hybrid retrieval spikes, and comparison against a gold set.

That means the next research outcome should be an evidence-based upgrade program, not a new architecture from scratch.

## Methodology

Research used:

- BMAD party-mode agent perspectives: architecture, engineering, QA, and business analysis.
- Tavily CLI search across eight OSS categories.
- Tavily CLI crawl for Qdrant, Docling, and Ragas documentation.
- Exa fetch/search for key GitHub READMEs and model pages.
- GitHub CLI API metadata for repo health, stars, pushed dates, languages, licenses, and archive status.

Generated evidence artifacts:

- `docs/research/raw/2026-05-22/github-repo-metadata-2026-05-22.json`
- `docs/research/raw/2026-05-22/tavily-search-rag-eval.json`
- `docs/research/raw/2026-05-22/tavily-search-hybrid-rerank.json`
- `docs/research/raw/2026-05-22/tavily-search-arabic-nlp.json`
- `docs/research/raw/2026-05-22/tavily-search-ingestion.json`
- `docs/research/raw/2026-05-22/tavily-search-structured-outputs.json`
- `docs/research/raw/2026-05-22/tavily-search-observability.json`
- `docs/research/raw/2026-05-22/tavily-search-graph-rag.json`
- `docs/research/raw/2026-05-22/tavily-search-rules-engines.json`
- `docs/research/raw/2026-05-22/tavily-crawl-qdrant-docs.json`
- `docs/research/raw/2026-05-22/tavily-crawl-docling-docs.json`
- `docs/research/raw/2026-05-22/tavily-crawl-ragas-docs.json`
- `docs/research/raw/2026-05-22/tavily-crawl-deepeval-docs.json`
- `docs/research/deep_research_official_source_crawler_2026-05-22.md`

Limitations:

- Tavily Research `pro` endpoint was unavailable because the account hit the plan usage limit.
- Tavily MCP extraction was unavailable because its `TAVILY_API_KEY` environment variable is not set, though the CLI search/crawl path worked through OAuth.
- DeepEval docs crawl returned no pages, so DeepEval evidence comes from GitHub/Exa fetch and GitHub API metadata.

## Ranked Opportunity Map

| Rank | Opportunity | Best candidates | Why it matters for Mushir | Adoption level |
|---:|---|---|---|---|
| 1 | Evaluation harness | DeepEval, Ragas, RAGChecker, custom pytest metrics | No RAG or model upgrade is safe without gold-set comparison | Immediate |
| 2 | Hybrid retrieval | bm25s, Qdrant hybrid, Pyserini, Tantivy | AAOIFI terms need lexical exactness plus semantic matching | Immediate spike |
| 3 | Reranking | BGE reranker, FlagEmbedding, RAGatouille | Improves precision after high-recall retrieval | Immediate spike |
| 4 | Embedding upgrade | BGE-M3, sentence-transformers baselines, multilingual-e5 | Arabic-English and long clause retrieval need direct measurement | Spike |
| 5 | Document ingestion | Docling, PyMuPDF4LLM, Unstructured, Marker | Better section/table extraction improves citation anchors | Spike |
| 6 | Observability | Phoenix/OpenInference, TruLens, Langfuse | Debug retrieval, citations, and refusals per run | Spike after eval schema |
| 7 | Structured extraction | Instructor, Pydantic AI, Outlines, Guardrails | Helps scenario facts and answer contracts | Use narrowly |
| 8 | Arabic NLP | CAMeL Tools, spaCy Arabic pipeline options, AraBERT as older reference | Improves normalization, morphology, NER, transliteration handling | Spike |
| 9 | Graph RAG | LightRAG, Microsoft GraphRAG, NetworkX/RDFLib | Useful for source relationships and concepts, risky for answer path | Hold |
| 10 | Rules-first evaluator | OPA, Catala, OpenFisca, Drools | L6 needs deterministic rule traces, but only after source catalog maturity | Later |

## Candidate Matrix

| Category | Repo or resource | License | Current signal | Fit for Mushir | Safety risk | Recommendation |
|---|---|---:|---|---|---|---|
| Evaluation | [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | Apache-2.0 | Active; GitHub API showed 15k+ stars and push on 2026-05-21 | Strong for pytest-like LLM/RAG evals, faithfulness, contextual precision/recall, JSON correctness | LLM-as-judge must not become truth without domain review | Tier 1 eval harness candidate |
| Evaluation | [explodinggradients/ragas](https://github.com/explodinggradients/ragas) | Apache-2.0 | Active; 14k+ stars; RAG metrics and test generation | Strong for context precision/recall and testset generation | Generated tests need human review | Tier 1 eval metrics candidate |
| Evaluation | [amazon-science/RAGChecker](https://github.com/amazon-science/RAGChecker) | Apache-2.0 | Claim-level RAG diagnostics; less active than DeepEval | Excellent for diagnosing retriever/generator failure separately | Requires ground-truth answers and evaluator setup | Use as diagnostic spike |
| Retrieval | [xhluca/bm25s](https://github.com/xhluca/bm25s) | MIT | Active; fast Python BM25 | Low-complexity lexical layer for exact AAOIFI terms | Needs Arabic tokenization/normalization care | First hybrid retrieval spike |
| Retrieval | [qdrant/qdrant](https://github.com/qdrant/qdrant) | Apache-2.0 | Mature vector DB; supports dense, sparse, multivector, filtering, hybrid fusion | Strong production target for source-family filters and hybrid retrieval | New service operational cost | Production vector-store path, not local MVP replacement |
| Retrieval | [castorini/pyserini](https://github.com/castorini/pyserini) | Apache-2.0 | Strong IR research toolkit | Strong BM25/Lucene baseline | Java/Lucene complexity on Windows and deployment | Use only if bm25s is insufficient |
| Retrieval | [quickwit-oss/tantivy](https://github.com/quickwit-oss/tantivy) | MIT | Mature Rust search library | Useful if building a Rust-backed lexical layer | Higher integration cost | Hold |
| Reranking | [FlagOpen/FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding) | MIT | Active BGE toolkit; includes embeddings, rerankers, eval examples | Strongest OSS candidate for BGE-M3 and multilingual reranking experiments | Larger models affect latency and memory | Tier 1 retrieval experiment |
| Reranking | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | Model card | Multilingual, long input, dense/sparse/multivector support | Very strong candidate for Arabic-English and hybrid retrieval | Index dimension and pipeline changes require separate index | Spike against gold set |
| Reranking | [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Model card | Multilingual cross-encoder reranker | Likely useful after retrieving broad candidates | Runtime cost; must preserve citation chunk IDs | Spike rerank-only |
| Reranking | [AnswerDotAI/RAGatouille](https://github.com/AnswerDotAI/RAGatouille) | Apache-2.0 | ColBERT/RAGatouille late-interaction style retrieval | Useful for high-precision retrieval experiments | More moving parts than reranker-only | Research spike, not first production step |
| Ingestion | [docling-project/docling](https://github.com/docling-project/docling) | MIT | Very active; 60k+ stars; PDF/table/OCR/Markdown/JSON; RAG integrations | Best first candidate for AAOIFI source ingestion quality | Needs extraction QA and source-currentness guard | Tier 1 ingestion spike |
| Ingestion | [pymupdf/RAG](https://github.com/pymupdf/RAG) | AGPL-3.0 | Lightweight PDF-to-Markdown for LLM/RAG | Useful for quick extraction and page chunks | AGPL/commercial license review required | Use only if license acceptable |
| Ingestion | [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) | Apache-2.0 | Broad file partitioning ecosystem | Good for many file types and pipeline connectors | Heavy dependencies; OCR/system deps | Medium-priority ingestion spike |
| Ingestion | [VikParuchuri/marker](https://github.com/VikParuchuri/marker) | GPL-3.0 | Strong PDF/table/OCR extraction; commercial constraints | High accuracy candidate | GPL and model/commercial restrictions | Hold pending license review |
| Arabic NLP | [CAMeL-Lab/camel_tools](https://github.com/CAMeL-Lab/camel_tools) | MIT | Arabic NLP toolkit with morphology, disambiguation, NER, dialect tools | Useful for Arabic normalization and terminology expansion | Data packages and Windows caveats | Spike for preprocessing only |
| Arabic NLP | [aub-mind/arabert](https://github.com/aub-mind/arabert) | Not clear in metadata | Older Arabic transformer repo | Useful as reference, not core | Less active | Do not adopt first |
| Framework | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | Apache-2.0 | Mature Python RAG pipelines | Good component inspiration for pipelines/eval | Could duplicate current orchestration | Do not replace core; borrow patterns |
| Framework | [run-llama/llama_index](https://github.com/run-llama/llama_index) | MIT | Strong ingestion/index abstractions and integrations | Useful for experiments and evaluation integrations | Framework gravity can obscure provenance | Use components only |
| Framework | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | Strong state graph/orchestration | Good for future human-review workflows | Agentic loops can weaken traceability | Hold for workflow layer only |
| Framework | [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | MIT | Prompt/program optimization | Useful for prompt tuning after eval harness | Optimizes to metrics that may be incomplete | Later, eval-gated only |
| Graph RAG | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | MIT | Active graph RAG project with reranker/citation features | Interesting for concept/source relationship retrieval | LLM-extracted graph edges must not become authority | Research only |
| Graph RAG | [microsoft/graphrag](https://github.com/microsoft/graphrag) | MIT | Mature GraphRAG project | Useful for source relationship summaries | Summarization can blur exact clauses | Hold until source graph is governed |
| Structured output | [instructor-ai/instructor](https://github.com/instructor-ai/instructor) | MIT | Simple Pydantic structured outputs, retries, provider support | Strong for scenario extraction and internal classifiers | Model-produced facts still need validation | Tier 1 structured extraction candidate |
| Structured output | [outlines-dev/outlines](https://github.com/outlines-dev/outlines) | Apache-2.0 | Grammar/JSON-schema constrained generation | Useful for local model structured outputs | More useful with self-hosted models | Later |
| Structured output | [guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) | Apache-2.0 | Input/output guards and validators | Useful for schema and banned-pattern checks | Validators cannot replace citation validation | Use as secondary guardrail only |
| Observability | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | License review needed | Strong OpenTelemetry-style AI observability/evals | Excellent for local traces, retrieval spans, experiments | License and platform scope review | Preferred observability spike after trace schema |
| Observability | [truera/trulens](https://github.com/truera/trulens) | MIT | RAG triad, feedback functions, experiment tracking | Strong for RAG quality iteration | Additional evaluator complexity | Secondary observability/eval candidate |
| Observability | [langfuse/langfuse](https://github.com/langfuse/langfuse) | Mixed OSS/EE | Popular tracing and prompt management | Good for production tracing | License/deployment complexity | Hold unless team wants a full platform |
| Rules | [open-policy-agent/opa](https://github.com/open-policy-agent/opa) | Apache-2.0 | Mature CNCF policy engine | Best pragmatic rules-first candidate for route/fact gates | Rego skills needed; not domain-aware by itself | First L6 rules spike |
| Rules | [CatalaLang/catala](https://github.com/CatalaLang/catala) | Apache-2.0 | Literate legal DSL | Strong conceptual fit for reviewed Sharia/legal clauses | OCaml/tooling learning curve | High-assurance later candidate |
| Rules | [openfisca/openfisca-core](https://github.com/openfisca/openfisca-core) | AGPL-3.0 | Public-policy calculation engine | Useful modeling inspiration | AGPL and tax/benefit orientation | Research only |
| Rules | [apache/incubator-kie-drools](https://github.com/apache/incubator-kie-drools) | Apache-2.0 | Enterprise Java rule/DMN engine | Powerful but heavy | JVM/DMN complexity | Reject for near term |

## Best Near-Term Experiments

### Experiment 0: Evaluation Baseline

Goal: create a repeatable command that compares baseline and candidate RAG behavior without production edits.

Candidate tools:

- DeepEval for pytest-like tests and RAG metrics.
- Ragas for context precision/recall and production-aligned test generation.
- Custom pytest metrics for source-family accuracy, expected-standard hit rate, citation support, refusal correctness, and Arabic robustness.

Suggested files:

- `scripts/eval/rag_baseline.py`
- `tests/eval/`
- `docs/research/rag-eval-baseline-results.md`

Required metrics:

- `expected_standard_hit_at_k`
- `source_family_accuracy`
- `citation_support_rate`
- `unsupported_answer_rate`
- `refusal_correctness`
- `clarification_precision`
- `arabic_mixed_language_pass_rate`
- `latency_p50`, `latency_p95`

Pass gate:

- Baseline report exists before any candidate library is adopted.

### Experiment 1: BM25 plus Dense Hybrid Retrieval

Goal: add exact-term recall for AAOIFI standard numbers, Arabic terms, transliterations, and legal/accounting phrases.

Candidates:

- `bm25s` first because it is Python-native and low complexity.
- Qdrant hybrid search as the production target if the local experiment wins.
- Pyserini only if Lucene-level retrieval is needed.

Test cases:

- Standard-number lookup.
- Arabic-only terms.
- Mixed Arabic-English terms.
- Transliterations: murabaha/murabahah/morabaha, ijara/ijarah, wakala/wakalah.
- Wrong-standard traps.
- Superseded-source traps.

Pass gate:

- Better expected-standard hit rate at k without reducing citation precision or increasing unsupported answers.

### Experiment 2: BGE-M3 and BGE Reranker

Goal: test whether multilingual, long-context, dense/sparse/multivector embeddings improve retrieval over the current `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.

Candidates:

- `BAAI/bge-m3` for embeddings.
- `BAAI/bge-reranker-v2-m3` for reranking broad retrieval candidates.
- `FlagEmbedding` package for implementation.

Important constraints:

- Build a separate temporary index; do not overwrite `chroma_db_multilingual`.
- Keep chunk IDs and citation metadata stable.
- Do not tune thresholds on the test set only.

Pass gate:

- Improved Arabic and mixed-language retrieval plus equal or better citation support.

### Experiment 3: Document Extraction Quality

Goal: improve AAOIFI source ingestion, section paths, tables, page anchors, and parent/child chunk metadata.

Candidates:

- Docling first.
- PyMuPDF4LLM as quick local baseline if AGPL is acceptable.
- Unstructured for broad file coverage.
- Marker only after GPL/commercial review.

Pass gate:

- Extraction preserves source file, page, heading hierarchy, table text, and citation anchors better than the current Markdown corpus.

### Experiment 4: Retrieval Trace Observability

Goal: record enough data to debug why Mushir answered, clarified, or refused.

Candidates:

- Phoenix/OpenInference for local OTel-style traces.
- TruLens for RAG feedback functions and experiment comparison.
- Langfuse only if a full platform is desired.

Required trace fields:

- original query
- normalized query
- language
- candidate concepts
- source-family route
- retrieval filters
- dense/sparse/rerank scores
- selected chunk IDs
- citation validation result
- final status
- refusal or clarification reason

Pass gate:

- One local run can be inspected from user query to citation validation without exposing secrets or chain-of-thought.

### Experiment 5: Structured Scenario Extraction

Goal: improve L6 scenario extraction without letting the model decide authority.

Candidates:

- Instructor with Pydantic models from `src/models/commercial.py`.
- Existing Pydantic schemas first; Pydantic AI only if workflow complexity grows.
- Guardrails as secondary schema/banned-pattern validation.

Pass gate:

- Better extraction of party roles, asset flow, ownership sequence, price/markup, penalty beneficiary, and missing facts.
- No answer is generated solely from extracted facts without source evidence.

### Experiment 6: One-Domain Rules Spike

Goal: implement a narrow deterministic rule trace for one high-value domain after source coverage is verified.

Candidates:

- OPA/Rego for practical JSON fact evaluation.
- Catala later for high-assurance literate rule encoding.

First domain:

- Murabaha routing/fact sufficiency, or late-payment penalty fail-closed checks.

Pass gate:

- Rule result is explainable, testable, and subordinate to source availability and citation gates.

## What Not To Do

Do not:

- Replace `ApplicationService` with a framework-level chain.
- Put agentic web search in the user answer path.
- Treat GraphRAG-generated entities or summaries as authority.
- Let an LLM reranker or query expander silently broaden beyond AAOIFI-approved source families.
- Fine-tune the answer model before the retrieval and citation eval harness exists.
- Adopt GPL/AGPL libraries into production without explicit license review.
- Use synthetic evals as truth without human/domain review.
- Optimize for helpfulness if fail-closed behavior gets worse.

## Recommended Implementation Order

1. Add the evaluation harness and baseline report.
2. Run BM25 plus dense hybrid retrieval locally with unchanged production path.
3. Run BGE-M3 and BGE reranker experiments against the same gold set.
4. Run Docling extraction on a controlled AAOIFI source sample.
5. Add retrieval trace records and local observability.
6. Add structured scenario extraction for one L6 domain.
7. Add an OPA proof of concept only after the domain source map is verified.

## Acceptance Gates For Any Candidate

A candidate can move toward production only if:

- License is acceptable for the project.
- It is maintained and can run on the target Windows/local and hosted environments.
- It preserves source IDs, chunk IDs, citation anchors, and retrieved text.
- It does not bypass `CitationValidator`.
- It does not reduce refusal correctness.
- It improves a named metric over baseline.
- It has a rollback path.
- It is covered by deterministic fixtures.
- It keeps secrets out of logs, prompts, and traces.

## Source Index

Primary sources and current repo evidence used:

- GitHub API metadata: `docs/research/raw/2026-05-22/github-repo-metadata-2026-05-22.json`
- Tavily search/crawl artifacts listed in the Methodology section.
- [DeepEval GitHub](https://github.com/confident-ai/deepeval)
- [Ragas GitHub](https://github.com/explodinggradients/ragas)
- [RAGChecker GitHub](https://github.com/amazon-science/RAGChecker)
- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [BAAI/bge-m3 Hugging Face](https://huggingface.co/BAAI/bge-m3)
- [BAAI/bge-reranker-v2-m3 Hugging Face](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- [bm25s GitHub](https://github.com/xhluca/bm25s)
- [Qdrant GitHub](https://github.com/qdrant/qdrant)
- [Qdrant documentation](https://qdrant.tech/documentation/)
- [Docling GitHub](https://github.com/docling-project/docling)
- [Docling documentation](https://docling-project.github.io/docling/)
- [PyMuPDF4LLM GitHub](https://github.com/pymupdf/RAG)
- [Unstructured GitHub](https://github.com/Unstructured-IO/unstructured)
- [Marker GitHub](https://github.com/VikParuchuri/marker)
- [CAMeL Tools GitHub](https://github.com/CAMeL-Lab/camel_tools)
- [Instructor GitHub](https://github.com/instructor-ai/instructor)
- [Outlines GitHub](https://github.com/outlines-dev/outlines)
- [Guardrails GitHub](https://github.com/guardrails-ai/guardrails)
- [Phoenix GitHub](https://github.com/Arize-ai/phoenix)
- [TruLens GitHub](https://github.com/truera/trulens)
- [Langfuse GitHub](https://github.com/langfuse/langfuse)
- [OPA GitHub](https://github.com/open-policy-agent/opa)
- [Catala GitHub](https://github.com/CatalaLang/catala)
- [OpenFisca Core GitHub](https://github.com/openfisca/openfisca-core)
- [Drools GitHub](https://github.com/apache/incubator-kie-drools)
