from fastapi import APIRouter
from models.hexmap import Hexmap
from models.terrain import Terrain
from models.constants import FOREST
from models.constants import BASE_TERRAINS

router = APIRouter()

hexmap = Hexmap(50,50,32)


@router.get("/api/map")
def get_map():
    return hexmap.to_dict()

@router.get("/api/terrains")
def get_terrains():
    terrain_dict = {}

    for key, terrain in BASE_TERRAINS.items():
        terrain_dict[key] = terrain.to_dict()

    return terrain_dict


@router.post("/api/hex/{q}/{r}/{terrain_key}")
def paint_hex(q:int, r:int,terrain_key:str):
    modified = hexmap.paint_radius(q,r,BASE_TERRAINS[terrain_key],0)

    return {
        "modified_hexes":
        [h.to_dict() for h in modified]
    }

@router.post("/api/newmap/{q}/{r}/{hexsize}")
def new_map(q:int,r:int ,hexsize:int):
    global hexmap
    hexmap = Hexmap(q,r,hexsize)
    return hexmap.to_dict()


@router.post("/api/hex/paint")
def paint_hexes(data: list[dict]):
    modified = []

    for h in data:
        q = h["q"]
        r = h["r"]
        terrain_key = h["terrain_key"]

        modified.extend(
            hexmap.paint_radius(
                q,
                r,
                BASE_TERRAINS[terrain_key],
                0
            )
        )

    return {
        "modified_hexes":
        [h.to_dict() for h in modified]
    }

@router.post("/api/hex/paintRadius")
def radius_paint(data: list[dict], radius:int):
    modified = []

    for h in data:
        q = h["q"]
        r = h["r"]
        terrain_key = h["terrain_key"]

        modified.extend(
            hexmap.paint_radius(
                q,
                r,
                BASE_TERRAINS[terrain_key],
                radius-1 # We consider radius 0 to be mono-hex the value passed by the slider 
                         # should be between 1 and 10
            )
        )

    return {
        "modified_hexes":
        [h.to_dict() for h in modified]
    }