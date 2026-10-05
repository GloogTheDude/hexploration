from pwdlib import PasswordHash

from dto.user_dto import UserCreate
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
