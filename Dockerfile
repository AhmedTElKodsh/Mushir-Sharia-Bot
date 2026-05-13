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
    OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free \
    API_HOST=0.0.0.0 \
    API_PORT=7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

EXPOSE 7860

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
