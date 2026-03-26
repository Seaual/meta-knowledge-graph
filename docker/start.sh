#!/bin/bash
set -e

echo "Starting Meta Knowledge Graph..."

# Create directories if they don't exist
mkdir -p /app/papers/pending /app/papers/processed /app/data

# Initialize database with WAL mode if it doesn't exist
if [ ! -f /app/mkg.db ]; then
    echo "Initializing database..."
    python -c "
from mkg.database import Database
db = Database('/app/mkg.db')
db.connect()
print('Database initialized with WAL mode')
db.close()
"
fi

# Start the backend (which also serves frontend in Docker mode)
cd /app
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088