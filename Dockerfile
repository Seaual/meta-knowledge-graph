# Multi-stage build for Meta Knowledge Graph

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install Java runtime (required by OpenDataLoader-PDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and core library
COPY backend/ ./backend/
COPY mkg/ ./mkg/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directories and initialize database
RUN mkdir -p /app/papers/pending /app/papers/processed /app/data && \
    python scripts/generate_demo_data.py

# Copy startup script
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 8089

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST=/app/frontend/dist

# Health check (Python-based, no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8089/api/graph/stats')" || exit 1

# Start command
CMD ["/app/start.sh"]