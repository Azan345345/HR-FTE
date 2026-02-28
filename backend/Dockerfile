# ============================================================
# Digital FTE — Backend Dockerfile
# Python 3.12 + FastAPI + LangGraph
# ============================================================

FROM python:3.12-slim

# System packages needed to compile native Python extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create directories for file uploads and generated PDFs
RUN mkdir -p uploads generated

# Expose the API port
EXPOSE 8080

# Health check — waits up to 30s for startup (sentence-transformers is slow)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
