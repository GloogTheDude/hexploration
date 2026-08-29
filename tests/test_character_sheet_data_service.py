import pytest
from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole, Character, CharacterStatus, User
from dto.character_sheet_data_dto import CharacterSheetForm
from services.character_sheet_data_service import (
    CharacterSheetDataForbiddenError,
    CharacterSheetDataService,
)


def make_character(db: Session, campaign: Campaign):
    owner = User(username="data_owner", email="data_owner@example.com", password_hash="x")
    db.add(owner)
    db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=owner.id,
        name="Flubert",
        race="Elf",
        character_class="Wizard",
        level=2,
        description="Remember the tower.",
        status=CharacterStatus.ACTIVE,
        current_game_minute=120,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return owner, character


def test_initialize_prefills_existing_character_data(db: Session, campaign: Campaign):
    owner, character = make_character(db, campaign)
    sheet = CharacterSheetDataService(db).initialize(character.id, owner.id)

    assert sheet.version == 1
    assert sheet.is_current is True
    assert sheet.campaign_game_minute == 120
    assert sheet.data["character_name"] == "Flubert"
    assert sheet.data["race"] == "Elf"
    assert sheet.data["character_class"] == "Wizard"
    assert sheet.data["level"] == 2
    assert sheet.data["player_name"] == "data_owner"
    assert sheet.data["notes"] == "Remember the tower."


def test_initialize_is_idempotent(db: Session, campaign: Campaign):
    owner, character = make_character(db, campaign)
    service = CharacterSheetDataService(db)
    first = service.initialize(character.id, owner.id)
    second = service.initialize(character.id, owner.id)

    assert first.id == second.id
    assert len(service.history(character.id, owner.id)) == 1


def test_save_creates_immutable_versions_and_marks_latest_current(db: Session, campaign: Campaign):
    owner, character = make_character(db, campaign)
    service = CharacterSheetDataService(db)
    first = service.initialize(character.id, owner.id)
    second = service.save(
        character.id,
        owner.id,
        CharacterSheetForm(character_name="Flubert", race="Elf", character_class="Wizard", level=3, strength=14),
    )

    history = service.history(character.id, owner.id)
    assert second.version == 2
    assert second.is_current is True
    assert history[0].version == 2
    assert history[1].version == 1
    assert history[1].data["level"] == 2
    db.refresh(first)
    assert first.is_current is False


def test_sheet_identity_updates_character_card(db: Session, campaign: Campaign):
    owner, character = make_character(db, campaign)
    service = CharacterSheetDataService(db)
    service.save(
        character.id,
        owner.id,
        CharacterSheetForm(character_name="Flubert II", race="High Elf", character_class="Abjurer", level=4),
    )
    db.refresh(character)
    assert character.name == "Flubert II"
    assert character.race == "High Elf"
    assert character.character_class == "Abjurer"
    assert character.level == 4


def test_other_user_cannot_read_or_write_db_sheet(db: Session, campaign: Campaign):
    owner, character = make_character(db, campaign)
    stranger = User(username="other", email="other@example.com", password_hash="x")
    db.add(stranger)
    db.commit()
    service = CharacterSheetDataService(db)
    service.initialize(character.id, owner.id)

    with pytest.raises(CharacterSheetDataForbiddenError):
        service.current(character.id, stranger.id)
    with pytest.raises(CharacterSheetDataForbiddenError):
        service.save(character.id, stranger.id, CharacterSheetForm(character_name="Hacker"))


def test_pdf_field_alias_matching_tolerates_spaces_and_case():
    resolved = CharacterSheetDataService._resolve_pdf_fields(
        ["CharacterName", "Race ", "DEXmod ", "Features and Traits"],
        {
            "character_name": "Flubert",
            "race": "Elf",
            "dexterity_mod": "+2",
            "features_traits": "Darkvision",
        },
    )
    assert resolved == {
        "CharacterName": "Flubert",
        "Race ": "Elf",
        "DEXmod ": "+2",
        "Features and Traits": "Darkvision",
    }


def test_pdf_values_derive_ability_modifiers():
    values = CharacterSheetDataService._pdf_values(
        CharacterSheetForm(character_name="Flubert", strength=8, dexterity=14, constitution=10, intelligence=18, wisdom=9, charisma=12)
    )
    assert values["strength_mod"] == "-1"
    assert values["dexterity_mod"] == "+2"
    assert values["constitution_mod"] == "+0"
    assert values["intelligence_mod"] == "+4"
    assert values["wisdom_mod"] == "-1"
    assert values["charisma_mod"] == "+1"


def test_pdf_export_updates_all_writer_pages_and_flattens(monkeypatch, tmp_path):
    """Regression: PdfWriter.pages is a virtual list, not a real list.

    Passing writer.pages directly to pypdf's update_page_form_field_values()
    silently skips every annotation. Using page=None makes pypdf iterate all
    pages itself; flatten=True also makes the values visible in browser PDF
    viewers instead of relying on AcroForm appearance regeneration.
    """
    from types import SimpleNamespace
    import services.character_sheet_data_service as module
    from services.character_sheet_service import CharacterSheetService

    template = tmp_path / "sheet.pdf"
    template.write_bytes(b"%PDF-test")

    class FakeReader:
        def __init__(self, path):
            self.path = path

        def get_fields(self):
            return {"CharacterName": {}, "STR": {}}

    calls = {}

    class FakeWriter:
        def clone_document_from_reader(self, reader):
            calls["cloned"] = reader.path

        def update_page_form_field_values(self, page, fields, auto_regenerate=True, flatten=False):
            calls["page"] = page
            calls["fields"] = fields
            calls["auto_regenerate"] = auto_regenerate
            calls["flatten"] = flatten

        def write(self, stream):
            stream.write(b"%PDF-filled")

    monkeypatch.setattr(CharacterSheetService, "_ensure_template", lambda self: template)
    monkeypatch.setattr(module, "PdfReader", FakeReader)
    monkeypatch.setattr(module, "PdfWriter", FakeWriter)

    item = SimpleNamespace(
        data=CharacterSheetForm(character_name="Flubert", strength=14).model_dump(mode="json")
    )
    content = CharacterSheetDataService(None).export_pdf(item)

    assert content == b"%PDF-filled"
    assert calls["page"] is None
    assert calls["fields"]["CharacterName"] == "Flubert"
    assert calls["fields"]["STR"] == "14"
    assert calls["auto_regenerate"] is False
    assert calls["flatten"] is True
