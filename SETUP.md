# Digital FTE — Setup & Deployment Guide

> **AI-powered multi-agent job application assistant**
> Works on macOS, Windows, and Linux via Docker.

---

## Table of Contents

1. [Quick Start (5 minutes with Docker)](#1-quick-start-docker)
2. [Getting Your API Keys](#2-getting-your-api-keys)
   - [LLM Providers (Required — pick one)](#21-llm-providers-required)
   - [Job Search APIs (Required — pick one)](#22-job-search-apis-required)
   - [HR Contact Finders (Optional)](#23-hr-contact-finders-optional)
   - [Google OAuth / Gmail (Optional)](#24-google-oauth--gmail-optional)
   - [Supabase (Optional — Production DB)](#25-supabase-optional)
   - [Upstash Redis (Optional)](#26-upstash-redis-optional)
   - [Observability Tools (Optional)](#27-observability-optional)
3. [Configuring Your .env File](#3-configuring-your-env-file)
4. [Running with Docker (Recommended)](#4-running-with-docker-recommended)
5. [Running Manually (Without Docker)](#5-running-manually-without-docker)
   - [macOS Setup](#51-macos)
   - [Windows Setup](#52-windows)
   - [Linux Setup](#53-linux)
6. [Accessing the App](#6-accessing-the-app)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start (Docker)

> **Prerequisites:** Docker Desktop installed and running.
> [Download Docker Desktop](https://www.docker.com/products/docker-desktop/) — free, works on macOS, Windows, Linux.

```bash
# 1. Clone / download the project
git clone <your-repo-url>
cd "FTE HR"

# 2. Copy the environment template
cp .env.example .env

# 3. Open .env in any text editor and fill in your API keys
#    (see Section 2 for how to get each key)

# 4. Start everything
#    macOS / Linux:
./start.sh

#    Windows (double-click or run in cmd):
start.bat

#    Or with make / docker directly:
make up
# -- OR --
docker compose up --build
```

**That's it.** On first run Docker builds the images (~5–10 min because it downloads AI model weights). Subsequent starts take ~30 seconds.

| Service  | URL                            |
|----------|--------------------------------|
| Frontend | http://localhost:5173          |
| Backend  | http://localhost:8080          |
| API Docs | http://localhost:8080/docs     |

### Test Credentials (Skip Registration)

A ready-made test account lets you log in immediately without signing up:

| Field    | Value              |
|----------|--------------------|
| Email    | `test@gmail.com`   |
| Password | `Test@12345`       |

**To create the test user, run once after the backend is up:**

```bash
# Docker (exec into the running container)
docker compose exec backend python scripts/create_test_user.py

# Manual / local dev (from the backend/ folder)
cd backend
python scripts/create_test_user.py
```

The script is idempotent — safe to run multiple times. After that, open http://localhost:5173 and sign in with the credentials above.

---

## 2. Getting Your API Keys

### 2.1 LLM Providers (Required)

You need **at least one** LLM provider. The app tries them in order: OpenAI → Gemini → Groq.

---

#### Option A — OpenAI (Best quality)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account or sign in
3. Navigate to **API Keys** (top-right menu → "API keys")
4. Click **"+ Create new secret key"**
5. Give it a name (e.g., `digital-fte`)
6. Copy the key — it starts with `sk-...`
7. Add $5–10 credit in **Billing** → **Add payment method**

```env
OPENAI_API_KEY=sk-...your-key-here...
```

> **Cost:** GPT-4o costs ~$0.005 per 1K tokens. A typical job application workflow uses ~5K tokens ≈ $0.025 per job.

---

#### Option B — Google Gemini (Free tier available)

1. Go to [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account
3. Click **"Get API key"** → **"Create API key"**
4. Select a Google Cloud project (or create one)
5. Copy the key — it starts with `AIza...`

```env
GOOGLE_AI_API_KEY=AIza...your-key-here...
```

> **Free tier:** 15 requests/min, 1M tokens/day. Sufficient for personal use.

---

#### Option C — Groq (Free, fastest)

1. Go to [console.groq.com](https://console.groq.com)
2. Create a free account
3. Navigate to **API Keys** in the left sidebar
4. Click **"Create API Key"**
5. Copy the key — it starts with `gsk_...`

```env
GROQ_API_KEY=gsk_...your-key-here...
```

> **Free tier:** 30 requests/min. Uses Llama 3.3 70B — excellent quality for free.

---

### 2.2 Job Search APIs (Required)

You need **at least one** job search API to find job listings.

---

#### Option A — SerpAPI (Recommended)

1. Go to [serpapi.com](https://serpapi.com)
2. Create a free account
3. Dashboard → **API Key** (top-right)
4. Copy your key

```env
SERPAPI_API_KEY=your-serpapi-key
```

> **Free tier:** 100 searches/month. Searches Google Jobs — best quality results.

---

#### Option B — RapidAPI / JSearch

1. Go to [rapidapi.com](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Create a free account
3. Subscribe to the **JSearch** API (Basic plan is free)
4. Go to your [RapidAPI Apps](https://rapidapi.com/developer/apps) → copy your **Application Key**

```env
RAPIDAPI_KEY=your-rapidapi-key
```

> **Free tier:** 200 requests/month.

---

### 2.3 HR Contact Finders (Optional)

These APIs let the app find HR manager email addresses so it can send personalized emails. You need **at least one** to use the email outreach feature.

---

#### Hunter.io (Recommended — Most reliable)

1. Go to [hunter.io](https://hunter.io)
2. Create a free account
3. Top-right menu → **API** → copy your API key

```env
HUNTER_API_KEY=your-hunter-api-key
```

> **Free tier:** 25 domain email searches/month.

---

#### Prospeo.io

1. Go to [prospeo.io](https://prospeo.io)
2. Create a free account
3. Dashboard → **API** → copy your key

```env
PROSPEO_API_KEY=your-prospeo-key
```

> **Free tier:** 150 domain email searches/month.

---

#### Snov.io

1. Go to [app.snov.io](https://app.snov.io)
2. Create a free account
3. Settings → **API** → copy Client ID and Client Secret

```env
SNOV_CLIENT_ID=your-snov-client-id
SNOV_CLIENT_SECRET=your-snov-client-secret
```

> **Free tier:** 50 searches/month.

---

#### Apify (LinkedIn scraper)

1. Go to [apify.com](https://apify.com)
2. Create a free account — you get $5 free credit
3. Settings → **Integrations** → copy API token

```env
APIFY_API_KEY=apify_api_...your-token...
```

---

### 2.4 Google OAuth / Gmail (Optional)

Required **only** if you want the app to send emails directly from your Gmail account. Skip this section if you don't need email sending.

#### Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **"New Project"**
3. Name it `digital-fte` → **Create**
4. Wait for it to be created, then select it

#### Step 2 — Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click it → **Enable**

#### Step 3 — Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External**
   - App name: `Digital FTE`
   - Support email: your Gmail
   - Scroll down → **Save and Continue** (skip optional fields)
   - Add yourself as a test user
4. Back on Create OAuth Client ID:
   - Application type: **Desktop app**
   - Name: `digital-fte`
   - Click **Create**
5. Download the JSON file → rename it to `credentials.json`
6. Place `credentials.json` in the **project root** (same folder as `.env`)

#### Step 4 — Generate a Refresh Token

```bash
# From the project root:
python backend/scripts/generate_gmail_token.py
```

This opens a browser window. Sign in with your Gmail and grant permissions. The script saves a token and prints your refresh token.

```env
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_OAUTH_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...your-secret...
GOOGLE_REFRESH_TOKEN=1//...your-refresh-token...
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

---

### 2.5 Supabase (Optional)

> **Default:** The app uses local SQLite — no setup needed for development.
> Use Supabase for production/multi-user deployments with persistent cloud storage.

1. Go to [supabase.com](https://supabase.com) → **"Start your project"**
2. Create a free account and a new project
3. Wait for the project to provision (~2 min)
4. Go to **Settings** → **Database** → copy the **Connection string** (URI format)
5. Go to **Settings** → **API** → copy:
   - **Project URL**
   - **anon/public** key
   - **service_role** key (keep this secret!)

```env
SUPABASE_URL=https://abcdefghijklm.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
DATABASE_URL=postgresql+asyncpg://postgres.abcdefghijklm:your-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
DIRECT_DATABASE_URL=postgresql://postgres.abcdefghijklm:your-password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

> **Free tier:** 500MB database, 2 projects, unlimited API requests.

---

### 2.6 Upstash Redis (Optional)

Used for API quota tracking and caching. The app works without it.

1. Go to [console.upstash.com](https://console.upstash.com)
2. Create a free account → **Create Database**
3. Region: choose closest to you
4. After creation, go to **Details** tab → copy:
   - **Redis URL** (starts with `rediss://`)
   - **REST URL** (starts with `https://`)
   - **REST Token**

```env
UPSTASH_REDIS_URL=rediss://default:password@endpoint.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://endpoint.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXxxxxxxxxxxxxxxxx
```

> **Free tier:** 10,000 commands/day, 256MB storage.

---

### 2.7 Observability (Optional)

These tools let you trace and debug LLM calls. Completely optional.

#### LangSmith

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Create a free account → **Settings** → **API Keys** → create one

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...your-key...
LANGCHAIN_PROJECT=digital-fte
```

#### Langfuse

1. Go to [cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a free account → **Project Settings** → copy keys

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 3. Configuring Your .env File

1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in any text editor (VS Code, Notepad, nano, etc.)

3. Fill in the values from Section 2. A **minimal working setup** needs:

   ```env
   # Minimum required — pick one from each group:
   OPENAI_API_KEY=sk-...           # OR GOOGLE_AI_API_KEY OR GROQ_API_KEY
   SERPAPI_API_KEY=...             # OR RAPIDAPI_KEY

   # Generate a secure secret (run this in terminal):
   # openssl rand -hex 32
   SECRET_KEY=your-32-char-or-longer-random-string
   ```

4. **Generate a secure SECRET_KEY:**

   ```bash
   # macOS / Linux:
   openssl rand -hex 32

   # Windows PowerShell:
   [System.Web.Security.Membership]::GeneratePassword(32, 4)
   # OR (simpler):
   -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
   ```

---

## 4. Running with Docker (Recommended)

Docker handles all dependencies automatically. Same commands work on macOS, Windows, and Linux.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free)
- 4GB+ free disk space (AI model weights are large)
- Your `.env` file configured

### Start

```bash
# First run (downloads/builds everything — takes 5-10 min):
docker compose up --build

# Background (detached) mode:
docker compose up --build -d

# Subsequent starts (fast):
docker compose up -d
```

### Stop

```bash
docker compose down
```

### View Logs

```bash
# All services:
docker compose logs -f

# Backend only:
docker compose logs -f backend

# Frontend only:
docker compose logs -f frontend
```

### Rebuild After Code Changes

```bash
docker compose up --build -d
```

### Reset Everything (wipe data)

```bash
docker compose down -v   # -v removes volumes (wipes SQLite DB, uploads)
docker compose up --build -d
```

---

## 5. Running Manually (Without Docker)

Use this if you prefer not to use Docker or want faster development iteration.

### Prerequisites (all platforms)

- **Python 3.11 or 3.12** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18, 20, or 22** — [nodejs.org](https://nodejs.org/)
- **Git** — [git-scm.com](https://git-scm.com/)

---

### 5.1 macOS

```bash
# Install Homebrew if you don't have it:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12 and Node.js:
brew install python@3.12 node

# Navigate to the project:
cd "FTE HR"

# Set up the backend:
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run the backend (in Terminal 1):
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Set up and run the frontend (in Terminal 2):
cd ../frontend
npm install
npm run dev
```

---

### 5.2 Windows

Open **PowerShell** as Administrator:

```powershell
# Install Python 3.12 (if not installed):
# Download from https://www.python.org/downloads/windows/
# IMPORTANT: Check "Add Python to PATH" during installation

# Install Node.js (if not installed):
# Download from https://nodejs.org/ (LTS version)

# Navigate to the project:
cd "D:\Projects\FTE HR"

# Set up the backend:
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# If you get a script execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the backend (in PowerShell window 1):
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Set up and run the frontend (in PowerShell window 2):
cd ..\frontend
npm install
npm run dev
```

---

### 5.3 Linux (Ubuntu/Debian)

```bash
# Install Python 3.12 and Node.js:
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip curl

# Node.js via NodeSource:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Navigate to the project:
cd "FTE HR"

# Set up the backend:
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run the backend (Terminal 1):
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Set up and run the frontend (Terminal 2):
cd ../frontend
npm install
npm run dev
```

---

## 6. Accessing the App

Once running (Docker or manual), open your browser:

| What              | URL                              |
|-------------------|----------------------------------|
| **App (Frontend)**| http://localhost:5173            |
| **API (Backend)** | http://localhost:8080            |
| **API Docs**      | http://localhost:8080/docs       |
| **Health Check**  | http://localhost:8080/health     |

### First Time

1. Open http://localhost:5173
2. Click **"Sign up"** — create an account (stored locally in SQLite)
3. Upload your CV (PDF or DOCX)
4. Type something like: *"Find me software engineer jobs in London"*
5. The AI agents will search, tailor your CV, find HR contacts, and draft emails

---

## 7. Troubleshooting

### Docker

**"Docker daemon is not running"**
- macOS/Windows: Open Docker Desktop and wait for it to fully start
- Linux: Run `sudo systemctl start docker`

**Backend container keeps restarting**
```bash
docker compose logs backend
```
Most common cause: missing required API key in `.env`. Check `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`, or `GROQ_API_KEY` is set.

**Frontend can't reach backend**
- This is a Docker networking issue. Make sure `VITE_BACKEND_URL=http://backend:8080` is set in docker-compose.yml (it is by default).
- Check that the backend container is healthy: `docker compose ps`

**"Port is already in use"**
```bash
# macOS / Linux:
lsof -i :8080   # find what's using port 8080
lsof -i :5173   # find what's using port 5173

# Windows PowerShell:
netstat -ano | findstr :8080
```
Either stop the conflicting process, or change ports in `docker-compose.yml`.

**First build takes very long**
Normal — the Python image downloads `sentence-transformers` which includes PyTorch (~1.5GB). This only happens once; subsequent builds use cached layers.

---

### Manual Setup

**`ModuleNotFoundError` on backend start**
```bash
# Make sure your virtual environment is activated:
# macOS/Linux:
source backend/venv/bin/activate

# Windows:
backend\venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt
```

**`aiosqlite` error on first run**
```bash
pip install aiosqlite
```

**Frontend shows blank page / CORS error**
- Make sure the backend is running on port 8080
- Check browser console for errors
- The backend must be running before you load the frontend

**`sentence-transformers` build fails on Windows**
- Install Visual C++ Build Tools: [visualstudio.microsoft.com/downloads/](https://visualstudio.microsoft.com/downloads/) → "Build Tools for Visual Studio"
- Or use Docker (avoids all native build issues)

**Gmail OAuth errors**
- Make sure `credentials.json` is in the project root
- Re-run `python backend/scripts/generate_gmail_token.py`
- Make sure your Google account is added as a test user in the OAuth consent screen

---

### Getting Help

- Check the full README.md for architecture details
- API Docs at http://localhost:8080/docs show all available endpoints
- Enable debug logging: set `DEBUG=true` and `LOG_LEVEL=DEBUG` in `.env`

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Required (one of three) | OpenAI GPT-4o API key |
| `GOOGLE_AI_API_KEY` | Required (one of three) | Google Gemini API key |
| `GROQ_API_KEY` | Required (one of three) | Groq API key (free) |
| `SERPAPI_API_KEY` | Required (one of two) | SerpAPI for Google Jobs |
| `RAPIDAPI_KEY` | Required (one of two) | RapidAPI JSearch |
| `SECRET_KEY` | Required | JWT signing secret (min 32 chars) |
| `HUNTER_API_KEY` | Optional | Hunter.io HR email finder |
| `PROSPEO_API_KEY` | Optional | Prospeo.io HR email finder |
| `SNOV_CLIENT_ID` | Optional | Snov.io HR email finder |
| `SNOV_CLIENT_SECRET` | Optional | Snov.io HR email finder |
| `APIFY_API_KEY` | Optional | Apify LinkedIn scraper |
| `GOOGLE_OAUTH_CLIENT_ID` | Optional | Google OAuth (Gmail sending) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Optional | Google OAuth |
| `GOOGLE_REFRESH_TOKEN` | Optional | Gmail refresh token |
| `DATABASE_URL` | Optional | Supabase PostgreSQL (defaults to SQLite) |
| `SUPABASE_URL` | Optional | Supabase project URL |
| `SUPABASE_ANON_KEY` | Optional | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase service role key |
| `UPSTASH_REDIS_URL` | Optional | Redis for caching |
| `LANGCHAIN_API_KEY` | Optional | LangSmith tracing |
| `LANGFUSE_PUBLIC_KEY` | Optional | Langfuse tracing |
| `APP_ENV` | Optional | `development` or `production` |
| `DEBUG` | Optional | Enable debug logging |
