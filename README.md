# MCP Game Demo

`mcp_game` is a small Model Context Protocol demo that turns a simple fantasy adventure into an MCP-shaped system.

The point of this project is not just "make a game." The point is to show how MCP can separate:

- agent narration
- deterministic tool execution
- policy enforcement
- audit history

In this repo, the model acts like the game master, but the tools own the facts. That means the model can describe the world, while the MCP server decides what actually changed.

## Why This Is an MCP Demo

This project maps game concepts onto MCP concepts:

- Agent = narrator / game master
- Tools = deterministic game functions
- MCP server = tool host and execution boundary
- Policy layer = what the agent is allowed to change
- Audit log = game history

That is the core design idea: the model can narrate, but it should not invent state changes. State changes go through MCP tools.

## How It Works

The runtime flow is:

1. The chat loop starts in [`src/governed_mcp_agent/agent_chat.py`](src/governed_mcp_agent/agent_chat.py).
2. It launches the MCP server from [`src/governed_mcp_agent/server.py`](src/governed_mcp_agent/server.py).
3. The server discovers tool modules from [`src/governed_mcp_agent/registry.py`](src/governed_mcp_agent/registry.py).
4. Each tool call is wrapped with session resolution, validation, policy checks, and audit logging in [`src/governed_mcp_agent/server.py`](src/governed_mcp_agent/server.py).
5. Sessions are resolved in [`src/governed_mcp_agent/sessions.py`](src/governed_mcp_agent/sessions.py).
6. Policy decisions happen in [`src/governed_mcp_agent/policy.py`](src/governed_mcp_agent/policy.py).
7. Audit records are written by [`src/governed_mcp_agent/audit.py`](src/governed_mcp_agent/audit.py).
8. Game state is stored by [`src/governed_mcp_agent/game_state.py`](src/governed_mcp_agent/game_state.py).

## Important Files

Core MCP and app files:

- [`src/governed_mcp_agent/server.py`](src/governed_mcp_agent/server.py): FastMCP server, tool wrapping, validation, policy, and audit flow.
- [`src/governed_mcp_agent/registry.py`](src/governed_mcp_agent/registry.py): dynamic tool discovery.
- [`src/governed_mcp_agent/policy.py`](src/governed_mcp_agent/policy.py): guardrails for what tool actions are allowed.
- [`src/governed_mcp_agent/audit.py`](src/governed_mcp_agent/audit.py): audit logging for requests.
- [`src/governed_mcp_agent/sessions.py`](src/governed_mcp_agent/sessions.py): approved session identities and roles.
- [`src/governed_mcp_agent/agent_chat.py`](src/governed_mcp_agent/agent_chat.py): playable terminal game loop.
- [`src/governed_mcp_agent/api.py`](src/governed_mcp_agent/api.py): optional API entrypoint.
- [`src/governed_mcp_agent/local_model.py`](src/governed_mcp_agent/local_model.py): local model call helper for narration.
- [`src/governed_mcp_agent/game_state.py`](src/governed_mcp_agent/game_state.py): JSON-backed character, encounter, and game-log storage.

Game tool files:

- [`src/governed_mcp_agent/tools/roll_dice.py`](src/governed_mcp_agent/tools/roll_dice.py): deterministic dice rolling.
- [`src/governed_mcp_agent/tools/create_character.py`](src/governed_mcp_agent/tools/create_character.py): character creation.
- [`src/governed_mcp_agent/tools/get_character_state.py`](src/governed_mcp_agent/tools/get_character_state.py): current character state lookup.
- [`src/governed_mcp_agent/tools/update_character_state.py`](src/governed_mcp_agent/tools/update_character_state.py): state changes for HP, items, conditions, and location.
- [`src/governed_mcp_agent/tools/save_game_event.py`](src/governed_mcp_agent/tools/save_game_event.py): structured game event logging.
- [`src/governed_mcp_agent/tools/resolve_action.py`](src/governed_mcp_agent/tools/resolve_action.py): success/failure resolution from a rolled total.
- [`src/governed_mcp_agent/tools/create_encounter.py`](src/governed_mcp_agent/tools/create_encounter.py): simple encounter scaffolding.

## The Game

The demo adventure is **The Lantern Below**.

Premise:

- Villagers claim a green lantern still burns beneath an abandoned watchtower.
- The player enters the tower to find proof and survive the descent.

Current scene structure:

- Road to the Watchtower
- Main Hall
- Basement Stairs
- Lantern Cellar
- Watchtower Exit

The current game loop is intentionally small. It is meant to demonstrate MCP orchestration clearly, not simulate a full tabletop rules engine.

## Why The Tool Layer Matters

Without tools, an LLM-driven game easily turns into made-up state. With the current MCP shape:

- rolls come from `roll_dice`
- success/failure comes from `resolve_action`
- HP and inventory changes come from `update_character_state`
- character reads come from `get_character_state`
- story history is written through `save_game_event`

That is the main MCP lesson in this repo: the model can improvise text, but tool calls should own the facts.

## Requirements

- Python 3.13 or similar recent Python
- A local environment with the dependencies from [`requirements.txt`](requirements.txt)
- Optional: Ollama running locally if you want model-driven narration from [`src/governed_mcp_agent/local_model.py`](src/governed_mcp_agent/local_model.py)

If Ollama is not available, some narration paths may fall back less gracefully or return local-model errors depending on the path taken.

## Install From GitHub

Clone the repo:

```powershell
git clone https://github.com/derrickSh43/mcp_game.git
cd mcp_game
```
Create a virtual environment:

```powershell
python -m venv .venv
```
Install dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
Set the package path:

```powershell
$env:PYTHONPATH="src"
How To Play
```
From the project root:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m governed_mcp_agent.agent_chat
```
The game will:

Ask for your character name.
Ask for your class.
Ask for a short background.
Create the character through MCP tools.
Start the watchtower adventure.

Useful things to type during play:

look around
open the tower door
search the crates
go down the stairs
talk to the guard
sneak past the guard
attack
inventory
character sheet

Exit with:

exit
Optional API Entry Point

The repo also includes a FastAPI entrypoint:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m uvicorn governed_mcp_agent.api:app --reload --port 8000
```
This is optional. The main playable demo is the terminal chat loop.

Project Goal

This project demonstrates a governed agent pattern in a lightweight, understandable way:

```powershell
user input
  ↓
local model / game master
  ↓
MCP tool request
  ↓
session resolution
  ↓
schema validation
  ↓
policy decision
  ↓
tool execution
  ↓
audit/game log
  ↓
narrated result
```
The model can tell the story, but tools own the facts.
