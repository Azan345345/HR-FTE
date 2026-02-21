"""Digital FTE - Chat Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.api.routes.auth import get_current_user
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str

@router.post("")
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a natural language request triggering the LangGraph agent mesh.
    """
    return await chat_service.process_chat_message(db, current_user.id, payload.message)

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history. Implemented in Phase 7."""
    return {"messages": []}
