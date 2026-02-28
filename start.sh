#!/usr/bin/env bash
# ============================================================
# Digital FTE — Quick Start Script (macOS / Linux)
# Usage: ./start.sh
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Digital FTE — Starting Up      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Check Docker ────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found.${NC}"
    echo "  Install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running.${NC}"
    echo "  Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# ── 2. Check .env ──────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ No .env file found — creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}  Edit .env and add your API keys, then re-run this script.${NC}"
    echo -e "${YELLOW}  See SETUP.md for instructions on getting API keys.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ .env file found${NC}"

# ── 3. Check at least one LLM key is set ───────────────────
source .env 2>/dev/null || true
if [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${GOOGLE_AI_API_KEY:-}" ] && [ -z "${GROQ_API_KEY:-}" ]; then
    echo -e "${RED}✗ No LLM API key found in .env${NC}"
    echo "  Set at least one of: OPENAI_API_KEY, GOOGLE_AI_API_KEY, or GROQ_API_KEY"
    echo "  See SETUP.md for instructions."
    exit 1
fi

echo -e "${GREEN}✓ LLM API key configured${NC}"

# ── 4. Build and start ─────────────────────────────────────
echo ""
echo -e "${CYAN}► Building containers (first run takes 5-10 min due to AI model downloads)...${NC}"
echo ""

docker compose up --build -d

# ── 5. Wait for backend health ─────────────────────────────
echo ""
echo -e "${CYAN}► Waiting for backend to be ready...${NC}"
RETRIES=30
until curl -sf http://localhost:8080/health > /dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -eq 0 ]; then
        echo -e "${RED}✗ Backend did not start in time. Check logs: docker compose logs backend${NC}"
        exit 1
    fi
    echo -n "."
    sleep 3
done

echo ""
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Digital FTE is Ready!       ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend:  http://localhost:5173    ║${NC}"
echo -e "${GREEN}║  Backend:   http://localhost:8080    ║${NC}"
echo -e "${GREEN}║  API Docs:  http://localhost:8080/docs ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  To stop:  ${YELLOW}docker compose down${NC}"
echo -e "  Logs:     ${YELLOW}docker compose logs -f${NC}"
echo ""
