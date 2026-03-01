"""LangGraph workflow — wires all agents into a state graph."""

import structlog
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import DigitalFTEState

logger = structlog.get_logger()

# Global checkpointer for in-memory persistence
checkpointer = MemorySaver()

def build_workflow() -> StateGraph:
    """Build the LangGraph state machine for Digital FTE.

    The workflow routes through the supervisor, which decides
    which specialized agent to invoke next based on the state.
    """

    async def supervisor_node(state: DigitalFTEState) -> dict:
        """Supervisor decides what to do next based on state."""
        user_msg = state.get("user_message", "")
        parsed_cv = state.get("parsed_cv")
        raw_cv_path = state.get("raw_cv_path")
        queue = state.get("automation_queue", [])
        current_work = state.get("current_work_item")
        waiting = state.get("waiting_for_user", False)
        full_pipe = state.get("full_pipeline_requested", False)

        # 0. Check for autonomous pipeline request
        if full_pipe and queue:
            from app.orchestration.pipeline_controller import ApplicationPipelineController
            # Note: We need a DB session. In LangGraph nodes, we usually don't have direct access 
            # to the session unless it's in the state or we use a dependency.
            # For now, we'll assume the session can be retrieved or we'll need to pass it in initial_state.
            # I will modify process_chat_message to inject it or use a global-ish helper if needed.
            # Better: use the AsyncSessionLocal to get a fresh session if not provided.
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                controller = ApplicationPipelineController(db)
                state = await controller.run_full_pipeline(state)
                # If we are waiting for user, do NOT clear the flag as we need to resume
                if not state.get("waiting_for_user"):
                    return {**state, "full_pipeline_requested": False, "next_step": "end"}
                return {**state, "next_step": "end"} # Return to end to pause execution turn

        # 1. Parse CV if missing
        if user_msg and not parsed_cv:
            if raw_cv_path:
                return {"next_step": "parse_cv", "current_agent": "supervisor"}
            else:
                return {"next_step": "end", "current_agent": "supervisor", 
                        "response_text": "I noticed you haven't uploaded a CV yet. Please upload it in the Data Sources tab so I can analyze it for you!"}
        
        # 2. If we have a queue, process next item
        if queue and not current_work:
            next_item = queue[0]
            remaining_queue = queue[1:]
            return {
                "current_work_item": next_item,
                "automation_queue": remaining_queue,
                "next_step": "tailor_cv",
                "current_agent": "supervisor"
            }

        # 3. If no work and message suggests search, find jobs
        if not current_work and ("find" in user_msg.lower() or "apply" in user_msg.lower() or "top" in user_msg.lower()):
            return {"next_step": "find_jobs", "current_agent": "supervisor"}

        # 4. Handle sequential steps for current work item
        if current_work:
            job_id = current_work.get("id")
            approvals = state.get("user_approvals", {})
            job_approved = approvals.get(job_id, {}).get("approved") if job_id else False

            # Check for approval via chat
            if waiting and user_msg and not job_approved:
                is_approval = any(w in user_msg.lower() for w in ["yes", "approve", "send", "proceed", "go ahead", "ok", "confirm"])
                if is_approval:
                    new_approvals = approvals.copy()
                    new_approvals[job_id] = {"approved": True}
                    return {
                        "user_approvals": new_approvals,
                        "waiting_for_user": False,
                        "next_step": "generate_pdf",
                        "current_agent": "supervisor",
                        "response_text": "Great! Approved. Generating final documents..."
                    }
                
                # If not approved, treat as an edit request
                return {
                    "next_step": "editor_node",
                    "current_agent": "supervisor",
                    "response_text": "I hear you. Making those changes now..."
                }

            if not state.get("draft_cv"):
                return {"next_step": "tailor_cv", "current_agent": "supervisor"}
            if not state.get("hr_contacts"):
                return {"next_step": "find_hr", "current_agent": "supervisor"}
            if not state.get("draft_email"):
                return {"next_step": "draft_email", "current_agent": "supervisor"}
            if not job_approved:
                return {"next_step": "human_approval", "current_agent": "supervisor"}
            if not state.get("tailored_cv_pdf_path"):
                 return {"next_step": "generate_pdf", "current_agent": "supervisor"}
            
            # If everything is ready and approved, send it
            return {"next_step": "send_email", "current_agent": "supervisor"}

        return {"next_step": "end", "current_agent": "supervisor",
                "response_text": state.get("response_text", "") or "All tasks completed. I'm watching for replies!"}

    async def editor_node(state: DigitalFTEState) -> dict:
        """Process user edits to CV, Cover Letter, or Email."""
        from app.core.llm_router import get_llm
        
        user_msg = state.get("user_message", "")
        draft_cv = state.get("draft_cv", {})
        draft_email = state.get("draft_email", {})
        draft_cl = state.get("draft_cover_letter", "")
        
        llm = get_llm(task="content_editor")
        
        prompt = f"""You are a professional editor. The user wants to change their application materials.
        
        User Request: "{user_msg}"
        
        Current Email Subject: {draft_email.get('email_subject')}
        Current Email Body: {draft_email.get('email_body')}
        Current Cover Letter: {draft_cl[:500]}...
        
        Analyze the request.
        1. If they want to change the email, rewrite the email subject/body.
        2. If they want to change the cover letter, rewrite the cover letter.
        3. If they want to change the CV, return a specific instruction key.
        
        Return JSON:
        {{
            "updated_email": {{ "email_subject": "...", "email_body": "..." }} (or null if no change),
            "updated_cover_letter": "..." (or null if no change),
            "response_message": "Brief confirmation of what was changed."
        }}
        """
        
        try:
            resp = await llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, 'content') else str(resp)
            import json
            updates = json.loads(content.strip().replace("```json", "").replace("```", ""))
            
            new_state = {"current_agent": "editor_node", "waiting_for_user": False} # Reset waiting flag to trigger approval again
            
            if updates.get("updated_email"):
                new_state["draft_email"] = updates["updated_email"]
            if updates.get("updated_cover_letter"):
                new_state["draft_cover_letter"] = updates["updated_cover_letter"]
                
            new_state["response_text"] = updates.get("response_message", "Updates made.")
            
            # Clear approval status if any to force re-review
            job_id = state.get("current_work_item", {}).get("id")
            if job_id:
                approvals = state.get("user_approvals", {}).copy()
                if job_id in approvals:
                    del approvals[job_id]
                new_state["user_approvals"] = approvals
            
            return new_state
            
        except Exception as e:
            return {
                "current_agent": "editor_node",
                "response_text": f"Sorry, I couldn't apply those edits. Error: {str(e)}"
            }

    async def cv_parser_node(state: DigitalFTEState) -> dict:
        """Parse uploaded CV."""
        from app.agents.cv_parser import parse_cv_file
        cv_path = state.get("raw_cv_path", "")
        if cv_path:
            file_type = "pdf" if cv_path.endswith(".pdf") else "docx"
            parsed = await parse_cv_file(cv_path, file_type)
            return {"parsed_cv": parsed, "current_agent": "cv_parser"}
        return {"current_agent": "cv_parser"}

    async def job_hunter_node(state: DigitalFTEState) -> dict:
        """Search for jobs and populate automation queue."""
        from app.agents.job_hunter import search_jobs
        user_msg = state.get("user_message", "")
        # Extract location/industry if possible, else defaults
        query = user_msg # Simple pass-through for now
        cv_data = state.get("parsed_cv")
        jobs = await search_jobs(query=query, cv_data=cv_data, limit=5)
        
        response = f"🔍 Found **{len(jobs)} target companies**.\n"
        response += "\n".join([f"- {j['company']} ({j['title']}) - {j.get('location', 'Remote')}" for j in jobs])
        response += "\n\n🚀 Starting the application cycle for the first one..."
        
        # Populate the automation queue so supervisor can loop through them
        return {
            "jobs_found": jobs,
            "automation_queue": jobs,
            "current_work_item": None,
            "response_text": response,
            "current_agent": "job_hunter"
        }

    async def email_drafter_node(state: DigitalFTEState) -> dict:
        """Draft the application email."""
        from app.agents.email_sender import compose_application_email
        
        job = state.get("current_work_item")
        cv_data = state.get("parsed_cv", {})
        hr_contacts = state.get("hr_contacts", [])
        hr_contact = hr_contacts[0] if hr_contacts else {}
        cover_letter = state.get("draft_cover_letter")
        
        email_draft = await compose_application_email(job, cv_data, hr_contact, cover_letter)
        
        msg = f"\n✅ **Email Drafted**: Subject: {email_draft.get('email_subject')}"
        
        return {
            "draft_email": email_draft,
            "response_text": state.get("response_text", "") + msg,
            "current_agent": "email_drafter"
        }

    async def cv_tailor_node(state: DigitalFTEState) -> dict:
        """Tailor CV for the current job in the queue."""
        from app.agents.cv_tailor import tailor_cv_for_job
        parsed_cv = state.get("parsed_cv", {})
        job = state.get("current_work_item")
        
        if not job:
            return {"current_agent": "cv_tailor"}
            
        result = await tailor_cv_for_job(parsed_cv, job)
        msg = f"\n\n✅ **CV Tailored** for {job.get('company')}. Match score: {result.get('match_score', 0)}%."
        
        return {
            "draft_cv": result.get("tailored_cv"),
            "draft_cover_letter": result.get("cover_letter"),
            "response_text": state.get("response_text", "") + msg,
            "current_agent": "cv_tailor"
        }

    async def hr_finder_node(state: DigitalFTEState) -> dict:
        """Find HR contact for the current job."""
        from app.agents.hr_finder import find_hr_contact
        job = state.get("current_work_item")
        
        if not job:
            return {"current_agent": "hr_finder"}
            
        contact = await find_hr_contact(
            job.get("company", ""),
            job.get("title", ""),
            user_id=state.get("user_id", "unknown"),
        )
        msg = f"\n✅ **Recruiter Found**: {contact.get('name', 'HR Team')} ({contact.get('email')})"
        
        return {
            "hr_contacts": [contact], # Keep as list for compatibility
            "response_text": state.get("response_text", "") + msg,
            "current_agent": "hr_finder"
        }


    async def interview_prep_node(state: DigitalFTEState) -> dict:
        """Generate interview prep."""
        from app.agents.interview_prep import generate_interview_prep
        jobs = state.get("selected_jobs") or state.get("jobs_found", [])
        preps = []
        for job in jobs[:1]:
            prep = await generate_interview_prep(
                job.get("title", ""), job.get("company", ""), job.get("description", "")
            )
            preps.append(prep)
        return {"interview_prep_data": preps, "current_agent": "interview_prep"}

    async def human_approval_node(state: DigitalFTEState) -> dict:
        """Pause execution and wait for user to approve/edit generated materials."""
        job = state.get("current_work_item", {})
        email = state.get("draft_email", {})
        cover = state.get("draft_cover_letter", "")
        
        msg = f"\n\n### 📥 Ready for Review: {job.get('company')}\n"
        msg += f"**Subject:** {email.get('email_subject')}\n\n"
        msg += f"**Email Body:**\n{email.get('email_body')}\n\n"
        msg += f"**Cover Letter Preview:**\n{cover[:200]}...\n\n"
        msg += "I've prepared the application. Type **'Approve'**, **'Yes'** or **'Send'** to proceed, or provide feedback to edit."
        
        return {
            "waiting_for_user": True, 
            "response_text": state.get("response_text", "") + msg,
            "current_agent": "human_approval"
        }

    async def pdf_generator_node(state: DigitalFTEState) -> dict:
        """Generate PDF from tailored CV data."""
        from app.agents.doc_generator import generate_cv_pdf
        tailored_data = state.get("draft_cv") or state.get("tailored_cvs", [{}])[0]
        pdf_path = await generate_cv_pdf(tailored_data)
        return {"tailored_cv_pdf_path": pdf_path, "current_agent": "doc_generator"}

    async def email_sender_node(state: DigitalFTEState) -> dict:
        """Compose and send emails with PDF attachment and clear state for next item."""
        from app.agents.email_sender import send_via_gmail
        
        job = state.get("current_work_item", {})
        email_draft = state.get("draft_email", {})
        pdf_path = state.get("tailored_cv_pdf_path")
        hr_contacts = state.get("hr_contacts", [])
        
        # In a real app, we'd get tokens from DB using user_id
        # For now, we assume the environment or a mock handles it
        # await send_via_gmail(user_tokens={}, to_email=hr_contacts[0]['email'], ...)
        
        return {
            "current_work_item": None,
            "draft_cv": None,
            "draft_cover_letter": None,
            "draft_email": None,
            "hr_contacts": [],
            "tailored_cv_pdf_path": None,
            "waiting_for_user": False,
            "current_agent": "email_sender",
            "response_text": state.get("response_text", "") + f"\n\n🚀 **Application Sent** for {job.get('company')}! I'm now watching for replies..."
        }

    def route_from_supervisor(state: DigitalFTEState) -> str:
        """Route based on supervisor's decision."""
        next_step = state.get("next_step", "end")
        routing = {
            "parse_cv": "cv_parser",
            "find_jobs": "job_hunter",
            "tailor_cv": "cv_tailor",
            "find_hr": "hr_finder",
            "draft_email": "email_drafter",
            "human_approval": "human_approval",
            "generate_pdf": "pdf_generator",
            "send_email": "email_sender",
            "prep_interview": "interview_prep",
            "editor_node": "editor_node",
            "end": END,
        }
        return routing.get(next_step, END)

    def route_after_approval(state: DigitalFTEState) -> str:
        """Check if user approved or if we need to end this turn."""
        approvals = state.get("user_approvals", {})
        job_id = state.get("current_work_item", {}).get("id")
        if job_id and approvals.get(job_id, {}).get("approved"):
            return "supervisor" # Loop back to supervisor to trigger next step (generate_pdf -> send_email)
        # Return END to pause execution and wait for user input
        return END
    
    def route_after_edit(state: DigitalFTEState) -> str:
        """After edit, loop back to supervisor to check state and likely re-trigger human_approval."""
        return "supervisor"

    def route_after_send(state: DigitalFTEState) -> str:
        """Check if there are more jobs in the queue to process."""
        queue = state.get("automation_queue", [])
        if queue:
            return "supervisor"
        return END

    # Build the graph
    workflow = StateGraph(DigitalFTEState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("cv_parser", cv_parser_node)
    workflow.add_node("job_hunter", job_hunter_node)
    workflow.add_node("cv_tailor", cv_tailor_node)
    workflow.add_node("hr_finder", hr_finder_node)
    workflow.add_node("email_drafter", email_drafter_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("editor_node", editor_node)
    workflow.add_node("pdf_generator", pdf_generator_node)
    workflow.add_node("email_sender", email_sender_node)
    workflow.add_node("interview_prep", interview_prep_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges("supervisor", route_from_supervisor)

    # Human approval logic
    workflow.add_conditional_edges("human_approval", route_after_approval)
    
    # Editor logic
    workflow.add_edge("editor_node", "supervisor")
    
    # PDF to Email (Changed: PDF generator now reports to supervisor to decide next step which is send_email)
    workflow.add_edge("pdf_generator", "supervisor")

    # Email sender logic
    workflow.add_conditional_edges("email_sender", route_after_send)

    # All other agents report back to supervisor
    for node in ["cv_parser", "job_hunter", "cv_tailor", "hr_finder", "email_drafter", "interview_prep"]:
        workflow.add_edge(node, "supervisor")

    return workflow


# Compile the workflow
try:
    digital_fte_graph = build_workflow().compile(checkpointer=checkpointer)
except Exception:
    digital_fte_graph = None
