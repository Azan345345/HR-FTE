# CV-JD Matching Service - Complete API User Journey

Complete documentation covering **ALL endpoints** with real examples.

---

## API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/analyze` | Full CV-JD analysis with scores & recommendations |
| PUT | `/api/v1/session` | Sync updated CV after user accepts/declines recommendations |
| POST | `/api/v1/chat` | Chat about CV sections (uses session_id only) |
| POST | `/api/v1/approve` | Approve pending chat actions |
| GET | `/api/v1/session/{id}` | Get session info |
| DELETE | `/api/v1/session/{id}` | Delete session |

---

## User Flow (Single Serial Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Step 1: Parse CV                                                           │
│           │                                                                 │
│           ▼                                                                 │
│  POST /parse (CV Parser - port 8000)                                        │
│  Upload PDF → Get structured parsed_cv JSON                                 │
│           │                                                                 │
│           ▼                                                                 │
│  Step 2: Upload Job Description                                             │
│  (Frontend collects job_title + job_description from user)                  │
│           │                                                                 │
│           ▼                                                                 │
│  Step 3: Analyze CV against JD                                              │
│  POST /api/v1/analyze                                                       │
│  Returns: scores, recommendations with field paths                          │
│           │                                                                 │
│           ▼                                                                 │
│  Step 3b: User accepts/declines recommendations (IN FRONTEND)               │
│  Frontend applies accepted changes to local CV display                      │
│           │                                                                 │
│           ▼                                                                 │
│  Step 3c: Sync updated CV to backend                                        │
│  PUT /api/v1/session (send CV with accepted changes)                        │
│  Backend now has latest CV state                                            │
│           │                                                                 │
│           ▼                                                                 │
│  Step 4: Chat about sections (NO CV SENT - session_id only)                 │
│  POST /api/v1/chat                                                          │
│  Backend uses current_cv from session                                       │
│  Returns: message + optional action (pending)                               │
│           │                                                                 │
│           ▼                                                                 │
│  Step 5: Apply chat changes                                                 │
│  POST /api/v1/approve                                                       │
│  Backend updates current_cv, returns updated CV                             │
│           │                                                                 │
│           ▼                                                                 │
│  (Repeat Steps 4-5 for other sections)                                      │
│           │                                                                 │
│           ▼                                                                 │
│  Step 6: End session                                                        │
│  DELETE /api/v1/session/{id}                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sample CV Data (Used Throughout)

```json
{
    "contact_info": {
        "full_name": "Abdul Rahman",
        "email": "abdul@email.com",
        "phone": "+92-300-1234567",
        "location": "Lahore, Pakistan",
        "linkedin": "linkedin.com/in/abdulrahman"
    },
    "title": "Front Desk Officer",
    "professional_summary": "Dynamic Front Desk Officer with experience of 11 years, expertise at National Hospital & Medical Center, excelling in patient management and appointment scheduling.",
    "work_experience": [
        {
            "job_title": "Front Desk Officer",
            "company": "National Hospital & Medical Center",
            "start_date": "2013-01-01",
            "end_date": "2024-01-01",
            "description": [
                "Greeted patients and visitors, ensuring a positive first impression.",
                "Managed appointment scheduling and maintained front desk operations.",
                "Handled patient inquiries, telephone calls, and front desk documentation.",
                "Coordinated with medical staff and departments to ensure smooth patient flow."
            ]
        }
    ],
    "education": [
        {
            "degree": "Bachelor of Commerce",
            "institution": "Punjab University",
            "end_date": "2012"
        }
    ],
    "skills": [
        "Patient Management",
        "Appointment Scheduling",
        "Customer Service",
        "Electronic Health Records",
        "MS Office"
    ],
    "projects": null,
    "certifications": null,
    "total_years_of_experience": 11
}
```

---

# Step 1: Parse CV

**Service:** CV Parser (port 8000)

### Request

```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@resume.pdf"
```

### Response

```json
{
    "success": true,
    "data": {
        "contact_info": {...},
        "title": "Front Desk Officer",
        "professional_summary": "Dynamic Front Desk Officer with experience of 11 years...",
        "work_experience": [...],
        "education": [...],
        "skills": ["Patient Management", "Appointment Scheduling", ...],
        "projects": null,
        "certifications": null,
        "total_years_of_experience": 11
    }
}
```

