import asyncio
import json
import os
import re
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


SYSTEM_INSTRUCTIONS = """
You are a local governed workflow agent.

You may request tool calls, but you do not execute tools yourself.
You must return ONLY valid JSON.

Available tools:

1. security_review
Input:
{
  "system_name": string,
  "environment": "dev" | "staging" | "prod",
  "requested_action": string,
  "contains_sensitive_data": boolean
}

2. local_model_review
Input:
{
  "system_name": string,
  "environment": "dev" | "staging" | "prod",
  "requested_action": string,
  "contains_sensitive_data": boolean,
  "model": string
}

3. create_controlled_artifact
Input:
{
  "title": string,
  "artifact_type": "runbook" | "report" | "task_note" | "security_note",
  "summary": string,
  "body": string
}

Rules:
- First, perform a security_review.
- Then, perform a local_model_review.
- Then, create a controlled artifact summarizing the review.
- Do not request execution of production changes.
- Do not request secret export.
- Do not approve your own work.
- Stop after the artifact is created.

Return one of these JSON objects:

To call a tool:
{
  "action": "call_tool",
  "tool_name": "tool name here",
  "input_data": {}
}

To finish:
{
  "action": "finish",
  "reason": "short reason"
}
"""
async def run_agent_workflow(objective: str, session_id: str = "sess_agent_local") -> dict:
    history: list[dict[str, Any]] = []

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

            for step in range(1, 6):
                prompt = build_agent_prompt(objective, history)

                model_output = call_local_model(prompt=prompt, model=MODEL)
                decision = extract_json(model_output)

                if decision.get("action") == "finish":
                    return {
                        "status": "completed",
                        "reason": decision.get("reason"),
                        "history": history,
                    }

                if decision.get("action") != "call_tool":
                    return {
                        "status": "failed",
                        "reason": "Unknown agent action.",
                        "decision": decision,
                        "history": history,
                    }

                tool_name = decision["tool_name"]
                input_data = decision["input_data"]

                payload = {
                    "session_id": session_id,
                    "input_data": input_data,
                }

                tool_result = await session.call_tool(tool_name, payload)

                history.append(
                    {
                        "step": step,
                        "tool_name": tool_name,
                        "input_data": input_data,
                        "tool_result": str(tool_result),
                    }
                )

            return {
                "status": "stopped",
                "reason": "Max steps reached.",
                "history": history,
            }

def extract_json(text: str) -> dict[str, Any]:
    """
    Pull the first JSON object out of a model response.
    Qwen may sometimes wrap output in text, so this keeps the demo resilient.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON object found in model response:\n{text}")

    return json.loads(match.group(0))


def build_agent_prompt(objective: str, history: list[dict[str, Any]]) -> str:
    return f"""
{SYSTEM_INSTRUCTIONS}

Objective:
{objective}

History:
{json.dumps(history, indent=2)}

Decide the next step.
Return only JSON.
"""


async def call_mcp_tool(session: ClientSession, tool_name: str, input_data: dict) -> Any:
    payload = {
        "session_id": SESSION_ID,
        "input_data": input_data,
    }

    result = await session.call_tool(tool_name, payload)
    return result


async def main():
    objective = """
Review a proposed production AI gateway routing change.
Create a controlled artifact summarizing the risks, concerns, and required approval steps.
"""

    history: list[dict[str, Any]] = []

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

            for step in range(1, 6):
                prompt = build_agent_prompt(objective, history)

                model_output = call_local_model(prompt=prompt, model=MODEL)
                decision = extract_json(model_output)

                print(f"\n=== Agent Step {step} ===")
                print(json.dumps(decision, indent=2))

                if decision.get("action") == "finish":
                    print("\nAgent finished:")
                    print(decision.get("reason"))
                    break

                if decision.get("action") != "call_tool":
                    raise ValueError(f"Unknown agent action: {decision}")

                tool_name = decision["tool_name"]
                input_data = decision["input_data"]

                tool_result = await call_mcp_tool(
                    session=session,
                    tool_name=tool_name,
                    input_data=input_data,
                )

                print("\nTool result:")
                print(tool_result)

                history.append(
                    {
                        "step": step,
                        "tool_name": tool_name,
                        "input_data": input_data,
                        "tool_result": str(tool_result),
                    }
                )


if __name__ == "__main__":
    objective = """
Review a proposed production AI gateway routing change.
Create a controlled artifact summarizing the risks, concerns, and required approval steps.
"""

    result = asyncio.run(run_agent_workflow(objective))
    print(result)
