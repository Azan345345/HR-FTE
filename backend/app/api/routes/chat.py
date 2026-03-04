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

    # Sanitize — strip null bytes that PostgreSQL TEXT rejects
    safe_message = body.message.replace('\x00', '').replace('\x0b', '').replace('\x0c', '')

    # Display version stored in DB — strip [ATTACHED FILE:] block so chat
    # history shows the user's clean text, not 6000 chars of file content.
    if "[ATTACHED FILE:" in safe_message:
        display_message = safe_message.split("[ATTACHED FILE:", 1)[0].strip() or "[File attached]"
    else:
        display_message = safe_message

    # Save user message (clean display version)
    try:
        user_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=display_message,
        )
        db.add(user_msg)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save message: {str(e)}")

    # Process through supervisor agent — returns (text, metadata)
    response_text = "I'm sorry, I encountered an error. Please try again."
    response_metadata = None
    try:
        from app.agents.supervisor import process_chat_message
        result = await process_chat_message(
            user_id=user_id,
            session_id=session_id,
            message=safe_message,
            db=db,
            pipeline=body.pipeline,
        )
        # Supervisor now returns a tuple (text, metadata)
        if isinstance(result, tuple):
            response_text, response_metadata = result
        else:
            response_text = result
    except Exception as e:
        response_text = f"I'm sorry, I encountered an error: {str(e)}. Please try again."

    # The agent may have held db open for minutes — the original connection is
    # likely dead after 30+ seconds of external API calls.  Use a fresh session
    # so the assistant message save never fails due to a stale connection.
    from app.db.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as fresh_db:
            assistant_msg = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                agent_name="supervisor",
                content=response_text,
                metadata_=response_metadata or {},
            )
            fresh_db.add(assistant_msg)
            await fresh_db.commit()
            await fresh_db.refresh(assistant_msg)
    except Exception as e:
        # If even a fresh session fails, return the response without persisting
        import structlog
        structlog.get_logger().warning("chat_save_failed", error=str(e))
        return ChatMessageResponse(
            id="",
            role="assistant",
            agent_name="supervisor",
            content=response_text,
            metadata=response_metadata,
            created_at=None,
        )

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

    def _clean(text: str) -> str:
        """Strip null bytes and other characters PostgreSQL TEXT rejects."""
        return text.replace('\x00', '').replace('\x0b', '').replace('\x0c', '')

    extracted = ""
    try:
        if ext in ("txt", "md"):
            extracted = _clean(content_bytes.decode("utf-8", errors="replace"))
        elif ext == "pdf":
            import io
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content_bytes))
                extracted = _clean("\n".join(page.extract_text() or "" for page in reader.pages))
            except Exception:
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract text from the PDF. Please save it as .txt and re-attach.",
                )
        elif ext == "docx":
            import io
            try:
                import docx
                doc = docx.Document(io.BytesIO(content_bytes))
                extracted = _clean("\n".join(p.text for p in doc.paragraphs))
            except Exception:
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract text from the DOCX. Please save it as .txt and re-attach.",
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read file: {str(e)}")

    if not extracted.strip():
        raise HTTPException(
            status_code=422,
            detail="The file appears to be empty or contains no readable text.",
        )

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
