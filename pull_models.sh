#!/bin/bash
echo "Waiting for Ollama to finish installing..."
while ! command -v ollama &> /dev/null; do
    sleep 5
done

echo "Ollama is installed. Waiting for daemon to start..."
while ! curl -s http://localhost:11434/api/tags &> /dev/null; do
    sleep 10
done

echo "Daemon is up. Pulling GGUF models sequentially..."
ollama pull hf.co/Qwen/Qwen2-0.5B-Instruct-GGUF:latest
ollama pull hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest
ollama pull hf.co/unsloth/Meta-Llama-3.1-8B-Instruct-GGUF:latest
ollama pull nomic-embed-text
echo "All models downloaded successfully."
