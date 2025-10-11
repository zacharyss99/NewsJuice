# Retriever Dockerfile (API)
FROM python:3.12-slim-bookworm

# --- System setup ---
ENV UV_LINK_MODE=copy
# Use a venv location that exists without creating /home/app:
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Optional: speed up HF/SB model caches on a mounted volume (/data from compose)
ENV SENTENCE_TRANSFORMERS_HOME=/data/st
ENV TRANSFORMERS_CACHE=/data/hf
ENV HF_HOME=/data/hf

RUN apt-get update && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends build-essential curl bash libpq-dev \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Python deps via uv ---
RUN pip install --no-cache-dir --upgrade pip && pip install uv

WORKDIR /app
COPY pyproject.toml ./

# If you commit uv.lock, keep --frozen; otherwise drop it.
# RUN uv sync --frozen
RUN uv sync

# Install uvicorn in system Python for volume mount compatibility
RUN pip install uvicorn fastapi psycopg pgvector sentence-transformers

# App code
COPY . ./

EXPOSE 8000
# Compose can override this with wait_for_db if you like.
CMD ["/usr/local/bin/python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
