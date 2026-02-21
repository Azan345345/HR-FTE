"""Digital FTE - Chat Schemas"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatMessageCreate(BaseModel):
    session_id: UUID
    content: str


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    role: str
    agent_name: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
