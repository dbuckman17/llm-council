"""Connector registration and execution."""

from dataclasses import dataclass
from typing import Dict, Any, Callable, Awaitable, Optional


@dataclass
class ConnectorDefinition:
    """Definition of an external connector that injects context before queries."""
    name: str
    description: str
    connector_type: str  # "simple" or "oauth"
    config_schema: Dict[str, Any]  # JSON Schema for config fields
    fetcher: Callable[..., Awaitable[str]]


# Global registry
CONNECTOR_REGISTRY: Dict[str, ConnectorDefinition] = {}


def register_connector(connector: ConnectorDefinition):
    """Register a connector in the global registry."""
    CONNECTOR_REGISTRY[connector.name] = connector


async def run_connector(name: str, config: Dict[str, Any]) -> Optional[str]:
    """
    Execute a connector and return its result text.

    Args:
        name: Connector name
        config: User-provided config values

    Returns:
        Result text to inject as context, or None on failure
    """
    connector = CONNECTOR_REGISTRY.get(name)
    if connector is None:
        print(f"Unknown connector: {name}")
        return None

    try:
        return await connector.fetcher(**config)
    except Exception as e:
        print(f"Connector '{name}' failed: {e}")
        return None