**Frontend stores:** `parsedCV = response.data`

---

# Step 2: User Uploads Job Description

Frontend collects from user:
- `job_title`: "Healthcare Administrator"
- `job_description`: Full JD text

---

# Step 3: Analyze CV Against Job Description

### Request

```bash
curl -X POST http://localhost:8001/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "parsed_cv": {...},
    "job_title": "Healthcare Administrator",
    "job_description": "We are seeking a Healthcare Administrator...",
    "instructions": "Do not include fake projects I have not done. Focus on keyword optimization across existing content. Add at least 5 new skills from JD.",
    "options": {
        "generate_missing_projects": true,
        "tone_analysis": true,
        "keyword_optimization": true
    }
}'
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parsed_cv` | object | Yes | Structured CV data from parser |
| `job_title` | string | Yes | Target job title |
| `job_description` | string | Yes | Full job description text |
| `instructions` | string | No | **User's custom preferences/instructions**. Examples: "Don't add fake projects", "Include 5+ projects", "Maximize keyword injection", "Keep it conservative" |
| `options` | object | No | Feature flags for analysis |

### Instructions Examples

The `instructions` field accepts any free-form text. User instructions **override default behavior** when there's a conflict.

```json
// User can give ANY instructions - these are just examples:

"instructions": "Only modify existing content. Do not add any new projects."

"instructions": "Be aggressive with keyword injection. Maximize ATS score."

"instructions": "Focus on leadership and management terminology."

"instructions": "Keep it minimal - only fix grammar and spelling."

"instructions": "I'm a career changer, emphasize transferable skills."

"instructions": "Make it more technical, I'm applying to a FAANG company."

"instructions": "Tone down the corporate speak, this is for a startup."
```

### Response

