from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from db.models import User, UserSession
from dto.auth_dto import LoginRequest
from dto.user_dto import UserCreate
from routes.auth_routes import login, logout
from services.auth_dependencies import get_current_session, get_current_user
from services.auth_service import (
    SESSION_COOKIE_NAME,
    authenticate_user,
    create_session,
    hash_session_token,
)
from services.csrf_service import csrf_failure
from services.user_service import UserService


def _request(
    *,
    method: str = "GET",
    cookie: str | None = None,
    origin: str | None = None,
    referer: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        headers.append((b"cookie", cookie.encode()))
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    if referer is not None:
        headers.append((b"referer", referer.encode()))
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/auth/me",
            "scheme": "http",
            "server": ("testserver", 80),
            "headers": headers,
        }
    )


def _user(db, username: str = "auth_user") -> User:
    return UserService(db).create(
        UserCreate(
            username=username,
            email=f"{username}@example.com",
            password="correct-horse-battery-staple",
        )
    )


def test_registration_hashes_password(db):
    user = _user(db, "registration_user")

    assert user.password_hash != "correct-horse-battery-staple"
    assert authenticate_user(db, user.username, "correct-horse-battery-staple") is not None


def test_valid_login_creates_hashed_session_and_cookie(db):
    user = _user(db)
    response = Response()

    result = login(
        LoginRequest(
            username_or_email=user.email,
            password="correct-horse-battery-staple",
        ),
        response,
        db,
    )

    assert result.id == user.id
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    morsel = cookie[SESSION_COOKIE_NAME]
    raw_token = morsel.value
    session = db.query(UserSession).one()
    assert raw_token
    assert session.token_hash == hash_session_token(raw_token)
    assert session.token_hash != raw_token
    assert morsel["httponly"]
    assert morsel["samesite"].lower() == "lax"
    assert morsel["path"] == "/"
    assert morsel["secure"] == ""
    assert int(morsel["max-age"]) == 30 * 24 * 60 * 60


def test_invalid_password_and_unknown_user_are_rejected(db):
    user = _user(db)
    response = Response()

    with pytest.raises(HTTPException) as invalid_password:
        login(
            LoginRequest(username_or_email=user.username, password="wrong-password"),
            response,
            db,
        )
    assert invalid_password.value.status_code == 401
    assert db.query(UserSession).count() == 0

    with pytest.raises(HTTPException) as unknown_user:
        login(
            LoginRequest(username_or_email="missing@example.com", password="anything"),
            response,
            db,
        )
    assert unknown_user.value.status_code == 401


def test_me_requires_a_valid_session_and_returns_current_user(db):
    user = _user(db)
    session, raw_token = create_session(db, user)
    request = _request(cookie=f"{SESSION_COOKIE_NAME}={raw_token}")

    current_session = get_current_session(request, db)
    current_user = get_current_user(current_session)
    assert current_user.id == user.id

    with pytest.raises(HTTPException) as anonymous:
        get_current_session(_request(), db)
    assert anonymous.value.status_code == 401


def test_logout_deletes_session_and_clears_cookie(db):
    user = _user(db)
    session, _raw_token = create_session(db, user)
    response = Response()

    logout(response, session, db)

    assert db.get(UserSession, session.id) is None
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    morsel = cookie[SESSION_COOKIE_NAME]
    assert morsel.value == ""
    assert morsel["max-age"] == "0"


def test_expired_and_deleted_sessions_return_401(db):
    user = _user(db)
    expired_token = "expired-token"
    expired = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(expired_token),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db.add(expired)
    db.commit()

    with pytest.raises(HTTPException) as expired_error:
        get_current_session(
            _request(cookie=f"{SESSION_COOKIE_NAME}={expired_token}"), db
        )
    assert expired_error.value.status_code == 401

    active, active_token = create_session(db, user)
    db.delete(active)
    db.commit()
    with pytest.raises(HTTPException) as deleted_error:
        get_current_session(
            _request(cookie=f"{SESSION_COOKIE_NAME}={active_token}"), db
        )
    assert deleted_error.value.status_code == 401


def test_multiple_simultaneous_sessions_are_independent(db):
    user = _user(db)
    first, first_token = create_session(db, user)
    second, second_token = create_session(db, user)

    assert first.id != second.id
    assert first_token != second_token
    assert db.query(UserSession).count() == 2
    assert get_current_session(
        _request(cookie=f"{SESSION_COOKIE_NAME}={first_token}"), db
    ).id == first.id
    assert get_current_session(
        _request(cookie=f"{SESSION_COOKIE_NAME}={second_token}"), db
    ).id == second.id


def test_unsupported_password_hash_fails_safely(db):
    user = User(
        username="invalid_hash_user",
        email="invalid_hash@example.com",
        password_hash="not-a-supported-password-hash",
    )
    db.add(user)
    db.commit()

    assert authenticate_user(db, user.username, "anything") is None


def test_csrf_checks_origin_or_referer_for_cookie_authenticated_unsafe_requests():
    cookie = f"{SESSION_COOKIE_NAME}=opaque-token"
    assert csrf_failure(
        _request(method="POST", cookie=cookie, origin="http://testserver")
    ) is None
    assert csrf_failure(
        _request(method="POST", cookie=cookie, origin="https://attacker.example")
    ) == "Origin is not trusted"
    assert csrf_failure(
        _request(method="POST", cookie=cookie, referer="https://attacker.example/page")
    ) == "Referer is not trusted"
    assert csrf_failure(
        _request(method="POST", cookie=cookie, referer="http://testserver/page")
    ) is None
    assert csrf_failure(_request(method="GET", cookie=cookie, origin="https://attacker.example")) is None
