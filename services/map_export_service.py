from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from math import cos, pi, sin, sqrt

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MapArea, MapEdge, MapHex, MapVersion, PointOfInterest, WorldMap
from models.constants import BASE_TERRAINS
from services.errors import NotFoundError


SQRT3 = sqrt(3)
HEX_DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
WATER_AREA_TYPES = {"LAKE", "INLAND_SEA"}


class MapExportService:
    """Render a persisted MapVersion independently from the browser viewport.

    ``mode='world'`` is the DM-facing default and includes semantic layers.
    ``mode='terrain'`` preserves the old physical-map-only export.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def render(
        self,
        map_version_id: int,
        output_format: str,
        mode: str = "world",
        quality: str = "high",
    ) -> tuple[bytes, str, str]:
        mode = mode.lower().strip()
        quality = quality.lower().strip()
        if mode not in {"world", "terrain"}:
            raise ValueError("Unsupported export mode. Use world or terrain")
        if quality not in {"standard", "high"}:
            raise ValueError("Unsupported export quality. Use standard or high")

        version = self.db.get(MapVersion, map_version_id)
        if version is None:
            raise NotFoundError("MapVersion not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")

        hexes = list(self.db.scalars(select(MapHex).where(MapHex.map_version_id == version.id)))
        sparse = bool(version.default_terrain_key)
        if not sparse and not hexes:
            raise NotFoundError("MapVersion has no hexes")

        areas: list[MapArea] = []
        edges: list[MapEdge] = []
        pois: list[PointOfInterest] = []
        if mode == "world":
            areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == version.id)))
            edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id)))
            pois = list(
                self.db.scalars(
                    select(PointOfInterest)
                    .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                    .where(MapHex.map_version_id == version.id)
                )
            )

        native_size = max(10, int(version.hex_size))
        # High quality exports render at up to 2x the map's native pixel size.
        # This keeps labels, diagonal roads/rivers and hex outlines crisp instead
        # of stretching a small raster after the fact. Huge maps remain bounded.
        quality_scale = 2.0 if quality == "high" else 1.0
        max_dim = 8_192 if quality == "high" else 4_096
        logical_w = max(1.0, 1.5 * native_size * max(0, version.width - 1) + 2 * native_size)
        logical_h = max(1.0, SQRT3 * native_size * (version.height + .5))
        scale = min(quality_scale, max_dim / logical_w, max_dim / logical_h)
        size = native_size * scale
        pad = max(8, int(min(32, max(8, size))))
        width = max(1, int(logical_w * scale + 2 * pad))
        height = max(1, int(logical_h * scale + 2 * pad))
        image = Image.new("RGB", (width, height), "#0b1117")
        draw = ImageDraw.Draw(image)

        def center(q: int, r: int) -> tuple[float, float]:
            x = 1.5 * size * q
            y = SQRT3 * size * (r + q / 2.0)
            return width / 2 + x, height / 2 + y

        def points_for(q: int, r: int, radius: float | None = None):
            cx, cy = center(q, r)
            rad = size if radius is None else radius
            return [(cx + rad * cos(pi / 3 * i), cy + rad * sin(pi / 3 * i)) for i in range(6)]

        # --- Physical terrain layer -------------------------------------------------
        terrain_by_coord = {(h.q, h.r): h.terrain_key for h in hexes}
        if sparse:
            default = BASE_TERRAINS.get(version.default_terrain_key or "SEA")
            fill = getattr(default, "color", "#010554")
            draw.rectangle((pad, pad, width - pad, height - pad), fill=fill)
            if size >= 1.2 and version.width * version.height <= 2_000_000:
                for col in range(version.width):
                    q = col - version.width // 2
                    parity = q & 1
                    for row in range(version.height):
                        r = row - version.height // 2 - (q + parity) // 2
                        draw.polygon(points_for(q, r), fill=fill, outline="#26323d")
            for h in hexes:
                terrain = BASE_TERRAINS.get(h.terrain_key)
                color = getattr(terrain, "color", "#555555")
                if size < 1.2:
                    cx, cy = center(h.q, h.r)
                    d = max(2, int(size * 2))
                    draw.rectangle((cx - d, cy - d, cx + d, cy + d), fill=color)
                else:
                    draw.polygon(points_for(h.q, h.r), fill=color, outline="#26323d")
        else:
            for h in hexes:
                terrain = BASE_TERRAINS.get(h.terrain_key)
                fill = getattr(terrain, "color", "#555555")
                draw.polygon(points_for(h.q, h.r), fill=fill, outline="#26323d")

        if mode == "world":
            self._draw_world_layers(
                draw=draw,
                version=version,
                hexes=hexes,
                areas=areas,
                edges=edges,
                pois=pois,
                size=size,
                center=center,
                points_for=points_for,
                terrain_by_coord=terrain_by_coord,
            )

        fmt = output_format.lower()
        out = BytesIO()
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in world_map.name).strip("_") or "map"
        suffix = "" if mode == "world" else "_terrain"
        filename = f"{safe_name}_v{version.version}{suffix}.{fmt if fmt != 'jpeg' else 'jpg'}"
        if fmt == "png":
            image.save(out, format="PNG", optimize=True)
            media = "image/png"
        elif fmt in {"jpg", "jpeg"}:
            image.save(out, format="JPEG", quality=92, optimize=True)
            media = "image/jpeg"
        elif fmt == "pdf":
            image.save(out, format="PDF", resolution=150.0)
            media = "application/pdf"
            filename = f"{safe_name}_v{version.version}{suffix}.pdf"
        else:
            raise ValueError("Unsupported export format. Use png, jpeg or pdf")
        return out.getvalue(), media, filename

    def _draw_world_layers(
        self,
        *,
        draw: ImageDraw.ImageDraw,
        version: MapVersion,
        hexes: list[MapHex],
        areas: list[MapArea],
        edges: list[MapEdge],
        pois: list[PointOfInterest],
        size: float,
        center,
        points_for,
        terrain_by_coord: dict[tuple[int, int], str],
    ) -> None:
        """Server-side equivalent of the semantic World Editor overlay."""

        # Areas first: water visually replaces the internal terrain/grid while the
        # shoreline remains visible around the exterior only.
        water_area_cells: set[tuple[int, int]] = set()
        for area in areas:
            cells = [(int(c["q"]), int(c["r"])) for c in (area.cells or []) if "q" in c and "r" in c]
            if not cells:
                continue
            water = area.feature_type in WATER_AREA_TYPES
            if water:
                water_area_cells.update(cells)
            fill = "#368faf" if area.feature_type == "LAKE" else "#286f9d" if area.feature_type == "INLAND_SEA" else "#8a7138"
            for q, r in cells:
                # Small overlap suppresses the physical-map grid inside a semantic area.
                draw.polygon(points_for(q, r, size * 1.005), fill=fill)

            cell_set = set(cells)
            bank_segments = []
            rad = size * .965
            for q, r in cells:
                cx, cy = center(q, r)
                for i, (dq, dr) in enumerate(HEX_DIRS):
                    if (q + dq, r + dr) in cell_set:
                        continue
                    a1 = -i * pi / 3
                    a2 = (1 - i) * pi / 3
                    bank_segments.append(
                        (
                            (cx + rad * cos(a1), cy + rad * sin(a1)),
                            (cx + rad * cos(a2), cy + rad * sin(a2)),
                        )
                    )
            outer = "#0a374c" if water else "#5c461c"
            inner = "#7edaff" if water else "#ecc970"
            for a, b in bank_segments:
                draw.line((a, b), fill=outer, width=max(2, round(size * .12)))
            for a, b in bank_segments:
                draw.line((a, b), fill=inner, width=max(1, round(size * .045)))

        def terrain_at(q: int, r: int) -> str | None:
            key = terrain_by_coord.get((q, r))
            if key is not None:
                return key
            return version.default_terrain_key

        def is_water(h: tuple[int, int]) -> bool:
            return h in water_area_cells or terrain_at(*h) == "SEA"

        def endpoint(edge: MapEdge, which: str) -> tuple[int, int]:
            data = edge.extra_data or {}
            key = "path_from" if which == "from" else "path_to"
            value = data.get(key)
            if isinstance(value, dict) and "q" in value and "r" in value:
                return int(value["q"]), int(value["r"])
            return (edge.from_q, edge.from_r) if which == "from" else (edge.to_q, edge.to_r)

        def clipped_line(a: tuple[int, int], b: tuple[int, int]):
            pa, pb = center(*a), center(*b)
            if is_water(a) and not is_water(b):
                pa = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            if is_water(b) and not is_water(a):
                pb = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            return pa, pb

        groups: dict[tuple[str, int], list[MapEdge]] = defaultdict(list)
        for edge in edges:
            groups[(edge.feature_type, edge.feature_id)].append(edge)
        for group in groups.values():
            group.sort(key=lambda e: (e.segment_index or 0, e.id))

        # Rivers are a graph. Deduplicate shared physical corridors across semantic
        # river features and draw every corridor once, with round junction nodes.
        river_segments: dict[tuple[tuple[int, int], tuple[int, int]], tuple[tuple[int, int], tuple[int, int]]] = {}
        river_degree: defaultdict[tuple[int, int], int] = defaultdict(int)
        for (feature_type, _), group in groups.items():
            if feature_type != "RIVER":
                continue
            for edge in group:
                a, b = endpoint(edge, "from"), endpoint(edge, "to")
                key = tuple(sorted((a, b)))
                river_segments[key] = (a, b)
                if not is_water(a):
                    river_degree[a] += 1
                if not is_water(b):
                    river_degree[b] += 1
        if river_segments:
            outer_w = max(4, round(size * .34))
            inner_w = max(2, round(size * .20))
            for a, b in river_segments.values():
                p, q = clipped_line(a, b)
                draw.line((p, q), fill="#0c374c", width=outer_w)
            for a, b in river_segments.values():
                p, q = clipped_line(a, b)
                draw.line((p, q), fill="#55c5f2", width=inner_w)
            for h, degree in river_degree.items():
                if degree >= 3:
                    cx, cy = center(*h)
                    rr = max(2, round(inner_w * .55))
                    draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill="#55c5f2")

        # Other linear features. Roads intentionally render as graph segments so
        # merged branches remain connected. Shared ROAD/RIVER corridors are kept
        # readable by a small deterministic perpendicular offset for the road.
        river_keys = set(river_segments)
        for (feature_type, _), group in groups.items():
            if feature_type == "RIVER":
                continue
            base = "#ead9b9" if feature_type == "BRIDGE" else "#d9b26f"
            road_w = max(2, round(size * .13))
            junctions: defaultdict[tuple[int, int], int] = defaultdict(int)
            shared_nodes: set[tuple[int, int]] = set()
            for edge in group:
                a, b = endpoint(edge, "from"), endpoint(edge, "to")
                p, q = center(*a), center(*b)
                key = tuple(sorted((a, b)))
                shared = feature_type == "ROAD" and key in river_keys
                if shared:
                    dx, dy = q[0] - p[0], q[1] - p[1]
                    length = max(1.0, (dx * dx + dy * dy) ** .5)
                    offset = max(2.0, size * .16)
                    ox, oy = -dy / length * offset, dx / length * offset
                    p, q = (p[0] + ox, p[1] + oy), (q[0] + ox, q[1] + oy)
                    shared_nodes.update((a, b))
                draw.line((p, q), fill=base, width=road_w)
                junctions[a] += 1
                junctions[b] += 1
            if feature_type == "ROAD":
                rr = max(1, round(road_w * .55))
                for h, degree in junctions.items():
                    # A junction touching a visually offset ROAD/RIVER corridor
                    # must not be filled at the canonical hex center: that fill
                    # is the small beige dot artifact visible on shared routes.
                    if degree < 2 or h in shared_nodes:
                        continue
                    cx, cy = center(*h)
                    draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=base)

        # POIs sit on top of world geometry. Yellow means POI; outline communicates
        # visibility exactly like the World Editor: black = visible landmark,
        # white = hidden/local POI.
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", max(10, round(size * .32)))
        except OSError:
            font = ImageFont.load_default()
        for poi in pois:
            hx = poi.hex
            cx, cy = center(hx.q, hx.r)
            radius = max(3, round(size * .18))
            outline = "#111820" if poi.is_landmark else "#ffffff"
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill="#ffd84d",
                outline=outline,
                width=max(1, round(size * .07)),
            )
            if size >= 7:
                label = poi.name
                tx, ty = cx + radius + max(2, size * .08), cy - radius - 2
                # Tiny dark shadow preserves labels on both light and dark terrain.
                draw.text((tx + 1, ty + 1), label, font=font, fill="#10171c")
                draw.text((tx, ty), label, font=font, fill="#f5f8fb")
