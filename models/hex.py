from .terrain import Terrain
from .constants import FogSatuts
from .poi import POI


class Hex:
    def __init__(
        self,
        q: int,
        r: int,
        terrain: Terrain,
        fog: FogSatuts = FogSatuts.FOG_HIDDEN,
        pois: list[POI] | None = None,
    ):
        self.q = q
        self.r = r
        self.terrain = terrain
        self.pois = pois or []
        self.fog = fog

    @property
    def key(self) -> str:
        return f"{self.q},{self.r}"

    def to_dict(self) -> dict:
        return {
            "q": self.q,
            "r": self.r,
            "terrain": self.terrain.__dict__,
            "pois": [poi.__dict__ for poi in self.pois],
            "fog": self.fog.name,
        }
