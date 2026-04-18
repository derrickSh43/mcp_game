from pydantic import BaseModel, Field


TOOL_NAME = "resolve_action"
TOOL_DESCRIPTION = "Resolve an action by comparing a rolled total against a difficulty class."


class ResolveActionInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    action_type: str = Field(min_length=3, max_length=60)
    difficulty_class: int = Field(ge=1, le=40)
    roll_total: int = Field(ge=0, le=1000)


INPUT_SCHEMA = ResolveActionInput


def run(input_data: dict) -> dict:
    total = input_data["roll_total"]
    difficulty_class = input_data["difficulty_class"]
    margin = total - difficulty_class
    success = total >= difficulty_class

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "action_type": input_data["action_type"],
        "success": success,
        "total": total,
        "difficulty_class": difficulty_class,
        "margin": margin,
        "outcome": "success" if success else "failure",
    }
