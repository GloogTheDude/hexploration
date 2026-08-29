from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from db.models import Character, CharacterSheetVersion


class CharacterSheetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_character_for_update(self, character_id: int) -> Character | None:
        stmt = (
            select(Character)
            .where(Character.id == character_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def next_version(self, character_id: int) -> int:
        stmt = select(
            func.coalesce(func.max(CharacterSheetVersion.version), 0) + 1
        ).where(CharacterSheetVersion.character_id == character_id)
        return int(self.db.scalar(stmt) or 1)

    def clear_current(self, character_id: int) -> None:
        stmt = (
            update(CharacterSheetVersion)
            .where(
                CharacterSheetVersion.character_id == character_id,
                CharacterSheetVersion.is_current.is_(True),
            )
            .values(is_current=False)
        )
        self.db.execute(stmt)

    def add(self, sheet: CharacterSheetVersion) -> CharacterSheetVersion:
        self.db.add(sheet)
        self.db.flush()
        return sheet

    def current(self, character_id: int) -> CharacterSheetVersion | None:
        stmt = (
            select(CharacterSheetVersion)
            .where(
                CharacterSheetVersion.character_id == character_id,
                CharacterSheetVersion.is_current.is_(True),
            )
            .order_by(CharacterSheetVersion.version.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def by_version(
        self,
        character_id: int,
        version: int,
    ) -> CharacterSheetVersion | None:
        stmt = select(CharacterSheetVersion).where(
            CharacterSheetVersion.character_id == character_id,
            CharacterSheetVersion.version == version,
        )
        return self.db.scalar(stmt)

    def history(self, character_id: int) -> list[CharacterSheetVersion]:
        stmt = (
            select(CharacterSheetVersion)
            .where(CharacterSheetVersion.character_id == character_id)
            .order_by(CharacterSheetVersion.version.desc())
        )
        return list(self.db.scalars(stmt))
