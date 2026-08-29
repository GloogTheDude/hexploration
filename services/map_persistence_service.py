from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import Campaign, MapEdge, MapHex, MapVersion, PointOfInterest, WorldMap
from models.constants import BASE_TERRAINS
from models.hexmap import Hexmap
from models.terrain import Terrain
from services.errors import ConflictError, NotFoundError
from services.map_feature_service import MapFeatureService


class MapPersistenceError(Exception):
    pass


class MapPersistenceService:
    """Bridge between the in-memory terrain editor and persistent map versions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.features = MapFeatureService(db)

    @staticmethod
    def _terrain_key(terrain: object) -> str:
        for key, known in BASE_TERRAINS.items():
            if terrain is known:
                return key
        terrain_type = getattr(terrain, "type", None)
        if terrain_type is not None:
            for key, known in BASE_TERRAINS.items():
                if getattr(known, "type", None) == terrain_type:
                    return key
        raise MapPersistenceError(f"Unable to resolve terrain key for terrain {terrain!r}")

    @staticmethod
    def _visibility_score(terrain: object) -> int:
        if not hasattr(terrain, "visibility_score"):
            raise MapPersistenceError(f"Terrain {terrain!r} has no visibility_score attribute")
        value = int(getattr(terrain, "visibility_score"))
        if value < 0:
            raise MapPersistenceError("Terrain visibility_score must be >= 0")
        return value

    @staticmethod
    def _travel_cost(terrain: object) -> float:
        if not hasattr(terrain, "travel_cost"):
            raise MapPersistenceError(f"Terrain {terrain!r} has no travel_cost attribute")
        value = float(getattr(terrain, "travel_cost"))
        if value <= 0:
            raise MapPersistenceError("Terrain travel_cost must be greater than 0")
        return value

    def _snapshot_hexes(self, version: MapVersion) -> dict[tuple[int, int], MapHex]:
        import routes.map_routes as map_routes
        editor_map = map_routes.hexmap
        by_coord: dict[tuple[int, int], MapHex] = {}
        for editor_hex in editor_map.hexes.values():
            terrain = editor_hex.terrain
            row = MapHex(
                map_version_id=version.id,
                q=editor_hex.q,
                r=editor_hex.r,
                terrain_key=self._terrain_key(terrain),
                elevation=int(getattr(terrain, "elevation", 0)),
                visibility_score=self._visibility_score(terrain),
                travel_cost=self._travel_cost(terrain),
                extra_data={},
            )
            self.db.add(row)
            self.db.flush()
            by_coord[(row.q, row.r)] = row
        return by_coord

    def snapshot_current_editor_map(
        self,
        *,
        campaign_id: int,
        name: str,
        description: str | None,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int]:
        if self.db.get(Campaign, campaign_id) is None:
            raise NotFoundError("Campaign not found")
        import routes.map_routes as map_routes
        editor_map = map_routes.hexmap
        world_map = WorldMap(campaign_id=campaign_id, name=name.strip(), description=description)
        self.db.add(world_map)
        self.db.flush()
        version = MapVersion(
            map_id=world_map.id,
            parent_version_id=None,
            version=1,
            name=version_name,
            width=editor_map.width,
            height=editor_map.height,
            hex_size=editor_map.hex_size,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()
        hexes = self._snapshot_hexes(version)
        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)
        return world_map, version, len(hexes)

    def load_version_into_editor(self, map_version_id: int) -> tuple[WorldMap, MapVersion, int]:
        version = self.db.get(MapVersion, map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        persisted = list(self.db.scalars(select(MapHex).where(MapHex.map_version_id == version.id)))
        editor = Hexmap(version.width, version.height, version.hex_size)
        for row in persisted:
            base_terrain = BASE_TERRAINS.get(row.terrain_key)
            if base_terrain is None:
                raise MapPersistenceError(f"Unknown persisted terrain: {row.terrain_key}")
            tile = editor.get_hex(row.q, row.r)
            if tile is None:
                raise MapPersistenceError(f"Persisted hex ({row.q},{row.r}) is outside editor dimensions")
            # Rehydrate the frozen version values instead of replacing them with
            # whatever the current global terrain defaults happen to be.
            tile.terrain = Terrain(
                type=base_terrain.type,
                color=base_terrain.color,
                visibility_score=row.visibility_score,
                elevation=row.elevation,
                travel_cost=row.travel_cost,
            )
        import routes.map_routes as map_routes
        map_routes.hexmap = editor
        return world_map, version, len(persisted)

    def snapshot_new_version_from_editor(
        self,
        *,
        map_id: int,
        parent_version_id: int,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int, int, int]:
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        parent = self.db.get(MapVersion, parent_version_id)
        if parent is None or parent.map_id != map_id:
            raise NotFoundError("Parent map version not found")
        if effective_from_game_minute <= parent.effective_from_game_minute:
            raise ConflictError(
                "A new map version must become effective after its parent version"
            )

        import routes.map_routes as map_routes
        editor_map = map_routes.hexmap
        next_version = (self.db.scalar(select(func.max(MapVersion.version)).where(MapVersion.map_id == map_id)) or 0) + 1
        version = MapVersion(
            map_id=map_id,
            parent_version_id=parent.id,
            version=next_version,
            name=version_name,
            width=editor_map.width,
            height=editor_map.height,
            hex_size=editor_map.hex_size,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()
        new_hexes = self._snapshot_hexes(version)

        parent_pois = list(
            self.db.execute(
                select(PointOfInterest, MapHex)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(MapHex.map_version_id == parent.id)
            ).all()
        )
        for poi, old_hex in parent_pois:
            new_hex = new_hexes.get((old_hex.q, old_hex.r))
            if new_hex is None:
                self.db.rollback()
                raise ConflictError(
                    f"Cannot remove hex ({old_hex.q},{old_hex.r}): it carries POI {poi.name}"
                )
            self.features.ensure(
                campaign_id=world_map.campaign_id,
                map_id=world_map.id,
                feature_type="POI",
                feature_id=poi.feature_id,
            )
            self.db.add(PointOfInterest(
                feature_id=poi.feature_id,
                hex_id=new_hex.id,
                name=poi.name,
                kind=poi.kind,
                dm_description=poi.dm_description,
                is_landmark=poi.is_landmark,
            ))

        parent_edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == parent.id)))
        for edge in parent_edges:
            if (edge.from_q, edge.from_r) not in new_hexes or (edge.to_q, edge.to_r) not in new_hexes:
                self.db.rollback()
                raise ConflictError(
                    f"Cannot remove an endpoint of {edge.feature_type} #{edge.feature_id}"
                )
            self.features.ensure(
                campaign_id=world_map.campaign_id,
                map_id=world_map.id,
                feature_type=edge.feature_type,
                feature_id=edge.feature_id,
            )
            self.db.add(MapEdge(
                map_version_id=version.id,
                from_q=edge.from_q,
                from_r=edge.from_r,
                to_q=edge.to_q,
                to_r=edge.to_r,
                feature_type=edge.feature_type,
                feature_id=edge.feature_id,
                name=edge.name,
                extra_data=dict(edge.extra_data or {}),
            ))

        self.db.commit()
        self.db.refresh(version)
        return world_map, version, len(new_hexes), len(parent_pois), len(parent_edges)
