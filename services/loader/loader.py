'''

loader service

* Reads from "articles" database in DB "newsbd" (all "new" articles i.e. vflag =0)
* Chunks the articles and embeds the chunks
* Loads to the "chunks_vector" table in the DB "newsdb"

* Chunking (semantic version) uses Vertex api for embedding 
* Final chunks will be embedded with "sentence-transformers/all-mpnet-base-v2" 
so it the same embedding model as used for the retriever service


* NOTE: FOR TESTING USE:  
#ARTICLES_TABLE_NAME = "articles_test"
#VECTOR_TABLE_NAME = "chunks_vector_test"
'''

# ###
ARTICLES_TABLE_NAME = "articles"
#ARTICLES_TABLE_NAME = "articles_test"

VECTOR_TABLE_NAME = "chunks_vector"
#VECTOR_TABLE_NAME = "chunks_vector_test"


import uuid
import pandas as pd
import psycopg
from psycopg import sql
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.genai import types

#from google.cloud import storage

#BUCKET_NAME = "newsjuice-data-exchange"

from typing import List


# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker

#from vertex_embeddings import VertexEmbeddings
#from langchain_openai import OpenAIEmbeddings  # or another embedding provider
#from langchain_huggingface import HuggingFaceEmbeddings

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Load the jsonl file from /data/news.jsonl
import json, sys, pathlib
#PATH_TO_NEWS= pathlib.Path("/data/news.jsonl")  # for M2 docker-compose version
#PATH_TO_CHUNKS = pathlib.Path("/data/chunked_articles")
#path = pathlib.Path("./news.jsonl")  # for standalone version


EMBEDDING_MODEL = "text-embedding-004"
GENERATIVE_MODEL = "gemini-2.0-flash-001"
EMBEDDING_DIM = 768 #256

# Parameter for character chunking 
CHUNK_SIZE_CHAR = 350
CHUNK_OVERLAP_CHAR = 20
# Parameter for recursive chunking 
CHUNK_SIZE_RECURSIVE = 350


import os
DB_URL = os.environ["DATABASE_URL"]       
#DB_URL= "postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" # for use with container
#DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
#TIMEOUT = 10.0
#USER_AGENT = "minimal-rag-ingest/0.1"

from pgvector.psycopg import register_vector


class VertexEmbeddings:
    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        if not project:
            raise RuntimeError("Set GOOGLE_CLOUD_PROJECT")
        # Uses ADC via GOOGLE_APPLICATION_CREDENTIALS or gcloud
        self.client = genai.Client(vertexai=True, project=project, location=location)
        self.model = EMBEDDING_MODEL
        self.dim = EMBEDDING_DIM

    def _embed_one(self, text: str) -> List[float]:
        resp = self.client.models.embed_content(
            model=self.model,
            contents=[text],  # one at a time to avoid 20k token limit
            config=types.EmbedContentConfig(output_dimensionality=self.dim),
        )
        return resp.embeddings[0].values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)
# Chunking function

def chunk_embed_load(method='char-split'):
    #PATH_TO_CHUNKS.mkdir(parents=True, exist_ok=True)

    conn = psycopg.connect(DB_URL, autocommit=True)

    register_vector(conn)

    cur = conn.cursor()

    # Fetch new articles from articles table (vflag = 0)
    cur.execute(
        sql.SQL("""
            SELECT id, author, title, summary, content,
                source_link, source_type, fetched_at, published_at,
                vflag, article_id
            FROM {}
            WHERE vflag = 0;
        """).format(sql.Identifier(ARTICLES_TABLE_NAME))
)


    rows = cur.fetchall()

    # Prepare semantic splitter once (if requested)
    sem_splitter = None
    if method == "semantic-split":
        emb = VertexEmbeddings()
        sem_splitter = SemanticChunker(embeddings=emb)

    for i, row in enumerate(rows, start=1):
        (id, author, title, summary, content,
            source_link, source_type, fetched_at, published_at,
            vflag, article_id) = row

        # --- Chunking ---
        if method == "char-split":
            text_splitter = CharacterTextSplitter(
                chunk_size=CHUNK_SIZE_CHAR,
                chunk_overlap=CHUNK_OVERLAP_CHAR,
                separator=None,
                strip_whitespace=False,
            )
            docs = text_splitter.create_documents([content or ""])

        elif method == "recursive-split":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE_RECURSIVE
            )
            docs = text_splitter.create_documents([content or ""])

        elif method == "semantic-split":
            if sem_splitter is None:
                raise RuntimeError("Semantic splitter not initialized")
            docs = sem_splitter.create_documents([content or ""])

        else:
            raise ValueError(f"Unknown method: {method}")

        text_chunks = [d.page_content for d in docs]
        print(f"[{i}/{len(rows)}] article_id={article_id} → {len(text_chunks)} chunks")

        # --- Build rows to insert ---
        df = pd.DataFrame(text_chunks, columns=["chunk"])
        df["author"] = author
        df["title"] = title
        df["summary"] = summary
        df["content"] = content
        df["source_link"] = source_link
        df["source_type"] = source_type
        df["fetched_at"] = fetched_at
        df["published_at"] = published_at
        df["chunk_index"] = range(len(df))
        df["article_id"] = article_id
        # Final embeddings (align with retrieval model)
        df["embedding"] = [model.encode(t).tolist() for t in df["chunk"]] # sentence-transformers/all-mpnet-base-v2
        # --- Insert chunks ---
        inserted = 0
        for _, r in df.iterrows():
            # --- INSERT chunk row into vector table ---
            insert_sql = sql.SQL("""
                INSERT INTO {} (
                    author, title, summary, content,
                    source_link, source_type, fetched_at, published_at,
                    chunk, chunk_index, embedding, article_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """).format(sql.Identifier(VECTOR_TABLE_NAME))

            cur.execute(
                insert_sql,
                (
                    r["author"],
                    r["title"],
                    r["summary"],
                    r["content"],
                    r["source_link"],
                    r["source_type"],
                    r["fetched_at"],
                    r["published_at"],
                    r["chunk"],
                    int(r["chunk_index"]),
                    r["embedding"],     # ⚠️ pass the Python list directly if pgvector
                    r["article_id"],
                )
            )

        # --- UPDATE article as processed ---
        update_sql = sql.SQL("""
            UPDATE {} 
            SET vflag = 1 
            WHERE article_id = %s
        """).format(sql.Identifier(ARTICLES_TABLE_NAME))

        cur.execute(update_sql, (article_id,))

    cur.close()
    conn.close()

def main():

    chunk_embed_load("semantic-split")

if __name__ == "__main__":
    main()

