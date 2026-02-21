"""Tool registration and execution for Stage 1 tool-use."""

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Awaitable, List, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool that models can call during Stage 1."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable[..., Awaitable[str]]


# Global registry
TOOL_REGISTRY: Dict[str, ToolDefinition] = {}


def register_tool(tool: ToolDefinition):
    """Register a tool in the global registry."""
    TOOL_REGISTRY[tool.name] = tool


def get_enabled_tools(names: List[str]) -> List[ToolDefinition]:
    """Get tool definitions for the given names."""
    return [TOOL_REGISTRY[n] for n in names if n in TOOL_REGISTRY]


async def execute_tool(
    name: str,
    args: Dict[str, Any],
    tool_map: Optional[Dict[str, ToolDefinition]] = None,
) -> str:
    """Execute a tool by name with the given arguments."""
    # Prefer the provided tool_map (may be a subset), fall back to global registry
    registry = tool_map if tool_map else TOOL_REGISTRY
    tool = registry.get(name)
    if tool is None:
        return f"Error: Unknown tool '{name}'"

    try:
        result = await tool.handler(**args)
        return str(result) if result is not None else ""
    except Exception as e:
        return f"Error executing tool '{name}': {e}"
