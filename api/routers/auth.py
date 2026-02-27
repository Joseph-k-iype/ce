from datetime import timedelta
import logging

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

# In-memory fallback/bootstrap users.
FALLBACK_USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "user": {"password": "user", "role": "user"}
}

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user via LDAP or Fallback system and return a JWT Access Token.
    """
    username = form_data.username
    password = form_data.password
    
    role = "user" # Default
    authenticated = False
    
    # 1. Try LDAP First
    if settings.auth.enable_ldap:
        logger.info(f"Attempting LDAP auth for {username}")
        if authenticate_ldap(username, password):
            authenticated = True
            # Basic mapping logic - could be expanded to parse LDAP groups
            if "admin" in username.lower():
                role = "admin"
                
    # 2. Try Fallback Local Users if LDAP fails or is disabled
    if not authenticated:
        if username in FALLBACK_USERS and FALLBACK_USERS[username]["password"] == password:
            authenticated = True
            role = FALLBACK_USERS[username]["role"]
            logger.info(f"Resolved fallback local auth for {username}")
            
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username, "role": role}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": role,
        "username": username
    }
