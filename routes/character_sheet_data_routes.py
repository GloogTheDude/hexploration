from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.character_sheet_data_dto import CharacterSheetDataVersionResponse, CharacterSheetForm
from services.character_sheet_data_service import (
    CharacterSheetDataExportError,
    CharacterSheetDataForbiddenError,
    CharacterSheetDataNotFoundError,
    CharacterSheetDataService,
)
from services.character_sheet_service import CharacterSheetTemplateError


router = APIRouter(prefix="/api/characters/{character_id}/sheet-data", tags=["character sheet data"])


def _response(item) -> CharacterSheetDataVersionResponse:
    return CharacterSheetDataVersionResponse.model_validate(item)


def _raise(exc: Exception) -> None:
    if isinstance(exc, CharacterSheetDataForbiddenError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, CharacterSheetDataNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CharacterSheetTemplateError):
        raise HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, CharacterSheetDataExportError):
        raise HTTPException(status_code=422, detail=str(exc))
    raise HTTPException(status_code=500, detail="Character sheet error")


@router.post("/initialize", response_model=CharacterSheetDataVersionResponse, status_code=status.HTTP_201_CREATED)
def initialize_sheet(character_id: int, user_id: int, db: Session = Depends(get_db)) -> CharacterSheetDataVersionResponse:
    try:
        return _response(CharacterSheetDataService(db).initialize(character_id, user_id))
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError) as exc:
        _raise(exc)


@router.post("", response_model=CharacterSheetDataVersionResponse, status_code=status.HTTP_201_CREATED)
def save_sheet(character_id: int, user_id: int, form: CharacterSheetForm, db: Session = Depends(get_db)) -> CharacterSheetDataVersionResponse:
    try:
        return _response(CharacterSheetDataService(db).save(character_id, user_id, form))
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError) as exc:
        _raise(exc)


@router.get("", response_model=list[CharacterSheetDataVersionResponse])
def sheet_history(character_id: int, user_id: int, db: Session = Depends(get_db)) -> list[CharacterSheetDataVersionResponse]:
    try:
        return [_response(item) for item in CharacterSheetDataService(db).history(character_id, user_id)]
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError) as exc:
        _raise(exc)


@router.get("/current", response_model=CharacterSheetDataVersionResponse)
def current_sheet(character_id: int, user_id: int, db: Session = Depends(get_db)) -> CharacterSheetDataVersionResponse:
    try:
        return _response(CharacterSheetDataService(db).current(character_id, user_id))
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError) as exc:
        _raise(exc)


def _pdf_response(service: CharacterSheetDataService, item, filename: str) -> Response:
    content = service.export_pdf(item)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/current/pdf")
def export_current_pdf(character_id: int, user_id: int, db: Session = Depends(get_db)) -> Response:
    service = CharacterSheetDataService(db)
    try:
        item = service.current(character_id, user_id)
        return _pdf_response(service, item, f"character-{character_id}-sheet-v{item.version}.pdf")
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError, CharacterSheetTemplateError, CharacterSheetDataExportError) as exc:
        _raise(exc)


@router.get("/{version}/pdf")
def export_version_pdf(character_id: int, version: int, user_id: int, db: Session = Depends(get_db)) -> Response:
    service = CharacterSheetDataService(db)
    try:
        item = service.by_version(character_id, version, user_id)
        return _pdf_response(service, item, f"character-{character_id}-sheet-v{version}.pdf")
    except (CharacterSheetDataForbiddenError, CharacterSheetDataNotFoundError, CharacterSheetTemplateError, CharacterSheetDataExportError) as exc:
        _raise(exc)