```json
{
    "metadata": {
        "request_id": "req_a1b2c3d4",
        "processed_at": "2024-12-26T10:00:00.000Z",
        "job_title": "Healthcare Administrator",
        "processing_time_ms": 3200
    },
    "industry": "healthcare",
    "scores": {
        "current_match_score": 58,
        "potential_score_after_changes": 87,
        "rating": "Fair",
        "breakdown": {
            "skills_score": 55,
            "experience_score": 70,
            "education_score": 60,
            "projects_score": 20
        }
    },
    "skills_analysis": {
        "matched_skills": ["Patient Management", "Electronic Health Records"],
        "missing_skills": ["HIPAA Compliance", "Budget Management", "Staff Leadership"],
        "nice_to_have_missing": ["Project Management"]
    },
    "cv_sections": {
        "title": {
            "field_path": "title",
            "content": "Healthcare Operations Manager | Patient Services & Compliance",
            "original_content": "Front Desk Officer",
            "tag": "modified",
            "reason": "Aligned with administrative focus of target role"
        },
        "professional_summary": {
            "field_path": "professional_summary",
            "content": "Results-driven healthcare professional with 11+ years optimizing medical facility operations...",
            "original_content": "Dynamic Front Desk Officer with experience of 11 years...",
            "tag": "modified",
            "reason": "Added leadership language and compliance focus"
        },
        "work_experience": [
            {
                "job_index": 0,
                "job_title": "Front Desk Officer",
                "company": "National Hospital & Medical Center",
                "descriptions": [
                    {
                        "field_path": "work_experience[0].description[0]",
                        "content": "Supervised front-of-house operations serving 200+ patients daily with 98% satisfaction rate",
                        "original_content": "Greeted patients and visitors, ensuring a positive first impression.",
                        "tag": "modified",
                        "reason": "Added metrics and leadership language"
                    },
                    {
                        "field_path": "work_experience[0].description[4]",
                        "content": "Implemented workflow optimization initiatives reducing patient wait times by 25%",
                        "tag": "new",
                        "reason": "Addresses JD requirement for workflow optimization"
                    }
                ]
            }
        ],
        "skills": [
            {"field_path": "skills[5]", "content": "HIPAA Compliance", "tag": "new", "reason": "Required in JD"},
            {"field_path": "skills[6]", "content": "Budget Management", "tag": "new", "reason": "Key JD requirement"},
            {"field_path": "skills[7]", "content": "Staff Leadership", "tag": "new", "reason": "Administrative role requires this"}
        ]
    },
    "non_cv_sections": {
        "projects": [
            {
                "field_path": "projects[0]",
                "name": "EHR System Implementation & Staff Training",
                "description": "Led implementation of electronic health records system across 3 departments...",
                "technologies": ["Epic EHR", "Staff Training", "Change Management"],
                "tag": "new",
                "reason": "Addresses EHR experience requirement in JD"
            },
            {
                "field_path": "projects[1]",
                "name": "Patient Flow Optimization Initiative",
                "description": "Designed and implemented patient scheduling system reducing wait times by 30%...",
                "technologies": ["Process Optimization", "Scheduling Systems"],
                "tag": "new",
                "reason": "Demonstrates workflow optimization skills"
            },
            {
                "field_path": "projects[2]",
                "name": "HIPAA Compliance Audit Program",
                "description": "Established compliance monitoring program achieving 100% audit pass rate...",
                "technologies": ["HIPAA", "Compliance Auditing"],
                "tag": "new",
                "reason": "Addresses compliance requirements in JD"
            }
        ],
        "certifications": [
            {
                "field_path": "certifications[0]",
                "name": "Certified Healthcare Administrative Professional (cHAP)",
                "issuer": "AHA",
                "tag": "new",
                "reason": "Validates healthcare administration expertise"
            }
        ]
    },
    "overall_feedback": {
        "strengths": ["Extensive healthcare experience (11 years)", "Strong patient management background"],
        "weaknesses": ["No explicit leadership/management experience shown", "Missing compliance certifications"],
        "quick_wins": ["Add HIPAA and compliance keywords", "Reframe front desk role as operations management"],
        "interview_tips": ["Prepare examples of handling difficult patients", "Be ready to discuss EHR systems experience"]
    },
    "writing_quality": {
        "grammar_issues": [
            {
                "original": "Greeted patients and visitors, ensuring a positive first impression.",
                "corrected": "Greeted patients and visitors, ensuring positive first impressions.",
                "location": "work_experience[0].description[0]",
                "issue_type": "grammar"
            }
        ],
        "tone_analysis": {
            "current_tone": "professional but passive",
            "recommended_tone": "confident and results-oriented",
            "tone_issues": ["Too many passive constructions", "Lacks confident language"]
        },
        "passive_voice_instances": [
            {
                "original": "was responsible for managing",
                "active_version": "managed",
                "location": "work_experience[0].description[1]"
            }
        ],
        "weak_phrases": [
            {
                "weak_phrase": "responsible for",
                "stronger_alternative": "led/managed/directed",
                "reason": "Passive and doesn't show ownership"
            },
            {
                "weak_phrase": "helped with",
                "stronger_alternative": "contributed to/supported/facilitated",
                "reason": "Vague and minimizes contribution"
            }
        ],
        "action_verbs": {
            "weak_verbs_used": ["handled", "managed", "worked"],
            "recommended_power_verbs": ["orchestrated", "streamlined", "spearheaded", "optimized", "implemented"]
        }
    },
    "ats_optimization": {
        "ats_score": 62,
        "keyword_density": {
            "jd_keywords_found": ["patient management", "scheduling", "EHR"],
            "jd_keywords_missing": ["HIPAA", "compliance", "budget", "staff supervision", "healthcare regulations"],
            "keyword_match_percentage": 45
        },
        "formatting_issues": ["No issues detected"],
        "section_headers": {
            "standard_headers_used": ["Work Experience", "Education", "Skills"],
            "non_standard_headers": [],
            "recommended_headers": ["Professional Summary", "Certifications", "Projects"]
        }
    },
    "industry_vocabulary": {
        "current_industry_terms": ["patient management", "EHR", "appointment scheduling"],
        "missing_industry_terms": ["care coordination", "patient outcomes", "clinical workflows", "regulatory compliance"],
        "buzzwords_to_add": ["patient-centered care", "operational excellence", "quality improvement"],
        "outdated_terms": []
    },
    "quantification_opportunities": [
        {
            "current_text": "Managed appointment scheduling",
            "location": "work_experience[0].description[1]",
            "suggestion": "Add volume and efficiency metrics",
            "example_metrics": ["X appointments per day", "Y% reduction in wait times", "Z% scheduling accuracy"]
        }
    ],
    "red_flags": [
        {
            "issue": "Single employer for 11 years may raise questions about adaptability",
            "severity": "low",
            "recommendation": "Highlight diverse responsibilities and growth within the role"
        }
    ],
    "length_analysis": {
        "current_length": "appropriate",
        "recommended_length": "1 page for this experience level",
        "sections_to_trim": [],
        "sections_to_expand": ["Skills section could include more technical competencies"]
    },
    "next_steps": {
        "current_score": 58,
        "potential_score": 86,
        "summary": "Focus on adding projects to gain up to 15 points.",
        "suggestions": [
            {
                "priority": 1,
                "section": "projects",
                "current_score": 0,
                "max_score": 15,
                "potential_gain": 15,
                "action": "Add 3 more project(s) to reach 3 total",
                "hint": "Ask me to 'add a project about [technology from JD]' or 'suggest projects for this role'",
                "impact": "high"
            },
            {
                "priority": 2,
                "section": "skills",
                "current_score": 14.5,
                "max_score": 35,
                "potential_gain": 10,
                "action": "Add more JD-relevant skills (18/45 keywords matched)",
                "hint": "Ask me to 'add missing skills from the JD' or 'what skills am I missing?'",
                "impact": "high"
            },
            {
                "priority": 3,
                "section": "work_experience",
                "current_score": 3.5,
                "max_score": 10,
                "potential_gain": 6.5,
                "action": "Inject more JD keywords into work experience descriptions",
                "hint": "Ask me to 'optimize my work experience for ATS' or 'add keywords to my job descriptions'",
                "impact": "medium"
            }
        ]
    },
    "session_info": {
        "session_id": "sess_abc123def456",
        "expires_at": "2024-12-27T10:00:00.000Z",
        "chatbot_enabled": true
    }
}
```

