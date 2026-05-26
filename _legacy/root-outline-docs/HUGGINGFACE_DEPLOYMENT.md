# Hugging Face Space Deployment Guide

## 🚀 Quick Deploy

### Step 1: Prepare Vector Database

```bash
# Ensure ChromaDB is populated
python scripts/ingest.py
```

### Step 2: Configure Space Secrets

Go to your Space settings: https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot/settings

Add these secrets:
- `GEMINI_API_KEY`: Your Google Gemini API key (get from https://makersuite.google.com/app/apikey)
- `HF_TOKEN`: Your Hugging Face token (optional, for private repos)

### Step 3: Deploy Files

```bash
# Run the deployment script
python scripts/deploy_to_hf.py
```

## 📦 What Gets Deployed

1. **Application Code** (`src/`)
2. **Vector Database** (`chroma_db_multilingual/`)
3. **Knowledge Base** (`gemini-gem-prototype/knowledge-base/`)
4. **Configuration Files**:
   - `Dockerfile`
   - `requirements.txt`
   - `README.md`

## 🔧 Manual Deployment

If the script fails, deploy manually:

```bash
# Clone your Space
git clone https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
cd mushir-sharia-bot

# Copy files
cp -r ../Mushir-Sharia-Bot/src .
cp -r ../Mushir-Sharia-Bot/chroma_db_multilingual .
cp -r ../Mushir-Sharia-Bot/gemini-gem-prototype .
cp ../Mushir-Sharia-Bot/Dockerfile .
cp ../Mushir-Sharia-Bot/requirements.txt .
cp ../Mushir-Sharia-Bot/README.md .

# Commit and push
git add .
git commit -m "Deploy Mushir Sharia Bot"
git push
```

## 🐛 Troubleshooting

### Space Shows "Refused to Connect"

**Cause**: Missing GEMINI_API_KEY or invalid API key

**Fix**:
1. Go to Space Settings → Repository Secrets
2. Add `GEMINI_API_KEY` with your valid key
3. Restart the Space

### Space Shows "Building" Forever

**Cause**: Docker build failure or missing dependencies

**Fix**:
1. Check Space logs for build errors
2. Verify `requirements.txt` has all dependencies
3. Ensure Dockerfile is valid

### 500 Internal Server Error

**Cause**: Missing vector database or corpus files

**Fix**:
1. Ensure `chroma_db_multilingual/` is uploaded
2. Ensure `gemini-gem-prototype/knowledge-base/` has markdown files
3. Check Space logs for specific errors

### ChromaDB Not Found

**Cause**: Vector database not included in deployment

**Fix**:
```bash
# Re-run ingestion locally
python scripts/ingest.py

# Re-deploy with vector database
python scripts/deploy_to_hf.py
```

## 📊 Monitoring

### Check Space Status

```bash
curl https://aelkodsh-mushir-sharia-bot.hf.space/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-11T...",
  "version": "1.0.0"
}
```

### Check Readiness

```bash
curl https://aelkodsh-mushir-sharia-bot.hf.space/ready
```

Expected response:
```json
{
  "status": "ready",
  "readiness_level": "dev",
  "infrastructure": {
    "vector_store": "chroma",
    "session_store": "SessionManager",
    ...
  }
}
```

## 🔐 Security Notes

- Never commit `.env` file to Space
- Use Space Secrets for API keys
- Set `APP_ENV=production` for production deployments
- Enable `REQUIRE_DISCLAIMER_ACK=true` for compliance

## 📝 Environment Variables

Configure these in Space Settings → Variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *required* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `VECTOR_DB_TYPE` | `chroma` | Vector database type |
| `CHROMA_DIR` | `/app/chroma_db_multilingual` | ChromaDB directory |
| `EMBED_MODEL` | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Embedding model |
| `CORPUS_DIR` | `/app/gemini-gem-prototype/knowledge-base` | Knowledge base directory |
| `APP_ENV` | `dev` | Environment (dev/production) |
| `LOG_LEVEL` | `INFO` | Logging level |

## 🎯 Post-Deployment Checklist

- [ ] Space is running (green status)
- [ ] `/health` endpoint returns 200
- [ ] `/ready` endpoint returns 200
- [ ] `/chat` page loads
- [ ] Test query returns valid response
- [ ] Citations are included in responses
- [ ] No errors in Space logs
