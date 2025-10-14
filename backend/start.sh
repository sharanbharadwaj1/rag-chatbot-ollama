#!/bin/bash

# Start the Ollama server in the background
/bin/ollama serve &

# Wait a few seconds for the server to be ready
echo "Waiting for Ollama server to start..."
sleep 5

# Pull the model (this will only happen if the model isn't already there)
echo "Pulling model..."
ollama pull gemma:2b-instruct-q4_0

echo "Starting FastAPI server..."
# Start the FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8080