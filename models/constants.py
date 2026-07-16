from enum import Enum
from .terrain import Terrain

class FogSatuts(Enum):
    FOG_HIDDEN = 0
    FOG_DISCOVERED = 1
    FOG_VISIBLE =2

#terrain types
PLAIN = Terrain("Plain","#88cc66", 3, 1)
SEA = Terrain ("Sea", "#010554", 5, 0)
SWAMP= Terrain("Swamp","#1d4001", 2,1)
HILL = Terrain("Hill", "#769c2c", 3,2)
FOREST = Terrain("Forest", "#2ee81a", 2,1)
DEEP_FOREST = Terrain("Deep Forest", "#023b06", 2,2)
LOW_MOUNTAIN = Terrain("Low mountain", "#464746", 5,3)
MOUNTAIN = Terrain("Mountain", "#282928", 6,4)
HIGH_MOUNTAIN = Terrain("High Mountain", "#1c1c1c", 7,5)

BASE_TERRAINS={
    "PLAIN": PLAIN,
    "SEA": SEA,
    "SWAMP": SWAMP,
    "HILL": HILL,
    "FOREST": FOREST,
    "DEEP_FOREST": DEEP_FOREST,
    "LOW_MOUNTAIN": LOW_MOUNTAIN,
    "MOUNTAIN": MOUNTAIN,
    "HIGH_MOUNTAIN": HIGH_MOUNTAIN
}

HEX_DIRECTIONS = [
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1)
]