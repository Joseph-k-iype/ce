"""
RBAC Admin Router
=================
Manages users, roles, workspaces, and audit log.
All endpoints require admin role.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies.auth import get_current_admin, User
from services.operational_store import get_operational_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rbac", tags=["Internal - RBAC"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    username: str
    email: str = ""
    role: str = "user"
    workspace_id: str = "default"
    password_hash: Optional[str] = None


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    workspace_id: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None


class RoleCreateRequest(BaseModel):
    name: str
    permissions: List[str]


class RoleUpdateRequest(BaseModel):
    permissions: List[str]


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: str = ""
    environment: str = "dev"


class WorkspaceMemberRequest(BaseModel):
    user_id: str
    role: str = "user"


# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(current_user: User = Depends(get_current_admin)):
    """List all users."""
    store = get_operational_store()
    users = store.list_users()
    # Don't expose password hashes
    for u in users:
        u.pop("password_hash", None)
    return {"users": users, "count": len(users)}


@router.post("/users")
async def create_user(request: UserCreateRequest,
                      current_user: User = Depends(get_current_admin)):
    """Create a new user."""
    store = get_operational_store()
    existing = store.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=409, detail=f"User '{request.username}' already exists")
    user_id = store.create_user(
        username=request.username,
        email=request.email,
        role=request.role,
        password_hash=request.password_hash,
        workspace_id=request.workspace_id,
    )
    store.log_action("user.create", user_id=current_user.user_id,
                     resource_type="user", resource_id=user_id,
                     details={"username": request.username, "role": request.role})
    return {"status": "created", "user_id": user_id}


@router.put("/users/{user_id}")
async def update_user(user_id: str, request: UserUpdateRequest,
                      current_user: User = Depends(get_current_admin)):
    """Update a user's role, workspace, or active status."""
    store = get_operational_store()
    kwargs = {}
    if request.role is not None:
        kwargs["role"] = request.role
    if request.workspace_id is not None:
        kwargs["workspace_id"] = request.workspace_id
    if request.is_active is not None:
        kwargs["is_active"] = 1 if request.is_active else 0
    if request.email is not None:
        kwargs["email"] = request.email
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = store.update_user(user_id, **kwargs)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    store.log_action("user.update", user_id=current_user.user_id,
                     resource_type="user", resource_id=user_id, details=kwargs)
    return {"status": "updated", "user_id": user_id}


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str,
                          current_user: User = Depends(get_current_admin)):
    """Deactivate a user (soft delete)."""
    store = get_operational_store()
    success = store.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    store.log_action("user.deactivate", user_id=current_user.user_id,
                     resource_type="user", resource_id=user_id)
    return {"status": "deactivated", "user_id": user_id}


# ── Roles ────────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(current_user: User = Depends(get_current_admin)):
    """List all roles and their permissions."""
    store = get_operational_store()
    return {"roles": store.list_roles()}


@router.post("/roles")
async def create_role(request: RoleCreateRequest,
                      current_user: User = Depends(get_current_admin)):
    """Create a custom role."""
    store = get_operational_store()
    role_id = store.create_role(request.name, request.permissions)
    store.log_action("role.create", user_id=current_user.user_id,
                     resource_type="role", resource_id=role_id,
                     details={"name": request.name})
    return {"status": "created", "role_id": role_id}


@router.put("/roles/{role_id}")
async def update_role(role_id: str, request: RoleUpdateRequest,
                      current_user: User = Depends(get_current_admin)):
    """Update a role's permissions."""
    store = get_operational_store()
    success = store.update_role_permissions(role_id, request.permissions)
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    store.log_action("role.update", user_id=current_user.user_id,
                     resource_type="role", resource_id=role_id,
                     details={"permissions": request.permissions})
    return {"status": "updated", "role_id": role_id}


# ── Workspaces ───────────────────────────────────────────────────────────────

@router.get("/workspaces")
async def list_workspaces(current_user: User = Depends(get_current_admin)):
    """List all workspaces."""
    store = get_operational_store()
    workspaces = store.list_workspaces()
    # Enrich with member counts
    for ws in workspaces:
        members = store.get_workspace_members(ws["workspace_id"])
        ws["member_count"] = len(members)
    return {"workspaces": workspaces}


@router.post("/workspaces")
async def create_workspace(request: WorkspaceCreateRequest,
                           current_user: User = Depends(get_current_admin)):
    """Create a new workspace."""
    store = get_operational_store()
    workspace_id = store.create_workspace(
        name=request.name,
        description=request.description,
        environment=request.environment,
    )
    store.log_action("workspace.create", user_id=current_user.user_id,
                     resource_type="workspace", resource_id=workspace_id,
                     details={"name": request.name})
    return {"status": "created", "workspace_id": workspace_id}


@router.get("/workspaces/{workspace_id}/members")
async def get_workspace_members(workspace_id: str,
                                current_user: User = Depends(get_current_admin)):
    """List members of a workspace."""
    store = get_operational_store()
    ws = store.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    members = store.get_workspace_members(workspace_id)
    return {"workspace_id": workspace_id, "members": members}


@router.post("/workspaces/{workspace_id}/members")
async def add_workspace_member(workspace_id: str, request: WorkspaceMemberRequest,
                               current_user: User = Depends(get_current_admin)):
    """Add a user to a workspace."""
    store = get_operational_store()
    ws = store.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    user = store.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    store.add_workspace_member(request.user_id, workspace_id, request.role)
    store.log_action("workspace.add_member", user_id=current_user.user_id,
                     resource_type="workspace", resource_id=workspace_id,
                     details={"member_user_id": request.user_id, "role": request.role})
    return {"status": "added", "workspace_id": workspace_id, "user_id": request.user_id}


# ── Audit Log ────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(limit: int = 50, offset: int = 0,
                        current_user: User = Depends(get_current_admin)):
    """Get paginated audit log."""
    store = get_operational_store()
    entries = store.list_audit_log(limit=limit, offset=offset)
    total = store.count_audit_log()
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}
