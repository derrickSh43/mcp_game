import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from governed_mcp_agent.local_model import call_local_model


SESSION_ID = "sess_agent_local"
MODEL = "qwen3:8b"
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
GAME_TITLE = "The Lantern Below"


SCENE_GUIDE = {
    "Road to the Watchtower": "A wind-cut path climbs toward an abandoned watchtower with a swollen oak door and cold green light leaking from cracks in the stone.",
    "Main Hall": "Broken crates, old rations, and damp banners fill the main hall. A cracked stair and a locked hatch suggest a way below.",
    "Basement Stairs": "The stairs into the cellar are narrow, slick, and half-rotted. Every step threatens to give way.",
    "Lantern Cellar": "A chamber beneath the tower glows with green lantern light. A cursed guard lingers near the source, half memory and half malice.",
    "Watchtower Exit": "The tower groans behind you as you retreat into the night with proof of what burned below.",
}


def lower_text(text: str) -> str:
    return text.strip().lower()


def has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def stat_modifier(score: int) -> int:
    return (score - 10) // 2


def format_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def build_roll_notation(character_state: dict, action_type: str) -> str:
    stats = character_state.get("stats", {})

    if action_type in {"stealth", "finesse_attack", "reflex"}:
        modifier = stat_modifier(int(stats.get("dexterity", 10)))
    elif action_type in {"investigation", "knowledge"}:
        modifier = stat_modifier(int(stats.get("intelligence", 10)))
    elif action_type in {"persuasion", "presence"}:
        modifier = stat_modifier(int(stats.get("charisma", 10)))
    elif action_type in {"endure", "fortitude"}:
        modifier = stat_modifier(int(stats.get("constitution", 10)))
    else:
        modifier = stat_modifier(int(stats.get("strength", 10)))

    return f"1d20{format_modifier(modifier)}"


def summarize_sheet(character_state: dict) -> str:
    stats = character_state.get("stats", {})
    inventory = ", ".join(character_state.get("inventory", [])) or "nothing"
    conditions = ", ".join(character_state.get("conditions", [])) or "none"
    return (
        f'{character_state["name"]} the {character_state["class_name"]}\n'
        f'HP: {character_state["hp"]}/{character_state.get("max_hp", character_state["hp"])}\n'
        f'Location: {character_state.get("location", "unknown")}\n'
        f'Quest: {character_state.get("active_quest", "none")}\n'
        f'Conditions: {conditions}\n'
        f'Inventory: {inventory}\n'
        f'Stats: STR {stats.get("strength", 10)}, DEX {stats.get("dexterity", 10)}, CON {stats.get("constitution", 10)}, '
        f'INT {stats.get("intelligence", 10)}, WIS {stats.get("wisdom", 10)}, CHA {stats.get("charisma", 10)}'
    )


def fallback_narration(location: str, facts: list[str], outcome: str) -> str:
    scene = SCENE_GUIDE.get(location, location)
    joined_facts = " ".join(facts)
    return f"{scene} {outcome} {joined_facts}".strip()


def narrate(location: str, character_state: dict, user_message: str, facts: list[str], outcome: str) -> str:
    prompt = f"""
You are the game master for a grounded fantasy adventure called "{GAME_TITLE}".

Write a short second-person narration for the player.
Do not invent mechanics or facts beyond what is provided.
Keep it to 3 short paragraphs maximum.

Player character:
- Name: {character_state.get("name")}
- Class: {character_state.get("class_name")}
- Location: {location}

Current scene:
{SCENE_GUIDE.get(location, location)}

Player action:
{user_message}

Facts that must remain true:
{chr(10).join(f"- {fact}" for fact in facts)}

Mechanical outcome:
{outcome}
"""

    result = call_local_model(prompt=prompt, model=MODEL).strip()

    if not result or result.startswith("LOCAL_MODEL_ERROR"):
        return fallback_narration(location, facts, outcome)

    return result


async def call_mcp_tool(session: ClientSession, tool_name: str, input_data: dict) -> Any:
    payload = {
        "session_id": SESSION_ID,
        "input_data": input_data,
    }
    result = await session.call_tool(tool_name, payload)

    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent

    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if not text:
            continue

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Unable to parse MCP tool result for {tool_name}: {result}")


async def fetch_character_state(session: ClientSession, character_id: str) -> dict:
    return await call_mcp_tool(
        session,
        "get_character_state",
        {"character_id": character_id},
    )


