#!/bin/bash
set -e

echo "Starting Meta Knowledge Graph..."

# Create papers directories if they don't exist
mkdir -p /app/papers/pending /app/papers/processed

# Start the backend (which also serves frontend in Docker mode)
cd /app
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088