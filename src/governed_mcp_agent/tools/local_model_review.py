from typing import List
from pydantic import BaseModel, Field

from governed_mcp_agent.local_model import call_local_model


TOOL_NAME = "local_model_review"
TOOL_DESCRIPTION = "Use a local model to review a system action and return advisory feedback."


class LocalModelReviewInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    roles: List[str] = []
    session_id: str = Field(min_length=3, max_length=120)

    system_name: str = Field(min_length=3, max_length=120)
    environment: str = Field(pattern="^(dev|staging|prod)$")
    requested_action: str = Field(min_length=5, max_length=500)
    contains_sensitive_data: bool = False
    model: str = "qwen3:8b"


INPUT_SCHEMA = LocalModelReviewInput


def run(input_data: dict) -> dict:
    prompt = f"""
You are reviewing a requested infrastructure/security action.

Principal:
{input_data["caller"]}

Actor:
{input_data["actor_id"]} ({input_data["actor_type"]})

System:
{input_data["system_name"]}

Environment:
{input_data["environment"]}

Requested action:
{input_data["requested_action"]}

Contains sensitive data:
{input_data["contains_sensitive_data"]}

Return a concise review with:
1. risk level
2. main concern
3. suggested control
4. whether human approval is needed

Do not approve execution. Only provide advisory review.
"""

    model_response = call_local_model(
        prompt=prompt,
        model=input_data.get("model", "qwen3:8b"),
    )

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "principal": input_data["caller"],
        "actor_id": input_data["actor_id"],
        "actor_type": input_data["actor_type"],
        "system_name": input_data["system_name"],
        "environment": input_data["environment"],
        "model": input_data.get("model", "qwen3:8b"),
        "review": model_response,
    }