**Key Output:**
- `next_steps.suggestions` - Prioritized list of what to improve next with hints
- `next_steps.summary` - Quick summary of top priority
- Frontend can show these as clickable suggestions to guide user

**Frontend stores:**
- `sessionId = response.session_info.session_id`
- Display recommendations to user with Accept/Decline buttons

---

# Step 3b: User Accepts/Declines Recommendations (Frontend)

**This happens in the frontend UI - NO API call.**

Frontend displays each recommendation with:
- Original content
- Suggested content
- Accept / Decline buttons

### Frontend Logic (JavaScript Example)

```javascript
// Store the current CV state (starts as parsed CV)
let currentCV = { ...parsedCV };

// When user clicks "Accept" on a recommendation
function acceptRecommendation(recommendation) {
    const { field_path, content, tag } = recommendation;

    // Apply change to currentCV using field_path
    applyChange(currentCV, field_path, content, tag);

    // Update UI to show accepted state
    markAsAccepted(recommendation);
}

// When user clicks "Decline" on a recommendation
function declineRecommendation(recommendation) {
    // Just mark as declined in UI, don't apply
    markAsDeclined(recommendation);
}

// Helper to apply changes using field_path
function applyChange(cv, fieldPath, newValue, tag) {
    // Parse field path: "work_experience[0].description[2]"
    // and set the value at that path

    if (tag === "new") {
        // For new items, append to array or create field
        appendToPath(cv, fieldPath, newValue);
    } else if (tag === "modified") {
        // For modified items, replace existing value
        setAtPath(cv, fieldPath, newValue);
    }
}

// Example field path parsing
function setAtPath(obj, path, value) {
    const parts = path.match(/([^\[\].]+|\[\d+\])/g);
    let current = obj;

    for (let i = 0; i < parts.length - 1; i++) {
        let part = parts[i];
        if (part.startsWith('[')) {
            const index = parseInt(part.slice(1, -1));
            current = current[index];
        } else {
            if (!current[part]) current[part] = {};
            current = current[part];
        }
    }

    const lastPart = parts[parts.length - 1];
    if (lastPart.startsWith('[')) {
        const index = parseInt(lastPart.slice(1, -1));
        current[index] = value;
    } else {
        current[lastPart] = value;
    }
}
```

