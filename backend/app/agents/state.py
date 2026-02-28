"""LangGraph state schema for the Digital FTE multi-agent system."""

from typing import TypedDict, List, Optional, Annotated
from operator import add


class DigitalFTEState(TypedDict, total=False):
    """State shared across all agents in the LangGraph workflow."""

    # ── User context ──────────────────────────
    user_id: str
    session_id: str
    raw_cv_path: str
    user_message: str

    # ── Parsed CV ─────────────────────────────
    parsed_cv: dict
    cv_embeddings: list

    # ── Job Search ────────────────────────────
    search_query: str
    target_role: str
    target_location: str
    jobs_found: List[dict]
    selected_jobs: List[dict]

    # ── Tailored CVs ─────────────────────────
    tailored_cvs: List[dict]

    # ── HR Contacts ──────────────────────────
    hr_contacts: List[dict]

    # ── Applications ─────────────────────────
    applications_sent: List[dict]
    pending_approvals: List[dict]
    
    # ── Automation Queue ─────────────────────
    automation_queue: List[dict]  # List of jobs to process
    current_work_item: Optional[dict]  # Current job being processed
    
    # ── Human-in-the-loop ────────────────────
    user_approvals: dict  # {job_id: {cv: bool, email: bool, cover_letter: bool}}
    draft_cv: Optional[dict]
    draft_email: Optional[dict]
    draft_cover_letter: Optional[str]
    tailored_cv_pdf_path: Optional[str]  # Path to generated PDF
    waiting_for_user: bool
    
    # ── Interview Prep ───────────────────────
    interview_prep_data: List[dict]

    # ── Agent Orchestration ──────────────────
    current_agent: str
    agent_plan: str
    agent_status: str
    execution_log: List[dict]
    errors: List[str]

    # ── Control Flow ─────────────────────────
    next_step: str
    full_pipeline_requested: bool
    requires_user_input: bool
    user_approval_needed: bool
    response_text: str
