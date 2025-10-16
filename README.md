# 📆 NewsJuice (AC215 - Milestone 2)

> Personalized daily podcast summaries of Harvard-related news — built with a scalable RAG pipeline.

---

## 👥 Team

- **Khaled Aly**  
- **Zac Sardi-Santos**  
- **Joshua Rosenblum**  
- **Christian Michel**

**Team name:** `NewsJuice`

---

## 📚 Project Overview

**NewsJuice** is an application that generates a **customized podcasts** summarizing the latest news based on the user’s interests.  
It is primarily designed for the **Harvard community**, pulling content from Harvard-related news sources.

Users can:
- Set preferences and topics of interest  
- Provide a short news brief  
- Receive an **audio podcast** generated automatically  
- *(Future)* Interactively **ask follow-up questions** during playback  

---

## 🎯 Milestone 2 — Prototype Scope

In Milestone 2, we built a complete **RAG (Retrieval-Augmented Generation)** pipeline with the following features:

1. **Scraping:** Collect Harvard-related news (RSS/Atom feeds, websites, etc.)  
2. **Ingestion:** Load scraped data into a **PostgreSQL database** (hosted on GCP). Specifically, we load the scraped articles into our articles table. 
3. **Processing:**  
   - Semantic chunking (using Vertex AI). The chunks are stored in our chunks_vector table.
   - Text embedding (using `sentence-transformers/all-mpnet-base-v2`). The text embeddings are used for embedding the chunks, AND also for embedding the user query for retrieval.
4. **Vector Storage:** Store embeddings in a **pgvector**-enabled PostgreSQL database table, titled chunks_vector. 
5. **Input Query & User_ID** Collect the unique user identification and the specific user query for podcast generation. 
6. **Retrieval**  
   - Retrieve the most relevant news chunks from our database based on embedded user query
7. **LLM Podcast Generation**
    - Generate a text summary of the relevant news chunks with an LLM API call (Google Gemini). 
    - Convert the text summary to audio (mp3) via TTS API call (Google Cloud Text-To-Speech API)
8. **Chat Log History**
    - Model text output and user identification pair saved to PostgreSQL database table, titled llm-conversations

---

## ⚙️ Pipeline Architecture

![Project Architecture](app_architecture.png)

The pipeline consists of **five containers**, each responsible for a specific stage.  
A **PostgreSQL vector database** (on **Google Cloud SQL**) serves as the central data store.

### 🧱 Containers

1. **🕸️ Scraper**  
   - Fetches news articles from multiple Harvard-related sources on the web 
   - Stores them in the `articles` table of the PostgreSQL database `newsdb`

2. **📥 Loader**  
   - Loads unprocessed articles (`vflag = 0`) from the `articles` table of `newsdb`
   - Performs **chunking** and **embedding**  
   - Stores the chunks in the `chunks_vector` table of `newsdb`

3. **💬 Chatter**  
   - Accepts a user’s **query** and **user_id** via user interface
   - Passes the user's query to the retriever
   - Recieves a podcast script from the retriever and passes it to TTS for conversion into an audio file
   - Saves the chat history in the `newsdb` inside of the llm_conversations table

4. **🔍 Retriever**
    - Receives and **Embeds** the user's query
    - **Retrieves the most relevant chunks** (top-n)
    - **Combines** retrieved chunks with the query and user preferences (**promt augmentation**) 
    - Generates a summary in podcast script form via an **LLM** based on the augmented prompt
    - Passes the podcast script back to the chatter

5. **🗣️ TTS**
    - Receives a podcast transcript from chatter 
    - Produces an **audio podcast file** (MP3) from the summary via the Google text-to-speech api
    - Saves the podcast to the audio_output folder locally (in the future, it will be saved to a GCS bucket)

---

## 🚀 Usage

This project supports both **one-line execution** and **step-by-step** runs using `docker-compose` and `Makefile`.

### ▶️ Quick Start (One-line)

**Option 1: Makefile** for a scraper - loader batch cycle and for a chatter cycle

```bash
make -f MakefileBatch run
make -f MakefileChatter run

```

**Option 2: Docker Compose**

**one command**

```bash
docker compose build \
  && docker compose up -d dbproxy \
  && docker compose run --rm scraper \
  && docker compose run --rm loader \
  && docker compose run --rm chatter
```

**step by step**

```bash
docker compose build
docker compose up -d dbproxy
docker compose run --rm scraper
docker compose run --rm loader
docker compose run --rm chatter
```

---


To stop all services:
```bash
docker compose down
```

---

## 🔑 Prerequisites

1. **Install Cloud SQL Proxy** (to connect locally to the GCS-hosted database):

```bash
brew install cloud-sql-proxy
```
Or via Google Cloud SDK:
```bash
brew install google-cloud-sdk
```

2. **Service Account Key**  
   Place your GCP service account key file here:
```
../secrets/sa-key.json
```
Service account:  
`newsjuice-proxy@newsjuice-123456.iam.gserviceaccount.com`

The SQL proxy runs automatically via `docker-compose`, opening a local port (`5432`) that connects securely to the Cloud SQL instance.

---

## 📊 Data

**News Sources:** (WIP)

- ✅ The Harvard Gazette
    https://news.harvard.edu/gazette/feed/
- ✅ The Harvard Crimson
    https://www.thecrimson.com/
- Harvard Magazine
    https://www.harvardmagazine.com/harvard-headlines
- Colloquy: The alumni newsletter for the Graduate School of Arts and Sciences.
    https://gsas.harvard.edu/news/all
- Harvard Business School Communications Office: Publishes news and research from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx
- Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
- Harvard Medical School Office of Communications and External Relations - News: Disseminates news from the medical school.
    https://hms.harvard.edu/news

---

---

## 🗄️ Database Details

- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`  
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`  
- **Database:** `newsdb` (PostgreSQL 15)  
- **Tables:** `articles`, `chunks_vector`  

> ⚠️ **Note:** The above identifiers are for documentation and environment setup. Do not commit actual secrets to version control.

---

## 📊 Database Schema

### 📰 Table: `articles`
Stores raw scraped news articles.

```sql
id BIGSERIAL PRIMARY KEY,
author TEXT,
title TEXT,
summary TEXT,
content TEXT,
source_link TEXT, 
source_type TEXT,
fetched_at TIMESTAMPTZ,
published_at TIMESTAMPTZ,
vflag INT,
article_id TEXT
```

### 🧠 Table: `chunks_vector`
Stores semantic chunks and vector embeddings.

```sql
id BIGSERIAL PRIMARY KEY,
author TEXT,
title TEXT,
summary TEXT,
content TEXT,
source_link TEXT, 
source_type TEXT,
fetched_at TIMESTAMPTZ,
published_at TIMESTAMPTZ,
chunk TEXT,
chunk_index INT,
embedding VECTOR(768),
article_id TEXT
```

### 🧠 Table: `llm_conversations`
Stores the history of conversations

```sql
id BIGSERIAL PRIMARY KEY,
user_id TEXT,
model_name TEXT,
conversation_data JSON,
created_at TIMESTAMPTZ,
updated_at TIMESTAMPTZ
```

---

## In future milestones, we plan to:
- Summarize the `conversation_data` that we store in the `llm_conversations` table as context for future user queries to get a sense of the user's preferences and provide the history of past conversations for better podcast generation.
- Transition to interacting with the model with only speech rather than typing in the command line.
- Build the interactive component of our model so that the user can interupt the podcast and ask followup questions.

## References

For this project we have used ChatGPT, Gemini and tools like app.eraser.io for learrning purposes.

## 📜 License

This project is part of the **NewsJuice** prototype.  
All rights reserved.

