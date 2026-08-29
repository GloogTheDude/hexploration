from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamedModifier:
    key: str
    multiplier: float


WEATHER_MODIFIERS: dict[str, NamedModifier] = {
    "CLEAR": NamedModifier("CLEAR", 1.00),
    "RAIN": NamedModifier("RAIN", 1.15),
    "HEAVY_RAIN": NamedModifier("HEAVY_RAIN", 1.35),
    "STORM": NamedModifier("STORM", 1.75),
    "SNOW": NamedModifier("SNOW", 1.50),
    "BLIZZARD": NamedModifier("BLIZZARD", 2.25),
    "FOG": NamedModifier("FOG", 1.20),
}


TRANSPORT_MODIFIERS: dict[str, NamedModifier] = {
    "FOOT": NamedModifier("FOOT", 1.00),
    "HORSE": NamedModifier("HORSE", 0.75),
    "CART": NamedModifier("CART", 1.10),
    "BOAT": NamedModifier("BOAT", 0.80),
}


def get_weather_modifier(key: str | None) -> NamedModifier | None:
    if key is None:
        return None

    normalized = key.upper()
    modifier = WEATHER_MODIFIERS.get(normalized)

    if modifier is None:
        raise ValueError(f"Unknown weather modifier: {key}")

    return modifier


def get_transport_modifier(key: str | None) -> NamedModifier | None:
    if key is None:
        return None

    normalized = key.upper()
    modifier = TRANSPORT_MODIFIERS.get(normalized)

    if modifier is None:
        raise ValueError(f"Unknown transport modifier: {key}")

    return modifier
