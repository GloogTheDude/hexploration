from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.movement_dto import (
    ExpeditionMoveRequest,
    ExpeditionPositionResponse,
    ExpeditionPositionSet,
    MapSnapshotCreate,
    MapSnapshotResponse,
    MovementResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.expedition_movement_service import (
    ExpeditionMovementService,
    InvalidMovementError,
)
from services.map_persistence_service import (
    MapPersistenceError,
    MapPersistenceService,
)


router = APIRouter(tags=["movement"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidMovementError):
        raise HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, MapPersistenceError):
        raise HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc))
    raise exc


@router.post(
    "/api/campaigns/{campaign_id}/maps/from-editor",
    response_model=MapSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def persist_current_editor_map(
    campaign_id: int,
    data: MapSnapshotCreate,
    db: Session = Depends(get_db),
) -> MapSnapshotResponse:
    try:
        world_map, version, hex_count = (
            MapPersistenceService(db).snapshot_current_editor_map(
                campaign_id=campaign_id,
                name=data.name,
                description=data.description,
                version_name=data.version_name,
                effective_from_game_minute=data.effective_from_game_minute,
            )
        )

        return MapSnapshotResponse(
            map_id=world_map.id,
            map_version_id=version.id,
            version=version.version,
            width=version.width,
            height=version.height,
            hex_size=version.hex_size,
            hex_count=hex_count,
        )
    except (NotFoundError, MapPersistenceError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/position",
    response_model=ExpeditionPositionResponse,
)
def set_expedition_position(
    expedition_id: int,
    data: ExpeditionPositionSet,
    db: Session = Depends(get_db),
) -> ExpeditionPositionResponse:
    try:
        expedition = ExpeditionMovementService(db).set_position(
            expedition_id,
            data,
        )

        return ExpeditionPositionResponse(
            expedition_id=expedition.id,
            map_version_id=expedition.current_map_version_id,
            q=expedition.current_q,
            r=expedition.current_r,
            current_game_minute=expedition.current_game_minute,
        )
    except (
        NotFoundError,
        ForbiddenOperationError,
        ConflictError,
    ) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/move",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def move_expedition(
    expedition_id: int,
    data: ExpeditionMoveRequest,
    db: Session = Depends(get_db),
) -> MovementResponse:
    try:
        movement = ExpeditionMovementService(db).move(
            expedition_id=expedition_id,
            to_q=data.to_q,
            to_r=data.to_r,
            base_duration_minutes=data.base_duration_minutes,
        )
        return MovementResponse.model_validate(movement)
    except (
        NotFoundError,
        ForbiddenOperationError,
        ConflictError,
        InvalidMovementError,
        ValueError,
    ) as exc:
        _raise_http(exc)


@router.get(
    "/api/expeditions/{expedition_id}/movements",
    response_model=list[MovementResponse],
)
def list_expedition_movements(
    expedition_id: int,
    db: Session = Depends(get_db),
) -> list[MovementResponse]:
    try:
        movements = ExpeditionMovementService(db).history(expedition_id)
        return [
            MovementResponse.model_validate(movement)
            for movement in movements
        ]
    except (NotFoundError,) as exc:
        _raise_http(exc)
