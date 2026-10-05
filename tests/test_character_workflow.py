import pytest
from pydantic import ValidationError

from db.models import Campaign, CampaignMembership, CampaignRole, CharacterStatus, User
from dto.character_dto import CharacterCreate
from services.character_service import CharacterService
from services.errors import ForbiddenOperationError, NotFoundError


def _seed_campaign(db):
    owner = User(username="character_owner", email="character_owner@example.com", password_hash="unused")
    outsider = User(username="character_outsider", email="character_outsider@example.com", password_hash="unused")
    campaign = Campaign(name="Character Campaign", epoch_name="Day 1")
    db.add_all([owner, outsider, campaign])
    db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    db.commit()
    return owner, outsider, campaign


def test_character_creation_persists_campaign_owner_and_defaults(db):
    owner, _, campaign = _seed_campaign(db)

    character = CharacterService(db).create(
        campaign.id,
        CharacterCreate(
            owner_user_id=owner.id,
            name="  Mira  ",
            race="Human",
            character_class="Ranger",
            level=1,
        ),
    )

    assert character.campaign_id == campaign.id
    assert character.owner_user_id == owner.id
    assert character.name == "Mira"
    assert character.status is CharacterStatus.ACTIVE
    assert character.current_game_minute == 0


def test_character_creation_rejects_invalid_campaign_and_owner(db):
    owner, _, campaign = _seed_campaign(db)
    data = CharacterCreate(owner_user_id=owner.id, name="Mira")

    with pytest.raises(NotFoundError, match="Campaign not found"):
        CharacterService(db).create(999999, data)

    with pytest.raises(NotFoundError, match="Owner user not found"):
        CharacterService(db).create(campaign.id, data.model_copy(update={"owner_user_id": 999999}))


def test_character_creation_rejects_non_member_owner(db):
    _, outsider, campaign = _seed_campaign(db)

    with pytest.raises(ForbiddenOperationError, match="must be a member"):
        CharacterService(db).create(
            campaign.id,
            CharacterCreate(owner_user_id=outsider.id, name="Mira"),
        )


def test_character_creation_rejects_whitespace_only_name():
    with pytest.raises(ValidationError):
        CharacterCreate(owner_user_id=1, name="   ")
