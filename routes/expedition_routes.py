from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import CampaignRole, User
from dto.expedition_dto import (
    ExpeditionCharacterAdd,
    ExpeditionCharacterResponse,
    ExpeditionCreate,
    ExpeditionResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.expedition_service import ExpeditionService
from services.auth_dependencies import get_current_user
from services.authorization import require_campaign_dm, require_campaign_member, require_expedition_access, require_expedition_dm


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
    _membership = Depends(require_campaign_dm),
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
    membership = Depends(require_campaign_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExpeditionResponse]:
    try:
        service = ExpeditionService(db)
        expeditions = (
            service.list_for_campaign(campaign_id)
            if membership.role == CampaignRole.DM
            else service.list_for_user(campaign_id, current_user.id)
        )
        return [ExpeditionResponse.model_validate(e) for e in expeditions]
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.get(
    "/api/expeditions/{expedition_id}",
    response_model=ExpeditionResponse,
)
def get_expedition(
    expedition_id: int,
    _access = Depends(require_expedition_access),
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
    _access = Depends(require_expedition_dm),
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
    _access = Depends(require_expedition_access),
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
    _access = Depends(require_expedition_dm),
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
    _access = Depends(require_expedition_dm),
    db: Session = Depends(get_db),
) -> ExpeditionResponse:
    try:
        expedition = ExpeditionService(db).return_to_hub(expedition_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)
