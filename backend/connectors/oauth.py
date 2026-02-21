"""OAuth flow infrastructure for external connectors.

This module provides the scaffolding for OAuth-based connectors
(Google Drive, GitHub, Slack, etc.). The actual OAuth connectors
will be implemented after the simple connectors are stable.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

TOKEN_DIR = "data/connector_tokens"


def _ensure_token_dir():
    Path(TOKEN_DIR).mkdir(parents=True, exist_ok=True)


def save_token(connector_name: str, token_data: Dict[str, Any]):
    """Save an OAuth token for a connector."""
    _ensure_token_dir()
    path = os.path.join(TOKEN_DIR, f"{connector_name}.json")
    with open(path, "w") as f:
        json.dump(token_data, f, indent=2)


def load_token(connector_name: str) -> Optional[Dict[str, Any]]:
    """Load a saved OAuth token for a connector."""
    path = os.path.join(TOKEN_DIR, f"{connector_name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def delete_token(connector_name: str):
    """Delete a saved OAuth token."""
    path = os.path.join(TOKEN_DIR, f"{connector_name}.json")
    if os.path.exists(path):
        os.remove(path)
