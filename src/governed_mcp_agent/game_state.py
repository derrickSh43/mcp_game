import json
from pathlib import Path


DATA_DIR = Path("game_data")
CHARACTERS_FILE = DATA_DIR / "characters.json"
ENCOUNTERS_FILE = DATA_DIR / "encounters.json"
GAME_LOG_DIR = Path("game_logs")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_file(path: Path, payload) -> None:
    _ensure_parent(path)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_characters() -> dict:
    return load_json_file(CHARACTERS_FILE, {})


def save_characters(characters: dict) -> None:
    save_json_file(CHARACTERS_FILE, characters)


def load_encounters() -> dict:
    return load_json_file(ENCOUNTERS_FILE, {})


def save_encounters(encounters: dict) -> None:
    save_json_file(ENCOUNTERS_FILE, encounters)


def next_identifier(prefix: str, existing: dict) -> str:
    if not existing:
        return f"{prefix}_001"

    numbers = []

    for key in existing:
        if not key.startswith(f"{prefix}_"):
            continue

        try:
            numbers.append(int(key.split("_", 1)[1]))
        except ValueError:
            continue

    next_number = max(numbers, default=0) + 1
    return f"{prefix}_{next_number:03d}"
