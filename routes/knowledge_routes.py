from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from db.models import User

from db.session import get_db
from dto.knowledge_dto import (
    CharacterKnowledgeSummary,
    KnowledgeObservationResponse,
    POIDiscoveryResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.knowledge_service import KnowledgeService
from services.auth_dependencies import get_current_user
from services.authorization import require_character_access, require_expedition_access

router = APIRouter(tags=["knowledge"])


def _raise_domain_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    raise exc


@router.post(
    "/api/expeditions/{expedition_id}/pois/{poi_id}/discover",
    response_model=POIDiscoveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def discover_poi(
    expedition_id: int,
    poi_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        observations = KnowledgeService(db).discover_poi(expedition_id, poi_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return {
        "expedition_id": expedition_id,
        "poi_id": poi_id,
        "observed_game_minute": observations[0].observed_game_minute,
        "observations": observations,
    }


@router.get(
    "/api/characters/{character_id}/knowledge",
    response_model=CharacterKnowledgeSummary,
)
def list_character_knowledge(
    character_id: int,
    _character = Depends(require_character_access),
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        observations = KnowledgeService(db).list_latest_for_character(
            character_id,
            as_of_game_minute=as_of_game_minute,
        )
    except (NotFoundError, ValueError) as exc:
        _raise_domain_error(exc)
    return {
        "character_id": character_id,
        "as_of_game_minute": as_of_game_minute,
        "observations": observations,
    }


@router.get(
    "/api/characters/{character_id}/knowledge/{target_type}/{target_id}",
    response_model=KnowledgeObservationResponse,
)
def get_latest_target_knowledge(
    character_id: int,
    target_type: str,
    target_id: int,
    _character = Depends(require_character_access),
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        return KnowledgeService(db).latest_for_target(
            character_id,
            target_type,
            target_id,
            as_of_game_minute=as_of_game_minute,
        )
    except (NotFoundError, ValueError) as exc:
        _raise_domain_error(exc)


@router.get(
    "/api/characters/{character_id}/knowledge/{target_type}/{target_id}/history",
    response_model=list[KnowledgeObservationResponse],
)
def get_target_knowledge_history(
    character_id: int,
    target_type: str,
    target_id: int,
    _character = Depends(require_character_access),
    db: Session = Depends(get_db),
):
    try:
        return KnowledgeService(db).history_for_target(
            character_id,
            target_type,
            target_id,
        )
    except (NotFoundError, ValueError) as exc:
        _raise_domain_error(exc)
