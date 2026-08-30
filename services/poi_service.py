from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from db.models import MapHex, MapVersion, PointOfInterest, WorldEvent, WorldMap
from dto.poi_dto import POICreate
from repositories.poi_repository import POIRepository
from services.errors import ForbiddenOperationError, NotFoundError
from services.map_feature_service import MapFeatureService
from services.world_event_service import WorldEventService

POI_EVENT_TYPES = {"POI_CREATED", "POI_STATE_CHANGED", "POI_VISIBILITY_CHANGED", "POI_DAMAGED", "POI_DESTROYED", "POI_REBUILT", "POI_OCCUPIED", "POI_ABANDONED"}
DEFAULT_POI_STATE = "ACTIVE"

@dataclass(frozen=True)
class ResolvedPOIState:
    poi: PointOfInterest
    game_minute: int
    state: str
    exists: bool
    visible_at_distance: bool
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
        # State and long-distance visibility are independent temporal properties.
        # Fold the complete target timeline instead of looking only at the latest
        # event: a visibility change must not erase the previously resolved
        # physical state (and vice versa).
        # Fetch the complete target timeline first.  A POI without an explicit
        # POI_CREATED event keeps the legacy behaviour (it exists from minute 0).
        # Once a POI_CREATED event exists, however, the POI is absent before its
        # first creation date.  This lets DMs model settlements, camps, towers,
        # etc. that appear later in the campaign without changing the canonical
        # POI identity.
        all_events = self.world.repo.list_for_campaign(
            campaign_id,
            target_type="POI",
            target_id=poi.feature_id,
        )
        has_explicit_creation = any(
            event.event_type == "POI_CREATED" for event in all_events
        )

        state = DEFAULT_POI_STATE
        exists = not has_explicit_creation
        visible_at_distance = bool(poi.is_landmark)
        latest_event: WorldEvent | None = None
        for event in all_events:
            if event.game_minute > game_minute:
                break
            if event.event_type not in POI_EVENT_TYPES:
                continue
            latest_event = event
            if event.event_type == "POI_CREATED":
                state, exists = "ACTIVE", True
            elif event.event_type == "POI_DESTROYED":
                state, exists = "DESTROYED", False
            elif event.event_type == "POI_REBUILT":
                state, exists = "ACTIVE", True
            elif event.event_type == "POI_STATE_CHANGED":
                state = str(event.payload.get("state", state)).upper()
                exists = state != "DESTROYED"
            elif event.event_type == "POI_DAMAGED":
                state, exists = "DAMAGED", True
            elif event.event_type == "POI_OCCUPIED":
                state, exists = "OCCUPIED", True
            elif event.event_type == "POI_ABANDONED":
                state, exists = "ABANDONED", True

            if "visible_at_distance" in (event.payload or {}):
                visible_at_distance = bool(event.payload["visible_at_distance"])

        return ResolvedPOIState(
            poi, game_minute, state, exists, visible_at_distance, latest_event
        )
