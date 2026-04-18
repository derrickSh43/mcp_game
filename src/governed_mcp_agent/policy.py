def evaluate_policy(tool_name: str, request: dict) -> dict:
    """
    Generic policy layer for all tools.
    Later this can be replaced with OPA.
    """

    environment = request.get("environment")
    requested_action = request.get("requested_action", "").lower()
    contains_sensitive_data = request.get("contains_sensitive_data", False)

    blocked_phrases = [
        "dump secrets",
        "export credentials",
        "delete production",
        "disable logging",
        "bypass approval",
    ]

    roles = request.get("roles", [])
    actor_type = request.get("actor_type")

    for phrase in blocked_phrases:
        if phrase in requested_action:
            return {
                "decision": "deny",
                "reason": f"Blocked phrase detected: {phrase}",
            }

    if environment == "prod" and contains_sensitive_data:
        return {
            "decision": "review_required",
            "reason": "Production sensitive-data request requires human approval.",
        }

    if tool_name in {
        "local_model_review",
        "roll_dice",
        "create_character",
        "get_character_state",
        "save_game_event",
        "resolve_action",
        "create_encounter",
    }:
        return {
            "decision": "allow",
            "reason": "Read-only or bounded game action allowed.",
        }

    if environment == "prod" and "change" in requested_action:
        return {
            "decision": "review_required",
            "reason": "Production change requires human approval.",
        }
    if tool_name == "update_character_state":
        if abs(int(request.get("hp_delta", 0))) > 50:
            return {
                "decision": "deny",
                "reason": "HP delta exceeds allowed bounds.",
            }

        return {
            "decision": "allow",
            "reason": "Bounded character state update allowed.",
        }

    if tool_name == "create_controlled_artifact":
        allowed_roles = ["developer", "security-reviewer", "advisory-reviewer", "lab-user"]

        if not any(role in roles for role in allowed_roles):
            return {
                "decision": "deny",
                "reason": "Caller does not have a role allowed to create artifacts.",
            }

    if tool_name == "create_controlled_artifact" and actor_type == "agent" and request.get("artifact_type") not in ["report", "task_note", "security_note"]:
        return {
            "decision": "deny",
            "reason": "Agents may only create report, task_note, or security_note artifacts.",
        }

    return {
        "decision": "allow",
        "reason": "Request passed policy checks.",
    }
