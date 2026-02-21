"""Async storage for conversations — Postgres or JSON files."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import DATA_DIR, DATABASE_URL

USE_POSTGRES = bool(DATABASE_URL)


# ---------------------------------------------------------------------------
# JSON helpers (unchanged logic, just wrapped in async)
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def _conversation_path(conversation_id: str) -> str:
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


# ---------------------------------------------------------------------------
# Public API — every function is async, dual-mode
# ---------------------------------------------------------------------------

async def create_conversation(conversation_id: str) -> Dict[str, Any]:
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        row = await pool.fetchrow(
            "INSERT INTO conversations (id) VALUES ($1) RETURNING id, title, created_at",
            conversation_id,
        )
        return {
            "id": row["id"],
            "created_at": row["created_at"].isoformat(),
            "title": row["title"],
            "messages": [],
        }

    _ensure_data_dir()
    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": [],
    }
    with open(_conversation_path(conversation_id), "w") as f:
        json.dump(conversation, f, indent=2)
    return conversation


async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT id, title, created_at FROM conversations WHERE id = $1",
            conversation_id,
        )
        if row is None:
            return None
        messages = await pool.fetch(
            "SELECT role, content, stage1, stage2, stage3, stage4, run_config "
            "FROM messages WHERE conversation_id = $1 ORDER BY position",
            conversation_id,
        )
        msg_list = []
        for m in messages:
            if m["role"] == "user":
                msg_list.append({"role": "user", "content": m["content"]})
            else:
                msg = {
                    "role": "assistant",
                    "stage1": json.loads(m["stage1"]) if m["stage1"] else None,
                    "stage2": json.loads(m["stage2"]) if m["stage2"] else None,
                    "stage3": json.loads(m["stage3"]) if m["stage3"] else None,
                }
                if m["stage4"]:
                    msg["stage4"] = json.loads(m["stage4"])
                if m["run_config"]:
                    msg["run_config"] = json.loads(m["run_config"])
                msg_list.append(msg)
        return {
            "id": row["id"],
            "created_at": row["created_at"].isoformat(),
            "title": row["title"],
            "messages": msg_list,
        }

    path = _conversation_path(conversation_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


async def list_conversations() -> List[Dict[str, Any]]:
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        rows = await pool.fetch(
            "SELECT c.id, c.title, c.created_at, "
            "  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
            "FROM conversations c ORDER BY c.created_at DESC",
        )
        return [
            {
                "id": r["id"],
                "created_at": r["created_at"].isoformat(),
                "title": r["title"],
                "message_count": r["message_count"],
            }
            for r in rows
        ]

    _ensure_data_dir()
    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            path = os.path.join(DATA_DIR, filename)
            with open(path, "r") as f:
                data = json.load(f)
                conversations.append(
                    {
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "title": data.get("title", "New Conversation"),
                        "message_count": len(data["messages"]),
                    }
                )
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations


async def add_user_message(conversation_id: str, content: str):
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        pos = await pool.fetchval(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM messages WHERE conversation_id = $1",
            conversation_id,
        )
        await pool.execute(
            "INSERT INTO messages (conversation_id, position, role, content) VALUES ($1, $2, 'user', $3)",
            conversation_id, pos, content,
        )
        return

    conversation = await get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    conversation["messages"].append({"role": "user", "content": content})
    _save_json(conversation)


async def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    stage4: Optional[Dict[str, Any]] = None,
    run_config: Optional[Dict[str, Any]] = None,
):
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        pos = await pool.fetchval(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM messages WHERE conversation_id = $1",
            conversation_id,
        )
        await pool.execute(
            "INSERT INTO messages (conversation_id, position, role, stage1, stage2, stage3, stage4, run_config) "
            "VALUES ($1, $2, 'assistant', $3, $4, $5, $6, $7)",
            conversation_id,
            pos,
            json.dumps(stage1),
            json.dumps(stage2),
            json.dumps(stage3),
            json.dumps(stage4) if stage4 is not None else None,
            json.dumps(run_config) if run_config is not None else None,
        )
        return

    conversation = await get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    message = {"role": "assistant", "stage1": stage1, "stage2": stage2, "stage3": stage3}
    if stage4 is not None:
        message["stage4"] = stage4
    if run_config is not None:
        message["run_config"] = run_config
    conversation["messages"].append(message)
    _save_json(conversation)


async def update_conversation_title(conversation_id: str, title: str):
    if USE_POSTGRES:
        from .db import get_pool
        pool = await get_pool()
        await pool.execute(
            "UPDATE conversations SET title = $1 WHERE id = $2",
            title, conversation_id,
        )
        return

    conversation = await get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    conversation["title"] = title
    _save_json(conversation)


# ---------------------------------------------------------------------------
# JSON-only helper
# ---------------------------------------------------------------------------

def _save_json(conversation: Dict[str, Any]):
    _ensure_data_dir()
    with open(_conversation_path(conversation["id"]), "w") as f:
        json.dump(conversation, f, indent=2)
