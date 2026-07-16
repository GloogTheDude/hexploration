from models.hex import Hex
from models.terrain import Terrain
from models.constants import *


class MapService:
    def __init__(self):

        self.world: dict[str, Hex] = {
            "0,0": Hex(0, 0, PLAIN),
            "1,0": Hex(1, 0, PLAIN),
            "0,1": Hex(0, 1, PLAIN),
        }

    def get_hex(self, q: int, r: int) -> Hex | None:
        return self.world.get(f"{q},{r}")

    def reveal_hex(self, q: int, r: int) -> Hex | None:
        hex_tile = self.get_hex(q, r)

        if hex_tile is None:
            return None

        hex_tile.fog = FogSatuts.FOG_DISCOVERED
        return hex_tile

    def get_all_hexes(self) -> list[Hex]:
        return list(self.world.values())