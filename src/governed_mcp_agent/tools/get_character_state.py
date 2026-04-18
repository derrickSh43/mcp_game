from pydantic import BaseModel, Field

from governed_mcp_agent.game_state import load_characters


TOOL_NAME = "get_character_state"
TOOL_DESCRIPTION = "Read the current state of a player character."


class GetCharacterStateInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    character_id: str = Field(min_length=5, max_length=40)


INPUT_SCHEMA = GetCharacterStateInput


def run(input_data: dict) -> dict:
    characters = load_characters()
    character = characters.get(input_data["character_id"])

    if not character:
        return {
            "status": "not_found",
            "tool": TOOL_NAME,
            "reason": f"Unknown character_id: {input_data['character_id']}",
        }

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        **character,
    }
