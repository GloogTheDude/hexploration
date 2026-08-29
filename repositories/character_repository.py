from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Character


class CharacterRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, character_id: int) -> Character | None:
        return self.db.get(Character, character_id)

    def add(self, character: Character) -> Character:
        self.db.add(character)
        self.db.flush()
        return character

    def list_for_campaign(self, campaign_id: int) -> list[Character]:
        stmt = (
            select(Character)
            .where(Character.campaign_id == campaign_id)
            .order_by(Character.name)
        )
        return list(self.db.scalars(stmt))

    def list_for_user(self, user_id: int) -> list[Character]:
        stmt = (
            select(Character)
            .where(Character.owner_user_id == user_id)
            .order_by(Character.name)
        )
        return list(self.db.scalars(stmt))
