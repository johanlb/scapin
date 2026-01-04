"""
Authentication Router

Login endpoint for obtaining JWT tokens.
Single-user system with PIN code authentication.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.core.config_manager import get_config
from src.jeeves.api.auth import JWTHandler, TokenData, verify_pin
from src.jeeves.api.deps import get_current_user
from src.jeeves.api.models.responses import APIResponse

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request body"""

    pin: str = Field(..., min_length=4, max_length=6, description="PIN code (4-6 digits)")


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(request: LoginRequest) -> APIResponse[TokenResponse]:
    """
    Authenticate with PIN and get JWT token

    Single-user system: no username required, just PIN code.

    - **pin**: 4-6 digit PIN code

    Returns JWT access token valid for 7 days (configurable).
    """
    config = get_config()

    # Check if auth is enabled
    if not config.auth.enabled:
        # Auth disabled - return token without verification
        jwt_handler = JWTHandler()
        access_token = jwt_handler.create_access_token()
        return APIResponse(
            success=True,
            data=TokenResponse(
                access_token=access_token,
                expires_in=config.auth.jwt_expire_minutes * 60,
            ),
            error=None,
            timestamp=datetime.now(timezone.utc),
        )

    # Check if PIN hash is configured
    if not config.auth.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PIN non configuré. Ajoutez AUTH__PIN_HASH dans .env",
        )

    # Verify PIN
    if not verify_pin(request.pin, config.auth.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrect",
        )

    # Generate token
    jwt_handler = JWTHandler()
    access_token = jwt_handler.create_access_token()

    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=access_token,
            expires_in=config.auth.jwt_expire_minutes * 60,
        ),
        error=None,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/check")
async def check_auth(
    current_user: Optional[TokenData] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Check current authentication status

    Requires valid JWT token (unless auth is disabled).

    Returns:
        - authenticated: True if user is authenticated
        - user: Username from token (or "anonymous" if auth disabled)
    """
    config = get_config()

    # If auth disabled, always authenticated as anonymous
    if not config.auth.enabled:
        return APIResponse(
            success=True,
            data={
                "authenticated": True,
                "user": "anonymous",
                "auth_required": False,
            },
            error=None,
            timestamp=datetime.now(timezone.utc),
        )

    # Auth enabled and we have a valid user (get_current_user would have raised 401 otherwise)
    return APIResponse(
        success=True,
        data={
            "authenticated": True,
            "user": current_user.sub if current_user else "anonymous",
            "auth_required": True,
        },
        error=None,
        timestamp=datetime.now(timezone.utc),
    )
