from fastapi import APIRouter

from models.constants import BASE_TERRAINS


router = APIRouter(tags=["terrains"])


@router.get("/api/terrains")
def get_terrains():
    return {key: terrain.to_dict() for key, terrain in BASE_TERRAINS.items()}
