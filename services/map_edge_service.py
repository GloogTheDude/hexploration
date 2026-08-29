from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import MapEdge
from dto.map_edge_dto import MapEdgeCreate
from repositories.map_edge_repository import (
    MapEdgeRepository,
    canonical_edge_coordinates,
)
from services.errors import ConflictError, NotFoundError


def axial_hex_distance(q1: int, r1: int, q2: int, r2: int) -> int:
    return (
        abs(q1 - q2)
        + abs(q1 + r1 - q2 - r2)
        + abs(r1 - r2)
    ) // 2


class MapEdgeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MapEdgeRepository(db)

    def create(self, map_version_id: int, data: MapEdgeCreate) -> MapEdge:
        map_version = self.repo.get_map_version(map_version_id)
        if map_version is None:
            raise NotFoundError("Map version not found")

        if axial_hex_distance(data.from_q, data.from_r, data.to_q, data.to_r) != 1:
            raise ValueError("A map edge must connect two adjacent hexes")

        source = self.repo.get_hex(map_version_id, data.from_q, data.from_r)
        destination = self.repo.get_hex(map_version_id, data.to_q, data.to_r)
        if source is None or destination is None:
            raise NotFoundError("Both edge endpoints must exist in the map version")

        from_q, from_r, to_q, to_r = canonical_edge_coordinates(
            data.from_q,
            data.from_r,
            data.to_q,
            data.to_r,
        )

        if self.repo.get_between(map_version_id, from_q, from_r, to_q, to_r):
            raise ConflictError("An edge already exists between these hexes")

        edge = MapEdge(
            map_version_id=map_version_id,
            from_q=from_q,
            from_r=from_r,
            to_q=to_q,
            to_r=to_r,
            feature_type=data.feature_type.strip().upper(),
            feature_id=data.feature_id,
            name=data.name,
            extra_data=dict(data.extra_data),
        )

        try:
            self.repo.add(edge)
            self.db.commit()
            self.db.refresh(edge)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("An edge already exists between these hexes") from exc

        return edge

    def get(self, edge_id: int) -> MapEdge:
        edge = self.repo.get(edge_id)
        if edge is None:
            raise NotFoundError("Map edge not found")
        return edge

    def list_for_map_version(self, map_version_id: int) -> list[MapEdge]:
        if self.repo.get_map_version(map_version_id) is None:
            raise NotFoundError("Map version not found")
        return self.repo.list_for_map_version(map_version_id)

    def delete(self, edge_id: int) -> None:
        edge = self.get(edge_id)
        self.repo.delete(edge)
        self.db.commit()
