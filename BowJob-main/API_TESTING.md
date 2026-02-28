# API Testing Guide

## Base URLs

- **CV Parser:** `http://localhost:8000`
- **CV-JD Matching:** `http://localhost:8001`

---

## 1. CV Parser Service (Port 8000)

### Health Check

```
GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "cv-parser-api-v3",
  "openai_configured": true
}
```

---

### Parse CV (Upload PDF)

```
POST http://localhost:8000/parse
Content-Type: multipart/form-data
```

**Postman Setup:**
1. Method: `POST`
2. URL: `http://localhost:8000/parse`
3. Body → form-data
4. Key: `file` (type: File)
5. Value: Select your PDF file

**Sample Response:**
```json
{
  "success": true,
  "filename": "john_doe_resume.pdf",
  "data": {
    "contact_info": {
      "full_name": "John Doe",
      "email": "john.doe@email.com",
      "phone": "+1-555-123-4567",
      "location": "San Francisco, CA",
      "linkedin": "linkedin.com/in/johndoe",
      "website": "github.com/johndoe"
    },
    "title": "Senior Software Engineer",
    "professional_summary": "Experienced software engineer with 8+ years of expertise in building scalable web applications and microservices.",
    "work_experience": [
      {
        "job_title": "Senior Software Engineer",
        "company": "Tech Corp",
        "location": "San Francisco, CA",
        "start_date": "2020-01-01",
        "end_date": "Present",
        "description": [
          "Led development of microservices architecture serving 10M+ users",
          "Reduced API response time by 40% through optimization",
          "Mentored team of 5 junior developers"
        ]
      }
    ],
    "education": [
      {
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "institution": "Stanford University",
        "location": "Stanford, CA",
        "start_date": "2012",
        "end_date": "2016",
        "gpa": "3.8"
      }
    ],
    "skills": {
      "technical_skills": ["Python", "JavaScript", "React", "Node.js", "AWS", "Docker", "Kubernetes"],
      "soft_skills": ["Leadership", "Communication", "Problem Solving"],
      "languages": [
        {"language": "English", "proficiency": "Native"},
        {"language": "Spanish", "proficiency": "Intermediate"}
      ]
    },
    "projects": [
      {
        "name": "E-commerce Platform",
        "description": "Built scalable e-commerce platform handling 100K daily transactions",
        "technologies": ["Python", "Django", "PostgreSQL", "Redis"],
        "date": "2022"
      }
    ],
    "certifications": [
      {
        "name": "AWS Solutions Architect",
        "issuing_organization": "Amazon Web Services",
        "issue_date": "2023-01",
        "expiry_date": "2026-01"
      }
    ],
    "total_years_of_experience": 8.5
  }
}
```

---

## 2. CV-JD Matching Service (Port 8001)

### Health Check

```
GET http://localhost:8001/health
```

---

### Analyze CV Against Job Description

```
POST http://localhost:8001/api/v1/analyze
Content-Type: application/json
```

