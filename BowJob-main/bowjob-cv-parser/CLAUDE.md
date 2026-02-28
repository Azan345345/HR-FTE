# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CV Parser API v3 - An AI-powered CV/resume parser using OpenAI GPT-4o-mini. Accepts PDF file uploads and returns structured JSON with comprehensive CV information extraction.

## Development Commands

### Running the Application

```bash
# Development mode (with auto-reload)
python app_v3.py

# Production mode via Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Parse CV (file upload)
curl -X POST http://localhost:8000/parse \
  -F "file=@path/to/cv.pdf"

# Interactive API docs
open http://localhost:8000/docs
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Required environment variable: OPENAI_API_KEY
# Optional: PORT (default: 8000), ENV (production/development)
```

## Architecture

### Core Components

**app_v3.py** - FastAPI application that handles HTTP requests
- `/parse` endpoint accepts PDF file uploads via multipart/form-data
- Validates PDF files (checks magic bytes, file size)
- Creates temporary files for PDF processing
- Returns structured JSON with parsed CV data

**parser_v3.py** - OpenAI-powered CV extraction engine
- `CVParserV3` class manages the parsing workflow
- Uses PyPDF2 for text extraction from PDFs
- Implements OpenAI function calling with detailed structured schema
- Schema enforces NULL values for missing data (no placeholder generation)
- Calculates total years of experience excluding employment gaps

### Data Schema Design

The parser uses a comprehensive structured schema with these key sections:
- **contact_info**: name, email, phone, location, linkedin, website
- **title**: current or desired job title
- **professional_summary**: can be string or array depending on CV format
- **work_experience**: job history with descriptions (bullet points → array, paragraph → string)
- **education**: degrees with institutions and dates
- **projects**: personal/professional projects with technologies
- **skills**: categorized into technical_skills, soft_skills, languages
- **certifications**: professional certifications with issue/expiry dates
- **awards_scholarships**: honors and recognition
- **publications**: research papers and articles
- **total_years_of_experience**: calculated field that excludes employment gaps

### Key Implementation Details

**Flexible Description Handling**: Work experience, projects, and other description fields intelligently adapt to CV formatting:
- Bullet points in CV → Array of strings in JSON
- Continuous paragraph → Single string in JSON
- This preserves the original structure and improves readability

**Date Normalization**: Dates are standardized to YYYY-MM-DD format where possible, with fallbacks to YYYY when month/day unavailable. "Present" or "Current" used for ongoing roles.

**NULL-first Approach**: Missing information returns NULL rather than placeholder text, ensuring data integrity and downstream processing reliability.

**Experience Calculation**: `total_years_of_experience` accounts for overlapping positions and excludes gaps between jobs for accurate tenure measurement.

## API Dependencies

- **FastAPI**: Web framework with automatic OpenAPI documentation
- **OpenAI API**: GPT-4o-mini for CV parsing (pricing: $0.150/1M input tokens, $0.600/1M output tokens)
- **PyPDF2**: PDF text extraction
- **Uvicorn**: ASGI server for FastAPI

## File Upload Validation

The API performs multiple validation checks:
1. File extension must be .pdf
2. Minimum file size: 100 bytes
3. PDF magic bytes verification (%PDF header)
4. Temporary file handling with automatic cleanup

## Error Handling

All endpoints return proper HTTP status codes:
- 200: Success
- 400: Invalid file (not PDF, corrupted, too small)
- 500: Parsing failure or internal errors

Temporary files are cleaned up even on error conditions.

## Configuration

Environment variables (set in .env):
- `OPENAI_API_KEY`: Required for OpenAI API access
- `PORT`: Server port (default: 8000)
- `ENV`: "development" enables auto-reload, "production" disables it

CORS is configured for all origins (adjust in production).

## Railway Deployment

When deploying to Railway:

1. **Set Environment Variables**: In Railway dashboard, add `OPENAI_API_KEY` to your service's environment variables
2. **Port Configuration**: Railway automatically sets the `PORT` variable - no need to configure
3. **Health Check**: The `/health` endpoint works without API key configuration
4. **Lazy Initialization**: The parser initializes only when first needed, allowing the app to start even if the API key is temporarily unavailable

The application uses lazy initialization for the OpenAI parser to prevent startup failures when environment variables are not yet available.
