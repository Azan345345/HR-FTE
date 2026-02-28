# ============================================================
# Digital FTE — Root Dockerfile (Railway deployment)
# Build context: repo root — includes backend/ + skills/
# ============================================================

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source into /app
COPY backend/ .

# Copy skills directory to /skills/
# skills.py resolves: /app/app/core/skills.py -> 4x parent -> / -> /skills
COPY skills/ /skills/

# Create runtime directories
RUN mkdir -p uploads generated

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