**Sample Request Body:**
```json
{
  "parsed_cv": {
    "contact_info": {
      "full_name": "John Doe",
      "email": "john.doe@email.com",
      "phone": "+1-555-123-4567",
      "location": "San Francisco, CA",
      "linkedin": "linkedin.com/in/johndoe",
      "website": "github.com/johndoe"
    },
    "title": "Senior Software Engineer",
    "professional_summary": "Experienced software engineer with 8+ years of expertise in building scalable web applications and microservices. Proficient in Python, JavaScript, and cloud technologies.",
    "work_experience": [
      {
        "job_title": "Senior Software Engineer",
        "company": "Tech Corp",
        "location": "San Francisco, CA",
        "start_date": "2020-01-01",
        "end_date": "Present",
        "description": [
          "Led development of microservices architecture serving 10M+ users",
          "Reduced API response time by 40% through optimization",
          "Mentored team of 5 junior developers",
          "Implemented CI/CD pipelines using Jenkins and GitHub Actions"
        ]
      },
      {
        "job_title": "Software Engineer",
        "company": "StartupXYZ",
        "location": "Palo Alto, CA",
        "start_date": "2016-06-01",
        "end_date": "2019-12-31",
        "description": [
          "Developed RESTful APIs using Python and Flask",
          "Built real-time data processing pipeline using Apache Kafka",
          "Collaborated with product team to deliver features on schedule"
        ]
      }
    ],
    "education": [
      {
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "institution": "Stanford University",
        "location": "Stanford, CA",
        "start_date": "2012",
        "end_date": "2016",
        "gpa": "3.8"
      }
    ],
    "skills": {
      "technical_skills": [
        "Python",
        "JavaScript",
        "TypeScript",
        "React",
        "Node.js",
        "AWS",
        "Docker",
        "Kubernetes",
        "PostgreSQL",
        "MongoDB",
        "Redis",
        "GraphQL",
        "REST APIs"
      ],
      "soft_skills": [
        "Leadership",
        "Communication",
        "Problem Solving",
        "Team Collaboration"
      ],
      "languages": [
        {"language": "English", "proficiency": "Native"},
        {"language": "Spanish", "proficiency": "Intermediate"}
      ]
    },
    "projects": [
      {
        "name": "E-commerce Platform",
        "description": "Built scalable e-commerce platform handling 100K daily transactions with microservices architecture",
        "technologies": ["Python", "Django", "PostgreSQL", "Redis", "Docker"],
        "date": "2022"
      },
      {
        "name": "Real-time Analytics Dashboard",
        "description": "Developed real-time analytics dashboard for monitoring business metrics",
        "technologies": ["React", "Node.js", "WebSocket", "D3.js"],
        "date": "2021"
      }
    ],
    "certifications": [
      {
        "name": "AWS Solutions Architect - Professional",
        "issuing_organization": "Amazon Web Services",
        "issue_date": "2023-01",
        "expiry_date": "2026-01"
      },
      {
        "name": "Certified Kubernetes Administrator",
        "issuing_organization": "CNCF",
        "issue_date": "2022-06"
      }
    ],
    "total_years_of_experience": 8.5
  },
  "job_title": "Staff Software Engineer",
  "job_description": "We are looking for a Staff Software Engineer to join our growing team.\n\nResponsibilities:\n- Design and implement scalable backend services\n- Lead technical architecture decisions\n- Mentor and guide junior engineers\n- Collaborate with product and design teams\n- Drive best practices in code quality and testing\n- Participate in on-call rotation\n\nRequirements:\n- 7+ years of software engineering experience\n- Strong proficiency in Python or Go\n- Experience with cloud platforms (AWS, GCP, or Azure)\n- Experience with containerization (Docker, Kubernetes)\n- Strong understanding of distributed systems\n- Experience with SQL and NoSQL databases\n- Excellent communication skills\n\nNice to have:\n- Experience with machine learning pipelines\n- Contributions to open source projects\n- Experience with Terraform or infrastructure as code\n- Knowledge of GraphQL",
  "options": {
    "include_full_cv": true,
    "generate_missing_projects": true,
    "tone_analysis": true,
    "keyword_optimization": true
  }
}
```

**Sample Response:**
```json
{
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "processed_at": "2024-01-15T10:30:00Z",
    "job_title": "Staff Software Engineer",
    "processing_time_ms": 2500
  },
  "matching_analysis": {
    "overall_score": {
      "percentage": 78,
      "rating": "Good",
      "confidence": 0.85
    },
    "skills_analysis": {
      "technical_skills": {
        "matched": [
          {
            "skill": "Python",
            "cv_mention": "8+ years experience, used in multiple projects",
            "jd_requirement": "Strong proficiency in Python or Go",
            "match_strength": "exact"
          },
          {
            "skill": "AWS",
            "cv_mention": "AWS Solutions Architect certification",
            "jd_requirement": "Experience with cloud platforms",
            "match_strength": "exact"
          },
          {
            "skill": "Docker",
            "cv_mention": "Listed in technical skills and projects",
            "jd_requirement": "Experience with containerization",
            "match_strength": "exact"
          },
          {
            "skill": "Kubernetes",
            "cv_mention": "CKA certification",
            "jd_requirement": "Experience with containerization",
            "match_strength": "exact"
          }
        ],
        "missing": [
          {
            "skill": "Go",
            "jd_context": "Strong proficiency in Python or Go",
            "importance": "preferred",
            "suggestion": "Consider learning Go as an alternative backend language"
          },
          {
            "skill": "Terraform",
            "jd_context": "Experience with infrastructure as code",
            "importance": "nice-to-have",
            "suggestion": "Add Terraform to expand IaC capabilities"
          }
        ]
      }
    },
    "detailed_scores": {
      "technical_skills_score": 82,
      "soft_skills_score": 75,
      "experience_score": 85,
      "education_score": 90,
      "keywords_score": 70
    }
  },
  "improvements": {
    "professional_tone": [
      {
        "section": "work_experience[0].description[0]",
        "field_path": "work_experience.0.description.0",
        "original_text": "Led development of microservices architecture serving 10M+ users",
        "modified_text": "Architected and led development of enterprise microservices platform, scaling to support 10M+ active users while maintaining 99.9% uptime",
        "improvement_type": "quantification",
        "explanation": "Added specific metrics and outcome to demonstrate impact"
      }
    ],
    "quantification": [
      {
        "section": "work_experience[1].description[0]",
        "original_text": "Developed RESTful APIs using Python and Flask",
        "suggested_text": "Developed 15+ RESTful APIs using Python and Flask, reducing integration time by 30% for partner teams",
        "metrics_added": ["15+ APIs", "30% reduction"],
        "explanation": "Added specific numbers to quantify contribution"
      }
    ]
  },
  "projects": {
    "missing": [
      {
        "suggested_project_name": "ML Pipeline Infrastructure",
        "suggested_description": "Design and implement scalable machine learning pipeline for model training and deployment using Python, Docker, and Kubernetes",
        "reason_from_jd": "JD mentions 'Experience with machine learning pipelines' as nice-to-have",
        "required_skills": ["Python", "Docker", "Kubernetes"],
        "suggested_technologies": ["MLflow", "Kubeflow", "Apache Airflow"],
        "placement_recommendation": {
          "location": "projects",
          "rationale": "Would strengthen candidacy by addressing ML pipeline gap"
        }
      }
    ]
  },
  "keywords": {
    "required_keywords": [
      {
        "keyword": "distributed systems",
        "category": "technology",
        "jd_frequency": 1,
        "cv_presence": false,
        "recommended_additions": ["professional_summary", "work_experience descriptions"]
      },
      {
        "keyword": "on-call",
        "category": "methodology",
        "jd_frequency": 1,
        "cv_presence": false,
        "recommended_additions": ["work_experience - mention incident response experience"]
      }
    ],
    "optimization_suggestions": [
      {
        "current_term": "REST APIs",
        "optimized_term": "RESTful microservices",
        "reason": "Better alignment with JD terminology"
      }
    ]
  },
  "strengths": [
    "Strong match on core technical requirements (Python, AWS, Docker, Kubernetes)",
    "Proven leadership experience mentoring junior developers",
    "Solid educational background from top university",
    "Relevant certifications (AWS, CKA) demonstrate continued learning",
    "Experience with high-scale systems (10M+ users)"
  ],
  "concerns": [
    "No explicit mention of distributed systems experience",
    "Missing Go language proficiency (alternative to Python)",
    "No machine learning pipeline experience mentioned",
    "On-call/incident response experience not highlighted"
  ],
  "interview_questions": [
    "Can you describe a complex distributed system you've designed and the trade-offs you made?",
    "How have you handled production incidents and what was your on-call experience?",
    "Tell me about a time you had to make a difficult technical architecture decision.",
    "How do you approach mentoring junior engineers?"
  ],
  "session_info": {
    "session_id": "abc123-def456-ghi789",
    "expires_at": "2024-01-16T10:30:00Z",
    "chatbot_enabled": true
  }
}
```

