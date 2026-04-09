#!/bin/bash
set -e

echo "Starting Meta Knowledge Graph..."

# Create directories if they don't exist
mkdir -p /app/papers/pending /app/papers/processed /app/data

# Initialize database - load demo if first run
if [ ! -f /app/mkg.db ]; then
    echo "Initializing database..."
    if [ -f /app/mkg-demo.db ]; then
        echo "Loading demo data..."
        cp /app/mkg-demo.db /app/mkg.db
        echo "Demo database loaded (10 LLM papers with concept graph)"
    else
        python -c "
from mkg.database import Database
db = Database('/app/mkg.db')
db.connect()
print('Empty database initialized')
db.close()
"
    fi
else
    echo "Database exists, skipping initialization"
fi

# Start the backend (which also serves frontend in Docker mode)
cd /app
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8089