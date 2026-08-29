from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    Character,
    CharacterMapHexObservation,
    Expedition,
    ExpeditionCharacter,
    MapVersion,
    WorldMap,
)


class MapKnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_character(self, character_id: int) -> Character | None:
        return self.db.get(Character, character_id)

    def get_expedition(self, expedition_id: int) -> Expedition | None:
        return self.db.get(Expedition, expedition_id)

    def get_map(self, map_id: int) -> WorldMap | None:
        return self.db.get(WorldMap, map_id)

    def get_map_version(self, map_version_id: int) -> MapVersion | None:
        return self.db.get(MapVersion, map_version_id)

    def active_participants(
        self,
        expedition_id: int,
        game_minute: int,
    ) -> list[ExpeditionCharacter]:
        stmt = select(ExpeditionCharacter).where(
            ExpeditionCharacter.expedition_id == expedition_id,
            ExpeditionCharacter.joined_game_minute <= game_minute,
            ExpeditionCharacter.left_game_minute.is_(None),
        )
        return list(self.db.scalars(stmt))

    def add(self, observation: CharacterMapHexObservation) -> CharacterMapHexObservation:
        self.db.add(observation)
        self.db.flush()
        return observation

    def get_exact(
        self,
        *,
        character_id: int,
        expedition_id: int | None,
        map_id: int,
        q: int,
        r: int,
        observed_game_minute: int,
    ) -> CharacterMapHexObservation | None:
        stmt = select(CharacterMapHexObservation).where(
            CharacterMapHexObservation.character_id == character_id,
            CharacterMapHexObservation.map_id == map_id,
            CharacterMapHexObservation.q == q,
            CharacterMapHexObservation.r == r,
            CharacterMapHexObservation.observed_game_minute == observed_game_minute,
        )
        if expedition_id is None:
            stmt = stmt.where(CharacterMapHexObservation.expedition_id.is_(None))
        else:
            stmt = stmt.where(CharacterMapHexObservation.expedition_id == expedition_id)
        return self.db.scalar(stmt)

    def latest_for_hex(
        self,
        *,
        character_id: int,
        map_id: int,
        q: int,
        r: int,
        as_of_game_minute: int | None = None,
    ) -> CharacterMapHexObservation | None:
        stmt = select(CharacterMapHexObservation).where(
            CharacterMapHexObservation.character_id == character_id,
            CharacterMapHexObservation.map_id == map_id,
            CharacterMapHexObservation.q == q,
            CharacterMapHexObservation.r == r,
        )
        if as_of_game_minute is not None:
            stmt = stmt.where(
                CharacterMapHexObservation.observed_game_minute <= as_of_game_minute
            )
        stmt = stmt.order_by(
            CharacterMapHexObservation.observed_game_minute.desc(),
            CharacterMapHexObservation.id.desc(),
        )
        return self.db.scalar(stmt)

    def history_for_hex(
        self,
        *,
        character_id: int,
        map_id: int,
        q: int,
        r: int,
    ) -> list[CharacterMapHexObservation]:
        stmt = (
            select(CharacterMapHexObservation)
            .where(
                CharacterMapHexObservation.character_id == character_id,
                CharacterMapHexObservation.map_id == map_id,
                CharacterMapHexObservation.q == q,
                CharacterMapHexObservation.r == r,
            )
            .order_by(
                CharacterMapHexObservation.observed_game_minute,
                CharacterMapHexObservation.id,
            )
        )
        return list(self.db.scalars(stmt))

    def list_for_character_map(
        self,
        *,
        character_id: int,
        map_id: int,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterMapHexObservation]:
        stmt = select(CharacterMapHexObservation).where(
            CharacterMapHexObservation.character_id == character_id,
            CharacterMapHexObservation.map_id == map_id,
        )
        if as_of_game_minute is not None:
            stmt = stmt.where(
                CharacterMapHexObservation.observed_game_minute <= as_of_game_minute
            )
        stmt = stmt.order_by(
            CharacterMapHexObservation.q,
            CharacterMapHexObservation.r,
            CharacterMapHexObservation.observed_game_minute.desc(),
            CharacterMapHexObservation.id.desc(),
        )
        return list(self.db.scalars(stmt))
