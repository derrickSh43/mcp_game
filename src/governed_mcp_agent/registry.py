import importlib
import pkgutil
from pathlib import Path


TOOLS_PACKAGE = "governed_mcp_agent.tools"


def discover_tools():
    """
    Dynamically discover tools inside the tools/ folder.

    Each tool file must expose:
      TOOL_NAME
      TOOL_DESCRIPTION
      INPUT_SCHEMA
      run(input_data: dict) -> dict
    """

    discovered = []

    tools_path = Path(__file__).parent / "tools"

    for module_info in pkgutil.iter_modules([str(tools_path)]):
        module_name = module_info.name

        if module_name.startswith("_"):
            continue

        module = importlib.import_module(f"{TOOLS_PACKAGE}.{module_name}")

        required_attrs = [
            "TOOL_NAME",
            "TOOL_DESCRIPTION",
            "INPUT_SCHEMA",
            "run",
        ]

        missing = [attr for attr in required_attrs if not hasattr(module, attr)]

        if missing:
            raise RuntimeError(
                f"Tool module {module_name} is missing required fields: {missing}"
            )

        discovered.append(module)

    return discovered
