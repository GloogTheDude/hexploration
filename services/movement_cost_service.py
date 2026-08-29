from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from db.models import MapHex
from services.movement_modifiers import (
    get_transport_modifier,
    get_weather_modifier,
)


@dataclass(frozen=True)
class MovementCost:
    base_duration_minutes: int
    effective_duration_minutes: int
    modifiers: list[dict]


class MovementCostService:
    """
    Centralized travel-time calculator.

    Formula:
        base duration
        × terrain
        × weather
        × transport

    Future modifiers such as route, visibility and encumbrance can be added
    here without changing route code.
    """

    def terrain_modifier(self, campaign_id: int, destination: MapHex) -> float:
        modifier = float(destination.travel_cost)

        if modifier <= 0:
            raise ValueError("Terrain travel_cost must be greater than 0")

        return modifier

    def calculate(
        self,
        *,
        campaign_id: int,
        destination: MapHex,
        base_duration_minutes: int,
        weather_key: str | None = None,
        transport_key: str | None = None,
    ) -> MovementCost:
        if base_duration_minutes <= 0:
            raise ValueError("base_duration_minutes must be positive")

        modifiers: list[dict] = []

        terrain_multiplier = self.terrain_modifier(
            campaign_id,
            destination,
        )
        total_multiplier = terrain_multiplier

        modifiers.append(
            {
                "type": "terrain",
                "terrain_key": destination.terrain_key,
                "multiplier": terrain_multiplier,
            }
        )

        weather = get_weather_modifier(weather_key)
        if weather is not None:
            total_multiplier *= weather.multiplier
            modifiers.append(
                {
                    "type": "weather",
                    "weather_key": weather.key,
                    "multiplier": weather.multiplier,
                }
            )

        transport = get_transport_modifier(transport_key)
        if transport is not None:
            total_multiplier *= transport.multiplier
            modifiers.append(
                {
                    "type": "transport",
                    "transport_key": transport.key,
                    "multiplier": transport.multiplier,
                }
            )

        effective = max(
            1,
            ceil(base_duration_minutes * total_multiplier),
        )

        return MovementCost(
            base_duration_minutes=base_duration_minutes,
            effective_duration_minutes=effective,
            modifiers=modifiers,
        )
