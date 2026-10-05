from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.visibility_dto import (
    ExpeditionVisibilityObservationResponse,
    ExpeditionVisibilityResponse,
)
from services.errors import ConflictError, NotFoundError
from services.visibility_service import VisibilityService
from services.authorization import require_expedition_access


router = APIRouter(tags=["visibility"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    raise exc


def _scan_payload(scan) -> dict:
    return {
        "expedition_id": scan.expedition_id,
        "game_minute": scan.game_minute,
        "map_version_id": scan.map_version_id,
        "origin_q": scan.origin_q,
        "origin_r": scan.origin_r,
        "origin_visibility_score": scan.origin_visibility_score,
        "weather_key": scan.weather_key,
        "visible_hexes": [
            {
                "q": item.hex.q,
                "r": item.hex.r,
                "terrain_key": item.hex.terrain_key,
                "elevation": item.hex.elevation,
                "visibility_score": item.hex.visibility_score,
                "distance": item.distance,
                "max_visible_distance": item.max_visible_distance,
                "weather_penalty": item.weather_penalty,
                "elevation_bonus": item.elevation_bonus,
                "terrain_concealment_penalty": item.terrain_concealment_penalty,
                "los_path": item.los_path,
            }
            for item in scan.visible_hexes
        ],
        "occluded_hexes": [
            {
                "q": item.hex.q,
                "r": item.hex.r,
                "terrain_key": item.hex.terrain_key,
                "elevation": item.hex.elevation,
                "visibility_score": item.hex.visibility_score,
                "distance": item.distance,
                "max_visible_distance": item.max_visible_distance,
                "blocker_q": item.blocker_q,
                "blocker_r": item.blocker_r,
                "blocker_reason": item.blocker_reason,
                "blocker_elevation": item.blocker_elevation,
                "sightline_elevation": item.sightline_elevation,
                "los_path": item.los_path,
            }
            for item in scan.occluded_hexes
        ],
        "visible_pois": [
            {
                "poi_id": item.poi.id,
                "name": item.poi.name,
                "kind": item.poi.kind,
                "q": item.hex.q,
                "r": item.hex.r,
                "distance": item.distance,
                "max_visible_distance": item.max_visible_distance,
                "is_landmark": item.poi.is_landmark,
                "state": item.state,
                "exists": item.exists,
                "world_event_id": item.world_event_id,
                "weather_penalty": item.weather_penalty,
                "landmark_bonus": item.landmark_bonus,
                "elevation_bonus": item.elevation_bonus,
                "terrain_concealment_penalty": item.terrain_concealment_penalty,
                "los_path": item.los_path,
            }
            for item in scan.visible_pois
        ],
        "occluded_pois": [
            {
                "poi_id": item.poi.id,
                "name": item.poi.name,
                "kind": item.poi.kind,
                "q": item.hex.q,
                "r": item.hex.r,
                "distance": item.distance,
                "max_visible_distance": item.max_visible_distance,
                "blocker_q": item.blocker_q,
                "blocker_r": item.blocker_r,
                "blocker_reason": item.blocker_reason,
                "blocker_elevation": item.blocker_elevation,
                "sightline_elevation": item.sightline_elevation,
                "los_path": item.los_path,
            }
            for item in scan.occluded_pois
        ],
    }


@router.get(
    "/api/expeditions/{expedition_id}/visibility",
    response_model=ExpeditionVisibilityResponse,
)
def preview_visibility(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        scan = VisibilityService(db).scan(expedition_id)
        return _scan_payload(scan)
    except (NotFoundError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/expeditions/{expedition_id}/visibility/observe",
    response_model=ExpeditionVisibilityObservationResponse,
)
def observe_visibility(
    expedition_id: int,
    _access = Depends(require_expedition_access),
    db: Session = Depends(get_db),
):
    try:
        result = VisibilityService(db).observe_visible_pois(expedition_id)
        payload = _scan_payload(result.scan)
        payload["observations"] = result.observations
        payload["map_observations"] = result.map_observations
        return payload
    except (NotFoundError, ConflictError) as exc:
        _raise_http(exc)
