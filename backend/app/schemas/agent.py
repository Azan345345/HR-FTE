"""Digital FTE - Agent Status Schemas"""
from typing import Optional, List
from pydantic import BaseModel


class AgentStatusRead(BaseModel):
    agent_name: str
    status: str  # idle, processing, completed, error
    plan: Optional[str] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_action: Optional[str] = None
    elapsed_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None


class WorkflowStatus(BaseModel):
    active_node: Optional[str] = None
    completed_nodes: List[str] = []
    pending_nodes: List[str] = []
