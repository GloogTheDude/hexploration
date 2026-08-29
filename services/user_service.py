from __future__ import annotations

from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import User
from dto.user_dto import UserCreate
from repositories.user_repository import UserRepository
from services.errors import ConflictError, NotFoundError


_password_hash = PasswordHash.recommended()


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def create(self, data: UserCreate) -> User:
        if self.repo.get_by_username(data.username) is not None:
            raise ConflictError("Username already exists")

        if self.repo.get_by_email(str(data.email)) is not None:
            raise ConflictError("Email already exists")

        user = User(
            username=data.username.strip(),
            email=str(data.email).lower(),
            password_hash=_password_hash.hash(data.password),
        )

        try:
            self.repo.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Username or email already exists") from exc

    def get(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
