"""Digital FTE - CV Schemas (expanded with strongly-typed nested models)"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ── Nested models for parsed CV data ──────────────


class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class SkillSet(BaseModel):
    technical: List[str] = Field(default_factory=list)
    soft: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    company: str
    role: str
    duration: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    achievements: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None


class ProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None


# ── Main parsed CV model ─────────────────────────


class ParsedCVData(BaseModel):
    """Structured CV data extracted by the CV Parser agent."""
    personal_info: Optional[PersonalInfo] = None
    summary: Optional[str] = None
    skills: Optional[SkillSet] = None
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


# ── API schemas ──────────────────────────────────


class CVUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_name: str
    file_type: str
    is_primary: bool
    parsed_data: Optional[dict] = None
    created_at: Optional[datetime] = None


class CVRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_name: str
    file_type: str
    parsed_data: Optional[dict] = None
    raw_text: Optional[str] = None
    is_primary: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CVListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_name: str
    file_type: str
    is_primary: bool
    has_parsed_data: bool = False
    created_at: Optional[datetime] = None


class CVAnalysis(BaseModel):
    """Response for CV analysis endpoint."""
    cv_id: UUID
    parsed_data: ParsedCVData
    estimated_years: int = 0
    sections_found: List[str] = Field(default_factory=list)
    embedding_stored: bool = False
