from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.wiki_dto import (
    ExpeditionRecallLibraryResponse,
    RecallRecordResponse,
    RecallRequest,
    RecallSearchResponse,
    RecallStatusResponse,
    RecalledPageResponse,
    WikiPageResponse,
    WikiPageStateResponse,
    WikiRevisionResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.recall_service import RecallService

router = APIRouter(tags=["knowledge-recall"])


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


def _recalled_payload(state) -> RecalledPageResponse:
    return RecalledPageResponse(
        recall=RecallRecordResponse.model_validate(state.recall),
        page=WikiPageResponse.model_validate(state.page),
        revision=WikiRevisionResponse.model_validate(state.revision),
    )


@router.get(
    "/api/expeditions/{expedition_id}/recall/status",
    response_model=RecallStatusResponse,
)
def recall_status(
    expedition_id: int,
    character_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    try:
        value = RecallService(db).status(expedition_id, character_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return RecallStatusResponse(**value.__dict__)


@router.get(
    "/api/expeditions/{expedition_id}/recall/search",
    response_model=RecallSearchResponse,
)
def search_recallable_wiki(
    expedition_id: int,
    character_id: int = Query(gt=0),
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
):
    service = RecallService(db)
    try:
        status_value = service.status(expedition_id, character_id)
        results = service.search_available(expedition_id, character_id, q)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return RecallSearchResponse(
        expedition_id=expedition_id,
        character_id=character_id,
        knowledge_cutoff_game_minute=status_value.knowledge_cutoff_game_minute,
        results=[
            WikiPageStateResponse(
                page=WikiPageResponse.model_validate(page),
                as_of_game_minute=status_value.knowledge_cutoff_game_minute,
                revision=WikiRevisionResponse.model_validate(revision),
            )
            for page, revision in results
        ],
    )


@router.post(
    "/api/expeditions/{expedition_id}/recall",
    response_model=RecalledPageResponse,
    status_code=status.HTTP_201_CREATED,
)
def recall_page(
    expedition_id: int,
    data: RecallRequest,
    db: Session = Depends(get_db),
):
    try:
        state = RecallService(db).recall_page(
            expedition_id,
            data.character_id,
            data.page_id,
        )
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return _recalled_payload(state)


@router.get(
    "/api/expeditions/{expedition_id}/recall",
    response_model=ExpeditionRecallLibraryResponse,
)
def list_recalled_pages(
    expedition_id: int,
    db: Session = Depends(get_db),
):
    try:
        states = RecallService(db).list_unlocked(expedition_id)
    except (NotFoundError, ForbiddenOperationError, ConflictError, ValueError) as exc:
        _raise_domain_error(exc)
    return ExpeditionRecallLibraryResponse(
        expedition_id=expedition_id,
        pages=[_recalled_payload(state) for state in states],
    )
