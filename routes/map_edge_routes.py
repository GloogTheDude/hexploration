from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.map_edge_dto import MapEdgeCreate, MapEdgeResponse
from services.errors import ConflictError, NotFoundError
from services.map_edge_service import MapEdgeService


router = APIRouter(tags=["map edges"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.post(
    "/api/map-versions/{map_version_id}/edges",
    response_model=MapEdgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_map_edge(
    map_version_id: int,
    data: MapEdgeCreate,
    db: Session = Depends(get_db),
):
    try:
        return MapEdgeService(db).create(map_version_id, data)
    except (NotFoundError, ConflictError, ValueError) as exc:
        _raise_http(exc)


@router.get(
    "/api/map-versions/{map_version_id}/edges",
    response_model=list[MapEdgeResponse],
)
def list_map_edges(map_version_id: int, db: Session = Depends(get_db)):
    try:
        return MapEdgeService(db).list_for_map_version(map_version_id)
    except NotFoundError as exc:
        _raise_http(exc)


@router.get(
    "/api/map-edges/{edge_id}",
    response_model=MapEdgeResponse,
)
def get_map_edge(edge_id: int, db: Session = Depends(get_db)):
    try:
        return MapEdgeService(db).get(edge_id)
    except NotFoundError as exc:
        _raise_http(exc)


@router.delete(
    "/api/map-edges/{edge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_map_edge(edge_id: int, db: Session = Depends(get_db)):
    try:
        MapEdgeService(db).delete(edge_id)
    except NotFoundError as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
