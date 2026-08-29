from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import CharacterKnowledgeObservation


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        observation: CharacterKnowledgeObservation,
    ) -> CharacterKnowledgeObservation:
        self.db.add(observation)
        self.db.flush()
        return observation

    def get_exact(
        self,
        *,
        character_id: int,
        expedition_id: int | None,
        target_type: str,
        target_id: int,
        observed_game_minute: int,
    ) -> CharacterKnowledgeObservation | None:
        stmt = select(CharacterKnowledgeObservation).where(
            CharacterKnowledgeObservation.character_id == character_id,
            CharacterKnowledgeObservation.expedition_id == expedition_id,
            CharacterKnowledgeObservation.target_type == target_type,
            CharacterKnowledgeObservation.target_id == target_id,
            CharacterKnowledgeObservation.observed_game_minute == observed_game_minute,
        )
        return self.db.scalar(stmt)

    def history_for_target(
        self,
        *,
        character_id: int,
        target_type: str,
        target_id: int,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterKnowledgeObservation]:
        stmt = select(CharacterKnowledgeObservation).where(
            CharacterKnowledgeObservation.character_id == character_id,
            CharacterKnowledgeObservation.target_type == target_type,
            CharacterKnowledgeObservation.target_id == target_id,
        )
        if as_of_game_minute is not None:
            stmt = stmt.where(
                CharacterKnowledgeObservation.observed_game_minute
                <= as_of_game_minute
            )
        stmt = stmt.order_by(
            CharacterKnowledgeObservation.observed_game_minute.asc(),
            CharacterKnowledgeObservation.id.asc(),
        )
        return list(self.db.scalars(stmt))

    def latest_for_target(
        self,
        *,
        character_id: int,
        target_type: str,
        target_id: int,
        as_of_game_minute: int | None = None,
    ) -> CharacterKnowledgeObservation | None:
        stmt = select(CharacterKnowledgeObservation).where(
            CharacterKnowledgeObservation.character_id == character_id,
            CharacterKnowledgeObservation.target_type == target_type,
            CharacterKnowledgeObservation.target_id == target_id,
        )
        if as_of_game_minute is not None:
            stmt = stmt.where(
                CharacterKnowledgeObservation.observed_game_minute
                <= as_of_game_minute
            )
        stmt = stmt.order_by(
            CharacterKnowledgeObservation.observed_game_minute.desc(),
            CharacterKnowledgeObservation.id.desc(),
        )
        return self.db.scalar(stmt)

    def list_for_character(
        self,
        character_id: int,
        *,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterKnowledgeObservation]:
        stmt = select(CharacterKnowledgeObservation).where(
            CharacterKnowledgeObservation.character_id == character_id
        )
        if as_of_game_minute is not None:
            stmt = stmt.where(
                CharacterKnowledgeObservation.observed_game_minute
                <= as_of_game_minute
            )
        stmt = stmt.order_by(
            CharacterKnowledgeObservation.observed_game_minute.asc(),
            CharacterKnowledgeObservation.id.asc(),
        )
        return list(self.db.scalars(stmt))

    def list_for_expedition(
        self,
        expedition_id: int,
    ) -> list[CharacterKnowledgeObservation]:
        stmt = (
            select(CharacterKnowledgeObservation)
            .where(CharacterKnowledgeObservation.expedition_id == expedition_id)
            .order_by(
                CharacterKnowledgeObservation.observed_game_minute.asc(),
                CharacterKnowledgeObservation.id.asc(),
            )
        )
        return list(self.db.scalars(stmt))
