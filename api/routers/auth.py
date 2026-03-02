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

    role = "user" # Default
    authenticated = False

    # 1. Try LDAP First (preferred for production)
    if settings.auth.enable_ldap:
        logger.info(f"Attempting LDAP auth for {username}")
        if authenticate_ldap(username, password):
            authenticated = True
            # Basic mapping logic - could be expanded to parse LDAP groups
            if "admin" in username.lower():
                role = "admin"
            logger.info(f"LDAP authentication successful for {username}")

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

    access_token_expires = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username, "role": role}, expires_delta=access_token_expires
    )

    logger.info(f"Access token generated for {username} with role: {role}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "username": username
    }
