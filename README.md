# 🤖 Behavioral Agentic AI

**Sentiment-Aware Customer Support Platform with Real-Time Escalation & RAG Knowledge Base**

A production-grade SaaS platform that provides AI-powered customer support through an embeddable chat widget. The system analyzes customer sentiment in real time, auto-escalates critical conversations, and uses Retrieval-Augmented Generation (RAG) to answer questions from your knowledge base.

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Quick Start (Local Development)](#-quick-start-local-development)
- [Docker Deployment (Production)](#-docker-deployment-production)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Frontend Pages Guide](#-frontend-pages-guide)
- [Client-Side Widget (What Goes to Your Customer)](#-client-side-widget-what-goes-to-your-customer)
- [Testing Guide](#-testing-guide)
- [Environment Variables](#-environment-variables)
- [FRD v3.0 Feature Coverage](#-frd-v30-feature-coverage)

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
│  • Themed to match client branding                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ /api/widget/{api_key}/chat
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐      │
│  │ Auth/JWT │ │ Sentiment│ │   RAG    │ │ Rate Limiter │      │
│  │ Engine   │ │ Pipeline │ │ Pipeline │ │ (FR-7.2.5)   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │ Escalate │ │ Analytics│ │  Admin   │                       │
│  │ Engine   │ │ & Reports│ │ Panel API│                       │
│  └──────────┘ └──────────┘ └──────────┘                       │
├─────────────────────────────────────────────────────────────────┤
│  SQLite (dev) / PostgreSQL (prod)  │  ChromaDB (vectors)       │
└─────────────────────────────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────┴───────────────────────────────────────────────┐
│               MANAGEMENT DASHBOARD (HTML/JS/CSS)               │
│  • Login / Signup / Onboarding                                 │
│  • Dashboard, Analytics, Conversations                         │
│  • Reports (CSV Export), Settings, Knowledge Base              │
│  • Widget Manager, Admin Panel (super_admin only)              │
└─────────────────────────────────────────────────────────────────┘
```

**Two-Part System:**
1. **Management Dashboard** — Used by the business owner (you) to monitor conversations, view analytics, manage settings, and train the AI knowledge base.
2. **Embeddable Widget** — A `<script>` tag your clients paste into their website. Their customers chat with the AI through this widget.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Database** | SQLite (dev) / PostgreSQL 15 (prod) |
| **Vector DB** | ChromaDB (RAG knowledge storage) |
| **Cache** | Redis 7 (sessions, rate limiting) |
| **AI/NLP** | VADER Sentiment, LangDetect, TextBlob |
| **LLM** | OpenRouter API (Llama 3.3 70B) |
| **Auth** | JWT (python-jose) + bcrypt |
| **Frontend** | Vanilla HTML/CSS/JS (no framework) |
| **Proxy** | Nginx (production reverse proxy) |
| **Container** | Docker + Docker Compose |

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
# From project root
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY to a random string
```

### Step 4: Start the Backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend auto-creates the SQLite database on first run.

### Step 5: Start the Frontend

Open a **second terminal**:

```bash
cd frontend
python -m http.server 5500
```

### Step 6: Open in Browser

| Page | URL |
|---|---|
| **Signup** | http://localhost:5500/pages/signup.html |
| **Login** | http://localhost:5500/pages/login.html |
| **Dashboard** | http://localhost:5500/pages/dashboard.html |
| **API Docs** | http://localhost:8000/docs |

### Quick Test

```bash
# Signup
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"Demo123!","full_name":"Demo User","business_name":"Demo Corp"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"Demo123!"}'
```

---

## 🐳 Docker Deployment (Production)

### Prerequisites

- **Docker** and **Docker Compose** installed

### Step 1: Configure

```bash
cp .env.example .env
```

Edit `.env` and set **production values**:

```env
POSTGRES_PASSWORD=a-strong-random-password
JWT_SECRET_KEY=a-random-string-at-least-32-characters-long
SECRET_KEY=another-random-secret-key
OPENROUTER_API_KEY=your-openrouter-key    # optional, for AI chat
```

### Step 2: Build & Launch

```bash
docker compose up -d --build
```

This starts 4 containers:
| Container | Port | Purpose |
|---|---|---|
| `behavioral-ai-frontend` | **80** | Nginx (serves frontend + proxies API) |
| `behavioral-ai-backend` | 8000 | FastAPI (API + AI pipeline) |
| `behavioral-ai-postgres` | 5432 | PostgreSQL database |
| `behavioral-ai-redis` | 6379 | Redis (cache, sessions) |

### Step 3: Access

- **Dashboard**: http://localhost (port 80)
- **API Docs**: http://localhost/api/docs  *(proxied through Nginx)*

### Useful Docker Commands

```bash
# View logs
docker compose logs -f backend

# Restart backend only
docker compose restart backend

# Stop everything
docker compose down

# Full reset (delete data volumes)
docker compose down -v
```

---

## 📁 Project Structure

```
behavioral-agentic-ai/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   │   ├── auth.py         #   Signup, Login, Refresh, Profile
│   │   │   ├── conversations.py#   CRUD + Escalate + Resolve
│   │   │   ├── analytics.py    #   Dashboard metrics + trends
│   │   │   ├── settings_api.py #   User preferences + team
│   │   │   ├── knowledge.py    #   RAG document upload + search
│   │   │   ├── admin.py        #   Super Admin panel (FR-4)
│   │   │   ├── widget_api.py   #   Widget endpoints
│   │   │   └── onboarding_api.py
│   │   ├── middleware/
│   │   │   ├── jwt.py          #   JWT auth + token management
│   │   │   └── rate_limit.py   #   Rate limiting (FR-7.2.5)
│   │   ├── models/             #   SQLAlchemy data models
│   │   ├── ai/                 #   AI pipeline (NLP + RAG)
│   │   ├── main.py             #   FastAPI app entry point
│   │   └── config.py           #   App configuration
│   ├── data/                   #   SQLite DB + vector store
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Static Frontend
│   ├── pages/                  #   12 HTML pages
│   ├── js/                     #   11 JavaScript modules
│   ├── css/                    #   12 CSS stylesheets
│   └── assets/                 #   Images, icons
├── docker-compose.yml          # Multi-container orchestration
├── nginx.conf                  # Reverse proxy config
├── .env.example                # Environment template
├── START_SYSTEM.bat            # Windows one-click launcher
└── README.md                   # ← You are here
```

---

## 📡 API Documentation

Interactive API docs are available at **http://localhost:8000/docs** (Swagger UI).

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
| | GET | `/api/analytics/escalation-triggers` | Top escalation reasons |
| **Sentiment** | POST | `/api/analyze/sentiment` | Analyze text sentiment |
| | POST | `/api/analyze/language` | Detect language |
| **Knowledge** | POST | `/api/knowledge/text` | Upload text to KB |
| | POST | `/api/knowledge/upload` | Upload document (PDF/DOCX) |
| | POST | `/api/knowledge/search` | Search knowledge base |
| **Settings** | GET | `/api/settings` | Get all settings |
| | PUT | `/api/settings/preferences` | Update AI preferences |
| | POST | `/api/settings/regenerate-key` | Regenerate API key |
| **Widget** | GET | `/api/widget/config` | Widget configuration |
| | PUT | `/api/widget/config` | Update widget config |
| | GET | `/api/widget/embed-code` | Get embed snippet |
| **Admin** | GET | `/api/admin/clients` | List all clients *(super_admin)* |
| | GET | `/api/admin/analytics` | System analytics *(super_admin)* |
| | GET | `/api/admin/logs` | Audit logs *(super_admin)* |

### Authentication

All API calls (except signup/login and widget public endpoints) require a Bearer token:

```bash
curl -H "Authorization: Bearer <your_access_token>" \
     http://localhost:8000/api/settings
```

---

## 🖥 Frontend Pages Guide

| Page | File | Purpose |
|---|---|---|
| **Sign Up** | `signup.html` | New user registration |
| **Login** | `login.html` | User authentication |
| **Onboarding** | `onboarding.html` | 5-step setup wizard |
| **Dashboard** | `dashboard.html` | Overview metrics & charts |
| **Analytics** | `analytics.html` | Deep-dive sentiment analytics |
| **Conversations** | `chat.html` | Live chat management |
| **Escalations** | `escalations.html` | Escalated conversations |
| **Reports** | `reports.html` | Generate & export CSV reports |
| **Settings** | `settings.html` | Preferences, team, API keys |
| **Knowledge Base** | `knowledge-base.html` | Upload & manage KB documents |
| **Widget Mgmt** | `widget-management.html` | Configure embed widget |
| **Admin Panel** | `admin.html` | Super admin god-mode *(restricted)* |

---

## 🔌 Client-Side Widget (What Goes to Your Customer)

The widget is the customer-facing part of the system. After you sign up and configure your widget, you (or your client) paste a **single `<script>` tag** into their website's HTML.

### How It Works

```
┌─────────────────────────────────────────┐
│  YOUR CLIENT'S WEBSITE (e.g., Shopify)  │
│                                         │
│  <script src="https://your-server       │
│    .com/widget/embed.js?key=API_KEY">   │
│  </script>                              │
│                                         │
│  ┌─────────────┐                        │
│  │  💬 Chat    │ ← Floating button      │
│  │   Widget    │    appears here         │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
```

### Getting the Embed Code

1. **Login** to your dashboard
2. Go to **Widget Management** → Click **"Get Embed Code"**
3. Copy the generated `<script>` tag
4. Paste it into the client's website, just before `</body>`

### Example Embed Code

```html
<!-- Behavioral Agentic AI — Chat Widget -->
<script
  src="http://localhost:8000/widget/embed.js"
  data-api-key="YOUR_WIDGET_API_KEY"
  data-theme-color="#6366f1"
  data-position="bottom-right"
  async>
</script>
```

### Widget API Endpoints (Public — No Auth Needed)

These are the endpoints the widget JS calls internally:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/widget/{api_key}/session` | Start chat session |
| POST | `/api/widget/{api_key}/chat` | Send customer message |
| GET | `/api/widget/{api_key}/history` | Load chat history |
| GET | `/api/widget/{api_key}/config` | Get widget styling |

### What Goes Where

| Component | Where It Lives | Who Sees It |
|---|---|---|
| **Dashboard** (frontend/) | Your server | You (business owner) |
| **Backend API** | Your server | Both (API calls) |
| **Widget Script** | Client's website (1 line of HTML) | Your client's customers |
| **Widget Data** | Your server (via API) | Stored on your backend |

> **Important:** The widget script is served FROM your backend server. The client's website only has a `<script>` tag pointing to your server — no code is hosted on the client's side.

---

## 🧪 Testing Guide

### Quick API Smoke Test (PowerShell)

```powershell
# 1. Signup
$body = '{"email":"test@demo.com","password":"Test123!","full_name":"Tester","business_name":"TestCorp"}'
Invoke-WebRequest -Uri "http://localhost:8000/api/auth/signup" -Method POST -ContentType "application/json" -Body $body

# 2. Login
$r = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"test@demo.com","password":"Test123!"}'
$token = ($r.Content | ConvertFrom-Json).access_token

# 3. Get Settings (authenticated)
Invoke-WebRequest -Uri "http://localhost:8000/api/settings" -Headers @{Authorization="Bearer $token"}

# 4. Analyze Sentiment
Invoke-WebRequest -Uri "http://localhost:8000/api/analyze/sentiment" -Method POST -Headers @{Authorization="Bearer $token"; "Content-Type"="application/json"} -Body '{"text":"I am furious about this!"}'
```

### Quick API Smoke Test (curl / Bash)

```bash
# Signup
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"Test123!","full_name":"Tester","business_name":"TestCorp"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@demo.com","password":"Test123!"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Get Settings
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/settings

# Analyze Sentiment
curl -X POST http://localhost:8000/api/analyze/sentiment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"I am furious about this!"}'
```

### Run Backend Unit Tests

```bash
cd backend
pytest -v
```

### Verified Test Results (32/32 Pass)

All endpoints verified across 7 FRD zones:

| Zone | Tests | Status |
|---|---|---|
| Auth | Signup, Login, Profile, Token Refresh | ✅ 4/4 |
| Settings | GET, PUT 11 fields, Persistence, Key Regen | ✅ 4/4 |
| Analytics | Dashboard, Trends, Escalation, Language, Hourly | ✅ 5/5 |
| Conversations | Create, Message, Escalate, Resolve | ✅ 4/4 |
| Sentiment | Analyze, Language Detection | ✅ 2/2 |
| Admin | Analytics, Clients, Audit Logs | ✅ 3/3 |
| Knowledge Base | Stats, Docs, Text Upload, Search | ✅ 4/4 |
| Widget | Config, Update, Embed Code, Toggle | ✅ 4/4 |
| Security | Rate Limiting, Auth Guard | ✅ 2/2 |

---

## ⚙ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | Database connection string |
| `JWT_SECRET_KEY` | *(must set)* | JWT signing secret (min 32 chars) |
| `SECRET_KEY` | *(must set)* | Application secret key |
| `OPENROUTER_API_KEY` | *(optional)* | For LLM-powered AI responses |
| `LLM_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | LLM model identifier |
| `CORS_ORIGINS` | `http://localhost:5500,...` | Allowed CORS origins |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `POSTGRES_PASSWORD` | `changeme123` | PostgreSQL password (Docker) |
| `REDIS_HOST` | `redis` | Redis hostname (Docker) |

---

## ✅ FRD v3.0 Feature Coverage

| Zone | Feature | Status |
|---|---|---|
| **FR-1** | JWT Auth (signup, login, refresh, logout) | ✅ |
| **FR-2** | 5-step Onboarding Wizard | ✅ |
| **FR-3.1** | Dashboard Metrics & Charts | ✅ |
| **FR-3.2** | Conversation Management + Auto-Escalation | ✅ |
| **FR-3.3** | Reports + CSV Export | ✅ |
| **FR-3.4** | Sentiment Analysis (VADER + multilingual) | ✅ |
| **FR-3.5** | AI Chat with RAG | ✅ |
| **FR-3.6** | Settings (11 preference fields) | ✅ |
| **FR-4** | Super Admin Panel (clients, analytics, logs) | ✅ |
| **FR-5** | Knowledge Base (upload, search, FAQs) | ✅ |
| **FR-6** | Embeddable Widget (config, toggle, embed) | ✅ |
| **FR-7.2.5** | Rate Limiting (60/120/200 tiers) | ✅ |
| **FR-7.3** | Tenant Isolation (multi-tenant) | ✅ |

---

## 📝 License

This project is developed as a Final Year Project (FYP). All dependencies are free and open source.
