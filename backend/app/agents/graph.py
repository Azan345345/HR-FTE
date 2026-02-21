"""
Digital FTE - LangGraph Workflow Definition
Wires all agent nodes into a StateGraph.
"""

from langgraph.graph import StateGraph, END

from app.agents.state import DigitalFTEState
from app.agents.supervisor import supervisor_node
from app.agents.cv_parser import cv_parser_node
from app.agents.job_hunter import job_hunter_node
from app.agents.cv_tailor import cv_tailor_node
from app.agents.hr_finder import hr_finder_node
from app.agents.email_sender import email_sender_node
from app.agents.interview_prep import interview_prep_node
from app.agents.doc_generator import doc_generator_node


def _route_from_supervisor(state: DigitalFTEState) -> str:
    """Routing function — supervisor decides the next agent."""
    return state.get("next_step", "end")


def build_graph() -> StateGraph:
    """Construct and compile the Digital FTE agent graph."""

    workflow = StateGraph(DigitalFTEState)

    # ── Add nodes ────────────────────────────────────
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("cv_parser", cv_parser_node)
    workflow.add_node("job_hunter", job_hunter_node)
    workflow.add_node("cv_tailor", cv_tailor_node)
    workflow.add_node("hr_finder", hr_finder_node)
    workflow.add_node("email_sender", email_sender_node)
    workflow.add_node("interview_prep", interview_prep_node)
    workflow.add_node("doc_generator", doc_generator_node)

    # ── Entry point ──────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Conditional edges from supervisor ────────────
    workflow.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "parse_cv": "cv_parser",
            "find_jobs": "job_hunter",
            "tailor_cv": "cv_tailor",
            "find_hr": "hr_finder",
            "send_email": "email_sender",
            "prep_interview": "interview_prep",
            "generate_doc": "doc_generator",
            "end": END,
        },
    )

    # ── Agent → Supervisor (report back) ─────────────
    for agent_name in [
        "cv_parser", "job_hunter", "cv_tailor",
        "hr_finder", "email_sender", "interview_prep", "doc_generator",
    ]:
        workflow.add_edge(agent_name, "supervisor")

    return workflow.compile()


# Compiled graph singleton (lazy import-safe)
graph = build_graph()
