from enum import Enum

from .terrain import Terrain


class FogSatuts(Enum):
    FOG_HIDDEN = 0
    FOG_DISCOVERED = 1
    FOG_VISIBLE = 2


# ---------------------------------------------------------------------------
# Terrain travel costs
# ---------------------------------------------------------------------------
#
# travel_cost is a multiplier:
#
#   effective_duration = base_duration * travel_cost
#
# Keep the values here as the global/default campaign rules.
# Campaign-specific overrides can later supersede these values in
# MovementCostService without changing the map editor or movement endpoint.
#
PLAIN = Terrain("Plain", "#88cc66", 3, 1, travel_cost=1.00)
SEA = Terrain("Sea", "#010554", 5, 0, travel_cost=2.00)
SWAMP = Terrain("Swamp", "#1d4001", 2, 1, travel_cost=2.00)
HILL = Terrain("Hill", "#769c2c", 3, 2, travel_cost=1.50)
FOREST = Terrain("Forest", "#2ee81a", 2, 1, travel_cost=1.50)
DEEP_FOREST = Terrain("Deep Forest", "#023b06", 2, 2, travel_cost=2.00)
LOW_MOUNTAIN = Terrain("Low mountain", "#464746", 5, 3, travel_cost=2.00)
MOUNTAIN = Terrain("Mountain", "#282928", 6, 4, travel_cost=3.00)
HIGH_MOUNTAIN = Terrain("High Mountain", "#1c1c1c", 7, 5, travel_cost=4.00)


BASE_TERRAINS = {
    "PLAIN": PLAIN,
    "SEA": SEA,
    "SWAMP": SWAMP,
    "HILL": HILL,
    "FOREST": FOREST,
    "DEEP_FOREST": DEEP_FOREST,
    "LOW_MOUNTAIN": LOW_MOUNTAIN,
    "MOUNTAIN": MOUNTAIN,
    "HIGH_MOUNTAIN": HIGH_MOUNTAIN,
}


HEX_DIRECTIONS = [
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
]