---

### Chat with Analysis (Follow-up Questions)

```
POST http://localhost:8001/api/v1/chat
Content-Type: application/json
```

**Sample Request:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "message": "How can I improve my chances for this role? What skills should I highlight more?"
}
```

**Sample Response:**
```json
{
  "message": "Based on the analysis, here are my top recommendations to improve your chances:\n\n1. **Highlight Distributed Systems Experience**: Your microservices work clearly involves distributed systems. Add explicit mentions of concepts like 'distributed systems', 'fault tolerance', and 'eventual consistency' in your experience descriptions.\n\n2. **Add On-Call Experience**: If you've participated in incident response or on-call rotations, make sure to mention this. It's a key responsibility in the JD.\n\n3. **Consider a ML Pipeline Project**: The JD lists ML pipeline experience as nice-to-have. Even a personal project using tools like MLflow or Kubeflow would strengthen your application.\n\n4. **Quantify More Achievements**: Your current descriptions are good, but adding more specific metrics (response times, cost savings, team velocity improvements) would make them stronger.\n\nWould you like me to help rewrite any specific section of your CV?",
  "session_id": "abc123-def456-ghi789",
  "suggestions": []
}
```

---

### Get Session Info

```
GET http://localhost:8001/api/v1/session/{session_id}
```

**Sample Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "job_title": "Staff Software Engineer",
  "chat_history_count": 2,
  "analysis_available": true
}
```

---

### Approve Changes

```
POST http://localhost:8001/api/v1/approve
Content-Type: application/json
```

**Sample Request:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "change_ids": ["improvement_1", "improvement_2", "project_suggestion_1"]
}
```

---

## Postman Collection Import

You can import these as a Postman collection. Create a new collection and add the following environment variables:

| Variable | Value |
|----------|-------|
| `base_url_parser` | `http://localhost:8000` |
| `base_url_matching` | `http://localhost:8001` |

---

## cURL Commands for Quick Testing

### Test CV Parser Health
```bash
curl http://localhost:8000/health
```

### Test CV-JD Matching Health
```bash
curl http://localhost:8001/health
```

### Parse CV (replace with your file path)
```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@/path/to/your/resume.pdf"
```

### Analyze CV (minimal example)
```bash
curl -X POST http://localhost:8001/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "parsed_cv": {
      "contact_info": {"full_name": "John Doe", "email": "john@email.com"},
      "title": "Software Engineer",
      "work_experience": [{"job_title": "Developer", "company": "ABC Corp", "description": ["Built web apps"]}],
      "skills": {"technical_skills": ["Python", "JavaScript", "AWS"]}
    },
    "job_title": "Senior Developer",
    "job_description": "Looking for a senior developer with Python and AWS experience."
  }'
```
