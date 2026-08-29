from .hex import Hex
from .constants import SEA, HEX_DIRECTIONS


class Hexmap:
    def __init__(
        self,
        width: int,
        height: int,
        hex_size: int,
        hexes: dict[str, Hex] | None = None,
    ):
        self.width = width
        self.height = height
        self.hex_size = hex_size
        self.hexes = hexes or {}

        if hexes is None:
            self.fill_hexes()

    def fill_hexes(self):
        q_offset = self.width // 2
        r_offset = self.height // 2
        for i in range(self.width):
            for j in range(self.height):
                q = i - q_offset
                r = j - r_offset
                an_hex = Hex(q, r, SEA)
                self.hexes[an_hex.key] = an_hex

    def get_hex(self, q: int, r: int) -> Hex | None:
        return self.hexes.get(f"{q},{r}")

    def get_neighbours(self, q: int, r: int):
        neighbours = []
        for d in HEX_DIRECTIONS:
            hex_tile = self.get_hex(q + d[0], r + d[1])
            if hex_tile is not None:
                neighbours.append(hex_tile)
        return neighbours

    def hex_distance(self, q1: int, r1: int, q2: int, r2: int):
        return (
            abs(q1 - q2)
            + abs(q1 + r1 - q2 - r2)
            + abs(r1 - r2)
        ) // 2

    def get_hexes_in_radius(self, q: int, r: int, radius: int):
        result = []
        for dq in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                current_q = q + dq
                current_r = r + dr
                distance = self.hex_distance(q, r, current_q, current_r)
                if distance <= radius:
                    hex_tile = self.get_hex(current_q, current_r)
                    if hex_tile is not None:
                        result.append(hex_tile)
        return result

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "hex_size": self.hex_size,
            "hexes": self.hexes,
        }

    def paint_hex(self, q, r, terrain):
        hex_tile = self.get_hex(q, r)
        if hex_tile is None:
            return None
        hex_tile.terrain = terrain
        return hex_tile

    def bucket(self, q, r, terrain, base_terrain=None):
        initial_hex = self.get_hex(q, r)
        if initial_hex is None:
            return []

        base_terrain = initial_hex.terrain
        modified = []
        stack = [initial_hex]

        while stack:
            current = stack.pop()
            if current.terrain != base_terrain:
                continue
            current.terrain = terrain
            modified.append(current)

            for neighbour in self.get_neighbours(current.q, current.r):
                if neighbour.terrain == base_terrain:
                    stack.append(neighbour)

        return modified

    def paint_radius(self, q, r, terrain, radius):
        hexes = self.get_hexes_in_radius(q, r, radius)
        for h in hexes:
            h.terrain = terrain
        return hexes

    def get_coord_schema(self):
        q_offset = self.width // 2
        r_offset = self.height // 2
        schema = []
        for i in range(self.height):
            row = []
            for j in range(self.width):
                q = j - q_offset
                r = i - r_offset
                hex_tile = self.hexes[f"{q},{r}"]
                row.append((hex_tile.q, hex_tile.r))
            schema.append(row)
        return schema

    def get_terrain_schema(self):
        q_offset = self.width // 2
        r_offset = self.height // 2
        schema = []
        for i in range(self.height):
            row = []
            for j in range(self.width):
                q = j - q_offset
                r = i - r_offset
                hex_tile = self.hexes[f"{q},{r}"]
                row.append(hex_tile.terrain)
            schema.append(row)
        return schema
