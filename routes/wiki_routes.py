from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.wiki_dto import (
    CampaignWikiResponse,
    ExpeditionReportCreate,
    ExpeditionReportPublishResponse,
    ExpeditionReportResponse,
    WikiPageResponse,
    WikiPageStateResponse,
    WikiRevisionResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.wiki_service import WikiService

router = APIRouter(tags=["wiki"])


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


def _state_payload(page, revision, as_of_game_minute):
    return WikiPageStateResponse(
        page=WikiPageResponse.model_validate(page),
        as_of_game_minute=as_of_game_minute,
        revision=WikiRevisionResponse.model_validate(revision),
    )


@router.post(
    "/api/expeditions/{expedition_id}/report",
    response_model=ExpeditionReportPublishResponse,
    status_code=status.HTTP_201_CREATED,
)
def publish_expedition_report(
    expedition_id: int,
    data: ExpeditionReportCreate,
    db: Session = Depends(get_db),
):
    try:
        report, published = WikiService(db).publish_expedition_report(
            expedition_id,
            data,
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)

    return ExpeditionReportPublishResponse(
        report=ExpeditionReportResponse.model_validate(report),
        published_pages=[
            _state_payload(page, revision, report.published_game_minute)
            for page, revision in published
        ],
    )


@router.get(
    "/api/expeditions/{expedition_id}/report",
    response_model=ExpeditionReportResponse,
)
def get_expedition_report(
    expedition_id: int,
    db: Session = Depends(get_db),
):
    try:
        return ExpeditionReportResponse.model_validate(
            WikiService(db).get_expedition_report(expedition_id)
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)


@router.get(
    "/api/campaigns/{campaign_id}/wiki",
    response_model=CampaignWikiResponse,
)
def list_campaign_wiki(
    campaign_id: int,
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        states = WikiService(db).list_campaign_wiki(
            campaign_id,
            as_of_game_minute=as_of_game_minute,
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)

    return CampaignWikiResponse(
        campaign_id=campaign_id,
        as_of_game_minute=as_of_game_minute,
        pages=[
            _state_payload(page, revision, as_of_game_minute)
            for page, revision in states
        ],
    )


@router.get(
    "/api/campaigns/{campaign_id}/wiki/pages/{page_id}",
    response_model=WikiPageStateResponse,
)
def get_wiki_page(
    campaign_id: int,
    page_id: int,
    as_of_game_minute: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    try:
        page, revision = WikiService(db).get_page_state(
            page_id,
            campaign_id=campaign_id,
            as_of_game_minute=as_of_game_minute,
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return _state_payload(page, revision, as_of_game_minute)