---

# Step 3c: Sync Updated CV to Backend

**After user finishes accepting/declining, sync the updated CV to backend.**

### Request

```bash
curl -X PUT http://localhost:8001/api/v1/session \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "parsed_cv": {
        "contact_info": {...},
        "title": "Healthcare Operations Manager | Patient Services & Compliance",
        "professional_summary": "Results-driven healthcare professional with 11+ years...",
        "work_experience": [
            {
                "job_title": "Front Desk Officer",
                "company": "National Hospital & Medical Center",
                "description": [
                    "Supervised front-of-house operations serving 200+ patients daily with 98% satisfaction rate",
                    "Managed appointment scheduling and maintained front desk operations.",
                    "Handled patient inquiries, telephone calls, and front desk documentation.",
                    "Coordinated with medical staff and departments to ensure smooth patient flow.",
                    "Implemented workflow optimization initiatives reducing patient wait times by 25%"
                ]
            }
        ],
        "skills": [
            "Patient Management",
            "Appointment Scheduling",
            "Customer Service",
            "Electronic Health Records",
            "MS Office",
            "HIPAA Compliance",
            "Budget Management",
            "Staff Leadership"
        ],
        "projects": [
            {
                "name": "EHR System Implementation & Staff Training",
                "description": "Led implementation of electronic health records system...",
                "technologies": ["Epic EHR", "Staff Training", "Change Management"]
            },
            {
                "name": "Patient Flow Optimization Initiative",
                "description": "Designed and implemented patient scheduling system...",
                "technologies": ["Process Optimization", "Scheduling Systems"]
            },
            {
                "name": "HIPAA Compliance Audit Program",
                "description": "Established compliance monitoring program...",
                "technologies": ["HIPAA", "Compliance Auditing"]
            }
        ],
        ...
    }
}'
```

### Response

```json
{
    "status": "success",
    "session_id": "sess_abc123def456",
    "message": "CV updated in session"
}
```

**Now backend has the latest CV state. Chat will use this.**

---

# Step 4: Chat About Sections (NO CV SENT)

**From now on, only `session_id` is sent. Backend uses `current_cv` from session.**

User selects a section from dropdown and asks for improvements.

