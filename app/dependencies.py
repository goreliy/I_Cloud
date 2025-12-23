"""Common dependencies for routes"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.api_key import ApiKey

security = HTTPBearer(auto_error=False)


def get_token_from_cookie_or_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None)
) -> Optional[str]:
    """
    Extract JWT token from cookie (for web) or Authorization header (for API)
    """
    # Try to get from Authorization header first (API calls)
    if credentials:
        return credentials.credentials
    
    # Try to get from cookie (web interface)
    if access_token:
        # Remove "Bearer " prefix if present
        if access_token.startswith("Bearer "):
            return access_token[7:]
        return access_token
    
    return None


def get_current_user(
    token: Optional[str] = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token (cookie or header)
    If AUTH_ENABLED is False, returns None (no authentication required)
    """
    if not settings.AUTH_ENABLED:
        return None
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token, but don't raise error if not authenticated
    """
    if not settings.AUTH_ENABLED:
        return None
    
    if token is None:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user if user and user.is_active else None


def verify_api_key(
    api_key: str,
    key_type: str,
    db: Session
) -> Optional[ApiKey]:
    """
    Verify API key for channel access
    If AUTH_ENABLED is False, returns mock ApiKey (no verification)
    """
    if not settings.AUTH_ENABLED:
        # In no-auth mode, create a mock ApiKey for compatibility
        mock_key = ApiKey()
        mock_key.id = 0
        mock_key.channel_id = 0
        mock_key.type = key_type
        mock_key.is_active = True
        return mock_key
    
    key = db.query(ApiKey).filter(
        ApiKey.key == api_key,
        ApiKey.type == key_type,
        ApiKey.is_active == True
    ).first()
    
    return key


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that current user is admin
    """
    if settings.AUTH_ENABLED and (not current_user or not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

