from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import WorldEvent
from dto.world_event_dto import WorldEventCreate, WorldEventUpdate
from repositories.world_event_repository import WorldEventRepository
from services.errors import ForbiddenOperationError, NotFoundError
from services.movement_modifiers import get_weather_modifier


WEATHER_CHANGED = "WEATHER_CHANGED"

TRAVERSAL_BLOCK_EVENT_TYPES = {
    "BRIDGE_DESTROYED",
    "ROAD_BLOCKED",
    "PASSAGE_BLOCKED",
    "TRAVERSAL_BLOCKED",
}
TRAVERSAL_OPEN_EVENT_TYPES = {
    "BRIDGE_REPAIRED",
    "ROAD_REOPENED",
    "PASSAGE_OPENED",
    "TRAVERSAL_OPENED",
}
TRAVERSAL_EVENT_TYPES = TRAVERSAL_BLOCK_EVENT_TYPES | TRAVERSAL_OPEN_EVENT_TYPES


@dataclass(frozen=True)
class TraversalState:
    allowed: bool
    event: WorldEvent | None


@dataclass(frozen=True)
class ResolvedWorldState:
    campaign_id: int
    game_minute: int
    weather_key: str | None
    latest_global_events: list[WorldEvent]
    latest_target_events: list[WorldEvent]


