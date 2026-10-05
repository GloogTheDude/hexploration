from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import Response
from db.models import User

from db.session import get_db
from dto.dm_dashboard_dto import (
    DMCampaignSummary,
    DMCampaignUpdate,
    DMDashboardResponse,
    DMExpeditionPlanCreate,
    DMExpeditionPlanResponse,
    DMMapWorkbenchResponse,
    DMPOICreate,
    DMPOIUpdate,
    DMFeatureEdgeCreate,
    DMLinearFeatureCreate,
    DMLinearFeatureMerge,
    DMLinearFeatureUpdate,
    DMAreaFeatureUpdate,
    DMWorldEditorSnapshot,
    DMHexFeatureClear,
    DMAreaFeatureCreate,
    DMTargetWorldEventCreate,
    DMMemberAdd,
    DMMemberSummary,
    DMCharacterCreate,
    DMEditorMapCreate,
    DMEditorMapVersionCreate,
    DMEditorMapVersionUpdate,
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
from services.map_export_service import MapExportService
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.auth_dependencies import get_current_user
from services.authorization import require_same_user


router = APIRouter(tags=["dm-dashboard"])


def _current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.id


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
def list_dm_campaigns(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_same_user(user_id, current_user)
    return DMDashboardService(db).list_dm_campaigns(current_user.id)




@router.patch("/api/campaigns/{campaign_id}/dm-settings", response_model=DMCampaignSummary)
def update_dm_campaign(
    campaign_id: int,
    data: DMCampaignUpdate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).update_campaign(campaign_id, user_id, data)
    except (NotFoundError, ForbiddenOperationError, ValueError) as exc:
        _raise_http(exc)


@router.delete("/api/campaigns/{campaign_id}/dm-settings", status_code=204)
def delete_dm_campaign(
    campaign_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).delete_campaign(campaign_id, user_id)
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)
    return None


@router.delete("/api/campaigns/{campaign_id}/dm-maps/{map_id}", status_code=204)
def delete_dm_map(
    campaign_id: int,
    map_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).delete_map(campaign_id, user_id, map_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)
    return None


@router.get("/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/export")
def export_dm_map_version(
    campaign_id: int,
    map_version_id: int,
    format: str = Query(default="png"),
    mode: str = Query(default="world"),
    quality: str = Query(default="high"),
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db)._require_dm(campaign_id, user_id)
        world_map, _ = DMDashboardService(db)._require_map_version(campaign_id, map_version_id)
        payload, media_type, filename = MapExportService(db).render(map_version_id, format, mode=mode, quality=quality)
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
    except (NotFoundError, ForbiddenOperationError, ValueError) as exc:
        _raise_http(exc)


@router.get("/api/campaigns/{campaign_id}/dm-dashboard", response_model=DMDashboardResponse)
def dm_dashboard(
    campaign_id: int,
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        expedition = DMDashboardService(db).return_expedition(campaign_id, expedition_id, user_id)
        return ExpeditionResponse.model_validate(expedition)
    except (NotFoundError, ForbiddenOperationError, ConflictError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-expeditions/{expedition_id}/pois/{poi_id}/reveal",
    status_code=201,
)
def reveal_dm_poi(
    campaign_id: int,
    expedition_id: int,
    poi_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        observations = DMDashboardService(db).reveal_poi_to_expedition(
            campaign_id, expedition_id, poi_id, user_id
        )
        return {
            "expedition_id": expedition_id,
            "poi_id": poi_id,
            "observed_game_minute": observations[0].observed_game_minute if observations else None,
            "character_ids": [row.character_id for row in observations],
        }
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-expeditions/{expedition_id}/pois/{poi_id}/hide",
    status_code=201,
)
def hide_dm_poi(
    campaign_id: int,
    expedition_id: int,
    poi_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        observations = DMDashboardService(db).hide_poi_from_expedition(
            campaign_id, expedition_id, poi_id, user_id
        )
        return {
            "expedition_id": expedition_id,
            "poi_id": poi_id,
            "observed_game_minute": observations[0].observed_game_minute if observations else None,
            "character_ids": [row.character_id for row in observations],
            "hidden": True,
        }
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-members",
    response_model=DMMemberSummary,
    status_code=201,
)
def dm_add_member(
    campaign_id: int,
    data: DMMemberAdd,
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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


@router.patch(
    "/api/campaigns/{campaign_id}/dm-maps/{map_id}/versions/{map_version_id}/from-editor",
    response_model=MapSnapshotResponse,
)
def dm_update_map_version_from_editor(
    campaign_id: int,
    map_id: int,
    map_version_id: int,
    data: DMEditorMapVersionUpdate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        world_map, version, hex_count = DMDashboardService(db).update_map_version_from_editor(
            campaign_id, user_id, map_id, map_version_id, data
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
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).get_map_workbench(campaign_id, user_id, map_version_id)
    except (NotFoundError, ForbiddenOperationError) as exc:
        _raise_http(exc)




@router.get(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/world-editor-snapshot",
    response_model=DMWorldEditorSnapshot,
)
def dm_world_editor_snapshot(
    campaign_id: int,
    map_version_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).world_editor_snapshot(campaign_id, user_id, map_version_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.put(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/world-editor-snapshot",
    response_model=DMMapWorkbenchResponse,
)
def dm_restore_world_editor_snapshot(
    campaign_id: int,
    map_version_id: int,
    data: DMWorldEditorSnapshot,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).restore_world_editor_snapshot(campaign_id, user_id, map_version_id, data)
        return DMDashboardService(db).get_map_workbench(campaign_id, user_id, map_version_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.delete(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/hex-features",
    response_model=DMMapWorkbenchResponse,
)
def dm_clear_hex_features(
    campaign_id: int,
    map_version_id: int,
    data: DMHexFeatureClear,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).clear_hex_features(campaign_id, user_id, map_version_id, data.q, data.r)
        return DMDashboardService(db).get_map_workbench(campaign_id, user_id, map_version_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).update_poi(campaign_id, user_id, poi_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.delete("/api/campaigns/{campaign_id}/dm-pois/{poi_id}", status_code=204)
def dm_delete_poi(
    campaign_id: int,
    poi_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).delete_poi(campaign_id, user_id, poi_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/linear-features",
    response_model=list[MapEdgeResponse],
    status_code=201,
)
def dm_create_linear_feature(
    campaign_id: int,
    map_version_id: int,
    data: DMLinearFeatureCreate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_linear_feature(campaign_id, user_id, map_version_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.post(
    "/api/campaigns/{campaign_id}/dm-linear-features/merge",
    response_model=list[MapEdgeResponse],
)
def dm_merge_linear_features(
    campaign_id: int,
    data: DMLinearFeatureMerge,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).merge_linear_features(campaign_id, user_id, data.edge_ids)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.patch(
    "/api/campaigns/{campaign_id}/dm-linear-features/{edge_id}",
    response_model=list[MapEdgeResponse],
)
def dm_update_linear_feature(
    campaign_id: int,
    edge_id: int,
    data: DMLinearFeatureUpdate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).update_linear_feature(campaign_id, user_id, edge_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.patch(
    "/api/campaigns/{campaign_id}/dm-area-features/{area_id}",
)
def dm_update_area_feature(
    campaign_id: int,
    area_id: int,
    data: DMAreaFeatureUpdate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).update_area_feature(campaign_id, user_id, area_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.delete("/api/campaigns/{campaign_id}/dm-linear-features/{edge_id}", status_code=204)
def dm_delete_linear_feature(
    campaign_id: int,
    edge_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).delete_linear_feature(campaign_id, user_id, edge_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)
    return None


@router.delete("/api/campaigns/{campaign_id}/dm-area-features/{area_id}", status_code=204)
def dm_delete_area_feature(
    campaign_id: int,
    area_id: int,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        DMDashboardService(db).delete_area_feature(campaign_id, user_id, area_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)
    return None


@router.post(
    "/api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/area-features",
    status_code=201,
)
def dm_create_area_feature(
    campaign_id: int,
    map_version_id: int,
    data: DMAreaFeatureCreate,
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_area_feature(campaign_id, user_id, map_version_id, data)
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
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
    user_id: int = Depends(_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return DMDashboardService(db).create_edge_world_event(campaign_id, user_id, edge_id, data)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_http(exc)
