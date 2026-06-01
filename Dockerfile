FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

ENV VECTOR_DB_TYPE=chroma \
    CHROMA_DIR=/app/chroma_db_multilingual \
    EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
    REQUIRE_ARABIC_RETRIEVAL=true \
    REQUIRE_GOVERNED_SOURCE_METADATA=true \
    OPENROUTER_MODEL=openrouter/free \
    OPENROUTER_MAX_TOKENS=1024 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/ready || exit 1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}"]
