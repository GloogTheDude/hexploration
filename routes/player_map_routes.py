from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.player_map_dto import (
    PlayerMapBootstrapResponse,
    PlayerMapHexResponse,
    PlayerMapPOIResponse,
    PlayerMapResponse,
)
from services.errors import ConflictError, NotFoundError
from services.player_map_service import PlayerMapService


router = APIRouter(tags=["player-map"])


@router.get(
    "/api/expeditions/{expedition_id}/player-map",
    response_model=PlayerMapResponse,
)
def player_map(expedition_id: int, db: Session = Depends(get_db)):
    try:
        state = PlayerMapService(db).get(expedition_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    expedition = state.expedition
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
        hexes=[
            PlayerMapHexResponse(
                q=row.q,
                r=row.r,
                discovery_state=row.discovery_state,
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
            )
            for row in state.pois
            if row.knowledge.get("q") is not None
            and row.knowledge.get("r") is not None
        ],
    )


@router.post(
    "/api/expeditions/{expedition_id}/player-map/bootstrap",
    response_model=PlayerMapBootstrapResponse,
)
def bootstrap_player_map(expedition_id: int, db: Session = Depends(get_db)):
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
