from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from app import config

ACCESS_TOKEN_TTL_SECONDS = 60 * 60
WEBSOCKET_TICKET_TTL_SECONDS = 60
JWT_ISSUER = "meta-lead-ads-poc"
JWT_AUDIENCE = "meta-lead-ads-api"
WEBSOCKET_AUDIENCE = "meta-lead-ads-websocket"
password_hasher = PasswordHash.recommended()


def ensure_auth_configured() -> None:
    if (
        not config.ADMIN_EMAIL
        or not config.ADMIN_PASSWORD_HASH.startswith("$argon2id$")
        or len(config.JWT_SECRET_KEY.encode("utf-8")) < 32
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured",
        )


def _create_token(email: str, audience: str, lifetime_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": email,
            "iat": now,
            "exp": now + timedelta(seconds=lifetime_seconds),
            "iss": JWT_ISSUER,
            "aud": audience,
        },
        config.JWT_SECRET_KEY,
        algorithm="HS256",
    )


def create_access_token(email: str) -> str:
    return _create_token(email, JWT_AUDIENCE, ACCESS_TOKEN_TTL_SECONDS)


def create_websocket_ticket(email: str) -> str:
    return _create_token(email, WEBSOCKET_AUDIENCE, WEBSOCKET_TICKET_TTL_SECONDS)


def _authenticate_token(token: str, audience: str) -> str:
    ensure_auth_configured()
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=audience,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or subject.casefold() != config.ADMIN_EMAIL.casefold():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def authenticate_access_token(token: str) -> str:
    return _authenticate_token(token, JWT_AUDIENCE)


def authenticate_websocket_ticket(ticket: str) -> str:
    return _authenticate_token(ticket, WEBSOCKET_AUDIENCE)
