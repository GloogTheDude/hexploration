from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User
from dto.player_map_dto import (
    PlayerMapBootstrapResponse,
    PlayerMapHexResponse,
    PlayerMapPOIResponse,
    PlayerMapEdgeResponse,
    PlayerMapAreaResponse,
    PlayerMapResponse,
    ExpeditionPingSet,
    ExpeditionPingResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.expedition_ping_service import ExpeditionPingService
from services.player_map_service import PlayerMapService
from services.auth_dependencies import get_current_user
from services.authorization import require_expedition_access, require_expedition_dm


router = APIRouter(tags=["player-map"])


@router.get(
    "/api/expeditions/{expedition_id}/player-map",
    response_model=PlayerMapResponse,
)
def player_map(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        state = PlayerMapService(db).get(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    expedition = state.expedition
    ping_service = ExpeditionPingService(db)
    ping = ping_service.get_ping(expedition.id)
    return PlayerMapResponse(
        expedition_id=expedition.id,
        expedition_name=expedition.name,
        expedition_status=expedition.status.value,
        current_game_minute=expedition.current_game_minute,
        map_id=state.world_map.id,
        map_name=state.world_map.name,
        map_version_id=state.map_version.id,
        map_version=state.map_version.version,
        hex_size=state.map_version.hex_size,
        current_q=expedition.current_q,
        current_r=expedition.current_r,
        weather_key=expedition.weather_key,
        transport_key=expedition.transport_key,
        ping_q=ping.q,
        ping_r=ping.r,
        ping_game_minute=ping.game_minute,
        ping_user_id=ping.user_id,
        ping_username=ping.username,
        ping_color=ping.color,
        ping_created_at=ping.created_at,
        # DM pings are intentionally excluded from the player-view payload.
        # DMs use the separate /dm-ping endpoint when they need that state.
        dm_ping_q=None,
        dm_ping_r=None,
        dm_ping_game_minute=None,
        dm_ping_user_id=None,
        dm_ping_username=None,
        dm_ping_color=None,
        dm_ping_created_at=None,
        hexes=[
            PlayerMapHexResponse(
                q=row.q,
                r=row.r,
                discovery_state=row.discovery_state,
                visibility_state=("VISIBLE" if (row.q, row.r) in state.visible_hex_coords else "SEEN"),
                terrain_key=row.terrain_key,
                elevation=row.elevation,
                visibility_score=row.visibility_score,
                observed_game_minute=row.observed_game_minute,
                map_version_id=row.map_version_id,
            )
            for row in state.hexes
        ],
        pois=[
            PlayerMapPOIResponse(
                poi_id=row.target_id,
                name=row.knowledge.get("name") or f"POI #{row.target_id}",
                kind=row.knowledge.get("kind"),
                q=row.knowledge["q"],
                r=row.knowledge["r"],
                state=row.knowledge.get("state"),
                exists=row.knowledge.get("exists"),
                observed_game_minute=row.observed_game_minute,
                description=row.knowledge.get("description"),
            )
            for row in state.pois
            if row.knowledge.get("q") is not None
            and row.knowledge.get("r") is not None
        ],
        edges=[
            PlayerMapEdgeResponse(
                feature_type=edge.feature_type,
                feature_id=edge.feature_id,
                name=edge.name,
                from_q=edge.from_q,
                from_r=edge.from_r,
                to_q=edge.to_q,
                to_r=edge.to_r,
            )
            for edge in state.edges
        ],
        areas=[PlayerMapAreaResponse(**area) for area in state.areas],
    )


@router.post(
    "/api/expeditions/{expedition_id}/player-map/bootstrap",
    response_model=PlayerMapBootstrapResponse,
)
def bootstrap_player_map(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        initialized, map_count, poi_count = PlayerMapService(db).bootstrap(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return PlayerMapBootstrapResponse(
        expedition_id=expedition_id,
        initialized=initialized,
        map_observations_created=map_count,
        poi_observations_created=poi_count,
    )


@router.get(
    "/api/expeditions/{expedition_id}/ping",
    response_model=ExpeditionPingResponse,
)
def get_expedition_ping(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        expedition = ExpeditionPingService(db).get_ping(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ExpeditionPingResponse(
        expedition_id=expedition.expedition_id, q=expedition.q, r=expedition.r,
        game_minute=expedition.game_minute, user_id=expedition.user_id,
        username=expedition.username, color=expedition.color, created_at=expedition.created_at,
    )


@router.put(
    "/api/expeditions/{expedition_id}/ping",
    response_model=ExpeditionPingResponse,
)
def set_expedition_ping(
    expedition_id: int,
    data: ExpeditionPingSet,
    current_user: User = Depends(get_current_user),
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        expedition = ExpeditionPingService(db).set_ping(expedition_id, current_user.id, data.q, data.r)
    except (NotFoundError, ConflictError, ForbiddenOperationError, ValueError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_403_FORBIDDEN if isinstance(exc, ForbiddenOperationError) else status.HTTP_409_CONFLICT if isinstance(exc, ConflictError) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(code, str(exc)) from exc
    return ExpeditionPingResponse(expedition_id=expedition.expedition_id, q=expedition.q, r=expedition.r, game_minute=expedition.game_minute, user_id=expedition.user_id, username=expedition.username, color=expedition.color, created_at=expedition.created_at)


@router.delete(
    "/api/expeditions/{expedition_id}/ping",
    response_model=ExpeditionPingResponse,
)
def clear_expedition_ping(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        expedition = ExpeditionPingService(db).clear_ping(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ExpeditionPingResponse(expedition_id=expedition.expedition_id, q=None, r=None, game_minute=None)


@router.get(
    "/api/expeditions/{expedition_id}/dm-ping",
    response_model=ExpeditionPingResponse,
)
def get_expedition_dm_ping(
    expedition_id: int,
    _access = Depends(require_expedition_dm),
    db: Session = Depends(get_db),
):
    try:
        ping = ExpeditionPingService(db).get_dm_ping(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ExpeditionPingResponse(
        expedition_id=ping.expedition_id, q=ping.q, r=ping.r, game_minute=ping.game_minute,
        user_id=ping.user_id, username=ping.username, color=ping.color, created_at=ping.created_at,
    )


@router.put(
    "/api/expeditions/{expedition_id}/dm-ping",
    response_model=ExpeditionPingResponse,
)
def set_expedition_dm_ping(
    expedition_id: int,
    data: ExpeditionPingSet,
    current_user: User = Depends(get_current_user),
    _access = Depends(require_expedition_dm),
    db: Session = Depends(get_db),
):
    try:
        ping = ExpeditionPingService(db).set_dm_ping(expedition_id, current_user.id, data.q, data.r)
    except (NotFoundError, ConflictError, ForbiddenOperationError, ValueError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_403_FORBIDDEN if isinstance(exc, ForbiddenOperationError) else status.HTTP_409_CONFLICT if isinstance(exc, ConflictError) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(code, str(exc)) from exc
    return ExpeditionPingResponse(
        expedition_id=ping.expedition_id, q=ping.q, r=ping.r, game_minute=ping.game_minute,
        user_id=ping.user_id, username=ping.username, color=ping.color, created_at=ping.created_at,
    )
