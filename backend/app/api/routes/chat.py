"""Chat interface routes — send messages, get history."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.database import get_db
from app.db.models import User, ChatMessage
from app.api.deps import get_current_user
import os
import json
from app.agents.state import DigitalFTEState
from app.schemas.schemas import (
    ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse,
    ChatSessionResponse, ChatSessionListResponse
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a chat message and get AI response."""
    session_id = body.session_id or str(uuid.uuid4())
    user_id = str(current_user.id)  # capture as plain str before any long agent calls

    # Save user message
    user_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.commit()

    # Process through supervisor agent — returns (text, metadata)
    response_text = "I'm sorry, I encountered an error. Please try again."
    response_metadata = None
    try:
        from app.agents.supervisor import process_chat_message
        result = await process_chat_message(
            user_id=user_id,
            session_id=session_id,
            message=body.message,
            db=db,
        )
        # Supervisor now returns a tuple (text, metadata)
        if isinstance(result, tuple):
            response_text, response_metadata = result
        else:
            response_text = result
    except Exception as e:
        response_text = f"I'm sorry, I encountered an error: {str(e)}. Please try again."

    # The agent may have held db open for minutes — rollback any stale state
    # so the session is clean before we write the assistant message.
    try:
        await db.rollback()
    except Exception:
        pass

    # Save assistant response with metadata
    assistant_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        agent_name="supervisor",
        content=response_text,
        metadata_=response_metadata or {},
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatMessageResponse(
        id=assistant_msg.id,
        role=assistant_msg.role,
        agent_name=assistant_msg.agent_name,
        content=assistant_msg.content,
        metadata=response_metadata,
        created_at=str(assistant_msg.created_at) if assistant_msg.created_at else None,
    )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=m.id,
                role=m.role,
                agent_name=m.agent_name,
                content=m.content,
                metadata=m.metadata_ if m.metadata_ else None,
                created_at=str(m.created_at) if m.created_at else None,
            )
            for m in messages
        ],
        session_id=session_id,
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active chat sessions with metadata."""
    first_msg_sub = (
        select(
            ChatMessage.session_id,
            ChatMessage.content.label("title"),
            func.row_number().over(
                partition_by=ChatMessage.session_id,
                order_by=ChatMessage.created_at.asc()
            ).label("rn")
        )
        .where(ChatMessage.user_id == current_user.id, ChatMessage.role == "user")
    ).subquery()

    result = await db.execute(
        select(
            ChatMessage.session_id,
            func.max(ChatMessage.created_at).label("updated_at"),
            first_msg_sub.c.title
        )
        .outerjoin(first_msg_sub, ChatMessage.session_id == first_msg_sub.c.session_id)
        .where(ChatMessage.user_id == current_user.id, first_msg_sub.c.rn == 1)
        .group_by(ChatMessage.session_id, first_msg_sub.c.title)
        .order_by(desc("updated_at"))
        .limit(20)
    )

    sessions = []
    for row in result.all():
        sessions.append(ChatSessionResponse(
            session_id=row[0],
            updated_at=str(row[1]),
            title=row[2][:50] + "..." if row[2] and len(row[2]) > 50 else (row[2] or "New Chat")
        ))

    return ChatSessionListResponse(sessions=sessions)


@router.post("/upload-context")
async def upload_context(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file to use as conversation context.

    Accepts PDF, DOCX, TXT, MD files.
    Returns extracted text content for the frontend to inject into the chat.
    """
    filename = file.filename or "file"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx", "txt", "md"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, TXT, or MD.")

    content_bytes = await file.read()
    if len(content_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    extracted = ""
    try:
        if ext == "txt" or ext == "md":
            extracted = content_bytes.decode("utf-8", errors="replace")
        elif ext == "pdf":
            import io
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                extracted = content_bytes.decode("utf-8", errors="replace")
        elif ext == "docx":
            import io
            try:
                import docx
                doc = docx.Document(io.BytesIO(content_bytes))
                extracted = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                extracted = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        extracted = f"[Could not extract text: {str(e)}]"

    return {"filename": filename, "content": extracted[:10000]}


@router.patch("/draft/{session_id}")
async def update_draft(
    session_id: str,
    draft_type: str,
    content: dict,
    current_user: User = Depends(get_current_user),
):
    """Update a draft component."""
    return {"status": "updated", "type": draft_type}
