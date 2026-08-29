from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    checksum_sha256: str


class LocalFileStorage:
    """Store uploaded files outside PostgreSQL.

    storage_key is deliberately relative to the storage root so the database
    does not depend on an absolute path. This makes a later move to S3-like
    object storage much easier.
    """

    def __init__(self, root: str | Path = "storage/uploads") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_character_sheet(
        self,
        character_id: int,
        version: int,
        file: UploadFile,
    ) -> StoredFile:
        relative_dir = Path("characters") / str(character_id) / "sheets"
        relative_name = f"v{version}-{uuid4().hex}.pdf"
        storage_key = (relative_dir / relative_name).as_posix()

        destination = self._resolve_key(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()

        try:
            with destination.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        return StoredFile(
            storage_key=storage_key,
            checksum_sha256=digest.hexdigest(),
        )


    def save_character_sheet_path(
        self,
        character_id: int,
        version: int,
        source: str | Path,
    ) -> StoredFile:
        """Copy an existing PDF into versioned character-sheet storage."""
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)

        relative_dir = Path("characters") / str(character_id) / "sheets"
        relative_name = f"v{version}-{uuid4().hex}.pdf"
        storage_key = (relative_dir / relative_name).as_posix()
        destination = self._resolve_key(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        with source_path.open("rb") as src, destination.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                digest.update(chunk)
                dst.write(chunk)

        return StoredFile(storage_key=storage_key, checksum_sha256=digest.hexdigest())

    def path_for(self, storage_key: str) -> Path:
        path = self._resolve_key(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path

    def delete(self, storage_key: str) -> None:
        self._resolve_key(storage_key).unlink(missing_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()

        # Prevent "../" or an absolute path stored in the database from
        # escaping storage/uploads.
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Invalid storage key")

        return candidate
