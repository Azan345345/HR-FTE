"""
FastAPI Application for CV-JD Matching and Improvement System.
Analyzes CVs against Job Descriptions and provides improvement suggestions.
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from improvement_engine import CVImprovementEngine


# Initialize FastAPI app
app = FastAPI(
    title="CV-JD Matching & Improvement API",
    description="AI-powered CV analysis, matching, and improvement system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}

# Lazy-loaded engine
engine: Optional[CVImprovementEngine] = None


def get_engine() -> CVImprovementEngine:
    """Get or initialize the improvement engine."""
    global engine
    if engine is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        engine = CVImprovementEngine(api_key=api_key)
    return engine


# ============== Pydantic Models ==============

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class WorkExperience(BaseModel):
    company: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[Any] = None  # Can be string or list
    achievements: List[str] = []


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    location: Optional[str] = None


class Skills(BaseModel):
    technical_skills: Optional[List[str]] = []
    soft_skills: Optional[List[str]] = []
    languages: Optional[List[Any]] = []


class ParsedCV(BaseModel):
    contact_info: Optional[Dict[str, Any]] = None
    personal_info: Optional[PersonalInfo] = None
    title: Optional[str] = None
    professional_summary: Optional[Any] = None
    summary: Optional[str] = None
    work_experience: Optional[List[Dict[str, Any]]] = []
    education: Optional[List[Dict[str, Any]]] = []
    skills: Optional[Any] = None
    certifications: Optional[List[Dict[str, Any]]] = []
    projects: Optional[List[Dict[str, Any]]] = []
    awards_scholarships: Optional[List[Dict[str, Any]]] = []
    publications: Optional[List[Dict[str, Any]]] = []
    total_years_of_experience: Optional[float] = None

    class Config:
        extra = "allow"  # Allow additional fields


class AnalyzeRequest(BaseModel):
    parsed_cv: Dict[str, Any]  # Flexible to accept any CV format
    job_title: str
    job_description: str
    instructions: Optional[str] = None  # User's custom instructions/preferences for the analysis
    options: Dict[str, bool] = Field(default_factory=lambda: {
        "include_full_cv": True,
        "generate_missing_projects": True,
        "tone_analysis": True,
        "keyword_optimization": True
    })


class ChatMessage(BaseModel):
    session_id: str
    message: str
    section: Optional[str] = "entire_resume"  # entire_resume, professional_summary, work_experience, education, skills, projects, certifications


class ActionChange(BaseModel):
    field: str  # e.g., "professional_summary", "work_experience[0].description[2]"
    original_value: Optional[Any] = None
    new_value: Any
    change_type: str  # "replace", "add", "remove", "modify"


class ChatAction(BaseModel):
    action_id: str
    action_type: str  # "improve", "add", "remove", "replace", "rewrite", "none"
    section: str
    status: str  # "pending", "confirmed", "rejected"
    description: str  # Human-readable description of what this action does
    changes: List[Dict[str, Any]]  # List of specific changes
    requires_confirmation: bool = True


class ApprovalRequest(BaseModel):
    session_id: str
    action_ids: List[str]  # Changed from change_ids to action_ids


class CreateSessionRequest(BaseModel):
    """Create a chat session with CV data (without running full analysis)"""
    parsed_cv: Dict[str, Any]
    job_title: Optional[str] = None
    job_description: Optional[str] = None


class UpdateCVRequest(BaseModel):
    """Update the CV in an existing session"""
    session_id: str
    parsed_cv: Dict[str, Any]


# ============== Helper Functions ==============

def _apply_changes_to_cv(session: Dict, action: Dict) -> None:
    """
    Apply action changes to the current_cv in session.

    Handles field paths like:
    - "professional_summary" -> direct field
    - "skills" -> entire array
    - "skills[0]" -> specific array item
    - "work_experience[0].description[2]" -> nested array item
    """
    import re

    current_cv = session.get("current_cv", {})
    if not current_cv:
        current_cv = session.get("parsed_cv", {}).copy()
        session["current_cv"] = current_cv

    for change in action.get("changes", []):
        field = change.get("field", "")
        change_type = change.get("change_type", "replace")
        new_value = change.get("new_value")

        try:
            # Parse field path: "work_experience[0].description[2]"
            parts = re.split(r'\.(?![^\[]*\])', field)  # Split by . but not inside []

            obj = current_cv
            for i, part in enumerate(parts[:-1]):
                # Handle array indexing: "work_experience[0]"
                match = re.match(r'(\w+)\[(\d+)\]', part)
                if match:
                    key, index = match.groups()
                    if key not in obj:
                        obj[key] = []
                    while len(obj[key]) <= int(index):
                        obj[key].append({})
                    obj = obj[key][int(index)]
                else:
                    if part not in obj:
                        obj[part] = {}
                    obj = obj[part]

            # Handle the final part
            final_part = parts[-1]
            match = re.match(r'(\w+)\[(\d+)\]', final_part)

            if match:
                key, index = match.groups()
                index = int(index)
                if key not in obj:
                    obj[key] = []

                if change_type == "add":
                    obj[key].append(new_value)
                elif change_type == "remove":
                    if index < len(obj[key]):
                        obj[key].pop(index)
                else:  # replace or modify
                    while len(obj[key]) <= index:
                        obj[key].append(None)
                    obj[key][index] = new_value
            else:
                if change_type == "add":
                    if final_part not in obj:
                        obj[final_part] = []
                    if isinstance(obj[final_part], list):
                        obj[final_part].append(new_value)
                    else:
                        obj[final_part] = new_value
                elif change_type == "remove":
                    if final_part in obj:
                        del obj[final_part]
                else:  # replace or modify
                    obj[final_part] = new_value

        except Exception as e:
            # Log error but don't fail the whole operation
            print(f"Error applying change to field '{field}': {e}")
            continue


# ============== API Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CV-JD Matching & Improvement API",
        "version": "1.0.0",
        "description": "AI-powered CV analysis and improvement system",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "create_session": "POST /api/v1/session - Create chat session with CV",
            "update_cv": "PUT /api/v1/session - Update CV in session",
            "analyze": "POST /api/v1/analyze - Full CV-JD analysis",
            "chat": "POST /api/v1/chat - Chat about CV sections",
            "approve": "POST /api/v1/approve - Approve pending actions",
            "get_session": "GET /api/v1/session/{session_id}",
            "delete_session": "DELETE /api/v1/session/{session_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "cv-jd-matching",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.post("/api/v1/session")
async def create_session(request: CreateSessionRequest):
    """
    Create a chat session with CV data (without running full analysis).

    Use this when you want to chat about a CV without matching against a JD.
    The CV can be modified through chat, and you can optionally add JD later.

    Request:
        - parsed_cv: The parsed CV data
        - job_title: Optional job title for context
        - job_description: Optional JD for context

    Returns:
        - session_id: Use this for subsequent chat/approve calls
    """
    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "parsed_cv": request.parsed_cv,
        "current_cv": request.parsed_cv.copy(),  # Track current state (with approved changes)
        "job_title": request.job_title,
        "job_description": request.job_description,
        "analysis": None,  # No analysis yet
        "chat_history": [],
        "pending_actions": {},
        "confirmed_actions": {},
        "applied_changes": []  # Track what changes have been applied
    }

    return {
        "status": "success",
        "session_id": session_id,
        "expires_at": sessions[session_id]["expires_at"],
        "message": "Session created. You can now use /api/v1/chat to discuss the CV."
    }


@app.put("/api/v1/session")
async def update_session_cv(request: UpdateCVRequest):
    """
    Update the CV in an existing session.

    Use this when the CV has been modified externally (e.g., user edited in UI)
    and you want the chat to know about the latest state.

    Request:
        - session_id: Existing session ID
        - parsed_cv: Updated CV data
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[request.session_id]
    session["parsed_cv"] = request.parsed_cv
    session["current_cv"] = request.parsed_cv.copy()
    session["applied_changes"].append({
        "type": "cv_update",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "external"
    })

    return {
        "status": "success",
        "session_id": request.session_id,
        "message": "CV updated in session"
    }


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
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        improvement_engine = get_engine()

        # Perform analysis
        analysis = improvement_engine.analyze(
            parsed_cv=request.parsed_cv,
            job_title=request.job_title,
            job_description=request.job_description,
            options=request.options,
            instructions=request.instructions
        )

        processing_time = int((time.time() - start_time) * 1000)

        # Create session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "parsed_cv": request.parsed_cv,
            "current_cv": request.parsed_cv.copy(),  # Track current state
            "job_title": request.job_title,
            "job_description": request.job_description,
            "analysis": analysis,
            "chat_history": [],
            "pending_actions": {},
            "confirmed_actions": {},
            "applied_changes": []
        }

        # Get improvement suggestions
        suggestions = improvement_engine.get_improvement_suggestions(
            parsed_cv=request.parsed_cv,
            job_description=request.job_description
        )

        # Build response
        response = {
            "metadata": {
                "request_id": request_id,
                "processed_at": datetime.utcnow().isoformat(),
                "job_title": request.job_title,
                "processing_time_ms": processing_time
            },
            **analysis,
            "next_steps": {
                "current_score": suggestions["current_score"],
                "potential_score": suggestions["potential_score"],
                "summary": suggestions["summary"],
                "suggestions": suggestions["suggestions"]
            },
            "session_info": {
                "session_id": session_id,
                "expires_at": sessions[session_id]["expires_at"],
                "chatbot_enabled": True
            }
        }

        return response

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing CV: {str(e)}"
        )


