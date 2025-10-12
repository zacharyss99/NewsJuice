# services/retriever/server.py
from __future__ import annotations
import os, math, hashlib, datetime
from typing import Optional, List, Dict, Any

import psycopg
from pgvector.psycopg import register_vector, Vector
from sentence_transformers import SentenceTransformer

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------- Config (env) ----------
DB_URL = os.environ["DATABASE_URL"]  # e.g., postgresql://...@dbproxy:5432/newsdb

# How many chunks to pull from pgvector first, and how many unique docs to return.
FETCH_K = int(os.getenv("FETCH_K", "30"))
DOCS_K  = int(os.getenv("DOCS_K",  "3"))

# Gentle recency bias: 0 = off; try 0.03–0.07 to favor fresher items.
RECENCY_LAMBDA = float(os.getenv("RECENCY_LAMBDA", "0.0"))

# Name of your filter column for source; adjust if your table uses a different name.
SOURCE_FILTER_COLUMN = os.getenv("SOURCE_FILTER_COLUMN", "source_type")

# Embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

# ---------- Heavy deps (init once) ----------
# Tip: set SENTENCE_TRANSFORMERS_HOME=/data in compose to cache the model.
model = SentenceTransformer(EMBEDDING_MODEL)

# Single connection is fine for this setup. (For higher QPS, use a pool.)
conn = psycopg.connect(DB_URL, autocommit=True)
register_vector(conn)

# ---------- API models ----------
class RetrieveIn(BaseModel):
    query: str
    # optional filters (Manager may pass; users never see these)
    source: Optional[str] = None     # compared against SOURCE_FILTER_COLUMN
    after: Optional[str] = None      # YYYY-MM-DD (inclusive)
    before: Optional[str] = None     # YYYY-MM-DD (inclusive)

class Chunk(BaseModel):
    id: str
    text: str
    title: Optional[str] = None
    source: Optional[str] = None        # URL
    score: float
    published_at: Optional[str] = None  # ISO8601 string

class RetrieveOut(BaseModel):
    chunks: List[Chunk] = Field(default_factory=list)

# ---------- FastAPI app ----------
app = FastAPI(title="NewsJuice Retriever")

@app.get("/health")
def health():
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return {"ok": True, "fetch_k": FETCH_K, "docs_k": DOCS_K}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _doc_id_from_url(url: Optional[str]) -> str:
    if not url:
        return "no-url"
    return hashlib.md5(url.encode("utf-8")).hexdigest()

def _recency_weight(ts: Optional[datetime.datetime]) -> float:
    if ts is None or RECENCY_LAMBDA <= 0:
        return 1.0
    now = datetime.datetime.now(datetime.timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
    return math.exp(-RECENCY_LAMBDA * age_days)

@app.post("/retrieve", response_model=RetrieveOut)
def retrieve(body: RetrieveIn) -> RetrieveOut:
    try:
        q_emb = Vector(model.encode(body.query).tolist())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"embedding failure: {e}")

    # Build SQL with optional filters. Column names are fixed in SQL; values come from env/filters.
    where_parts = []
    params = [q_emb]
    param_idx = 2  # q_emb is param 1

    if body.source:
        where_parts.append(f"{SOURCE_FILTER_COLUMN} = %s")
        params.append(body.source)

    if body.after:
        where_parts.append("published_at >= %s")
        params.append(body.after)

    if body.before:
        where_parts.append("published_at <= %s")
        params.append(body.before)

    where_clause = " AND ".join(where_parts) if where_parts else "TRUE"

    # Vector similarity search with optional filters
    sql = f"""
        SELECT 
            id, content, title, source_link as source, 
            published_at, 1 - (embedding <=> %s) as score
        FROM chunks_vector 
        WHERE {where_clause}
        ORDER BY embedding <=> %s
        LIMIT %s
    """
    params.extend([q_emb, FETCH_K])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"query failure: {e}")

    # Deduplicate by source URL and apply recency weighting
    seen_docs = set()
    chunks = []
    
    for row in rows:
        doc_id = _doc_id_from_url(row[3])  # source URL
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        
        # Apply recency weighting if enabled
        published_at = row[4]
        if published_at:
            try:
                if isinstance(published_at, str):
                    published_at = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                recency_weight = _recency_weight(published_at)
                adjusted_score = row[5] * recency_weight
            except Exception:
                adjusted_score = row[5]
        else:
            adjusted_score = row[5]
        
        chunks.append(Chunk(
            id=str(row[0]),
            text=row[1],
            title=row[2],
            source=row[3],
            score=adjusted_score,
            published_at=row[4].isoformat() if row[4] else None
        ))
        
        if len(chunks) >= DOCS_K:
            break

    return RetrieveOut(chunks=chunks)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
