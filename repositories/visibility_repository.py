from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Expedition, ExpeditionCharacter, MapHex, PointOfInterest


class VisibilityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_expedition(self, expedition_id: int) -> Expedition | None:
        return self.db.get(Expedition, expedition_id)

    def get_hex(self, map_version_id: int, q: int, r: int) -> MapHex | None:
        stmt = select(MapHex).where(
            MapHex.map_version_id == map_version_id,
            MapHex.q == q,
            MapHex.r == r,
        )
        return self.db.scalar(stmt)

    def list_hexes(self, map_version_id: int) -> list[MapHex]:
        stmt = (
            select(MapHex)
            .where(MapHex.map_version_id == map_version_id)
            .order_by(MapHex.q, MapHex.r)
        )
        return list(self.db.scalars(stmt))

    def list_pois_with_hex(
        self,
        map_version_id: int,
    ) -> list[tuple[PointOfInterest, MapHex]]:
        stmt = (
            select(PointOfInterest, MapHex)
            .join(MapHex, PointOfInterest.hex_id == MapHex.id)
            .where(MapHex.map_version_id == map_version_id)
            .order_by(PointOfInterest.id)
        )
        return list(self.db.execute(stmt).all())

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