@app.post("/api/v1/chat")
async def chat_message(request: ChatMessage):
    """
    Chatbot endpoint: Process user message and return response with optional actions.

    Supports:
    - Entire resume or section-specific conversations
    - Brainstorming/chitchat (no action)
    - Improvement suggestions (action with pending status)

    Request:
        - session_id: Session identifier
        - message: User's message
        - section: "entire_resume" | "professional_summary" | "work_experience" | "education" | "skills" | "projects" | "certifications"

    Response:
        - message: AI response text
        - action: Optional action object with changes (status: pending until confirmed)
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[request.session_id]
    section = request.section or "entire_resume"

    try:
        improvement_engine = get_engine()

        # Process chat message with section context
        response = improvement_engine.chat_with_section(
            message=request.message,
            section=section,
            session_context=session
        )

        # Update chat history
        session["chat_history"].append({
            "role": "user",
            "content": request.message,
            "section": section,
            "timestamp": datetime.utcnow().isoformat()
        })
        session["chat_history"].append({
            "role": "assistant",
            "content": response["message"],
            "section": section,
            "action": response.get("action"),
            "timestamp": datetime.utcnow().isoformat()
        })

        # Store pending action in session if present
        if response.get("action") and response["action"].get("status") == "pending":
            if "pending_actions" not in session:
                session["pending_actions"] = {}
            session["pending_actions"][response["action"]["action_id"]] = response["action"]

        # Add improvement suggestions if JD is available
        if session.get("job_description"):
            try:
                suggestions = improvement_engine.get_improvement_suggestions(
                    parsed_cv=session.get("current_cv"),
                    job_description=session.get("job_description")
                )
                response["next_steps"] = {
                    "current_score": suggestions["current_score"],
                    "potential_score": suggestions["potential_score"],
                    "summary": suggestions["summary"],
                    "suggestions": suggestions["suggestions"][:3]  # Top 3 suggestions
                }
            except Exception:
                pass  # Suggestions failed, continue without them

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )


@app.post("/api/v1/approve")
async def approve_actions(request: ApprovalRequest):
    """
    Approve/confirm pending actions and apply them to CV.

    Changes action status from "pending" to "confirmed" and updates current_cv
    so subsequent chats see the updated CV state.

    Request:
        - session_id: Session identifier
        - action_ids: List of action IDs to approve

    Response:
        - confirmed_actions: List of confirmed action objects with changes to apply
        - current_cv: Updated CV after applying changes (for frontend to sync)
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[request.session_id]
    pending_actions = session.get("pending_actions", {})

    try:
        confirmed_actions = []
        not_found = []

        for action_id in request.action_ids:
            if action_id in pending_actions:
                action = pending_actions[action_id]
                action["status"] = "confirmed"
                confirmed_actions.append(action)

                # Apply changes to current_cv
                _apply_changes_to_cv(session, action)

                # Move to confirmed actions
                if "confirmed_actions" not in session:
                    session["confirmed_actions"] = {}
                session["confirmed_actions"][action_id] = action

                # Track applied change
                if "applied_changes" not in session:
                    session["applied_changes"] = []
                session["applied_changes"].append({
                    "action_id": action_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "description": action.get("description", "")
                })

                del pending_actions[action_id]
            else:
                not_found.append(action_id)

        # Recalculate score with updated CV
        new_scores = None
        if session.get("job_description"):
            try:
                improvement_engine = get_engine()
                new_scores = improvement_engine.calculate_match_score(
                    parsed_cv=session.get("current_cv"),
                    job_description=session.get("job_description")
                )
            except Exception:
                pass  # Score calculation failed, continue without it

        response = {
            "status": "success",
            "confirmed_count": len(confirmed_actions),
            "confirmed_actions": confirmed_actions,
            "not_found": not_found,
            "current_cv": session.get("current_cv"),  # Return updated CV
            "message": f"Successfully confirmed {len(confirmed_actions)} action(s)"
        }

        # Add new scores if available
        if new_scores:
            response["new_scores"] = {
                "current_match_score": new_scores["current_match_score"],
                "rating": new_scores["rating"],
                "breakdown": new_scores["breakdown"],
                "details": new_scores.get("details", {})
            }

        # Add improvement suggestions for next steps
        if session.get("job_description"):
            try:
                suggestions = improvement_engine.get_improvement_suggestions(
                    parsed_cv=session.get("current_cv"),
                    job_description=session.get("job_description")
                )
                response["next_steps"] = {
                    "current_score": suggestions["current_score"],
                    "potential_score": suggestions["potential_score"],
                    "summary": suggestions["summary"],
                    "suggestions": suggestions["suggestions"][:3]  # Top 3 suggestions
                }
            except Exception:
                pass  # Suggestions failed, continue without them

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error approving changes: {str(e)}"
        )


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str):
    """
    Get current session state including CV and analysis.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "expires_at": session["expires_at"],
        "job_title": session["job_title"],
        "chat_history_count": len(session["chat_history"]),
        "analysis_available": "analysis" in session
    }


@app.delete("/api/v1/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del sessions[session_id]
    return {"status": "success", "message": "Session deleted"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "production") == "development"
    )
