# CLAUDE.md - Egyptian Law RAG System

## Project Overview

This is an **Egyptian Law Retrieval-Augmented Generation (RAG) System** - an intelligent legal assistant that answers Arabic legal questions using Egyptian and multi-country law documents. It combines hybrid search (dense + sparse vectors), cross-encoder reranking, and LLM generation to provide accurate legal answers with citations.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI 0.115.0+ with Uvicorn ASGI server
- **Vector Database**: Qdrant (hybrid dense + sparse vectors)
- **Session Storage**: Redis
- **Embedding Model**: Qwen/Qwen3-Embedding-0.6B (1024-dim)
- **Sparse Encoder**: Qdrant/bm25
- **Reranker**: Qwen/Qwen3-Reranker-0.6B
- **LLM**: Google Gemini (gemini-2.5-flash)
- **PDF Processing**: PyMuPDF

## Project Structure

```
law-rag-backend/
├── app/
│   ├── main.py                 # FastAPI entry point with lifespan management
│   ├── api/
│   │   ├── routes/             # Endpoints: query, ingest, laws, sessions, health
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── deps.py             # Dependency injection
│   ├── core/
│   │   └── config.py           # Settings, SupportedCountry & LawType enums
│   ├── db/
│   │   ├── qdrant_client.py    # QdrantManager singleton
│   │   ├── redis_client.py     # RedisManager for sessions
│   │   └── factory.py          # CollectionFactory for Qdrant collections
│   ├── pipelines/
│   │   ├── base.py             # Pipeline and PipelineStep base classes
│   │   ├── ingestion/          # 7-step PDF ingestion pipeline
│   │   │   ├── pipeline.py
│   │   │   ├── models.py
│   │   │   └── steps/          # PDF→Text→ArticleSplit→Metadata→DenseEmbed→SparseEncode→Store
│   │   └── query/              # 6-step query pipeline
│   │       ├── pipeline.py
│   │       ├── models.py
│   │       └── steps/          # Preprocess→DualEncode→HybridRetrieve→Rerank→Generate→Format
│   ├── services/               # ML model services (singletons)
│   │   ├── embedding_service.py
│   │   ├── sparse_encoder_service.py
│   │   ├── reranker_service.py
│   │   ├── llm_service.py
│   │   └── session_service.py
│   └── utils/
│       ├── patterns.py         # ArticlePatterns for Arabic legal text
│       ├── arabic.py           # ArabicNormalizer, ArabicNumerals
│       ├── device.py           # GPU/CPU detection
│       └── logger.py
├── scripts/
│   ├── ingest_all.py           # Batch ingestion CLI
│   ├── verify_setup.py         # Health check script
│   └── download_models.py      # Model downloading utility
├── law_material/               # PDF storage by country
│   └── Egyptian/               # Egyptian law PDFs
├── docker-compose.yml          # Qdrant + Redis + App orchestration
├── docker-compose.cpu.yml      # CPU-only variant
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Common Commands

```bash
# Setup
cd law-rag-backend
cp .env.example .env   # Add GOOGLE_API_KEY

# Docker (recommended)
docker compose up --build              # With GPU
docker compose -f docker-compose.cpu.yml up --build  # CPU only

# Local development
pip install -r requirements.txt
python scripts/verify_setup.py         # Health check
python scripts/ingest_all.py --country egypt  # Ingest PDFs

# API query example
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "ما هي عقوبة السرقة؟", "country": "egypt"}'
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/query` | Ask legal question |
| POST | `/api/v1/ingest` | Upload PDF for ingestion |
| GET | `/api/v1/laws` | List country collections |
| GET | `/api/v1/laws/{country}` | Get country details |
| DELETE | `/api/v1/laws/{country}` | Delete country laws |
| POST | `/api/v1/laws/{country}/reset` | Reset collection |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions/{id}` | Get session history |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |

## Key Patterns & Conventions

### Architecture
- **Singleton Pattern**: All services (EmbeddingService, RerankerService, etc.)
- **Pipeline Pattern**: Composable steps for ingestion and query flows
- **Dependency Injection**: FastAPI `Depends()` for loose coupling
- **Factory Pattern**: CollectionFactory for Qdrant collection management

### Code Style
- Type hints throughout (Pydantic models, Optional, List[Dict])
- Async/await in FastAPI endpoints
- Comprehensive logging with emoji indicators
- Docstrings on all major classes/functions
- Environment-based config via pydantic-settings

### Arabic Text Handling
- `ArticlePatterns` class detects مادة (article) in multiple formats
- `ArabicNormalizer` handles diacritics, tatweel, alef variants
- `ArabicNumerals` converts between Arabic/English numerals
- Search vs display normalization modes

### Supported Countries
Egypt, Jordan, UAE, Saudi Arabia, Kuwait (enum in `config.py`)

### Law Types
Criminal, Civil, Commercial, Economic, Administrative, Arbitration, Labor, Personal Status

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | **Required** |
| `QDRANT_HOST` | Qdrant hostname | localhost |
| `QDRANT_PORT` | Qdrant port | 6333 |
| `REDIS_HOST` | Redis hostname | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `EMBEDDING_MODEL` | Dense model | Qwen/Qwen3-Embedding-0.6B |
| `RERANKER_MODEL` | Reranker model | Qwen/Qwen3-Reranker-0.6B |
| `LLM_MODEL` | Gemini model | gemini-2.5-flash |
| `HYBRID_PREFETCH` | Results before reranking | 25 |
| `RERANK_TOP_K` | Final results after reranking | 5 |
| `SESSION_TTL` | Session expiration (seconds) | 86400 |

## Adding New Countries

1. Create folder: `law_material/{CountryName}/`
2. Add PDFs with Arabic law text
3. Update `COUNTRY_LAWS` in `scripts/ingest_all.py`
4. Run: `python scripts/ingest_all.py --country {country_code}`

## Article Pattern Recognition

The system recognizes these مادة (article) formats:
- `مادة ١٢٣` - Arabic numerals
- `مادة 123` - Western numerals
- `مادة (١٢٣)` - Parentheses
- `مادة [10]` - Square brackets
- `المادة ١٢٣` - With definite article
