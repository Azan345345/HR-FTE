"""Digital FTE - Interview Prep Schemas"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.application import JobMinimal

class QA_Pair(BaseModel):
    question: str
    hints: Optional[List[str]] = None
    ideal_answer: Optional[str] = None

class CompanyResearch(BaseModel):
    overview: Optional[str] = None
    culture_insights: Optional[str] = None

class InterviewPrepBase(BaseModel):
    status: str = "generating"
    company_research: Optional[Dict[str, Any]] = None
    technical_questions: Optional[List[Dict[str, Any]]] = None
    behavioral_questions: Optional[List[Dict[str, Any]]] = None
    situational_questions: Optional[List[Dict[str, Any]]] = None
    salary_research: Optional[Dict[str, Any]] = None
    tips: Optional[List[str]] = None
    study_material_path: Optional[str] = None
    prep_score: Optional[float] = None

class InterviewPrepCreate(InterviewPrepBase):
    job_id: UUID
    application_id: Optional[UUID] = None

class InterviewPrepRead(InterviewPrepBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    job_id: UUID
    application_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    
    # Nested for convenience
    job: Optional[JobMinimal] = None
