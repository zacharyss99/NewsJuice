# Manager Dockerfile (API)
FROM python:3.12-slim-bookworm

ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends build-essential curl bash \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && pip install uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync 

# Install uvicorn in system Python for volume mount compatibility
RUN pip install uvicorn fastapi httpx

COPY . ./

EXPOSE 8000
CMD ["/usr/local/bin/python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
