---
description: How to push code changes to GitHub and deploy
---

# GitHub Push & Deploy Workflow

## Project Context
- **Repo:** https://github.com/usshamsuddeen/behavioral-agentic-ai (PRIVATE)
- **Username:** usshamsuddeen
- **Classic PAT:** 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
- **Branch:** main
- **Python:** 3.13

## Push Changes to GitHub

// turbo-all

1. Refresh PATH so git is available:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

2. Stage all changes:
```powershell
cd D:\FYP\behavioral-agentic-ai; git add -A
```

3. Commit with a descriptive message:
```powershell
cd D:\FYP\behavioral-agentic-ai; git commit -m "your commit message here"
```

4. Push (embed token in URL for auth):
```powershell
cd D:\FYP\behavioral-agentic-ai; git remote set-url origin https://usshamsuddeen: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@github.com/usshamsuddeen/behavioral-agentic-ai.git; git push origin main
```

5. Clean token from remote URL after push:
```powershell
cd D:\FYP\behavioral-agentic-ai; git remote set-url origin https://github.com/usshamsuddeen/behavioral-agentic-ai.git
```

## API Keys Location

All keys live in `D:\FYP\behavioral-agentic-ai\backend\.env` (gitignored, never pushed):

| Key | Purpose | Where to Get |
|-----|---------|-------------|
| LLM_API_KEY | AI responses (fal.ai) | https://fal.ai/dashboard/keys |
| LLM_BASE_URL | LLM endpoint | Set per provider (see .env.example) |
| LLM_MODEL | AI model name | deepseek-r1 (default) |
| OPENROUTER_API_KEY | Fallback LLM | https://openrouter.ai/keys |
| GOOGLE_API_KEY | Gemini embeddings | https://aistudio.google.com/apikey |

## LLM Provider Switching (only change .env)

| Provider | LLM_BASE_URL | LLM_MODEL | LLM_API_KEY prefix |
|----------|-------------|-----------|-------------------|
| fal.ai | https://fal.ai/api/v1 | deepseek-r1 | fal-xxx |
| OpenRouter | https://openrouter.ai/api/v1 | meta-llama/llama-3.3-70b-instruct:free | sk-or-xxx |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini | sk-xxx |
| Claude | https://api.anthropic.com/v1 | claude-sonnet-4-20250514 | sk-ant-xxx |

## Project Structure

```
behavioral-agentic-ai/
├── backend/                 # FastAPI backend (Python 3.13)
│   ├── app/
│   │   ├── ai/              # LLM, RAG, embeddings, vector store
│   │   ├── api/             # REST endpoints (auth, widget, knowledge)
│   │   ├── models/          # SQLAlchemy DB models
│   │   ├── services/        # Sentiment, escalation, language
│   │   ├── nlp/             # BERT transformer sentiment
│   │   ├── knowledge/       # Document processing, indexing
│   │   └── main.py          # FastAPI entrypoint
│   ├── .env                 # API keys (NEVER push this)
│   ├── .env.example         # Template for env vars
│   ├── Dockerfile           # Production container
│   └── requirements.txt     # Pinned dependencies (80+)
├── frontend/                # HTML/CSS/JS dashboard + widget
├── docker-compose.yml       # One-command deployment
└── .gitignore               # Excludes .env, venv, databases
```

## Run Locally

```powershell
cd D:\FYP\behavioral-agentic-ai\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deploy on Hostinger VPS

```bash
ssh root@your-vps-ip
git clone https://usshamsuddeen:TOKEN@github.com/usshamsuddeen/behavioral-agentic-ai.git
cd behavioral-agentic-ai
nano backend/.env   # paste production keys
docker-compose up -d
docker exec -it behavioral-ai-backend python seed_data.py
```

## Database

- **Type:** SQLite (file-based, zero setup)
- **Location:** `backend/data/app.db` (auto-created on first start)
- **Default admin:** admin@behavioral-ai.com / admin123
- **Upgrade path:** Change DATABASE_URL in .env to PostgreSQL if needed
