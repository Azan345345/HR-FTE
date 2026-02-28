# CV Improvement System - Technical Specification

## CRITICAL RULES - READ FIRST

### ⚠️ NO PLACEHOLDERS
- **NEVER** use placeholder syntax like `{percentage}%`, `${amount}`, `{timeframe}`
- **ALWAYS** generate realistic, believable metrics: `32%`, `$1.2M`, `4 months`
- Infer reasonable metrics based on role, industry, and context

### ⚠️ EXACT SECTION NAMES ONLY
- Project placement can **ONLY** suggest sections that **EXIST** in input CV
- Use **EXACT** section names from input JSON: `projects`, `work_experience`, etc.
- **NEVER** suggest `projects_section` - use `projects` (exact name)
- Check `available_sections` before suggesting placement

### ⚠️ PRESERVE ORIGINAL TEXT
- In `suggested_improvements`, the `original` field must contain **EXACT** original text
- **NO modifications** to original text whatsoever
- Copy original content character-for-character

### ⚠️ NO cv_content IN RESPONSE
- Response does **NOT** include full original/modified CV
- Only improvements, suggestions, and analysis are returned

---

## Project Overview

An AI-powered CV/Resume improvement system that analyzes parsed CVs against Job Descriptions (JD) and returns comprehensive JSON responses with improvements, suggestions, and matching analysis.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Input Specification](#input-specification)
3. [Output Specification](#output-specification)
4. [Core Algorithms](#core-algorithms)
5. [Professional Tone Rules](#professional-tone-rules)
6. [Project Placement Logic](#project-placement-logic)
7. [Scoring Algorithm](#scoring-algorithm)
8. [OpenAI Integration](#openai-integration)
9. [Stateful Chatbot System](#stateful-chatbot-system)
10. [API Endpoints](#api-endpoints)
11. [Database Schema](#database-schema)
12. [Implementation Guide](#implementation-guide)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CV IMPROVEMENT SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐  │
│   │  INPUT API   │────▶│  CV ANALYZER     │────▶│  IMPROVEMENT ENGINE   │  │
│   │              │     │  (OpenAI GPT-4)  │     │  (Rule-based + AI)    │  │
│   │ - Parsed CV  │     │                  │     │                        │  │
│   │ - Job Title  │     │ - Extract Skills │     │ - Tone Enhancement    │  │
│   │ - JD Text    │     │ - Parse Sections │     │ - Content Suggestions │  │
│   └──────────────┘     │ - Match Analysis │     │ - Gap Identification  │  │
│                        └──────────────────┘     └────────────────────────┘  │
│                                                            │                 │
│                                                            ▼                 │
│   ┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐  │
│   │ OUTPUT API   │◀────│  RESPONSE        │◀────│  SCORING ENGINE       │  │
│   │              │     │  BUILDER         │     │                        │  │
│   │ - Full JSON  │     │                  │     │ - JD Match Score      │  │
│   │ - Modified   │     │ - Structure JSON │     │ - Skill Match         │  │
│   │ - Suggested  │     │ - Mark Changes   │     │ - Section Analysis    │  │
│   └──────────────┘     └──────────────────┘     └────────────────────────┘  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                     STATEFUL CHATBOT SESSION                          │  │
│   │  - Session Management  - Context Retention  - Incremental Updates    │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Input Specification

### Standard Parsed CV JSON Format

```json
{
  "personal_info": {
    "name": "string | null",
    "email": "string | null",
    "phone": "string | null",
    "linkedin": "string | null",
    "github": "string | null",
    "portfolio": "string | null",
    "address": "string | null",
    "city": "string | null",
    "country": "string | null"
  },
  "summary": "string | null",
  "work_experience": [
    {
      "company": "string",
      "job_title": "string",
      "start_date": "string",
      "end_date": "string | null",
      "is_current": "boolean",
      "location": "string | null",
      "description": "string",
      "achievements": ["string"],
      "projects": [
        {
          "name": "string",
          "description": "string",
          "technologies": ["string"]
        }
      ]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field_of_study": "string",
      "start_date": "string",
      "end_date": "string | null",
      "gpa": "string | null",
      "achievements": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft": ["string"],
    "languages": ["string"],
    "tools": ["string"]
  },
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "date": "string",
      "expiry": "string | null",
      "credential_id": "string | null"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "technologies": ["string"],
      "url": "string | null",
      "start_date": "string | null",
      "end_date": "string | null"
    }
  ],
  "awards": [
    {
      "name": "string",
      "issuer": "string",
      "date": "string",
      "description": "string | null"
    }
  ],
  "publications": [
    {
      "title": "string",
      "publication": "string",
      "date": "string",
      "url": "string | null"
    }
  ],
  "volunteer": [
    {
      "organization": "string",
      "role": "string",
      "description": "string",
      "start_date": "string",
      "end_date": "string | null"
    }
  ],
  "references": [
    {
      "name": "string",
      "title": "string",
      "company": "string",
      "contact": "string"
    }
  ]
}
```

### API Request Structure

```json
{
  "parsed_cv": { /* Standard CV JSON above */ },
  "job_title": "string",
  "job_description": "string",
  "options": {
    "include_full_cv": true,
    "generate_missing_projects": true,
    "tone_analysis": true,
    "keyword_optimization": true
  }
}
```

---

## Output Specification

### Complete Response JSON Structure

```json
{
  "metadata": {
    "request_id": "uuid",
    "processed_at": "ISO8601 timestamp",
    "job_title": "string",
    "processing_time_ms": "number"
  },
  
  "matching_analysis": {
    "overall_score": {
      "percentage": "number (0-100)",
      "rating": "string (Poor|Fair|Good|Excellent)",
      "confidence": "number (0-1)"
    },
    "skills_analysis": {
      "technical_skills": {
        "matched": [
          {
            "skill": "string",
            "cv_mention": "string (where found in CV)",
            "jd_requirement": "string (how mentioned in JD)",
            "match_strength": "string (exact|partial|inferred)"
          }
        ],
        "missing": [
          {
            "skill": "string",
            "jd_context": "string (how mentioned in JD)",
            "importance": "string (required|preferred|nice-to-have)",
            "suggestion": "string (how to address this gap)"
          }
        ]
      },
      "soft_skills": {
        "matched": [/* same structure */],
        "missing": [/* same structure */]
      }
    },
    "experience_analysis": {
      "relevance_score": "number (0-100)",
      "depth_match": {
        "jd_requires": "string (junior|mid|senior|expert level depth)",
        "cv_demonstrates": "string (assessed depth level)",
        "gap_analysis": "string (description of depth gap if any)"
      },
      "relevant_experiences": [
        {
          "company": "string",
          "role": "string",
          "relevance_percentage": "number",
          "matching_responsibilities": ["string"],
          "missing_aspects": ["string"]
        }
      ]
    },
    "projects_relevancy": {
      "relevance_score": "number (0-100)",
      "jd_project_requirements": ["string (what kind of projects JD expects)"],
      "matched_projects": [
        {
          "project_name": "string",
          "relevance_to_jd": "string",
          "matching_technologies": ["string"],
          "demonstrates_skills": ["string"]
        }
      ],
      "gaps": [
        {
          "jd_expectation": "string",
          "current_coverage": "string (none|partial|insufficient depth)",
          "recommendation": "string"
        }
      ]
    },
    "sections_analysis": {
      "present": ["string (section names)"],
      "missing": ["string (recommended sections)"],
      "recommendations": [
        {
          "section": "string",
          "reason": "string",
          "priority": "string (high|medium|low)"
        }
      ]
    }
  },
  
  "improvements": {
    "grammatical_tone": [
      {
        "section": "string (e.g., work_experience[0].description)",
        "field_path": "string (JSON path to the field)",
        "original_text": "string",
        "modified_text": "string",
        "improvement_type": "string (grammar|tone|clarity|quantification)",
        "explanation": "string",
        "applied_rule": "string (which rule/pattern was applied)"
      }
    ],
    "professional_tone": [
      {
        "section": "string",
        "field_path": "string",
        "original_text": "string",
        "modified_text": "string",
        "pattern_used": "string (the strong pattern template)",
        "metrics_added": ["string (what metrics were suggested)"],
        "explanation": "string"
      }
    ]
  },
  
  "projects": {
    "missing": [
      {
        "suggested_project_name": "string",
        "suggested_description": "string",
        "reason_from_jd": "string (why this is needed based on JD)",
        "required_skills": ["string"],
        "suggested_technologies": ["string"],
        "placement_recommendation": {
          "location": "string (EXACT section name from input JSON: 'projects' OR 'work_experience')",
          "available_sections": ["string (list of sections present in input CV)"],
          "company_index": "number | null (if under work_experience, index of company)",
          "company_name": "string | null (actual company name from input)",
          "rationale": "string"
        }
      }
    ],
    "suggested_improvements": [
      {
        "section": "string (EXACT section name from input)",
        "field_path": "string",
        "project_name": "string",
        "original": {
          "description": "string (EXACT original text - NO modifications)",
          "technologies": ["string (EXACT original technologies)"]
        },
        "suggested": {
          "description": "string",
          "technologies": ["string"],
          "additional_details": "string"
        },
        "jd_alignment": "string (how this aligns better with JD)",
        "improvement_areas": ["string"]
      }
    ]
  },
  
  "keywords": {
    "required_keywords": [
      {
        "keyword": "string",
        "category": "string (skill|technology|methodology|certification)",
        "jd_frequency": "number (times mentioned in JD)",
        "cv_presence": "boolean",
        "cv_frequency": "number",
        "recommended_additions": ["string (where to add)"]
      }
    ],
    "optimization_suggestions": [
      {
        "current_term": "string",
        "optimized_term": "string",
        "reason": "string"
      }
    ]
  },
  
  "missing_essentials": {
    "critical": [
      {
        "field": "string (e.g., email, phone)",
        "importance": "string",
        "suggestion": "string"
      }
    ],
    "recommended": [
      {
        "field": "string",
        "reason": "string",
        "example": "string"
      }
    ]
  },
  
  "session_info": {
    "session_id": "uuid",
    "expires_at": "ISO8601 timestamp",
    "chatbot_enabled": "boolean"
  }
}
```

---

## Core Algorithms

### Algorithm 1: CV-JD Matching Score Calculator

```python
"""
CV-JD Matching Score Algorithm
------------------------------
Calculates overall matching percentage based on multiple weighted factors.
"""

def calculate_matching_score(cv: dict, jd: dict) -> dict:
    """
    Main scoring function that aggregates all sub-scores.
    
    Weights Configuration:
    - Technical Skills: 35%
    - Soft Skills: 15%
    - Experience Relevance: 25%
    - Education Match: 10%
    - Keywords/Certifications: 15%
    
    Returns:
        dict with percentage, rating, and breakdown
    """
    
    weights = {
        'technical_skills': 0.35,
        'soft_skills': 0.15,
        'experience_relevance': 0.25,
        'education_match': 0.10,
        'keywords_certs': 0.15
    }
    
    # Sub-score calculations
    scores = {
        'technical_skills': calculate_technical_skill_match(cv, jd),
        'soft_skills': calculate_soft_skill_match(cv, jd),
        'experience_relevance': calculate_experience_relevance(cv, jd),
        'education_match': calculate_education_match(cv, jd),
        'keywords_certs': calculate_keyword_match(cv, jd)
    }
    
    # Weighted aggregation
    total_score = sum(
        scores[key] * weights[key] 
        for key in weights
    )
    
    # Rating determination
    rating = determine_rating(total_score)
    
    return {
        'percentage': round(total_score, 2),
        'rating': rating,
        'breakdown': scores,
        'confidence': calculate_confidence(cv, jd)
    }


def calculate_technical_skill_match(cv: dict, jd: dict) -> float:
    """
    Technical skills matching using semantic similarity.
    
    Process:
    1. Extract all technical skills from JD using NLP
    2. Extract all technical skills from CV
    3. Perform exact matching
    4. Perform semantic similarity for partial matches
    5. Weight by skill importance in JD
    """
    
    jd_skills = extract_technical_skills_from_jd(jd)  # Returns list of (skill, importance_weight)
    cv_skills = extract_all_skills_from_cv(cv)  # Flattened list from all sections
    
    matched_score = 0
    total_weight = sum(weight for _, weight in jd_skills)
    
    for skill, weight in jd_skills:
        match_type = find_skill_match(skill, cv_skills)
        
        if match_type == 'exact':
            matched_score += weight * 1.0
        elif match_type == 'partial':
            matched_score += weight * 0.7
        elif match_type == 'inferred':  # Found in project descriptions, etc.
            matched_score += weight * 0.5
    
    return (matched_score / total_weight) * 100 if total_weight > 0 else 0


def determine_rating(score: float) -> str:
    """Convert percentage to rating."""
    if score >= 85:
        return 'Excellent'
    elif score >= 70:
        return 'Good'
    elif score >= 50:
        return 'Fair'
    else:
        return 'Poor'
```

### Algorithm 2: Professional Tone Analyzer

```python
"""
Professional Tone Analysis Engine
---------------------------------
Identifies weak statements and converts to strong, metrics-driven content.
"""

# Weak Pattern Indicators
WEAK_PATTERNS = [
    r'^I\s+(improved|enhanced|developed|managed|worked|handled|helped)',
    r'^(Improved|Enhanced|Developed|Managed|Worked|Handled|Helped)\s+',
    r'various\s+',
    r'multiple\s+',
    r'several\s+',
    r'(responsible for|duties included|tasks involved)',
    r'(etc|and so on|and more)',
    r'^(Did|Made|Got|Had)\s+',
]

# Strong Pattern Template
STRONG_PATTERN_TEMPLATE = """
Implemented {action/strategy} using {method/technology} which resulted in {specific measurable outcome} within {time period}.
"""

def analyze_statement(text: str, job_title: str, context: dict) -> dict:
    """
    Analyze a single statement for professional tone.
    
    Args:
        text: The statement to analyze
        job_title: Target job title for context-aware suggestions
        context: Additional context (company, industry, etc.)
    
    Returns:
        Analysis result with improvement suggestions
    """
    
    analysis = {
        'original': text,
        'is_weak': False,
        'weakness_reasons': [],
        'suggested_improvement': None,
        'applied_patterns': []
    }
    
    # Check for weak patterns
    for pattern in WEAK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            analysis['is_weak'] = True
            analysis['weakness_reasons'].append(pattern)
    
    # Check for lack of metrics
    if not contains_metrics(text):
        analysis['is_weak'] = True
        analysis['weakness_reasons'].append('no_quantifiable_metrics')
    
    # Check for passive voice
    if is_passive_voice(text):
        analysis['is_weak'] = True
        analysis['weakness_reasons'].append('passive_voice')
    
    # Generate improvement if weak
    if analysis['is_weak']:
        analysis['suggested_improvement'] = generate_strong_statement(
            text, job_title, context
        )
    
    return analysis


def generate_strong_statement(weak_text: str, job_title: str, context: dict) -> str:
    """
    Transform weak statement to strong using LLM.
    
    CRITICAL: Do NOT use any placeholders. Generate realistic metrics.
    """
    
    prompt = f"""
    Transform this weak CV statement into a strong, metrics-driven achievement.
    
    Job Title Context: {job_title}
    Original Statement: {weak_text}
    
    Rules:
    1. Use action verbs (Implemented, Designed, Achieved, Spearheaded, Orchestrated)
    2. Include specific metrics (percentages, dollar amounts, time savings)
    3. Mention technologies/methods used
    4. Include timeframes where possible
    5. Focus on impact and results
    
    Pattern to follow:
    "Implemented [action/strategy] using [method/technology] which resulted in [specific measurable outcome] within [time period]."
    
    CRITICAL - NO PLACEHOLDERS:
    - Do NOT use placeholder syntax like {{percentage}}%, ${{amount}}, or {{timeframe}}
    - Generate REALISTIC, BELIEVABLE metrics based on the context
    - Use actual numbers: "32%", "$1.2M", "4 months", "15 team members"
    - If the original text hints at scale, use appropriate metrics
    - For vague statements, infer reasonable metrics based on typical outcomes for the role
    
    Examples of what to generate:
    ✓ "Reduced API latency by 48% by optimizing database queries"
    ✓ "Led team of 8 engineers to deliver $2.3M project 3 weeks ahead of schedule"
    ✓ "Increased customer retention by 23% through implementing NPS feedback system"
    
    Examples of what NOT to generate:
    ✗ "Reduced latency by {{percentage}}%"
    ✗ "Led team to deliver ${{amount}} project"
    ✗ "Increased retention by X%"
    
    Return ONLY the improved statement with real metrics.
    """
    
    # Call OpenAI API
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": get_role_specific_system_prompt(job_title)},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content
```

### Algorithm 3: Project Gap Analyzer

```python
"""
Project Gap Analysis Engine
---------------------------
Identifies missing and partial projects based on JD requirements.
"""

def analyze_project_gaps(cv: dict, jd_requirements: dict) -> dict:
    """
    Main project gap analysis function.
    
    Returns:
        - missing: Projects completely absent from CV
        - partial: Projects present but need enhancement
    
    CRITICAL: In partial projects, 'original' field must contain
    EXACT original text with NO modifications whatsoever.
    """
    
    # Extract project requirements from JD
    required_project_types = extract_project_requirements(jd_requirements)
    
    # Get all projects from CV (both standalone and under experience)
    cv_projects = collect_all_cv_projects(cv)
    
    # Identify available sections for placement
    available_sections = identify_available_sections(cv)
    
    missing_projects = []
    partial_projects = []
    
    for req in required_project_types:
        match_result = find_project_match(req, cv_projects)
        
        if match_result['match_type'] == 'none':
            # Only suggest placement in sections that EXIST
            placement = determine_project_placement(cv, req, req.get('technologies', []))
            
            if placement['location']:  # Only add if valid placement exists
                missing_projects.append({
                    'requirement': req,
                    'suggested_project': generate_project_suggestion(req, cv),
                    'placement_recommendation': placement
                })
        elif match_result['match_type'] == 'partial':
            # CRITICAL: Preserve original text EXACTLY
            original_project = match_result['matched_project']
            
            partial_projects.append({
                'requirement': req,
                'existing_project': original_project,
                'field_path': match_result['field_path'],
                'original': {
                    # EXACT original text - NO changes
                    'description': original_project.get('description', ''),
                    'technologies': original_project.get('technologies', []).copy()
                },
                'suggested': generate_project_enhancement(
                    original_project,
                    req,
                    match_result['gaps']
                ),
                'gaps': match_result['gaps'],
                'improvement_areas': match_result['improvement_areas']
            })
    
    return {
        'missing': missing_projects,
        'suggested_improvements': partial_projects,
        'available_sections': available_sections
    }


def collect_all_cv_projects(cv: dict) -> list:
    """
    Collect projects from all CV sections.
    
    Sources:
    1. Dedicated projects section
    2. Projects under work_experience
    3. Project descriptions in achievements
    """
    
    all_projects = []
    
    # From projects section
    if cv.get('projects'):
        for project in cv['projects']:
            all_projects.append({
                'source': 'projects_section',
                'data': project
            })
    
    # From work experience
    for i, exp in enumerate(cv.get('work_experience', [])):
        if exp.get('projects'):
            for project in exp['projects']:
                all_projects.append({
                    'source': f'work_experience[{i}]',
                    'company': exp.get('company'),
                    'data': project
                })
        
        # Also check achievements for project-like content
        for achievement in exp.get('achievements', []):
            if is_project_description(achievement):
                all_projects.append({
                    'source': f'work_experience[{i}].achievements',
                    'company': exp.get('company'),
                    'data': {'description': achievement}
                })
    
    return all_projects


def generate_project_suggestion(requirement: dict, cv: dict) -> dict:
    """
    Generate a project suggestion based on JD requirement and CV context.
    CRITICAL: Do NOT use placeholders. Generate realistic details.
    """
    
    prompt = f"""
    Based on this job requirement and the candidate's background, suggest a project they could add.
    
    Requirement: {requirement}
    Candidate Skills: {cv.get('skills', {})}
    Candidate Experience Summary: {summarize_experience(cv)}
    
    Generate a realistic project suggestion that:
    1. Aligns with the JD requirement
    2. Is believable given the candidate's background
    3. Uses specific technologies mentioned in the JD
    4. Includes measurable outcomes with REAL numbers (not placeholders)
    
    CRITICAL - NO PLACEHOLDERS:
    - Do NOT use {{placeholder}} syntax anywhere
    - Use realistic metrics: "27%", "3 months", "$45K savings", "15,000 users"
    - Make the project scale appropriate for the candidate's experience level
    
    Return JSON format:
    {{
        "name": "Actual Project Name (not placeholder)",
        "description": "Detailed description with real metrics like 'reduced processing time by 35%'",
        "technologies": ["Python", "AWS Lambda", "PostgreSQL"],
        "suggested_duration": "4 months"
    }}
    """
    
    # Call OpenAI API and parse response
    response = call_openai_json(prompt)
    return response
```

---

## Professional Tone Rules

### Role-Specific Transformation Rules

```python
"""
Professional Tone Rules by Job Category
---------------------------------------
Each role has specific patterns for strong statements.
"""

ROLE_PATTERNS = {
    'sales': {
        'weak_examples': [
            "I enhanced sales.",
            "I improved customer relations.",
            "Managed client accounts.",
            "Increased revenue."
        ],
        'strong_patterns': [
            "Implemented a targeted outbound strategy that boosted monthly sales by 32% within 4 months.",
            "Closed $1.2M in new B2B accounts by designing a personalized pitch framework.",
            "Exceeded quarterly quota by 127% through strategic account management of 45 enterprise clients.",
            "Generated $850K pipeline by developing and executing ABM campaigns targeting healthcare sector."
        ],
        'key_metrics': ['revenue', 'quota achievement', 'deal size', 'conversion rate', 'pipeline value'],
        'action_verbs': ['Closed', 'Generated', 'Negotiated', 'Secured', 'Expanded', 'Captured']
    },
    
    'software_developer': {
        'weak_examples': [
            "I developed features.",
            "I fixed bugs.",
            "Worked on the backend.",
            "Improved code quality."
        ],
        'strong_patterns': [
            "Designed and deployed a recommendation algorithm improving result accuracy by 27%, increasing user engagement by 35%.",
            "Reduced API latency by 48% by optimizing database queries and introducing Redis caching.",
            "Implemented CI/CD pipelines cutting release time from 3 days to 4 hours.",
            "Architected microservices handling 2.5M requests/day with 99.97% uptime."
        ],
        'key_metrics': ['latency', 'uptime', 'performance', 'code coverage', 'deployment frequency'],
        'action_verbs': ['Architected', 'Engineered', 'Optimized', 'Refactored', 'Automated', 'Deployed']
    },
    
    'data_scientist': {
        'weak_examples': [
            "Built ML models.",
            "Analyzed data.",
            "Created dashboards.",
            "Worked with big data."
        ],
        'strong_patterns': [
            "Developed a gradient boosting model achieving 94.3% accuracy, resulting in $2.1M annual cost savings.",
            "Built automated ETL pipeline processing 15M records daily, reducing manual work by 85%.",
            "Designed A/B testing framework that drove 23% improvement in user conversion rates.",
            "Created predictive analytics solution forecasting customer churn with 89% accuracy."
        ],
        'key_metrics': ['accuracy', 'AUC', 'F1-score', 'processing time', 'cost savings'],
        'action_verbs': ['Modeled', 'Predicted', 'Quantified', 'Discovered', 'Validated', 'Trained']
    },
    
    'project_manager': {
        'weak_examples': [
            "Managed projects.",
            "Led team meetings.",
            "Oversaw deliverables.",
            "Coordinated with stakeholders."
        ],
        'strong_patterns': [
            "Led cross-functional team of 12 to deliver $3.5M project 3 weeks ahead of schedule.",
            "Reduced project delivery time by 40% through implementation of Agile methodology.",
            "Managed portfolio of 8 concurrent projects with combined budget of $12M.",
            "Achieved 96% stakeholder satisfaction score through structured communication framework."
        ],
        'key_metrics': ['budget', 'timeline', 'team size', 'projects delivered', 'stakeholder satisfaction'],
        'action_verbs': ['Spearheaded', 'Orchestrated', 'Directed', 'Streamlined', 'Championed', 'Delivered']
    },
    
    'marketing': {
        'weak_examples': [
            "Ran marketing campaigns.",
            "Managed social media.",
            "Created content.",
            "Improved brand awareness."
        ],
        'strong_patterns': [
            "Launched multi-channel campaign generating 2,400 qualified leads with $45 CAC.",
            "Grew social media following by 340% across LinkedIn and Twitter, driving 67% increase in engagement.",
            "Developed content strategy resulting in 156% increase in organic traffic within 6 months.",
            "Executed rebranding initiative increasing brand recognition by 52% in target demographic."
        ],
        'key_metrics': ['CAC', 'ROAS', 'conversion rate', 'engagement rate', 'lead generation'],
        'action_verbs': ['Launched', 'Amplified', 'Positioned', 'Cultivated', 'Scaled', 'Drove']
    },
    
    'finance': {
        'weak_examples': [
            "Managed budgets.",
            "Did financial analysis.",
            "Prepared reports.",
            "Handled audits."
        ],
        'strong_patterns': [
            "Managed $45M annual budget with 98.5% variance accuracy.",
            "Identified $1.8M in cost savings through comprehensive financial analysis.",
            "Automated financial reporting reducing close cycle from 12 days to 4 days.",
            "Led due diligence for $25M M&A transaction, identifying 7 key risk factors."
        ],
        'key_metrics': ['budget size', 'variance', 'cost savings', 'ROI', 'audit findings'],
        'action_verbs': ['Forecasted', 'Audited', 'Reconciled', 'Optimized', 'Assessed', 'Valued']
    },
    
    'hr': {
        'weak_examples': [
            "Recruited candidates.",
            "Handled employee relations.",
            "Managed HR processes.",
            "Conducted training."
        ],
        'strong_patterns': [
            "Reduced time-to-hire by 35% while improving quality-of-hire score by 28%.",
            "Designed and implemented onboarding program achieving 94% new hire retention at 90 days.",
            "Led talent acquisition for 150 hires annually with $420K recruitment budget.",
            "Developed L&D curriculum resulting in 31% improvement in employee performance scores."
        ],
        'key_metrics': ['time-to-hire', 'retention rate', 'employee satisfaction', 'training completion'],
        'action_verbs': ['Recruited', 'Onboarded', 'Developed', 'Retained', 'Assessed', 'Mentored']
    }
}

# Generic pattern for unrecognized roles
GENERIC_STRONG_PATTERN = """
Action Structure: [Strong Action Verb] + [What You Did] + [Using What Method/Tool] + [Achieving What Result] + [In What Timeframe]

Template: "Implemented [strategy/initiative] using [method/technology] which resulted in [specific measurable outcome] within [time period]."

Examples (NO PLACEHOLDERS - use realistic metrics):
- "Implemented process automation using Python scripting which resulted in 40% reduction in manual work within 2 months."
- "Spearheaded departmental initiative using Agile methodology which resulted in 25% faster delivery cycles within Q3."
- "Redesigned customer onboarding flow using user research insights, reducing drop-off rate by 18% in 6 weeks."

CRITICAL: Never use placeholder syntax like {percentage}%, ${amount}, or {timeframe}.
Always generate realistic, believable metrics based on context.
"""
```

### Transformation Function

```python
def transform_to_professional_tone(
    text: str, 
    job_category: str,
    context: dict = None
) -> dict:
    """
    Transform weak statement to professional tone.
    
    Args:
        text: Original statement
        job_category: Category of job (sales, software_developer, etc.)
        context: Additional context for better transformation
    
    Returns:
        Transformation result with before/after and applied rules
    """
    
    # Get role-specific patterns
    patterns = ROLE_PATTERNS.get(job_category, ROLE_PATTERNS['generic'])
    
    # Detect weakness type
    weakness_analysis = {
        'is_vague': not contains_specifics(text),
        'lacks_metrics': not contains_metrics(text),
        'weak_verb': has_weak_verb(text),
        'passive_voice': is_passive_voice(text),
        'first_person_start': text.strip().startswith('I ')
    }
    
    # Build transformation prompt
    transformation = {
        'original': text,
        'weaknesses': weakness_analysis,
        'category': job_category,
        'modified': None,
        'pattern_used': None
    }
    
    if any(weakness_analysis.values()):
        # Generate strong version using LLM
        strong_version = generate_strong_version(
            text, 
            patterns,
            context
        )
        transformation['modified'] = strong_version['text']
        transformation['pattern_used'] = strong_version['pattern']
    
    return transformation
```

---

## Project Placement Logic

### Decision Tree for Project Placement

```python
"""
Project Placement Algorithm
---------------------------
Determines where to place suggested projects in the CV.
CRITICAL: Only suggest placement in sections that EXIST in the input CV JSON.
"""

def determine_project_placement(
    cv: dict,
    suggested_project: dict,
    project_technologies: list
) -> dict:
    """
    Determine optimal placement for a suggested project.
    
    CRITICAL RULE: Only suggest sections that exist in input CV.
    Use EXACT section names from input JSON.
    
    Decision Logic:
    1. First, identify available sections in the input CV
    2. Only recommend placement in sections that EXIST
    3. If 'projects' section exists AND project is personal/side project -> 'projects'
    4. If 'work_experience' exists:
       a. Check latest company tenure
       b. If tenure < 6 months -> place in 2nd latest company (if exists)
       c. Otherwise -> place in latest company
    5. NEVER suggest a section that doesn't exist in input
    """
    
    # Step 1: Identify available sections in input CV
    available_sections = identify_available_sections(cv)
    
    placement = {
        'location': None,
        'available_sections': available_sections,
        'company_index': None,
        'company_name': None,
        'rationale': None
    }
    
    # Step 2: Check what sections are available
    has_projects_section = 'projects' in available_sections
    has_work_experience = 'work_experience' in available_sections
    
    # If neither exists, cannot place project
    if not has_projects_section and not has_work_experience:
        placement['rationale'] = 'No suitable section found in CV. Add either projects or work_experience section.'
        return placement
    
    # Determine project nature
    project_nature = classify_project_nature(suggested_project)
    
    # Personal/Portfolio projects go to dedicated section IF it exists
    if project_nature == 'personal' and has_projects_section:
        placement['location'] = 'projects'  # EXACT name from input
        placement['rationale'] = 'Personal/portfolio project placed in existing projects section'
        return placement
    
    # Work-related projects go to work_experience IF it exists
    if has_work_experience:
        work_experience = cv.get('work_experience', [])
        
        if work_experience:
            latest_exp = work_experience[0]
            tenure_months = calculate_tenure_months(
                latest_exp.get('start_date'),
                latest_exp.get('end_date')
            )
            
            # If latest job is very new (< 6 months) and there's a 2nd company
            if tenure_months < 6 and len(work_experience) > 1:
                placement['location'] = 'work_experience'  # EXACT name
                placement['company_index'] = 1
                placement['company_name'] = work_experience[1].get('company')
                placement['rationale'] = (
                    f"Latest position ({latest_exp.get('company')}) tenure is only "
                    f"{tenure_months} months. Placing under {work_experience[1].get('company')} for credibility."
                )
            else:
                placement['location'] = 'work_experience'  # EXACT name
                placement['company_index'] = 0
                placement['company_name'] = latest_exp.get('company')
                placement['rationale'] = (
                    f"Placing under current/latest company ({latest_exp.get('company')}) "
                    f"with {tenure_months} months tenure."
                )
        return placement
    
    # Fallback to projects section if only that exists
    if has_projects_section:
        placement['location'] = 'projects'  # EXACT name
        placement['rationale'] = 'No work_experience section found, adding to projects section.'
    
    return placement


def identify_available_sections(cv: dict) -> list:
    """
    Identify all sections present in the input CV.
    Returns EXACT section names as they appear in input JSON.
    """
    
    available = []
    
    # Check each possible section
    section_checks = [
        'personal_info',
        'summary',
        'work_experience',
        'education',
        'skills',
        'certifications',
        'projects',
        'awards',
        'publications',
        'volunteer',
        'references'
    ]
    
    for section in section_checks:
        if section in cv and cv[section]:
            # Check if it's not empty
            value = cv[section]
            if isinstance(value, list) and len(value) > 0:
                available.append(section)
            elif isinstance(value, dict) and any(v for v in value.values()):
                available.append(section)
            elif isinstance(value, str) and value.strip():
                available.append(section)
    
    return available


def calculate_tenure_months(start_date: str, end_date: str = None) -> int:
    """
    Calculate tenure in months.
    If end_date is None, uses current date.
    """
    from datetime import datetime
    from dateutil import parser, relativedelta
    
    start = parser.parse(start_date)
    end = parser.parse(end_date) if end_date else datetime.now()
    
    delta = relativedelta.relativedelta(end, start)
    return delta.years * 12 + delta.months


def classify_project_nature(project: dict) -> str:
    """
    Classify project as 'personal', 'work', or 'academic'.
    
    Indicators:
    - Personal: GitHub links, portfolio, side project keywords
    - Work: Client names, company context, enterprise keywords
    - Academic: University, thesis, research keywords
    """
    
    description = project.get('description', '').lower()
    name = project.get('suggested_project_name', '').lower()
    
    personal_keywords = ['personal', 'side project', 'hobby', 'github', 'open source', 'portfolio']
    work_keywords = ['client', 'enterprise', 'production', 'deployed', 'company', 'organization']
    academic_keywords = ['university', 'thesis', 'research', 'academic', 'course', 'capstone']
    
    for keyword in personal_keywords:
        if keyword in description or keyword in name:
            return 'personal'
    
    for keyword in work_keywords:
        if keyword in description or keyword in name:
            return 'work'
    
    for keyword in academic_keywords:
        if keyword in description or keyword in name:
            return 'academic'
    
    return 'work'  # Default to work-related
```

---

## Scoring Algorithm

### Detailed Scoring Implementation

```python
"""
Comprehensive CV-JD Scoring System
----------------------------------
Multi-dimensional scoring with weighted components.
Includes project relevancy and experience depth analysis.
"""

class CVScorer:
    def __init__(self, cv: dict, jd: str, job_title: str):
        self.cv = cv
        self.jd = jd
        self.job_title = job_title
        self.jd_analysis = self._analyze_jd()
    
    def _analyze_jd(self) -> dict:
        """
        Use OpenAI to extract structured requirements from JD.
        """
        prompt = f"""
        Analyze this job description and extract:
        1. Required technical skills (with importance: required/preferred/nice-to-have)
        2. Required soft skills
        3. Required experience years
        4. Required education level
        5. Required certifications
        6. Key responsibilities
        7. Project types expected (with complexity: basic/intermediate/advanced/expert)
        8. Industry keywords
        9. Experience depth required (entry/mid/senior/expert level complexity)
        10. Project scale expected (small/medium/large/enterprise)
        
        Job Description:
        {self.jd}
        
        Return as JSON.
        """
        
        response = call_openai_json(prompt)
        return response
    
    def calculate_full_score(self) -> dict:
        """
        Calculate comprehensive matching score.
        
        Weights:
        - Technical Skills: 25%
        - Soft Skills: 10%
        - Experience Relevance & Depth: 25%
        - Project Relevancy: 20%
        - Education Match: 5%
        - Keywords & Certifications: 15%
        """
        
        scores = {}
        
        # 1. Technical Skills Score (25%)
        scores['technical_skills'] = self._score_technical_skills()
        
        # 2. Soft Skills Score (10%)
        scores['soft_skills'] = self._score_soft_skills()
        
        # 3. Experience Relevance & Depth (25%)
        scores['experience'] = self._score_experience_with_depth()
        
        # 4. Project Relevancy (20%)
        scores['projects'] = self._score_project_relevancy()
        
        # 5. Education Match (5%)
        scores['education'] = self._score_education()
        
        # 6. Keywords & Certifications (15%)
        scores['keywords'] = self._score_keywords()
        
        # Weighted total
        weights = {
            'technical_skills': 0.25,
            'soft_skills': 0.10,
            'experience': 0.25,
            'projects': 0.20,
            'education': 0.05,
            'keywords': 0.15
        }
        
        total = sum(scores[k]['score'] * weights[k] for k in weights)
        
        return {
            'overall_percentage': round(total, 1),
            'rating': self._get_rating(total),
            'breakdown': scores,
            'detailed_analysis': self._generate_detailed_analysis(scores)
        }
    
    def _score_experience_with_depth(self) -> dict:
        """
        Score experience relevance AND depth/complexity match.
        
        Depth Levels:
        - Entry: Basic tasks, learning, supporting roles
        - Mid: Independent work, ownership, standard projects
        - Senior: Architecture decisions, mentoring, complex systems
        - Expert: Strategic decisions, innovation, industry impact
        """
        
        required_years = self.jd_analysis.get('required_years', 0)
        required_depth = self.jd_analysis.get('experience_depth', 'mid')
        actual_years = self._calculate_total_experience_years()
        
        # Years score (30% of this component)
        if required_years > 0:
            years_ratio = min(actual_years / required_years, 1.5)
            years_score = min(years_ratio * 100, 100)
        else:
            years_score = 100
        
        # Relevance score (30% of this component)
        relevance_score = self._calculate_role_relevance()
        
        # Depth analysis (40% of this component)
        depth_analysis = self._analyze_experience_depth()
        depth_score = self._calculate_depth_match(required_depth, depth_analysis)
        
        combined = (years_score * 0.30) + (relevance_score * 0.30) + (depth_score * 0.40)
        
        return {
            'score': combined,
            'years_required': required_years,
            'years_actual': actual_years,
            'relevance_score': relevance_score,
            'depth_analysis': {
                'jd_requires': required_depth,
                'cv_demonstrates': depth_analysis['assessed_level'],
                'depth_score': depth_score,
                'gap_description': depth_analysis.get('gap_description', '')
            }
        }
    
    def _score_project_relevancy(self) -> dict:
        """
        Score how well CV projects align with JD requirements.
        
        Factors:
        - Project type match
        - Technology alignment
        - Complexity/scale match
        - Outcome demonstration
        """
        
        jd_project_reqs = self.jd_analysis.get('project_types', [])
        jd_project_scale = self.jd_analysis.get('project_scale', 'medium')
        cv_projects = self._collect_all_projects()
        
        if not jd_project_reqs:
            return {'score': 100, 'message': 'No specific project requirements in JD'}
        
        if not cv_projects:
            return {
                'score': 0, 
                'message': 'No projects found in CV',
                'gaps': jd_project_reqs
            }
        
        matched_projects = []
        gaps = []
        total_weight = 0
        earned_weight = 0
        
        for req in jd_project_reqs:
            req_type = req if isinstance(req, str) else req.get('type', '')
            importance = 'preferred' if isinstance(req, str) else req.get('importance', 'preferred')
            
            weight = {'required': 1.0, 'preferred': 0.6, 'nice-to-have': 0.3}.get(importance, 0.6)
            total_weight += weight
            
            match = self._find_matching_project(req_type, cv_projects)
            
            if match['found']:
                # Adjust for scale match
                scale_factor = self._calculate_scale_match(jd_project_scale, match.get('project_scale', 'medium'))
                earned_weight += weight * match['match_strength'] * scale_factor
                matched_projects.append({
                    'requirement': req_type,
                    'matched_project': match['project_name'],
                    'match_strength': match['match_strength'],
                    'technologies_matched': match.get('tech_overlap', []),
                    'scale_match': scale_factor
                })
            else:
                gaps.append({
                    'jd_expectation': req_type,
                    'current_coverage': 'none',
                    'recommendation': f"Add project demonstrating {req_type} experience"
                })
        
        score = (earned_weight / total_weight * 100) if total_weight > 0 else 0
        
        return {
            'score': score,
            'matched_projects': matched_projects,
            'gaps': gaps,
            'jd_project_requirements': jd_project_reqs,
            'expected_scale': jd_project_scale
        }
    
    def _analyze_experience_depth(self) -> dict:
        """
        Analyze depth/complexity demonstrated in CV.
        """
        
        depth_indicators = {
            'entry': ['assisted', 'supported', 'learned', 'trained', 'junior', 'intern', 'entry'],
            'mid': ['developed', 'implemented', 'managed', 'designed', 'built', 'created', 'delivered'],
            'senior': ['architected', 'led', 'mentored', 'strategized', 'scaled', 'enterprise', 'cross-functional', 'owned'],
            'expert': ['pioneered', 'innovated', 'transformed', 'industry-wide', 'patents', 'published', 'keynote', 'advisory']
        }
        
        cv_text = self._get_full_cv_text().lower()
        
        level_scores = {}
        for level, indicators in depth_indicators.items():
            score = sum(1 for ind in indicators if ind in cv_text)
            level_scores[level] = score
        
        max_level = max(level_scores, key=level_scores.get)
        
        return {
            'assessed_level': max_level,
            'level_scores': level_scores,
            'gap_description': ''
        }
    
    def _calculate_depth_match(self, required: str, analysis: dict) -> float:
        """
        Calculate depth match score.
        """
        
        level_order = ['entry', 'mid', 'senior', 'expert']
        required_idx = level_order.index(required) if required in level_order else 1
        actual_idx = level_order.index(analysis['assessed_level'])
        
        if actual_idx >= required_idx:
            return 100
        else:
            gap = required_idx - actual_idx
            return max(0, 100 - (gap * 33))
    
    def _calculate_scale_match(self, required_scale: str, actual_scale: str) -> float:
        """
        Calculate project scale match factor.
        """
        
        scale_order = ['small', 'medium', 'large', 'enterprise']
        required_idx = scale_order.index(required_scale) if required_scale in scale_order else 1
        actual_idx = scale_order.index(actual_scale) if actual_scale in scale_order else 1
        
        if actual_idx >= required_idx:
            return 1.0
        else:
            gap = required_idx - actual_idx
            return max(0.5, 1.0 - (gap * 0.2))
    
    def _collect_all_projects(self) -> list:
        """
        Collect all projects from CV (standalone + under experience).
        """
        
        all_projects = []
        
        # From projects section
        if self.cv.get('projects'):
            for project in self.cv['projects']:
                all_projects.append({
                    'source': 'projects',
                    'data': project
                })
        
        # From work experience
        for i, exp in enumerate(self.cv.get('work_experience', [])):
            if exp.get('projects'):
                for project in exp['projects']:
                    all_projects.append({
                        'source': f'work_experience[{i}]',
                        'company': exp.get('company'),
                        'data': project
                    })
        
        return all_projects
    
    def _score_technical_skills(self) -> dict:
        """
        Score technical skills match.
        
        Scoring Method:
        - Exact match: 100% of skill weight
        - Partial match (similar tech): 70% of skill weight
        - Inferred (found in descriptions): 50% of skill weight
        - Missing required: 0%
        """
        
        required_skills = self.jd_analysis.get('technical_skills', [])
        cv_skills = self._extract_cv_skills()
        
        matched = []
        missing = []
        total_weight = 0
        earned_weight = 0
        
        for skill_info in required_skills:
            skill = skill_info['skill']
            importance = skill_info['importance']
            weight = {'required': 1.0, 'preferred': 0.6, 'nice-to-have': 0.3}.get(importance, 0.5)
            total_weight += weight
            
            match_result = self._find_skill_in_cv(skill, cv_skills)
            
            if match_result['found']:
                match_score = {'exact': 1.0, 'partial': 0.7, 'inferred': 0.5}[match_result['type']]
                earned_weight += weight * match_score
                matched.append({
                    'skill': skill,
                    'match_type': match_result['type'],
                    'cv_location': match_result['location']
                })
            else:
                missing.append({
                    'skill': skill,
                    'importance': importance
                })
        
        score = (earned_weight / total_weight * 100) if total_weight > 0 else 0
        
        return {
            'score': score,
            'matched': matched,
            'missing': missing
        }
    
    def _score_soft_skills(self) -> dict:
        """
        Score soft skills using NLP inference from CV text.
        """
        
        required_soft = self.jd_analysis.get('soft_skills', [])
        
        # Combine all text from CV for soft skill inference
        cv_text = self._get_full_cv_text()
        
        # Use OpenAI to identify soft skills in CV text
        prompt = f"""
        Analyze this CV text and identify which of these soft skills are demonstrated:
        Required skills: {required_soft}
        
        CV Text:
        {cv_text}
        
        Return JSON with:
        - demonstrated: list of skills found with evidence
        - missing: list of skills not found
        """
        
        analysis = call_openai_json(prompt)
        
        matched_count = len(analysis.get('demonstrated', []))
        total_count = len(required_soft)
        
        score = (matched_count / total_count * 100) if total_count > 0 else 100
        
        return {
            'score': score,
            'matched': analysis.get('demonstrated', []),
            'missing': analysis.get('missing', [])
        }
    
    def _score_experience(self) -> dict:
        """
        Score experience relevance.
        
        Factors:
        - Years of experience match
        - Industry alignment
        - Role progression relevance
        - Responsibility overlap
        """
        
        required_years = self.jd_analysis.get('required_years', 0)
        actual_years = self._calculate_total_experience_years()
        
        # Years score (max at required, bonus for extra up to 50%)
        if required_years > 0:
            years_ratio = min(actual_years / required_years, 1.5)
            years_score = min(years_ratio * 100, 100)
        else:
            years_score = 100
        
        # Relevance score (using AI to compare responsibilities)
        relevance_score = self._calculate_role_relevance()
        
        # Combined score
        combined = (years_score * 0.4) + (relevance_score * 0.6)
        
        return {
            'score': combined,
            'years_required': required_years,
            'years_actual': actual_years,
            'relevance_analysis': relevance_score
        }
    
    def _get_rating(self, score: float) -> str:
        """Convert score to rating."""
        if score >= 85:
            return 'Excellent'
        elif score >= 70:
            return 'Good'
        elif score >= 50:
            return 'Fair'
        else:
            return 'Poor'
```

---

## OpenAI Integration

### Main OpenAI Service Class

```python
"""
OpenAI Integration Layer
------------------------
Handles all LLM interactions for CV improvement.
"""

import openai
from typing import Optional, Dict, Any
import json

class CVImprovementAI:
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.system_prompts = self._load_system_prompts()
    
    def _load_system_prompts(self) -> dict:
        """Load role-specific system prompts."""
        
        return {
            'cv_analyzer': """
You are an expert CV/Resume analyst with 15+ years of experience in HR and recruitment.
Your task is to analyze CVs against job descriptions with extreme attention to detail.
You identify:
1. Skill gaps (technical and soft)
2. Experience mismatches
3. Content improvement opportunities
4. Missing sections or information
5. Keyword optimization needs

Always be specific, actionable, and constructive in your analysis.
""",
            
            'tone_improver': """
You are a professional copywriter specializing in CV/Resume optimization.
Your expertise is transforming weak, vague statements into powerful, metrics-driven achievements.

Rules:
1. ALWAYS use strong action verbs (Implemented, Spearheaded, Architected, Orchestrated)
2. ALWAYS include quantifiable metrics (percentages, dollar amounts, time savings)
3. ALWAYS mention specific technologies/methods used
4. ALWAYS include timeframes when possible
5. NEVER start with "I" or use passive voice
6. NEVER be vague - be specific and concrete

Template: "Implemented [action/strategy] using [method/technology] which resulted in [specific measurable outcome] within [time period]."
""",
            
            'project_generator': """
You are a senior technical consultant who helps professionals articulate their project experience.
When suggesting projects:
1. Make them realistic and believable given the candidate's background
2. Use specific technologies from the job description
3. Include measurable outcomes
4. Ensure they demonstrate required skills
5. Match the candidate's experience level
""",
            
            'keyword_optimizer': """
You are an ATS (Applicant Tracking System) optimization expert.
Your job is to identify keywords from job descriptions and ensure CVs include them naturally.
Focus on:
1. Technical skills and technologies
2. Industry-specific terminology
3. Methodology and framework names
4. Certifications and qualifications
5. Action verbs that ATS systems look for
"""
        }
    
    def analyze_cv_against_jd(
        self, 
        cv: dict, 
        jd: str, 
        job_title: str
    ) -> dict:
        """
        Main analysis function that orchestrates all improvements.
        """
        
        # Step 1: Extract JD requirements
        jd_requirements = self._extract_jd_requirements(jd, job_title)
        
        # Step 2: Analyze skills gaps
        skills_analysis = self._analyze_skills(cv, jd_requirements)
        
        # Step 3: Analyze and improve tone
        tone_improvements = self._analyze_tone(cv, job_title)
        
        # Step 4: Identify project gaps
        project_analysis = self._analyze_projects(cv, jd_requirements)
        
        # Step 5: Keyword optimization
        keyword_analysis = self._analyze_keywords(cv, jd_requirements)
        
        # Step 6: Missing essentials check
        missing_essentials = self._check_missing_essentials(cv)
        
        # Step 7: Generate modified CV
        modified_cv = self._generate_modified_cv(
            cv, 
            tone_improvements,
            project_analysis,
            keyword_analysis
        )
        
        # Step 8: Calculate score
        score = self._calculate_match_score(cv, jd_requirements)
        
        return {
            'jd_requirements': jd_requirements,
            'skills_analysis': skills_analysis,
            'tone_improvements': tone_improvements,
            'project_analysis': project_analysis,
            'keyword_analysis': keyword_analysis,
            'missing_essentials': missing_essentials,
            'modified_cv': modified_cv,
            'match_score': score
        }
    
    def _extract_jd_requirements(self, jd: str, job_title: str) -> dict:
        """Extract structured requirements from JD text."""
        
        prompt = f"""
Analyze this job description for "{job_title}" and extract:

Job Description:
{jd}

Return a JSON object with:
{{
    "technical_skills": [
        {{"skill": "name", "importance": "required|preferred|nice-to-have", "context": "how mentioned"}}
    ],
    "soft_skills": ["skill1", "skill2"],
    "experience_years": number,
    "education": {{"level": "bachelors|masters|phd", "field": "field", "required": true/false}},
    "certifications": ["cert1", "cert2"],
    "responsibilities": ["resp1", "resp2"],
    "project_types": ["type1", "type2"],
    "keywords": ["keyword1", "keyword2"],
    "industry": "industry name",
    "seniority_level": "junior|mid|senior|lead"
}}
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompts['cv_analyzer']},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _analyze_tone(self, cv: dict, job_title: str) -> list:
        """
        Analyze and improve professional tone throughout CV.
        """
        
        improvements = []
        
        # Analyze summary
        if cv.get('summary'):
            improvement = self._improve_text_tone(
                cv['summary'], 
                'summary',
                'summary',
                job_title
            )
            if improvement['is_improved']:
                improvements.append(improvement)
        
        # Analyze work experience
        for i, exp in enumerate(cv.get('work_experience', [])):
            # Description
            if exp.get('description'):
                improvement = self._improve_text_tone(
                    exp['description'],
                    f'work_experience[{i}].description',
                    'work_experience_description',
                    job_title
                )
                if improvement['is_improved']:
                    improvements.append(improvement)
            
            # Achievements
            for j, achievement in enumerate(exp.get('achievements', [])):
                improvement = self._improve_text_tone(
                    achievement,
                    f'work_experience[{i}].achievements[{j}]',
                    'achievement',
                    job_title
                )
                if improvement['is_improved']:
                    improvements.append(improvement)
        
        return improvements
    
    def _improve_text_tone(
        self, 
        text: str, 
        field_path: str,
        context_type: str,
        job_title: str
    ) -> dict:
        """
        Improve individual text section.
        """
        
        prompt = f"""
Analyze and improve this CV text for a {job_title} position:

Original Text:
"{text}"

Context: This is from the {context_type} section.

If the text needs improvement, return JSON:
{{
    "needs_improvement": true,
    "original_text": "original",
    "modified_text": "improved version",
    "improvement_type": "grammar|tone|clarity|quantification",
    "explanation": "what was improved and why",
    "metrics_suggested": ["list of suggested metrics if applicable"]
}}

If the text is already strong, return:
{{
    "needs_improvement": false,
    "original_text": "original"
}}

Remember:
- Use strong action verbs
- Include specific metrics where possible
- Be concise but impactful
- Don't start with "I"
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompts['tone_improver']},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5
        )
        
        result = json.loads(response.choices[0].message.content)
        result['field_path'] = field_path
        result['is_improved'] = result.get('needs_improvement', False)
        
        return result
    
    def improve_with_chat(
        self,
        session_id: str,
        cv: dict,
        user_message: str,
        conversation_history: list
    ) -> dict:
        """
        Chatbot improvement function for iterative changes.
        """
        
        # Build context from conversation history
        messages = [
            {"role": "system", "content": f"""
You are a CV improvement assistant. You have access to the user's CV and can make specific changes based on their requests.

Current CV:
{json.dumps(cv, indent=2)}

Guidelines:
1. When user asks to change a specific section, provide the exact modification
2. Always confirm what you're changing
3. Provide before/after comparison
4. Suggest additional improvements if relevant
5. Keep track of all changes made in this session
"""}
        ]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            'session_id': session_id,
            'response': result,
            'updated_cv': self._apply_chat_changes(cv, result.get('changes', []))
        }
```

---

## Stateful Chatbot System

### Session Management

```python
"""
Stateful Chatbot Session Management
-----------------------------------
Manages conversation state for iterative CV improvements.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import uuid
import redis
import json

@dataclass
class ChatSession:
    session_id: str
    user_id: str
    original_cv: dict
    current_cv: dict
    job_title: str
    job_description: str
    conversation_history: List[dict] = field(default_factory=list)
    changes_made: List[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=24)


class SessionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.session_ttl = 86400  # 24 hours
    
    def create_session(
        self,
        user_id: str,
        cv: dict,
        job_title: str,
        job_description: str,
        initial_analysis: dict
    ) -> ChatSession:
        """
        Create a new chat session after initial CV analysis.
        """
        
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            original_cv=cv,
            current_cv=cv.copy(),
            job_title=job_title,
            job_description=job_description,
            conversation_history=[
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "type": "initial_analysis",
                        "data": initial_analysis
                    })
                }
            ]
        )
        
        self._save_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieve session from Redis."""
        
        data = self.redis.get(f"session:{session_id}")
        if data:
            session_dict = json.loads(data)
            return ChatSession(**session_dict)
        return None
    
    def update_session(self, session: ChatSession):
        """Update session in Redis."""
        session.last_activity = datetime.now()
        self._save_session(session)
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: dict = None
    ) -> ChatSession:
        """Add message to conversation history."""
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata
        
        session.conversation_history.append(message)
        self.update_session(session)
        
        return session
    
    def apply_change(
        self,
        session_id: str,
        change: dict
    ) -> ChatSession:
        """
        Apply a change to the current CV state.
        
        Change format:
        {
            "field_path": "work_experience[0].description",
            "original_value": "...",
            "new_value": "...",
            "change_type": "tone|content|add|remove"
        }
        """
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Apply change to current CV
        session.current_cv = self._apply_change_to_cv(
            session.current_cv,
            change
        )
        
        # Record change
        session.changes_made.append({
            **change,
            "applied_at": datetime.now().isoformat()
        })
        
        self.update_session(session)
        
        return session
    
    def get_diff(self, session_id: str) -> dict:
        """
        Get diff between original and current CV.
        """
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            "original": session.original_cv,
            "current": session.current_cv,
            "changes": session.changes_made,
            "total_changes": len(session.changes_made)
        }
    
    def _save_session(self, session: ChatSession):
        """Save session to Redis."""
        
        session_dict = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "original_cv": session.original_cv,
            "current_cv": session.current_cv,
            "job_title": session.job_title,
            "job_description": session.job_description,
            "conversation_history": session.conversation_history,
            "changes_made": session.changes_made,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "expires_at": session.expires_at.isoformat()
        }
        
        self.redis.setex(
            f"session:{session.session_id}",
            self.session_ttl,
            json.dumps(session_dict)
        )
    
    def _apply_change_to_cv(self, cv: dict, change: dict) -> dict:
        """
        Apply a single change to CV using field path.
        
        Example field_path: "work_experience[0].achievements[1]"
        """
        
        import copy
        cv = copy.deepcopy(cv)
        
        path = change['field_path']
        new_value = change['new_value']
        
        # Parse path and navigate to target
        keys = self._parse_field_path(path)
        
        # Navigate to parent
        current = cv
        for key in keys[:-1]:
            if isinstance(key, int):
                current = current[key]
            else:
                current = current[key]
        
        # Apply change
        final_key = keys[-1]
        if isinstance(final_key, int):
            current[final_key] = new_value
        else:
            current[final_key] = new_value
        
        return cv
    
    def _parse_field_path(self, path: str) -> list:
        """
        Parse field path like "work_experience[0].achievements[1]" into keys.
        """
        import re
        
        parts = []
        for part in path.replace(']', '').split('.'):
            if '[' in part:
                key, idx = part.split('[')
                parts.append(key)
                parts.append(int(idx))
            else:
                parts.append(part)
        
        return parts
```

### Chatbot Interaction Handler

```python
"""
Chatbot Interaction Handler
---------------------------
Processes user messages and generates appropriate responses.
"""

class ChatbotHandler:
    def __init__(self, ai_service: CVImprovementAI, session_manager: SessionManager):
        self.ai = ai_service
        self.sessions = session_manager
    
    def process_message(
        self,
        session_id: str,
        user_message: str
    ) -> dict:
        """
        Process user message and return response with any changes.
        """
        
        session = self.sessions.get_session(session_id)
        if not session:
            return {"error": "Session not found or expired"}
        
        # Detect intent
        intent = self._detect_intent(user_message, session)
        
        # Process based on intent
        if intent['type'] == 'section_edit':
            return self._handle_section_edit(session, user_message, intent)
        elif intent['type'] == 'approval':
            return self._handle_approval(session, intent)
        elif intent['type'] == 'rejection':
            return self._handle_rejection(session, intent)
        elif intent['type'] == 'question':
            return self._handle_question(session, user_message)
        elif intent['type'] == 'export':
            return self._handle_export(session)
        else:
            return self._handle_general(session, user_message)
    
    def _detect_intent(self, message: str, session: ChatSession) -> dict:
        """
        Detect user intent from message.
        """
        
        message_lower = message.lower()
        
        # Check for section references
        section_keywords = {
            'summary': ['summary', 'professional summary', 'objective'],
            'experience': ['experience', 'work experience', 'job', 'employment'],
            'education': ['education', 'degree', 'university', 'college'],
            'skills': ['skills', 'technical skills', 'skill set'],
            'projects': ['project', 'projects'],
            'certifications': ['certification', 'certificate']
        }
        
        # Detect section being referenced
        target_section = None
        for section, keywords in section_keywords.items():
            if any(kw in message_lower for kw in keywords):
                target_section = section
                break
        
        # Detect action type
        if any(word in message_lower for word in ['edit', 'change', 'modify', 'update', 'improve', 'rewrite']):
            return {
                'type': 'section_edit',
                'section': target_section,
                'action': 'edit'
            }
        elif any(word in message_lower for word in ['approve', 'accept', 'yes', 'apply', 'confirm']):
            return {
                'type': 'approval',
                'section': target_section
            }
        elif any(word in message_lower for word in ['reject', 'no', 'decline', 'skip', 'ignore']):
            return {
                'type': 'rejection',
                'section': target_section
            }
        elif any(word in message_lower for word in ['export', 'download', 'save', 'finish', 'done']):
            return {'type': 'export'}
        elif '?' in message:
            return {'type': 'question'}
        else:
            return {
                'type': 'general',
                'section': target_section
            }
    
    def _handle_section_edit(
        self, 
        session: ChatSession, 
        message: str,
        intent: dict
    ) -> dict:
        """
        Handle request to edit a specific section.
        """
        
        # Add user message to history
        self.sessions.add_message(session.session_id, "user", message)
        
        # Generate edit suggestion using AI
        response = self.ai.improve_with_chat(
            session.session_id,
            session.current_cv,
            message,
            session.conversation_history
        )
        
        # Format response
        result = {
            "type": "edit_suggestion",
            "section": intent.get('section'),
            "suggestion": response.get('response'),
            "preview": {
                "before": self._extract_section(session.current_cv, intent.get('section')),
                "after": response.get('response', {}).get('modified_content')
            },
            "session_id": session.session_id
        }
        
        # Add assistant response to history
        self.sessions.add_message(
            session.session_id, 
            "assistant", 
            json.dumps(result),
            {"type": "edit_suggestion"}
        )
        
        return result
    
    def _handle_approval(self, session: ChatSession, intent: dict) -> dict:
        """
        Handle user approval of suggested changes.
        """
        
        # Get last suggestion from history
        last_suggestion = self._get_last_suggestion(session)
        
        if not last_suggestion:
            return {
                "type": "error",
                "message": "No pending suggestions to approve"
            }
        
        # Apply the change
        change = {
            "field_path": last_suggestion.get('field_path'),
            "original_value": last_suggestion.get('before'),
            "new_value": last_suggestion.get('after'),
            "change_type": "approved_edit"
        }
        
        session = self.sessions.apply_change(session.session_id, change)
        
        return {
            "type": "change_applied",
            "message": "Change has been applied successfully",
            "updated_section": self._extract_section(
                session.current_cv, 
                intent.get('section')
            ),
            "total_changes": len(session.changes_made)
        }
    
    def _handle_export(self, session: ChatSession) -> dict:
        """
        Handle export/finish request.
        """
        
        diff = self.sessions.get_diff(session.session_id)
        
        return {
            "type": "export_ready",
            "original_cv": diff['original'],
            "final_cv": diff['current'],
            "changes_summary": {
                "total_changes": diff['total_changes'],
                "changes": diff['changes']
            },
            "session_id": session.session_id
        }
```

---

## API Endpoints

### FastAPI Implementation

```python
"""
FastAPI Application
-------------------
REST API endpoints for CV Improvement System.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

app = FastAPI(
    title="CV Improvement API",
    description="AI-powered CV analysis and improvement system",
    version="1.0.0"
)

# Request/Response Models

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class WorkExperience(BaseModel):
    company: str
    job_title: str
    start_date: str
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    achievements: List[str] = []
    projects: List[dict] = []

class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: str
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    achievements: List[str] = []

class Skills(BaseModel):
    technical: List[str] = []
    soft: List[str] = []
    languages: List[str] = []
    tools: List[str] = []

class ParsedCV(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = None
    work_experience: List[WorkExperience] = []
    education: List[Education] = []
    skills: Skills = Skills()
    certifications: List[dict] = []
    projects: List[dict] = []
    awards: List[dict] = []
    publications: List[dict] = []
    volunteer: List[dict] = []
    references: List[dict] = []

class AnalyzeRequest(BaseModel):
    parsed_cv: ParsedCV
    job_title: str
    job_description: str
    options: dict = Field(default_factory=lambda: {
        "include_full_cv": True,
        "generate_missing_projects": True,
        "tone_analysis": True,
        "keyword_optimization": True
    })

class ChatMessage(BaseModel):
    session_id: str
    message: str

class ApprovalRequest(BaseModel):
    session_id: str
    change_ids: List[str]


# API Endpoints

@app.post("/api/v1/analyze")
async def analyze_cv(request: AnalyzeRequest):
    """
    Main endpoint: Analyze CV against JD and return improvements.
    
    Returns comprehensive JSON with:
    - Matching score
    - Skills analysis
    - Tone improvements
    - Project suggestions
    - Keyword optimization
    - Full original and modified CV
    """
    
    try:
        # Initialize services
        ai_service = CVImprovementAI(api_key=settings.OPENAI_API_KEY)
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        
        # Perform analysis
        analysis = ai_service.analyze_cv_against_jd(
            cv=request.parsed_cv.dict(),
            jd=request.job_description,
            job_title=request.job_title
        )
        
        # Create session for chatbot
        session = session_manager.create_session(
            user_id="anonymous",  # Replace with actual user ID
            cv=request.parsed_cv.dict(),
            job_title=request.job_title,
            job_description=request.job_description,
            initial_analysis=analysis
        )
        
        # Build response
        response = build_full_response(
            analysis=analysis,
            original_cv=request.parsed_cv.dict(),
            session_id=session.session_id
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat")
async def chat_message(request: ChatMessage):
    """
    Chatbot endpoint: Process user message and return response.
    """
    
    try:
        ai_service = CVImprovementAI(api_key=settings.OPENAI_API_KEY)
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        chatbot = ChatbotHandler(ai_service, session_manager)
        
        response = chatbot.process_message(
            session_id=request.session_id,
            user_message=request.message
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/approve")
async def approve_changes(request: ApprovalRequest):
    """
    Approve suggested changes and apply them to CV.
    """
    
    try:
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Apply approved changes
        for change_id in request.change_ids:
            # Implementation to apply specific changes
            pass
        
        return {
            "status": "success",
            "applied_changes": len(request.change_ids),
            "current_cv": session.current_cv
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str):
    """
    Get current session state including CV and changes.
    """
    
    try:
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session.session_id,
            "original_cv": session.original_cv,
            "current_cv": session.current_cv,
            "changes_made": session.changes_made,
            "expires_at": session.expires_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/session/{session_id}/diff")
async def get_diff(session_id: str):
    """
    Get diff between original and current CV.
    """
    
    try:
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        diff = session_manager.get_diff(session_id)
        
        return diff
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/session/{session_id}/export")
async def export_cv(session_id: str):
    """
    Export final CV with all applied changes.
    """
    
    try:
        session_manager = SessionManager(redis_url=settings.REDIS_URL)
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "status": "success",
            "original_cv": session.original_cv,
            "final_cv": session.current_cv,
            "changes_summary": {
                "total_changes": len(session.changes_made),
                "changes": session.changes_made
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper Functions

def build_full_response(analysis: dict, original_cv: dict, session_id: str) -> dict:
    """
    Build the complete response structure.
    Note: cv_content removed - original/modified CV not included in response.
    """
    
    return {
        "metadata": {
            "request_id": str(uuid.uuid4()),
            "processed_at": datetime.now().isoformat(),
            "job_title": analysis['jd_requirements'].get('job_title'),
            "processing_time_ms": 0  # Calculate actual time
        },
        "matching_analysis": {
            "overall_score": analysis['match_score'],
            "skills_analysis": analysis['skills_analysis'],
            "experience_analysis": analysis.get('experience_analysis', {}),
            "projects_relevancy": analysis.get('projects_relevancy', {}),
            "sections_analysis": analysis.get('sections_analysis', {})
        },
        "improvements": {
            "grammatical_tone": [
                imp for imp in analysis['tone_improvements']
                if imp.get('improvement_type') == 'grammar'
            ],
            "professional_tone": [
                imp for imp in analysis['tone_improvements']
                if imp.get('improvement_type') in ['tone', 'quantification']
            ]
        },
        "projects": analysis['project_analysis'],
        "keywords": analysis['keyword_analysis'],
        "missing_essentials": analysis['missing_essentials'],
        "session_info": {
            "session_id": session_id,
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "chatbot_enabled": True
        }
    }
```

---

## Database Schema

### PostgreSQL Schema (Optional persistence layer)

```sql
-- CV Improvement System Database Schema

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CV Analysis Sessions
CREATE TABLE analysis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_title VARCHAR(255) NOT NULL,
    job_description TEXT NOT NULL,
    original_cv JSONB NOT NULL,
    modified_cv JSONB,
    match_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active'
);

-- Changes History
CREATE TABLE cv_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES analysis_sessions(id),
    field_path VARCHAR(255) NOT NULL,
    original_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'suggested',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP
);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES analysis_sessions(id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis Cache (for frequently used JDs)
CREATE TABLE jd_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_hash VARCHAR(64) UNIQUE NOT NULL,
    job_title VARCHAR(255),
    analysis_result JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_sessions_user ON analysis_sessions(user_id);
CREATE INDEX idx_sessions_status ON analysis_sessions(status);
CREATE INDEX idx_changes_session ON cv_changes(session_id);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_jd_cache_hash ON jd_analysis_cache(jd_hash);
```

---

## Implementation Guide

### Project Structure

```
cv-improvement-system/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── cv.py               # CV Pydantic models
│   │   ├── request.py          # Request models
│   │   └── response.py         # Response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py   # OpenAI integration
│   │   ├── analyzer.py         # CV analysis logic
│   │   ├── scorer.py           # Scoring algorithms
│   │   ├── tone_improver.py    # Professional tone transformation
│   │   └── project_analyzer.py # Project gap analysis
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analyze.py          # Analysis endpoints
│   │   ├── chat.py             # Chatbot endpoints
│   │   └── session.py          # Session management endpoints
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── json_path.py        # JSON path utilities
│   │   ├── text_utils.py       # Text processing utilities
│   │   └── metrics.py          # Metrics extraction utilities
│   └── core/
│       ├── __init__.py
│       ├── session_manager.py  # Session management
│       ├── chatbot.py          # Chatbot handler
│       └── rules.py            # Professional tone rules
├── tests/
│   ├── __init__.py
│   ├── test_analyzer.py
│   ├── test_scorer.py
│   ├── test_chatbot.py
│   └── fixtures/
│       ├── sample_cvs.json
│       └── sample_jds.json
├── scripts/
│   ├── setup_db.py
│   └── seed_data.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Requirements.txt

```
# Core
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.3

# OpenAI
openai==1.10.0

# Database & Cache
redis==5.0.1
asyncpg==0.29.0
sqlalchemy==2.0.25

# Utilities
python-dateutil==2.8.2
python-multipart==0.0.6
httpx==0.26.0

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0

# Monitoring
sentry-sdk[fastapi]==1.39.2
prometheus-client==0.19.0
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:password@db:5432/cv_improvement
    depends_on:
      - redis
      - db
    volumes:
      - ./app:/app/app

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=cv_improvement
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

---

## Step-by-Step Development Workflow

### Phase 1: Core Setup (Day 1-2)

```
1. [ ] Set up project structure
2. [ ] Configure FastAPI application
3. [ ] Set up Redis for session management
4. [ ] Create Pydantic models for CV and requests/responses
5. [ ] Set up OpenAI client
6. [ ] Create basic configuration management
```

### Phase 2: Analysis Engine (Day 3-5)

```
1. [ ] Implement JD requirement extraction
2. [ ] Build skills matching algorithm
3. [ ] Create scoring engine
4. [ ] Implement tone analyzer
5. [ ] Build project gap analyzer
6. [ ] Create keyword optimizer
7. [ ] Implement missing essentials checker
```

### Phase 3: Response Builder (Day 6-7)

```
1. [ ] Build JSON response structure
2. [ ] Implement field path tracking for changes
3. [ ] Create CV modification engine
4. [ ] Build comparison utilities
5. [ ] Implement full CV generation with modifications
```

### Phase 4: Chatbot System (Day 8-10)

```
1. [ ] Implement session manager
2. [ ] Build conversation handler
3. [ ] Create intent detection
4. [ ] Implement section-specific editing
5. [ ] Build approval/rejection workflow
6. [ ] Create export functionality
```

### Phase 5: Testing & Refinement (Day 11-14)

```
1. [ ] Write unit tests for all components
2. [ ] Create integration tests
3. [ ] Test with various CV types and JDs
4. [ ] Refine professional tone rules
5. [ ] Optimize OpenAI prompts
6. [ ] Performance testing
7. [ ] Documentation
```

---

## Key Considerations

### Performance Optimization

1. **Caching JD Analysis**: Cache analyzed JDs by hash to avoid re-processing
2. **Batch OpenAI Calls**: Group similar requests where possible
3. **Async Processing**: Use async/await for all I/O operations
4. **Redis for Sessions**: Keep sessions in Redis for fast access

### Error Handling

1. **OpenAI Failures**: Implement retry logic with exponential backoff
2. **Session Expiry**: Gracefully handle expired sessions
3. **Invalid Input**: Comprehensive input validation with clear error messages
4. **Rate Limiting**: Implement rate limiting for API endpoints

### Security

1. **Input Sanitization**: Sanitize all user inputs
2. **Session Security**: Use secure session IDs and expiry
3. **API Key Protection**: Never expose OpenAI API key
4. **CORS Configuration**: Properly configure CORS for frontend integration

---

## Usage Examples

### Example API Call

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "parsed_cv": {
      "personal_info": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "summary": "Experienced software developer",
      "work_experience": [
        {
          "company": "Tech Corp",
          "job_title": "Software Developer",
          "start_date": "2020-01",
          "is_current": true,
          "description": "I developed features and fixed bugs",
          "achievements": ["I improved the system"]
        }
      ],
      "skills": {
        "technical": ["Python", "JavaScript"],
        "soft": ["Communication"]
      }
    },
    "job_title": "Senior Software Engineer",
    "job_description": "We are looking for a Senior Software Engineer with experience in Python, React, AWS..."
  }'
```

### Example Chat Interaction

```bash
# Send chat message
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "message": "Please improve my work experience description to be more impactful"
  }'

# Approve changes
curl -X POST "http://localhost:8000/api/v1/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "change_ids": ["change-1", "change-2"]
  }'
```

---

## Appendix: OpenAI Prompt Templates

### JD Analysis Prompt

```
You are an expert HR analyst. Extract structured requirements from this job description.

Job Description:
{jd_text}

Return JSON with:
- technical_skills: [{skill, importance, context}]
- soft_skills: [skills]
- experience_years: number
- experience_depth: "entry" | "mid" | "senior" | "expert"
- education: {level, field, required}
- certifications: [certs]
- responsibilities: [items]
- project_types: [{type, complexity, importance}]
- project_scale: "small" | "medium" | "large" | "enterprise"
- keywords: [keywords]
- industry: string
- seniority_level: string
```

### Tone Improvement Prompt

```
Transform this weak CV statement into a strong, metrics-driven achievement.

Job Title: {job_title}
Original: "{text}"

Rules:
1. Use strong action verbs (Implemented, Designed, Achieved)
2. Include specific metrics (%, $, time)
3. Mention technologies/methods used
4. Include timeframes
5. Don't start with "I"

CRITICAL - NO PLACEHOLDERS:
- Do NOT use {percentage}%, ${amount}, or {timeframe} syntax
- Generate REAL numbers: "32%", "$1.2M", "4 months"
- Infer realistic metrics based on context

Template: "Implemented [action] using [method] which resulted in [outcome] within [timeframe]."

Return only the improved statement with REAL metrics.
```

### Project Suggestion Prompt

```
Suggest a project for this candidate based on JD requirements.

Requirement: {requirement}
Candidate Skills: {skills}
Experience Summary: {experience}
Available CV Sections: {available_sections}

Generate a realistic project that:
1. Aligns with JD requirement
2. Is believable given background
3. Uses specific technologies from JD
4. Includes measurable outcomes with REAL numbers

CRITICAL RULES:
- NO placeholders - use real metrics: "reduced by 35%", "saved $50K annually"
- Only suggest placement in sections that exist in Available CV Sections
- Use EXACT section names from input

Return JSON: {name, description, technologies, duration, placement_section}
```

### Project Enhancement Prompt

```
Enhance this existing project to better align with JD requirements.

Original Project (preserve EXACTLY in 'original' field):
{original_project}

JD Requirements: {jd_requirements}
Identified Gaps: {gaps}

Generate enhanced version that:
1. Addresses the identified gaps
2. Adds relevant technologies from JD
3. Includes measurable outcomes with REAL numbers
4. Maintains believability

CRITICAL:
- The 'original' field must contain the EXACT original text - NO modifications
- Generate real metrics in 'suggested' - no placeholders

Return JSON:
{
  "original": {exact original - character for character},
  "suggested": {enhanced version with real metrics}
}
```

---

*Document Version: 1.1*
*Last Updated: December 2024*
*For use with Claude CLI development*