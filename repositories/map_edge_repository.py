from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MapEdge, MapHex, MapVersion, WorldMap


def canonical_edge_coordinates(
    q1: int,
    r1: int,
    q2: int,
    r2: int,
) -> tuple[int, int, int, int]:
    a = (q1, r1)
    b = (q2, r2)
    if a <= b:
        return q1, r1, q2, r2
    return q2, r2, q1, r1


class MapEdgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

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

    def get(self, edge_id: int) -> MapEdge | None:
        return self.db.get(MapEdge, edge_id)

    def get_between(
        self,
        map_version_id: int,
        q1: int,
        r1: int,
        q2: int,
        r2: int,
        *,
        feature_type: str | None = None,
        feature_id: int | None = None,
    ) -> MapEdge | None:
        from_q, from_r, to_q, to_r = canonical_edge_coordinates(
            q1, r1, q2, r2
        )
        stmt = select(MapEdge).where(
            MapEdge.map_version_id == map_version_id,
            MapEdge.from_q == from_q,
            MapEdge.from_r == from_r,
            MapEdge.to_q == to_q,
            MapEdge.to_r == to_r,
        )
        if feature_type is not None:
            stmt = stmt.where(MapEdge.feature_type == feature_type.strip().upper())
        if feature_id is not None:
            stmt = stmt.where(MapEdge.feature_id == feature_id)
        return self.db.scalar(stmt)

    def list_for_map_version(self, map_version_id: int) -> list[MapEdge]:
        stmt = (
            select(MapEdge)
            .where(MapEdge.map_version_id == map_version_id)
            .order_by(MapEdge.id)
        )
        return list(self.db.scalars(stmt))

    def add(self, edge: MapEdge) -> MapEdge:
        self.db.add(edge)
        self.db.flush()
        return edge

    def delete(self, edge: MapEdge) -> None:
        self.db.delete(edge)
