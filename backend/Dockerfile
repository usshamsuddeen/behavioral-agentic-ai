# ═══════════════════════════════════════════════════════════════════
# Behavioral Agentic AI — Backend Dockerfile
# FRD v3.0 Production-Ready Container
# Version: 3.1
# ═══════════════════════════════════════════════════════════════════

FROM python:3.13-slim AS base

LABEL maintainer="Behavioral Agentic AI Team"
LABEL version="3.1"
LABEL description="Sentiment-Aware Customer Support AI with RAG + Real-time WebSockets"

# ── Environment ──────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app

# ── System Dependencies ─────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python Dependencies (cached layer) ──────────────────────────
# Install torch CPU-only first (smaller image, no CUDA)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application Code ────────────────────────────────────────────
# Build context is project root (set in docker-compose.yml)
COPY backend/ /app/

# ── Frontend (served as static files by FastAPI) ─────────────────
COPY frontend/ /app/frontend/

# ── Data Directories ────────────────────────────────────────────
RUN mkdir -p /app/data /app/data/vector_store /app/data/chroma_db /app/logs

# ── Permissions ──────────────────────────────────────────────────
RUN chmod -R 755 /app

# ── Port ─────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health Check ─────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# ── Default Environment Variables ────────────────────────────────
ENV ENVIRONMENT="production"
ENV DATABASE_URL="sqlite:///./data/app.db"
ENV JWT_SECRET_KEY="change-this-in-production-minimum-32-characters"
ENV LLM_API_KEY=""
ENV LLM_BASE_URL="https://fal.ai/api/v1"
ENV LLM_MODEL="deepseek-r1"
ENV LLM_FALLBACK_MODEL="deepseek-v3"
ENV VECTOR_STORE_DIR="/app/data/vector_store"
ENV EMBEDDING_MODEL="all-MiniLM-L6-v2"
ENV LOG_LEVEL="INFO"
ENV CORS_ORIGINS="*"

# ── Run ──────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
