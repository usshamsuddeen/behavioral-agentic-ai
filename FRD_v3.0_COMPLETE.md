# FUNCTIONAL REQUIREMENTS DOCUMENT (FRD) v3.0
# Behavioral Agentic AI — Sentiment-Aware Escalation System
## WIDGET-EMBED · NO PAYMENTS · SINGLE RAG · BERT SENTIMENT

**Project:** Final Year Project — KFUEIT  
**Author:** Usman Shams | SWEN221101044  
**Version:** 3.0 (Revised)  
**Date:** February 2026  
**Sentiment Model:** `nlptown/bert-base-multilingual-uncased-sentiment` (HuggingFace)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Three-Actor Model](#2-three-actor-model)
3. [Zone 1 — Public Zone (Client Entry)](#3-zone-1--public-zone)
4. [Zone 2 — Onboarding Wizard](#4-zone-2--onboarding-wizard)
5. [Zone 3 — Client Dashboard](#5-zone-3--client-dashboard)
6. [Zone 4 — Super Admin Panel](#6-zone-4--super-admin-panel)
7. [Zone 5 — Core AI/ML Engine](#7-zone-5--core-aiml-engine)
8. [Zone 6 — Customer Chat Layer](#8-zone-6--customer-chat-layer)
9. [Zone 7 — Security & Compliance](#9-zone-7--security--compliance)
10. [Data Flow Pipeline](#10-data-flow-pipeline)
11. [Zone Dependency Map](#11-zone-dependency-map)
12. [Database Schema Overview](#12-database-schema-overview)
13. [API Endpoint Registry](#13-api-endpoint-registry)
14. [Technology Stack](#14-technology-stack)

---

## 1. System Overview

### 1.1 Purpose

The Behavioral Agentic AI platform is a **multi-tenant SaaS system** that provides e-commerce store owners with an **embeddable AI-powered chat widget**. The widget handles customer inquiries using RAG (Retrieval-Augmented Generation), performs **real-time sentiment analysis** using the `nlptown/bert-base-multilingual-uncased-sentiment` BERT model, and **intelligently escalates** conversations to human agents when emotional thresholds are breached.

### 1.2 Delivery Model

| Aspect | Specification |
|--------|--------------|
| **Deployment** | Embeddable `<script>` tag widget — works on ANY website |
| **Supported Platforms** | Shopify, WooCommerce, Wix, Squarespace, Custom HTML |
| **Payment Processing** | REMOVED — no billing, subscriptions, or plan management |
| **RAG Ingestion** | SINGLE method — client uploads documents via dashboard |
| **Supported Formats** | PDF, DOCX, TXT, CSV |
| **Sentiment Model** | `nlptown/bert-base-multilingual-uncased-sentiment` (HuggingFace, deployed) |
| **LLM Provider** | OpenRouter API (free-tier: Llama 3.3 70B, Mistral Small 24B) |

### 1.3 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT'S E-COMMERCE STORE                        │
│   (Shopify / WooCommerce / Wix / Squarespace / Custom HTML)            │
│                                                                         │
│   ┌─────────────────────────────────────────────────────┐               │
│   │  <script src="https://our-api/widget/{API_KEY}">   │  ◄── ZONE 6  │
│   │  Embeddable Chat Widget (JS Bundle)                 │               │
│   └───────────────────────┬─────────────────────────────┘               │
└───────────────────────────┼─────────────────────────────────────────────┘
                            │ HTTPS REST + WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     OUR PLATFORM (Backend API Server)                    │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ ZONE 1   │  │ ZONE 2   │  │ ZONE 3   │  │ ZONE 4   │  │ ZONE 7   │ │
│  │ Public   │  │Onboarding│  │ Client   │  │ Super    │  │ Security │ │
│  │ Zone     │  │ Wizard   │  │Dashboard │  │ Admin    │  │ Layer    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │              │      │
│       └──────────────┴──────────────┴──────────────┴──────────────┘      │
│                                     │                                    │
│                                     ▼                                    │
│                    ┌────────────────────────────────┐                    │
│                    │         ZONE 5                  │                    │
│                    │    CORE AI/ML ENGINE             │                    │
│                    │                                  │                    │
│                    │  ┌──────────┐  ┌──────────────┐ │                    │
│                    │  │Sentiment │  │ RAG Pipeline │ │                    │
│                    │  │(BERT)    │  │              │ │                    │
│                    │  └──────────┘  └──────────────┘ │                    │
│                    │  ┌──────────┐  ┌──────────────┐ │                    │
│                    │  │Escalation│  │ Behavioral   │ │                    │
│                    │  │Engine    │  │ Prediction   │ │                    │
│                    │  └──────────┘  └──────────────┘ │                    │
│                    └────────────────────────────────┘                    │
│                                     │                                    │
│                    ┌────────────────┴────────────────┐                   │
│                    │         DATA LAYER               │                   │
│                    │  SQLite/PostgreSQL + ChromaDB    │                   │
│                    │  (Tenant-Isolated Collections)   │                   │
│                    └─────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Three-Actor Model

### 2.1 Actor: END CUSTOMER (Store Visitor)

| Attribute | Detail |
|-----------|--------|
| **Who** | A person visiting the client's online store |
| **Entry Point** | Sees the embedded chat widget on the store's website |
| **Capabilities** | Click widget → open chat → converse with AI → get help or get escalated to human |
| **Authentication** | NONE — anonymous; optionally provides name/email via pre-chat form |
| **Touches** | Zone 6 only (Widget + Chat UI) |
| **Data Created** | Messages, sentiment scores, conversation records |

### 2.2 Actor: CLIENT (Store Owner / Team)

| Attribute | Detail |
|-----------|--------|
| **Who** | E-commerce store owner or their team members |
| **Entry Point** | Signs up on our platform via Zone 1 |
| **Capabilities** | Configure widget, upload KB docs, monitor conversations, handle escalations, view analytics |
| **Authentication** | Email + password → JWT token |
| **Touches** | Zone 1 → Zone 2 → Zone 3 (full client journey) |
| **Data Owned** | Tenant record, widget config, KB documents, conversation logs, analytics |

**CLIENT Sub-Roles:**
| Sub-Role | Permissions |
|----------|------------|
| `client_owner` | Full access — widget config, KB upload, team management, settings |
| `client_agent` | Chat monitoring, escalation handling, conversation view — NO settings/config access |

### 2.3 Actor: SUPER ADMIN (Platform Owner — Us)

| Attribute | Detail |
|-----------|--------|
| **Who** | The platform operators (us) |
| **Entry Point** | Direct login to admin panel |
| **Capabilities** | View ALL clients, ALL conversations, ALL logs, suspend accounts, manage AI models |
| **Authentication** | Email + password + elevated role check |
| **Touches** | Zone 4 (God-Mode Panel) |
| **Data Access** | Everything across all tenants |

---

## 3. Zone 1 — Public Zone (Client Entry)

### FR-1.1 Landing Page

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-1.1.1 | Hero section with SaaS value proposition | Must | Headline: AI-powered customer support widget for any e-commerce store |
| FR-1.1.2 | Feature showcase section | Must | Cards for: Sentiment Analysis, RAG-based Answers, Smart Escalation, Widget Embed |
| FR-1.1.3 | "How It Works" process flow | Must | 3 steps: Paste widget code → AI handles chats → Monitor in dashboard |
| FR-1.1.4 | Supported platforms display | Must | Show logos: Shopify, WooCommerce, Wix, Squarespace, Custom HTML |
| FR-1.1.5 | Live demo widget preview | Should | Interactive mock of the chat widget on the landing page |
| FR-1.1.6 | CTA buttons | Must | "Sign Up Free" → FR-1.2, "Try Demo" → FR-1.1.5 |
| FR-1.1.7 | Navigation bar | Must | Links: Features, How it Works, Demo, Login, Sign Up |
| FR-1.1.8 | Footer with project info | Must | FYP info, author, university |

**Existing Implementation:** `frontend/index.html` + `css/landing.css` + `js/landing.js`  
**Gap:** Hero text mentions "CRM integration" — must change to "widget-embed for any store."

### FR-1.2 Client Signup

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-1.2.1 | Registration form | Must | Fields: Full Name, Email, Password, Confirm Password |
| FR-1.2.2 | Company/Store name field | Must | Used to create the Tenant record |
| FR-1.2.3 | Store URL field | Should | Optional at signup, required during onboarding |
| FR-1.2.4 | Email validation | Must | Format check + uniqueness check |
| FR-1.2.5 | Password strength enforcement | Must | Min 8 chars, 1 uppercase, 1 number |
| FR-1.2.6 | Auto-create Tenant on signup | Must | Creates `tenants` record with `owner_id = new_user.id` |
| FR-1.2.7 | Auto-assign CLIENT role | Must | New user gets `role = "client_owner"` |
| FR-1.2.8 | Auto-generate widget API key | Must | `widget_api_key = "wk_" + random(32)` stored in tenant |
| FR-1.2.9 | JWT token issuance on signup | Must | Return access_token + refresh_token |
| FR-1.2.10 | Redirect to onboarding wizard | Must | After successful signup → Zone 2 |

**Existing Implementation:** `frontend/pages/signup.html` + `backend/app/api/auth.py::signup()`  
**Gap:** No company/store fields, no Tenant creation, no widget API key generation.

### FR-1.3 Client Login

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-1.3.1 | Login form | Must | Fields: Email, Password |
| FR-1.3.2 | JWT authentication | Must | Return access_token + refresh_token |
| FR-1.3.3 | Role-based redirect | Must | CLIENT → Zone 3 dashboard, SUPER_ADMIN → Zone 4 admin panel |
| FR-1.3.4 | "Forgot password" link | Should | Placeholder — email-based reset |
| FR-1.3.5 | Session persistence | Must | Store JWT in localStorage, auto-refresh before expiry |
| FR-1.3.6 | Onboarding check | Must | If `onboarding_completed == false` → redirect to Zone 2 |

**Existing Implementation:** `frontend/pages/login.html` + `backend/app/api/auth.py::login()`  
**Gap:** No role-based redirect, no onboarding completion check.

---

## 4. Zone 2 — Onboarding Wizard

> **Purpose:** Guide a new CLIENT through a 5-step setup process to configure their AI chat widget and deploy it on their store.

### FR-2.1 Step 1: Business Profile

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-2.1.1 | Company name input | Must | Pre-filled from signup if provided |
| FR-2.1.2 | Industry/category selector | Should | Dropdown: Fashion, Electronics, Food, Health, General, Other |
| FR-2.1.3 | Company description textarea | Should | Used to personalize AI responses |
| FR-2.1.4 | Support email input | Must | Where escalation notifications are sent |
| FR-2.1.5 | Timezone selector | Should | For analytics time-based reporting |
| FR-2.1.6 | Save & continue to Step 2 | Must | `POST /api/onboarding/business-profile` |

**Backend Endpoint:** `POST /api/onboarding/business-profile`  
**Request Body:**
```json
{
  "company_name": "string",
  "industry": "string",
  "description": "string",
  "support_email": "string",
  "timezone": "string"
}
```
**Storage:** Updates `tenants` table fields.

### FR-2.2 Step 2: Connect Store

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-2.2.1 | Store URL input | Must | Full URL of the client's e-commerce store |
| FR-2.2.2 | Platform selector | Must | Dropdown: Shopify, WooCommerce, Wix, Squarespace, Custom HTML |
| FR-2.2.3 | URL validation | Should | Check that URL is reachable (basic HTTP HEAD check) |
| FR-2.2.4 | Platform-specific instructions | Should | Contextual help: "For Shopify: go to Online Store → Themes → Edit Code → paste in theme.liquid" |
| FR-2.2.5 | Save & continue to Step 3 | Must | `POST /api/onboarding/connect-store` |

**Backend Endpoint:** `POST /api/onboarding/connect-store`  
**Request Body:**
```json
{
  "store_url": "string",
  "platform": "shopify|woocommerce|wix|squarespace|custom"
}
```
**Storage:** Updates `tenants.store_url` and `tenants.store_platform`.

### FR-2.3 Step 3: Configure Widget

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-2.3.1 | Widget position selector | Must | Bottom-right (default) or Bottom-left |
| FR-2.3.2 | Theme color picker | Must | Primary color for widget bubble and header |
| FR-2.3.3 | Welcome message input | Must | Default: "Hi! How can I help you today?" |
| FR-2.3.4 | Bot name input | Should | Default: "AI Assistant" — shown in chat header |
| FR-2.3.5 | Pre-chat form toggle | Should | Enable/disable requiring name+email before chat starts |
| FR-2.3.6 | Live preview panel | Must | Real-time preview of widget appearance as settings change |
| FR-2.3.7 | Save & continue to Step 4 | Must | `POST /api/onboarding/configure-widget` |

**Backend Endpoint:** `POST /api/onboarding/configure-widget`  
**Request Body:**
```json
{
  "position": "bottom-right|bottom-left",
  "theme_color": "#hex",
  "welcome_message": "string",
  "bot_name": "string",
  "pre_chat_form_enabled": true,
  "pre_chat_fields": ["name", "email"]
}
```
**Storage:** Creates/updates `widget_configs` table record for this tenant.

### FR-2.4 Step 4: Upload Knowledge Base

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-2.4.1 | Drag-and-drop file upload area | Must | Accepts PDF, DOCX, TXT, CSV |
| FR-2.4.2 | Multi-file upload support | Must | Upload 1-10 files at once |
| FR-2.4.3 | File size limit display | Must | Max 10MB per file |
| FR-2.4.4 | Upload progress indicator | Must | Per-file progress bar |
| FR-2.4.5 | Processing status feedback | Must | "Parsing → Chunking → Embedding → Indexed ✓" per file |
| FR-2.4.6 | Skip option | Should | "Skip for now — you can upload later from the dashboard" |
| FR-2.4.7 | Document list after upload | Must | Show uploaded files with chunk counts |
| FR-2.4.8 | Save & continue to Step 5 | Must | Files upload via `POST /api/knowledge/upload` |

**Backend Endpoint:** Re-uses existing `POST /api/knowledge/upload` with `client_id = tenant_id`  
**Pipeline:** Upload → Parse → Smart Chunk → Generate Embeddings → Store in tenant-scoped ChromaDB collection.

### FR-2.5 Step 5: Test & Deploy

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-2.5.1 | Widget preview with test chat | Must | Fully functional widget preview — user can test chat with AI |
| FR-2.5.2 | Test message interaction | Must | Send a test message → see AI response using uploaded KB |
| FR-2.5.3 | Embed code display | Must | Show the `<script>` tag code to copy |
| FR-2.5.4 | Copy-to-clipboard button | Must | One-click copy of embed code |
| FR-2.5.5 | Platform-specific paste instructions | Should | "For Shopify: paste before `</body>` in theme.liquid" |
| FR-2.5.6 | "Complete Setup" button | Must | Marks `onboarding_completed = true`, redirects to Zone 3 |

**Embed Code Format:**
```html
<script src="https://your-domain.com/widget/embed.js" 
        data-widget-key="wk_abc123def456"></script>
```

**Backend Endpoint:** `POST /api/onboarding/complete`  
**Effect:** Sets `tenants.onboarding_completed = true`, `tenants.is_active = true`.

---

## 5. Zone 3 — Client Dashboard (Daily Operations)

> **Purpose:** The main workspace for CLIENTs. All daily monitoring, KB management, widget config, and analytics happen here.

### FR-3.1 Dashboard Home (Metrics Overview)

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.1.1 | Total conversations count (today/week/month) | Must | Scoped to this tenant's data only |
| FR-3.1.2 | Active conversations count | Must | Conversations with status "open" |
| FR-3.1.3 | Average sentiment score | Must | Mean sentiment across all conversations this period |
| FR-3.1.4 | Escalation rate | Must | `(escalated conversations / total conversations) × 100` |
| FR-3.1.5 | Sentiment distribution chart | Must | Pie/donut chart: positive / neutral / negative breakdown |
| FR-3.1.6 | Conversations over time chart | Must | Line chart: daily conversation volume |
| FR-3.1.7 | Recent escalations list | Must | Last 5 escalated conversations with priority tags |
| FR-3.1.8 | Widget status indicator | Must | Green "Active" / Red "Inactive" badge |
| FR-3.1.9 | Quick actions panel | Should | "Upload KB", "Configure Widget", "View Escalations" |

**Existing Implementation:** `frontend/pages/dashboard.html` + `js/dashboard.js`  
**Gap:** Not tenant-scoped, no widget status, uses hardcoded `default_client` ID.

### FR-3.2 Chat Interface (Live Monitor)

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.2.1 | Conversation list sidebar | Must | All conversations with status badges (active/escalated/resolved) |
| FR-3.2.2 | Real-time message display | Must | Messages appear instantly via WebSocket |
| FR-3.2.3 | Sentiment indicator per message | Must | Color-coded dot: green/yellow/red with score |
| FR-3.2.4 | Escalation alert banner | Must | Red banner when a conversation is escalated |
| FR-3.2.5 | Human takeover button | Must | CLIENT agent clicks to take over from AI |
| FR-3.2.6 | Agent response input | Must | Text input for human agent to type responses |
| FR-3.2.7 | Agent response goes to widget | Must | Human response replaces AI, customer sees it in widget |
| FR-3.2.8 | Conversation metadata panel | Should | Show: customer name/email (if pre-chat), start time, message count, avg sentiment |
| FR-3.2.9 | Typing indicators | Should | Show when customer is typing |
| FR-3.2.10 | Conversation search/filter | Should | Search by customer name, filter by status |

**Existing Implementation:** `frontend/pages/chat.html` + `js/chat.js`  
**Gap:** No human takeover flow, no escalation banner, not tenant-scoped.

### FR-3.3 Analytics & Reports

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.3.1 | Sentiment trends chart | Must | Line chart: avg sentiment score over time |
| FR-3.3.2 | Escalation trends chart | Must | Bar chart: escalations per day/week |
| FR-3.3.3 | Response time metrics | Must | Average AI response time, average human response time |
| FR-3.3.4 | Top escalation reasons | Must | Table: most common escalation trigger keywords |
| FR-3.3.5 | Customer satisfaction proxy | Should | Derived from final sentiment of resolved conversations |
| FR-3.3.6 | Conversation volume heatmap | Should | Hourly/daily heatmap of conversation activity |
| FR-3.3.7 | Churn risk overview | Should | Customers flagged as high churn risk (from FR-5.4) |
| FR-3.3.8 | Date range filter | Must | Today, Last 7 days, Last 30 days, Custom range |
| FR-3.3.9 | Export to CSV | Should | Download analytics data as CSV |

**Existing Implementation:** `frontend/pages/analytics.html` + `js/analytics.js` + `frontend/pages/reports.html`  
**Gap:** Not tenant-scoped. Reports page may be merged into analytics.

### FR-3.4 Knowledge Base Management

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.4.1 | Document upload (drag-and-drop) | Must | PDF, DOCX, TXT, CSV — max 10MB per file |
| FR-3.4.2 | Document list with metadata | Must | Filename, type, chunk count, upload date, size |
| FR-3.4.3 | Document delete (individual) | Must | Removes document + all its chunks from vector store |
| FR-3.4.4 | Delete all documents | Must | Clears entire KB for this tenant (with confirmation) |
| FR-3.4.5 | Knowledge search test | Must | Input a query → see which KB chunks are retrieved |
| FR-3.4.6 | KB statistics display | Must | Total documents, total chunks, total size |
| FR-3.4.7 | Document category labels | Should | Assign categories: Products, Policies, FAQs, General |
| FR-3.4.8 | FAQ bulk upload (JSON) | Should | Upload structured Q&A pairs |
| FR-3.4.9 | Processing status per document | Must | Pending → Processing → Indexed / Failed |

**Existing Implementation:** `frontend/pages/knowledge-base.html` + `js/knowledge.js` + `backend/app/api/knowledge.py` + `backend/app/knowledge/`  
**Gap:** Uses `default_client` — must use `tenant_id`. Otherwise functionally complete.

### FR-3.5 Widget Management

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.5.1 | Widget appearance editor | Must | Color picker, position, welcome message, bot name |
| FR-3.5.2 | Live preview panel | Must | Real-time preview as settings change |
| FR-3.5.3 | Pre-chat form configuration | Should | Toggle on/off, configure required fields |
| FR-3.5.4 | Embed code display + copy | Must | Show `<script>` tag with tenant's widget API key |
| FR-3.5.5 | Widget enable/disable toggle | Must | Instantly activate or deactivate the widget |
| FR-3.5.6 | Widget analytics summary | Should | Total loads, conversations started, avg session duration |

**Existing Implementation:** NONE — must be built from scratch.  
**Replaces:** The old `integrations.html` page.

### FR-3.6 Settings & Team Management

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-3.6.1 | Profile settings | Must | Edit name, email, password |
| FR-3.6.2 | Company settings | Must | Edit company name, industry, support email |
| FR-3.6.3 | Notification preferences | Should | Email notifications for escalations on/off |
| FR-3.6.4 | AI behavior settings | Should | Escalation sensitivity threshold (slider: 0.0 — 1.0) |
| FR-3.6.5 | Team member invite | Should | Invite agents by email → they get `client_agent` role |
| FR-3.6.6 | Team member list | Should | View/remove team members |
| FR-3.6.7 | API key management | Should | View/regenerate widget API key |

**Existing Implementation:** `frontend/pages/settings.html` — partially covers FR-3.6.1, FR-3.6.2.  
**Gap:** No team management, no AI behavior settings, no API key management.

---

## 6. Zone 4 — Super Admin Panel

> **Purpose:** God-mode panel for platform owners (us). Sees ALL clients, ALL data, ALL logs.  
> **Access:** Only users with `role = "super_admin"` can access.

### FR-4.1 All-Account Management

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-4.1.1 | Client account list | Must | Table: tenant name, owner email, plan, status, created date |
| FR-4.1.2 | Search clients | Must | Search by name, email, store URL |
| FR-4.1.3 | Suspend client account | Must | Toggle: active ↔ suspended. Suspended = widget stops responding |
| FR-4.1.4 | View client dashboard (read-only) | Should | Impersonate a client's dashboard view without modifying anything |
| FR-4.1.5 | Override client settings | Should | Force-update widget config or AI settings for a client |
| FR-4.1.6 | Client detail view | Must | Show: conversations count, documents count, escalation rate, last activity |

### FR-4.2 System-Wide Analytics

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-4.2.1 | Total conversations (all clients) | Must | Aggregate count with trend arrow |
| FR-4.2.2 | Total active clients | Must | Clients with at least 1 conversation in last 30 days |
| FR-4.2.3 | Aggregated sentiment trends | Must | System-wide sentiment distribution over time |
| FR-4.2.4 | Global escalation rate | Must | System-wide escalation percentage |
| FR-4.2.5 | AI response quality metrics | Should | Average confidence score of AI responses |
| FR-4.2.6 | System health monitoring | Should | API response times, error rates, uptime |
| FR-4.2.7 | Resource usage per client | Should | Conversations count, KB size, API calls per client |

### FR-4.3 Global Audit Logs

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-4.3.1 | API call log | Must | Every API call logged: timestamp, user, endpoint, status code |
| FR-4.3.2 | Error tracking | Must | Failed requests with stack traces |
| FR-4.3.3 | Auth event log | Must | Login/logout/signup events with IP addresses |
| FR-4.3.4 | Search/filter logs | Must | Filter by: date range, client, event type, status |
| FR-4.3.5 | Log export (CSV) | Should | Download filtered logs as CSV |

**Existing Implementation:** NONE — must be built from scratch.

---

## 7. Zone 5 — Core AI/ML Engine

> **Purpose:** Powers ALL intelligence across the platform. Shared engine used by Zone 6 (widget chat) and Zone 3 (analytics/predictions). This is the CORE of the system.

### FR-5.1 Sentiment Analysis

> **Model:** `nlptown/bert-base-multilingual-uncased-sentiment` from HuggingFace  
> **Architecture:** 3-tier fallback: BERT (Primary) → VADER (Secondary) → TextBlob/Dictionary (Tertiary)

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-5.1.1 | Per-message sentiment scoring | Must | Every incoming customer message gets a sentiment score (0.0–1.0) |
| FR-5.1.2 | Sentiment classification | Must | Classify as: `positive`, `neutral`, `negative` |
| FR-5.1.3 | BERT model integration | Must | Primary: `nlptown/bert-base-multilingual-uncased-sentiment` — 5-star → normalized 0–1 |
| FR-5.1.4 | VADER fallback | Must | Secondary: If BERT fails or is unavailable, use VADER for English |
| FR-5.1.5 | Dictionary fallback | Must | Tertiary: Keyword-based multilingual dictionaries for non-English when BERT unavailable |
| FR-5.1.6 | Emotion classification | Must | Detect specific emotions: anger, joy, frustration, confusion, satisfaction |
| FR-5.1.7 | Compound sentiment tracking | Must | Track sentiment trajectory across conversation (moving average) |
| FR-5.1.8 | Urgency keyword detection | Must | Flag messages containing legal threats, refund demands, profanity |
| FR-5.1.9 | Multilingual support | Must | Languages: English, Spanish, French, German, Arabic, Chinese |
| FR-5.1.10 | Threshold configuration per tenant | Should | Clients can set their own negative-sentiment escalation threshold |
| FR-5.1.11 | Response time < 500ms | Must | Sentiment analysis must complete within 500ms per message |

**BERT Model Details:**

| Property | Value |
|----------|-------|
| Model ID | `nlptown/bert-base-multilingual-uncased-sentiment` |
| Source | HuggingFace Transformers |
| Output | 5-class: 1 star → 5 stars |
| Normalization | `score = (predicted_stars - 1) / 4` → 0.0 (most negative) to 1.0 (most positive) |
| Languages | 6 languages: English, Dutch, German, French, Spanish, Italian |
| Fallback trigger | If model loading fails or inference errors → fall back to VADER |

**Score Mapping:**
```
Stars → Sentiment Label:
1 star (0.00–0.20) → "very_negative"  → Emotion: anger/rage
2 star (0.20–0.40) → "negative"       → Emotion: frustration/disappointment
3 star (0.40–0.60) → "neutral"        → Emotion: calm/indifferent
4 star (0.60–0.80) → "positive"       → Emotion: satisfaction/happy
5 star (0.80–1.00) → "very_positive"  → Emotion: delight/enthusiasm
```

**Existing Implementation:** `backend/app/services/sentiment.py` + `backend/app/nlp/transformer_sentiment.py`  
**Status:** ✅ Fully implemented with 3-tier fallback.

### FR-5.2 RAG Pipeline (Single Input Method)

> **Ingestion:** Client uploads documents via dashboard (Zone 3 → FR-3.4)  
> **Supported Formats:** PDF, DOCX, TXT, CSV

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-5.2.1 | Document parsing | Must | Extract text from PDF (PyPDF2), DOCX (python-docx), TXT, CSV |
| FR-5.2.2 | Smart text chunking | Must | Split documents into 500-token chunks with 50-token overlap |
| FR-5.2.3 | Embedding generation | Must | Generate vector embeddings per chunk (TF-IDF or sentence-transformers) |
| FR-5.2.4 | Tenant-scoped vector storage | Must | Each tenant's documents stored in isolated ChromaDB collection: `tenant_{id}` |
| FR-5.2.5 | Similarity search at query time | Must | Customer message → embed → cosine similarity → Top-K chunks |
| FR-5.2.6 | Context injection into LLM prompt | Must | Retrieved chunks injected as context in LLM system prompt |
| FR-5.2.7 | No cross-tenant data leakage | Must | Queries ONLY search within the requesting tenant's collection |
| FR-5.2.8 | Document metadata tracking | Must | Track: filename, upload date, chunk count, file size, status |
| FR-5.2.9 | Document deletion with chunk cleanup | Must | Deleting a document removes all its chunks from ChromaDB |
| FR-5.2.10 | Top-K configurable | Should | Default K=5, configurable per tenant |

**RAG Pipeline Flow:**
```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Client   │──▶│  Parse &     │──▶│  Generate    │──▶│  Store in    │
│  Uploads  │   │  Chunk       │   │  Embeddings  │   │  ChromaDB    │
│  File(s)  │   │  (500 tokens │   │  (per chunk) │   │  collection: │
│           │   │   + overlap)  │   │              │   │  tenant_{id} │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘

At Query Time:
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Customer    │──▶│  Embed       │──▶│  Similarity  │──▶│  Top-K       │
│  Message     │   │  Query       │   │  Search in   │   │  Chunks      │
│              │   │              │   │  tenant_{id} │   │  Retrieved   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────┐
                                                          │  Inject into │
                                                          │  LLM Prompt  │
                                                          │  as Context  │
                                                          └──────┬───────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────┐
                                                          │  AI Response │
                                                          │  Sent to     │
                                                          │  Customer    │
                                                          └──────────────┘
```

**Existing Implementation:** `backend/app/ai/embeddings.py`, `vector_store.py`, `retrieval.py`, `knowledge/indexer.py`, `processor.py`, `manager.py`  
**Status:** ✅ Fully implemented. Gap: uses `client_id` string — must enforce it equals `tenant_id`.

### FR-5.3 Escalation Engine

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-5.3.1 | Rule-based keyword triggers | Must | Match against 50+ escalation keywords (legal, refund, profanity, etc.) |
| FR-5.3.2 | Sentiment threshold breach | Must | Escalate when compound sentiment drops below configurable threshold (default: 0.25) |
| FR-5.3.3 | Repeated negative loop detection | Must | 3+ consecutive negative messages → auto-escalate |
| FR-5.3.4 | Explicit human-agent request | Must | Detect "talk to a human", "real person", "speak to manager" → immediate escalate |
| FR-5.3.5 | Profanity/abuse detection | Must | Strong language, slurs, threats → immediate escalate |
| FR-5.3.6 | Caps lock frustration detection | Must | >40% uppercase characters → add to trigger score |
| FR-5.3.7 | Repeated punctuation detection | Must | "!!!" or "???" patterns → add to trigger score |
| FR-5.3.8 | Trigger score calculation | Must | Weighted sum of all signals → 0.0–1.0 score |
| FR-5.3.9 | Escalation priority assignment | Must | Priority levels: `low`, `normal`, `high`, `urgent` |
| FR-5.3.10 | Handoff package generation | Must | When escalated, create package: full conversation, sentiment history, trigger reasons, priority |
| FR-5.3.11 | Real-time escalation notification | Must | WebSocket push to CLIENT's dashboard when escalation occurs |

**Handoff Package Structure:**
```json
{
  "conversation_id": "string",
  "customer_info": { "name": "string", "email": "string" },
  "priority": "urgent|high|normal|low",
  "trigger_reasons": ["keyword: lawyer", "sentiment below threshold"],
  "sentiment_history": [
    { "message_index": 1, "score": 0.72, "label": "positive" },
    { "message_index": 2, "score": 0.31, "label": "negative" },
    { "message_index": 3, "score": 0.15, "label": "very_negative" }
  ],
  "full_conversation": [ /* all messages */ ],
  "ai_suggested_response": "string"
}
```

**Existing Implementation:** `backend/app/services/escalation.py`  
**Status:** ✅ Fully implemented with optimized thresholds.

### FR-5.4 Behavioral Prediction

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-5.4.1 | Churn risk scoring | Must | Based on: sentiment trajectory, escalation count, resolution time |
| FR-5.4.2 | Churn risk labels | Must | `low` (<30%), `medium` (30-60%), `high` (>60%) with recommendations |
| FR-5.4.3 | Purchase intent signals | Should | Detect positive buying signals in conversation |
| FR-5.4.4 | Frustration pattern detection | Must | Identify escalating frustration across multiple messages |
| FR-5.4.5 | Escalation probability prediction | Must | Predict likelihood of escalation based on current conversation state |
| FR-5.4.6 | Resolution time estimation | Should | Predict time to resolution based on issue category and sentiment |
| FR-5.4.7 | Customer satisfaction prediction | Should | Predict CSAT score from sentiment history |
| FR-5.4.8 | Session behavior analysis | Should | Track conversation patterns: response frequency, message length trends |

**Existing Implementation:** `backend/app/services/prediction.py`  
**Status:** ✅ Fully implemented with rule-based scoring, ready for ML model upgrade.

---

## 8. Zone 6 — Customer Chat Layer

> **Purpose:** The end-customer's touchpoint. An embeddable JavaScript widget that loads on the client's store and provides AI-powered chat.

### FR-6.1 Embeddable JS Widget

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-6.1.1 | Single `<script>` tag embed | Must | `<script src=".../widget/embed.js" data-widget-key="wk_xxx">` |
| FR-6.1.2 | Platform-agnostic | Must | Works on: Shopify, WooCommerce, Wix, Squarespace, any HTML page |
| FR-6.1.3 | No conflicts with host page | Must | Widget runs in isolated DOM scope (shadow DOM or iframe) |
| FR-6.1.4 | Lazy loading | Must | Widget JS loads asynchronously, does not block host page |
| FR-6.1.5 | Chat bubble icon | Must | Floating circle button in configured position (bottom-right/left) |
| FR-6.1.6 | Bubble uses tenant theme color | Must | Color matches tenant's `widget_config.theme_color` |
| FR-6.1.7 | Config loaded from API | Must | On load: `GET /api/widget/{api_key}/config` → returns theme, welcome msg, etc. |
| FR-6.1.8 | Bubble click → expand chat window | Must | Smooth animation expanding chat panel |
| FR-6.1.9 | Minimize/close button | Must | Customer can minimize chat back to bubble |
| FR-6.1.10 | Mobile responsive | Must | Widget adapts to mobile viewports |
| FR-6.1.11 | Widget deactivation support | Must | If tenant's widget is disabled → bubble does not appear |

### FR-6.2 Chat UI (Customer-Facing)

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-6.2.1 | Pre-chat form (if enabled) | Should | Collect name + email before first message |
| FR-6.2.2 | Chat header | Must | Shows bot name + online status indicator |
| FR-6.2.3 | Message input field | Must | Text input with send button |
| FR-6.2.4 | Message display area | Must | Scrollable area showing conversation bubbles |
| FR-6.2.5 | Customer message styling | Must | Right-aligned bubbles in light color |
| FR-6.2.6 | AI/Agent response styling | Must | Left-aligned bubbles in theme color |
| FR-6.2.7 | Typing indicator | Must | "AI is typing..." animation while waiting for response |
| FR-6.2.8 | Timestamp display | Should | Time shown under each message |
| FR-6.2.9 | Message send via API | Must | `POST /api/widget/{api_key}/chat` with message content |
| FR-6.2.10 | Real-time response via WebSocket | Must | Response pushed back via WebSocket, not polling |
| FR-6.2.11 | Human agent seamless transition | Must | When escalated, human agent's messages appear in same chat UI |
| FR-6.2.12 | Emoji support | Should | Basic emoji picker or text emoji rendering |
| FR-6.2.13 | File attachment support | Could | Allow customer to attach images (stretch goal) |
| FR-6.2.14 | Session persistence | Should | If customer refreshes page, conversation continues (localStorage session ID) |

**Widget API Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/widget/{api_key}/config` | Load widget configuration (theme, welcome msg) |
| POST | `/api/widget/{api_key}/session` | Start new chat session, return session_id |
| POST | `/api/widget/{api_key}/chat` | Send customer message, receive AI response |
| GET | `/api/widget/{api_key}/history/{session_id}` | Reload conversation if page refreshed |

**Existing Implementation:** NONE — must be built from scratch.

---

## 9. Zone 7 — Security & Compliance

> **Purpose:** Wraps ALL zones horizontally. Every request, every data access, every API call goes through this layer.

### FR-7.1 Authentication & Authorization

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-7.1.1 | JWT token authentication | Must | Access token (15min) + Refresh token (7 days) |
| FR-7.1.2 | Role-based access control (RBAC) | Must | Roles: `super_admin`, `client_owner`, `client_agent`, `end_customer` |
| FR-7.1.3 | Route-level RBAC guards | Must | Each API endpoint specifies allowed roles |
| FR-7.1.4 | Session management | Must | Track active sessions, support logout (revoke token) |
| FR-7.1.5 | Password hashing | Must | bcrypt with salt rounds |
| FR-7.1.6 | Widget API key auth | Must | Widget endpoints authenticate via `widget_api_key` (no JWT needed for end customers) |

**RBAC Matrix:**

| Endpoint Group | super_admin | client_owner | client_agent | end_customer (widget) |
|---------------|:-----------:|:------------:|:------------:|:--------------------:|
| Zone 1 (Public) | ✅ | ✅ | ✅ | ✅ |
| Zone 2 (Onboarding) | ❌ | ✅ | ❌ | ❌ |
| Zone 3 (Dashboard) | ✅ (read-only) | ✅ | ✅ (limited) | ❌ |
| Zone 4 (Admin) | ✅ | ❌ | ❌ | ❌ |
| Zone 5 (AI Engine) | ✅ | ✅ (own tenant) | ✅ (own tenant) | ✅ (via widget key) |
| Zone 6 (Widget API) | ✅ | ❌ | ❌ | ✅ |

### FR-7.2 Data Protection

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-7.2.1 | HTTPS/TLS in transit | Must | All API calls over HTTPS |
| FR-7.2.2 | Password encryption at rest | Must | bcrypt hashed, never stored in plaintext |
| FR-7.2.3 | Credential encryption | Must | Integration credentials stored as encrypted JSON |
| FR-7.2.4 | CORS configuration | Must | Widget domain whitelisting per tenant |
| FR-7.2.5 | Rate limiting | Should | Widget API: 60 req/min per session. Dashboard API: 120 req/min per user |

### FR-7.3 Tenant Isolation

| ID | Requirement | Priority | Detail |
|----|-------------|----------|--------|
| FR-7.3.1 | Per-tenant data isolation | Must | All DB queries include `WHERE tenant_id = X` |
| FR-7.3.2 | Separate ChromaDB collections | Must | Each tenant's KB stored in `collection: tenant_{id}` |
| FR-7.3.3 | No cross-tenant data leakage | Must | A client can NEVER see another client's conversations, KB, or analytics |
| FR-7.3.4 | Scoped API keys | Must | Widget API key scoped to exactly one tenant |
| FR-7.3.5 | Tenant deletion cascade | Should | Deleting tenant removes ALL data: users, conversations, KB, widget config |

**Existing Implementation:** `backend/app/middleware/jwt.py`, `auth.py`, `logging_middleware.py`  
**Gap:** No tenant isolation logic, no RBAC guards beyond basic auth, no widget API key auth.

---

## 10. Data Flow Pipeline

### 10.1 Happy Path (Customer → AI Response)

```
Customer visits store → Widget <script> loads → Widget fetches config
    → Customer clicks chat bubble → Chat UI opens
    → Customer types message → POST /api/widget/{key}/chat
    → Backend receives message
        → Step 1: Sentiment Analysis (BERT model)
            → Score: 0.72 (positive) → No escalation trigger
        → Step 2: RAG Pipeline
            → Embed query → Search tenant's ChromaDB → Top-5 chunks retrieved
        → Step 3: LLM Response Generation
            → System prompt + KB context + conversation history + sentiment
            → OpenRouter API → Llama 3.3 70B generates response
        → Step 4: Behavioral Prediction (background)
            → Update churn risk, escalation probability
        → Response sent back via WebSocket → Customer sees AI reply
    → All events logged → Dashboard updates in real-time
```

### 10.2 Escalation Path (Negative Sentiment)

```
Customer sends angry message → POST /api/widget/{key}/chat
    → Sentiment Analysis: score = 0.18 (very_negative), emotion: anger
    → Escalation Engine checks:
        ✓ Keyword match: "lawyer", "refund"
        ✓ Sentiment below threshold (0.18 < 0.25)
        ✓ Trigger score: 0.85 (high)
    → ESCALATION TRIGGERED
        → Priority: URGENT
        → Handoff package generated (full context + sentiment history)
        → WebSocket notification → CLIENT dashboard (Zone 3)
        → Escalation appears in Zone 3 escalations panel
    → AI sends empathetic holding response to customer:
        "I understand your frustration. Let me connect you with a team member who can help."
    → Human agent sees escalation in Zone 3 → clicks "Take Over"
    → Human agent types response → sent via WebSocket → customer sees human reply
```

---

## 11. Zone Dependency Map

```
Zone 1 (Public — Landing, Signup, Login)
  │
  ▼
Zone 2 (Onboarding — 5-step wizard)
  │  [Step 4: Upload KB → triggers Zone 5 RAG ingestion]
  │
  ▼
Zone 3 (Client Dashboard — daily operations)
  │                    ▲
  │                    │ Escalation handoff flows UP to client
  │                    │
  ▼                    │
Zone 6 (Widget/Chat) ──┘
  │
  │  [Every customer message routes through Zone 5]
  ▼
Zone 5 (AI Engine) ◄── ALL intelligence routes through here
  │
  │  [Sentiment, RAG, Escalation, Prediction]
  │
Zone 7 (Security) ════ Wraps ALL zones horizontally ════
  │                     [JWT, RBAC, Tenant Isolation, Encryption]
  ▼
Zone 4 (Super Admin) ◄── Observes everything, controls everything
```

---

## 12. Database Schema Overview

### Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | All user accounts (clients, agents, admins) | id, email, password_hash, role, tenant_id, onboarding_completed |
| `tenants` | Multi-tenant organizations | id, name, store_url, store_platform, widget_api_key, is_active, owner_id |
| `widget_configs` | Widget appearance per tenant | id, tenant_id, position, theme_color, welcome_message, bot_name, pre_chat_form_enabled |
| `conversations` | Chat sessions | id, tenant_id, session_id, customer_name, customer_email, status, created_at |
| `messages` | Individual messages | id, conversation_id, tenant_id, content, sender_type, sentiment_score, sentiment_label |
| `knowledge_documents` | KB document metadata | id, tenant_id, filename, doc_type, category, chunk_count, file_size, status |
| `escalations` | Escalation events | id, conversation_id, tenant_id, priority, trigger_reasons, handoff_package, resolved_by |
| `user_sessions` | JWT session tracking | id, user_id, token_hash, is_active, expires_at |
| `audit_logs` | System event log | id, user_id, tenant_id, action, endpoint, status_code, timestamp |

### Vector Store (ChromaDB)

| Collection Pattern | Purpose |
|-------------------|---------|
| `tenant_{tenant_id}` | Per-tenant knowledge base vectors |

---

## 13. API Endpoint Registry

### Zone 1 — Public
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/auth/signup` | None | Client registration |
| POST | `/api/auth/login` | None | Authentication |
| POST | `/api/auth/refresh` | Refresh Token | Token refresh |

### Zone 2 — Onboarding
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/onboarding/business-profile` | JWT (client_owner) | Step 1 |
| POST | `/api/onboarding/connect-store` | JWT (client_owner) | Step 2 |
| POST | `/api/onboarding/configure-widget` | JWT (client_owner) | Step 3 |
| POST | `/api/onboarding/complete` | JWT (client_owner) | Step 5 |
| GET | `/api/onboarding/status` | JWT (client_owner) | Progress check |

### Zone 3 — Client Dashboard
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/dashboard/metrics` | JWT (client) | Dashboard stats |
| GET | `/api/conversations` | JWT (client) | List conversations |
| GET | `/api/conversations/{id}` | JWT (client) | Conversation detail |
| POST | `/api/conversations/{id}/respond` | JWT (client) | Human agent response |
| POST | `/api/conversations/{id}/takeover` | JWT (client) | Take over from AI |
| GET | `/api/analytics` | JWT (client) | Analytics data |
| POST | `/api/knowledge/upload` | JWT (client) | Upload KB document |
| GET | `/api/knowledge/documents` | JWT (client) | List KB documents |
| DELETE | `/api/knowledge/documents/{id}` | JWT (client) | Delete KB document |
| GET | `/api/knowledge/search` | JWT (client) | Test KB search |
| GET | `/api/widget/config` | JWT (client) | Get widget config |
| PUT | `/api/widget/config` | JWT (client_owner) | Update widget config |
| GET | `/api/settings` | JWT (client) | Get settings |
| PUT | `/api/settings` | JWT (client_owner) | Update settings |

### Zone 4 — Super Admin
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/admin/clients` | JWT (super_admin) | List all clients |
| GET | `/api/admin/clients/{id}` | JWT (super_admin) | Client detail |
| PATCH | `/api/admin/clients/{id}/status` | JWT (super_admin) | Suspend/activate |
| GET | `/api/admin/analytics` | JWT (super_admin) | System-wide metrics |
| GET | `/api/admin/logs` | JWT (super_admin) | Audit logs |

### Zone 6 — Widget (Customer-Facing)
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/widget/{api_key}/config` | Widget API Key | Load widget config |
| POST | `/api/widget/{api_key}/session` | Widget API Key | Start chat session |
| POST | `/api/widget/{api_key}/chat` | Widget API Key | Send message |
| GET | `/api/widget/{api_key}/history/{session_id}` | Widget API Key | Reload chat |

---

## 14. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | FastAPI (Python) | REST API + WebSocket server |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Relational data storage |
| **Vector Database** | ChromaDB | RAG embedding storage with tenant isolation |
| **Sentiment Model** | `nlptown/bert-base-multilingual-uncased-sentiment` | Primary sentiment analysis (HuggingFace) |
| **Sentiment Fallback 1** | VADER (vaderSentiment) | English-focused fast fallback |
| **Sentiment Fallback 2** | TextBlob + Dictionary | Tertiary multilingual fallback |
| **LLM Provider** | OpenRouter API | Free-tier LLM access (Llama 3.3, Mistral) |
| **Embeddings** | TF-IDF / sentence-transformers (optional) | Document chunk vectorization |
| **Document Parsing** | PyPDF2, python-docx | PDF and DOCX extraction |
| **Auth** | JWT (python-jose) + bcrypt | Token auth + password hashing |
| **Real-time** | WebSocket (native FastAPI) | Live chat + escalation notifications |
| **Frontend** | Vanilla HTML/CSS/JS | Dashboard, admin panel, landing page |
| **Widget** | Vanilla JS (standalone bundle) | Embeddable chat widget |
| **Caching** | Redis (optional) | Session and response caching |

---

*End of FRD v3.0 — All zones specified, all requirements numbered, no open loops.*
