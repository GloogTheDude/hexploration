from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import Expedition
from services.errors import NotFoundError
from services.movement_modifiers import get_transport_modifier
from services.world_event_service import WorldEventService


@dataclass(frozen=True)
class ExpeditionModifierState:
    weather_key: str | None
    transport_key: str | None


class ExpeditionModifierStateService:
    """
    Compatibility facade for the existing movement-modifier API.

    Weather is now written to/read from the campaign WorldEvent timeline at
    the expedition's current game minute. Transport is still stored directly
    on the expedition because it describes the party, not the world.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.world_events = WorldEventService(db)

    def get(self, expedition_id: int) -> ExpeditionModifierState:
        expedition = self.db.get(Expedition, expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        return ExpeditionModifierState(
            weather_key=self.world_events.weather_at(
                expedition.campaign_id,
                expedition.current_game_minute,
            ),
            transport_key=expedition.transport_key,
        )

    def set(
        self,
        expedition_id: int,
        *,
        weather_key: str | None,
        transport_key: str | None,
    ) -> ExpeditionModifierState:
        expedition = self.db.get(Expedition, expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        transport = get_transport_modifier(transport_key)
        expedition.transport_key = (
            transport.key if transport is not None else None
        )

        # Keep the legacy column synchronized for old tooling, but movement
        # no longer reads it. Temporal resolution comes from WorldEvent.
        expedition.weather_key = (
            weather_key.upper() if weather_key is not None else None
        )

        # Flush transport/legacy state before the event service commits the
        # transaction. The event is campaign-wide world truth at this minute.
        self.db.flush()
        self.world_events.set_weather(
            campaign_id=expedition.campaign_id,
            expedition_id=expedition.id,
            game_minute=expedition.current_game_minute,
            weather_key=weather_key,
        )
        self.db.refresh(expedition)

        return ExpeditionModifierState(
            weather_key=self.world_events.weather_at(
                expedition.campaign_id,
                expedition.current_game_minute,
            ),
            transport_key=expedition.transport_key,
        )
