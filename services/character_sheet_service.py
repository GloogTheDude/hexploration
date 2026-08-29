from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import requests
from fastapi import UploadFile
from sqlalchemy.orm import Session

from db.models import Character, CharacterSheetVersion, Expedition
from repositories.character_sheet_repository import CharacterSheetRepository
from storage.local_storage import LocalFileStorage


MAX_PDF_SIZE = 20 * 1024 * 1024
DEFAULT_TEMPLATE_URL = "https://media.wizards.com/2016/dnd/downloads/5E_CharacterSheet_Fillable.pdf"


class CharacterNotFoundError(Exception):
    pass


class SheetNotFoundError(Exception):
    pass


class InvalidCharacterSheetError(Exception):
    pass


class CharacterSheetTemplateError(Exception):
    pass


class CharacterSheetForbiddenError(Exception):
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
    def __init__(self, db: Session, file_storage: LocalFileStorage | None = None) -> None:
        self.db = db
        self.repo = CharacterSheetRepository(db)
        self.storage = file_storage or LocalFileStorage()

    def require_owner(self, character_id: int, user_id: int) -> Character:
        character = self.db.get(Character, character_id)
        if character is None:
            raise CharacterNotFoundError(character_id)
        if character.owner_user_id != user_id:
            raise CharacterSheetForbiddenError("A player can only manage their own character sheet.")
        return character

    async def upload(
        self,
        character_id: int,
        file: UploadFile,
        campaign_game_minute: int | None = None,
        expedition_id: int | None = None,
        user_id: int | None = None,
    ) -> CharacterSheetVersion:
        character = self.repo.get_character_for_update(character_id)
        if character is None:
            raise CharacterNotFoundError(character_id)
        if user_id is not None and character.owner_user_id != user_id:
            raise CharacterSheetForbiddenError("A player can only manage their own character sheet.")

        if campaign_game_minute is not None and campaign_game_minute < 0:
            raise InvalidCharacterSheetError("campaign_game_minute cannot be negative.")

        if expedition_id is not None:
            expedition = self.db.get(Expedition, expedition_id)
            if expedition is None:
                raise InvalidCharacterSheetError(f"Expedition {expedition_id} does not exist.")
            if expedition.campaign_id != character.campaign_id:
                raise InvalidCharacterSheetError("Character and expedition must belong to the same campaign.")

        await self._validate_pdf(file)
        version = self.repo.next_version(character_id)
        stored = None

        try:
            stored = await self.storage.save_character_sheet(character_id=character_id, version=version, file=file)
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

    def create_from_template(self, character_id: int, user_id: int) -> CharacterSheetVersion:
        character = self.require_owner(character_id, user_id)
        current = self.repo.current(character_id)
        if current is not None:
            return current

        template = self._ensure_template()
        version = self.repo.next_version(character_id)
        stored = None
        try:
            stored = self.storage.save_character_sheet_path(character_id, version, template)
            sheet = CharacterSheetVersion(
                character_id=character_id,
                version=version,
                storage_key=stored.storage_key,
                original_filename="5E_CharacterSheet_Fillable.pdf",
                mime_type="application/pdf",
                checksum_sha256=stored.checksum_sha256,
                campaign_game_minute=character.current_game_minute,
                expedition_id=None,
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

    def current(self, character_id: int, user_id: int | None = None) -> CharacterSheetVersion:
        if user_id is not None:
            self.require_owner(character_id, user_id)
        elif self.db.get(Character, character_id) is None:
            raise CharacterNotFoundError(character_id)
        sheet = self.repo.current(character_id)
        if sheet is None:
            raise SheetNotFoundError(character_id)
        return sheet

    def version(self, character_id: int, version: int, user_id: int | None = None) -> CharacterSheetVersion:
        if user_id is not None:
            self.require_owner(character_id, user_id)
        sheet = self.repo.by_version(character_id, version)
        if sheet is None:
            raise SheetNotFoundError((character_id, version))
        return sheet

    def history(self, character_id: int, user_id: int | None = None) -> list[CharacterSheetVersion]:
        if user_id is not None:
            self.require_owner(character_id, user_id)
        elif self.db.get(Character, character_id) is None:
            raise CharacterNotFoundError(character_id)
        return self.repo.history(character_id)

    def path_for(self, sheet: CharacterSheetVersion) -> Path:
        try:
            return self.storage.path_for(sheet.storage_key)
        except FileNotFoundError as exc:
            raise SheetNotFoundError(sheet.id) from exc

    def _template_cache_path(self) -> Path:
        configured = os.getenv("CHARACTER_SHEET_TEMPLATE_PATH")
        if configured:
            return Path(configured).expanduser().resolve()
        path = Path("storage/templates/5E_CharacterSheet_Fillable.pdf").resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_template(self) -> Path:
        path = self._template_cache_path()
        if path.is_file():
            self._validate_template_bytes(path.read_bytes())
            return path

        configured = os.getenv("CHARACTER_SHEET_TEMPLATE_PATH")
        if configured:
            raise CharacterSheetTemplateError(f"Configured template does not exist: {path}")

        url = os.getenv("CHARACTER_SHEET_TEMPLATE_URL", DEFAULT_TEMPLATE_URL)
        try:
            response = requests.get(url, timeout=20, headers={"User-Agent": "Hexploration/0.26"})
            response.raise_for_status()
            content = response.content
            self._validate_template_bytes(content)
            path.write_bytes(content)
            return path
        except CharacterSheetTemplateError:
            raise
        except Exception as exc:
            raise CharacterSheetTemplateError(
                "Unable to obtain the blank character-sheet template. "
                "Download the official fillable PDF and set CHARACTER_SHEET_TEMPLATE_PATH in .env."
            ) from exc

    @staticmethod
    def _validate_template_bytes(content: bytes) -> None:
        if not content.startswith(b"%PDF-"):
            raise CharacterSheetTemplateError("Character-sheet template is not a valid PDF.")
        if len(content) > MAX_PDF_SIZE:
            raise CharacterSheetTemplateError("Character-sheet template exceeds the 20 MiB limit.")

    async def _validate_pdf(self, file: UploadFile) -> None:
        if file.content_type not in {None, "application/pdf"}:
            raise InvalidCharacterSheetError("The uploaded file must be a PDF.")
        header = await file.read(5)
        await file.seek(0)
        if header != b"%PDF-":
            raise InvalidCharacterSheetError("The uploaded file is not a valid PDF.")
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > MAX_PDF_SIZE:
            raise InvalidCharacterSheetError("The PDF exceeds the 20 MiB limit.")
