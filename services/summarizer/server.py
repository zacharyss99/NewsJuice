from __future__ import annotations
import os, textwrap
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from groq import Groq

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
if "GROQ_API_KEY" not in os.environ:
    raise RuntimeError("GROQ_API_KEY not set")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

app = FastAPI(title="NewsJuice Summarizer (Groq)")

class Chunk(BaseModel):
    id: str
    text: str
    title: Optional[str] = None
    source: Optional[str] = None  # URL
    score: Optional[float] = None

class SummarizeIn(BaseModel):
    mode: str = Field(default="answer", description='"answer" or "history"')
    query: str
    chunks: List[Chunk] = Field(default_factory=list)
    max_sentences: int = Field(default=6, ge=1, le=10)
    # used only for history mode
    limit_chars: int = 240

class AnswerOut(BaseModel):
    summary: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)

class HistoryOut(BaseModel):
    history_summary: str

SYSTEM_PROMPT = (
    "You are NewsJuice Answerer. Synthesize an accurate, concise answer using only the provided CONTEXT.\n"
    "Rules:\n"
    "• Do not introduce facts that are not in CONTEXT.\n"
    "• Write a clear answer in 4–6 sentences (max).\n"
    "• Add bracket citations like [1], [2] after sentences that use those chunks.\n"
    "• If the context is insufficient, say so briefly.\n"
)

def build_context(chunks: List[Chunk], max_chars_per_chunk: int = 1200) -> str:
    lines = []
    for i, c in enumerate(chunks, start=1):
        snippet = c.text.strip().replace("\n", " ")
        snippet = textwrap.shorten(snippet, width=max_chars_per_chunk, placeholder="…")
        lines.append(
            f"[{i}] id={c.id}\n"
            f"Title: {c.title or 'N/A'}\n"
            f"URL: {c.source or 'N/A'}\n"
            f"Text: {snippet}\n"
        )
    return "\n".join(lines)

def build_citations(chunks: List[Chunk]) -> List[Dict[str, Any]]:
    cites = []
    for i, c in enumerate(chunks, start=1):
        cites.append({"n": i, "id": c.id, "url": c.source, "title": c.title})
    return cites

@app.get("/health")
def health():
    return {"ok": True, "model": GROQ_MODEL}

@app.post("/summarize", response_model=AnswerOut | HistoryOut)
def summarize(body: SummarizeIn):
    # No context? Respond gracefully.
    if len(body.chunks) == 0:
        if body.mode == "history":
            return HistoryOut(history_summary=textwrap.shorten(f'Query: "{body.query}" (no context)', width=body.limit_chars))
        return AnswerOut(summary="I couldn’t find enough context to answer confidently.", citations=[])

    if body.mode == "history":
        titles = [c.title for c in body.chunks if c.title][:3]
        srcs   = [c.source for c in body.chunks if c.source][:3]
        parts = [f'Query: "{body.query}"']
        if titles: parts.append("Top titles: " + "; ".join(titles))
        if srcs:   parts.append("Sources: " + "; ".join(srcs))
        text = " | ".join(parts)
        return HistoryOut(history_summary=textwrap.shorten(text, width=body.limit_chars, placeholder="…"))

    # mode == "answer"
    try:
        ctx = build_context(body.chunks)
        user_prompt = (
            f"QUESTION:\n{body.query}\n\n"
            f"CONTEXT (numbered source excerpts):\n{ctx}\n\n"
            f"Write up to {body.max_sentences} sentences. Include bracket citations [n] that refer to the numbered context."
        )
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        answer = resp.choices[0].message.content.strip()
        citations = build_citations(body.chunks)
        return AnswerOut(summary=answer, citations=citations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"summarizer failure: {e}")
