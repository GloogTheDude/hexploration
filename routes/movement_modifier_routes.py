from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from dto.movement_modifier_dto import (
    MovementModifierSet,
    MovementModifierState,
)
from services.errors import NotFoundError
from services.expedition_modifier_state import ExpeditionModifierStateService
from services.movement_modifiers import (
    TRANSPORT_MODIFIERS,
    WEATHER_MODIFIERS,
)
from services.authorization import require_expedition_access, require_expedition_dm


router = APIRouter(tags=["movement modifiers"])


@router.get("/api/movement-modifiers")
def get_available_movement_modifiers():
    return {
        "weather": {
            key: {"multiplier": value.multiplier}
            for key, value in WEATHER_MODIFIERS.items()
        },
        "transport": {
            key: {"multiplier": value.multiplier}
            for key, value in TRANSPORT_MODIFIERS.items()
        },
    }


@router.get(
    "/api/expeditions/{expedition_id}/movement-modifiers",
    response_model=MovementModifierState,
)
def get_modifiers(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        state = ExpeditionModifierStateService(db).get(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return MovementModifierState(
        expedition_id=expedition_id,
        weather_key=state.weather_key,
        transport_key=state.transport_key,
    )


@router.put(
    "/api/expeditions/{expedition_id}/movement-modifiers",
    response_model=MovementModifierState,
)
def update_modifiers(
    expedition_id: int,
    data: MovementModifierSet,
    _access = Depends(require_expedition_dm),
    db: Session = Depends(get_db),
):
    try:
        state = ExpeditionModifierStateService(db).set(
            expedition_id,
            weather_key=data.weather_key,
            transport_key=data.transport_key,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return MovementModifierState(
        expedition_id=expedition_id,
        weather_key=state.weather_key,
        transport_key=state.transport_key,
    )
