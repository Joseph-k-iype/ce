from datetime import timedelta
import logging
import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from config.settings import settings
from api.dependencies.auth import create_access_token
from api.services.ldap_auth import authenticate_ldap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Internal - Authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


def verify_local_user(username: str, password: str) -> tuple[bool, str]:
    """
    Verify local fallback user credentials using bcrypt.

    Returns:
        tuple[bool, str]: (authenticated, role)
    """
    if not settings.auth.enable_local_fallback:
        return False, ""

    try:
        if username == settings.auth.local_admin_username:
            password_hash = settings.auth.local_admin_password_hash
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return True, "admin"
        elif username == settings.auth.local_user_username:
            password_hash = settings.auth.local_user_password_hash
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return True, "user"
    except Exception as e:
        logger.error(f"Error verifying local user credentials: {e}")
        return False, ""

    return False, ""

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user via LDAP or local fallback system and return a JWT Access Token.

    Security Note: Local fallback authentication is for development only.
    In production, disable local fallback and use LDAP authentication.
    """
    username = form_data.username
    password = form_data.password

    role = "user"  # Default
    authenticated = False
    display_name = username  # overwritten by LDAP result if available
    email = ""

    # 1. Try LDAP First (preferred for production)
    if settings.auth.enable_ldap:
        logger.info(f"Attempting LDAP auth for employee_id={username}")
        ldap_result = authenticate_ldap(username, password)
        if ldap_result:
            authenticated = True
            # Role determined by explicit admin employee-ID whitelist only
            role = "admin" if username in settings.auth.ldap_admin_employee_ids else "user"
            display_name = ldap_result.get("display_name", username)
            email = ldap_result.get("email", "")

    # 2. Try Local Fallback if LDAP fails or is disabled
    if not authenticated and settings.auth.enable_local_fallback:
        is_valid, user_role = verify_local_user(username, password)
        if is_valid:
            authenticated = True
            role = user_role
            logger.warning(f"Using local fallback authentication for {username} - NOT recommended for production!")

    if not authenticated:
        logger.warning(f"Authentication failed for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up or auto-create user in SQLite operational store
    user_id = None
    workspace_id = "default"
    try:
        from services.operational_store import get_operational_store
        store = get_operational_store()
        db_user = store.get_user_by_username(username)
        if db_user:
            user_id = db_user.get("user_id")
            workspace_id = db_user.get("workspace_id") or "default"
            # Keep auth-derived role authoritative (admin list may have changed)
            if db_user.get("role") != role:
                store.update_user(user_id, role=role)
        else:
            # Auto-create user record on first login; password_hash stays NULL for LDAP users
            user_id = store.create_user(
                username=username,
                email=email,
                role=role,
                workspace_id=workspace_id,
            )
            logger.info(f"Auto-created user record for {username} with role {role}")
    except Exception as e:
        logger.warning(f"Could not sync user with operational store: {e}")

    access_token_expires = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username, "role": role, "user_id": user_id, "workspace_id": workspace_id},
        expires_delta=access_token_expires
    )

    logger.info(f"Access token generated for {username} with role: {role}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "username": display_name,  # LDAP displayName shown in UI; falls back to employee_id
    }
