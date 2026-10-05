import pytest
from pydantic import ValidationError

from db.models import CampaignMembership, CampaignRole, User
from dto.campaign_dto import CampaignCreate
from services.campaign_service import CampaignService
from services.errors import NotFoundError


def test_campaign_creation_persists_campaign_and_creator_as_dm(db):
    creator = User(
        username="campaign_creator",
        email="campaign_creator@example.com",
        password_hash="unused",
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)

    campaign = CampaignService(db).create(
        CampaignCreate(
            name="  The First Expedition  ",
            description="A campaign description",
            epoch_name="  Year One  ",
            creator_user_id=creator.id,
        )
    )

    assert campaign.name == "The First Expedition"
    assert campaign.description == "A campaign description"
    assert campaign.epoch_name == "Year One"

    membership = db.query(CampaignMembership).filter_by(
        campaign_id=campaign.id,
        user_id=creator.id,
    ).one()
    assert membership.role is CampaignRole.DM


def test_campaign_creation_rejects_unknown_creator(db):
    with pytest.raises(NotFoundError, match="Creator user not found"):
        CampaignService(db).create(
            CampaignCreate(
                name="Orphan Campaign",
                creator_user_id=999999,
            )
        )


@pytest.mark.parametrize("field", ["name", "epoch_name"])
def test_campaign_creation_rejects_whitespace_only_required_text(field):
    payload = {
        "name": "Valid name",
        "epoch_name": "Valid epoch",
        "creator_user_id": 1,
        field: "   ",
    }

    with pytest.raises(ValidationError):
        CampaignCreate(**payload)
