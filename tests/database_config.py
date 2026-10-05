from __future__ import annotations

import os

from sqlalchemy.engine import make_url


def validated_test_database_url() -> str | None:
    """Return the explicit external test URL, rejecting non-test databases."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        return None

    try:
        database_name = make_url(database_url).database or ""
    except Exception as exc:
        raise ValueError(
            "pytest refuses TEST_DATABASE_URL because it is not a valid database URL"
        ) from exc

    if "test" not in database_name.lower():
        raise ValueError(
            "pytest refuses to use TEST_DATABASE_URL because the database name "
            "does not appear to be dedicated to tests; include 'test' in the "
            "database name"
        )

    return database_url
