.PHONY: run build scrape load retrieve up-proxy down clean rebuild

run: build up-proxy load  ## Build images, start proxy, load data
	@echo "✅ Data pipeline finished. Use 'make chat' to start interactive chat."

build:
	docker compose build

up-proxy:
	docker compose up -d dbproxy

scrape:
	mkdir -p artifacts
	docker compose run --rm scraper

load:
	docker compose run --rm loader

retrieve:
	docker compose run --rm retriever

chat:  ## Start interactive chat with Gemini (includes retrieval)
	docker compose run --rm chatter

down:
	docker compose down

clean: down
	@echo "💥 (kept artifacts/. Delete manually if you want a fresh file)"