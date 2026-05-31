# Hugging Face Spaces Deployment

Hugging Face Spaces is the recommended free beta host for Mushir because CPU Basic currently provides enough memory for the multilingual embedding model and local Chroma index.

## Why This Host

- Free CPU Basic hardware: 2 vCPU, 16 GB RAM, 50 GB ephemeral disk.
- Supports Docker Spaces.
- Supports Space secrets and variables.
- Suitable for a demo or beta, not a regulated production deployment.

Official references:

- Hugging Face Spaces overview: https://huggingface.co/docs/hub/spaces-overview
- Docker Spaces: https://huggingface.co/docs/hub/spaces-sdks-docker
- Space secrets and variables: https://huggingface.co/docs/huggingface_hub/guides/manage-spaces

## Prerequisites

- A Hugging Face account.
- A write-capable Hugging Face access token in `HF_TOKEN`.
- An OpenRouter key in `OPENROUTER_API_KEY`.
- `chroma_db_multilingual/chroma.sqlite3` present locally.

Install the deployment client if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install huggingface_hub
```

## Deploy Policy

Keep Hugging Face Spaces as the public demo app host. A storage-limit or LFS failure while uploading `chroma_db_multilingual` does not, by itself, mean the host is wrong. It usually means the deploy bundled a large retrieval artifact with a small app/UI change.

Default rule:

- UI-only changes: use `--ui-only`.
- App/runtime changes that do not alter retrieval data: use `--skip-index`.
- Retrieval changes: use the full deploy path and verify `/ready` plus a real query smoke.

Long-term upgrade direction: externalize the retrieval payload into artifact or vector storage so routine app deploys stay small. Prefer a versioned object/artifact store, a managed vector database, or a deliberate Postgres/pgvector design. Do not use Supabase as a raw Chroma folder store unless the project explicitly accepts the boot-time download, integrity, and cold-start tradeoffs.

## Full Deploy

```powershell
$env:HF_TOKEN="hf_..."
$env:OPENROUTER_API_KEY="..."
.\.venv\Scripts\python.exe scripts\deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot
```

The script creates or updates a Docker Space, stores `OPENROUTER_API_KEY` as a Space secret, sets runtime variables, and uploads the repo plus `chroma_db_multilingual`.

## Lightweight Deploys

For a UI-only repair, do not re-upload the Chroma payload:

```powershell
.\.venv\Scripts\python.exe scripts\deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot --ui-only --commit-message "Fix chat UI layout"
```

For app/runtime changes that do not alter retrieval data, reuse the existing Space index:

```powershell
.\.venv\Scripts\python.exe scripts\deploy_huggingface_space.py --repo-id your-user/mushir-sharia-bot --skip-index --commit-message "Deploy app runtime update"
```

Use the full deploy path only when `chroma_db_multilingual` changes. That keeps routine UI/API deploys small while preserving `/ready` as the gate for full bot readiness.

## Post-Deploy Smoke

```powershell
curl.exe https://your-user-mushir-sharia-bot.hf.space/health
curl.exe https://your-user-mushir-sharia-bot.hf.space/ready
```

Then open:

```text
https://your-user-mushir-sharia-bot.hf.space/chat
```

Run one English question, one Arabic question, and one unanswerable question. Do not treat the Space as launched unless `/ready` is healthy and Arabic answers show correct text with citations or a controlled refusal.

## Limits

- Free Spaces can sleep after inactivity.
- Disk is not persistent across rebuilds; the index must be uploaded or rebuilt.
- Do not use the free Space for confidential production traffic.
