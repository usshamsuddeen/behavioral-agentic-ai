"""
Authentication API Endpoints — FRD v3.0
Login, Signup, Logout, Token Refresh, Password Management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets

from app.database import get_db
from app.models.user import User, UserSession, UserSettings, UserRole
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.schemas.auth import (
    SignupRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, PasswordChangeRequest,
    UserResponse, UserUpdateRequest, OnboardingUpdateRequest
)
from app.middleware.jwt import (
    create_tokens, verify_refresh_token, revoke_session,
    revoke_all_user_sessions, get_current_user, hash_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ═══════════════════════════════════════════════════════════════════
# SIGNUP — FR-1.2 (Auto-creates Tenant + WidgetConfig)
# ═══════════════════════════════════════════════════════════════════

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    data: SignupRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new CLIENT user.
    Automatically creates:
      1. User record (role=CLIENT)
      2. Tenant record (with widget_api_key)
      3. WidgetConfig record (default settings)
      4. UserSettings record (default preferences)
    Returns JWT tokens upon successful registration.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 1. Create new user with CLIENT role
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        name=data.full_name,  # Backward compatibility
        company_name=data.company_name,
        role=UserRole.CLIENT.value,
        status="active",
        is_active=True,
        onboarding_completed=False,
        onboarding_step=0
    )
    user.set_password(data.password)

    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Create Tenant (multi-tenancy foundation)
    tenant = Tenant(
        name=data.company_name or f"{data.full_name}'s Store",
        store_url=data.store_url,
        widget_api_key=Tenant.generate_api_key(),
        owner_id=user.id,
        is_active=True,
        onboarding_completed=False,
        onboarding_step=0
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Link user to tenant
    user.tenant_id = tenant.id
    db.commit()

    # 3. Create default WidgetConfig
    widget_config = WidgetConfig(tenant_id=tenant.id)
    db.add(widget_config)
    db.commit()

    # 4. Create default settings
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    db.commit()

    # Generate API key for the user
    settings.api_key = f"bai_{secrets.token_urlsafe(32)}"
    db.commit()

    # Create tokens
    access_token, refresh_token, expires_at = create_tokens(user, db, request)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


# ═══════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    """
    # Find user by email
    user = db.query(User).filter(User.email == data.email.lower()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.verify_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token, refresh_token, expires_at = create_tokens(user, db, request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


# ═══════════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════════

@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout current session (revoke token).
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        revoke_session(token, db)
    
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout from all devices (revoke all sessions).
    """
    count = revoke_all_user_sessions(current_user.id, db)
    return {"message": f"Successfully logged out from {count} devices"}


# ═══════════════════════════════════════════════════════════════════
# TOKEN REFRESH
# ═══════════════════════════════════════════════════════════════════

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    user = verify_refresh_token(data.refresh_token, db)
    
    # Revoke old session
    old_token_hash = hash_token(data.refresh_token)
    old_session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == old_token_hash
    ).first()
    if old_session:
        old_session.revoke()
        db.commit()
    
    # Create new tokens
    access_token, refresh_token, expires_at = create_tokens(user, db, request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict()
    )


# ═══════════════════════════════════════════════════════════════════
# GET CURRENT USER (ME)
# ═══════════════════════════════════════════════════════════════════

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user profile.
    """
    # Get settings
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    user_data = current_user.to_dict()
    user_data["settings"] = settings.to_dict() if settings else None
    
    return user_data


# ═══════════════════════════════════════════════════════════════════
# UPDATE PROFILE
# ═══════════════════════════════════════════════════════════════════

@router.put("/me")
async def update_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile.
    """
    update_data = data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)
    
    # Update name for backward compatibility
    if 'full_name' in update_data:
        current_user.name = update_data['full_name']
    
    db.commit()
    db.refresh(current_user)
    
    return current_user.to_dict()


# ═══════════════════════════════════════════════════════════════════
# CHANGE PASSWORD
# ═══════════════════════════════════════════════════════════════════

@router.post("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    """
    if not current_user.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.set_password(data.new_password)
    
    # Revoke all other sessions (security measure)
    revoke_all_user_sessions(current_user.id, db)
    
    db.commit()
    
    return {"message": "Password changed successfully. Please login again."}


# ═══════════════════════════════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════════════════════════════

@router.put("/onboarding")
async def update_onboarding(
    data: OnboardingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update onboarding progress.
    """
    current_user.onboarding_step = data.step
    
    if data.completed:
        current_user.onboarding_completed = True
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "onboarding_step": current_user.onboarding_step,
        "onboarding_completed": current_user.onboarding_completed
    }


# ═══════════════════════════════════════════════════════════════════
# CHECK AUTH STATUS
# ═══════════════════════════════════════════════════════════════════

@router.get("/status")
async def auth_status(
    current_user: User = Depends(get_current_user)
):
    """
    Check if current token is valid.
    Returns basic user info if authenticated.
    """
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
