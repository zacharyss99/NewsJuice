# Loader module


- Loads articles from `articles` table in the DB (only entries with vflag = 0, this flag indicates which article is already chunked and vectorized) 
   - Performs **chunking & embedding**  
   - Adds new article chunks to the **vector DB** (table `chunks_vector`)  
- use the same embedder for final chunk embedding as Zac 


Uses Vertex AI for embeddings of the chunks
**Chunking option available**
- `char-split` character splitting
- `recursive-split` recursive splitting
- `semantic-split` (using embedding model below)

Database Information
- **Account:** `harvardnewsjuice@gmail.com`  
- **Project:** `NewsJuice`  
- **Project ID:** `newsjuice-123456`
- **Instance:** `newsdb-instance`  
- **Region:** `us-central1`
- **Database:** `newsdb` (PostgreSQL 15)  
- **Table:** IN: `articles`, OUT:`chunks_vector`  
- Service account used for all GC services in this module (PosgresSQL, VertexAI) = 


