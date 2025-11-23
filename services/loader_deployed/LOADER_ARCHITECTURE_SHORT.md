# Loader Service - Technical Architecture

## Short description

The Loader service is a Cloud Run application that ingests news articles from the SCRAPER service, cuts them into semantic chunks with vector embeddings, and stores them in PostgreSQL for the NewsJuice platform.

---

## System Architecture

```
Harvard related web news sources → Loader service (Cloud Run) → PostgreSQL (Cloud SQL + pgvector)
              ↓
         Cloud Scheduler (every 24 hours)
```

### Key Components

1. **Cloud Run service**: Stateless containerized application
2. **Cloud SQL (PostgreSQL + pgvector)**: Article storage with vector search
3. **Cloud Scheduler**: Automated periodic ingestion (every 24 hours)
4. **Google Cloud Storage**: DVC data versioning backend

---

## Technology Stack

**Runtime**: Python 3.12
**Framework**: FastAPI
**Database**: PostgreSQL with pgvector extension
**Package Manager**: UV
**Container**: Docker

**Core Dependencies**:
- `langchain` - Text processing pipeline
- `psycopg[binary]` + `pgvector` - Database operations

---

## Data Processing Pipeline

```
1. Detect New Articles
   ↓ Query GCS SQL database **articles** table for unprocessed articles

2. Content Extraction
   ↓ Fetch unprocessed articles

3. Chunking
   ↓ Split text using strategy (Recursive)

5. Embedding Generation
   ↓ Generate vectors using VertexAI (model: XYZ)

6. Storage
   ↓ Store chunks + embeddings in PostgreSQL (pgvector) in **chunks_vector" table
```

---

## Chunking Strategies

### CharacterChunking
- Fixed-size character-based splitting
- Configurable chunk size and overlap
- Fast, deterministic

### RecursiveChunking
- Hierarchical splitting (paragraphs → sentences)
- Preserves semantic boundaries
- Better context retention

### SemanticChunking
- Hierarchical splitting (paragraphs → sentences)
- Preserves semantic boundaries
- Better context retention


**Selection via**: `get_chunking_strategy(strategy: str)`

---

## Database Schema

```sql
-- Articles
CREATE TABLE articles (

);

-- Chunks with vector embeddings
CREATE TABLE chunks_vector (

);

```

---

## Cloud Run Deployment

### Configuration

```yaml
Service: loader-service
Region: us-central1
Timeout: 3600s (60 min max)
Memory: 4Gi
CPU: 2 cores (always allocated)
Concurrency: 1
Max Instances: 10
```

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE
GOOGLE_CLOUD_PROJECT=newsjuice-123456
CHUNKING_STRATEGY=recursive
LOG_LEVEL=INFO
```

### Deployment Command

```bash
gcloud run deploy loader-service \
  --source . \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --cpu-always-allocated \
  --max-instances 10 \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --set-env-vars DATABASE_URL=${DATABASE_URL}
```

---

## Scheduling

**Cloud Scheduler Job**:
```bash
gcloud scheduler jobs update http article-loader-job \
  --location us-central1 \
  --schedule="0 */2 * * *"  # Every 2 hours
  --uri="https://loader-service-xxx.run.app/api/v1/ingest" \
  --http-method=POST \
  --oidc-service-account-email=scheduler@PROJECT.iam.gserviceaccount.com
```

**Schedule**: Every 2 hours at :00 (00:00, 02:00, 04:00, etc.)

---

## API Endpoints

```
POST /api/v1/ingest
  - Detects new articles from GCS SQL database
  - Processes and stores with embeddings
  - Returns: { "processed": N, "errors": [] }

GET /health
  - Health check endpoint
  - Returns: { "status": "healthy" }
