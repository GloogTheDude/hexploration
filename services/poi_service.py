from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from db.models import MapHex, MapVersion, PointOfInterest, WorldEvent, WorldMap
from dto.poi_dto import POICreate
from repositories.poi_repository import POIRepository
from services.errors import ForbiddenOperationError, NotFoundError
from services.map_feature_service import MapFeatureService
from services.world_event_service import WorldEventService

POI_EVENT_TYPES = {"POI_CREATED", "POI_STATE_CHANGED", "POI_DAMAGED", "POI_DESTROYED", "POI_REBUILT", "POI_OCCUPIED", "POI_ABANDONED"}
DEFAULT_POI_STATE = "ACTIVE"

@dataclass(frozen=True)
class ResolvedPOIState:
    poi: PointOfInterest
    game_minute: int
    state: str
    exists: bool
    latest_event: WorldEvent | None

class POIService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = POIRepository(db)
        self.world = WorldEventService(db)
        self.features = MapFeatureService(db)

    def _context_for_hex(self, hex_id: int) -> tuple[MapHex, MapVersion, WorldMap]:
        hex_tile = self.repo.get_hex(hex_id)
        if hex_tile is None:
            raise NotFoundError("Map hex not found")
        version = self.db.get(MapVersion, hex_tile.map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        return hex_tile, version, world_map

    def create(self, data: POICreate):
        _, _, world_map = self._context_for_hex(data.hex_id)
        identity = self.features.allocate(
            campaign_id=world_map.campaign_id,
            map_id=world_map.id,
            feature_type="POI",
        )
        poi = PointOfInterest(feature_id=identity.feature_id, **data.model_dump())
        self.repo.add(poi)
        self.db.commit()
        self.db.refresh(poi)
        return poi

    def get(self, poi_id: int):
        poi = self.repo.get(poi_id)
        if poi is None:
            raise NotFoundError("POI not found")
        return poi

    def list_for_map_version(self, map_version_id: int):
        return self.repo.list_for_map_version(map_version_id)

    def state_at(self, poi_id: int, *, campaign_id: int, game_minute: int):
        poi = self.get(poi_id)
        _, _, world_map = self._context_for_hex(poi.hex_id)
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("POI does not belong to this campaign")
        if game_minute < 0:
            raise ValueError("game_minute must be >= 0")
        event = self.world.repo.latest_target_event_of_types(
            campaign_id,
            game_minute=game_minute,
            target_type="POI",
            target_id=poi.feature_id,
            event_types=POI_EVENT_TYPES,
        )
        if event is None:
            return ResolvedPOIState(poi, game_minute, DEFAULT_POI_STATE, True, None)
        if event.event_type == "POI_DESTROYED":
            state, exists = "DESTROYED", False
        elif event.event_type in {"POI_CREATED", "POI_REBUILT"}:
            state, exists = "ACTIVE", True
        elif event.event_type == "POI_STATE_CHANGED":
            state = str(event.payload.get("state", DEFAULT_POI_STATE)).upper()
            exists = state != "DESTROYED"
        else:
            state, exists = event.event_type.removeprefix("POI_"), True
        return ResolvedPOIState(poi, game_minute, state, exists, event)
