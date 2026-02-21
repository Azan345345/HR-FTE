"""
Digital FTE - Document Generator Agent
Generates static HTML files from JSON data representing CVs/Preps for quick download.
"""
import time
import structlog
import uuid
import os

from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.config import settings

logger = structlog.get_logger()

# Template for simple HTML material dump
MATERIAL_TEMPLATE = \"\"\"
<!DOCTYPE html>
<html>
<head>
<title>Prep Material</title>
<style>
    body {{ font-family: sans-serif; padding: 20px; color: #333; }}
    h1 {{ color: #4f46e5; }}
    .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; }}
    .q {{ font-weight: bold; }}
    .a {{ margin-top: 5px; color: #059669; }}
</style>
</head>
<body>
    <h1>Interview Preparation Material</h1>
    <div class="section">
        <h2>Technical Questions</h2>
        {technical_html}
    </div>
    <div class="section">
        <h2>Behavioral Questions</h2>
        {behavioral_html}
    </div>
</body>
</html>
\"\"\"

async def doc_generator_node(state: DigitalFTEState) -> dict:
    """
    Document Production Specialist — Creates downloadable HTML formats 
    from generated JSON states (like Interview Prep details).
    """
    session_id = state.get("user_id", "unknown")
    
    interview_data = state.get("interview_prep_data", [])
    if not interview_data:
        return {
            "current_agent": "doc_generator",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No prep data available to generate documents for."],
        }

    start_time = time.time()
    
    try:
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="doc_generator",
            plan="Generate static HTML study materials from prep context.",
            estimated_time=2.0,
        )

        for idx, prep in enumerate(interview_data):
            # Parse questions
            tech_qs = prep.get("technical_questions", [])
            beh_qs = prep.get("behavioral_questions", [])
            
            t_html = "".join([f"<p class='q'>Q: {q.get('question', '')}</p><p class='a'>A: {q.get('ideal_answer', '')}</p>" for q in tech_qs])
            b_html = "".join([f"<p class='q'>Q: {q.get('question', '')}</p><p class='a'>A: {q.get('ideal_answer', '')}</p>" for q in beh_qs])

            final_html = MATERIAL_TEMPLATE.format(technical_html=t_html or "<p>None</p>", behavioral_html=b_html or "<p>None</p>")
            
            # Save file
            file_name = f"prep_{uuid.uuid4().hex[:8]}.html"
            file_path = os.path.join(settings.GENERATED_DIR, file_name)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_html)
                
            prep["study_material_path"] = file_name
        
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="doc_generator",
            result_summary=f"Generated {len(interview_data)} document artifacts.",
            time_taken=elapsed,
        )

        return {
            "interview_prep_data": interview_data,
            "current_agent": "doc_generator",
            "agent_status": "completed",
            "agent_plan": "Document generation complete",
        }

    except Exception as e:
        logger.error("doc_generator_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="doc_generator",
            error_message=str(e),
        )
        return {
            "current_agent": "doc_generator",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