```

---

## Known Issue & Mitigation

### Problem
Service stops after processing ~50-60 articles without error.

### Root Cause
Cloud Run request timeout (default 5-15 min) or memory limits.

### Solutions Implemented

1. **Increased Timeout**: 3600s (60 min max)
2. **Increased Memory**: 4Gi
3. **CPU Always Allocated**: Prevents throttling
4. **Batch Processing**: Limit articles per run

### Recommended Architecture Update

**Option A: Batch with Continuation**
```python
@app.post("/api/v1/ingest")
async def ingest(batch_size: int = 50):
    articles = get_new_articles(limit=batch_size)
    process_articles(articles)
    return {"processed": len(articles), "has_more": len(articles) == batch_size}
```

**Option B: Cloud Tasks Queue**
- Queue each article as separate task
- Process independently with retries
- Better fault tolerance

---

## Performance Characteristics

**Throughput**: ~50-60 articles per run (~10-15 min)
**Memory Usage**: ~2-3 Gi (embeddings + model loading)
**Database Connections**: Pooled (max 10)
**Embedding Latency**: ~500ms per chunk

---

## Monitoring

### Cloud Logging Query
```bash
gcloud logging read "resource.type=cloud_run_revision
  AND resource.labels.service_name=loader-service" \
  --limit=100 \
  --format=json
```

### Key Metrics to Monitor
- Request duration (should be < 3600s)
- Memory utilization (should be < 4Gi)
- Articles processed per run
- Error rates
- Database connection pool exhaustion

---

## Testing

Testing is set up in separate Service folder "loader_testing"

### Local Testing
```bash
cd services/loader_faster
uv sync
pytest tests/unit/ -v --cov=api

# System tests with Docker
docker-compose -f docker-compose.test.yml up --build
```

### CI/CD
GitHub Actions workflow (`.github/workflows/ci-unit_only_loader.yaml`):
- Triggers on changes to `services/loader_faster/**`
- Runs unit tests with coverage
- Python 3.12 environment
- UV package management

---

## Security

- **No API Keys in Code**: Environment variables only
- **Cloud SQL Private IP**: Accessed via Unix socket
- **Service Account**: Minimal permissions (Cloud SQL Client, Storage Admin)
- **Non-root Container**: Security best practice
- **OIDC Authentication**: Scheduler → Cloud Run

---

## Data Versioning

**DVC (Data Version Control)**:
- Exports key tables (articles, chunks_vector) as snapshot
- Tracks PostgreSQL database exports
- Backend: Google Cloud Storage
- Enables reproducibility of training data
- Version control for article datasets

```bash
# Export database snapshot
dvc add data/exports/db_export_YYYYMMDD.sql
dvc push
```

---

## Future Enhancements

### Immediate Priorities
- [ ] Implement proper batch processing (50 articles/batch)
- [ ] Add Cloud Tasks for article queue
- [ ] Improve error handling and retry logic
- [ ] Add deduplication logic

### Long-term Improvements
- [ ] Streaming ingestion for real-time feeds
- [ ] Multi-language embedding models
- [ ] Incremental article updates (detect changes)
- [ ] GraphQL API for flexible queries
- [ ] Distributed tracing (Cloud Trace)

---

## Directory Structure

```
services/loader_faster/
├── src/api-service/api/
│   ├── loader.py              # Core chunking logic
│   └── __init__.py
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── system/                # System tests
├── Dockerfile                 # Cloud Run container
├── pyproject.toml            # Dependencies
└── .github/workflows/        # CI/CD
```

---

## Quick Reference

**Deploy**: `gcloud run deploy loader-service --source .`
**Logs**: `gcloud logging tail "resource.labels.service_name=loader-service"`
**Schedule**: `gcloud scheduler jobs update http article-loader-job --schedule="0 */2 * * *"`
**Test**: `pytest tests/unit/ -v`

---

**Version**: 1.0
**Last Updated**: November 22, 2025
**Owner**: Christian Michel
**Repository**: `zsardisantos/ac215_NewsJuice`
**Service**: `services/loader_faster`
