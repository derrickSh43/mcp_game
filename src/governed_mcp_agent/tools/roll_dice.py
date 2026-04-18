import random
import re

from pydantic import BaseModel, Field


TOOL_NAME = "roll_dice"
TOOL_DESCRIPTION = "Roll dice using standard notation such as 1d20, 2d6, or 1d8+3."


ROLL_PATTERN = re.compile(r"^(?P<count>\d+)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$")


class RollDiceInput(BaseModel):
    caller: str = Field(min_length=3, max_length=80)
    actor_id: str = Field(min_length=3, max_length=80)
    actor_type: str = Field(min_length=3, max_length=80)
    session_id: str = Field(min_length=3, max_length=120)

    roll: str = Field(min_length=3, max_length=20)


INPUT_SCHEMA = RollDiceInput


def run(input_data: dict) -> dict:
    match = ROLL_PATTERN.fullmatch(input_data["roll"].strip().lower())

    if not match:
        return {
            "status": "rejected",
            "tool": TOOL_NAME,
            "reason": "Roll must use NdM or NdM+K notation.",
        }

    count = int(match.group("count"))
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or 0)

    if count < 1 or count > 20:
        return {
            "status": "rejected",
            "tool": TOOL_NAME,
            "reason": "Dice count must be between 1 and 20.",
        }

    if sides < 2 or sides > 1000:
        return {
            "status": "rejected",
            "tool": TOOL_NAME,
            "reason": "Die sides must be between 2 and 1000.",
        }

    dice = [random.randint(1, sides) for _ in range(count)]
    total = sum(dice) + modifier

    return {
        "status": "completed",
        "tool": TOOL_NAME,
        "roll": input_data["roll"],
        "dice": dice,
        "modifier": modifier,
        "total": total,
    }
