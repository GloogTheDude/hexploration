from __future__ import annotations

import os
from urllib.parse import urlsplit

from starlette.requests import Request

from services.auth_service import SESSION_COOKIE_NAME


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _origin(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _trusted_origins(request: Request) -> set[str]:
    configured = {
        item.strip().rstrip("/")
        for item in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
        if item.strip()
    }
    configured.add(f"{request.url.scheme}://{request.url.netloc}")
    return configured


def csrf_failure(request: Request) -> str | None:
    """Return a reason when a cookie-authenticated unsafe request is invalid."""
    if request.method.upper() not in UNSAFE_METHODS:
        return None
    if SESSION_COOKIE_NAME not in request.cookies:
        # Login and public registration do not carry an authenticated session.
        return None

    trusted = _trusted_origins(request)
    request_origin = _origin(request.headers.get("origin"))
    if request_origin is not None:
        if request_origin not in trusted:
            return "Origin is not trusted"
        return None

    referer = request.headers.get("referer")
    if referer is not None:
        if _origin(referer) not in trusted:
            return "Referer is not trusted"
        return None

    # Non-browser clients may omit both headers. They do not have browser
    # ambient-origin behavior, so preserve API usability in the MVP.
    return None
