"""
Digital FTE - File Upload/Download Handler
Handles CV file upload, validation, and text extraction.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple

import pdfplumber
from docx import Document as DocxDocument
from fastapi import UploadFile, HTTPException

from app.config import settings

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


async def save_upload(file: UploadFile, user_id: str) -> Tuple[str, str]:
    """
    Save an uploaded file to disk.
    Returns (saved_path, file_type).
    """
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use PDF or DOCX.")

    # Validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    # Create user upload directory
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save with unique name
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = user_dir / unique_name

    with open(save_path, "wb") as f:
        f.write(contents)

    file_type = ext.lstrip(".")  # "pdf" or "docx"
    return str(save_path), file_type


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {str(e)}")

    if not text_parts:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF. Is it image-based?")

    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        doc = DocxDocument(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse DOCX: {str(e)}")

    if not paragraphs:
        raise HTTPException(status_code=422, detail="DOCX appears to be empty.")

    return "\n\n".join(paragraphs)


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from a file based on its type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")


def delete_file(file_path: str) -> bool:
    """Delete a file from disk. Returns True if deleted."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except OSError:
        pass
    return False
