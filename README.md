# NewsJuice Prototype Pipeline (WIP for Milestone 2)

This repository contains the **NewsJuice Prototype Pipeline**, a containerized system for **scraping**, **processing**, **retrieving**, and **summarizing** news content.  

---

## ⚙️ Pipeline Overview

Here pict-> **NEEDS UPDATE**

![Project logo](app-diagram.png)

The pipeline consists of **four containers**, each responsible for a distinct stage of processing.  
A **PostgreSQL vector database** hosted on **Google Cloud SQL (GCS)** is used for storage and exchange of information.


### 📦 Containers

1. **🕸️ Scraper**  
   - Accesses various sources:  *Harvard Gazette* RSS feed, **NEEDS UPDATE**  
   - Extracts the articles
   - Stores the articles in the `articles` table of the BD

2. **📥 Loader**  
   - Loads articles from `articles` table (only entries with vflag = 0) 
   - Performs **chunking & embedding**  
   - Adds chunks to the **vector database** (table `chunks_vector`)  

3. **🔍 Retriever**  **NEEDS UPDATE**
   - Prompts the user for a **news briefing**  
   - Embeds the **news briefing**  
   - Retrieves top-x relevant entries from the **vector database** 
   - Carries out a LLM query based on user preferences, news brief and retrieved top-x articles

4. **📝 Summarizer** [NOT YET THERE]  
   - Reads `top-2.txt`
   - Calls an **LLM** to generate a **summary**  
   - Saves output to `summary.txt`  

---

## 🚀 Usage

The project provides both **one-line execution** and **step-by-step** container runs using `docker-compose` and `Makefile`.

### 🔧 One-line build & run options

**Option 1: Docker Compose**  
```bash
docker compose build \
 && docker compose up -d dbproxy \
 && docker compose run --rm scraper \
 && docker compose run --rm loader \
 && docker compose run --rm retriever \
 && docker compose run --rm summarizer
 ```

**Option 2: Makefile**

```bash
make run
```

### 🔧 Step-by-step execution:

```bash
docker compose build
docker compose up -d dbproxy
docker compose run --rm scaper
docker compose run --rm loader
docker compose run --rm retriever
docker compose run --rm summarizer
```

To stop all services:
```bash
docker compose down
```



Database Information

- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`
- **Database:** `newsdb` (PostgreSQL 15)  
- **Tables used:** `articles`, `chunks_vector`  


---

## Prerequisites

1. **Install Cloud SQL Proxy** (to connect to GCS database from local dev):

   ```bash
   brew install cloud-sql-proxy
   ```
   or install as part of Google Cloud SDK:

   ```bash
   brew install google-cloud-sdk
   ```

2. **Have the GCP Service Account key file** in `~/../secrects/sa-key.json`  (i.e. in a folder called secrets in the parent directory of `NewsJuice-Pipeline_MS_v2`.) The service account used: `newsjuice-proxy@newsjuice-123456.iam.gserviceaccount.com`


The SQL proxy is started in the docker-compose file and runs in the background. This opens a local port (`5432`) and connects securely to the Cloud SQL instance.


---

## License

This project is part of the **NewsJuice** prototype. All rights reserved.
