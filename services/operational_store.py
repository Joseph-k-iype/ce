"""
Operational Store — SQLite-backed persistence for data sources, RBAC, and audit log.

All tables are auto-created on first access. The SQLite file path defaults to
data/operational.db but is configurable via the OPERATIONAL_DB_PATH env var.
"""

import sqlite3
import json
import uuid
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def _db_path() -> Path:
    """Resolve the operational DB file path."""
    import os
    from config.settings import settings
    env_path = os.environ.get("OPERATIONAL_DB_PATH")
    if env_path:
        return Path(env_path)
    data_dir = settings.paths.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "operational.db"


@contextmanager
def _get_conn():
    """Context manager for a SQLite connection with WAL mode and row_factory."""
    path = _db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema initialization ────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS data_sources (
    source_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    description     TEXT DEFAULT '',
    config_json     TEXT NOT NULL DEFAULT '{}',
    auth_config_json TEXT NOT NULL DEFAULT '{}',
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT DEFAULT '',
    environment     TEXT NOT NULL DEFAULT 'dev',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT DEFAULT '',
    password_hash   TEXT,
    role            TEXT NOT NULL DEFAULT 'user',
    workspace_id    TEXT REFERENCES workspaces(workspace_id),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    role_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    permissions_json TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_members (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    workspace_id    TEXT NOT NULL REFERENCES workspaces(workspace_id),
    role            TEXT NOT NULL,
    UNIQUE(user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    details_json    TEXT,
    timestamp       TEXT NOT NULL
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO workspaces (workspace_id, name, description, environment, created_at, updated_at)
VALUES ('default', 'Default', 'Default workspace', 'dev', ?, ?);

INSERT OR IGNORE INTO roles (role_id, name, permissions_json, created_at)
VALUES
  ('role_admin',  'admin',  '["*"]',                                            ?),
  ('role_editor', 'editor', '["rule.read","rule.approve","rule.submit","rule.edit"]', ?),
  ('role_user',   'user',   '["rule.read","evaluation.run"]',                   ?);
"""


class OperationalStore:
    """Singleton class for all operational SQLite operations."""

    def __init__(self):
        self._initialized = False

    def init(self):
        """Initialize schema and seed defaults. Call once at startup."""
        with _get_conn() as conn:
            conn.executescript(SCHEMA_SQL)
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO workspaces (workspace_id, name, description, environment, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                ('default', 'Default', 'Default workspace', 'dev', now, now)
            )
            for role_id, name, perms in [
                ('role_admin',  'admin',  '["*"]'),
                ('role_editor', 'editor', '["rule.read","rule.approve","rule.submit","rule.edit"]'),
                ('role_user',   'user',   '["rule.read","evaluation.run"]'),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO roles (role_id, name, permissions_json, created_at) VALUES (?,?,?,?)",
                    (role_id, name, perms, now)
                )
        self._initialized = True
        logger.info("Operational store initialized at %s", _db_path())

    # ── Data Sources ──────────────────────────────────────────────────────────

    def upsert_data_source(self, source_id: str, name: str, source_type: str,
                           description: str, config: dict, auth_config: dict,
                           enabled: bool = True) -> None:
        now = _now()
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO data_sources (source_id, name, source_type, description, config_json, auth_config_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name,
                    source_type=excluded.source_type,
                    description=excluded.description,
                    config_json=excluded.config_json,
                    auth_config_json=excluded.auth_config_json,
                    enabled=excluded.enabled,
                    updated_at=excluded.updated_at
            """, (source_id, name, source_type, description,
                  json.dumps(config), json.dumps(auth_config),
                  1 if enabled else 0, now, now))

    def get_data_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM data_sources WHERE source_id=?", (source_id,)).fetchone()
            return self._ds_row(row) if row else None

    def list_data_sources(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            if source_type:
                rows = conn.execute("SELECT * FROM data_sources WHERE source_type=? ORDER BY created_at", (source_type,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM data_sources ORDER BY created_at").fetchall()
            return [self._ds_row(r) for r in rows]

    def delete_data_source(self, source_id: str) -> bool:
        with _get_conn() as conn:
            cur = conn.execute("DELETE FROM data_sources WHERE source_id=?", (source_id,))
            return cur.rowcount > 0

    def find_data_source_by_hash(self, name: str, source_type: str, config_hash: str) -> Optional[str]:
        """Return existing source_id if name+type+config match (deduplication)."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT source_id FROM data_sources WHERE name=? AND source_type=?",
                (name, source_type)
            ).fetchone()
            if not row:
                return None
            # Compare config hash
            existing = conn.execute(
                "SELECT config_json FROM data_sources WHERE source_id=?", (row[0],)
            ).fetchone()
            if existing:
                import hashlib
                existing_hash = hashlib.md5(existing[0].encode()).hexdigest()
                if existing_hash == config_hash:
                    return row[0]
            return None

    @staticmethod
    def _ds_row(row) -> Dict[str, Any]:
        return {
            "source_id": row["source_id"],
            "name": row["name"],
            "source_type": row["source_type"],
            "description": row["description"],
            "config": json.loads(row["config_json"]),
            "auth_config": json.loads(row["auth_config_json"]),
            "enabled": bool(row["enabled"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ── Users ──────────────────────────────────────────────────────────────────

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            return dict(row) if row else None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
            return [dict(r) for r in rows]

    def create_user(self, username: str, email: str = '', role: str = 'user',
                    password_hash: Optional[str] = None,
                    workspace_id: str = 'default') -> str:
        user_id = str(uuid.uuid4())
        now = _now()
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, email, password_hash, role, workspace_id, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (user_id, username, email, password_hash, role, workspace_id, now, now))
        return user_id

    def update_user(self, user_id: str, **kwargs) -> bool:
        allowed = {'email', 'role', 'workspace_id', 'is_active', 'password_hash'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        fields['updated_at'] = _now()
        set_clause = ', '.join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [user_id]
        with _get_conn() as conn:
            cur = conn.execute(f"UPDATE users SET {set_clause} WHERE user_id=?", values)
            return cur.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        with _get_conn() as conn:
            cur = conn.execute("UPDATE users SET is_active=0, updated_at=? WHERE user_id=?", (_now(), user_id))
            return cur.rowcount > 0

    # ── Roles ──────────────────────────────────────────────────────────────────

    def list_roles(self) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM roles ORDER BY name").fetchall()
            return [{"role_id": r["role_id"], "name": r["name"],
                     "permissions": json.loads(r["permissions_json"]),
                     "created_at": r["created_at"]} for r in rows]

    def create_role(self, name: str, permissions: List[str]) -> str:
        role_id = f"role_{uuid.uuid4().hex[:8]}"
        now = _now()
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO roles (role_id, name, permissions_json, created_at) VALUES (?, ?, ?, ?)",
                (role_id, name, json.dumps(permissions), now)
            )
        return role_id

    def update_role_permissions(self, role_id: str, permissions: List[str]) -> bool:
        with _get_conn() as conn:
            cur = conn.execute(
                "UPDATE roles SET permissions_json=? WHERE role_id=?",
                (json.dumps(permissions), role_id)
            )
            return cur.rowcount > 0

    # ── Workspaces ─────────────────────────────────────────────────────────────

    def list_workspaces(self) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM workspaces ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM workspaces WHERE workspace_id=?", (workspace_id,)).fetchone()
            return dict(row) if row else None

    def create_workspace(self, name: str, description: str = '',
                         environment: str = 'dev') -> str:
        workspace_id = f"ws_{uuid.uuid4().hex[:8]}"
        now = _now()
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO workspaces (workspace_id, name, description, environment, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (workspace_id, name, description, environment, now, now))
        return workspace_id

    def add_workspace_member(self, user_id: str, workspace_id: str, role: str) -> None:
        member_id = str(uuid.uuid4())
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO workspace_members (id, user_id, workspace_id, role)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, workspace_id) DO UPDATE SET role=excluded.role
            """, (member_id, user_id, workspace_id, role))

    def get_workspace_members(self, workspace_id: str) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT wm.*, u.username, u.email, u.is_active
                FROM workspace_members wm
                JOIN users u ON u.user_id = wm.user_id
                WHERE wm.workspace_id=?
            """, (workspace_id,)).fetchall()
            return [dict(r) for r in rows]

    # ── Audit Log ──────────────────────────────────────────────────────────────

    def log_action(self, action: str, user_id: Optional[str] = None,
                   resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None,
                   details: Optional[dict] = None) -> None:
        now = _now()
        entry_id = str(uuid.uuid4())
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (entry_id, user_id, action, resource_type, resource_id,
                  json.dumps(details) if details else None, now))

    def list_audit_log(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            result = []
            for r in rows:
                row_dict = dict(r)
                if row_dict.get('details_json'):
                    try:
                        row_dict['details'] = json.loads(row_dict['details_json'])
                    except Exception:
                        row_dict['details'] = None
                del row_dict['details_json']
                result.append(row_dict)
            return result

    def count_audit_log(self) -> int:
        with _get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]


# ── Global singleton ─────────────────────────────────────────────────────────

_store = OperationalStore()


def get_operational_store() -> OperationalStore:
    """Get the global operational store instance."""
    return _store
