from typing import List
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel, Field


TOOL_NAME = "create_controlled_artifact"
TOOL_DESCRIPTION = "Create a controlled markdown artifact inside the approved workspace."


WORKSPACE_DIR = Path("workspace").resolve()


class CreateControlledArtifactInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    roles: List[str] = []
    session_id: str = Field(min_length=3, max_length=120)

    title: str = Field(min_length=3, max_length=120)
    artifact_type: str = Field(pattern="^(runbook|report|task_note|security_note)$")
    summary: str = Field(min_length=10, max_length=1000)
    body: str = Field(min_length=10, max_length=5000)


INPUT_SCHEMA = CreateControlledArtifactInput


def safe_filename(title: str) -> str:
    cleaned = title.lower().strip()

    for char in [" ", "/", "\\", ":", "*", "?", "\"", "<", ">", "|"]:
        cleaned = cleaned.replace(char, "-")

    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")

    return cleaned[:80].strip("-") + ".md"


def run(input_data: dict) -> dict:
    WORKSPACE_DIR.mkdir(exist_ok=True)

    filename = safe_filename(input_data["title"])
    output_path = (WORKSPACE_DIR / filename).resolve()

    if not str(output_path).startswith(str(WORKSPACE_DIR)):
        return {
            "status": "blocked",
            "tool": TOOL_NAME,
            "reason": "Resolved file path escaped approved workspace.",
        }

    content = f"""# {input_data["title"]}

**Artifact Type:** {input_data["artifact_type"]}  
**Principal:** {input_data["caller"]}  
**Actor:** {input_data["actor_id"]} ({input_data["actor_type"]})  
**Session:** {input_data["session_id"]}  
**Created At:** {datetime.now(timezone.utc).isoformat()}  

## Summary

{input_data["summary"]}

## Body

{input_data["body"]}
"""

    output_path.write_text(content, encoding="utf-8")

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "artifact_path": str(output_path),
        "artifact_type": input_data["artifact_type"],
        "principal": input_data["caller"],
        "actor_id": input_data["actor_id"],
        "actor_type": input_data["actor_type"],
    }