async def save_event(
    session: ClientSession,
    character_name: str,
    action: str,
    outcome: str,
    event_type: str = "player_action",
    roll_total: int | None = None,
    details: str | None = None,
) -> None:
    await call_mcp_tool(
        session,
        "save_game_event",
        {
            "event_type": event_type,
            "character": character_name,
            "action": action,
            "roll_total": roll_total,
            "outcome": outcome,
            "details": details,
        },
    )


async def run_check(
    session: ClientSession,
    character_state: dict,
    user_message: str,
    action_type: str,
    difficulty_class: int,
) -> tuple[dict, dict]:
    roll_result = await call_mcp_tool(
        session,
        "roll_dice",
        {"roll": build_roll_notation(character_state, action_type)},
    )
    resolve_result = await call_mcp_tool(
        session,
        "resolve_action",
        {
            "action_type": action_type,
            "difficulty_class": difficulty_class,
            "roll_total": roll_result["total"],
        },
    )

    await save_event(
        session,
        character_state["name"],
        action=user_message,
        outcome=resolve_result["outcome"],
        roll_total=roll_result["total"],
        details=f"{action_type} check vs DC {difficulty_class}",
    )

    return roll_result, resolve_result


async def ensure_intro_event(session: ClientSession, character_state: dict) -> None:
    await save_event(
        session,
        character_state["name"],
        action="Entered the road to the old watchtower",
        outcome="began_adventure",
        event_type="story_start",
        details="Opening scene for The Lantern Below",
    )


