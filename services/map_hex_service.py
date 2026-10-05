from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MapHex, MapVersion
from models.constants import BASE_TERRAINS
from models.hexmap import Hexmap


def contains(version: MapVersion, q: int, r: int) -> bool:
    col, row = Hexmap.axial_to_offset(q, r, version.width, version.height)
    return 0 <= col < version.width and 0 <= row < version.height


def get_or_materialize_hex(db: Session, version: MapVersion, q: int, r: int) -> MapHex | None:
    row = db.scalar(
        select(MapHex).where(
            MapHex.map_version_id == version.id,
            MapHex.q == q,
            MapHex.r == r,
        )
    )
    if row is not None:
        return row
    if not version.default_terrain_key or not contains(version, q, r):
        return None
    terrain = BASE_TERRAINS[version.default_terrain_key]
    row = MapHex(
        map_version_id=version.id,
        q=q,
        r=r,
        terrain_key=version.default_terrain_key,
        elevation=terrain.elevation,
        visibility_score=terrain.visibility_score,
        travel_cost=terrain.travel_cost,
        extra_data={},
    )
    db.add(row)
    db.flush()
    return row


def materialize_radius(
    db: Session,
    version: MapVersion,
    origin_q: int,
    origin_r: int,
    radius: int,
) -> list[MapHex]:
    rows: list[MapHex] = []
    for dq in range(-radius, radius + 1):
        for dr in range(-radius, radius + 1):
            if (abs(dq) + abs(dq + dr) + abs(dr)) // 2 > radius:
                continue
            tile = get_or_materialize_hex(db, version, origin_q + dq, origin_r + dr)
            if tile is not None:
                rows.append(tile)
    return rows
