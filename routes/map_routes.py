from fastapi import APIRouter, HTTPException

from models.hexmap import Hexmap
from models.constants import BASE_TERRAINS


router = APIRouter(tags=["map editor"])

hexmap = Hexmap(50, 50, 32)
dirty_hex_coords: set[tuple[int, int]] = set()
editor_source_version_id: int | None = None
editor_source_map_identity: int | None = None


def clear_dirty_hexes() -> None:
    dirty_hex_coords.clear()


def _mark_dirty(hexes) -> None:
    dirty_hex_coords.update((h.q, h.r) for h in hexes)


@router.get("/api/map")
def get_map():
    return hexmap.to_dict()


@router.get("/api/terrains")
def get_terrains():
    return {
        key: terrain.to_dict()
        for key, terrain in BASE_TERRAINS.items()
    }


def _terrain(terrain_key: str):
    terrain = BASE_TERRAINS.get(terrain_key)
    if terrain is None:
        raise HTTPException(status_code=404, detail=f"Unknown terrain: {terrain_key}")
    return terrain


@router.post("/api/hex/{q}/{r}/{terrain_key}")
def paint_hex(q: int, r: int, terrain_key: str):
    modified = hexmap.paint_radius(q, r, _terrain(terrain_key), 0)
    _mark_dirty(modified)
    return {"modified_hexes": [h.to_dict() for h in modified]}


@router.post("/api/newmap/{width}/{height}/{hexsize}")
def new_map(width: int, height: int, hexsize: int):
    global hexmap, editor_source_version_id, editor_source_map_identity
    try:
        hexmap = Hexmap(width, height, hexsize)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    editor_source_version_id = None
    editor_source_map_identity = id(hexmap)
    clear_dirty_hexes()
    return hexmap.to_dict()


@router.post("/api/hex/paint")
def paint_hexes(data: list[dict]):
    terrain_by_key = {}
    modified_by_coord = {}
    for item in data:
        terrain = terrain_by_key.setdefault(item["terrain_key"], _terrain(item["terrain_key"]))
        tile = hexmap.paint_hex(item["q"], item["r"], terrain)
        if tile is not None:
            modified_by_coord[(tile.q, tile.r)] = tile
    modified = list(modified_by_coord.values())
    _mark_dirty(modified)
    return {"modified_hexes": [h.to_dict() for h in modified]}


@router.post("/api/hex/paintRadius")
def radius_paint(data: list[dict], radius: int):
    if radius < 1 or radius > 25:
        raise HTTPException(status_code=422, detail="Brush radius must be between 1 and 25")
    modified_by_coord = {}
    for item in data:
        terrain = _terrain(item["terrain_key"])
        for tile in hexmap.get_hexes_in_radius(item["q"], item["r"], radius - 1):
            painted = hexmap.paint_hex(tile.q, tile.r, terrain)
            if painted is not None:
                modified_by_coord[(painted.q, painted.r)] = painted
    modified = list(modified_by_coord.values())
    _mark_dirty(modified)
    return {"modified_hexes": [h.to_dict() for h in modified]}
