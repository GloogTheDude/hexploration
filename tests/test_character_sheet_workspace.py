from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole, Character, CharacterStatus, User
from services.character_sheet_service import CharacterSheetForbiddenError, CharacterSheetService
from storage.local_storage import LocalFileStorage


def make_character(db: Session, campaign: Campaign) -> tuple[User, Character]:
    user = User(username="sheet_owner", email="sheet@example.com", password_hash="x")
    db.add(user)
    db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=user.id, role=CampaignRole.PLAYER))
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=user.id,
        name="Flubert",
        race="Elf",
        character_class="Wizard",
        level=1,
        description=None,
        status=CharacterStatus.ACTIVE,
        current_game_minute=42,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return user, character


def test_blank_template_becomes_version_one(db: Session, campaign: Campaign, tmp_path: Path, monkeypatch):
    user, character = make_character(db, campaign)
    template = tmp_path / "blank.pdf"
    template.write_bytes(b"%PDF-1.4\n% blank test sheet\n%%EOF\n")
    monkeypatch.setenv("CHARACTER_SHEET_TEMPLATE_PATH", str(template))

    storage = LocalFileStorage(tmp_path / "uploads")
    service = CharacterSheetService(db, storage)
    sheet = service.create_from_template(character.id, user.id)

    assert sheet.version == 1
    assert sheet.is_current is True
    assert sheet.campaign_game_minute == 42
    assert service.path_for(sheet).read_bytes() == template.read_bytes()


def test_template_initialization_is_idempotent(db: Session, campaign: Campaign, tmp_path: Path, monkeypatch):
    user, character = make_character(db, campaign)
    template = tmp_path / "blank.pdf"
    template.write_bytes(b"%PDF-1.4\n%%EOF\n")
    monkeypatch.setenv("CHARACTER_SHEET_TEMPLATE_PATH", str(template))
    service = CharacterSheetService(db, LocalFileStorage(tmp_path / "uploads"))

    first = service.create_from_template(character.id, user.id)
    second = service.create_from_template(character.id, user.id)

    assert first.id == second.id
    assert len(service.history(character.id, user.id)) == 1


def test_other_player_cannot_access_sheet(db: Session, campaign: Campaign, tmp_path: Path, monkeypatch):
    owner, character = make_character(db, campaign)
    stranger = User(username="stranger", email="stranger@example.com", password_hash="x")
    db.add(stranger)
    db.commit()
    template = tmp_path / "blank.pdf"
    template.write_bytes(b"%PDF-1.4\n%%EOF\n")
    monkeypatch.setenv("CHARACTER_SHEET_TEMPLATE_PATH", str(template))
    service = CharacterSheetService(db, LocalFileStorage(tmp_path / "uploads"))
    service.create_from_template(character.id, owner.id)

    with pytest.raises(CharacterSheetForbiddenError):
        service.history(character.id, stranger.id)


def test_dashboard_exposes_db_backed_character_sheet_workspace():
    html = Path("static/dashboard.html").read_text()
    js = Path("static/js/dashboard.js").read_text()
    assert 'id="sheet-modal"' in html
    assert 'id="sheet-data-form"' in html
    assert 'name="strength"' in html
    assert 'id="sheet-export-pdf"' in html
    assert 'data-character-sheet' in js
    assert '/sheet-data/initialize?user_id=' in js
    assert '/sheet-data?user_id=' in js
    assert 'sheetFormPayload()' in js
