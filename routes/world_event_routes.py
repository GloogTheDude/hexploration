from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.world_event_dto import (
    WorldEventCreate,
    WorldEventResponse,
    WorldEventUpdate,
    WorldStateResponse,
)
from services.errors import ForbiddenOperationError, NotFoundError
from services.world_event_service import WorldEventService
from services.authorization import require_campaign_dm, require_campaign_member, require_world_event_dm, require_world_event_member


router = APIRouter(tags=["world events"])


def _raise_domain_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.post(
    "/api/campaigns/{campaign_id}/world-events",
    response_model=WorldEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_world_event(
    campaign_id: int,
    data: WorldEventCreate,
    _membership = Depends(require_campaign_dm),
    db: Session = Depends(get_db),
):
    try:
        return WorldEventService(db).create(campaign_id, data)
    except (NotFoundError, ForbiddenOperationError, ValueError) as exc:
        _raise_domain_error(exc)


@router.get(
    "/api/world-events/{event_id}",
    response_model=WorldEventResponse,
)
def get_world_event(event_id: int, _event = Depends(require_world_event_member), db: Session = Depends(get_db)):
    try:
        return WorldEventService(db).get(event_id)
    except NotFoundError as exc:
        _raise_domain_error(exc)


@router.patch(
    "/api/world-events/{event_id}",
    response_model=WorldEventResponse,
)
def update_world_event(
    event_id: int,
    data: WorldEventUpdate,
    _event = Depends(require_world_event_dm),
    db: Session = Depends(get_db),
):
    try:
        return WorldEventService(db).update(event_id, data)
    except (NotFoundError, ForbiddenOperationError, ValueError) as exc:
        _raise_domain_error(exc)


@router.delete(
    "/api/world-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_world_event(event_id: int, _event = Depends(require_world_event_dm), db: Session = Depends(get_db)):
    try:
        WorldEventService(db).delete(event_id)
    except NotFoundError as exc:
        _raise_domain_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/api/campaigns/{campaign_id}/world-events",
    response_model=list[WorldEventResponse],
)
def list_world_events(
    campaign_id: int,
    from_game_minute: int | None = Query(default=None, ge=0),
    to_game_minute: int | None = Query(default=None, ge=0),
    event_type: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    _membership = Depends(require_campaign_member),
    db: Session = Depends(get_db),
):
    try:
        return WorldEventService(db).list_for_campaign(
            campaign_id,
            from_game_minute=from_game_minute,
            to_game_minute=to_game_minute,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
        )
    except (NotFoundError, ValueError) as exc:
        _raise_domain_error(exc)


@router.get(
    "/api/campaigns/{campaign_id}/world-state",
    response_model=WorldStateResponse,
)
def get_world_state(
    campaign_id: int,
    game_minute: int = Query(ge=0),
    _membership = Depends(require_campaign_member),
    db: Session = Depends(get_db),
):
    try:
        state = WorldEventService(db).resolve_state(campaign_id, game_minute)
    except (NotFoundError, ValueError) as exc:
        _raise_domain_error(exc)

    return WorldStateResponse(
        campaign_id=state.campaign_id,
        game_minute=state.game_minute,
        weather_key=state.weather_key,
        latest_global_events=state.latest_global_events,
        latest_target_events=state.latest_target_events,
    )
