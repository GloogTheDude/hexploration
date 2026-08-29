from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import Expedition
from services.errors import NotFoundError
from services.movement_modifiers import (
    get_transport_modifier,
    get_weather_modifier,
)


@dataclass(frozen=True)
class ExpeditionModifierState:
    weather_key: str | None
    transport_key: str | None


class ExpeditionModifierStateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, expedition_id: int) -> ExpeditionModifierState:
        expedition = self.db.get(Expedition, expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        return ExpeditionModifierState(
            weather_key=expedition.weather_key,
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

        weather = get_weather_modifier(weather_key)
        transport = get_transport_modifier(transport_key)

        expedition.weather_key = weather.key if weather is not None else None
        expedition.transport_key = (
            transport.key if transport is not None else None
        )

        self.db.commit()
        self.db.refresh(expedition)

        return ExpeditionModifierState(
            weather_key=expedition.weather_key,
            transport_key=expedition.transport_key,
        )
