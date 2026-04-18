from datetime import datetime, timezone

from pydantic import BaseModel, Field

from governed_mcp_agent.game_state import load_encounters
from governed_mcp_agent.game_state import next_identifier
from governed_mcp_agent.game_state import save_encounters


TOOL_NAME = "create_encounter"
TOOL_DESCRIPTION = "Create a simple deterministic encounter scaffold."


ENCOUNTER_TEMPLATES = {
    ("combat", "easy"): {
        "name": "Goblin Road Ambush",
        "enemies": [{"name": "Goblin Scout", "hp": 7, "armor": 12}],
        "objective": "Survive the ambush or scare off the goblin.",
    },
    ("combat", "medium"): {
        "name": "Watchtower Skirmish",
        "enemies": [
            {"name": "Cursed Guard", "hp": 12, "armor": 13},
            {"name": "Lantern Wisp", "hp": 6, "armor": 11},
        ],
        "objective": "Defeat the defenders and reach the lower stair.",
    },
    ("exploration", "easy"): {
        "name": "Collapsed Hallway Search",
        "enemies": [],
        "objective": "Search the debris without triggering the unstable floor.",
    },
    ("social", "easy"): {
        "name": "Shaken Villager Rumor",
        "enemies": [],
        "objective": "Win the villager's trust and learn what waits below.",
    },
}


class CreateEncounterInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    encounter_type: str = Field(min_length=3, max_length=40)
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    theme: str = Field(min_length=3, max_length=120)


INPUT_SCHEMA = CreateEncounterInput


def run(input_data: dict) -> dict:
    encounters = load_encounters()
    encounter_id = next_identifier("enc", encounters)
    template = ENCOUNTER_TEMPLATES.get(
        (input_data["encounter_type"].lower(), input_data["difficulty"].lower()),
        {
            "name": f"{input_data['theme'].title()} Challenge",
            "enemies": [],
            "objective": f"Overcome the {input_data['theme']} challenge.",
        },
    )

    encounter = {
        "encounter_id": encounter_id,
        "encounter_type": input_data["encounter_type"],
        "difficulty": input_data["difficulty"],
        "theme": input_data["theme"],
        "name": template["name"],
        "enemies": template["enemies"],
        "objective": template["objective"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    encounters[encounter_id] = encounter
    save_encounters(encounters)

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        **encounter,
    }
