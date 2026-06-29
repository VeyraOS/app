from pydantic import BaseModel
from typing import Optional


class AgentCreate(BaseModel):
    name: str
    template: str
    model: str = "claude-sonnet-4-6"
    mission_goal: str = ""


class TaskCreate(BaseModel):
    agent_id: str
    input: str
