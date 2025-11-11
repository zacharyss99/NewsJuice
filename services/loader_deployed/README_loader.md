# Loader module

- Loads articles from `articles` table in the DB (only entries with vflag = 0, this flag indicates which article is already chunked and vectorized) 
   - Performs **chunking & embedding**  
   - Adds new article chunks to the **vector DB** (table `chunks_vector`)  
- uses Vertex AI ("text-embedding-004") for final chunk embeddings

Uses Vertex AI for embeddings of the chunks
**Chunking option available**
- `char-split` character splitting
- `recursive-split` recursive splitting
- `semantic-split` (using embedding model below)

* We use: SemanticChunker from langchain_experimental.text_splitter
* Parameters that can be tuned:
-embeddings
-breakpoint_threshold_type ("percentile" or "standard_deviation")
-breakpoint_threshold_amount (default 95 for "percentile)


Database Information
- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`
- **Database:** `newsdb` (PostgreSQL 15)  
- **Table:** 
PRODUCTION: IN: `articles`, OUT:`chunks_vector`  
TEST: IN: `articles_test`, OUT:`chunks_vector_test` (set via env variables ARTICLE_TABLE and CHUNKS_VECTOR_TABLE)  

- Service account used for all GC services in this module (PosgresSQL, VertexAI) = 

---


## This loader container is currently deployed on GCS (Cloud Run)

Service URL of deployed loader:
https://article-loader-919568151211.us-central1.run.app
Latest revision: article-loader-00001-9cx
	

## Instructions for local deployment  

1. Test that secrets exist:  
```bash
ls -la ../../../secrets/sa-key.json
ls -la ../../../secrets/gemini-service-account.json
```

2. Make sure .env.local has OpenAI key  
```bash
cat .env.local
```

3. Make sure Docker is running  
```bash
docker ps
```

4. Start with logs visible (Note: I use .env.local and docker-compose.local.yml)
```bash
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

## LOCAL TESTING

Health:
```bash
curl http://localhost:8080/
```

Run the loader once 
```bash
curl -X POST http://localhost:8080/process
```

Watch logs to see results
```bash
docker compose -f docker-compose.local.yml logs -f loader
```

Stop and remove loader and cloud-sql-proxy containers
```bash
docker compose -f docker-compose.local.yml down
```

Start the containers again
```bash
docker compose -f docker-compose.local.yml up
```


LOGGING:

Local:
For each loader run a timestamped logfile is created and stored in the 
logs folder (./logs is mounted to /app/logs/ in the container)

For Cloud Run:
Logs go to Google Cloud Logging (not files)
File logging in Cloud Run is not recommended
Use gcloud logging read to view logs instead


## Instructions for deployment with Cloud Run

Run:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Prerequisites

Make sure right account set
```bash
gcloud auth list
gcloud config get-value account
gcloud auth login harvardnewsjuice@gmail.com
gcloud config set account harvardnewsjuice@gmail.com
```



## Switch between test and production tables

Go to production  

Make sure right project
```bash
gcloud config set project newsjuice-123456
gcloud config get-value project
```
```bash
gcloud run services update article-loader \
  --region us-central1 \
  --project=newsjuice-123456 \
  --update-env-vars ARTICLES_TABLE_NAME=articles,VECTOR_TABLE_NAME=chunks_vector
```

Back to test

```bash
gcloud run services update article-loader \
  --region us-central1 \
  --project=newsjuice-123456 \
  --update-env-vars ARTICLES_TABLE_NAME=articles_test,VECTOR_TABLE_NAME=chunks_vector_test
```

Check the environmental variables
```bash
gcloud run services describe article-loader \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
``


## APPENDIX
**Cloud Run's architecture:**
Internet → Cloud Run (HTTPS 443) → Your Container (port 8080)

Cloud Run automatically:

Exposes your service on HTTPS (port 443) publicly
Routes traffic to your container's internal port (8080)
Handles load balancing, scaling, etc.

You never directly expose port 8080 to the internet. Cloud Run manages that.



## APPENDIX

##E mbedding used:  

Library: google-genai is Google’s official Python SDK for interacting with the Gemini family of generative AI models (like gemini-1.5-pro, gemini-2.0-flash, etc.).  
It lets your code talk directly to Google’s GenAI API, which can be accessed in two ways:  
- **Directly** via Google AI Studio (using an API key)  
- **Via Vertex** AI (in Google Cloud) — using a GCP project and service account  
Here: We are accessing Google’s Gemini models through Vertex AI’s managed GenAI service rather than through the lightweight public API key route.  

The google-genai library:
- Handles all the API calls to Gemini models
- Authenticates automatically (with a Google Cloud project or API key)
- Provides simple methods for: 
text generation (generate_content)
chat (start_chat, send_message)
embeddings (embed_content)
multimodal inputs (text + image)
streaming responses

vertexai=True in your client:
tells the library to:
- Send requests to Vertex AI’s managed Gemini endpoint

- Use your GCP project billing, IAM permissions, and regional deployment

- Integrate with other Vertex services (data, tuning, monitoring)


=====
INSERT TEST ARTICLE

sql-- Connect to your database
psql "postgresql://postgres:Newsjuice25+@localhost:5432/newsdb"

-- Insert a test article
INSERT INTO articles_test (
    author, title, summary, content, 
    source_link, source_type, 
    fetched_at, published_at, 
    vflag, article_id
)
VALUES (
    'Test Author',
    'Test Article Title',
    'This is a test summary',
    'This is the full content of the test article. It should be long enough to create multiple chunks when processed by the semantic chunker.',
    'https://example.com/test',
    'web',
    NOW(),
    NOW(),
    0,  -- vflag=0 means "not processed yet"
    'test-' || gen_random_uuid()::text
);

-- Verify it was inserted
SELECT article_id, title, vflag FROM articles_test WHERE vflag = 0;



# STEP BY STEP - DEPLOYMENT
===========================

make sure right account: (switch if needed)
gcloud auth list
gcloud config set account harvardnewsjuice@gmail.com

make sure right project:
gcloud config get-value project
gcloud config set project newsjuice-123456

RUN DEPLOY script

chmod +x deploy.sh
./deploy.sh

WATCH DEPLOYMENT
gcloud builds list --limit 3

SEE DEPLOYED SERIVCES
gcloud run services list --region us-central1


## Set up Scheduler

Create SA (cloud-run-invoker):

gcloud iam service-accounts create cloud-run-invoker \
  --display-name "Cloud Run Invoker" \
  --project newsjuice-123456

Grant permissions:

gcloud run services add-iam-policy-binding article-loader \
  --member="serviceAccount:cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region us-central1 \
  --project newsjuice-123456

Enable API [cloudscheduler.googleapis.com] on project [newsjuice-123456]

# Grant Vertex AI User role

gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.serviceAgent"
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:919568151211-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"

Create schedule job (name: article-loader-job)

gcloud scheduler jobs create http article-loader-job \
  --location us-central1 \
  --schedule="*/10 * * * *" \
  --uri="https://article-loader-919568151211.us-central1.run.app/process" \
  --http-method POST \
  --oidc-service-account-email=cloud-run-invoker@newsjuice-123456.iam.gserviceaccount.com \
  --oidc-token-audience="https://article-loader-919568151211.us-central1.run.app" \
  --project newsjuice-123456

Test scheduler manually:

gcloud scheduler jobs run article-loader-job \
  --location us-central1 \
  --project newsjuice-123456

After running check:


# View Cloud Run logs
gcloud run services logs read article-loader \
  --region us-central1 \
  --limit 20

# Check scheduler logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit 10

# view all cloud builds and revisions
gcloud builds list --limit 20






  CHANGE SCHEDULE:

  gcloud scheduler jobs update http article-loader-job \
  --location us-central1 \
  --schedule="0 0 * * *"


  force a run  
  gcloud scheduler jobs run article-loader-job \
  --location us-central1


See the print to standard i/o:
  gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=article-loader" \
  --limit=100 \
  --format="value(timestamp,textPayload)" \
  --freshness=1h




  ======
  How to deploy locally with docker compose and then test


  =====
 
# Deploy with secret
gcloud run deploy article-loader \
  --source . \
  --region us-central1 \
  --env-vars-file env.yaml \
  --set-secrets DATABASE_URL=database-url:latest \
  --add-cloudsql-instances newsjuice-123456:us-central1:newsdb-instance

# NEW END
