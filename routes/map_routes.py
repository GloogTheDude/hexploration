from fastapi import APIRouter, HTTPException

from models.hexmap import Hexmap
from models.constants import BASE_TERRAINS


router = APIRouter(tags=["map editor"])

hexmap = Hexmap(50, 50, 32)


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
        raise HTTPException(
            status_code=404,
            detail=f"Unknown terrain: {terrain_key}",
        )
    return terrain


@router.post("/api/hex/{q}/{r}/{terrain_key}")
def paint_hex(q: int, r: int, terrain_key: str):
    modified = hexmap.paint_radius(
        q,
        r,
        _terrain(terrain_key),
        0,
    )
    return {
        "modified_hexes": [h.to_dict() for h in modified]
    }


@router.post("/api/newmap/{q}/{r}/{hexsize}")
def new_map(q: int, r: int, hexsize: int):
    global hexmap
    hexmap = Hexmap(q, r, hexsize)
    return hexmap.to_dict()


@router.post("/api/hex/paint")
def paint_hexes(data: list[dict]):
    modified = []
    for h in data:
        modified.extend(
            hexmap.paint_radius(
                h["q"],
                h["r"],
                _terrain(h["terrain_key"]),
                0,
            )
        )
    return {
        "modified_hexes": [h.to_dict() for h in modified]
    }


@router.post("/api/hex/paintRadius")
def radius_paint(data: list[dict], radius: int):
    modified = []
    for h in data:
        modified.extend(
            hexmap.paint_radius(
                h["q"],
                h["r"],
                _terrain(h["terrain_key"]),
                radius - 1,
            )
        )
    return {
        "modified_hexes": [h.to_dict() for h in modified]
    }
