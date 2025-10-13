'''
loader service

takes the jsonl file `./artifacts/news.jsonl`, which contains the scraped news articles,
chunks them, does embedding and loads the chunks into the vector database


* chunking (semantic version) uses OpenAI api for embedding
* but final chunks will be embedded with XYZ so it is consistent with embedding used for retrieval 
'''

import uuid

import pandas as pd
#app/main.py
#---import httpx
#---import feedparser

import psycopg

from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser



# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.genai import types

from google.cloud import storage

BUCKET_NAME = "newsjuice-data-exchange"

from typing import List

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768 #256
# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
#from vertex_embeddings import VertexEmbeddings

from langchain_openai import OpenAIEmbeddings  # or another embedding provider
from langchain_huggingface import HuggingFaceEmbeddings


from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Load the jsonl file from /data/news.jsonl
import json, sys, pathlib
PATH_TO_NEWS= pathlib.Path("/data/news.jsonl")  # for M2 docker-compose version
PATH_TO_CHUNKS = pathlib.Path("/data/chunked_articles")
#path = pathlib.Path("./news.jsonl")  # for standalone version


# Parameter for character chunking 
CHUNK_SIZE_CHAR = 350
CHUNK_OVERLAP_CHAR = 20

# Parameter for recursive chunking 
CHUNK_SIZE_RECURSIVE = 350


import os
DB_URL = os.environ["DATABASE_URL"]       
#DB_URL= "postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" # for use with container
#DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768 #256
GENERATIVE_MODEL = "gemini-2.0-flash-001"

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

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"✅ File {source_file_path} uploaded to gs://{bucket_name}/{destination_blob_name}")


# Chunking function

def chunk_embed_load(method='char-split'):
    PATH_TO_CHUNKS.mkdir(parents=True, exist_ok=True)

    conn = psycopg.connect(DB_URL, autocommit=True)
    cur = conn.cursor()

    # Fetch pending articles
    cur.execute("""
        SELECT id, author, title, summary, content,
               source_link, source_type, fetched_at, published_at,
               vflag, article_id
        FROM articles
        WHERE vflag = 0;
    """)
    rows = cur.fetchall()

    # Prepare semantic splitter once (if requested)
    sem_splitter = None
    if method == "semantic-split":
        emb = VertexEmbeddings()
        sem_splitter = SemanticChunker(embeddings=emb)

    for i, row in enumerate(rows, start=1):
        (_id, author, title, summary, content,
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
        df["embedding"] = [model.encode(t).tolist() for t in df["chunk"]]

        # --- Insert chunks ---
        inserted = 0
        for _, r in df.iterrows():
            cur.execute(
                """
                INSERT INTO chunks_vector
                  (author, title, summary, content,
                   source_link, source_type, fetched_at, published_at,
                   chunk, chunk_index, embedding, article_id)
                VALUES
                  (%s, %s, %s, %s,
                   %s, %s, %s, %s,
                   %s, %s, %s, %s);
                """,
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
                    json.dumps(r["embedding"]),   # If pgvector VECTOR(768), pass list directly and remove dumps
                    r["article_id"],
                )
            )
            inserted += 1
        print("Inserted chunks:", inserted)

        # --- Mark this article processed (parameterized) ---
        cur.execute(
            "UPDATE articles SET vflag = 1 WHERE article_id = %s;",
            (article_id,)
        )

    cur.close()
    conn.close()

def main():

    chunk_embed_load("semantic-split")

    # Bucket upload test
    upload_to_gcs(
        BUCKET_NAME, 
        "/data/news.jsonl", 
        "news2.jsonl")
 

if __name__ == "__main__":
    main()

