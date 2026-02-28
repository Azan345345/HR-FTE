---
title: BowJob CV Parser
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
short_description: AI-powered CV/Resume parser - extracts structured JSON from PDFs
---

# CV Parser API

AI-powered CV/Resume parser that extracts structured JSON from PDF files using OpenAI GPT-4o-mini.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /parse` - Parse CV (upload PDF file)
- `GET /docs` - Interactive API documentation

## Usage

```bash
# Health check
curl https://abubakar-dev-bowjob-cv-parser.hf.space/health

# Parse a CV
curl -X POST https://abubakar-dev-bowjob-cv-parser.hf.space/parse \
  -F "file=@resume.pdf"
```

## Response Format

```json
{
  "success": true,
  "filename": "resume.pdf",
  "data": {
    "contact_info": { ... },
    "title": "Software Engineer",
    "professional_summary": "...",
    "work_experience": [ ... ],
    "education": [ ... ],
    "skills": [ ... ],
    "projects": [ ... ],
    "certifications": [ ... ],
    "total_years_of_experience": 5.0
  }
}
```

## Configuration

Set `OPENAI_API_KEY` in Space Settings > Repository secrets.
