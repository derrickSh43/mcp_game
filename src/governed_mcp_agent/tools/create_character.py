from datetime import datetime, timezone

from pydantic import BaseModel, Field

from governed_mcp_agent.game_state import load_characters
from governed_mcp_agent.game_state import next_identifier
from governed_mcp_agent.game_state import save_characters


TOOL_NAME = "create_character"
TOOL_DESCRIPTION = "Create a simple player character for the game."


CLASS_TEMPLATES = {
    "fighter": {
        "hp": 12,
        "stats": {
            "strength": 14,
            "dexterity": 11,
            "constitution": 13,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
        },
        "inventory": ["longsword", "shield", "travel pack"],
    },
    "rogue": {
        "hp": 10,
        "stats": {
            "strength": 10,
            "dexterity": 14,
            "constitution": 12,
            "intelligence": 11,
            "wisdom": 10,
            "charisma": 13,
        },
        "inventory": ["dagger", "torch", "travel cloak"],
    },
    "wizard": {
        "hp": 8,
        "stats": {
            "strength": 8,
            "dexterity": 12,
            "constitution": 10,
            "intelligence": 15,
            "wisdom": 12,
            "charisma": 11,
        },
        "inventory": ["spellbook", "wand", "ink-stained satchel"],
    },
    "cleric": {
        "hp": 11,
        "stats": {
            "strength": 11,
            "dexterity": 10,
            "constitution": 13,
            "intelligence": 10,
            "wisdom": 14,
            "charisma": 12,
        },
        "inventory": ["mace", "holy symbol", "bandages"],
    },
}


class CreateCharacterInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    name: str = Field(min_length=2, max_length=80)
    class_name: str = Field(min_length=3, max_length=40)
    background: str = Field(min_length=5, max_length=300)


INPUT_SCHEMA = CreateCharacterInput


def run(input_data: dict) -> dict:
    characters = load_characters()
    character_id = next_identifier("char", characters)
    class_name = input_data["class_name"].strip()
    class_key = class_name.lower()
    template = CLASS_TEMPLATES.get(class_key, CLASS_TEMPLATES["rogue"])

    character = {
        "character_id": character_id,
        "name": input_data["name"].strip(),
        "class_name": class_name,
        "background": input_data["background"].strip(),
        "hp": template["hp"],
        "max_hp": template["hp"],
        "stats": dict(template["stats"]),
        "inventory": list(template["inventory"]),
        "location": "Road to the Watchtower",
        "active_quest": "The Lantern Below",
        "conditions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    characters[character_id] = character
    save_characters(characters)

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        **character,
    }
