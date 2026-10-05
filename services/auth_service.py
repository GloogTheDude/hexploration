from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import User, UserSession


SESSION_COOKIE_NAME = "hexploration_session"
SESSION_TTL = timedelta(days=30)
SESSION_MAX_AGE = int(SESSION_TTL.total_seconds())
_password_hash = PasswordHash.recommended()


def utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> tuple[UserSession, str]:
    raw_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=utc_now() + SESSION_TTL,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def find_user_for_login(db: Session, username_or_email: str) -> User | None:
    identifier = username_or_email.strip()
    return db.scalar(
        select(User).where(
            (User.username == identifier)
            | (User.email == identifier.lower())
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Return False for unsupported hashes without exposing hash errors."""
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def authenticate_user(
    db: Session, username_or_email: str, password: str
) -> User | None:
    user = find_user_for_login(db, username_or_email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def get_session_by_token(db: Session, raw_token: str) -> UserSession | None:
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_session_token(raw_token)
        )
    )
    if session is None or _as_utc(session.expires_at) <= utc_now():
        return None
    return session


def session_cookie_secure() -> bool:
    configured = os.getenv("SESSION_COOKIE_SECURE")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
