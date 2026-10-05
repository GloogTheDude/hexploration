from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    CharacterMapHexObservation,
    Expedition,
    MapArea,
    MapEdge,
    MapFeature,
    MapHex,
    MapVersion,
    Movement,
    PointOfInterest,
    WorldMap,
)
from models.constants import BASE_TERRAINS
from models.hexmap import Hexmap
from services.errors import ConflictError, NotFoundError
from services.map_feature_service import MapFeatureService


class MapPersistenceError(Exception):
    pass


class MapPersistenceService:
    """Persist campaign-owned map editor operations.

    The editor formerly synchronized through a process-global ``Hexmap``.
    Changes now go directly to the campaign-owned map version.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _terrain_payload(version_id: int, q: int, r: int, terrain_key: str) -> dict:
        terrain = BASE_TERRAINS.get(terrain_key)
        if terrain is None:
            raise ValueError(f"Unknown terrain: {terrain_key}")
        return {
            "map_version_id": version_id,
            "q": q,
            "r": r,
            "terrain_key": terrain_key,
            "elevation": terrain.elevation,
            "visibility_score": terrain.visibility_score,
            "travel_cost": terrain.travel_cost,
            "extra_data": {},
        }

    @staticmethod
    def _coord_in_version(version: MapVersion, q: int, r: int) -> bool:
        col, row = Hexmap.axial_to_offset(q, r, version.width, version.height)
        return 0 <= col < version.width and 0 <= row < version.height

    def _map_version(self, map_id: int, map_version_id: int) -> tuple[WorldMap, MapVersion]:
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        version = self.db.get(MapVersion, map_version_id)
        if version is None or version.map_id != map_id:
            raise NotFoundError("Map version not found")
        return world_map, version

    def _assert_mutable(self, version: MapVersion) -> None:
        child = self.db.scalar(
            select(MapVersion.id).where(MapVersion.parent_version_id == version.id).limit(1)
        )
        movement = self.db.scalar(
            select(Movement.id).where(Movement.map_version_id == version.id).limit(1)
        )
        expedition = self.db.scalar(
            select(Expedition.id)
            .where(Expedition.current_map_version_id == version.id)
            .limit(1)
        )
        observation = self.db.scalar(
            select(CharacterMapHexObservation.id)
            .where(CharacterMapHexObservation.map_version_id == version.id)
            .limit(1)
        )
        if any(value is not None for value in (child, movement, expedition, observation)):
            raise ConflictError(
                "This map version already participates in campaign history; create a new version instead"
            )

    def create_map(
        self,
        *,
        campaign_id: int,
        name: str,
        description: str | None,
        version_name: str | None,
        effective_from_game_minute: int,
        width: int,
        height: int,
        hex_size: int,
    ) -> tuple[WorldMap, MapVersion, int]:
        if self.db.get(Campaign, campaign_id) is None:
            raise NotFoundError("Campaign not found")
        if effective_from_game_minute < 0:
            raise ValueError("effective_from_game_minute must be >= 0")
        if not 1 <= width <= 10_000 or not 1 <= height <= 10_000:
            raise ValueError("Map dimensions must be between 1 and 10,000")
        if not 8 <= hex_size <= 96:
            raise ValueError("hex_size must be between 8 and 96 pixels")
        if not name.strip():
            raise ValueError("Map name must contain non-whitespace characters")

        world_map = WorldMap(campaign_id=campaign_id, name=name.strip(), description=description)
        self.db.add(world_map)
        self.db.flush()
        version = MapVersion(
            map_id=world_map.id,
            version=1,
            name=version_name,
            width=width,
            height=height,
            hex_size=hex_size,
            default_terrain_key="SEA",
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)
        return world_map, version, width * height

    def paint_hexes(
        self,
        *,
        campaign_id: int,
        map_id: int,
        map_version_id: int,
        centers: list[tuple[int, int]],
        terrain_key: str,
        radius: int,
    ) -> list[MapHex]:
        world_map, version = self._map_version(map_id, map_version_id)
        if world_map.campaign_id != campaign_id:
            raise ConflictError("Map does not belong to this campaign")
        if radius < 1 or radius > 25:
            raise ValueError("Brush radius must be between 1 and 25")
        if terrain_key not in BASE_TERRAINS:
            raise ValueError(f"Unknown terrain: {terrain_key}")
        self._assert_mutable(version)

        coords: set[tuple[int, int]] = set()
        distance = radius - 1
        for q, r in centers:
            for dq in range(-distance, distance + 1):
                for dr in range(-distance, distance + 1):
                    if (abs(dq) + abs(dr) + abs(dq + dr)) // 2 <= distance:
                        candidate = (q + dq, r + dr)
                        if self._coord_in_version(version, *candidate):
                            coords.add(candidate)

        existing = {
            (row.q, row.r): row
            for row in self.db.scalars(
                select(MapHex).where(MapHex.map_version_id == version.id)
            )
            if (row.q, row.r) in coords
        }
        for q, r in coords:
            row = existing.get((q, r))
            if terrain_key == version.default_terrain_key:
                if row is not None:
                    self.db.delete(row)
                continue
            payload = self._terrain_payload(version.id, q, r, terrain_key)
            if row is None:
                self.db.add(MapHex(**payload))
            else:
                for key, value in payload.items():
                    if key != "map_version_id":
                        setattr(row, key, value)
        self.db.commit()
        return list(
            self.db.scalars(
                select(MapHex)
                .where(MapHex.map_version_id == version.id)
                .order_by(MapHex.q, MapHex.r)
            )
        )

    def update_version_metadata(
        self,
        *,
        map_id: int,
        map_version_id: int,
        map_name: str | None,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int]:
        world_map, version = self._map_version(map_id, map_version_id)
        self._assert_mutable(version)
        parent = self.db.get(MapVersion, version.parent_version_id) if version.parent_version_id else None
        if parent is not None and effective_from_game_minute <= parent.effective_from_game_minute:
            raise ConflictError("A map version must become effective after its parent")
        if map_name is not None:
            if not map_name.strip():
                raise ValueError("Map name must contain non-whitespace characters")
            world_map.name = map_name.strip()
        version.name = version_name
        version.effective_from_game_minute = effective_from_game_minute
        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)
        hex_count = version.width * version.height if version.default_terrain_key else self.db.scalar(
            select(func.count(MapHex.id)).where(MapHex.map_version_id == version.id)
        )
        return world_map, version, int(hex_count or 0)

    def clone_map_version(
        self,
        *,
        map_id: int,
        parent_version_id: int,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int, int, int]:
        world_map, parent = self._map_version(map_id, parent_version_id)
        if effective_from_game_minute <= parent.effective_from_game_minute:
            raise ConflictError("A new map version must become effective after its parent")
        latest = self.db.scalar(
            select(MapVersion.version)
            .where(MapVersion.map_id == map_id)
            .order_by(MapVersion.version.desc())
            .limit(1)
        ) or 0
        version = MapVersion(
            map_id=map_id,
            parent_version_id=parent.id,
            version=latest + 1,
            name=version_name,
            width=parent.width,
            height=parent.height,
            hex_size=parent.hex_size,
            default_terrain_key=parent.default_terrain_key,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()
        parent_hexes = list(self.db.scalars(select(MapHex).where(MapHex.map_version_id == parent.id)))
        for row in parent_hexes:
            self.db.add(MapHex(
                map_version_id=version.id,
                q=row.q,
                r=row.r,
                terrain_key=row.terrain_key,
                elevation=row.elevation,
                visibility_score=row.visibility_score,
                travel_cost=row.travel_cost,
                extra_data=dict(row.extra_data or {}),
            ))
        self.db.flush()
        new_hexes = {
            (row.q, row.r): row
            for row in self.db.scalars(select(MapHex).where(MapHex.map_version_id == version.id))
        }
        features = list(self.db.scalars(select(MapFeature).where(MapFeature.map_id == map_id)))
        feature_service = MapFeatureService(self.db)
        for feature in features:
            identity = feature_service.ensure(
                campaign_id=world_map.campaign_id,
                map_id=map_id,
                feature_type=feature.feature_type,
                feature_id=feature.feature_id,
            )
            identity.downstream_feature_type = feature.downstream_feature_type
            identity.downstream_feature_id = feature.downstream_feature_id
        pois = list(
            self.db.execute(
                select(PointOfInterest, MapHex)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(MapHex.map_version_id == parent.id)
            ).all()
        )
        for poi, old_hex in pois:
            new_hex = new_hexes.get((old_hex.q, old_hex.r))
            if new_hex is None:
                raise ConflictError(f"Cannot clone POI {poi.name}: its supporting hex is absent")
            self.db.add(PointOfInterest(
                feature_id=poi.feature_id,
                hex_id=new_hex.id,
                name=poi.name,
                kind=poi.kind,
                dm_description=poi.dm_description,
                player_description=poi.player_description,
                requires_discovery=poi.requires_discovery,
                is_landmark=poi.is_landmark,
                is_hub=poi.is_hub,
            ))
        edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == parent.id)))
        for edge in edges:
            self.db.add(MapEdge(
                map_version_id=version.id,
                from_q=edge.from_q,
                from_r=edge.from_r,
                to_q=edge.to_q,
                to_r=edge.to_r,
                feature_type=edge.feature_type,
                feature_id=edge.feature_id,
                segment_index=edge.segment_index,
                name=edge.name,
                extra_data=dict(edge.extra_data or {}),
            ))
        areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == parent.id)))
        for area in areas:
            self.db.add(MapArea(
                map_version_id=version.id,
                feature_type=area.feature_type,
                feature_id=area.feature_id,
                name=area.name,
                cells=list(area.cells or []),
                extra_data=dict(area.extra_data or {}),
            ))
        self.db.commit()
        self.db.refresh(version)
        return world_map, version, version.width * version.height, len(pois), len(edges)
