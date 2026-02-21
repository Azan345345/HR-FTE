"""
Digital FTE - LangGraph State Schema
Defines the shared state for the multi-agent workflow.
"""

from typing import TypedDict, List, Optional


class DigitalFTEState(TypedDict, total=False):
    """State flowing through the LangGraph agent pipeline."""

    # ── User Input ───────────────────────────────────
    user_id: str
    raw_cv_path: str
    user_message: str

    # ── Parsed CV ────────────────────────────────────
    parsed_cv: dict
    cv_embeddings: list

    # ── Job Search ───────────────────────────────────
    search_query: str
    target_role: str
    target_location: str
    jobs_found: List[dict]
    selected_jobs: List[dict]

    # ── Tailored CVs ────────────────────────────────
    tailored_cvs: List[dict]  # {job_id, tailored_cv_data, pdf_path, match_score}

    # ── HR Contacts ──────────────────────────────────
    hr_contacts: List[dict]  # {job_id, hr_name, hr_email, confidence}

    # ── Applications ─────────────────────────────────
    applications_sent: List[dict]  # {job_id, email_sent, timestamp, status}
    pending_approvals: List[dict]

    # ── Interview Prep ───────────────────────────────
    interview_prep_data: List[dict]

    # ── Agent Tracking ───────────────────────────────
    current_agent: str
    agent_plan: str
    agent_status: str
    execution_log: List[dict]
    errors: List[str]

    # ── Control Flow ─────────────────────────────────
    next_step: str
    requires_user_input: bool
    user_approval_needed: bool
