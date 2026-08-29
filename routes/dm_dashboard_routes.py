from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from dto.dm_dashboard_dto import (
    DMCampaignSummary,
    DMDashboardResponse,
    DMExpeditionPlanCreate,
    DMExpeditionPlanResponse,
    DMMapWorkbenchResponse,
    DMPOICreate,
    DMPOIUpdate,
    DMFeatureEdgeCreate,
    DMTargetWorldEventCreate,
    DMMemberAdd,
    DMMemberSummary,
    DMCharacterCreate,
    DMEditorMapCreate,
    DMEditorMapVersionCreate,
    DMEditorLoadResponse,
)
from dto.expedition_dto import ExpeditionResponse
from dto.character_dto import CharacterResponse
from dto.movement_dto import MapSnapshotResponse
from dto.poi_dto import POIResponse
from dto.map_edge_dto import MapEdgeResponse
from dto.world_event_dto import WorldEventResponse
from services.dm_dashboard_service import DMDashboardService
from services.map_persistence_service import MapPersistenceError
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


router = APIRouter(tags=["dm-dashboard"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ForbiddenOperationError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, (ValueError, MapPersistenceError)):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.get("/api/users/{user_id}/dm-campaigns", response_model=list[DMCampaignSummary])
def list_dm_campaigns(user_id: int, db: Session = Depends(get_db)):
    return DMDashboardService(db).list_dm_campaigns(user_id)


@router.get("/api/campaigns/{campaign_id}/dm-dashboard", response_model=DMDashboardResponse)
def dm_dashboard(
    campaign_id: int,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).get(campaign_id, user_id)
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-expeditions",
    response_model=DMExpeditionPlanResponse,
    status_code=201,
)
def create_dm_expedition(
    campaign_id: int,
    data: DMExpeditionPlanCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_expedition_plan(campaign_id, user_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-expeditions/{expedition_id}/start",
    response_model=ExpeditionResponse,
)
def start_dm_expedition(
    campaign_id: int,
    expedition_id: int,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        expedition = DMDashboardService(db).start_expedition(campaign_id, expedition_id, user_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-expeditions/{expedition_id}/return",
    response_model=ExpeditionResponse,
)
def return_dm_expedition(
    campaign_id: int,
    expedition_id: int,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        expedition = DMDashboardService(db).return_expedition(campaign_id, expedition_id, user_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)




@router.post(
    "/api/campaigns/{campaign_id}/dm-members",
    response_model=DMMemberSummary,
    status_code=201,
)
def dm_add_member(
    campaign_id: int,
    data: DMMemberAdd,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).add_member(campaign_id, user_id, data.user_id, data.role)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-characters",
    response_model=CharacterResponse,
    status_code=201,
)
def dm_create_character(
    campaign_id: int,
    data: DMCharacterCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        character = DMDashboardService(db).create_character(campaign_id, user_id, data)
        return CharacterResponse.model_validate(character)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-maps/from-editor",
    response_model=MapSnapshotResponse,
    status_code=201,
)
def dm_snapshot_editor_map(
    campaign_id: int,
    data: DMEditorMapCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        world_map, version, hex_count = DMDashboardService(db).snapshot_editor_map(
            campaign_id, user_id, data
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
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError, MapPersistenceError) as exc:
        _raise_http(exc)



@router.post(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/load-editor",
    response_model=DMEditorLoadResponse,
)
def dm_load_map_version_into_editor(
    campaign_id: int,
    map_version_id: int,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        world_map, version, hex_count = DMDashboardService(db).load_map_version_into_editor(
            campaign_id, user_id, map_version_id
        )
        return DMEditorLoadResponse(
            map_id=world_map.id,
            map_version_id=version.id,
            version=version.version,
            hex_count=hex_count,
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError, MapPersistenceError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-maps/{map_id}/versions/from-editor",
    response_model=MapSnapshotResponse,
    status_code=201,
)
def dm_snapshot_new_map_version(
    campaign_id: int,
    map_id: int,
    data: DMEditorMapVersionCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        world_map, version, hex_count, _poi_count, _edge_count = DMDashboardService(db).snapshot_new_map_version(
            campaign_id, user_id, map_id, data
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
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError, MapPersistenceError) as exc:
        _raise_http(exc)


@router.get(
    "/api/campaigns/{campaign_id}/dm-map-workbench",
    response_model=DMMapWorkbenchResponse,
)
def dm_map_workbench(
    campaign_id: int,
    map_version_id: int = Query(gt=0),
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).get_map_workbench(campaign_id, user_id, map_version_id)
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/pois",
    response_model=POIResponse,
    status_code=201,
)
def dm_create_poi(
    campaign_id: int,
    map_version_id: int,
    data: DMPOICreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_poi(campaign_id, user_id, map_version_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.patch(
    "/api/campaigns/{campaign_id}/dm-pois/{poi_id}",
    response_model=POIResponse,
)
def dm_update_poi(
    campaign_id: int,
    poi_id: int,
    data: DMPOIUpdate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).update_poi(campaign_id, user_id, poi_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/edges",
    response_model=MapEdgeResponse,
    status_code=201,
)
def dm_create_feature_edge(
    campaign_id: int,
    map_version_id: int,
    data: DMFeatureEdgeCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_feature_edge(campaign_id, user_id, map_version_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-pois/{poi_id}/world-events",
    response_model=WorldEventResponse,
    status_code=201,
)
def dm_create_poi_world_event(
    campaign_id: int,
    poi_id: int,
    data: DMTargetWorldEventCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_poi_world_event(campaign_id, user_id, poi_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-map-edges/{edge_id}/world-events",
    response_model=WorldEventResponse,
    status_code=201,
)
def dm_create_edge_world_event(
    campaign_id: int,
    edge_id: int,
    data: DMTargetWorldEventCreate,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_edge_world_event(campaign_id, user_id, edge_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)
