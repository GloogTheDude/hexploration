from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.expedition_dto import (
    ExpeditionCharacterAdd,
    ExpeditionCharacterResponse,
    ExpeditionCreate,
    ExpeditionResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.expedition_service import ExpeditionService


router = APIRouter(tags=["expeditions"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.post(
    "/api/campaigns/{campaign_id}/expeditions",
    response_model=ExpeditionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expedition(
    campaign_id: int,
    data: ExpeditionCreate,
    db: Session = Depends(get_db),
) -> ExpeditionResponse:
    try:
        expedition = ExpeditionService(db).create(campaign_id, data)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.get(
    "/api/campaigns/{campaign_id}/expeditions",
    response_model=list[ExpeditionResponse],
)
def list_campaign_expeditions(
    campaign_id: int,
    db: Session = Depends(get_db),
) -> list[ExpeditionResponse]:
    try:
        expeditions = ExpeditionService(db).list_for_campaign(campaign_id)
        return [ExpeditionResponse.model_validate(e) for e in expeditions]
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.get(
    "/api/expeditions/{expedition_id}",
    response_model=ExpeditionResponse,
)
def get_expedition(
    expedition_id: int,
    db: Session = Depends(get_db),
) -> ExpeditionResponse:
    try:
        return ExpeditionResponse.model_validate(
            ExpeditionService(db).get(expedition_id)
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/characters",
    response_model=ExpeditionCharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_character_to_expedition(
    expedition_id: int,
    data: ExpeditionCharacterAdd,
    db: Session = Depends(get_db),
) -> ExpeditionCharacterResponse:
    try:
        participant = ExpeditionService(db).add_character(
            expedition_id,
            data.character_id,
        )
        return ExpeditionCharacterResponse.model_validate(participant)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.get(
    "/api/expeditions/{expedition_id}/characters",
    response_model=list[ExpeditionCharacterResponse],
)
def list_expedition_characters(
    expedition_id: int,
    db: Session = Depends(get_db),
) -> list[ExpeditionCharacterResponse]:
    try:
        participants = ExpeditionService(db).list_characters(expedition_id)
        return [
            ExpeditionCharacterResponse.model_validate(participant)
            for participant in participants
        ]
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/start",
    response_model=ExpeditionResponse,
)
def start_expedition(
    expedition_id: int,
    db: Session = Depends(get_db),
) -> ExpeditionResponse:
    try:
        expedition = ExpeditionService(db).start(expedition_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/return",
    response_model=ExpeditionResponse,
)
def return_expedition_to_hub(
    expedition_id: int,
    db: Session = Depends(get_db),
) -> ExpeditionResponse:
    try:
        expedition = ExpeditionService(db).return_to_hub(expedition_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)
