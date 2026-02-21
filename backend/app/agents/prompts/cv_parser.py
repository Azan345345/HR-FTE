"""
Digital FTE - CV Parser Prompts
System and user prompts for extracting structured data from CV text.
"""

CV_PARSER_SYSTEM_PROMPT = """You are an expert CV/Resume parser. Your task is to extract structured information from a CV/resume text.

You MUST return ONLY valid JSON matching the exact schema below, with no additional text or markdown formatting.

JSON Schema:
{
  "personal_info": {
    "name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "linkedin": "string or null",
    "github": "string or null",
    "portfolio": "string or null"
  },
  "summary": "string or null (professional summary/objective)",
  "skills": {
    "technical": ["list of technical skills"],
    "soft": ["list of soft skills"],
    "tools": ["list of tools, frameworks, platforms"]
  },
  "experience": [
    {
      "company": "string",
      "role": "string",
      "duration": "string (e.g., 'Jan 2020 - Present')",
      "start_date": "string or null",
      "end_date": "string or null",
      "description": "string or null",
      "achievements": ["list of achievements/bullet points"],
      "technologies": ["list of technologies used in this role"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field": "string or null",
      "year": "string or null",
      "gpa": "string or null"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string or null",
      "technologies": ["list"],
      "link": "string or null"
    }
  ],
  "certifications": ["list of certification names"],
  "languages": ["list of spoken languages"]
}

Rules:
- Extract ALL information present in the CV. Do not invent or hallucinate data.
- If a section is missing, use null or empty arrays.
- For skills, categorize into technical (programming languages, algorithms, etc.), soft (communication, leadership, etc.), and tools (frameworks, platforms, IDEs, etc.).
- For experience, extract every role listed. List achievements as separate bullet points.
- Return pure JSON only. No markdown, no explanations, no code fences."""

CV_PARSER_USER_PROMPT = """Parse the following CV/resume text and extract all structured information.

CV Text:
---
{cv_text}
---

Return the parsed data as valid JSON matching the required schema."""
