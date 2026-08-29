from __future__ import annotations

from io import BytesIO
from math import cos, pi, sin, sqrt

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MapHex, MapVersion, WorldMap
from models.constants import BASE_TERRAINS
from services.errors import NotFoundError


class MapExportService:
    """Render a persisted MapVersion independently from the browser viewport."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def render(self, map_version_id: int, output_format: str) -> tuple[bytes, str, str]:
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

        # Bound raster exports even for 10k x 10k worlds. At world scale the
        # default terrain becomes a solid overview and sparse overrides are dots;
        # regional detail remains full hex geometry.
        native_size = max(10, int(version.hex_size))
        max_dim = 4_096
        logical_w = max(1.0, 1.5 * native_size * max(0, version.width - 1) + 2 * native_size)
        logical_h = max(1.0, sqrt(3) * native_size * (version.height + .5))
        scale = min(1.0, max_dim / logical_w, max_dim / logical_h)
        size = native_size * scale
        pad = max(8, int(min(32, max(8, size))))
        width = max(1, int(logical_w * scale + 2 * pad))
        height = max(1, int(logical_h * scale + 2 * pad))
        image = Image.new("RGB", (width, height), "#0b1117")
        draw = ImageDraw.Draw(image)

        def center(q: int, r: int):
            x = 1.5 * size * q
            y = sqrt(3) * size * (r + q / 2.0)
            return width / 2 + x, height / 2 + y

        if sparse:
            default = BASE_TERRAINS.get(version.default_terrain_key or "SEA")
            fill = getattr(default, "color", "#010554")
            draw.rectangle((pad, pad, width-pad, height-pad), fill=fill)
            if size >= 1.2 and version.width * version.height <= 2_000_000:
                # Small/medium sparse maps still export their complete hex grid.
                for col in range(version.width):
                    q = col - version.width // 2
                    parity = q & 1
                    for row in range(version.height):
                        r = row - version.height // 2 - (q + parity)//2
                        cx, cy = center(q, r)
                        points=[(cx+size*cos(pi/3*i), cy+size*sin(pi/3*i)) for i in range(6)]
                        draw.polygon(points, fill=fill, outline="#26323d")
            for h in hexes:
                cx, cy = center(h.q, h.r)
                terrain = BASE_TERRAINS.get(h.terrain_key)
                color = getattr(terrain, "color", "#555555")
                if size < 1.2:
                    d=max(2, int(size*2)); draw.rectangle((cx-d,cy-d,cx+d,cy+d), fill=color)
                else:
                    points=[(cx+size*cos(pi/3*i), cy+size*sin(pi/3*i)) for i in range(6)]
                    draw.polygon(points, fill=color, outline="#26323d")
        else:
            centers={(h.q,h.r): center(h.q,h.r) for h in hexes}
            for h in hexes:
                cx,cy=centers[(h.q,h.r)]
                terrain=BASE_TERRAINS.get(h.terrain_key)
                fill=getattr(terrain,"color","#555555")
                points=[(cx+size*cos(pi/3*i),cy+size*sin(pi/3*i)) for i in range(6)]
                draw.polygon(points,fill=fill,outline="#26323d")

        fmt = output_format.lower()
        out = BytesIO()
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in world_map.name).strip("_") or "map"
        filename = f"{safe_name}_v{version.version}.{fmt if fmt != 'jpeg' else 'jpg'}"
        if fmt == "png":
            image.save(out, format="PNG", optimize=True); media = "image/png"
        elif fmt in {"jpg", "jpeg"}:
            image.save(out, format="JPEG", quality=92, optimize=True); media = "image/jpeg"
        elif fmt == "pdf":
            image.save(out, format="PDF", resolution=150.0); media = "application/pdf"; filename = f"{safe_name}_v{version.version}.pdf"
        else:
            raise ValueError("Unsupported export format. Use png, jpeg or pdf")
        return out.getvalue(), media, filename
