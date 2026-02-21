"""External connectors for LLM Council — inject data as context before queries."""

from .registry import CONNECTOR_REGISTRY, register_connector, run_connector
from . import builtin  # noqa: F401 — registers built-in connectors on import