async def handle_scene_action(
    session: ClientSession,
    character_state: dict,
    user_message: str,
    encounter_created: bool,
) -> tuple[str, bool]:
    text = lower_text(user_message)
    location = character_state.get("location", "Road to the Watchtower")
    inventory = character_state.get("inventory", [])
    facts: list[str] = []

    if text in {"help", "commands"}:
        return (
            "Try natural actions like: look around, open the tower door, search the hall, descend the stairs, sneak past the guard, talk to the guard, or attack.",
            encounter_created,
        )

    if has_any(text, ["sheet", "stats", "character"]):
        return summarize_sheet(character_state), encounter_created

    if has_any(text, ["inventory", "items", "bag"]):
        items = ", ".join(inventory) or "nothing"
        return f"You are carrying: {items}.", encounter_created

    if has_any(text, ["look", "examine", "inspect"]) and not has_any(text, ["search", "find"]):
        return SCENE_GUIDE.get(location, location), encounter_created

    if location == "Road to the Watchtower":
        if has_any(text, ["door", "enter", "open", "tower", "pick", "force"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "force", 11)

            if resolve_result["success"]:
                updated = await call_mcp_tool(
                    session,
                    "update_character_state",
                    {
                        "character_id": character_state["character_id"],
                        "location": "Main Hall",
                    },
                )
                facts.extend(
                    [
                        f"You rolled {roll_result['total']} against DC 11.",
                        "The watchtower door gives way.",
                        "Your location is now Main Hall.",
                    ]
                )
                return (
                    narrate(
                        "Main Hall",
                        updated,
                        user_message,
                        facts,
                        "Success. The way into the tower is open.",
                    ),
                    encounter_created,
                )

            facts.extend(
                [
                    f"You rolled {roll_result['total']} against DC 11.",
                    "The old door holds.",
                ]
            )
            return (
                narrate(
                    location,
                    character_state,
                    user_message,
                    facts,
                    "Failure. The swollen oak door refuses to open.",
                ),
                encounter_created,
            )

        return (
            narrate(
                location,
                character_state,
                user_message,
                ["The tower still stands ahead of you.", "The door is the obvious obstacle."],
                "Nothing changes yet. You still need a way inside.",
            ),
            encounter_created,
        )

    if location == "Main Hall":
        if has_any(text, ["search", "find", "investigate", "supplies", "crate"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "investigation", 10)

            if resolve_result["success"] and "rusted key" not in inventory:
                updated = await call_mcp_tool(
                    session,
                    "update_character_state",
                    {
                        "character_id": character_state["character_id"],
                        "add_items": ["rusted key"],
                    },
                )
                facts.extend(
                    [
                        f"You rolled {roll_result['total']} against DC 10.",
                        "You found a rusted key hidden in the old supply crates.",
                    ]
                )
                return (
                    narrate(
                        location,
                        updated,
                        user_message,
                        facts,
                        "Success. You uncover a useful key and learn the hall hides a way down.",
                    ),
                    encounter_created,
                )

            if resolve_result["success"]:
                return (
                    "You search the hall carefully. The crates are empty now, but the locked hatch in the floor still draws your eye.",
                    encounter_created,
                )

            return (
                f"You turn over damp crates and torn canvas, but the hall yields nothing useful. Your roll of {roll_result['total']} was short of the DC 10 search.",
                encounter_created,
            )

        if has_any(text, ["down", "basement", "hatch", "stairs", "below", "descend"]):
            if "rusted key" not in inventory:
                return (
                    "The hatch is locked tight. Somewhere in this hall there must be a key or another way to force it.",
                    encounter_created,
                )

            updated = await call_mcp_tool(
                session,
                "update_character_state",
                {
                    "character_id": character_state["character_id"],
                    "location": "Basement Stairs",
                    "remove_items": [],
                },
            )
            facts.extend(
                [
                    "The rusted key turns in the hatch.",
                    "You open the way to the basement stairs.",
                ]
            )
            return (
                narrate(
                    "Basement Stairs",
                    updated,
                    user_message,
                    facts,
                    "The floor hatch opens and the cold green light grows stronger below.",
                ),
                encounter_created,
            )

        return (
            "The main hall answers with creaking beams and stale dust. The crates invite a search, and the locked hatch promises the way below.",
            encounter_created,
        )

    if location == "Basement Stairs":
        if has_any(text, ["down", "descend", "careful", "stairs", "climb"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "reflex", 12)

            update_payload = {
                "character_id": character_state["character_id"],
                "location": "Lantern Cellar",
            }

            outcome_text = "Success. You reach the cellar with your footing intact."
            if not resolve_result["success"]:
                update_payload["hp_delta"] = -2
                update_payload["add_conditions"] = ["bruised"]
                outcome_text = "Failure. The rotten steps collapse under you before you recover in the cellar."

            updated = await call_mcp_tool(session, "update_character_state", update_payload)

            if not encounter_created:
                await call_mcp_tool(
                    session,
                    "create_encounter",
                    {
                        "encounter_type": "combat",
                        "difficulty": "medium",
                        "theme": "cursed guard in green lantern cellar",
                    },
                )
                encounter_created = True

            facts.extend(
                [
                    f"You rolled {roll_result['total']} against DC 12.",
                    "You reach the Lantern Cellar.",
                    "A cursed guard waits near the green lantern.",
                ]
            )
            return (
                narrate("Lantern Cellar", updated, user_message, facts, outcome_text),
                encounter_created,
            )

        return (
            "The stairs groan beneath the hatch. Going down will take care and nerve.",
            encounter_created,
        )

    if location == "Lantern Cellar":
        if has_any(text, ["talk", "speak", "parley", "ask", "call out"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "persuasion", 12)

            if resolve_result["success"]:
                updated = await call_mcp_tool(
                    session,
                    "update_character_state",
                    {
                        "character_id": character_state["character_id"],
                        "location": "Watchtower Exit",
                        "add_items": ["green lantern shard"],
                        "active_quest": "The Lantern Below - completed",
                        "remove_conditions": ["bruised"],
                    },
                )
                facts.extend(
                    [
                        f"You rolled {roll_result['total']} against DC 12.",
                        "The guard yields the lantern's proof and lets you leave.",
                        "Your quest is complete.",
                    ]
                )
                return (
                    narrate(
                        "Watchtower Exit",
                        updated,
                        user_message,
                        facts,
                        "Success. The spirit relents and the watchtower finally releases its secret.",
                    ),
                    encounter_created,
                )

            return (
                f"Your words stir the dead guard's memory, but not enough. Its grip tightens on the lantern. Your roll of {roll_result['total']} fell short of DC 12.",
                encounter_created,
            )

        if has_any(text, ["sneak", "hide", "slip", "steal"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "stealth", 13)

            if resolve_result["success"]:
                updated = await call_mcp_tool(
                    session,
                    "update_character_state",
                    {
                        "character_id": character_state["character_id"],
                        "location": "Watchtower Exit",
                        "add_items": ["green lantern shard"],
                        "active_quest": "The Lantern Below - completed",
                    },
                )
                facts.extend(
                    [
                        f"You rolled {roll_result['total']} against DC 13.",
                        "You slip past the guard and take proof of the lantern.",
                        "Your quest is complete.",
                    ]
                )
                return (
                    narrate(
                        "Watchtower Exit",
                        updated,
                        user_message,
                        facts,
                        "Success. You move like a shadow and escape with the proof the villagers wanted.",
                    ),
                    encounter_created,
                )

            updated = await call_mcp_tool(
                session,
                "update_character_state",
                {
                    "character_id": character_state["character_id"],
                    "hp_delta": -3,
                    "add_conditions": ["shaken"],
                },
            )
            facts.extend(
                [
                    f"You rolled {roll_result['total']} against DC 13.",
                    "The cursed guard catches your movement and strikes.",
                    "You lose 3 HP.",
                ]
            )
            return (
                narrate(
                    "Lantern Cellar",
                    updated,
                    user_message,
                    facts,
                    "Failure. The guard turns on you before you can reach the lantern.",
                ),
                encounter_created,
            )

        if has_any(text, ["attack", "fight", "strike", "stab", "shoot", "charge"]):
            roll_result, resolve_result = await run_check(session, character_state, user_message, "finesse_attack", 12)

            if resolve_result["success"]:
                updated = await call_mcp_tool(
                    session,
                    "update_character_state",
                    {
                        "character_id": character_state["character_id"],
                        "location": "Watchtower Exit",
                        "add_items": ["green lantern shard"],
                        "active_quest": "The Lantern Below - completed",
                    },
                )
                facts.extend(
                    [
                        f"You rolled {roll_result['total']} against DC 12.",
                        "Your blow breaks the curse binding the guard.",
                        "You claim the lantern shard and escape.",
                    ]
                )
                return (
                    narrate(
                        "Watchtower Exit",
                        updated,
                        user_message,
                        facts,
                        "Success. The cursed guard falls and the chamber's green light finally weakens.",
                    ),
                    encounter_created,
                )

            updated = await call_mcp_tool(
                session,
                "update_character_state",
                {
                    "character_id": character_state["character_id"],
                    "hp_delta": -3,
                },
            )
            facts.extend(
                [
                    f"You rolled {roll_result['total']} against DC 12.",
                    "The cursed guard batters you back.",
                    "You lose 3 HP.",
                ]
            )
            return (
                narrate(
                    "Lantern Cellar",
                    updated,
                    user_message,
                    facts,
                    "Failure. Your attack misses its moment and the dead sentinel answers with force.",
                ),
                encounter_created,
            )

        return (
            "The lantern's green fire wavers over the cursed guard. You can speak to it, try to slip past it, or fight for the proof you came to claim.",
            encounter_created,
        )

    return (
        "The tower is quiet for a moment. Describe what you want to do next.",
        encounter_created,
    )


async def main():
    onboarding_step = "name"
    pending_name = ""
    pending_class = ""
    active_character_id = ""
    encounter_created = False

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "governed_mcp_agent.server"],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(SRC_ROOT),
        },
    )

    print(f"\n{GAME_TITLE}")
    print("A short DnD-style adventure in a haunted watchtower.")
    print("Type 'exit' to quit.\n")
    print("GM: Villagers say a green lantern still burns beneath an abandoned watchtower.")
    print("GM: Before we begin, what is your character's name?")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            while True:
                user_message = input("You: ").strip()

                if lower_text(user_message) in {"exit", "quit"}:
                    print("GM: The watchtower fades back into the mist.")
                    break

                if not user_message:
                    continue

                if not active_character_id:
                    if onboarding_step == "name":
                        pending_name = user_message
                        onboarding_step = "class"
                        print("GM: Choose a class: Fighter, Rogue, Wizard, or Cleric.")
                        continue

                    if onboarding_step == "class":
                        pending_class = user_message.title()
                        onboarding_step = "background"
                        print("GM: Give me a short background for your character.")
                        continue

                    create_result = await call_mcp_tool(
                        session,
                        "create_character",
                        {
                            "name": pending_name,
                            "class_name": pending_class,
                            "background": user_message,
                        },
                    )

                    active_character_id = create_result["character_id"]
                    await ensure_intro_event(session, create_result)

                    print("GM: Your character is ready.\n")
                    print(summarize_sheet(create_result))
                    print()
                    print(
                        narrate(
                            create_result["location"],
                            create_result,
                            "Begin the adventure",
                            [
                                f'You are {create_result["name"]}, a {create_result["class_name"]}.',
                                "You have arrived on the road to the old watchtower.",
                                "The villagers want proof of the green lantern below.",
                            ],
                            "The adventure begins now.",
                        )
                    )
                    continue

                character_state = await fetch_character_state(session, active_character_id)
                response, encounter_created = await handle_scene_action(
                    session,
                    character_state,
                    user_message,
                    encounter_created,
                )
                print(f"GM: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
