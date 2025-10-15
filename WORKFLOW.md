# NewsJuice Podcast Generator - Complete Workflow

## Overview
This system implements a two-phase workflow for generating personalized news podcasts:

1. **Data Ingestion Phase**: Scrape articles → Chunk & Embed → Store in Vector DB
2. **Podcast Generation Phase**: User Query → Retrieve Relevant Chunks → Generate Podcast

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│   Scraper   │───▶│   articles  │───▶│     Loader      │
└─────────────┘    └─────────────┘    └─────────────────┘
                                              │
                                              ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chatter   │◀───│    Retriever    │◀───│ chunks_vector   │
└─────────────┘    └─────────────────┘    └─────────────────┘
       │
       ▼
┌─────────────┐
│ Gemini API  │
└─────────────┘
```

## Phase 1: Data Ingestion

### Step 1: Scrape Articles
```bash
make scrape
```
- Scrapes Harvard Gazette and Crimson articles
- Stores articles in `articles` table
- Checks for duplicates using `PostgresDBManager`

### Step 2: Load & Embed Articles
```bash
make load
```
- Reads articles from `articles` table
- Chunks articles using semantic chunking (Vertex AI)
- Embeds chunks using `sentence-transformers/all-mpnet-base-v2`
- Stores chunks and embeddings in `chunks_vector` table

### Complete Data Pipeline
```bash
make run  # Runs both scrape and load
```

## Phase 2: Podcast Generation

### Start Interactive Podcast Generator
```bash
make chat
```

### Workflow Steps:
1. **User Input**: Enter user_id and query
2. **Retrieval**: Retriever embeds query and searches `chunks_vector` for top 2 chunks via cosine similarity
3. **Context Building**: Chatter receives chunks and builds context
4. **Podcast Generation**: Gemini API generates podcast-style response using query + chunks as context
5. **Output**: Personalized news podcast response

## Database Tables

### `articles`
- Stores raw scraped articles
- Fields: `id`, `author`, `title`, `summary`, `content`, `source_link`, `source_type`, `fetched_at`, `published_at`, `vflag`, `article_id`

### `chunks_vector`
- Stores processed article chunks with embeddings
- Fields: `id`, `author`, `title`, `summary`, `content`, `source_link`, `source_type`, `fetched_at`, `published_at`, `chunk`, `chunk_index`, `embedding`, `article_id`

## Services

### Scraper Service
- **Input**: None (scrapes from web)
- **Output**: Articles stored in `articles`
- **Key Features**: Duplicate detection, database integration

### Loader Service
- **Input**: Articles from `articles`
- **Output**: Chunks and embeddings in `chunks_vector`
- **Key Features**: Semantic chunking, vector embeddings

### Retriever Service
- **Input**: User query
- **Output**: Top 2 relevant chunks with similarity scores
- **Key Features**: Cosine similarity search, configurable limit

### Chatter Service
- **Input**: User query and user_id
- **Output**: Podcast-style response
- **Key Features**: Integration with retriever, Gemini API, conversation logging

## Usage Examples

### 1. Full Pipeline
```bash
# Build and start database proxy
make up-proxy

# Run complete data ingestion
make run

# Start podcast generation
make chat
```

### 2. Individual Steps
```bash
# Just scrape articles
make scrape

# Just load articles
make load

# Just test retrieval
make retrieve

# Just start chat
make chat
```

### 3. Clean Restart
```bash
make clean  # Stops all containers
make run    # Fresh start
```

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_REGION`: GCP region
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key

### Table Names (production)
- `ARTICLES_TABLE_NAME = "articles"`
- `VECTOR_TABLE_NAME = "chunks_vector"`

## Key Features

✅ **Database Integration**: Direct PostgreSQL storage, no file dependencies  
✅ **Semantic Chunking**: Uses Vertex AI for intelligent text splitting  
✅ **Vector Search**: Cosine similarity for relevant chunk retrieval  
✅ **Podcast Generation**: Gemini API creates engaging podcast-style responses  
✅ **Conversation Logging**: All interactions stored in `llm_conversations` table  
✅ **Duplicate Prevention**: Scraper checks for existing articles  
✅ **Modular Design**: Each service can run independently  

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure `dbproxy` is running (`make up-proxy`)
2. **No Articles Found**: Run data ingestion first (`make run`)
3. **Gemini API Errors**: Check service account credentials
4. **Import Errors**: Ensure all services are built (`make build`)

### Logs
- Check container logs: `docker compose logs <service_name>`
- Database logs: `docker compose logs dbproxy`
- Service-specific logs are printed to stdout
