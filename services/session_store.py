"""
Session Store
=============
Server-side JSON file persistence for wizard sessions.
Saves to data/saved_sessions/ directory.
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "saved_sessions"


class SessionStore:
    """Manages wizard session persistence via JSON files."""

    _instance: Optional['SessionStore'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        logger.info(f"Session store initialized at {SESSIONS_DIR}")

    def save_session(self, session_id: str, state: Dict[str, Any]) -> str:
        """Save a wizard session state to a JSON file."""
        state["saved_at"] = datetime.now().isoformat()
        file_path = SESSIONS_DIR / f"{session_id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Saved session {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            raise

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a saved session from JSON file."""
        file_path = SESSIONS_DIR / f"{session_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all saved sessions, optionally filtered by user."""
        sessions = []
        for file_path in SESSIONS_DIR.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                if user_id and data.get("user_id") != user_id:
                    continue
                sessions.append({
                    "session_id": data.get("session_id", file_path.stem),
                    "user_id": data.get("user_id", "anonymous"),
                    "origin_country": data.get("origin_country"),
                    "receiving_countries": data.get("receiving_countries", []),
                    "rule_text": (data.get("rule_text") or "")[:100],
                    "current_step": data.get("current_step", 1),
                    "status": data.get("status", "saved"),
                    "saved_at": data.get("saved_at", ""),
                    "updated_at": data.get("updated_at", ""),
                })
            except Exception as e:
                logger.warning(f"Failed to read session file {file_path}: {e}")
        sessions.sort(key=lambda s: s.get("saved_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a saved session."""
        file_path = SESSIONS_DIR / f"{session_id}.json"
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"Deleted session {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {e}")
                return False
        return False


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get the session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
