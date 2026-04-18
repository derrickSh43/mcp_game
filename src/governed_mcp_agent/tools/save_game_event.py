import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from governed_mcp_agent.game_state import GAME_LOG_DIR


TOOL_NAME = "save_game_event"
TOOL_DESCRIPTION = "Append a structured game event to the session game log."


class SaveGameEventInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    event_type: str = Field(min_length=3, max_length=60)
    character: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=3, max_length=400)
    roll_total: int | None = None
    outcome: str | None = Field(default=None, max_length=80)
    details: str | None = Field(default=None, max_length=1000)


INPUT_SCHEMA = SaveGameEventInput


def run(input_data: dict) -> dict:
    GAME_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = Path(GAME_LOG_DIR / f"{input_data['session_id']}.jsonl")

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": input_data["event_type"],
        "character": input_data["character"],
        "action": input_data["action"],
        "roll_total": input_data.get("roll_total"),
        "outcome": input_data.get("outcome"),
        "details": input_data.get("details"),
        "caller": input_data["caller"],
        "actor_id": input_data["actor_id"],
        "actor_type": input_data["actor_type"],
        "session_id": input_data["session_id"],
    }

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "log_path": str(log_path.resolve()),
        "event": event,
    }
