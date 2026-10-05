import pytest
from fastapi import HTTPException
from pwdlib import PasswordHash
from pydantic import ValidationError

from dto.user_dto import UserCreate
from routes.user_routes import create_user
from services.user_service import UserService


def test_user_creation_stores_a_verifiable_password_hash(db):
    user = UserService(db).create(
        UserCreate(
            username="hashed_user",
            email="hashed@example.com",
            password="correct-horse-battery-staple",
        )
    )

    assert user.password_hash != "correct-horse-battery-staple"
    assert PasswordHash.recommended().verify(
        "correct-horse-battery-staple", user.password_hash
    )


def test_duplicate_username_or_email_is_a_client_conflict(db):
    data = UserCreate(
        username="duplicate_user",
        email="duplicate@example.com",
        password="correct-horse-battery-staple",
    )
    create_user(data, db)

    with pytest.raises(HTTPException) as duplicate:
        create_user(data, db)

    assert duplicate.value.status_code == 409


def test_public_registration_rejects_privilege_fields(db):
    with pytest.raises(ValidationError):
        UserCreate(
            username="safe_user",
            email="safe@example.com",
            password="correct-horse-battery-staple",
            campaign_role="DM",
        )