### Request

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "section": "work_experience",
    "message": "Can you improve my second bullet point to show more leadership?"
}'
```

### Response (With Action)

```json
{
    "message": "I've enhanced your second bullet point to demonstrate leadership.\n\n**Original:**\n\"Managed appointment scheduling and maintained front desk operations.\"\n\n**Improved:**\n\"Directed appointment scheduling operations for 5-physician practice, managing 150+ daily bookings while mentoring 3 junior staff.\"",
    "section": "work_experience",
    "session_id": "sess_abc123def456",
    "action": {
        "action_id": "action_7f8g9h0i1j2k",
        "action_type": "improve",
        "section": "work_experience",
        "status": "pending",
        "description": "Improve second work experience bullet to show leadership",
        "changes": [
            {
                "field": "work_experience[0].description[1]",
                "change_type": "replace",
                "original_value": "Managed appointment scheduling and maintained front desk operations.",
                "new_value": "Directed appointment scheduling operations for 5-physician practice, managing 150+ daily bookings while mentoring 3 junior staff."
            }
        ],
        "requires_confirmation": true
    },
    "next_steps": {
        "current_score": 58,
        "potential_score": 78,
        "summary": "Focus on adding projects to gain up to 15 points.",
        "suggestions": [
            {
                "priority": 1,
                "section": "projects",
                "potential_gain": 15,
                "action": "Add 3 project(s)",
                "hint": "Ask me to 'suggest projects for this role'"
            }
        ]
    }
}
```

### Response (No Action - Just Q&A)

```json
{
    "message": "Your work experience looks good! The bullets now show metrics and leadership. If you want, I can add more quantifiable achievements?",
    "section": "work_experience",
    "session_id": "sess_abc123def456",
    "next_steps": {
        "current_score": 58,
        "potential_score": 78,
        "summary": "Focus on adding projects to gain up to 15 points.",
        "suggestions": [...]
    }
}
```

**Note:** `next_steps` shows what to improve next. Use `suggestions[].hint` as clickable prompts.

---

# Step 5: Approve Chat Action

User clicks "Apply" button after reviewing the suggested change.

### Request

```bash
curl -X POST http://localhost:8001/api/v1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "action_ids": ["action_7f8g9h0i1j2k"]
}'
```

### Response

```json
{
    "status": "success",
    "confirmed_count": 1,
    "confirmed_actions": [
        {
            "action_id": "action_7f8g9h0i1j2k",
            "action_type": "improve",
            "section": "work_experience",
            "status": "confirmed",
            "description": "Improve second work experience bullet to show leadership",
            "changes": [
                {
                    "field": "work_experience[0].description[1]",
                    "change_type": "replace",
                    "original_value": "Managed appointment scheduling and maintained front desk operations.",
                    "new_value": "Directed appointment scheduling operations for 5-physician practice, managing 150+ daily bookings while mentoring 3 junior staff."
                }
            ]
        }
    ],
    "not_found": [],
    "current_cv": {
        "title": "Healthcare Operations Manager | Patient Services & Compliance",
        "work_experience": [...],
        "skills": [...],
        ...
    },
    "new_scores": {
        "current_match_score": 72,
        "rating": "Good",
        "breakdown": {
            "skills_score": 28.5,
            "experience_score": 25,
            "education_score": 15,
            "projects_score": 0,
            "keywords_score": 3.5
        },
        "details": {
            "jd_keywords_count": 45,
            "keywords_matched": 18,
            "cv_years": 11,
            "required_years": 5,
            "project_count": 0,
            "skills_count": 8
        }
    },
    "message": "Successfully confirmed 1 action(s)"
}
```

**Key Points:**
- `current_cv` - Updated CV with approved changes applied
- `new_scores` - **Recalculated score** based on updated CV vs JD (deterministic formula)
- Frontend should sync CV display and update score indicator

---

# Repeat Steps 4-5

User continues chatting about other sections. Each `/approve` returns updated `current_cv`.

---

# Session Management

## Get Session Info

```bash
curl -X GET http://localhost:8001/api/v1/session/sess_abc123def456
```

```json
{
    "session_id": "sess_abc123def456",
    "created_at": "2024-12-26T10:00:00.000Z",
    "expires_at": "2024-12-27T10:00:00.000Z",
    "job_title": "Healthcare Administrator",
    "chat_history_count": 5,
    "analysis_available": true
}
```

## Delete Session

```bash
curl -X DELETE http://localhost:8001/api/v1/session/sess_abc123def456
```

```json
{
    "status": "success",
    "message": "Session deleted"
}
```

---

# Field Path Reference

| Field Path | Target | Example |
|------------|--------|---------|
| `title` | Job title | "Front Desk Officer" |
| `professional_summary` | Summary text | "Dynamic professional..." |
| `skills` | Entire skills array | ["Skill1", "Skill2"] |
| `skills[5]` | 6th skill (0-indexed) | "HIPAA Compliance" |
| `work_experience[0]` | First job | {...} |
| `work_experience[0].job_title` | First job's title | "Front Desk Officer" |
| `work_experience[0].description` | First job's bullets | ["Bullet1", "Bullet2"] |
| `work_experience[0].description[1]` | Second bullet of first job | "Managed scheduling..." |
| `education[0].degree` | First education's degree | "Bachelor of Commerce" |
| `projects[0]` | First project | {...} |
| `projects[0].name` | First project name | "EHR Implementation" |
| `projects[0].description` | First project description | "Led implementation..." |
| `certifications[0].name` | First certification name | "cHAP" |

---

# Frontend Action Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  STEP 3: ANALYZE RECOMMENDATIONS                            │
│  ─────────────────────────────────────────                  │
│  For each recommendation:                                   │
│    - Display original vs suggested                          │
│    - Show [Accept] [Decline] buttons                        │
│    - Use field_path to apply accepted changes locally       │
│                                                             │
│  When done accepting/declining:                             │
│    → PUT /api/v1/session (sync updated CV to backend)       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 4-5: CHAT FLOW                                        │
│  ─────────────────────────────────────────                  │
│  User sends message → POST /api/v1/chat                     │
│                              │                              │
│                              ▼                              │
│                    Response has action?                     │
│                      /            \                         │
│                    NO              YES                      │
│                    │                │                       │
│                    ▼                ▼                       │
│              Show message     Show message +                │
│                only          [Apply] button                 │
│                                     │                       │
│                                     ▼                       │
│                           User clicks "Apply"               │
│                                     │                       │
│                                     ▼                       │
│                          POST /api/v1/approve               │
│                                     │                       │
│                                     ▼                       │
│                    Update UI with current_cv                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

# Complete Session Example

```
1. Parse CV
   └─► POST http://localhost:8000/parse
   └─► Frontend stores: parsedCV

