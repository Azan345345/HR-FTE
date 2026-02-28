"""
FastAPI application for CV/Resume parsing using Experiment 3 focused schema.
Accepts CV file uploads for parsing.
"""

import os
import tempfile
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from parser_v3 import CVParserV3

# Initialize FastAPI app
app = FastAPI(
    title="CV Parser API (Experiment 3)",
    description="Extract essential CV information with focused schema. Accepts CV PDF file uploads.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Parser will be lazily initialized
parser = None

def get_parser():
    """Get or initialize the parser instance."""
    global parser
    if parser is None:
        parser = CVParserV3()
    return parser


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CV Parser API (Experiment 3 - Focused Schema)",
        "version": "3.0.0",
        "description": "Extract essential CV information with NULL for missing data",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "parse": "/parse"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "cv-parser-api-v3",
        "experiment": "Experiment 3 - Focused Schema",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.post("/parse", response_model=Dict[str, Any])
async def parse_cv(file: UploadFile = File(...)):
    """
    Parse a CV/Resume PDF file upload and extract structured information.

    Args:
        file: Uploaded PDF file

    Returns:
        JSON object with extracted CV information (no cost metrics)

    Raises:
        HTTPException: If file is not a PDF or parsing fails
    """
    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported (.pdf extension required)"
        )

    # Read the uploaded file content
    try:
        print(f"Processing uploaded file: {file.filename}")
        pdf_content = await file.read()

        # Check if file is too small
        if len(pdf_content) < 100:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file is too small ({len(pdf_content)} bytes). The file may be empty or corrupted."
            )

        # Check PDF magic bytes (PDF files start with %PDF)
        if not pdf_content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid PDF file."
            )

        print(f"Received {len(pdf_content)} bytes")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    # Save to temporary file and parse
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file_path = tmp_file.name

        # Parse the CV
        result = get_parser().parse_cv(tmp_file_path, file.filename)

        # Clean up temporary file
        os.unlink(tmp_file_path)

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse CV. The file may be corrupted or unreadable."
            )

        # Return only the parsed data (no cost metrics as requested)
        return {
            "success": True,
            "filename": file.filename,
            "data": result['data']
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up temporary file if it exists
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the CV: {str(e)}"
        )


if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(
        "app_v3:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "production") == "development"
    )
