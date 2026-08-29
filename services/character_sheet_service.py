from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from db.models import Character, CharacterSheetVersion, Expedition
from repositories.character_sheet_repository import CharacterSheetRepository
from storage.local_storage import LocalFileStorage


MAX_PDF_SIZE = 20 * 1024 * 1024


class CharacterNotFoundError(Exception):
    pass


class SheetNotFoundError(Exception):
    pass


class InvalidCharacterSheetError(Exception):
    pass


@dataclass(frozen=True)
class CharacterSheetData:
    id: int
    character_id: int
    version: int
    original_filename: str
    mime_type: str
    checksum_sha256: str | None
    campaign_game_minute: int | None
    expedition_id: int | None
    created_at: object
    is_current: bool


class CharacterSheetService:
    def __init__(
        self,
        db: Session,
        file_storage: LocalFileStorage | None = None,
    ) -> None:
        self.db = db
        self.repo = CharacterSheetRepository(db)
        self.storage = file_storage or LocalFileStorage()

    async def upload(
        self,
        character_id: int,
        file: UploadFile,
        campaign_game_minute: int | None = None,
        expedition_id: int | None = None,
    ) -> CharacterSheetVersion:
        character = self.repo.get_character_for_update(character_id)
        if character is None:
            raise CharacterNotFoundError(character_id)

        if campaign_game_minute is not None and campaign_game_minute < 0:
            raise InvalidCharacterSheetError(
                "campaign_game_minute cannot be negative."
            )

        if expedition_id is not None:
            expedition = self.db.get(Expedition, expedition_id)
            if expedition is None:
                raise InvalidCharacterSheetError(
                    f"Expedition {expedition_id} does not exist."
                )
            if expedition.campaign_id != character.campaign_id:
                raise InvalidCharacterSheetError(
                    "Character and expedition must belong to the same campaign."
                )

        await self._validate_pdf(file)

        version = self.repo.next_version(character_id)
        stored = None

        try:
            stored = await self.storage.save_character_sheet(
                character_id=character_id,
                version=version,
                file=file,
            )

            self.repo.clear_current(character_id)

            sheet = CharacterSheetVersion(
                character_id=character_id,
                version=version,
                storage_key=stored.storage_key,
                original_filename=Path(file.filename or "character-sheet.pdf").name,
                mime_type="application/pdf",
                checksum_sha256=stored.checksum_sha256,
                campaign_game_minute=campaign_game_minute,
                expedition_id=expedition_id,
                is_current=True,
            )

            self.repo.add(sheet)
            self.db.commit()
            self.db.refresh(sheet)
            return sheet

        except Exception:
            self.db.rollback()
            if stored is not None:
                self.storage.delete(stored.storage_key)
            raise

    def current(self, character_id: int) -> CharacterSheetVersion:
        if self.db.get(Character, character_id) is None:
            raise CharacterNotFoundError(character_id)

        sheet = self.repo.current(character_id)
        if sheet is None:
            raise SheetNotFoundError(character_id)
        return sheet

    def version(self, character_id: int, version: int) -> CharacterSheetVersion:
        sheet = self.repo.by_version(character_id, version)
        if sheet is None:
            raise SheetNotFoundError((character_id, version))
        return sheet

    def history(self, character_id: int) -> list[CharacterSheetVersion]:
        if self.db.get(Character, character_id) is None:
            raise CharacterNotFoundError(character_id)
        return self.repo.history(character_id)

    def path_for(self, sheet: CharacterSheetVersion) -> Path:
        try:
            return self.storage.path_for(sheet.storage_key)
        except FileNotFoundError as exc:
            raise SheetNotFoundError(sheet.id) from exc

    async def _validate_pdf(self, file: UploadFile) -> None:
        if file.content_type not in {None, "application/pdf"}:
            raise InvalidCharacterSheetError("The uploaded file must be a PDF.")

        header = await file.read(5)
        await file.seek(0)

        if header != b"%PDF-":
            raise InvalidCharacterSheetError("The uploaded file is not a valid PDF.")

        # UploadFile.seek() accepts only an absolute offset. The wrapped
        # SpooledTemporaryFile supports the normal seek(offset, whence) API.
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > MAX_PDF_SIZE:
            raise InvalidCharacterSheetError("The PDF exceeds the 20 MiB limit.")
