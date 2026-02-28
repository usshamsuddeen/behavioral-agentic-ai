# Behavioral Agentic AI — Backend

## Quick Start

### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Create .env in project root (see .env.example)
cp ../.env.example ../.env
# Set JWT_SECRET_KEY and LLM_API_KEY at minimum
```

### 4. Run Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. View API Docs
Open: http://localhost:8000/docs

## Architecture

```
app/
├── api/          # 14 API routers (auth, conversations, analytics, knowledge, admin, orders, widget, etc.)
├── ai/           # RAG pipeline (LLM, retrieval, vector store)
├── nlp/          # BERT transformer sentiment model
├── services/     # Business logic (sentiment, language, escalation, intent router, orders)
├── knowledge/    # Document processing + indexing pipeline
├── models/       # 12 SQLAlchemy models
├── middleware/    # JWT auth + rate limiting
├── main.py       # FastAPI entry point
└── database.py   # DB connection
```

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register user |
| POST | `/api/auth/login` | Login (JWT) |
| GET | `/api/conversations` | List conversations |
| POST | `/api/analyze/sentiment` | Analyze sentiment (BERT/VADER/Keywords) |
| POST | `/api/knowledge/upload` | Upload document or image |
| POST | `/api/knowledge/search` | Search knowledge base |
| GET | `/api/analytics/dashboard` | Dashboard metrics |
| GET | `/api/admin/clients` | List all clients (super_admin) |
| POST | `/api/orders/simulate` | Generate test orders |
| POST | `/api/widget/{key}/chat` | Widget chat endpoint |
