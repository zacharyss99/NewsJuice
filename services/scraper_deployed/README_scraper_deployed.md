# Scraper module

- scrapes articles from various Harvard-related news sources (currently a hard-coded list in "scrapers.py"), performs a tagging operation (stored later in a column in the articles table) and loads the articles not previously loaded into the articles table.


## Instructions for local deployment  

(CM ===CHECK IF THIS OR/AND OTHER NEEDED)
1. Test that secrets exist:  
```bash
ls -la ../../../secrets/sa-key.json
ls -la ../../../secrets/gemini-service-account.json 
```

(CM ===CHECK AND EXPLAIN WHAT NEEDS TO BE THERE, IF AT ALL)
2. Create a .env.local and make sure it has the OpenAI key  
```bash
cat .env.local
```

3. Make sure Docker is running  
```bash
docker ps
```

4. Start with logs visible (Note: we use .env.local and docker-compose.local.yml)
```bash
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

## LOCAL TESTING

Health:
```bash
curl http://localhost:8080/
```

Run the scraper once 
```bash
curl -X POST http://localhost:8080/process
```

Watch logs to see results
```bash
docker compose -f docker-compose.local.yml logs -f scrapers
```

Stop and remove scrapers and cloud-sql-proxy containers
```bash
docker compose -f docker-compose.local.yml down
```

Start the containers again
```bash
docker compose -f docker-compose.local.yml up
```