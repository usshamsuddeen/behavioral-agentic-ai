# 🤖 Behavioral Agentic AI

**Sentiment-Aware Customer Support Platform with BERT NLP, RAG Knowledge Base & Real-Time Escalation**

A production-grade SaaS platform that provides AI-powered customer support through an embeddable chat widget. The system analyzes customer sentiment in real time using a 3-tier NLP pipeline (BERT → VADER → Keywords), auto-escalates critical conversations, and uses Retrieval-Augmented Generation (RAG) to answer questions from your knowledge base — with inline image support.

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Key Features (V4)](#-key-features-v4)
- [Quick Start (Local Development)](#-quick-start-local-development)
- [Docker Deployment (Production)](#-docker-deployment-production)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Frontend Pages](#-frontend-pages)
- [Embeddable Widget](#-embeddable-widget)
- [Environment Variables](#-environment-variables)
- [FRD v4.0 Feature Coverage](#-frd-v40-feature-coverage)

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR CUSTOMERS                          │
│                    (visit your website)                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │  <script src="widget/embed.js">
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│               EMBEDDABLE CHAT WIDGET (JS)                      │
│  • Floating chat button on customer's website                  │
│  • Real-time messaging via API                                 │
│  • Inline image display from Knowledge Base                    │
│  • Themed to match client branding                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ /api/widget/{api_key}/chat
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python 3.13)              │
│  ┌──────────┐ ┌───────────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Auth/JWT │ │  3-Tier NLP   │ │   RAG    │ │Intent Router│  │
│  │ Engine   │ │ BERT→VADER→KW │ │ Pipeline │ │ (V4)        │  │
│  └──────────┘ └───────────────┘ └──────────┘ └─────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Escalate │ │ Analytics│ │  Admin   │ │  Order Gateway   │  │
│  │ Engine   │ │ & Reports│ │ Panel    │ │  (Zone 8 — V4)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  SQLite (dev)  │  NumPy Vector Store (RAG embeddings)          │
└─────────────────────────────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────┴───────────────────────────────────────────────┐
│               MANAGEMENT DASHBOARD (HTML/JS/CSS)               │
│  • Login / Signup / 5-Step Onboarding                          │
│  • Dashboard, Analytics, Conversations, Reports                │
│  • Knowledge Base (text, docs, images, FAQs)                   │
│  • Widget Manager, Admin Panel, Super Admin                    │
└─────────────────────────────────────────────────────────────────┘
```

**Two-Part System:**
1. **Management Dashboard** — Used by the business owner to monitor conversations, view analytics, manage settings, and train the AI knowledge base.
2. **Embeddable Widget** — A `<script>` tag your clients paste into their website. Their customers chat with the AI through this widget.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.13, FastAPI, Uvicorn |
| **Database** | SQLite (file-based, zero config) |
| **Vector Store** | Custom NumPy + JSON (cosine similarity, tenant-isolated) |
| **AI/NLP** | BERT Transformer (6 languages), VADER, TextBlob, LangDetect |
| **LLM** | Provider-agnostic (OpenRouter / OpenAI / Anthropic) |
| **Embeddings** | SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **Auth** | JWT (python-jose) + bcrypt |
| **Frontend** | Vanilla HTML/CSS/JS (no framework) |
| **Container** | Docker + Docker Compose |
| **Hosting** | Coolify / Any VPS |

---

## ✨ Key Features (V4)

### 🧠 3-Tier Sentiment Pipeline
- **Tier 1:** BERT Transformer (`nlptown/bert-base-multilingual-uncased-sentiment`) — supports en, de, fr, es, it, nl
- **Tier 2:** VADER — fast English fallback with jitter for natural score variation
- **Tier 3:** Weighted Keywords — 15 languages (en, de, fr, es, it, nl, ur, hi, ar, zh, pt, ru, ja, ko, tr) with intensity scoring

### 📚 RAG Knowledge Base
- Upload PDFs, DOCX, TXT, JSON, CSV, Markdown, and **images** (PNG, JPG, WEBP)
- Images are OCR'd for text + saved for **inline display in chat responses**
- 3-tier embedding fallback: Gemini API → SentenceTransformers → TF-IDF
- Top-5 cosine similarity retrieval → LLM response generation

### 🛒 Order Gateway (Zone 8)
- Built-in order simulator for testing without real e-commerce integration
- Order query service for customer order lookups in chat
- Intent router: automatically detects order-related vs knowledge-base queries

### 👑 Super Admin Panel
- System-wide analytics, client management (toggle active/inactive)
- Global conversations viewer, tenant order & product browsing
- System health monitoring, audit logs

### 🔌 Embeddable Widget
- Single `<script>` tag — works on any website
- Customizable colors, position, welcome messages
- Real-time chat with AI, inline image display
- Quick action buttons (Track Order, etc.)

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- **Python 3.10+** installed
- **Git** installed

### Step 1: Clone & Setup

```bash
git clone <your-repo-url>
cd behavioral-agentic-ai
```

### Step 2: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Create .env in project root
cp .env.example .env
# Edit .env — at minimum set:
#   JWT_SECRET_KEY=<random-64-chars>
#   LLM_API_KEY=<your-llm-api-key>
```

### Step 4: Start the Server

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend auto-creates the SQLite database on first run and serves the frontend at the same port.

### Step 5: Open in Browser

| Page | URL |
|---|---|
| **Landing Page** | http://localhost:8000/ |
| **Signup** | http://localhost:8000/signup |
| **Login** | http://localhost:8000/login |
| **Dashboard** | http://localhost:8000/dashboard |
| **API Docs** | http://localhost:8000/docs |

---

## 🐳 Docker Deployment (Production)

### Prerequisites

- **Docker** and **Docker Compose** installed

### Step 1: Configure Environment

Create a `.env` file in the project root:

```env
# Required
JWT_SECRET_KEY=a-random-string-at-least-64-characters-long

# LLM Provider
LLM_API_KEY=your-llm-provider-api-key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-3.5-sonnet
LLM_FALLBACK_MODEL=anthropic/claude-3-haiku

# Public URL
BACKEND_URL=https://your-domain.com
```

### Step 2: Build & Launch

```bash
docker compose up -d --build
```

This starts a single container:

| Container | Port | Purpose |
|---|---|---|
| `behavioral-ai-backend` | **8001→8000** | FastAPI (API + AI pipeline + frontend) |

### Step 3: Access

- **Dashboard**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### Useful Docker Commands

```bash
# View logs
docker compose logs -f backend

# Restart
docker compose restart backend

# Stop
docker compose down

# Full reset (delete data)
docker compose down -v
```

---

## 📁 Project Structure

```
behavioral-agentic-ai/
├── backend/                        # FastAPI Backend
│   ├── app/
│   │   ├── api/                    # API endpoints
│   │   │   ├── auth.py             #   Signup, Login, Refresh, Profile
│   │   │   ├── conversations.py    #   CRUD + Escalate + Resolve
│   │   │   ├── analytics.py        #   Dashboard metrics + trends
│   │   │   ├── knowledge.py        #   RAG document/image upload + search
│   │   │   ├── admin.py            #   Super Admin panel (Zone 4)
│   │   │   ├── orders_api.py       #   Order Gateway (Zone 8)
│   │   │   ├── products_api.py     #   Product listings (Zone 8)
│   │   │   ├── widget_api.py       #   Widget chat endpoints
│   │   │   ├── settings_api.py     #   Preferences + team
│   │   │   └── onboarding.py       #   5-step wizard
│   │   ├── ai/                     # AI pipeline
│   │   │   ├── llm.py              #   LLM integration (provider-agnostic)
│   │   │   ├── retrieval.py        #   RAG retrieval service
│   │   │   └── vector_store.py     #   NumPy vector store
│   │   ├── nlp/                    # NLP models
│   │   │   └── transformer_sentiment.py  # BERT sentiment model
│   │   ├── services/               # Business logic
│   │   │   ├── sentiment.py        #   3-tier sentiment pipeline
│   │   │   ├── language.py         #   Language detection (15 langs)
│   │   │   ├── escalation.py       #   Auto-escalation engine
│   │   │   ├── intent_router.py    #   Intent detection (order vs KB)
│   │   │   └── order_query.py      #   Order lookup service
│   │   ├── knowledge/              # Knowledge pipeline
│   │   │   ├── processor.py        #   Document chunking + OCR
│   │   │   ├── indexer.py          #   Embedding + indexing
│   │   │   └── manager.py          #   KB management facade
│   │   ├── models/                 # SQLAlchemy models (12 tables)
│   │   ├── middleware/             # JWT auth + rate limiting
│   │   ├── main.py                 # FastAPI app entry point
│   │   └── database.py             # DB connection
│   ├── data/                       # SQLite DB + vector store + uploads
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                       # Static Frontend
│   ├── pages/                      # 13 HTML pages
│   ├── js/                         # JavaScript modules
│   ├── css/                        # CSS stylesheets
│   ├── widget/                     # Embeddable widget (embed.js)
│   └── assets/                     # Images, icons
├── docker-compose.yml              # Production container
├── .env.example                    # Environment template
└── README.md
```

---

## 📡 API Documentation

Interactive API docs: **http://localhost:8000/docs** (Swagger UI).

### Key Endpoints

| Zone | Method | Endpoint | Description |
|---|---|---|---|
| **Auth** | POST | `/api/auth/signup` | Register new user |
| | POST | `/api/auth/login` | Login (returns JWT) |
| | POST | `/api/auth/refresh` | Refresh access token |
| | GET | `/api/auth/me` | Current user profile |
| **Conversations** | GET | `/api/conversations` | List conversations |
| | POST | `/api/conversations` | Create conversation |
| | PUT | `/api/conversations/{id}/escalate` | Escalate conversation |
| | PUT | `/api/conversations/{id}/resolve` | Resolve conversation |
| **Analytics** | GET | `/api/analytics/dashboard` | Dashboard metrics |
| | GET | `/api/analytics/sentiment-trends` | Sentiment over time |
| **Sentiment** | POST | `/api/analyze/sentiment` | Analyze text sentiment |
| | POST | `/api/analyze/language` | Detect language |
| **Knowledge** | POST | `/api/knowledge/upload` | Upload document/image |
| | POST | `/api/knowledge/text` | Upload raw text |
| | POST | `/api/knowledge/faqs` | Upload FAQs |
| | POST | `/api/knowledge/search` | Search knowledge base |
| | GET | `/api/knowledge/documents` | List documents |
| | GET | `/api/knowledge/stats` | KB statistics |
| **Orders** | GET | `/api/orders` | List orders |
| | POST | `/api/orders/simulate` | Simulate test orders |
| **Widget** | POST | `/api/widget/{key}/session` | Start chat session |
| | POST | `/api/widget/{key}/chat` | Send message |
| | GET | `/api/widget/{key}/history` | Chat history |
| **Admin** | GET | `/api/admin/clients` | List all clients |
| | GET | `/api/admin/analytics` | System analytics |
| | GET | `/api/admin/system-health` | Health check |
| | GET | `/api/admin/global-conversations` | All conversations |

### Authentication

All API calls (except signup/login and widget public endpoints) require a Bearer token:

```bash
curl -H "Authorization: Bearer <your_access_token>" \
     http://localhost:8000/api/settings
```

---

## 🖥 Frontend Pages

| Page | File | Purpose |
|---|---|---|
| **Landing** | `index.html` | Marketing landing page |
| **Sign Up** | `signup.html` | New user registration |
| **Login** | `login.html` | User authentication |
| **Onboarding** | `onboarding.html` | 5-step setup wizard |
| **Dashboard** | `dashboard.html` | Overview metrics & charts |
| **Analytics** | `analytics.html` | Deep-dive sentiment analytics |
| **Conversations** | `chat.html` | Live chat management |
| **Escalations** | `escalations.html` | Escalated conversations |
| **Reports** | `reports.html` | Generate & export CSV reports |
| **Settings** | `settings.html` | Preferences, team, API keys |
| **Knowledge Base** | `knowledge-base.html` | Upload docs, images, FAQs |
| **Widget Mgmt** | `widget-management.html` | Configure embed widget |
| **Admin Panel** | `admin.html` | Super admin (restricted) |

---

## 🔌 Embeddable Widget

The widget is the customer-facing chat interface. After setup, paste a **single `<script>` tag** into any website:

### Embed Code

```html
<!-- Behavioral Agentic AI — Chat Widget -->
<script
  src="https://your-server.com/widget/embed.js"
  data-api-key="YOUR_WIDGET_API_KEY"
  data-theme-color="#6366f1"
  data-position="bottom-right"
  async>
</script>
```

### Widget Features
- 💬 Real-time AI chat powered by RAG
- 📸 Inline image display from Knowledge Base
- 📦 Quick action buttons (Track Order, etc.)
- 🎨 Customizable theme colors and positioning
- 🌐 Multilingual support (15 languages)

---

## ⚙ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | *(must set)* | JWT signing secret (min 32 chars) |
| `LLM_API_KEY` | *(must set for AI)* | API key for LLM provider |
| `LLM_BASE_URL` | *(must set)* | LLM API endpoint (e.g. `https://openrouter.ai/api/v1`) |
| `LLM_MODEL` | *(must set)* | Primary LLM model (e.g. `anthropic/claude-3.5-sonnet`) |
| `LLM_FALLBACK_MODEL` | *(optional)* | Fallback LLM model (e.g. `anthropic/claude-3-haiku`) |
| `DATABASE_URL` | `sqlite:///./data/app.db` | Database connection string |
| `VECTOR_STORE_DIR` | `data/vector_store` | Vector embeddings storage |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence embedding model |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `BACKEND_URL` | *(optional)* | Public URL for widget embed code |

---

## ✅ FRD v4.0 Feature Coverage

| Zone | Feature | Status |
|---|---|---|
| **Zone 1** | JWT Auth (signup, login, refresh, logout) | ✅ |
| **Zone 2** | 5-step Onboarding Wizard | ✅ |
| **Zone 3** | Dashboard — Metrics, Analytics, Conversations, Reports, Settings | ✅ |
| **Zone 4** | Super Admin — System analytics, client management, audit logs | ✅ |
| **Zone 5** | Knowledge Base — Upload (docs, images, FAQs), search, inline images | ✅ |
| **Zone 6** | Embeddable Widget — Config, toggle, embed, inline images | ✅ |
| **Zone 7** | Security — JWT, rate limiting (60/120/200 tiers), tenant isolation | ✅ |
| **Zone 8** | Order Gateway — Simulator, order query, intent routing | ✅ |

### V4.1 Enhancements
- ✅ BERT Transformer sentiment (6 European languages)
- ✅ Granular sentiment scoring (weighted keywords, jitter, 11 labels)
- ✅ Inline image display in widget chat
- ✅ Refined system prompt with de-escalation
- ✅ 15-language support (extended from 6)

---

## 📝 License

This project is developed as a Final Year Project (FYP). All dependencies are free and open source.
