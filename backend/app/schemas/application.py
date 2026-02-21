"""Digital FTE - Application Schemas"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class JobMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str
    location: Optional[str] = None

class HRContactBase(BaseModel):
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    hr_title: Optional[str] = None
    hr_linkedin: Optional[str] = None
    confidence_score: Optional[float] = None
    source: Optional[str] = None
    verified: bool = False

class HRContactRead(HRContactBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    job_id: UUID
    created_at: Optional[datetime] = None

class ApplicationBase(BaseModel):
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    status: str = "pending_approval"
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    job_id: UUID
    tailored_cv_id: Optional[UUID] = None
    hr_contact_id: Optional[UUID] = None

class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    job_id: UUID
    tailored_cv_id: Optional[UUID] = None
    hr_contact_id: Optional[UUID] = None
    email_sent_at: Optional[datetime] = None
    gmail_message_id: Optional[str] = None
    user_approved: bool
    user_approved_at: Optional[datetime] = None
    follow_up_count: int
    last_follow_up_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Nested for convenience
    hr_contact: Optional[HRContactRead] = None
    job: Optional[JobMinimal] = None

class ApplicationApproval(BaseModel):
    approved: bool
    edited_email_body: Optional[str] = None
    edited_email_subject: Optional[str] = None
