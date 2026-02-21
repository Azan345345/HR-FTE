"""
Digital FTE - CV Parser Agent
Parses uploaded CV (PDF/DOCX), extracts structured data via LLM,
creates embeddings and stores in ChromaDB.
"""

import json
import time
import structlog

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DigitalFTEState
from app.agents.prompts.cv_parser import CV_PARSER_SYSTEM_PROMPT, CV_PARSER_USER_PROMPT
from app.agents.tools.cv_tools import read_cv_file, store_cv_embeddings
from app.core.llm_router import llm_router
from app.core.event_bus import event_bus
from app.schemas.cv import ParsedCVData

logger = structlog.get_logger()


def _parse_llm_json(content: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    text = content.strip()
    # Strip markdown json code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last line (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


async def cv_parser_node(state: DigitalFTEState) -> dict:
    """
    CV Intelligence Analyst — Main parsing pipeline:
    1. Extract raw text from file
    2. Send to LLM with structured prompt
    3. Parse JSON response
    4. Generate & store embeddings in ChromaDB
    5. Emit WebSocket events
    """
    session_id = state.get("user_id", "unknown")
    cv_path = state.get("raw_cv_path", "")
    user_id = state.get("user_id", "")

    if not cv_path:
        return {
            "current_agent": "cv_parser",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No CV path provided"],
        }

    start_time = time.time()

    try:
        # ── Step 1: Emit started event ─────────────
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="cv_parser",
            plan="Extract text → Parse with LLM → Generate embeddings → Store",
            estimated_time=15.0,
        )

        # ── Step 2: Extract text ───────────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="cv_parser",
            step=1, total_steps=4,
            current_action="Extracting text from file",
        )

        # Determine file type from path
        file_type = "pdf" if cv_path.lower().endswith(".pdf") else "docx"
        raw_text = read_cv_file(cv_path, file_type)
        logger.info("cv_text_extracted", length=len(raw_text))

        # ── Step 3: Parse with LLM ────────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="cv_parser",
            step=2, total_steps=4,
            current_action="Analyzing CV with AI",
            details=f"Sending {len(raw_text)} chars to LLM",
        )

        messages = [
            SystemMessage(content=CV_PARSER_SYSTEM_PROMPT),
            HumanMessage(content=CV_PARSER_USER_PROMPT.format(cv_text=raw_text[:8000])),
        ]

        response = await llm_router.invoke_with_fallback(messages)
        parsed_json = _parse_llm_json(response.content)

        # Validate against schema
        parsed_data = ParsedCVData(**parsed_json)
        logger.info("cv_parsed_successfully", sections=len(parsed_json))

        # ── Step 4: Generate embeddings ────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="cv_parser",
            step=3, total_steps=4,
            current_action="Generating embeddings for semantic matching",
        )

        embedding_id = ""
        try:
            embedding_id = store_cv_embeddings(
                cv_id=state.get("user_id", "unknown"),
                user_id=user_id,
                text=raw_text,
            )
        except Exception as embed_err:
            logger.warning("embedding_failed", error=str(embed_err))

        # ── Step 5: Emit completed ─────────────────
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="cv_parser",
            result_summary=f"Parsed CV: {parsed_data.personal_info.name if parsed_data.personal_info else 'Unknown'}, "
                          f"{len(parsed_data.experience)} experiences, "
                          f"{len(parsed_data.skills.technical) if parsed_data.skills else 0} skills",
            time_taken=elapsed,
        )

        return {
            "parsed_cv": parsed_data.model_dump(),
            "cv_embeddings": [embedding_id] if embedding_id else [],
            "current_agent": "cv_parser",
            "agent_status": "completed",
            "agent_plan": "CV parsed and embeddings stored",
        }

    except json.JSONDecodeError as e:
        logger.error("cv_parse_json_error", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="cv_parser",
            error_message=f"LLM returned invalid JSON: {str(e)}",
            retry_count=0,
            fallback_action="Retrying with different model",
        )
        return {
            "current_agent": "cv_parser",
            "agent_status": "error",
            "errors": state.get("errors", []) + [f"JSON parse error: {str(e)}"],
        }

    except Exception as e:
        logger.error("cv_parser_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="cv_parser",
            error_message=str(e),
        )
        return {
            "current_agent": "cv_parser",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
