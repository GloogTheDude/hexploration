from .hex import Hex
from .constants import SEA, HEX_DIRECTIONS, BASE_TERRAINS


class Hexmap:
    """Hex map stored with axial coordinates and presented as a rectangular grid.

    ``width`` and ``height`` describe the logical number of columns/rows seen by
    the editor.  Internally each tile still uses axial ``(q, r)`` coordinates so
    distance, neighbours, movement and persisted semantic identities keep using
    the same hex math.

    New maps use an even-q offset footprint converted to axial coordinates.  This
    produces a visually rectangular flat-top map instead of an axial
    parallelogram.
    """

    def __init__(
        self,
        width: int,
        height: int,
        hex_size: int,
        hexes: dict[str, Hex] | None = None,
    ):
        if width < 1 or height < 1:
            raise ValueError("Map width and height must be positive")
        if width > 10_000 or height > 10_000:
            raise ValueError("Map width and height are limited to 10,000 hexes each")
        if hex_size < 8 or hex_size > 96:
            raise ValueError("hex_size must be between 8 and 96 pixels")
        self.width = width
        self.height = height
        self.hex_size = hex_size
        self.hexes = hexes or {}
        self.layout = "even-q-rect"
        self.default_terrain_key = "SEA"
        # Sparse editor: an absent entry means default terrain.  This keeps a
        # 10,000 x 10,000 logical map at O(changed cells), not O(100M cells).
        self.sparse = True

    @staticmethod
    def offset_to_axial(col: int, row: int, width: int, height: int) -> tuple[int, int]:
        """Convert centered even-q offset coordinates to axial coordinates."""
        q = col - width // 2
        centered_row = row - height // 2
        r = centered_row - (q + (q & 1)) // 2
        return q, r

    @staticmethod
    def axial_to_offset(q: int, r: int, width: int, height: int) -> tuple[int, int]:
        """Inverse of :meth:`offset_to_axial` for a map footprint."""
        col = q + width // 2
        centered_row = r + (q + (q & 1)) // 2
        row = centered_row + height // 2
        return col, row

    def fill_hexes(self):
        for col in range(self.width):
            for row in range(self.height):
                q, r = self.offset_to_axial(col, row, self.width, self.height)
                an_hex = Hex(q, r, SEA)
                self.hexes[an_hex.key] = an_hex

    def contains(self, q: int, r: int) -> bool:
        col, row = self.axial_to_offset(q, r, self.width, self.height)
        return 0 <= col < self.width and 0 <= row < self.height

    def get_hex(self, q: int, r: int) -> Hex | None:
        if not self.contains(q, r):
            return None
        key = f"{q},{r}"
        tile = self.hexes.get(key)
        if tile is None:
            # Lazy materialisation keeps legacy call sites (get_hex(...).terrain =)
            # working without allocating the complete logical world up front.
            tile = Hex(q, r, BASE_TERRAINS[self.default_terrain_key])
            self.hexes[key] = tile
        return tile

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
            "layout": self.layout,
            "sparse": self.sparse,
            "default_terrain_key": self.default_terrain_key,
            "hexes": self.hexes,
        }

    def paint_hex(self, q, r, terrain):
        if not self.contains(q, r):
            return None
        key = f"{q},{r}"
        hex_tile = self.hexes.get(key) or Hex(q, r, BASE_TERRAINS[self.default_terrain_key])
        hex_tile.terrain = terrain
        # Store only overrides. Painting back to the default removes the row.
        if terrain is BASE_TERRAINS[self.default_terrain_key]:
            self.hexes.pop(key, None)
        else:
            self.hexes[key] = hex_tile
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
        result = []
        for h in self.get_hexes_in_radius(q, r, radius):
            painted = self.paint_hex(h.q, h.r, terrain)
            if painted is not None:
                result.append(painted)
        return result

    def get_coord_schema(self):
        schema = []
        for row in range(self.height):
            schema_row = []
            for col in range(self.width):
                q, r = self.offset_to_axial(col, row, self.width, self.height)
                hex_tile = self.get_hex(q, r)
                schema_row.append((hex_tile.q, hex_tile.r))
            schema.append(schema_row)
        return schema

    def get_terrain_schema(self):
        schema = []
        for row in range(self.height):
            schema_row = []
            for col in range(self.width):
                q, r = self.offset_to_axial(col, row, self.width, self.height)
                hex_tile = self.get_hex(q, r)
                schema_row.append(hex_tile.terrain)
            schema.append(schema_row)
        return schema
