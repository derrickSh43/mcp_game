from typing import List
from pydantic import BaseModel, Field


TOOL_NAME = "security_review"
TOOL_DESCRIPTION = "Review a requested system action against basic security expectations."


class SecurityReviewInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    roles: List[str] = []
    session_id: str = Field(min_length=3, max_length=120)

    system_name: str = Field(min_length=3, max_length=120)
    environment: str = Field(pattern="^(dev|staging|prod)$")
    requested_action: str = Field(min_length=5, max_length=200)
    contains_sensitive_data: bool = False


INPUT_SCHEMA = SecurityReviewInput


def run(input_data: dict) -> dict:
    requested_action = input_data["requested_action"].lower()
    environment = input_data["environment"]
    contains_sensitive_data = input_data["contains_sensitive_data"]

    concerns = []

    if contains_sensitive_data:
        concerns.append("Sensitive data is involved.")

    if environment == "prod":
        concerns.append("Production environment requires stronger control.")

    if "change" in requested_action:
        concerns.append("Change action detected.")

    if not concerns:
        concerns.append("No major concern detected.")

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "principal": input_data["caller"],
        "actor_id": input_data["actor_id"],
        "actor_type": input_data["actor_type"],
        "system_name": input_data["system_name"],
        "environment": environment,
        "concerns": concerns,
    }