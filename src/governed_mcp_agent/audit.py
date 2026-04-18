import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "tool_calls.jsonl"


def hash_input(data: dict) -> str:
    normalized = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def write_audit_event(
    *,
    tool: str,
    caller: str,
    request: dict,
    policy_decision: dict,
    result: dict,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "caller": caller,
        "input_hash": hash_input(request),
        "environment": request.get("environment"),
        "policy_decision": policy_decision.get("decision"),
        "policy_reason": policy_decision.get("reason"),
        "result_status": result.get("status"),
    }

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")