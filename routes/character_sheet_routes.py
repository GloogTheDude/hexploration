from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import CharacterSheetVersion, User
from db.session import get_db
from services.auth_dependencies import get_current_user
from services.authorization import require_character_access
from services.character_sheet_service import (
    CharacterNotFoundError, CharacterSheetForbiddenError, CharacterSheetService,
    CharacterSheetTemplateError, InvalidCharacterSheetError, SheetNotFoundError,
)

router = APIRouter(prefix="/api/characters/{character_id}/sheets", tags=["character sheets"])


class CharacterSheetResponse(BaseModel):
    id: int
    character_id: int
    version: int
    original_filename: str
    mime_type: str
    checksum_sha256: str | None
    campaign_game_minute: int | None
    expedition_id: int | None
    created_at: datetime
    is_current: bool

    @classmethod
    def from_model(cls, sheet: CharacterSheetVersion) -> "CharacterSheetResponse":
        return cls(id=sheet.id, character_id=sheet.character_id, version=sheet.version,
                   original_filename=sheet.original_filename, mime_type=sheet.mime_type,
                   checksum_sha256=sheet.checksum_sha256, campaign_game_minute=sheet.campaign_game_minute,
                   expedition_id=sheet.expedition_id, created_at=sheet.created_at, is_current=sheet.is_current)


def _errors(exc: Exception) -> HTTPException:
    if isinstance(exc, CharacterNotFoundError): return HTTPException(404, "Character not found")
    if isinstance(exc, CharacterSheetForbiddenError): return HTTPException(403, str(exc))
    if isinstance(exc, SheetNotFoundError): return HTTPException(404, "Character sheet not found")
    if isinstance(exc, InvalidCharacterSheetError): return HTTPException(415, str(exc))
    if isinstance(exc, CharacterSheetTemplateError): return HTTPException(503, str(exc))
    return HTTPException(500, "Character sheet error")


@router.post("/template", response_model=CharacterSheetResponse, status_code=status.HTTP_201_CREATED)
def create_blank_character_sheet(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> CharacterSheetResponse:
    try:
        return CharacterSheetResponse.from_model(CharacterSheetService(db).create_from_template(character_id, current_user.id))
    except (CharacterNotFoundError, CharacterSheetForbiddenError, CharacterSheetTemplateError) as exc:
        raise _errors(exc)


@router.post("", response_model=CharacterSheetResponse, status_code=status.HTTP_201_CREATED)
async def upload_character_sheet(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), file: UploadFile = File(...),
                                 campaign_game_minute: int | None = Form(default=None),
                                 expedition_id: int | None = Form(default=None),
                                 db: Session = Depends(get_db)) -> CharacterSheetResponse:
    try:
        sheet = await CharacterSheetService(db).upload(character_id, file, campaign_game_minute, expedition_id, user_id=current_user.id)
        return CharacterSheetResponse.from_model(sheet)
    except (CharacterNotFoundError, CharacterSheetForbiddenError, InvalidCharacterSheetError) as exc:
        raise _errors(exc)


@router.get("", response_model=list[CharacterSheetResponse])
def list_character_sheets(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> list[CharacterSheetResponse]:
    try:
        return [CharacterSheetResponse.from_model(s) for s in CharacterSheetService(db).history(character_id, current_user.id)]
    except (CharacterNotFoundError, CharacterSheetForbiddenError) as exc:
        raise _errors(exc)


@router.get("/current", response_model=CharacterSheetResponse)
def get_current_character_sheet_metadata(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> CharacterSheetResponse:
    try:
        return CharacterSheetResponse.from_model(CharacterSheetService(db).current(character_id, current_user.id))
    except (CharacterNotFoundError, CharacterSheetForbiddenError, SheetNotFoundError) as exc:
        raise _errors(exc)


@router.get("/current/pdf", response_class=FileResponse)
def open_current_character_sheet(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> FileResponse:
    service = CharacterSheetService(db)
    try:
        sheet = service.current(character_id, current_user.id)
        path = service.path_for(sheet)
    except (CharacterNotFoundError, CharacterSheetForbiddenError, SheetNotFoundError) as exc:
        raise _errors(exc)
    return FileResponse(path=path, media_type="application/pdf", headers={"Content-Disposition": "inline"})


@router.get("/{version}/pdf", response_class=FileResponse)
def open_character_sheet_version(character_id: int, version: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> FileResponse:
    service = CharacterSheetService(db)
    try:
        sheet = service.version(character_id, version, current_user.id)
        path = service.path_for(sheet)
    except (CharacterNotFoundError, CharacterSheetForbiddenError, SheetNotFoundError) as exc:
        raise _errors(exc)
    return FileResponse(path=path, media_type="application/pdf", headers={"Content-Disposition": "inline"})
