from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from governed_mcp_agent.sessions import resolve_session

from governed_mcp_agent.audit import write_audit_event
from governed_mcp_agent.policy import evaluate_policy
from governed_mcp_agent.registry import discover_tools


mcp = FastMCP("dynamic-governed-mcp-harness")


def make_mcp_tool(tool_module):
    """
    Wrap a discovered tool with:
    - session resolution
    - trusted identity injection
    - schema validation
    - policy check
    - audit logging
    """

    def wrapped_tool(session_id: str, input_data: dict) -> dict:
        session_context = resolve_session(session_id)

        if not session_context.get("approved"):
            result = {
                "status": "blocked",
                "tool": tool_module.TOOL_NAME,
                "reason": session_context.get("reason", "Session not approved."),
            }

            write_audit_event(
                tool=tool_module.TOOL_NAME,
                caller="unknown",
                request={
                    "session_id": session_id,
                    "input_data": input_data,
                },
                policy_decision={
                    "decision": "deny",
                    "reason": result["reason"],
                },
                result=result,
            )

            return result

        request_data = {
            **input_data,
            "caller": session_context["principal_id"],
            "actor_id": session_context["actor_id"],
            "actor_type": session_context["actor_type"],
            "roles": session_context["roles"],
            "session_id": session_context["session_id"],
        }

        try:
            validated = tool_module.INPUT_SCHEMA(**request_data)
            request = validated.model_dump()

        except ValidationError as e:
            result = {
                "status": "rejected",
                "tool": tool_module.TOOL_NAME,
                "reason": "Input validation failed.",
                "errors": e.errors(),
            }

            write_audit_event(
                tool=tool_module.TOOL_NAME,
                caller=session_context["principal_id"],
                request=request_data,
                policy_decision={
                    "decision": "deny",
                    "reason": "Schema validation failed.",
                },
                result=result,
            )

            return result

        policy_decision = evaluate_policy(tool_module.TOOL_NAME, request)

        if policy_decision["decision"] == "deny":
            result = {
                "status": "blocked",
                "tool": tool_module.TOOL_NAME,
                "decision": "deny",
                "reason": policy_decision["reason"],
            }

            write_audit_event(
                tool=tool_module.TOOL_NAME,
                caller=request.get("caller", "unknown"),
                request=request,
                policy_decision=policy_decision,
                result=result,
            )

            return result

        if policy_decision["decision"] == "review_required":
            result = {
                "status": "approval_required",
                "tool": tool_module.TOOL_NAME,
                "decision": "review_required",
                "reason": policy_decision["reason"],
                "next_step": "Route to human approval before execution.",
            }

            write_audit_event(
                tool=tool_module.TOOL_NAME,
                caller=request.get("caller", "unknown"),
                request=request,
                policy_decision=policy_decision,
                result=result,
            )

            return result

        result = tool_module.run(request)

        write_audit_event(
            tool=tool_module.TOOL_NAME,
            caller=request.get("caller", "unknown"),
            request=request,
            policy_decision=policy_decision,
            result=result,
        )

        return result

    wrapped_tool.__name__ = tool_module.TOOL_NAME
    wrapped_tool.__doc__ = tool_module.TOOL_DESCRIPTION

    return wrapped_tool


for tool in discover_tools():
    wrapped = make_mcp_tool(tool)

    mcp.tool(name=tool.TOOL_NAME)(wrapped)


@mcp.resource("policy://default")
def default_policy() -> str:
    return """
Default MCP Harness Policy:

1. Tools are discovered dynamically from the tools folder.
2. Every tool must define its own input schema.
3. The harness resolves the session before execution.
4. The harness injects trusted identity context.
5. The harness validates all tool input before execution.
6. The harness applies policy before execution.
7. The harness writes an audit event for every request.
8. Local model tools are advisory only unless explicitly promoted.
"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
