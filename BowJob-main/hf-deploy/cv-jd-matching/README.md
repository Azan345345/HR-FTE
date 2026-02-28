---
title: BowJob CV-JD Matching
emoji: 🎯
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
short_description: AI-powered CV analysis against job descriptions with scoring
---

# CV-JD Matching & Improvement API

AI-powered CV analysis against job descriptions with scoring and improvement suggestions using OpenAI GPT-4o.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /api/v1/analyze` - Analyze CV against job description
- `POST /api/v1/session` - Create chat session
- `POST /api/v1/chat` - Chat about CV improvements
- `POST /api/v1/approve` - Approve pending changes
- `GET /api/v1/session/{id}` - Get session state
- `GET /docs` - Interactive API documentation

## Usage

```bash
# Health check
curl https://abubakar-dev-bowjob-cv-jd-matching.hf.space/health

# Analyze CV against JD
curl -X POST https://abubakar-dev-bowjob-cv-jd-matching.hf.space/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "parsed_cv": { ... },
    "job_title": "Senior Software Engineer",
    "job_description": "We are looking for..."
  }'
```

## Response Format

```json
{
  "metadata": { ... },
  "scores": {
    "current_match_score": 72,
    "potential_score_after_changes": 92,
    "rating": "Good",
    "breakdown": {
      "skills_score": 25.5,
      "experience_score": 20.0,
      "education_score": 15.0,
      "projects_score": 5.0,
      "keywords_score": 6.5
    }
  },
  "cv_sections": { ... },
  "non_cv_sections": { ... },
  "session_info": {
    "session_id": "uuid",
    "chatbot_enabled": true
  }
}
```

## Scoring Weights

- Skills: 35 points
- Experience: 25 points
- Education: 15 points
- Projects: 15 points
- Keywords: 10 points

## Configuration

Set `OPENAI_API_KEY` in Space Settings > Repository secrets.
