from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.models import User, UserSession
from db.session import get_db
from services.auth_service import (
    SESSION_COOKIE_NAME,
    get_session_by_token,
)


def get_current_session(
    request: Request, db: Session = Depends(get_db)
) -> UserSession:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session = get_session_by_token(db, raw_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return session


def get_current_user(
    session: UserSession = Depends(get_current_session),
) -> User:
    return session.user
