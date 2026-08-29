from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import CharacterSheetVersion
from db.session import get_db
from services.character_sheet_service import (
    CharacterNotFoundError,
    CharacterSheetService,
    InvalidCharacterSheetError,
    SheetNotFoundError,
)


router = APIRouter(
    prefix="/api/characters/{character_id}/sheets",
    tags=["character sheets"],
)


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
        return cls(
            id=sheet.id,
            character_id=sheet.character_id,
            version=sheet.version,
            original_filename=sheet.original_filename,
            mime_type=sheet.mime_type,
            checksum_sha256=sheet.checksum_sha256,
            campaign_game_minute=sheet.campaign_game_minute,
            expedition_id=sheet.expedition_id,
            created_at=sheet.created_at,
            is_current=sheet.is_current,
        )


def _service(db: Session) -> CharacterSheetService:
    return CharacterSheetService(db)


@router.post(
    "",
    response_model=CharacterSheetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_character_sheet(
    character_id: int,
    file: UploadFile = File(...),
    campaign_game_minute: int | None = Form(default=None),
    expedition_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> CharacterSheetResponse:
    service = _service(db)

    try:
        sheet = await service.upload(
            character_id=character_id,
            file=file,
            campaign_game_minute=campaign_game_minute,
            expedition_id=expedition_id,
        )
    except CharacterNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")
    except InvalidCharacterSheetError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    return CharacterSheetResponse.from_model(sheet)


@router.get("", response_model=list[CharacterSheetResponse])
def list_character_sheets(
    character_id: int,
    db: Session = Depends(get_db),
) -> list[CharacterSheetResponse]:
    service = _service(db)

    try:
        sheets = service.history(character_id)
    except CharacterNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")

    return [CharacterSheetResponse.from_model(sheet) for sheet in sheets]


@router.get("/current", response_model=CharacterSheetResponse)
def get_current_character_sheet_metadata(
    character_id: int,
    db: Session = Depends(get_db),
) -> CharacterSheetResponse:
    service = _service(db)

    try:
        sheet = service.current(character_id)
    except CharacterNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")
    except SheetNotFoundError:
        raise HTTPException(status_code=404, detail="No character sheet found")

    return CharacterSheetResponse.from_model(sheet)


@router.get("/current/pdf", response_class=FileResponse)
def open_current_character_sheet(
    character_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    service = _service(db)

    try:
        sheet = service.current(character_id)
        path = service.path_for(sheet)
    except CharacterNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")
    except SheetNotFoundError:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    return FileResponse(
        path=path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{version}/pdf", response_class=FileResponse)
def open_character_sheet_version(
    character_id: int,
    version: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    service = _service(db)

    try:
        sheet = service.version(character_id, version)
        path = service.path_for(sheet)
    except SheetNotFoundError:
        raise HTTPException(status_code=404, detail="Character sheet version not found")

    return FileResponse(
        path=path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
