FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install uv && \
    pip install psycopg[binary]

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies directly with pip
RUN pip install google-cloud-texttospeech google-auth

# Copy application code
COPY . ./

# Set default command
CMD ["python3", "tts.py"]