2. User enters Job Description
   └─► Frontend collects: job_title, job_description

3. Analyze CV against JD
   └─► POST /api/v1/analyze
   └─► Frontend displays: scores + recommendations with Accept/Decline
   └─► Frontend stores: sessionId

3b. User accepts/declines recommendations (IN FRONTEND)
   └─► User clicks Accept on title change
   └─► User clicks Accept on 2 new skills
   └─► User clicks Decline on 1 project
   └─► Frontend applies accepted changes to local currentCV

3c. Sync updated CV to backend
   └─► PUT /api/v1/session (with currentCV)
   └─► Backend now has latest CV state

4. User selects "Work Experience" section, asks question
   └─► POST /api/v1/chat (session_id + section + message)
   └─► Response: feedback (no action)

5. User asks for specific change
   └─► POST /api/v1/chat
   └─► Response: message + action (status: pending)

6. User clicks "Apply"
   └─► POST /api/v1/approve
   └─► Response: confirmed_actions + current_cv
   └─► Frontend updates display

7. User continues with other sections...
   └─► Repeat steps 4-6

8. User done
   └─► DELETE /api/v1/session/{id}
```

---

# Summary Table

| Step | Endpoint | What's Sent | What's Returned |
|------|----------|-------------|-----------------|
| Parse CV | `POST /parse` | PDF file | Structured CV JSON |
| Analyze | `POST /analyze` | CV + JD + instructions | Scores + recommendations (with field_path) |
| Sync CV | `PUT /session` | session_id + updated CV | Success |
| Chat | `POST /chat` | session_id + section + message | Message + optional action |
| Approve | `POST /approve` | session_id + action_ids | Confirmed actions + current_cv + **new_scores** |
| Get info | `GET /session/{id}` | - | Session info |
| End | `DELETE /session/{id}` | - | Success |

---

# Scoring Formula (Deterministic)

Scores are calculated using a **deterministic formula** (not LLM estimation) for consistency.

## Formula: 100 Points Total

| Component | Max Points | Calculation |
|-----------|------------|-------------|
| **Skills** | 35 | `(keywords_matched / jd_keywords) × 35` |
| **Experience** | 25 | `min(cv_years / required_years, 1.5) × 25` |
| **Education** | 15 | Degree match: 15 (has degree), 12 (not required), 5 (missing but required) |
| **Projects** | 15 | 0 projects: 0, 1: 5, 2: 10, 3+: 15 |
| **Keywords/ATS** | 10 | `(jd_keywords_in_cv / total_jd_keywords) × 10` |

## Rating Thresholds

| Score | Rating |
|-------|--------|
| 80-100 | Excellent |
| 65-79 | Good |
| 50-64 | Fair |
| 0-49 | Poor |

## Example Calculation

```
CV: 11 years experience, Bachelor's degree, 0 projects, 8 skills
JD: Requires 5 years, 45 keywords extracted

Skills Score:    18 keywords matched / 45 total × 35 = 14.0
Experience:      min(11/5, 1.5) × 25 = 25.0 (capped at 25)
Education:       Has degree = 15.0
Projects:        0 projects = 0.0
Keywords:        18 matched / 45 total × 10 = 4.0
─────────────────────────────────────────────────
TOTAL:           58 points → "Fair" rating
```

## Why Deterministic?

- **Consistent**: Same CV + JD always produces same score
- **Transparent**: User can understand why score changed
- **Trackable**: Frontend can show score delta after each change
