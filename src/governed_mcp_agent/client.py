import asyncio
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


async def call_tool(session, tool_name, session_id, input_data):
    payload = {
        "session_id": session_id,
        "input_data": input_data,
    }

    result = await session.call_tool(tool_name, payload)

    print("\n==============================")
    print(f"Tool: {tool_name}")
    print("Payload:")
    print(payload)
    print("\nResult:")
    print(result)


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "governed_mcp_agent.server"],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(SRC_ROOT),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("\nAvailable tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Human-operated local client session
            await call_tool(
                session,
                "security_review",
                session_id="sess_derrick_local",
                input_data={
                    "system_name": "rag-control-plane",
                    "environment": "dev",
                    "requested_action": "review new ingestion policy before promotion",
                    "contains_sensitive_data": False,
                },
            )

            # Agent session using local Qwen model
            await call_tool(
                session,
                "local_model_review",
                session_id="sess_agent_local",
                input_data={
                    "system_name": "prod-ai-gateway",
                    "environment": "prod",
                    "requested_action": "review routing change for production inference gateway",
                    "contains_sensitive_data": False,
                    "model": "qwen3:8b",
                },
            )

            await call_tool(
                session,
                "create_controlled_artifact",
                session_id="sess_agent_local",
                input_data={
                    "title": "Production AI Gateway Routing Review",
                    "artifact_type": "report",
                    "summary": "Review of a proposed production routing change for the AI gateway.",
                    "body": """
            The local agent reviewed the proposed production routing change.

            Primary concern:
            A routing mistake could send production traffic to the wrong model backend or degrade latency.

            Suggested control:
            Use a canary rollout, validate traffic behavior, and confirm rollback steps before promotion.

            Approval:
            Human approval should be required before execution.
            """,
                },
            )
if __name__ == "__main__":
    asyncio.run(main())
