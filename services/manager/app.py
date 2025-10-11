# services/manager/app.py
from __future__ import annotations
import os, re, uuid, json, datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# -------------------- Config --------------------
RETRIEVER_URL  = os.getenv("RETRIEVER_URL")  # e.g., "http://retriever:8000/retrieve"
SUMMARIZER_URL = os.getenv("SUMMARIZER_URL") # e.g., "http://summarizer:8000/summarize" (optional)
HISTORY_PATH   = os.getenv("HISTORY_PATH", "/data/user_history.jsonl")

if not RETRIEVER_URL:
    raise RuntimeError("RETRIEVER_URL not set")

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20.0"))

# -------------------- App -----------------------
app = FastAPI(title="NewsJuice Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Models --------------------
class QueryRequest(BaseModel):
    """Client request to /ask (user never controls k)."""
    user_id: str
    query: str

class Chunk(BaseModel):
    id: str
    text: str
    title: Optional[str] = None
    source: Optional[str] = None         # URL
    score: Optional[float] = None
    published_at: Optional[str] = None   # ISO string if available

class ManagerResponse(BaseModel):
    trace_id: str
    summary: Optional[str] = None
    sources: List[Chunk] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

# -------------------- Facet parser --------------
# Inline facets the user *may* type; all optional.
# We do NOT parse k; retrieval fan-out is a system knob.
FACET_RX = {
    "source": re.compile(r'\bsource:(?P<q>"[^"]+"|\S+)', re.I),
    "after":  re.compile(r'\b(after|since):(?P<q>\d{4}-\d{2}-\d{2})', re.I),
    "before": re.compile(r'\b(before|until):(?P<q>\d{4}-\d{2}-\d{2})', re.I),
    "tags":   re.compile(r'\b(tag|tags|subject):(?P<q>"[^"]+"|[\w,-]+)', re.I),
}

def parse_query(raw: str) -> tuple[str, Dict[str, Any]]:
    """
    Extract optional filters (facets) from the user's text and return:
      clean_text: str   -> for embedding
      facets: dict      -> forwarded to Retriever as filters
    """
    text = raw
    facets: Dict[str, Any] = {}
    for key, rx in FACET_RX.items():
        matches = list(rx.finditer(text))
        if not matches:
            continue
        # last-one-wins if repeated
        val = matches[-1].group("q").strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        if key == "tags":
            facets[key] = [t.strip() for t in re.split(r'[,\s]+', val) if t.strip()]
        else:
            facets[key] = val
        # strip all facet tokens from the text
        text = rx.sub("", text)
    clean_text = re.sub(r'\s{2,}', ' ', text).strip()
    return clean_text, facets

# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "retriever": RETRIEVER_URL, "summarizer": bool(SUMMARIZER_URL)}

# -------------------- Main endpoint -------------
@app.post("/ask", response_model=ManagerResponse)
async def ask(req: QueryRequest):
    trace_id = str(uuid.uuid4())

    # 1) Parse facets out of the free-text query
    clean_text, facets = parse_query(req.query)

    # 2) Call Retriever for relevant chunks (deduped by article)
    retrieve_payload = {
        "query": clean_text,
        # optional filters (retriever ignores missing)
        "source": facets.get("source"),
        "after":  facets.get("after"),
        "before": facets.get("before"),
        "tags":   facets.get("tags"),
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            r = await client.post(RETRIEVER_URL, json=retrieve_payload)
            r.raise_for_status()
            rj = r.json()
            chunks = [Chunk(**c) for c in rj.get("chunks", [])]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"retriever error: {e}")

        # 3) Call Summarizer for a grounded answer + citations (optional)
        summary: Optional[str] = None
        citations: Optional[List[Dict[str, Any]]] = None
        summarize_err: Optional[str] = None

        if SUMMARIZER_URL:
            try:
                s = await client.post(SUMMARIZER_URL, json={
                    "mode": "answer",
                    "query": clean_text,
                    "chunks": [c.model_dump() for c in chunks],
                    "max_sentences": 6,
                })
                s.raise_for_status()
                sj = s.json()
                summary   = sj.get("summary")
                citations = sj.get("citations")
            except Exception as e:
                summarize_err = str(e)

    # 4) Log the interaction (append-only, non-fatal)
    log_event = {
        "trace_id": trace_id,
        "ts": datetime.datetime.utcnow().isoformat(),
        "user_id": req.user_id,
        "query_raw": req.query,
        "query_clean": clean_text,
        "facets": facets,
        "retrieved_ids": [c.id for c in chunks],
        "summary_len": (len(summary) if summary else 0),
        "citations_count": (len(citations) if citations else 0),
    }
    try:
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_event) + "\n")
    except Exception:
        pass  # never break the request on logging issues

    # 5) Build response
    meta: Dict[str, Any] = {"facets": facets}
    if citations:
        meta["citations"] = citations
    if not summary and SUMMARIZER_URL:
        meta["note"] = f"Summary unavailable ({summarize_err})"

    return ManagerResponse(trace_id=trace_id, summary=summary, sources=chunks, meta=meta)
