# Technology Research - Sharia Compliance Chatbot

## Vector Database Comparison

### Chroma
- **Pros**: Lightweight, embedded, no server needed. Good for MVP.
- **Cons**: Not distributed, limited scaling.
- **MVP**: Yes. Production: migrate to Qdrant.

### FAISS (Facebook AI Similarity Search)
- **Pros**: Very fast, Facebook backing.
- **Cons**: No metadata filtering, pure vector search only.
- **MVP**: No (lacks metadata filtering for AAOIFI standards).

### Qdrant
- **Pros**: Full-featured, REST API, cloud-native, metadata filtering, distributed.
- **Cons**: Needs server/container, more complex setup.
- **MVP**: No. Production: yes.

**Decision**: Chroma for MVP, Qdrant for production.

## Embedding Model Options

### sentence-transformers/all-mpnet-base-v2
- **Dimension**: 768
- **Pros**: Good English semantic quality, reasonable size (420MB), strong performance on STS tasks.
- **Cons**: English-only (no Arabic support for future expansion).
- **Decision**: Historical L0 model only. Do not use for Arabic retrieval claims.

### sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- **Dimension**: 768
- **Pros**: Supports Arabic and English in the same vector space, preserves the existing 768-dimensional Chroma/Qdrant shape.
- **Cons**: Requires re-ingesting the corpus; cannot be mixed with an index produced by `all-mpnet-base-v2`.
- **Decision**: Default local/demo embedding model for bilingual AAOIFI retrieval.

### multilingual-e5-large
- **Dimension**: 1024
- **Pros**: Multilingual (Arabic support), strong performance.
- **Cons**: Larger (2.2GB), slower inference.
- **Decision**: Future expansion if Arabic standards needed.

**Decision**: Use `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` for the active bilingual demo gate. Keep `all-mpnet-base-v2` only as historical context for the English-only L0 index.

## Web Scraping Strategy

### Playwright (Selected)
- **Pros**: Modern, handles JS-rendered content, good for AAOIFI website.
- **Cons**: Browser binaries increase deployment size.
- **Decision**: Use Playwright for AAOIFI standards acquisition.

### Alternatives Considered
- requests + BeautifulSoup: Too simple for JS-heavy sites.
- Scrapy: Overkill for targeted AAOIFI scraping.

## LLM Provider Comparison

### OpenAI GPT-4
- **Pros**: Strong reasoning, widely used, good API.
- **Cons**: Cost, data privacy concerns.
- **Use case**: MVP option.

### Anthropic Claude 3 (Opus/Sonnet)
- **Pros**: Strong reasoning, larger context window, good for long AAOIFI standards.
- **Cons**: Cost.
- **Use case**: Alternative/primary for MVP.

**Decision**: Support both via LLMClient wrapper. Default to OpenAI GPT-4 for MVP.

## Technology Decision Matrix

| Component | MVP | Production |
|-----------|-----|------------|
| Vector DB | Chroma | Qdrant |
| Embedding | paraphrase-multilingual-mpnet-base-v2 | paraphrase-multilingual-mpnet-base-v2 or multilingual-e5-large |
| Web Scraping | Playwright | Playwright |
| LLM | OpenAI GPT-4 | OpenAI GPT-4 or Claude 3 |
| Document Store | SQLite | PostgreSQL |
| Session Store | In-memory dict | Redis |
| API Framework | FastAPI | FastAPI + Load Balancer |
