from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.map_knowledge_dto import (
    CharacterMapKnowledgeResponse,
    ExpeditionMapKnowledgeHexResponse,
    ExpeditionMapKnowledgeResponse,
    MapHexKnowledgeResponse,
)
from services.errors import ForbiddenOperationError, NotFoundError
from services.map_knowledge_service import MapKnowledgeService
from services.authorization import require_character_access, require_expedition_access


router = APIRouter(tags=["map-knowledge"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    raise exc


@router.get(
    "/api/characters/{character_id}/map-knowledge/{map_id}",
    response_model=CharacterMapKnowledgeResponse,
)
def character_map_knowledge(
    character_id: int,
    map_id: int,
    _character = Depends(require_character_access),
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        rows = MapKnowledgeService(db).character_map(
            character_id=character_id,
            map_id=map_id,
            as_of_game_minute=as_of_game_minute,
        )
        return {
            "character_id": character_id,
            "map_id": map_id,
            "as_of_game_minute": as_of_game_minute,
            "hexes": rows,
        }
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)


@router.get(
    "/api/characters/{character_id}/map-knowledge/{map_id}/{q}/{r}",
    response_model=MapHexKnowledgeResponse,
)
def character_hex_knowledge(
    character_id: int,
    map_id: int,
    q: int,
    r: int,
    _character = Depends(require_character_access),
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        return MapKnowledgeService(db).character_hex(
            character_id=character_id,
            map_id=map_id,
            q=q,
            r=r,
            as_of_game_minute=as_of_game_minute,
        )
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)


@router.get(
    "/api/characters/{character_id}/map-knowledge/{map_id}/{q}/{r}/history",
    response_model=list[MapHexKnowledgeResponse],
)
def character_hex_history(
    character_id: int,
    map_id: int,
    q: int,
    r: int,
    _character = Depends(require_character_access),
    db: Session = Depends(get_db),
):
    try:
        return MapKnowledgeService(db).character_history(
            character_id=character_id,
            map_id=map_id,
            q=q,
            r=r,
        )
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)


@router.get(
    "/api/expeditions/{expedition_id}/map-knowledge/{map_id}",
    response_model=ExpeditionMapKnowledgeResponse,
)
def expedition_map_knowledge(
    expedition_id: int,
    map_id: int,
    _access = Depends(require_expedition_access),
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        service = MapKnowledgeService(db)
        expedition = service.repo.get_expedition(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        minute = expedition.current_game_minute if as_of_game_minute is None else as_of_game_minute
        rows = service.expedition_map(
            expedition_id=expedition_id,
            map_id=map_id,
            as_of_game_minute=minute,
        )
        return ExpeditionMapKnowledgeResponse(
            expedition_id=expedition_id,
            map_id=map_id,
            as_of_game_minute=minute,
            hexes=[
                ExpeditionMapKnowledgeHexResponse(
                    q=row.q,
                    r=row.r,
                    discovery_state=row.discovery_state,
                    terrain_key=row.terrain_key,
                    elevation=row.elevation,
                    visibility_score=row.visibility_score,
                    extra_data=row.extra_data,
                    observed_game_minute=row.observed_game_minute,
                    observed_by_character_id=row.character_id,
                    map_version_id=row.map_version_id,
                )
                for row in rows
            ],
        )
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)
