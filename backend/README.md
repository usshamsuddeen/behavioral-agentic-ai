# Behavioral Agentic AI - Backend

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

### 3. Seed Demo Data
```bash
python seed_data.py
```

### 4. Run Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. View API Docs
Open: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/{id}` | Get conversation |
| POST | `/api/messages` | Send message |
| POST | `/api/analyze/sentiment` | Analyze text sentiment |
| POST | `/api/analyze/language` | Detect language |
| GET | `/api/analytics/dashboard` | Dashboard metrics |
