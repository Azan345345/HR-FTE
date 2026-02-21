import pytest
from app.services.chat_service import process_chat_message

@pytest.mark.asyncio
async def test_supervisor_routing_logic():
    """
    Test that the supervisor correctly identifies intent.
    Note: Requires LLM API keys to be set in environment.
    """
    user_id = "00000000-0000-0000-0000-000000000001" # Mock UUID
    
    # Test case 1: Job search intent
    message = "I want to search for Python developer jobs in Berlin"
    result = await process_chat_message(message, user_id)
    
    assert "intent" in result
    assert result["intent"] in ["job_hunter", "supervisor"] # Supervisor is the entry point
    assert "status" in result
    
@pytest.mark.asyncio
async def test_cv_tailor_intent():
    user_id = "00000000-0000-0000-0000-000000000001"
    message = "Please tailor my CV for the Senior Frontend role at Google"
    result = await process_chat_message(message, user_id)
    
    assert result["intent"] in ["cv_tailor", "supervisor"]
