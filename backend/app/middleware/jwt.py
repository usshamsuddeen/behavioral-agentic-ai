"""
JWT Authentication Middleware
Token generation, validation, and session management
"""

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
import hashlib
import os

from app.database import get_db
from app.models.user import User, UserSession

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security
security = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int, email: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT refresh token
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_tokens(user: User, db: Session, request: Request = None) -> Tuple[str, str, datetime]:
    """
    Create both access and refresh tokens, and save session to database
    """
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    
    # Calculate expiry
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Get request metadata
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    
    # Save session to database
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        is_active=True
    )
    db.add(session)
    db.commit()
    
    return access_token, refresh_token, expires_at


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_access_token(token: str, db: Session) -> Optional[User]:
    """
    Verify an access token and return the user
    """
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = int(payload.get("sub"))
    
    # Check if session is still valid
    token_hash = hash_token(token)
    session = db.query(UserSession).filter(
        UserSession.token_hash == token_hash,
        UserSession.is_active == True
    ).first()
    
    if not session or not session.is_valid():
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    
    # Update last activity
    session.last_activity = datetime.utcnow()
    db.commit()
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    return user


def verify_refresh_token(token: str, db: Session) -> Optional[User]:
    """
    Verify a refresh token and return the user
    """
    payload = decode_token(token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = int(payload.get("sub"))
    
    # Check if session exists
    token_hash = hash_token(token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if session.is_expired():
        session.revoke()
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    
    return user


def revoke_session(token: str, db: Session) -> bool:
    """
    Revoke a session by its access token
    """
    token_hash = hash_token(token)
    session = db.query(UserSession).filter(
        UserSession.token_hash == token_hash
    ).first()
    
    if session:
        session.revoke()
        db.commit()
        return True
    return False


def revoke_all_user_sessions(user_id: int, db: Session) -> int:
    """
    Revoke all sessions for a user (logout from all devices)
    """
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()
    
    count = 0
    for session in sessions:
        session.revoke()
        count += 1
    
    db.commit()
    return count


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return verify_access_token(credentials.credentials, db)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get the current user (returns None if not authenticated)
    """
    if not credentials:
        return None
    
    try:
        return verify_access_token(credentials.credentials, db)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure the current user is a super admin — FRD v3.0 FR-7.1.2
    Accepts both 'super_admin' and 'admin' for backward compatibility.
    """
    if current_user.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_role(allowed_roles: List[str]):
    """
    RBAC dependency factory — FRD v3.0 FR-7.1.3
    Usage: Depends(require_role(["client", "super_admin"]))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def get_tenant_for_user(user: User, db: Session):
    """
    Resolve the tenant for an authenticated user — FRD v3.0 FR-7.3.1
    Returns the Tenant object. Raises 403 if user has no tenant.
    """
    from app.models.tenant import Tenant
    
    if user.role in ("super_admin", "admin"):
        # Super admins don't have a personal tenant — callers handle this
        return None
    
    if not user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="No tenant associated with this account. Please complete signup."
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account is suspended")
    
    return tenant
