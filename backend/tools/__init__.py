"""Tool-use support for LLM Council Stage 1."""

from .registry import TOOL_REGISTRY, register_tool, get_enabled_tools, execute_tool
from . import builtin  # noqa: F401 — registers built-in tools on import
