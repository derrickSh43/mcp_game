from typing import List

from pydantic import BaseModel, Field

from governed_mcp_agent.game_state import load_characters
from governed_mcp_agent.game_state import save_characters


TOOL_NAME = "update_character_state"
TOOL_DESCRIPTION = "Update character HP, inventory, location, quest, or conditions."


class UpdateCharacterStateInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    character_id: str = Field(min_length=5, max_length=40)
    hp_delta: int = Field(default=0, ge=-50, le=50)
    add_items: List[str] = []
    remove_items: List[str] = []
    add_conditions: List[str] = []
    remove_conditions: List[str] = []
    location: str | None = Field(default=None, max_length=120)
    active_quest: str | None = Field(default=None, max_length=200)


INPUT_SCHEMA = UpdateCharacterStateInput


def run(input_data: dict) -> dict:
    characters = load_characters()
    character = characters.get(input_data["character_id"])

    if not character:
        return {
            "status": "not_found",
            "tool": TOOL_NAME,
            "reason": f"Unknown character_id: {input_data['character_id']}",
        }

    max_hp = int(character.get("max_hp", character.get("hp", 0)))
    current_hp = int(character.get("hp", 0))
    next_hp = max(0, min(max_hp, current_hp + input_data["hp_delta"]))
    character["hp"] = next_hp

    inventory = list(character.get("inventory", []))

    for item in input_data["add_items"]:
        if item not in inventory:
            inventory.append(item)

    for item in input_data["remove_items"]:
        if item in inventory:
            inventory.remove(item)

    character["inventory"] = inventory

    conditions = list(character.get("conditions", []))

    for condition in input_data["add_conditions"]:
        if condition not in conditions:
            conditions.append(condition)

    for condition in input_data["remove_conditions"]:
        if condition in conditions:
            conditions.remove(condition)

    character["conditions"] = conditions

    if input_data["location"] is not None:
        character["location"] = input_data["location"]

    if input_data["active_quest"] is not None:
        character["active_quest"] = input_data["active_quest"]

    characters[input_data["character_id"]] = character
    save_characters(characters)

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        **character,
    }
