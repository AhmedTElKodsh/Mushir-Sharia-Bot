# Mushir Deployment Notes

The current recommended online launch path is Hugging Face Spaces for a free beta, or a small Docker-based VPS/container host when always-on production behavior is needed.

For the Hugging Face path, see [huggingface-spaces.md](./huggingface-spaces.md).

## Build

```powershell
docker compose build sharia-bot
```

## Run Locally

```powershell
$env:OPENROUTER_API_KEY="..."
$env:OPENROUTER_MODEL="openrouter/free"
$env:OPENROUTER_MAX_TOKENS="1024"
docker compose up -d sharia-bot
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
```

`openrouter/free` is acceptable for a beta/demo smoke path, but do not use it for bulk live generation tests. Keep concurrency low, add backoff between smoke calls, and use retrieval-only or fake-LLM evaluation for larger scenario matrices.

## Hosting Shape

- Run the `sharia-bot` container behind HTTPS.
- Mount or bake in `chroma_db_multilingual`; the checked runtime expects `/app/chroma_db_multilingual`.
- Set `CORS_ORIGINS` to the public URL.
- Keep memory sessions/rate limits/cache for beta unless multi-instance deployment is required.
- Move to Redis/PostgreSQL/Qdrant only when deployment topology requires shared state.

## Launch Blockers

- No hosting provider or server credentials are configured in this repo.
- No GitHub Actions deploy workflow exists yet.
- Public launch still requires a chosen host, domain/TLS setup, and post-deploy smoke evidence.
