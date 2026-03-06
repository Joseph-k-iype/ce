from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None

class User(BaseModel):
    username: str
    role: str
    user_id: Optional[str] = None
    workspace_id: str = "default"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.auth.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm
    )
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm]
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: Optional[str] = payload.get("user_id")
        workspace_id: str = payload.get("workspace_id", "default")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role, user_id=user_id, workspace_id=workspace_id)
    except JWTError:
        raise credentials_exception

    return User(username=token_data.username, role=token_data.role,
                user_id=token_data.user_id, workspace_id=token_data.workspace_id or "default")


async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Verifies that the current user has the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted",
        )
    return current_user


async def get_current_editor(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Verifies that the current user has the 'editor' or 'admin' role."""
    if current_user.role not in ("editor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires editor or admin role",
        )
    return current_user
