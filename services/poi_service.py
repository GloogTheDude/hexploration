from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from db.models import PointOfInterest, WorldEvent
from dto.poi_dto import POICreate
from repositories.poi_repository import POIRepository
from services.errors import NotFoundError
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
        self.db = db; self.repo = POIRepository(db); self.world = WorldEventService(db)
    def create(self, data: POICreate):
        if self.repo.get_hex(data.hex_id) is None: raise NotFoundError("Map hex not found")
        poi = PointOfInterest(**data.model_dump()); self.repo.add(poi); self.db.commit(); self.db.refresh(poi); return poi
    def get(self, poi_id: int):
        poi = self.repo.get(poi_id)
        if poi is None: raise NotFoundError("POI not found")
        return poi
    def list_for_map_version(self, map_version_id: int): return self.repo.list_for_map_version(map_version_id)
    def state_at(self, poi_id: int, *, campaign_id: int, game_minute: int):
        poi = self.get(poi_id)
        if game_minute < 0: raise ValueError("game_minute must be >= 0")
        event = self.world.repo.latest_target_event_of_types(campaign_id, game_minute=game_minute, target_type="POI", target_id=poi_id, event_types=POI_EVENT_TYPES)
        if event is None: return ResolvedPOIState(poi, game_minute, DEFAULT_POI_STATE, True, None)
        if event.event_type == "POI_DESTROYED": state, exists = "DESTROYED", False
        elif event.event_type in {"POI_CREATED", "POI_REBUILT"}: state, exists = "ACTIVE", True
        elif event.event_type == "POI_STATE_CHANGED":
            state = str(event.payload.get("state", DEFAULT_POI_STATE)).upper(); exists = state != "DESTROYED"
        else: state, exists = event.event_type.removeprefix("POI_"), True
        return ResolvedPOIState(poi, game_minute, state, exists, event)
