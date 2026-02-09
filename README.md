# Egyptian Law RAG System

A professional Retrieval-Augmented Generation (RAG) system for Egyptian legal documents with hybrid search, cross-encoder reranking, and multi-country support.

> **Admin GUI**: Once the server is running, open [http://localhost:8000/static/admin.html](http://localhost:8000/static/admin.html) to access the built-in admin panel (Dashboard, Ingest, Chat, Sessions, Chunks).

## Features

- 🔍 **Hybrid Search**: Dense (Qwen3-Embedding) + Sparse (BM25) with RRF fusion
- 🎯 **Cross-Encoder Reranking**: Qwen3-Reranker for precise relevance scoring
- 📜 **Article-Based Chunking**: Splits on مادة patterns for accurate citations
- 🌍 **Multi-Country Support**: Egypt, Jordan, UAE, Saudi Arabia, Kuwait
- 💬 **Session Management**: Redis-backed conversation history
- �️ **Admin GUI**: Built-in web interface for dashboard, ingestion, chat, sessions, and chunk browsing
- �🐳 **Docker Ready**: Single command deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ingestion Pipeline                           │
├─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┤
│ PDF     │ Text    │ Article │Metadata │ Dense   │ Sparse  │ Qdrant │
│ Loader  │ Extract │ Split   │ Enrich  │ Embed   │ Encode  │ Store  │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         Query Pipeline                              │
├───────────┬───────────┬───────────┬───────────┬───────────┬────────┤
│ Preproc   │ Dual      │ Hybrid    │ Reranker  │ Gemini    │ Format │
│           │ Encoder   │ Retriever │           │ Generator │        │
└───────────┴───────────┴───────────┴───────────┴───────────┴────────┘
```

## Quick Start

### 1. Clone and Configure

```bash
cd law-rag-backend
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
```

### 2. Start Services

```bash
# With GPU (recommended)
docker compose up --build

# CPU only
docker compose -f docker-compose.cpu.yml up --build
```

### 3. Ingest Laws

```bash
# Wait for services to be ready
python scripts/verify_setup.py

# Ingest all Egyptian laws
python scripts/ingest_all.py
```

### 4. Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "ما هي عقوبة السرقة في القانون المصري؟", "country": "egypt"}'
```

### 5. Admin GUI

Open [http://localhost:8000/static/admin.html](http://localhost:8000/static/admin.html) in your browser to access the built-in admin panel with:

- **Dashboard** — System stats and overview
- **Ingest** — Upload and ingest law PDFs
- **Chat** — Ask legal questions interactively
- **Sessions** — View and manage conversation history
- **Chunks** — Browse indexed document chunks

## API Endpoints

### Query
- `POST /api/v1/query` - Ask a legal question

### Ingest
- `POST /api/v1/ingest` - Upload and ingest a law PDF

### Laws
- `GET /api/v1/laws` - List all country collections
- `GET /api/v1/laws/{country}` - Get country details
- `DELETE /api/v1/laws/{country}` - Delete country laws
- `POST /api/v1/laws/{country}/reset` - Reset collection

### Sessions
- `POST /api/v1/sessions` - Create session
- `GET /api/v1/sessions/{id}` - Get session history
- `DELETE /api/v1/sessions/{id}` - Delete session

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

## Models

| Component | Model | Dimension |
|-----------|-------|-----------|
| Dense Embedding | Qwen/Qwen3-Embedding-0.6B | 1024 |
| Sparse Encoder | Qdrant/bm25 | Variable |
| Reranker | Qwen/Qwen3-Reranker-0.6B | N/A |
| LLM | gemini-2.5-flash | N/A |

## Project Structure

```
law-rag-backend/
├── app/
│   ├── api/               # FastAPI routes & schemas
│   ├── core/              # Settings & configuration
│   ├── db/                # Qdrant & Redis clients
│   ├── pipelines/         # Ingestion & Query pipelines
│   ├── services/          # ML model services
│   ├── utils/             # Utilities
│   └── main.py            # App entry point
├── scripts/               # CLI scripts
├── docker-compose.yml     # Container orchestration
├── Dockerfile             # App container
└── requirements.txt       # Python dependencies
```

## Article Patterns

The system recognizes these مادة (article) patterns:

- `مادة ١٢٣` - Arabic numerals
- `مادة 123` - Western numerals
- `مادة (١٢٣)` - Parentheses
- `مادة [10]` - Square brackets
- `المادة ١٢٣` - With definite article

## Adding New Countries

1. Create folder in `app/law_material/{CountryName}/`
2. Add PDFs with Arabic law text
3. Update `COUNTRY_LAWS` in `scripts/ingest_all.py`
4. Run ingestion for new country

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | Required |
| `QDRANT_HOST` | Qdrant hostname | qdrant |
| `REDIS_HOST` | Redis hostname | redis |
| `EMBEDDING_MODEL` | Dense model | Qwen/Qwen3-Embedding-0.6B |
| `RERANKER_MODEL` | Reranker model | Qwen/Qwen3-Reranker-0.6B |

## License

MIT