class WorldEventService:
    """
    Immutable campaign timeline + temporal state resolver.

    WorldEvent is canonical world truth. State is never read as "the latest row"
    globally; it is resolved at a specific in-world minute so two expeditions at
    different clocks can legitimately observe different states.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WorldEventRepository(db)

    @staticmethod
    def normalize_event_type(event_type: str) -> str:
        normalized = event_type.strip().upper()
        if not normalized:
            raise ValueError("event_type cannot be empty")
        return normalized

    @staticmethod
    def normalize_target_type(target_type: str | None) -> str | None:
        if target_type is None:
            return None
        normalized = target_type.strip().upper()
        return normalized or None

    def _validate_campaign(self, campaign_id: int) -> None:
        if self.repo.get_campaign(campaign_id) is None:
            raise NotFoundError("Campaign not found")

    def _validate_expedition(
        self,
        campaign_id: int,
        expedition_id: int | None,
    ) -> None:
        if expedition_id is None:
            return

        expedition = self.repo.get_expedition(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.campaign_id != campaign_id:
            raise ForbiddenOperationError(
                "Expedition and world event must belong to the same campaign"
            )

    def _validate_weather_payload(self, payload: dict) -> None:
        if "weather_key" not in payload:
            raise ValueError(
                "WEATHER_CHANGED requires payload.weather_key "
                "(use null to clear weather)"
            )

        weather_key = payload.get("weather_key")
        if weather_key is not None:
            get_weather_modifier(str(weather_key))

    def create(self, campaign_id: int, data: WorldEventCreate) -> WorldEvent:
        self._validate_campaign(campaign_id)
        self._validate_expedition(campaign_id, data.expedition_id)

        event_type = self.normalize_event_type(data.event_type)
        target_type = self.normalize_target_type(data.target_type)
        payload = dict(data.payload)

        if event_type == WEATHER_CHANGED:
            self._validate_weather_payload(payload)
            weather_key = payload.get("weather_key")
            if weather_key is not None:
                payload["weather_key"] = str(weather_key).upper()

        event = WorldEvent(
            campaign_id=campaign_id,
            expedition_id=data.expedition_id,
            game_minute=data.game_minute,
            event_type=event_type,
            target_type=target_type,
            target_id=data.target_id,
            payload=payload,
            dm_note=data.dm_note,
        )
        self.repo.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get(self, event_id: int) -> WorldEvent:
        event = self.repo.get(event_id)
        if event is None:
            raise NotFoundError("World event not found")
        return event

    def update(self, event_id: int, data: WorldEventUpdate) -> WorldEvent:
        event = self.get(event_id)
        changes = data.model_dump(exclude_unset=True)

        if "expedition_id" in changes:
            self._validate_expedition(event.campaign_id, changes["expedition_id"])

        event_type = (
            self.normalize_event_type(changes["event_type"])
            if "event_type" in changes
            else event.event_type
        )
        payload = (
            dict(changes["payload"])
            if "payload" in changes and changes["payload"] is not None
            else dict(event.payload)
        )

        if event_type == WEATHER_CHANGED:
            self._validate_weather_payload(payload)
            weather_key = payload.get("weather_key")
            if weather_key is not None:
                payload["weather_key"] = str(weather_key).upper()

        if "game_minute" in changes:
            event.game_minute = changes["game_minute"]
        if "event_type" in changes:
            event.event_type = event_type
        if "expedition_id" in changes:
            event.expedition_id = changes["expedition_id"]
        if "target_type" in changes:
            event.target_type = self.normalize_target_type(changes["target_type"])
        if "target_id" in changes:
            event.target_id = changes["target_id"]
        if "payload" in changes:
            event.payload = payload
        if "dm_note" in changes:
            event.dm_note = changes["dm_note"]

        # If the type changed to WEATHER_CHANGED without an explicit payload,
        # the existing payload was validated above and is kept.
        if event_type == WEATHER_CHANGED and "payload" not in changes:
            event.payload = payload

        self.db.commit()
        self.db.refresh(event)
        return event

    def delete(self, event_id: int) -> None:
        event = self.get(event_id)
        self.repo.delete(event)
        self.db.commit()

    def list_for_campaign(
        self,
        campaign_id: int,
        *,
        from_game_minute: int | None = None,
        to_game_minute: int | None = None,
        event_type: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
    ) -> list[WorldEvent]:
        self._validate_campaign(campaign_id)

        if from_game_minute is not None and from_game_minute < 0:
            raise ValueError("from_game_minute must be >= 0")
        if to_game_minute is not None and to_game_minute < 0:
            raise ValueError("to_game_minute must be >= 0")
        if (
            from_game_minute is not None
            and to_game_minute is not None
            and from_game_minute > to_game_minute
        ):
            raise ValueError("from_game_minute cannot be after to_game_minute")

        return self.repo.list_for_campaign(
            campaign_id,
            from_game_minute=from_game_minute,
            to_game_minute=to_game_minute,
            event_type=(
                self.normalize_event_type(event_type)
                if event_type is not None
                else None
            ),
            target_type=self.normalize_target_type(target_type),
            target_id=target_id,
        )

    def weather_at(self, campaign_id: int, game_minute: int) -> str | None:
        if game_minute < 0:
            raise ValueError("game_minute must be >= 0")

        event = self.repo.latest_event(
            campaign_id,
            game_minute=game_minute,
            event_type=WEATHER_CHANGED,
        )
        if event is None:
            return None

        weather_key = event.payload.get("weather_key")
        return str(weather_key) if weather_key is not None else None

    def traversal_state_for_target(
        self,
        campaign_id: int,
        *,
        game_minute: int,
        target_type: str,
        target_id: int,
    ) -> TraversalState:
        if game_minute < 0:
            raise ValueError("game_minute must be >= 0")

        event = self.repo.latest_target_event_of_types(
            campaign_id,
            game_minute=game_minute,
            target_type=self.normalize_target_type(target_type) or "",
            target_id=target_id,
            event_types=TRAVERSAL_EVENT_TYPES,
        )
        if event is None:
            return TraversalState(allowed=True, event=None)

        return TraversalState(
            allowed=event.event_type not in TRAVERSAL_BLOCK_EVENT_TYPES,
            event=event,
        )

    def set_weather(
        self,
        *,
        campaign_id: int,
        game_minute: int,
        weather_key: str | None,
        expedition_id: int | None = None,
        dm_note: str | None = None,
    ) -> WorldEvent:
        normalized_weather: str | None = None
        if weather_key is not None:
            weather = get_weather_modifier(weather_key)
            if weather is not None:
                normalized_weather = weather.key

        return self.create(
            campaign_id,
            WorldEventCreate(
                expedition_id=expedition_id,
                game_minute=game_minute,
                event_type=WEATHER_CHANGED,
                payload={"weather_key": normalized_weather},
                dm_note=dm_note,
            ),
        )

    def resolve_state(
        self,
        campaign_id: int,
        game_minute: int,
    ) -> ResolvedWorldState:
        self._validate_campaign(campaign_id)
        if game_minute < 0:
            raise ValueError("game_minute must be >= 0")

        events = self.repo.events_up_to(campaign_id, game_minute)

        latest_global: dict[str, WorldEvent] = {}
        latest_target: dict[tuple[str, int], WorldEvent] = {}
        weather_key: str | None = None

        for event in events:
            if event.event_type == WEATHER_CHANGED:
                value = event.payload.get("weather_key")
                weather_key = str(value) if value is not None else None
                continue

            if event.target_type is None or event.target_id is None:
                # Generic campaign-wide state: latest event of each type wins.
                latest_global[event.event_type] = event
            else:
                # Generic target state: latest event for that target wins,
                # regardless of event type (DESTROYED can later be REPAIRED).
                latest_target[(event.target_type, event.target_id)] = event

        return ResolvedWorldState(
            campaign_id=campaign_id,
            game_minute=game_minute,
            weather_key=weather_key,
            latest_global_events=list(latest_global.values()),
            latest_target_events=list(latest_target.values()),
        )
