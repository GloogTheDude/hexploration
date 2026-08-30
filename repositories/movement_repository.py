from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    Character,
    Expedition,
    ExpeditionCharacter,
    MapEdge,
    MapHex,
    MapVersion,
    Movement,
    WorldMap,
)


class MovementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_expedition_for_update(self, expedition_id: int) -> Expedition | None:
        stmt = (
            select(Expedition)
            .where(Expedition.id == expedition_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def get_map_version(self, map_version_id: int) -> MapVersion | None:
        return self.db.get(MapVersion, map_version_id)

    def get_world_map(self, map_id: int) -> WorldMap | None:
        return self.db.get(WorldMap, map_id)

    def get_hex(self, map_version_id: int, q: int, r: int) -> MapHex | None:
        stmt = select(MapHex).where(
            MapHex.map_version_id == map_version_id,
            MapHex.q == q,
            MapHex.r == r,
        )
        return self.db.scalar(stmt)


    def get_edges_between(
        self,
        map_version_id: int,
        q1: int,
        r1: int,
        q2: int,
        r2: int,
    ) -> list[MapEdge]:
        a = (q1, r1)
        b = (q2, r2)
        if a <= b:
            from_q, from_r, to_q, to_r = q1, r1, q2, r2
        else:
            from_q, from_r, to_q, to_r = q2, r2, q1, r1

        stmt = (
            select(MapEdge)
            .where(
                MapEdge.map_version_id == map_version_id,
                MapEdge.from_q == from_q,
                MapEdge.from_r == from_r,
                MapEdge.to_q == to_q,
                MapEdge.to_r == to_r,
            )
            .order_by(MapEdge.feature_type, MapEdge.feature_id, MapEdge.segment_index, MapEdge.id)
        )
        return list(self.db.scalars(stmt))

    def get_edge_between(
        self,
        map_version_id: int,
        q1: int,
        r1: int,
        q2: int,
        r2: int,
    ) -> MapEdge | None:
        # Compatibility helper for older callers; overlapping semantic features
        # are represented by get_edges_between().
        edges = self.get_edges_between(map_version_id, q1, r1, q2, r2)
        return edges[0] if edges else None

    def add_movement(self, movement: Movement) -> Movement:
        self.db.add(movement)
        self.db.flush()
        return movement

    def list_movements(self, expedition_id: int) -> list[Movement]:
        stmt = (
            select(Movement)
            .where(Movement.expedition_id == expedition_id)
            .order_by(Movement.departure_game_minute, Movement.id)
        )
        return list(self.db.scalars(stmt))

    def active_participants(
        self,
        expedition_id: int,
    ) -> list[ExpeditionCharacter]:
        stmt = select(ExpeditionCharacter).where(
            ExpeditionCharacter.expedition_id == expedition_id,
            ExpeditionCharacter.left_game_minute.is_(None),
        )
        return list(self.db.scalars(stmt))

    def get_character(self, character_id: int) -> Character | None:
        return self.db.get(Character, character_id)
