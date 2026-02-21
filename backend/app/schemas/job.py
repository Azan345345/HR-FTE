"""Digital FTE - Job Schemas (expanded)"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class JobSearchRequest(BaseModel):
    query: str
    target_role: Optional[str] = None
    target_location: Optional[str] = None
    job_type: Optional[str] = None  # full-time, remote, hybrid
    remote_only: bool = False
    num_results: int = Field(default=10, ge=1, le=50)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    description: str
    requirements: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    posted_date: Optional[str] = None
    application_url: Optional[str] = None
    source: str = ""
    match_score: Optional[float] = None
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    source: str = ""
    match_score: Optional[float] = None
    matching_skills: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class JobSearchResponse(BaseModel):
    """Response for job search endpoint."""
    jobs: List[JobListItem]
    total: int
    query: str
