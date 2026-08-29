from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from db.models import CharacterSheetDataVersion


class CharacterSheetDataRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def current(self, character_id: int) -> CharacterSheetDataVersion | None:
        stmt = (
            select(CharacterSheetDataVersion)
            .where(
                CharacterSheetDataVersion.character_id == character_id,
                CharacterSheetDataVersion.is_current.is_(True),
            )
            .order_by(CharacterSheetDataVersion.version.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def by_version(self, character_id: int, version: int) -> CharacterSheetDataVersion | None:
        stmt = select(CharacterSheetDataVersion).where(
            CharacterSheetDataVersion.character_id == character_id,
            CharacterSheetDataVersion.version == version,
        )
        return self.db.scalar(stmt)

    def history(self, character_id: int) -> list[CharacterSheetDataVersion]:
        stmt = (
            select(CharacterSheetDataVersion)
            .where(CharacterSheetDataVersion.character_id == character_id)
            .order_by(CharacterSheetDataVersion.version.desc())
        )
        return list(self.db.scalars(stmt))

    def next_version(self, character_id: int) -> int:
        stmt = select(func.max(CharacterSheetDataVersion.version)).where(
            CharacterSheetDataVersion.character_id == character_id
        )
        return int(self.db.scalar(stmt) or 0) + 1

    def clear_current(self, character_id: int) -> None:
        self.db.execute(
            update(CharacterSheetDataVersion)
            .where(CharacterSheetDataVersion.character_id == character_id)
            .values(is_current=False)
        )

    def add(self, version: CharacterSheetDataVersion) -> CharacterSheetDataVersion:
        self.db.add(version)
        self.db.flush()
        return version
