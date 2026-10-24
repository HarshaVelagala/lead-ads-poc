import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app import config
from app.services.auth import (
    ACCESS_TOKEN_TTL_SECONDS,
    WEBSOCKET_TICKET_TTL_SECONDS,
    authenticate_access_token,
    create_access_token,
    create_websocket_ticket,
    ensure_auth_configured,
    password_hasher,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authenticate_access_token(credentials.credentials)


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest) -> LoginResponse:
    ensure_auth_configured()
    email_matches = hmac.compare_digest(
        credentials.email.casefold().encode("utf-8"),
        config.ADMIN_EMAIL.casefold().encode("utf-8"),
    )
    password_matches = password_hasher.verify(
        credentials.password,
        config.ADMIN_PASSWORD_HASH,
    )
    if not email_matches or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginResponse(
        access_token=create_access_token(config.ADMIN_EMAIL),
        expires_in=ACCESS_TOKEN_TTL_SECONDS,
    )


@router.post("/ws-ticket", response_model=LoginResponse)
def create_ws_ticket(
    admin_email: Annotated[str, Depends(get_current_admin)],
) -> LoginResponse:
    return LoginResponse(
        access_token=create_websocket_ticket(admin_email),
        expires_in=WEBSOCKET_TICKET_TTL_SECONDS,
    )
