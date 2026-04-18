from datetime import datetime, timezone


APPROVED_SESSIONS = {
    "sess_derrick_local": {
        "principal_id": "derrick",
        "actor_id": "manual-client",
        "actor_type": "human-operated-client",
        "roles": ["developer", "security-reviewer"],
        "approved": True,
    },
    "sess_agent_local": {
        "principal_id": "derrick",
        "actor_id": "qwen-local-agent",
        "actor_type": "agent",
        "roles": ["advisory-reviewer"],
        "approved": True,
    },
    "sess_student_lab": {
        "principal_id": "student-lab-user",
        "actor_id": "manual-client",
        "actor_type": "human-operated-client",
        "roles": ["lab-user"],
        "approved": True,
    },
}


def resolve_session(session_id: str) -> dict:
    session = APPROVED_SESSIONS.get(session_id)

    if not session:
        return {
            "approved": False,
            "reason": "Unknown session_id.",
        }

    if not session.get("approved"):
        return {
            "approved": False,
            "reason": "Session is not approved.",
        }

    return {
        **session,
        "session_id": session_id,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }