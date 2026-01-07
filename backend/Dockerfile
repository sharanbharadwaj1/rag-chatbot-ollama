# syntax=docker/dockerfile:1.4
# Use a slim, fast-to-download Python image
FROM python:3.10-slim

# Install system dependencies (curl for Ollama)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama && chmod +x /usr/bin/ollama

WORKDIR /app

# --- This is the new, fast way ---

# 1. Install uv (the fast installer)
RUN pip install uv

# 2. Copy *only* the requirements file
COPY ./requirements.txt .

# 3. Install packages using uv AND a cache mount
# This line tells Docker to keep a cache at /root/.cache
# Subsequent builds will re-use this cache and be much faster.
RUN --mount=type=cache,target=/root/.cache \
    uv pip install --no-cache -r requirements.txt --system

# --- End of new section ---

# Copy the rest of your application code
COPY ./app /app/app
COPY ./start.sh /app/start.sh
COPY ./frontend /app/frontend  # This works now

RUN chmod +x /app/start.sh

EXPOSE 8080 11434

ENTRYPOINT ["/app/start.sh"]