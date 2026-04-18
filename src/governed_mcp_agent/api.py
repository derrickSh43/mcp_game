from pydantic import BaseModel, Field
from fastapi import FastAPI

from governed_mcp_agent.agent_runner import run_agent_workflow


app = FastAPI(title="Governed MCP Agent Intake")


class AgentRequest(BaseModel):
    session_id: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=10, max_length=2000)


@app.post("/agent/run")
async def run_agent(request: AgentRequest):
    result = await run_agent_workflow(
        objective=request.objective,
        session_id=request.session_id,
    )

    return result
