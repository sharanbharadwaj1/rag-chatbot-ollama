#!/bin/bash

# Ensure Ollama home directory exists and has correct permissions
mkdir -p /home/appuser/.ollama
chown -R appuser:appuser /home/appuser/.ollama

# Start the Ollama server in the background
# Set OLLAMA_HOST to allow connections from the FastAPI app within the container
# Set OLLAMA_MODELS to store models within the user's home directory
echo "Starting Ollama server..."
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_MODELS=/home/appuser/.ollama /usr/bin/ollama serve &
OLLAMA_PID=$!

# Wait for the Ollama server to be ready
echo "Waiting for Ollama server to start..."
while ! curl -s http://localhost:11434/ > /dev/null; do
    echo -n "."
    sleep 1
done
echo "\nOllama server is running."

# Pull the model if it's not already there
echo "Pulling model gemma:2b-instruct-q4_0..."
ollama pull gemma:2b-instruct-q4_0
echo "Model pull complete."

# Start the FastAPI application
echo "Starting FastAPI server..."
# Use port 8080 as defined in docker-compose
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Clean up Ollama process if Uvicorn exits
kill $OLLAMA_PID
wait $OLLAMA_PID