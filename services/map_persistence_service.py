from __future__ import annotations

from sqlalchemy import delete, func, insert, select, tuple_, update
from sqlalchemy.orm import Session

from db.models import (
    Campaign, CharacterMapHexObservation, Expedition, MapArea, MapEdge, MapHex, MapVersion,
    Movement, PointOfInterest, WorldMap,
)
from models.constants import BASE_TERRAINS
from models.hexmap import Hexmap
from models.hex import Hex
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

    @staticmethod
    def _hex_payload(version_id: int, editor_hex) -> dict:
        terrain = editor_hex.terrain
        return {
            "map_version_id": version_id,
            "q": editor_hex.q,
            "r": editor_hex.r,
            "terrain_key": MapPersistenceService._terrain_key(terrain),
            "elevation": int(getattr(terrain, "elevation", 0)),
            "visibility_score": MapPersistenceService._visibility_score(terrain),
            "travel_cost": MapPersistenceService._travel_cost(terrain),
            "extra_data": {},
        }

    def _snapshot_hexes(self, version: MapVersion, *, batch_size: int = 5000) -> int:
        """Bulk-copy the editor grid into a persisted version.

        The old implementation flushed once per hex, which becomes extremely
        expensive on 100x100+ maps.  Executemany batches keep transaction and
        ORM overhead bounded even for hundreds of thousands of cells.
        """
        import routes.map_routes as map_routes
        editor_map = map_routes.hexmap
        batch: list[dict] = []
        count = 0
        for editor_hex in editor_map.hexes.values():
            batch.append(self._hex_payload(version.id, editor_hex))
            if len(batch) >= batch_size:
                self.db.execute(insert(MapHex), batch)
                count += len(batch)
                batch.clear()
        if batch:
            self.db.execute(insert(MapHex), batch)
            count += len(batch)
        self.db.flush()
        return count

    @staticmethod
    def _mark_editor_synced(version_id: int) -> None:
        import routes.map_routes as map_routes
        map_routes.editor_source_version_id = version_id
        map_routes.editor_source_map_identity = id(map_routes.hexmap)
        map_routes.clear_dirty_hexes()

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
            default_terrain_key=editor_map.default_terrain_key,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()
        self._snapshot_hexes(version)
        hex_count = editor_map.width * editor_map.height
        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)
        self._mark_editor_synced(version.id)
        return world_map, version, hex_count

    def load_version_into_editor(self, map_version_id: int) -> tuple[WorldMap, MapVersion, int]:
        version = self.db.get(MapVersion, map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        persisted = list(self.db.scalars(select(MapHex).where(MapHex.map_version_id == version.id)))

        # Rebuild the editor from the exact persisted coordinate set instead of
        # assuming the current generator footprint.  This keeps legacy
        # axial-rectangle versions loadable after new maps switched to a
        # rectangular odd-q footprint.
        editor = Hexmap(version.width, version.height, version.hex_size, hexes={})
        for row in persisted:
            base_terrain = BASE_TERRAINS.get(row.terrain_key)
            if base_terrain is None:
                raise MapPersistenceError(f"Unknown persisted terrain: {row.terrain_key}")
            tile = Hex(
                row.q,
                row.r,
                Terrain(
                    type=base_terrain.type,
                    color=base_terrain.color,
                    visibility_score=row.visibility_score,
                    elevation=row.elevation,
                    travel_cost=row.travel_cost,
                ),
            )
            editor.hexes[tile.key] = tile
        import routes.map_routes as map_routes
        if version.default_terrain_key:
            editor.default_terrain_key = version.default_terrain_key
            editor.sparse = True
            editor.layout = "even-q-rect"
        else:
            # Legacy versions were dense. Their exact stored coordinates remain
            # authoritative and are still rendered through the compatibility path.
            expected_count = version.width * version.height
            editor.sparse = False
            editor.layout = "even-q-rect" if len(persisted) == expected_count else "axial-legacy"
        map_routes.hexmap = editor
        map_routes.editor_source_version_id = version.id
        map_routes.editor_source_map_identity = id(editor)
        map_routes.clear_dirty_hexes()
        return world_map, version, (version.width * version.height if version.default_terrain_key else len(persisted))

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
            default_terrain_key=editor_map.default_terrain_key,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()
        self._snapshot_hexes(version)
        hex_count = editor_map.width * editor_map.height

        parent_pois = list(
            self.db.execute(
                select(PointOfInterest, MapHex)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(MapHex.map_version_id == parent.id)
            ).all()
        )
        for poi, old_hex in parent_pois:
            if editor_map.get_hex(old_hex.q, old_hex.r) is None:
                self.db.rollback()
                raise ConflictError(
                    f"Cannot remove hex ({old_hex.q},{old_hex.r}): it carries POI {poi.name}"
                )
            new_hex = self.db.scalar(
                select(MapHex).where(
                    MapHex.map_version_id == version.id,
                    MapHex.q == old_hex.q,
                    MapHex.r == old_hex.r,
                )
            )
            if new_hex is None:
                # Sparse versions only persist overrides. A POI needs a concrete
                # MapHex FK, so materialise its otherwise-default supporting tile.
                support = editor_map.get_hex(old_hex.q, old_hex.r)
                self.db.execute(insert(MapHex), [self._hex_payload(version.id, support)])
                self.db.flush()
                new_hex = self.db.scalar(
                    select(MapHex).where(
                        MapHex.map_version_id == version.id,
                        MapHex.q == old_hex.q,
                        MapHex.r == old_hex.r,
                    )
                )
                if new_hex is None:
                    self.db.rollback()
                    raise MapPersistenceError("POI support hex could not be materialized")
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
                player_description=poi.player_description,
                requires_discovery=poi.requires_discovery,
                is_landmark=poi.is_landmark,
                is_hub=poi.is_hub,
            ))

        parent_edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == parent.id)))
        for edge in parent_edges:
            if editor_map.get_hex(edge.from_q, edge.from_r) is None or editor_map.get_hex(edge.to_q, edge.to_r) is None:
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
                segment_index=edge.segment_index,
                name=edge.name,
                extra_data=dict(edge.extra_data or {}),
            ))

        parent_areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == parent.id)))
        for area in parent_areas:
            valid_cells = []
            for cell in area.cells or []:
                q, r = int(cell["q"]), int(cell["r"])
                if editor_map.get_hex(q, r) is None:
                    self.db.rollback()
                    raise ConflictError(f"Cannot remove a cell of {area.feature_type} #{area.feature_id}")
                valid_cells.append({"q": q, "r": r})
            self.features.ensure(campaign_id=world_map.campaign_id, map_id=world_map.id, feature_type=area.feature_type, feature_id=area.feature_id)
            self.db.add(MapArea(map_version_id=version.id, feature_type=area.feature_type, feature_id=area.feature_id, name=area.name, cells=valid_cells, extra_data=dict(area.extra_data or {})))

        self.db.commit()
        self.db.refresh(version)
        self._mark_editor_synced(version.id)
        return world_map, version, hex_count, len(parent_pois), len(parent_edges)
    def update_version_from_editor(
        self,
        *,
        map_id: int,
        map_version_id: int,
        map_name: str | None,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int]:
        """Update an unused leaf version, writing only painted cells when possible."""
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        version = self.db.get(MapVersion, map_version_id)
        if version is None or version.map_id != map_id:
            raise NotFoundError("Map version not found")

        child = self.db.scalar(select(MapVersion.id).where(MapVersion.parent_version_id == version.id).limit(1))
        movement = self.db.scalar(select(Movement.id).where(Movement.map_version_id == version.id).limit(1))
        expedition = self.db.scalar(select(Expedition.id).where(Expedition.current_map_version_id == version.id).limit(1))
        observation = self.db.scalar(select(CharacterMapHexObservation.id).where(CharacterMapHexObservation.map_version_id == version.id).limit(1))
        if any(value is not None for value in (child, movement, expedition, observation)):
            raise ConflictError(
                "This map version already participates in campaign history; create a new version instead"
            )

        import routes.map_routes as map_routes
        editor_map = map_routes.hexmap
        if editor_map.width != version.width or editor_map.height != version.height:
            raise ConflictError("Changing map dimensions requires creating a new map")

        tracked = (
            map_routes.editor_source_version_id == version.id
            and map_routes.editor_source_map_identity == id(editor_map)
        )
        dirty = set(map_routes.dirty_hex_coords) if tracked else set(editor_map.hexes)
        # set(editor_map.hexes) contains string keys in fallback mode; normalize it.
        if not tracked:
            dirty = {(h.q, h.r) for h in editor_map.hexes.values()}

        if dirty:
            rows = self.db.execute(
                select(MapHex.id, MapHex.q, MapHex.r).where(
                    MapHex.map_version_id == version.id,
                    tuple_(MapHex.q, MapHex.r).in_(dirty),
                )
            ).all()
            ids = {(q, r): row_id for row_id, q, r in rows}
            updates: list[dict] = []
            inserts: list[dict] = []
            deletes: list[int] = []
            for coord in dirty:
                row_id = ids.get(coord)
                editor_hex = editor_map.hexes.get(f"{coord[0]},{coord[1]}")
                if editor_hex is None:
                    # Sparse/default terrain is represented by absence, not by a
                    # materialized default row. This also makes Ctrl+Z restore
                    # sparsity when a painted cell is undone back to default.
                    if row_id is not None:
                        deletes.append(row_id)
                    continue
                payload = self._hex_payload(version.id, editor_hex)
                if row_id is None:
                    inserts.append(payload)
                else:
                    payload.pop("map_version_id", None)
                    payload["id"] = row_id
                    updates.append(payload)
            if deletes:
                self.db.execute(delete(MapHex).where(MapHex.id.in_(deletes)))
            if updates:
                self.db.execute(update(MapHex), updates)
            if inserts:
                self.db.execute(insert(MapHex), inserts)

        if map_name is not None:
            world_map.name = map_name.strip()
        version.name = version_name
        version.hex_size = editor_map.hex_size
        version.effective_from_game_minute = effective_from_game_minute

        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)
        self._mark_editor_synced(version.id)
        return world_map, version, version.width * version.height

